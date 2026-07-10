from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import insert, select, update

from app.models import (
    item_meanings,
    item_notes,
    review_attempts,
    review_sessions,
    similar_items,
    source_items,
    sources,
    study_progress,
    vocab_items,
)
from app.services.item_service import (
    CannotDeleteImportedMeaningError,
    ItemNotFoundError,
    SynonymNotFoundError,
    add_synonym,
    delete_synonym,
    get_item_page,
    list_items,
    update_notes,
)


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _make_source(conn, key="work"):
    return conn.execute(
        insert(sources).values(source_key=key, display_name=key.title(), file_path=f"{key}.xlsx")
    ).inserted_primary_key[0]


def _make_item(conn, japanese, kana, meanings=("check",), item_type="word", srs_stage=0, romaji="r"):
    item_id = conn.execute(
        insert(vocab_items).values(
            item_type=item_type,
            japanese=japanese,
            kana=kana,
            romaji=romaji,
            part_of_speech="noun",
            normalized_japanese=japanese,
            normalized_kana=kana,
        )
    ).inserted_primary_key[0]
    for meaning in meanings:
        conn.execute(
            insert(item_meanings).values(
                item_id=item_id, meaning=meaning, normalized_meaning=meaning.lower(), origin="imported"
            )
        )
    conn.execute(insert(study_progress).values(item_id=item_id, srs_stage=srs_stage))
    return item_id


def _place(conn, source_id, item_id, level=1, position=1, active=True, source_note=None):
    conn.execute(
        insert(source_items).values(
            source_id=source_id,
            item_id=item_id,
            source_level=level,
            level_position=position,
            is_active=active,
            source_note=source_note,
        )
    )


# --- search -----------------------------------------------------------------------


def test_search_matches_japanese_kana_romaji(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", romaji="kakunin")
        _place(conn, source_id, item_id)

    with engine.connect() as conn:
        assert [r["item_id"] for r in list_items(conn, search="確認")] == [item_id]
        assert [r["item_id"] for r in list_items(conn, search="かくにん")] == [item_id]
        assert [r["item_id"] for r in list_items(conn, search="KAKUNIN")] == [item_id]


def test_search_matches_meaning(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", meanings=["confirm", "verify"])
        _place(conn, source_id, item_id)

    with engine.connect() as conn:
        assert [r["item_id"] for r in list_items(conn, search="verify")] == [item_id]


def test_search_matches_notes_and_mnemonic(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん")
        _place(conn, source_id, item_id)
        conn.execute(
            insert(item_notes).values(
                item_id=item_id, note_text="a helpful note", mnemonic_text="remember the kanji", updated_at=_now_naive()
            )
        )

    with engine.connect() as conn:
        assert [r["item_id"] for r in list_items(conn, search="helpful")] == [item_id]
        assert [r["item_id"] for r in list_items(conn, search="remember")] == [item_id]


def test_search_matches_similar_items(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん")
        _place(conn, source_id, item_id)
        conn.execute(insert(similar_items).values(item_id=item_id, similar_text="確かめる"))

    with engine.connect() as conn:
        assert [r["item_id"] for r in list_items(conn, search="確かめる")] == [item_id]


def test_search_matches_source_note_and_display_name(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn, "work")
        item_id = _make_item(conn, "確認", "かくにん")
        _place(conn, source_id, item_id, source_note="seen in an email")

    with engine.connect() as conn:
        assert [r["item_id"] for r in list_items(conn, search="seen in an email")] == [item_id]
        assert [r["item_id"] for r in list_items(conn, search="Work")] == [item_id]


# --- filters ------------------------------------------------------------------------


def test_filter_by_source_id_and_item_type(engine):
    with engine.begin() as conn:
        source_a = _make_source(conn, "work")
        source_b = _make_source(conn, "manga")
        word_item = _make_item(conn, "確認", "かくにん", item_type="word")
        phrase_item = _make_item(conn, "しょうがない", "しょうがない", item_type="phrase")
        _place(conn, source_a, word_item)
        _place(conn, source_b, phrase_item)

    with engine.connect() as conn:
        assert [r["item_id"] for r in list_items(conn, source_id=source_a)] == [word_item]
        assert [r["item_id"] for r in list_items(conn, item_type="phrase")] == [phrase_item]


def test_active_filter_modes(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        active_item = _make_item(conn, "確認", "かくにん")
        inactive_item = _make_item(conn, "了解", "りょうかい")
        _place(conn, source_id, active_item, active=True)
        _place(conn, source_id, inactive_item, position=2, active=False)

    with engine.connect() as conn:
        active_only = {r["item_id"] for r in list_items(conn, active_filter="active_only")}
        everything = {r["item_id"] for r in list_items(conn, active_filter="all")}
        inactive_only = {r["item_id"] for r in list_items(conn, active_filter="inactive_only")}

    assert active_only == {active_item}
    assert everything == {active_item, inactive_item}
    assert inactive_only == {inactive_item}


def test_srs_group_buckets(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        stages = {
            "unstarted": _make_item(conn, "a", "a", srs_stage=0),
            "apprentice": _make_item(conn, "b", "b", srs_stage=3),
            "guru": _make_item(conn, "c", "c", srs_stage=5),
            "master": _make_item(conn, "d", "d", srs_stage=7),
            "enlightened": _make_item(conn, "e", "e", srs_stage=8),
            "burned": _make_item(conn, "f", "f", srs_stage=9),
        }
        for item_id in stages.values():
            _place(conn, source_id, item_id, position=item_id)

    with engine.connect() as conn:
        for group, expected_item_id in stages.items():
            result_ids = {r["item_id"] for r in list_items(conn, srs_group=group)}
            assert result_ids == {expected_item_id}, group


def test_combined_filters_intersect(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        matching = _make_item(conn, "確認", "かくにん", meanings=["confirm"], srs_stage=1)
        wrong_stage = _make_item(conn, "了解", "りょうかい", meanings=["confirm"], srs_stage=5)
        _place(conn, source_id, matching)
        _place(conn, source_id, wrong_stage, position=2)

    with engine.connect() as conn:
        result_ids = {r["item_id"] for r in list_items(conn, search="confirm", srs_group="apprentice")}

    assert result_ids == {matching}


def test_browse_row_aggregates_multiple_source_memberships(engine):
    with engine.begin() as conn:
        source_a = _make_source(conn, "work")
        source_b = _make_source(conn, "manga")
        shared_item = _make_item(conn, "確認", "かくにん")
        _place(conn, source_a, shared_item)
        _place(conn, source_b, shared_item)

    with engine.connect() as conn:
        rows = list_items(conn)

    assert len(rows) == 1
    assert {s["source_id"] for s in rows[0]["sources"]} == {source_a, source_b}


# --- item detail page -----------------------------------------------------------------


def test_get_item_page_returns_none_for_unknown_item(engine):
    with engine.connect() as conn:
        assert get_item_page(conn, 999) is None


def test_get_item_page_includes_all_expected_sections(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", meanings=["confirm"])
        _place(conn, source_id, item_id, source_note="work email")
        conn.execute(insert(similar_items).values(item_id=item_id, similar_text="確かめる"))
        conn.execute(
            insert(item_notes).values(item_id=item_id, note_text="note", mnemonic_text="mnemonic", updated_at=_now_naive())
        )

    with engine.connect() as conn:
        detail = get_item_page(conn, item_id)

    assert detail["japanese"] == "確認"
    assert detail["meanings"][0]["origin"] == "imported"
    assert detail["similar_items"] == ["確かめる"]
    assert detail["sources"][0]["source_note"] == "work email"
    assert detail["notes"] == {"note_text": "note", "mnemonic_text": "mnemonic"}
    assert detail["srs"]["stage"] == 0
    assert detail["srs"]["stage_label"] == "Unstarted"
    assert detail["srs"]["accuracy_percent"] is None
    assert detail["review_history"] == []


def test_get_item_page_computes_accuracy_percent(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", srs_stage=3)
        _place(conn, source_id, item_id)
        conn.execute(
            update(study_progress)
            .where(study_progress.c.item_id == item_id)
            .values(total_reviews=4, correct_reviews=3, incorrect_reviews=1)
        )

    with engine.connect() as conn:
        detail = get_item_page(conn, item_id)

    assert detail["srs"]["accuracy_percent"] == 75.0


def test_review_history_excludes_lesson_quiz_and_caps_at_ten(engine):
    with engine.begin() as conn:
        source_id = _make_source(conn)
        item_id = _make_item(conn, "確認", "かくにん", srs_stage=1)
        _place(conn, source_id, item_id)

        lesson_session_id = conn.execute(
            insert(review_sessions).values(session_type="lesson_quiz")
        ).inserted_primary_key[0]
        conn.execute(
            insert(review_attempts).values(
                session_id=lesson_session_id, item_id=item_id, prompt_type="meaning",
                submitted_answer="x", normalized_answer="x", is_correct=True, created_at=_now_naive(),
            )
        )

        review_session_id = conn.execute(
            insert(review_sessions).values(session_type="review")
        ).inserted_primary_key[0]
        for i in range(12):
            conn.execute(
                insert(review_attempts).values(
                    session_id=review_session_id, item_id=item_id, prompt_type="meaning",
                    submitted_answer="x", normalized_answer="x", is_correct=True,
                    created_at=_now_naive() - timedelta(minutes=i),
                )
            )

    with engine.connect() as conn:
        detail = get_item_page(conn, item_id)

    assert len(detail["review_history"]) == 10


# --- synonyms -------------------------------------------------------------------------


def test_add_synonym_creates_user_synonym(engine):
    with engine.begin() as conn:
        item_id = _make_item(conn, "確認", "かくにん", meanings=["confirm"])

    with engine.begin() as conn:
        result = add_synonym(conn, item_id, "double-check")

    assert result["origin"] == "user_synonym"

    with engine.connect() as conn:
        rows = conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id)).all()
    assert {r[0] for r in rows} == {"confirm", "double-check"}


def test_add_synonym_is_idempotent_on_duplicate(engine):
    with engine.begin() as conn:
        item_id = _make_item(conn, "確認", "かくにん", meanings=["confirm"])

    with engine.begin() as conn:
        add_synonym(conn, item_id, "Confirm")  # normalizes to the same as the existing "confirm"

    with engine.connect() as conn:
        rows = conn.execute(select(item_meanings).where(item_meanings.c.item_id == item_id)).all()
    assert len(rows) == 1  # no duplicate row created


def test_add_synonym_raises_for_unknown_item(engine):
    with engine.begin() as conn:
        with pytest.raises(ItemNotFoundError):
            add_synonym(conn, 999, "anything")


def test_delete_synonym_removes_user_synonym(engine):
    with engine.begin() as conn:
        item_id = _make_item(conn, "確認", "かくにん", meanings=["confirm"])
        synonym = add_synonym(conn, item_id, "double-check")

    with engine.begin() as conn:
        delete_synonym(conn, item_id, synonym["id"])

    with engine.connect() as conn:
        rows = conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id)).all()
    assert {r[0] for r in rows} == {"confirm"}


def test_delete_synonym_rejects_imported_meaning(engine):
    with engine.begin() as conn:
        item_id = _make_item(conn, "確認", "かくにん", meanings=["confirm"])
        imported_id = conn.execute(
            select(item_meanings.c.id).where(item_meanings.c.item_id == item_id)
        ).scalar()

    with engine.begin() as conn:
        with pytest.raises(CannotDeleteImportedMeaningError):
            delete_synonym(conn, item_id, imported_id)

    with engine.connect() as conn:
        rows = conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id)).all()
    assert {r[0] for r in rows} == {"confirm"}  # untouched


def test_delete_synonym_raises_for_unknown_synonym(engine):
    with engine.begin() as conn:
        item_id = _make_item(conn, "確認", "かくにん", meanings=["confirm"])

    with engine.begin() as conn:
        with pytest.raises(SynonymNotFoundError):
            delete_synonym(conn, item_id, 999)


# --- notes ------------------------------------------------------------------------------


def test_update_notes_creates_row_when_none_exists(engine):
    with engine.begin() as conn:
        item_id = _make_item(conn, "確認", "かくにん")

    with engine.begin() as conn:
        result = update_notes(conn, item_id, {"note_text": "hello"})

    assert result == {"note_text": "hello", "mnemonic_text": None}


def test_update_notes_partial_update_preserves_other_field(engine):
    with engine.begin() as conn:
        item_id = _make_item(conn, "確認", "かくにん")

    with engine.begin() as conn:
        update_notes(conn, item_id, {"note_text": "hello", "mnemonic_text": "world"})

    with engine.begin() as conn:
        result = update_notes(conn, item_id, {"note_text": "updated"})

    assert result == {"note_text": "updated", "mnemonic_text": "world"}


def test_update_notes_returns_none_for_unknown_item(engine):
    with engine.begin() as conn:
        assert update_notes(conn, 999, {"note_text": "x"}) is None
