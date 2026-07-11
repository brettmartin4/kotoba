import sqlite3
from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select, update

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
from app.services.import_service import keep_separate_duplicate, merge_duplicate, run_import, skip_duplicate
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
            select(import_run_items)
            .where(import_run_items.c.status == status)
            .order_by(import_run_items.c.id.desc())
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


def _delete_item_leaving_dangling_references(engine, item_id):
    """Simulates an impossible-in-normal-V1-operation 'target vanished' state (V1
    never deletes items) to exercise the defensive fail-safe guard. Deliberately
    leaves source_row_resolutions.resolved_item_id and import_run_items.item_id
    dangling rather than nulling them out, since that's the actual scenario being
    guarded against -- a stale reference to an ID that no longer resolves. SQLite
    enforces foreign keys per-connection and defaults to OFF, so a fresh raw
    connection (bypassing the app's engine, which turns them ON) can construct
    this state directly."""
    raw_conn = sqlite3.connect(str(engine.url.database))
    try:
        raw_conn.execute("DELETE FROM source_items WHERE item_id = ?", (item_id,))
        raw_conn.execute("DELETE FROM examples WHERE item_id = ?", (item_id,))
        raw_conn.execute("DELETE FROM item_meanings WHERE item_id = ?", (item_id,))
        raw_conn.execute("DELETE FROM item_forms WHERE item_id = ?", (item_id,))
        raw_conn.execute("DELETE FROM item_notes WHERE item_id = ?", (item_id,))
        raw_conn.execute("DELETE FROM study_progress WHERE item_id = ?", (item_id,))
        raw_conn.execute("DELETE FROM vocab_items WHERE id = ?", (item_id,))
        raw_conn.commit()
    finally:
        raw_conn.close()


# --- merge stays resolved across reimport --------------------------------------------


def test_merge_then_unchanged_reimport_does_not_restage_and_stays_active(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    merge_duplicate(engine, duplicate_id, target_item_id)

    result = run_import(engine, wordbank_dir)

    assert "duplicate_pending_merge" not in result["summary"]
    assert "inactive" not in result["summary"]

    with engine.connect() as conn:
        memberships = conn.execute(
            select(source_items).where(source_items.c.item_id == target_item_id)
        ).mappings().all()

    assert len(memberships) == 2
    assert all(m["is_active"] for m in memberships)


def test_merge_resolution_preserves_srs_notes_synonyms_and_history_across_reimport(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    merge_duplicate(engine, duplicate_id, target_item_id)

    learned_at = _now_naive() - timedelta(days=3)
    with engine.begin() as conn:
        conn.execute(
            update(study_progress)
            .where(study_progress.c.item_id == target_item_id)
            .values(srs_stage=5, learned_at=learned_at, total_reviews=7, correct_reviews=6, current_correct_streak=2)
        )
        conn.execute(
            insert(item_notes).values(
                item_id=target_item_id, note_text="keep me", mnemonic_text="also keep me", updated_at=_now_naive()
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

    run_import(engine, wordbank_dir)  # unchanged reimport, resolution fast path exercised

    with engine.connect() as conn:
        progress = conn.execute(
            select(study_progress).where(study_progress.c.item_id == target_item_id)
        ).mappings().first()
        note = conn.execute(select(item_notes).where(item_notes.c.item_id == target_item_id)).mappings().first()
        synonym = conn.execute(
            select(item_meanings).where(
                item_meanings.c.item_id == target_item_id, item_meanings.c.origin == "user_synonym"
            )
        ).mappings().first()
        attempt_count = len(
            conn.execute(select(review_attempts).where(review_attempts.c.item_id == target_item_id)).all()
        )

    assert progress["srs_stage"] == 5
    assert progress["learned_at"] == learned_at
    assert progress["total_reviews"] == 7
    assert progress["current_correct_streak"] == 2
    assert note["note_text"] == "keep me"
    assert synonym is not None
    assert attempt_count == 1


# --- keep separate stays resolved across reimport ----------------------------------------


def test_keep_separate_then_unchanged_reimport_does_not_restage_and_stays_active(engine, wordbank_dir):
    _target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    kept = keep_separate_duplicate(engine, duplicate_id)
    kept_item_id = kept["item_id"]

    result = run_import(engine, wordbank_dir)

    assert "duplicate_pending_merge" not in result["summary"]
    assert "inactive" not in result["summary"]

    with engine.connect() as conn:
        membership = conn.execute(
            select(source_items).where(source_items.c.item_id == kept_item_id)
        ).mappings().first()

    assert membership is not None
    assert membership["is_active"] is True


# --- skip stays resolved across reimport -----------------------------------------------


def test_skip_then_unchanged_reimport_does_not_restage_or_create_relationship(engine, wordbank_dir):
    _target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    skip_duplicate(engine, duplicate_id)

    with engine.connect() as conn:
        items_before = len(conn.execute(select(vocab_items)).all())
        memberships_before = len(conn.execute(select(source_items)).all())

    result = run_import(engine, wordbank_dir)

    assert "duplicate_pending_merge" not in result["summary"]
    assert result["summary"].get("skipped") == 1

    with engine.connect() as conn:
        items_after = len(conn.execute(select(vocab_items)).all())
        memberships_after = len(conn.execute(select(source_items)).all())

    assert items_after == items_before  # no new canonical item was created
    assert memberships_after == memberships_before  # no source_items row for the skipped row


def test_skip_resolution_survives_multiple_reimports(engine, wordbank_dir):
    _target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    skip_duplicate(engine, duplicate_id)

    run_import(engine, wordbank_dir)
    third_result = run_import(engine, wordbank_dir)

    assert "duplicate_pending_merge" not in third_result["summary"]
    assert third_result["summary"].get("skipped") == 1


# --- stale/missing resolution target fails safely --------------------------------------


def test_missing_resolution_target_produces_row_level_error(engine, wordbank_dir):
    target_item_id, duplicate_id = _stage_duplicate(engine, wordbank_dir)
    merge_duplicate(engine, duplicate_id, target_item_id)

    _delete_item_leaving_dangling_references(engine, target_item_id)

    result = run_import(engine, wordbank_dir)

    assert result["summary"].get("error") is not None
    assert "duplicate_pending_merge" not in result["summary"]

    error_row = _find_row(engine, "error")
    assert str(target_item_id) in error_row["message"]
