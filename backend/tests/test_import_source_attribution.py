"""Phase 5D: exact-match reimport diffing must be scoped to what a specific source
previously contributed, not to everything any source ever added to a shared
canonical item. Before this fix, merging Source B's extra meaning into a
canonical item made Source A's unchanged reimport look "changed" forever."""

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
from app.services.import_service import merge_duplicate, run_import
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


def _latest_row_for_source_key(engine, source_key):
    """Looks up the most recent import_run_items row for a given source (by
    filename stem), independent of what other sources' files in the same
    wordbank folder are doing on the same run_import() call. Needed because
    run_import() rescans every .xlsx in the folder each time (openpyxl's
    read_only workbook handle from excel_parser.py is never explicitly closed,
    so on Windows the file can't be deleted/renamed between reimports either --
    filtering by source is the robust way to isolate one source's own row)."""
    from app.models import sources as sources_table

    with engine.connect() as conn:
        source_id = conn.execute(
            select(sources_table.c.id).where(sources_table.c.source_key == source_key)
        ).scalar()
        if source_id is None:
            return None
        row = conn.execute(
            select(import_run_items)
            .where(import_run_items.c.source_id == source_id)
            .order_by(import_run_items.c.id.desc())
        ).mappings().first()
    return dict(row) if row else None


def _stage_and_merge_source_b_extra_meaning(engine, wordbank_dir, target_item_id):
    """Imports a kana-only-matching row from source_b.xlsx that adds a brand-new
    meaning ("double-check") not present on Source A's row, then merges it into
    the Source A canonical item -- reproducing the originally reported scenario."""
    write_wordbank(wordbank_dir / "source_b.xlsx", [_row(japanese="別の漢字", meanings="double-check")])
    run_import(engine, wordbank_dir)
    duplicate_row = _find_row(engine, "duplicate_pending_merge")
    merge_duplicate(engine, duplicate_row["id"], target_item_id)


def test_scenario_1_to_4_reimport_unaffected_by_other_source_merge(engine, wordbank_dir):
    # 1. Import Source A exact item.
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()

    # 2. Import/merge Source B partial duplicate that adds an additional meaning.
    _stage_and_merge_source_b_extra_meaning(engine, wordbank_dir, target_item_id)
    with engine.connect() as conn:
        meanings_after_merge = {
            r[0] for r in conn.execute(select(item_meanings.c.normalized_meaning).where(item_meanings.c.item_id == target_item_id))
        }
    assert "double-check" in meanings_after_merge  # merge actually added it

    # 3. Reimport Source A unchanged.
    run_import(engine, wordbank_dir)

    # 4. Confirm no new updated_pending_approval is created merely because Source B
    # contributed extra meanings.
    source_a_row = _latest_row_for_source_key(engine, "source_a")
    assert source_a_row["status"] == "unchanged"

    # Reimporting again (a second time) must also stay clean -- proves this isn't
    # a one-shot backfill fluke but a stable, source-scoped comparison.
    run_import(engine, wordbank_dir)
    source_a_row_again = _latest_row_for_source_key(engine, "source_a")
    assert source_a_row_again["status"] == "unchanged"


def test_scenario_5_real_change_in_own_source_still_flags_for_approval(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()

    _stage_and_merge_source_b_extra_meaning(engine, wordbank_dir, target_item_id)
    run_import(engine, wordbank_dir)  # settle to a clean baseline first

    # Real change in Source A's own romaji.
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row(romaji="kakunin2")])
    run_import(engine, wordbank_dir)
    pending = _latest_row_for_source_key(engine, "source_a")
    assert pending["status"] == "updated_pending_approval"
    assert "romaji" in pending["message"]

    # Approve so the stored romaji matches, then make a real part_of_speech change.
    from app.services.import_service import approve_change

    approve_change(engine, pending["id"])
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row(romaji="kakunin2", part_of_speech="verb")])
    run_import(engine, wordbank_dir)
    pending2 = _latest_row_for_source_key(engine, "source_a")
    assert pending2["status"] == "updated_pending_approval"
    assert "part_of_speech" in pending2["message"]


def test_scenario_6_additive_change_in_own_source_row_flags_for_approval(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()

    _stage_and_merge_source_b_extra_meaning(engine, wordbank_dir, target_item_id)
    run_import(engine, wordbank_dir)  # settle to a clean baseline first

    # Source A's own row now adds a meaning it did not previously contribute.
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row(meanings="confirm; verify; double check")])
    run_import(engine, wordbank_dir)

    pending = _latest_row_for_source_key(engine, "source_a")
    assert pending["status"] == "updated_pending_approval"
    assert "meanings" in pending["message"]
    # Existing content must not have been deleted while pending.
    with engine.connect() as conn:
        meanings = {
            r[0] for r in conn.execute(select(item_meanings.c.normalized_meaning).where(item_meanings.c.item_id == target_item_id))
        }
    assert "confirm" in meanings
    assert "verify" in meanings


def test_scenario_7_user_synonyms_never_cause_update_pending_loop(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()
        conn.execute(
            insert(item_meanings).values(
                item_id=target_item_id,
                meaning="user added synonym",
                normalized_meaning="user added synonym",
                origin="user_synonym",
            )
        )
        conn.commit()

    run_import(engine, wordbank_dir)
    assert _latest_row_for_source_key(engine, "source_a")["status"] == "unchanged"

    run_import(engine, wordbank_dir)
    assert _latest_row_for_source_key(engine, "source_a")["status"] == "unchanged"

    with engine.connect() as conn:
        synonym = conn.execute(
            select(item_meanings).where(
                item_meanings.c.item_id == target_item_id, item_meanings.c.origin == "user_synonym"
            )
        ).mappings().first()
    assert synonym is not None
    assert synonym["meaning"] == "user added synonym"


def test_scenario_8_notes_mnemonics_srs_history_memberships_untouched(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()

    _stage_and_merge_source_b_extra_meaning(engine, wordbank_dir, target_item_id)

    learned_at = _now_naive() - timedelta(days=2)
    with engine.begin() as conn:
        conn.execute(
            update(study_progress)
            .where(study_progress.c.item_id == target_item_id)
            .values(srs_stage=4, learned_at=learned_at, total_reviews=3, correct_reviews=2, current_correct_streak=1)
        )
        conn.execute(
            insert(item_notes).values(
                item_id=target_item_id, note_text="my note", mnemonic_text="my mnemonic", updated_at=_now_naive()
            )
        )
        session_id = conn.execute(insert(review_sessions).values(session_type="review")).inserted_primary_key[0]
        conn.execute(
            insert(review_attempts).values(
                session_id=session_id, item_id=target_item_id, prompt_type="meaning",
                submitted_answer="confirm", normalized_answer="confirm", is_correct=True, created_at=_now_naive(),
            )
        )

    run_import(engine, wordbank_dir)  # unchanged reimport of Source A

    with engine.connect() as conn:
        progress = conn.execute(
            select(study_progress).where(study_progress.c.item_id == target_item_id)
        ).mappings().first()
        note = conn.execute(select(item_notes).where(item_notes.c.item_id == target_item_id)).mappings().first()
        attempt_count = len(
            conn.execute(select(review_attempts).where(review_attempts.c.item_id == target_item_id)).all()
        )
        memberships = conn.execute(
            select(source_items).where(source_items.c.item_id == target_item_id)
        ).mappings().all()

    assert progress["srs_stage"] == 4
    assert progress["learned_at"] == learned_at
    assert progress["total_reviews"] == 3
    assert progress["current_correct_streak"] == 1
    assert note["note_text"] == "my note"
    assert note["mnemonic_text"] == "my mnemonic"
    assert attempt_count == 1
    assert len(memberships) == 2
    assert all(m["is_active"] for m in memberships)
    # Source A's unchanged reimport must not re-insert its own example.
    source_a_row = _latest_row_for_source_key(engine, "source_a")
    assert source_a_row["status"] == "unchanged"


def test_pre_attribution_relationship_backfills_silently_without_false_positive(engine, wordbank_dir):
    """A source_items relationship that predates attribution tracking (no rows in
    item_meaning_sources/similar_item_sources for that source yet) must not be
    treated as "everything is new" -- it should backfill quietly on first reimport,
    with no updated_pending_approval and no data loss."""
    write_wordbank(wordbank_dir / "source_a.xlsx", [_row()])
    run_import(engine, wordbank_dir)
    with engine.connect() as conn:
        target_item_id = conn.execute(select(vocab_items.c.id)).scalar()

    from app.models import item_meaning_sources, similar_item_sources

    with engine.begin() as conn:
        conn.execute(item_meaning_sources.delete())
        conn.execute(similar_item_sources.delete())

    result = run_import(engine, wordbank_dir)
    assert result["summary"].get("updated_pending_approval") is None
    assert result["summary"].get("unchanged") == 1

    with engine.connect() as conn:
        source_id = conn.execute(select(source_items.c.source_id).where(source_items.c.item_id == target_item_id)).scalar()
        linked = conn.execute(
            select(item_meaning_sources.c.id)
            .select_from(item_meaning_sources.join(item_meanings, item_meanings.c.id == item_meaning_sources.c.item_meaning_id))
            .where(item_meanings.c.item_id == target_item_id, item_meaning_sources.c.source_id == source_id)
        ).all()
    assert len(linked) > 0  # backfilled

    # And a subsequent reimport stays clean too, now that attribution exists.
    result_again = run_import(engine, wordbank_dir)
    assert result_again["summary"].get("updated_pending_approval") is None
    assert result_again["summary"].get("unchanged") == 1
