from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, update

from app.models import review_attempts, review_sessions, source_items, sources, study_progress, vocab_items
from app.services.dashboard_service import get_dashboard
from app.services.settings_service import set_daily_lesson_cap
from app.services.time_utils import start_of_local_day_utc, today_local_date


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _forecast_boundaries():
    """Mirrors _review_forecast's own boundary computation so tests can place
    items precisely relative to real local-midnight boundaries. get_dashboard()
    has no injectable clock, matching this file's existing real-clock,
    relative-offset style (see the daily-streak tests below)."""
    now = _now_naive()
    midnight_today = start_of_local_day_utc(now.replace(tzinfo=timezone.utc))
    boundaries = [midnight_today + timedelta(days=i) for i in range(1, 6)]
    return now, boundaries


def _make_item(conn, japanese, kana, srs_stage=0, next_review_at=None, item_type="word"):
    item_id = conn.execute(
        insert(vocab_items).values(
            item_type=item_type,
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


def test_srs_distribution_by_type_splits_word_and_phrase(engine):
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=0, item_type="word")
        _make_item(conn, "b", "b", srs_stage=0, item_type="word")
        _make_item(conn, "c", "c", srs_stage=0, item_type="phrase")
        _make_item(conn, "d", "d", srs_stage=5, item_type="phrase")

    result = get_dashboard(engine)

    assert result["srs_distribution_by_type"]["0"] == {"word": 2, "phrase": 1}
    assert result["srs_distribution_by_type"]["5"] == {"word": 0, "phrase": 1}
    assert result["srs_distribution_by_type"]["9"] == {"word": 0, "phrase": 0}
    # The existing blended distribution is untouched by the new by-type field.
    assert result["srs_distribution"]["0"] == 3
    assert result["srs_distribution"]["5"] == 1


# --- review forecast --------------------------------------------------------------


def test_forecast_today_bucket_ends_at_local_midnight(engine):
    now, boundaries = _forecast_boundaries()
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=1, next_review_at=boundaries[0] - timedelta(minutes=1))
        _make_item(conn, "b", "b", srs_stage=1, next_review_at=boundaries[0] + timedelta(minutes=1))

    result = get_dashboard(engine)
    rows = result["review_forecast"]["rows"]

    assert rows[0]["new_items"] == 1
    assert rows[1]["new_items"] == 1


def test_forecast_next_four_rows_are_subsequent_local_calendar_days(engine):
    result = get_dashboard(engine)
    rows = result["review_forecast"]["rows"]

    assert len(rows) == 5
    local_date = today_local_date()
    expected_labels = [(local_date + timedelta(days=i)).strftime("%a") for i in range(5)]
    assert [r["label"] for r in rows] == expected_labels


def test_forecast_currently_due_items_count_toward_cumulative_not_new(engine):
    now, boundaries = _forecast_boundaries()
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=1, next_review_at=now - timedelta(hours=1))  # already overdue

    result = get_dashboard(engine)
    rows = result["review_forecast"]["rows"]

    assert rows[0]["new_items"] == 0  # not "new" today -- it was already due before "now"
    assert rows[0]["cumulative_available"] == 1  # but still counted as available
    assert rows[4]["cumulative_available"] == 1  # stays flat since nothing new becomes due later


def test_forecast_future_items_land_in_correct_day_bucket(engine):
    now, boundaries = _forecast_boundaries()
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=1, next_review_at=boundaries[0] - timedelta(minutes=30))
        _make_item(conn, "b", "b", srs_stage=1, next_review_at=boundaries[1] - timedelta(minutes=30))
        _make_item(conn, "c", "c", srs_stage=1, next_review_at=boundaries[2] - timedelta(minutes=30))
        _make_item(conn, "d", "d", srs_stage=1, next_review_at=boundaries[3] - timedelta(minutes=30))
        _make_item(conn, "e", "e", srs_stage=1, next_review_at=boundaries[4] - timedelta(minutes=30))

    result = get_dashboard(engine)
    rows = result["review_forecast"]["rows"]

    assert [r["new_items"] for r in rows] == [1, 1, 1, 1, 1]


def test_forecast_excludes_stage_zero_and_stage_nine(engine):
    now, boundaries = _forecast_boundaries()
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=0, next_review_at=now + timedelta(hours=1))  # unstarted
        _make_item(conn, "b", "b", srs_stage=9, next_review_at=now + timedelta(hours=1))  # burned
        _make_item(conn, "c", "c", srs_stage=1, next_review_at=now + timedelta(hours=1))  # included

    result = get_dashboard(engine)
    rows = result["review_forecast"]["rows"]

    assert rows[0]["new_items"] == 1
    assert rows[0]["cumulative_available"] == 1


def test_forecast_excludes_null_next_review_at(engine):
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=1, next_review_at=None)

    result = get_dashboard(engine)
    rows = result["review_forecast"]["rows"]

    assert all(r["new_items"] == 0 for r in rows)
    assert all(r["cumulative_available"] == 0 for r in rows)


def test_forecast_cumulative_totals_increase_correctly_across_rows(engine):
    now, boundaries = _forecast_boundaries()
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=1, next_review_at=now - timedelta(hours=1))  # backlog
        _make_item(conn, "b", "b", srs_stage=1, next_review_at=boundaries[0] - timedelta(minutes=30))  # row 0
        _make_item(conn, "c", "c", srs_stage=1, next_review_at=boundaries[2] - timedelta(minutes=30))  # row 2

    result = get_dashboard(engine)
    rows = result["review_forecast"]["rows"]

    assert [r["new_items"] for r in rows] == [1, 0, 1, 0, 0]
    assert [r["cumulative_available"] for r in rows] == [2, 2, 3, 3, 3]


def test_forecast_header_matches_first_row(engine):
    now, boundaries = _forecast_boundaries()
    with engine.begin() as conn:
        _make_item(conn, "a", "a", srs_stage=1, next_review_at=boundaries[0] - timedelta(minutes=30))

    result = get_dashboard(engine)
    forecast = result["review_forecast"]

    assert forecast["header_label"] == "Next 24 Hours:"
    assert forecast["header_new_items"] == forecast["rows"][0]["new_items"] == 1


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


def test_daily_lesson_cap_resets_at_local_midnight_not_a_rolling_window(engine):
    now = _now_naive()
    midnight_today = start_of_local_day_utc(now.replace(tzinfo=timezone.utc))

    with engine.begin() as conn:
        # Learned yesterday, just before today's local midnight -- must NOT
        # count toward today's cap, even though it's well within the last 24h.
        yesterday_item = _make_item(conn, "a", "a")
        conn.execute(
            update(study_progress)
            .where(study_progress.c.item_id == yesterday_item)
            .values(learned_at=midnight_today - timedelta(minutes=1))
        )
        # Learned today, just after local midnight -- must count.
        today_item = _make_item(conn, "b", "b")
        conn.execute(
            update(study_progress)
            .where(study_progress.c.item_id == today_item)
            .values(learned_at=midnight_today + timedelta(minutes=1))
        )

    result = get_dashboard(engine)

    assert result["lessons_learned_today"] == 1


def test_dashboard_respects_custom_daily_lesson_cap(engine):
    with engine.begin() as conn:
        source_id = conn.execute(
            insert(sources).values(source_key="work", display_name="Work", file_path="work.xlsx")
        ).inserted_primary_key[0]
        for i in range(5):
            item_id = _make_item(conn, f"item{i}", f"kana{i}", srs_stage=0)
            conn.execute(
                insert(source_items).values(
                    source_id=source_id, item_id=item_id, source_level=1, level_position=i + 1, is_active=True
                )
            )
        set_daily_lesson_cap(conn, 2)

    result = get_dashboard(engine)

    assert result["daily_lesson_cap"] == 2
    assert result["lessons_available"] == 2  # 5 eligible items, clamped to the custom cap of 2


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


def test_lesson_quiz_activity_does_not_count_toward_daily_streak(engine):
    with engine.begin() as conn:
        session_id = conn.execute(
            insert(review_sessions).values(session_type="lesson_quiz")
        ).inserted_primary_key[0]
        item_id = _make_item(conn, "a", "a", srs_stage=0)
        conn.execute(
            insert(review_attempts).values(
                session_id=session_id,
                item_id=item_id,
                prompt_type="meaning",
                submitted_answer="x",
                normalized_answer="x",
                is_correct=True,
                created_at=_now_naive(),
            )
        )

    result = get_dashboard(engine)

    assert result["daily_streak"] == 0
