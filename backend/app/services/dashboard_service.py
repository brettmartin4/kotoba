from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import func, select, update
from sqlalchemy.engine import Connection, Engine

from app.models import review_attempts, review_sessions, sources, study_progress, vocab_items
from app.services.lesson_service import eligible_lesson_item_ids, lessons_learned_today
from app.services.level_service import get_sources_overview
from app.services.review_service import select_due_item_ids
from app.services.settings_service import get_daily_lesson_cap
from app.services.time_utils import start_of_local_day_utc, today_local_date, utc_to_local_date

FORECAST_ROW_COUNT = 5


def rename_source(conn: Connection, source_id: int, display_name: str) -> Optional[dict]:
    existing = conn.execute(select(sources).where(sources.c.id == source_id)).mappings().first()
    if existing is None:
        return None
    conn.execute(
        update(sources)
        .where(sources.c.id == source_id)
        .values(display_name=display_name, updated_at=datetime.now(timezone.utc))
    )
    updated = conn.execute(select(sources).where(sources.c.id == source_id)).mappings().first()
    return dict(updated)


def _reviews_available_count(conn: Connection, now_naive_utc: datetime) -> int:
    return len(select_due_item_ids(conn, now_naive_utc))


def _review_forecast(conn: Connection, now_naive_utc: datetime) -> dict:
    """Five-row review forecast: row 0 is "today" (now until local midnight),
    rows 1-4 are the next four local calendar days. Counts all reviewable
    item types together (no word/phrase split here, unlike Item Spread).

    Eligible items match select_due_item_ids's own criteria (stage 1-8,
    non-null next_review_at) but aren't limited to already-due -- this needs
    every scheduled time, past and future, to bucket correctly.
    """
    # start_of_local_day_utc() converts via .astimezone(), which requires an
    # *aware* datetime -- passing the naive now_naive_utc directly would be
    # silently misinterpreted as naive local time instead of UTC, the same
    # pitfall utc_to_local_date already guards against.
    midnight_today = start_of_local_day_utc(now_naive_utc.replace(tzinfo=timezone.utc))
    boundaries = [midnight_today + timedelta(days=i) for i in range(1, FORECAST_ROW_COUNT + 1)]

    review_times = [
        r[0]
        for r in conn.execute(
            select(study_progress.c.next_review_at).where(
                study_progress.c.srs_stage.between(1, 8),
                study_progress.c.next_review_at.is_not(None),
            )
        ).all()
    ]

    cumulative = sum(1 for t in review_times if t <= now_naive_utc)
    local_date = today_local_date()

    rows = []
    window_start = now_naive_utc
    for i, boundary in enumerate(boundaries):
        new_items = sum(1 for t in review_times if window_start < t <= boundary)
        cumulative += new_items
        rows.append(
            {
                "label": (local_date + timedelta(days=i)).strftime("%a"),
                "start_at": window_start,
                "end_at": boundary,
                "new_items": new_items,
                "cumulative_available": cumulative,
            }
        )
        window_start = boundary

    return {
        "header_label": "Next 24 Hours:",
        "header_new_items": rows[0]["new_items"],
        "rows": rows,
    }


def _srs_distribution(conn: Connection) -> Dict[str, int]:
    rows = conn.execute(select(study_progress.c.srs_stage)).all()
    distribution = {str(stage): 0 for stage in range(10)}
    for (stage,) in rows:
        distribution[str(stage)] += 1
    return distribution


def _srs_distribution_by_type(conn: Connection) -> Dict[str, Dict[str, int]]:
    """Same 10 stages as _srs_distribution, but split by item_type -- for the
    Item Spread dashboard panel. Additive: _srs_distribution itself is
    untouched so existing consumers of its blended shape keep working."""
    rows = conn.execute(
        select(study_progress.c.srs_stage, vocab_items.c.item_type, func.count())
        .select_from(study_progress.join(vocab_items, study_progress.c.item_id == vocab_items.c.id))
        .group_by(study_progress.c.srs_stage, vocab_items.c.item_type)
    ).all()
    distribution = {str(stage): {"word": 0, "phrase": 0} for stage in range(10)}
    for stage, item_type, count in rows:
        distribution[str(stage)][item_type] = count
    return distribution


def _new_items_last_7_days(conn: Connection, now_naive_utc: datetime) -> int:
    cutoff = now_naive_utc - timedelta(days=7)
    rows = conn.execute(select(vocab_items.c.id).where(vocab_items.c.created_at >= cutoff)).all()
    return len(rows)


def _compute_daily_streak(conn: Connection) -> int:
    # Only true review activity counts toward the streak -- lesson_quiz sessions
    # must never inflate it, so this joins back to review_sessions and filters.
    rows = conn.execute(
        select(review_attempts.c.created_at)
        .select_from(review_attempts.join(review_sessions, review_attempts.c.session_id == review_sessions.c.id))
        .where(review_sessions.c.session_type == "review")
    ).all()
    local_dates = {utc_to_local_date(r[0]) for r in rows}
    if not local_dates:
        return 0

    day = today_local_date()
    if day not in local_dates:
        day = day - timedelta(days=1)
        if day not in local_dates:
            return 0

    streak = 0
    while day in local_dates:
        streak += 1
        day -= timedelta(days=1)
    return streak


def get_dashboard(engine: Engine) -> dict:
    with engine.connect() as conn:
        now_aware_utc = datetime.now(timezone.utc)
        now_naive_utc = now_aware_utc.replace(tzinfo=None)

        overview = get_sources_overview(conn)
        eligible_ids = eligible_lesson_item_ids(conn, overview)

        learned_today = lessons_learned_today(conn, now_aware_utc)
        daily_lesson_cap = get_daily_lesson_cap(conn)
        remaining_cap = max(0, daily_lesson_cap - learned_today)
        lessons_available = min(len(eligible_ids), remaining_cap)

        return {
            "lessons_available": lessons_available,
            "daily_lesson_cap": daily_lesson_cap,
            "lessons_learned_today": learned_today,
            "reviews_available": _reviews_available_count(conn, now_naive_utc),
            "review_forecast": _review_forecast(conn, now_naive_utc),
            "srs_distribution": _srs_distribution(conn),
            "srs_distribution_by_type": _srs_distribution_by_type(conn),
            "daily_streak": _compute_daily_streak(conn),
            "new_items_last_7_days": _new_items_last_7_days(conn, now_naive_utc),
            "sources": overview,
        }
