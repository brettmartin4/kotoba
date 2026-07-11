from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, insert, select, update

from app.models import (
    import_run_items,
    item_meanings,
    item_notes,
    review_attempts,
    review_sessions,
    source_items,
    study_progress,
    vocab_items,
)
from app.services.import_service import (
    AlreadyResolvedError,
    ImportRunItemNotFoundError,
    InvalidMergeTargetError,
    ItemNotFoundError,
    SourceRelationshipNotFoundError,
    approve_change,
    get_pending_changes,
    get_pending_duplicates,
    keep_separate_duplicate,
    merge_duplicate,
    reject_change,
    run_import,
    skip_duplicate,
)
from tests.helpers import write_wordbank


def _now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _row(**overrides):
    row = {
        "item_type": "word",
        "japanese": "確認",
        "kana": "かくにん",
        "romaji": "kakunin",
        "meanings": "confirm; verify",
        "part_of_speech": "noun",
        "example_japanese": "確認してください。",
        "example_kana": "かくにんしてください。",
        "example_english": "Please check.",
        "similar_items": "確かめる",
    }
    row.update(overrides)
    return row


def _find_row(engine, status):
    with engine.connect() as conn:
        row = conn.execute(
            select(import_run_items).where(import_run_items.c.status == status).order_by(import_run_items.c.id.desc())
        ).mappings().first()
    return dict(row) if row else None


def _stage_duplicate(engine, wordbank_dir):
    """Import "確認/かくにん" into work.xlsx, then a kana-only match ("別の漢字/かくにん")
    into manga.xlsx, returning (target_item_id, duplicate_import_run_item_id)."""
    write_wordbank(wordbank_dir / "work.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()

    write_wordbank(wordbank_dir / "manga.xlsx", [_row(japanese="別の漢字", meanings="check")])
    run_import(engine, wordbank_dir)
    duplicate_row = _find_row(engine, "duplicate_pending_merge")
    return target_item_id, duplicate_row["id"]


def _stage_change(engine, wordbank_dir):
    """Import a row, then reimport the same source with different romaji/meanings
    so the exact-match reimport stages an updated_pending_approval row."""
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        item_id = conn.execute(select(vocab_items.c.id)).scalar()

    write_wordbank(path, [_row(romaji="kakunin2", meanings="confirm; verify; double-check")])
    run_import(engine, wordbank_dir)
    change_row = _find_row(engine, "updated_pending_approval")
    return item_id, change_row["id"]


# --- merge --------------------------------------------------------------------------


def test_merge_adds_content_and_creates_source_membership_without_touching_display_fields(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)

    result = merge_duplicate(engine, duplicate_id, target_item_id)

    assert result == {"import_run_item_id": duplicate_id, "status": "merged", "item_id": target_item_id}

    with engine.connect() as conn:
        item = conn.execute(select(vocab_items).where(vocab_items.c.id == target_item_id)).mappings().first()
        meanings = {
            r[0] for r in conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == target_item_id))
        }
        all_memberships = conn.execute(
            select(source_items).where(source_items.c.item_id == target_item_id)
        ).mappings().all()

    # display-defining fields untouched by merge
    assert item["japanese"] == "確認"
    assert item["kana"] == "かくにん"
    assert item["romaji"] == "kakunin"
    # new meaning merged in additively, existing ones preserved
    assert meanings == {"confirm", "verify", "check"}
    # merge created a source membership for the second source
    assert len(all_memberships) == 2


def test_merge_reactivates_existing_inactive_source_relationship_without_new_slot(engine, wordbank_dir):
    # First: item exists in manga at some slot, then gets removed (inactive).
    write_wordbank(wordbank_dir / "manga.xlsx", [_row(japanese="確認")])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        item_id = conn.execute(select(vocab_items.c.id)).scalar()
        original_membership = conn.execute(
            select(source_items).where(source_items.c.item_id == item_id)
        ).mappings().first()

    write_wordbank(wordbank_dir / "manga.xlsx", [])  # row disappears -> membership goes inactive
    run_import(engine, wordbank_dir)

    # Now a kana-only match for the same source reappears (simulating a slightly-edited row)
    write_wordbank(wordbank_dir / "manga.xlsx", [_row(japanese="別の漢字")])
    run_import(engine, wordbank_dir)
    duplicate_row = _find_row(engine, "duplicate_pending_merge")

    merge_duplicate(engine, duplicate_row["id"], item_id)

    with engine.connect() as conn:
        memberships = conn.execute(
            select(source_items).where(source_items.c.item_id == item_id)
        ).mappings().all()

    assert len(memberships) == 1  # reactivated in place, not a second row
    assert memberships[0]["is_active"] is True
    assert memberships[0]["source_level"] == original_membership["source_level"]
    assert memberships[0]["level_position"] == original_membership["level_position"]


def test_merge_preserves_srs_progress_history_notes_and_synonyms(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)

    learned_at = _now_naive() - timedelta(days=3)
    next_review_at = _now_naive() + timedelta(hours=4)
    with engine.begin() as conn:
        conn.execute(
            update(study_progress)
            .where(study_progress.c.item_id == target_item_id)
            .values(
                srs_stage=5, learned_at=learned_at, next_review_at=next_review_at,
                total_reviews=10, correct_reviews=8, incorrect_reviews=2, current_correct_streak=3,
            )
        )
        conn.execute(
            insert(item_notes).values(
                item_id=target_item_id, note_text="my note", mnemonic_text="my mnemonic", updated_at=_now_naive()
            )
        )
        conn.execute(
            insert(item_meanings).values(
                item_id=target_item_id, meaning="my synonym", normalized_meaning="my synonym", origin="user_synonym"
            )
        )
        session_id = conn.execute(insert(review_sessions).values(session_type="review")).inserted_primary_key[0]
        conn.execute(
            insert(review_attempts).values(
                session_id=session_id, item_id=target_item_id, prompt_type="meaning",
                submitted_answer="x", normalized_answer="x", is_correct=True, created_at=_now_naive(),
            )
        )

    merge_duplicate(engine, duplicate_id, target_item_id)

    with engine.connect() as conn:
        progress = conn.execute(
            select(study_progress).where(study_progress.c.item_id == target_item_id)
        ).mappings().first()
        note = conn.execute(select(item_notes).where(item_notes.c.item_id == target_item_id)).mappings().first()
        synonym_present = conn.execute(
            select(item_meanings).where(
                item_meanings.c.item_id == target_item_id, item_meanings.c.origin == "user_synonym"
            )
        ).mappings().first()
        attempt_count = len(
            conn.execute(select(review_attempts).where(review_attempts.c.item_id == target_item_id)).all()
        )

    assert progress["srs_stage"] == 5
    assert progress["learned_at"] == learned_at
    assert progress["next_review_at"] == next_review_at
    assert progress["total_reviews"] == 10
    assert progress["correct_reviews"] == 8
    assert progress["current_correct_streak"] == 3
    assert note["note_text"] == "my note"
    assert note["mnemonic_text"] == "my mnemonic"
    assert synonym_present is not None
    assert attempt_count == 1


def test_merge_rejects_target_not_in_candidate_list(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    with pytest.raises(InvalidMergeTargetError):
        merge_duplicate(engine, duplicate_id, target_item_id + 999)


def test_merge_rejects_missing_item(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    # Force an impossible candidate list entry to exercise the defensive item-lookup guard.
    with engine.begin() as conn:
        conn.execute(
            update(import_run_items).where(import_run_items.c.id == duplicate_id).values(
                candidate_item_ids_json=f"[{target_item_id + 999}]"
            )
        )
    with pytest.raises(ItemNotFoundError):
        merge_duplicate(engine, duplicate_id, target_item_id + 999)


def test_merge_rejects_already_resolved(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    merge_duplicate(engine, duplicate_id, target_item_id)
    with pytest.raises(AlreadyResolvedError):
        merge_duplicate(engine, duplicate_id, target_item_id)


def test_merge_raises_for_unknown_import_run_item(engine):
    with pytest.raises(ImportRunItemNotFoundError):
        merge_duplicate(engine, 999, 1)


# --- keep separate --------------------------------------------------------------------


def test_keep_separate_creates_new_item_with_fresh_progress_and_slot(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)

    result = keep_separate_duplicate(engine, duplicate_id)

    new_item_id = result["item_id"]
    assert result["status"] == "kept_separate"
    assert new_item_id != target_item_id

    with engine.connect() as conn:
        new_item = conn.execute(select(vocab_items).where(vocab_items.c.id == new_item_id)).mappings().first()
        progress = conn.execute(select(study_progress).where(study_progress.c.item_id == new_item_id)).mappings().first()
        membership = conn.execute(
            select(source_items).where(source_items.c.item_id == new_item_id)
        ).mappings().first()
        run_item = conn.execute(
            select(import_run_items).where(import_run_items.c.id == duplicate_id)
        ).mappings().first()

    assert new_item["japanese"] == "別の漢字"
    assert progress["srs_stage"] == 0
    assert membership is not None
    assert membership["is_active"] is True
    assert run_item["status"] == "kept_separate"
    assert run_item["item_id"] == new_item_id


def test_keep_separate_rejects_already_resolved(engine, wordbank_dir):
    _target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    keep_separate_duplicate(engine, duplicate_id)
    with pytest.raises(AlreadyResolvedError):
        keep_separate_duplicate(engine, duplicate_id)


# --- skip -------------------------------------------------------------------------------


def test_skip_duplicate_only_changes_status(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)

    with engine.connect() as conn:
        items_before = len(conn.execute(select(vocab_items)).all())
        memberships_before = len(conn.execute(select(source_items)).all())

    result = skip_duplicate(engine, duplicate_id)
    assert result == {"import_run_item_id": duplicate_id, "status": "skipped"}

    with engine.connect() as conn:
        items_after = len(conn.execute(select(vocab_items)).all())
        memberships_after = len(conn.execute(select(source_items)).all())

    assert items_after == items_before
    assert memberships_after == memberships_before


def test_skip_duplicate_rejects_already_resolved(engine, wordbank_dir):
    _target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    skip_duplicate(engine, duplicate_id)
    with pytest.raises(AlreadyResolvedError):
        skip_duplicate(engine, duplicate_id)


# --- approve change -----------------------------------------------------------------------


def test_approve_change_replaces_romaji_and_part_of_speech_when_differ(engine, wordbank_dir):
    item_id, change_id = _stage_change(engine, wordbank_dir)

    result = approve_change(engine, change_id)
    assert result == {"import_run_item_id": change_id, "status": "approved", "item_id": item_id}

    with engine.connect() as conn:
        item = conn.execute(select(vocab_items).where(vocab_items.c.id == item_id)).mappings().first()
    assert item["romaji"] == "kakunin2"


def test_approve_change_adds_meanings_additively_without_removing_existing(engine, wordbank_dir):
    item_id, change_id = _stage_change(engine, wordbank_dir)

    approve_change(engine, change_id)

    with engine.connect() as conn:
        meanings = {r[0] for r in conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id))}
    assert meanings == {"confirm", "verify", "double-check"}


def test_approve_change_preserves_srs_notes_and_synonyms(engine, wordbank_dir):
    item_id, change_id = _stage_change(engine, wordbank_dir)

    with engine.begin() as conn:
        conn.execute(update(study_progress).where(study_progress.c.item_id == item_id).values(srs_stage=4))
        conn.execute(
            insert(item_notes).values(item_id=item_id, note_text="keep me", mnemonic_text=None, updated_at=_now_naive())
        )
        conn.execute(
            insert(item_meanings).values(
                item_id=item_id, meaning="my synonym", normalized_meaning="my synonym", origin="user_synonym"
            )
        )

    approve_change(engine, change_id)

    with engine.connect() as conn:
        progress = conn.execute(select(study_progress.c.srs_stage).where(study_progress.c.item_id == item_id)).scalar()
        note = conn.execute(select(item_notes.c.note_text).where(item_notes.c.item_id == item_id)).scalar()
        synonym = conn.execute(
            select(item_meanings).where(item_meanings.c.item_id == item_id, item_meanings.c.origin == "user_synonym")
        ).mappings().first()

    assert progress == 4
    assert note == "keep me"
    assert synonym is not None


def test_approve_change_updates_source_note_when_different(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row(source_note="original note")])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        item_id = conn.execute(select(vocab_items.c.id)).scalar()

    write_wordbank(path, [_row(source_note="updated note")])
    run_import(engine, wordbank_dir)
    change_row = _find_row(engine, "updated_pending_approval")

    approve_change(engine, change_row["id"])

    with engine.connect() as conn:
        note = conn.execute(
            select(source_items.c.source_note).where(source_items.c.item_id == item_id)
        ).scalar()
    assert note == "updated note"


def test_approve_change_fails_safely_when_source_relationship_missing(engine, wordbank_dir):
    item_id, change_id = _stage_change(engine, wordbank_dir)

    # Simulate the relationship having disappeared since the row was staged.
    with engine.begin() as conn:
        conn.execute(delete(source_items).where(source_items.c.item_id == item_id))

    with pytest.raises(SourceRelationshipNotFoundError):
        approve_change(engine, change_id)

    with engine.connect() as conn:
        item = conn.execute(select(vocab_items).where(vocab_items.c.id == item_id)).mappings().first()
        run_item = conn.execute(
            select(import_run_items.c.status).where(import_run_items.c.id == change_id)
        ).scalar()

    assert item["romaji"] == "kakunin"  # unchanged -- failed safely, nothing applied
    assert run_item == "updated_pending_approval"  # still pending, not silently resolved


def test_approve_change_rejects_already_resolved(engine, wordbank_dir):
    _item_id, change_id = _stage_change(engine, wordbank_dir)
    approve_change(engine, change_id)
    with pytest.raises(AlreadyResolvedError):
        approve_change(engine, change_id)


def test_approve_change_raises_for_unknown_import_run_item(engine):
    with pytest.raises(ImportRunItemNotFoundError):
        approve_change(engine, 999)


# --- reject change --------------------------------------------------------------------------


def test_reject_change_only_changes_status(engine, wordbank_dir):
    item_id, change_id = _stage_change(engine, wordbank_dir)

    result = reject_change(engine, change_id)
    assert result == {"import_run_item_id": change_id, "status": "skipped"}

    with engine.connect() as conn:
        item = conn.execute(select(vocab_items).where(vocab_items.c.id == item_id)).mappings().first()
        meanings = {r[0] for r in conn.execute(select(item_meanings.c.meaning).where(item_meanings.c.item_id == item_id))}

    assert item["romaji"] == "kakunin"
    assert meanings == {"confirm", "verify"}


def test_reject_change_rejects_already_resolved(engine, wordbank_dir):
    _item_id, change_id = _stage_change(engine, wordbank_dir)
    reject_change(engine, change_id)
    with pytest.raises(AlreadyResolvedError):
        reject_change(engine, change_id)


# --- pending queues -----------------------------------------------------------------------------


def test_get_pending_duplicates_includes_candidate_detail_and_excludes_resolved(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)

    pending = get_pending_duplicates(engine)
    assert len(pending) == 1
    assert pending[0]["id"] == duplicate_id
    assert pending[0]["source_display_name"] == "Manga"
    assert [c["item_id"] for c in pending[0]["candidates"]] == [target_item_id]

    merge_duplicate(engine, duplicate_id, target_item_id)

    assert get_pending_duplicates(engine) == []


def test_get_pending_changes_includes_current_item_and_excludes_resolved(engine, wordbank_dir):
    item_id, change_id = _stage_change(engine, wordbank_dir)

    pending = get_pending_changes(engine)
    assert len(pending) == 1
    assert pending[0]["id"] == change_id
    assert pending[0]["current_item"]["item_id"] == item_id
    assert pending[0]["raw_data"]["romaji"] == "kakunin2"

    reject_change(engine, change_id)

    assert get_pending_changes(engine) == []
