from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, update

from app.models import review_attempts, review_sessions, source_items, sources, study_progress, vocab_items
from app.services.dashboard_service import get_dashboard


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_item(conn, japanese, kana, srs_stage=0, next_review_at=None):
    item_id = conn.execute(
        insert(vocab_items).values(
            item_type="word",
            japanese=japanese,
            kana=kana,
            romaji="r",
            part_of_speech="noun",
            normalized_japanese=japanese,
            normalized_kana=kana,
        )
    ).inserted_primary_key[0]
    conn.execute(
        insert(study_progress).values(item_id=item_id, srs_stage=srs_stage, next_review_at=next_review_at)
    )
    return item_id


def test_reviews_available_counts_due_items_regardless_of_source_activity(engine):
    with engine.begin() as conn:
        past = _now_naive() - timedelta(hours=1)
        future = _now_naive() + timedelta(hours=1)
        _make_item(conn, "a", "a", srs_stage=1, next_review_at=past)
        _make_item(conn, "b", "b", srs_stage=1, next_review_at=future)
        _make_item(conn, "c", "c", srs_stage=0, next_review_at=past)  # unlearned
        _make_item(conn, "d", "d", srs_stage=9, next_review_at=past)  # burned

    result = get_dashboard(engine)

    assert result["reviews_available"] == 1


def test_srs_distribution_includes_stage_zero(engine):
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=0)
        _make_item(conn, "b", "b", srs_stage=0)
        _make_item(conn, "c", "c", srs_stage=5)

    result = get_dashboard(engine)

    assert result["srs_distribution"]["0"] == 2
    assert result["srs_distribution"]["5"] == 1
    assert result["srs_distribution"]["9"] == 0


def test_new_items_last_7_days(engine):
    with engine.begin() as conn:
        _make_item(conn, "a", "a")
        old_item = _make_item(conn, "b", "b")
        conn.execute(
            update(vocab_items).where(vocab_items.c.id == old_item).values(created_at=_now_naive() - timedelta(days=10))
        )

    result = get_dashboard(engine)

    assert result["new_items_last_7_days"] == 1


def test_lessons_learned_today_clamps_lessons_available(engine):
    with engine.begin() as conn:
        source_id = conn.execute(
            insert(sources).values(source_key="work", display_name="Work", file_path="work.xlsx")
        ).inserted_primary_key[0]

        for i in range(3):
            item_id = _make_item(conn, f"item{i}", f"kana{i}", srs_stage=0)
            conn.execute(
                insert(source_items).values(
                    source_id=source_id, item_id=item_id, source_level=1, level_position=i + 1, is_active=True
                )
            )

        for i in range(8):
            learned_item = _make_item(conn, f"learned{i}", f"learnedkana{i}", srs_stage=1)
            conn.execute(
                update(study_progress)
                .where(study_progress.c.item_id == learned_item)
                .values(learned_at=_now_naive())
            )

    result = get_dashboard(engine)

    assert result["lessons_learned_today"] == 8
    assert result["lessons_available"] == 2  # remaining cap 10-8=2, clamps the 3 eligible items down to 2


def test_daily_streak_consecutive_days_with_grace_for_today(engine):
    with engine.begin() as conn:
        session_id = conn.execute(
            insert(review_sessions).values(session_type="review")
        ).inserted_primary_key[0]
        item_id = _make_item(conn, "a", "a", srs_stage=1)
        yesterday = _now_naive() - timedelta(days=1)
        two_days_ago = _now_naive() - timedelta(days=2)
        for created_at in (yesterday, two_days_ago):
            conn.execute(
                insert(review_attempts).values(
                    session_id=session_id,
                    item_id=item_id,
                    prompt_type="meaning",
                    submitted_answer="x",
                    normalized_answer="x",
                    is_correct=True,
                    created_at=created_at,
                )
            )

    result = get_dashboard(engine)

    assert result["daily_streak"] == 2


def test_daily_streak_is_zero_when_broken_by_a_gap(engine):
    with engine.begin() as conn:
        session_id = conn.execute(
            insert(review_sessions).values(session_type="review")
        ).inserted_primary_key[0]
        item_id = _make_item(conn, "a", "a", srs_stage=1)
        three_days_ago = _now_naive() - timedelta(days=3)
        conn.execute(
            insert(review_attempts).values(
                session_id=session_id,
                item_id=item_id,
                prompt_type="meaning",
                submitted_answer="x",
                normalized_answer="x",
                is_correct=True,
                created_at=three_days_ago,
            )
        )

    result = get_dashboard(engine)

    assert result["daily_streak"] == 0
