from datetime import timedelta

import pytest
from sqlalchemy import insert, select

from app.models import item_forms, item_meanings, source_items, sources, study_progress, vocab_items
from app.services.lesson_service import (
    LessonSessionNotFoundError,
    NoEligibleItemsError,
    SourceNotFoundError,
    complete_lesson_session,
    get_lessons_available,
    record_lesson_answer,
    start_lesson_session,
)


def _make_source(conn, key="work"):
    return conn.execute(
        insert(sources).values(source_key=key, display_name=key.title(), file_path=f"{key}.xlsx")
    ).inserted_primary_key[0]


def _make_item(conn, japanese, kana, meanings, romaji="r", srs_stage=0):
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
    conn.execute(insert(study_progress).values(item_id=item_id, srs_stage=srs_stage))
    return item_id


def _place(conn, source_id, item_id, level=1, position=1, active=True):
    conn.execute(
        insert(source_items).values(
            source_id=source_id, item_id=item_id, source_level=level, level_position=position, is_active=active
        )
    )


def test_get_lessons_available_reflects_eligible_counts(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_id, item_id)

    result = get_lessons_available(engine)

    assert result["daily_lesson_cap"] == 10
    assert result["remaining_today"] == 10
    assert result["sources"][0]["lessons_available_in_source"] == 1


def test_start_lesson_session_returns_batch_with_full_content(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", ["confirm", "verify"])
        _place(conn, source_id, item_id)

    result = start_lesson_session(engine, source_id)

    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["item_id"] == item_id
    assert item["japanese"] == "確認"
    assert item["kana"] == "かくにん"
    assert set(item["meanings"]) == {"confirm", "verify"}
    assert item["notes"] == {"note_text": None, "mnemonic_text": None}


def test_start_lesson_session_raises_for_unknown_source(engine):
    with pytest.raises(SourceNotFoundError):
        start_lesson_session(engine, 999)


def test_start_lesson_session_raises_when_no_eligible_items(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)

    with pytest.raises(NoEligibleItemsError):
        start_lesson_session(engine, source_id)


def test_batch_size_capped_at_five(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        for i in range(8):
            item_id = _make_item(conn, f"item{i}", f"kana{i}", ["meaning"])
            _place(conn, source_id, item_id, position=i + 1)

    result = start_lesson_session(engine, source_id)

    assert len(result["items"]) == 5


def test_locked_level_items_are_excluded_from_the_batch(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        unlocked_item = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_id, unlocked_item, level=1, position=1)
        locked_item = _make_item(conn, "了解", "りょうかい", ["understood"])
        _place(conn, source_id, locked_item, level=2, position=1)

    result = start_lesson_session(engine, source_id)

    assert [item["item_id"] for item in result["items"]] == [unlocked_item]


def test_per_prompt_requeue_item_not_activated_until_both_prompts_correct(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_id, item_id)

    session_id = start_lesson_session(engine, source_id)["session_id"]

    meaning_result = record_lesson_answer(engine, session_id, item_id, "meaning", "confirm")
    assert meaning_result["is_correct"] is True
    assert meaning_result["item_passed"] is False
    assert meaning_result["item_activated"] is False

    japanese_wrong = record_lesson_answer(engine, session_id, item_id, "japanese", "kakunin")
    assert japanese_wrong["is_correct"] is False  # romaji rejected
    assert japanese_wrong["item_passed"] is False

    with engine.connect() as conn:
        stage = conn.execute(select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)).scalar()
    assert stage == 0

    japanese_right = record_lesson_answer(engine, session_id, item_id, "japanese", "かくにん")
    assert japanese_right["is_correct"] is True
    assert japanese_right["item_passed"] is True
    assert japanese_right["item_activated"] is True


def test_activation_sets_learned_at_and_rounds_next_review_to_the_hour(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_id, item_id)

    session_id = start_lesson_session(engine, source_id)["session_id"]
    record_lesson_answer(engine, session_id, item_id, "meaning", "confirm")
    record_lesson_answer(engine, session_id, item_id, "japanese", "かくにん")

    with engine.connect() as conn:
        progress = conn.execute(
            select(study_progress).where(study_progress.c.item_id == item_id)
        ).mappings().first()

    assert progress["srs_stage"] == 1
    assert progress["learned_at"] is not None
    assert progress["next_review_at"].minute == 0
    assert progress["next_review_at"].second == 0
    raw_target = progress["learned_at"] + timedelta(hours=4)
    assert progress["next_review_at"] <= raw_target
    assert raw_target - progress["next_review_at"] < timedelta(hours=1)


def test_activation_does_not_touch_review_stat_counters(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_id, item_id)

    session_id = start_lesson_session(engine, source_id)["session_id"]
    record_lesson_answer(engine, session_id, item_id, "meaning", "wrong first try")
    record_lesson_answer(engine, session_id, item_id, "meaning", "confirm")
    record_lesson_answer(engine, session_id, item_id, "japanese", "かくにん")

    with engine.connect() as conn:
        progress = conn.execute(
            select(study_progress).where(study_progress.c.item_id == item_id)
        ).mappings().first()

    assert progress["srs_stage"] == 1
    assert progress["total_reviews"] == 0
    assert progress["correct_reviews"] == 0
    assert progress["incorrect_reviews"] == 0
    assert progress["meaning_correct"] == 0
    assert progress["meaning_incorrect"] == 0
    assert progress["japanese_correct"] == 0
    assert progress["japanese_incorrect"] == 0


def test_redundant_correct_answer_after_activation_is_a_no_op(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_id, item_id)

    session_id = start_lesson_session(engine, source_id)["session_id"]
    record_lesson_answer(engine, session_id, item_id, "meaning", "confirm")
    first_activation = record_lesson_answer(engine, session_id, item_id, "japanese", "かくにん")
    assert first_activation["item_activated"] is True

    with engine.connect() as conn:
        learned_at_first = conn.execute(
            select(study_progress.c.learned_at).where(study_progress.c.item_id == item_id)
        ).scalar()

    second_attempt = record_lesson_answer(engine, session_id, item_id, "japanese", "かくにん")
    assert second_attempt["item_activated"] is False  # already activated, no-op

    with engine.connect() as conn:
        stage, learned_at_second = conn.execute(
            select(study_progress.c.srs_stage, study_progress.c.learned_at).where(
                study_progress.c.item_id == item_id
            )
        ).first()
    assert stage == 1
    assert learned_at_second == learned_at_first


def test_duplicate_item_across_sources_becomes_ineligible_after_activation(engine):
    with engine.begin() as conn:
        source_a = _make_source(conn, "work")
        source_b = _make_source(conn, "manga")
        shared_item = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_a, shared_item)
        _place(conn, source_b, shared_item)

    before = get_lessons_available(engine)
    assert {s["source_id"]: s["lessons_available_in_source"] for s in before["sources"]} == {
        source_a: 1,
        source_b: 1,
    }

    session_id = start_lesson_session(engine, source_a)["session_id"]
    record_lesson_answer(engine, session_id, shared_item, "meaning", "confirm")
    record_lesson_answer(engine, session_id, shared_item, "japanese", "かくにん")

    after = get_lessons_available(engine)
    assert {s["source_id"]: s["lessons_available_in_source"] for s in after["sources"]} == {
        source_a: 0,
        source_b: 0,
    }


def test_complete_lesson_session_marks_completed_and_lists_activated_items(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", ["confirm"])
        _place(conn, source_id, item_id)

    session_id = start_lesson_session(engine, source_id)["session_id"]
    record_lesson_answer(engine, session_id, item_id, "meaning", "confirm")
    record_lesson_answer(engine, session_id, item_id, "japanese", "かくにん")

    result = complete_lesson_session(engine, session_id)

    assert result["activated_item_ids"] == [item_id]
    assert result["completed_at"] is not None


def test_record_lesson_answer_raises_for_unknown_session(engine):
    with pytest.raises(LessonSessionNotFoundError):
        record_lesson_answer(engine, 999, 1, "meaning", "confirm")


def test_complete_raises_for_unknown_session(engine):
    with pytest.raises(LessonSessionNotFoundError):
        complete_lesson_session(engine, 999)
