from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.engine import Connection, Engine

from app.core.config import settings
from app.models import review_attempts, review_sessions, sources, study_progress, vocab_items
from app.services.lesson_service import eligible_lesson_item_ids, lessons_learned_today
from app.services.level_service import get_sources_overview
from app.services.time_utils import today_local_date, utc_to_local_date


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
    rows = conn.execute(
        select(study_progress.c.item_id).where(
            study_progress.c.srs_stage.between(1, 8),
            study_progress.c.next_review_at.is_not(None),
            study_progress.c.next_review_at <= now_naive_utc,
        )
    ).all()
    return len(rows)


def _srs_distribution(conn: Connection) -> Dict[str, int]:
    rows = conn.execute(select(study_progress.c.srs_stage)).all()
    distribution = {str(stage): 0 for stage in range(10)}
    for (stage,) in rows:
        distribution[str(stage)] += 1
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
        remaining_cap = max(0, settings.daily_lesson_cap - learned_today)
        lessons_available = min(len(eligible_ids), remaining_cap)

        return {
            "lessons_available": lessons_available,
            "daily_lesson_cap": settings.daily_lesson_cap,
            "lessons_learned_today": learned_today,
            "reviews_available": _reviews_available_count(conn, now_naive_utc),
            "srs_distribution": _srs_distribution(conn),
            "daily_streak": _compute_daily_streak(conn),
            "new_items_last_7_days": _new_items_last_7_days(conn, now_naive_utc),
            "sources": overview,
        }
