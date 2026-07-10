from datetime import datetime, timedelta, timezone

import pytest
from dateutil.relativedelta import relativedelta
from sqlalchemy import insert, select

from app.models import item_forms, item_meanings, study_progress, vocab_items
from app.services.review_service import (
    SRS_INTERVALS,
    NoDueItemsError,
    ReviewSessionNotFoundError,
    complete_review_session,
    get_reviews_available,
    record_review_answer,
    start_review_session,
)


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_item(conn, japanese, kana, meanings, srs_stage=1, next_review_at=None, romaji="r"):
    item_id = conn.execute(
        insert(vocab_items).values(
            item_type="word",
            japanese=japanese,
            kana=kana,
            romaji=romaji,
            part_of_speech="noun",
            normalized_japanese=japanese,
            normalized_kana=kana,
        )
    ).inserted_primary_key[0]
    conn.execute(
        insert(item_forms).values(item_id=item_id, form=japanese, normalized_form=japanese, form_type="display")
    )
    conn.execute(insert(item_forms).values(item_id=item_id, form=kana, normalized_form=kana, form_type="kana"))
    for meaning in meanings:
        conn.execute(
            insert(item_meanings).values(
                item_id=item_id, meaning=meaning, normalized_meaning=meaning.lower(), origin="imported"
            )
        )
    conn.execute(
        insert(study_progress).values(item_id=item_id, srs_stage=srs_stage, next_review_at=next_review_at)
    )
    return item_id


def _due_item(conn, japanese, kana, meanings, srs_stage=1):
    return _make_item(conn, japanese, kana, meanings, srs_stage=srs_stage, next_review_at=_now_naive() - timedelta(hours=1))


# --- selection / availability ---------------------------------------------------


def test_reviews_available_excludes_unlearned_burned_future_and_null(engine):
    with engine.begin() as conn:
        _due_item(conn, "a", "a", ["m"], srs_stage=1)  # due
        _make_item(conn, "b", "b", ["m"], srs_stage=0, next_review_at=_now_naive() - timedelta(hours=1))  # unlearned
        _make_item(conn, "c", "c", ["m"], srs_stage=9, next_review_at=_now_naive() - timedelta(hours=1))  # burned
        _make_item(conn, "d", "d", ["m"], srs_stage=1, next_review_at=_now_naive() + timedelta(hours=1))  # future
        _make_item(conn, "e", "e", ["m"], srs_stage=1, next_review_at=None)  # never scheduled

    result = get_reviews_available(engine)

    assert result["reviews_available"] == 1


def test_start_review_session_returns_all_due_items_with_full_detail(engine):
    with engine.begin() as conn:
        _due_item(conn, "確認", "かくにん", ["confirm", "verify"], srs_stage=1)
        _due_item(conn, "了解", "りょうかい", ["understood"], srs_stage=2)

    result = start_review_session(engine)

    assert len(result["items"]) == 2
    japanese_forms = {item["japanese"] for item in result["items"]}
    assert japanese_forms == {"確認", "了解"}


def test_start_review_session_raises_when_none_due(engine):
    with pytest.raises(NoDueItemsError):
        start_review_session(engine)


# --- grading ----------------------------------------------------------------------


def test_japanese_prompt_is_binary_wrong_is_final_no_retry(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["confirm"])
    session_id = start_review_session(engine)["session_id"]

    result = record_review_answer(engine, session_id, item_id, "japanese", "kakunin")  # romaji

    assert result["status"] == "incorrect"
    assert result["correct_answers"] == ["確認", "かくにん"]

    # resubmitting the same prompt again is idempotent, not a fresh retry
    second = record_review_answer(engine, session_id, item_id, "japanese", "かくにん")
    assert second["status"] == "incorrect"  # still reports the original (final) resolution


def test_meaning_typo_warning_does_not_resolve_and_allows_retry(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"])
    session_id = start_review_session(engine)["session_id"]

    typo_result = record_review_answer(engine, session_id, item_id, "meaning", "cheek")
    assert typo_result["status"] == "typo_warning"
    assert typo_result["correct_answers"] == []
    assert typo_result["item_resolved"] is False

    retry_result = record_review_answer(engine, session_id, item_id, "meaning", "check")
    assert retry_result["status"] == "correct"


def test_genuinely_wrong_meaning_is_resolved_incorrect(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"])
    session_id = start_review_session(engine)["session_id"]

    result = record_review_answer(engine, session_id, item_id, "meaning", "completely wrong")
    assert result["status"] == "incorrect"
    assert result["correct_answers"] == ["check"]


# --- item-level pass/fail and SRS -------------------------------------------------


def test_item_advances_only_when_both_prompts_correct(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=1)
    session_id = start_review_session(engine)["session_id"]

    meaning_result = record_review_answer(engine, session_id, item_id, "meaning", "check")
    assert meaning_result["item_resolved"] is False

    japanese_result = record_review_answer(engine, session_id, item_id, "japanese", "かくにん")
    assert japanese_result["item_resolved"] is True
    assert japanese_result["item_passed"] is True
    assert japanese_result["new_srs_stage"] == 2

    with engine.connect() as conn:
        progress = conn.execute(select(study_progress).where(study_progress.c.item_id == item_id)).mappings().first()

    assert progress["srs_stage"] == 2
    assert progress["total_reviews"] == 1
    assert progress["correct_reviews"] == 1
    assert progress["incorrect_reviews"] == 0
    assert progress["current_correct_streak"] == 1
    assert progress["longest_correct_streak"] == 1
    assert progress["next_review_at"].minute == 0
    assert progress["next_review_at"].second == 0
    raw_target = _now_naive() + SRS_INTERVALS[2]
    assert progress["next_review_at"] <= raw_target
    assert raw_target - progress["next_review_at"] < timedelta(hours=1)


def test_item_demotes_when_either_prompt_wrong(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=3)
    session_id = start_review_session(engine)["session_id"]

    record_review_answer(engine, session_id, item_id, "meaning", "check")
    record_review_answer(engine, session_id, item_id, "japanese", "wrong")

    with engine.connect() as conn:
        progress = conn.execute(select(study_progress).where(study_progress.c.item_id == item_id)).mappings().first()

    assert progress["srs_stage"] == 2  # demoted by exactly one stage
    assert progress["total_reviews"] == 1
    assert progress["incorrect_reviews"] == 1
    assert progress["correct_reviews"] == 0
    assert progress["current_correct_streak"] == 0


def test_demotion_never_goes_below_apprentice_1(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=1)
    session_id = start_review_session(engine)["session_id"]

    record_review_answer(engine, session_id, item_id, "meaning", "wrong")
    record_review_answer(engine, session_id, item_id, "japanese", "wrong")

    with engine.connect() as conn:
        stage = conn.execute(select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)).scalar()

    assert stage == 1


def test_stage_8_pass_burns_the_item(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=8)
    session_id = start_review_session(engine)["session_id"]

    record_review_answer(engine, session_id, item_id, "meaning", "check")
    result = record_review_answer(engine, session_id, item_id, "japanese", "かくにん")

    assert result["burned"] is True
    assert result["new_srs_stage"] == 9

    with engine.connect() as conn:
        progress = conn.execute(select(study_progress).where(study_progress.c.item_id == item_id)).mappings().first()

    assert progress["srs_stage"] == 9
    assert progress["burned_at"] is not None
    assert progress["next_review_at"] is None

    # burned items must leave the normal review queue
    availability = get_reviews_available(engine)
    assert availability["reviews_available"] == 0


def test_prompt_level_counters_are_independent_of_item_level_outcome(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=2)
    session_id = start_review_session(engine)["session_id"]

    record_review_answer(engine, session_id, item_id, "meaning", "check")  # correct
    record_review_answer(engine, session_id, item_id, "japanese", "wrong")  # incorrect

    with engine.connect() as conn:
        progress = conn.execute(select(study_progress).where(study_progress.c.item_id == item_id)).mappings().first()

    assert progress["meaning_correct"] == 1
    assert progress["meaning_incorrect"] == 0
    assert progress["japanese_correct"] == 0
    assert progress["japanese_incorrect"] == 1
    # item-level counters reflect ONE failed review, not two
    assert progress["total_reviews"] == 1
    assert progress["incorrect_reviews"] == 1


def test_typo_warning_does_not_increment_prompt_counters(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=2)
    session_id = start_review_session(engine)["session_id"]

    record_review_answer(engine, session_id, item_id, "meaning", "cheek")  # typo warning

    with engine.connect() as conn:
        progress = conn.execute(select(study_progress).where(study_progress.c.item_id == item_id)).mappings().first()

    assert progress["meaning_correct"] == 0
    assert progress["meaning_incorrect"] == 0
    assert progress["total_reviews"] == 0


def test_redundant_resubmission_after_resolution_does_not_double_count(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=1)
    session_id = start_review_session(engine)["session_id"]

    record_review_answer(engine, session_id, item_id, "meaning", "check")
    record_review_answer(engine, session_id, item_id, "japanese", "かくにん")

    with engine.connect() as conn:
        stage_after_first = conn.execute(
            select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)
        ).scalar()

    # resubmitting a resolved prompt must not re-trigger SRS processing
    repeat = record_review_answer(engine, session_id, item_id, "japanese", "かくにん")
    assert repeat["new_srs_stage"] is None

    with engine.connect() as conn:
        progress = conn.execute(select(study_progress).where(study_progress.c.item_id == item_id)).mappings().first()

    assert progress["srs_stage"] == stage_after_first
    assert progress["total_reviews"] == 1


# --- calendar-month intervals ------------------------------------------------------


def test_srs_intervals_use_relativedelta_for_stages_seven_and_eight():
    assert SRS_INTERVALS[7] == relativedelta(months=1)
    assert SRS_INTERVALS[8] == relativedelta(months=4)


def test_month_end_calendar_arithmetic_does_not_crash_and_is_valid():
    start = datetime(2026, 1, 31)

    one_month_later = start + SRS_INTERVALS[7]
    assert one_month_later.year == 2026
    assert one_month_later.month == 2
    assert one_month_later.day == 28  # clamped: 2026 is not a leap year

    four_months_later = datetime(2026, 5, 31) + SRS_INTERVALS[8]
    assert four_months_later.year == 2026
    assert four_months_later.month == 9
    assert four_months_later.day == 30  # clamped: September has 30 days


def test_stage_seven_advancement_schedules_a_calendar_month_out(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=6)
    session_id = start_review_session(engine)["session_id"]
    before = _now_naive()

    record_review_answer(engine, session_id, item_id, "meaning", "check")
    record_review_answer(engine, session_id, item_id, "japanese", "かくにん")

    with engine.connect() as conn:
        next_review_at = conn.execute(
            select(study_progress.c.next_review_at).where(study_progress.c.item_id == item_id)
        ).scalar()

    raw_target = before + relativedelta(months=1)
    assert next_review_at.minute == 0
    assert next_review_at.second == 0
    assert next_review_at <= raw_target
    assert raw_target - next_review_at < timedelta(hours=1)


# --- session bookkeeping ------------------------------------------------------------


def test_complete_review_session_marks_completed_and_lists_results(engine):
    with engine.begin() as conn:
        item_id = _due_item(conn, "確認", "かくにん", ["check"], srs_stage=1)
    session_id = start_review_session(engine)["session_id"]

    record_review_answer(engine, session_id, item_id, "meaning", "check")
    record_review_answer(engine, session_id, item_id, "japanese", "かくにん")

    result = complete_review_session(engine, session_id)

    assert result["completed_at"] is not None
    assert result["results"] == [{"item_id": item_id, "passed": True, "new_srs_stage": 2}]


def test_record_review_answer_raises_for_unknown_session(engine):
    with pytest.raises(ReviewSessionNotFoundError):
        record_review_answer(engine, 999, 1, "meaning", "check")


def test_complete_raises_for_unknown_session(engine):
    with pytest.raises(ReviewSessionNotFoundError):
        complete_review_session(engine, 999)
