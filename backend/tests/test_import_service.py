from sqlalchemy import select

from app.models import item_meanings, source_items, sources, study_progress, vocab_items
from app.services.import_service import run_import
from tests.helpers import write_wordbank


def _row(**overrides):
    row = {
        "item_type": "word",
        "japanese": "確認",
        "kana": "かくにん",
        "romaji": "kakunin",
        "meanings": "confirm; verify",
        "part_of_speech": "noun",
    }
    row.update(overrides)
    return row


def test_new_item_creates_canonical_row_slot_and_progress(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "work.xlsx", [_row()])

    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"new": 1}
    with engine.connect() as conn:
        item = conn.execute(select(vocab_items)).mappings().first()
        assert item["japanese"] == "確認"
        assert item["normalized_kana"] == "かくにん"

        source_item = conn.execute(select(source_items)).mappings().first()
        assert (source_item["source_level"], source_item["level_position"]) == (1, 1)
        assert source_item["is_active"] is True

        progress = conn.execute(select(study_progress)).mappings().first()
        assert progress["srs_stage"] == 0


def test_source_display_name_and_key_derived_from_filename(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "fate_stay_night.xlsx", [_row()])

    run_import(engine, wordbank_dir)

    with engine.connect() as conn:
        source = conn.execute(select(sources)).mappings().first()
        assert source["source_key"] == "fate_stay_night"
        assert source["display_name"] == "Fate Stay Night"


def test_reimport_unchanged_file_is_idempotent(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)

    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"unchanged": 1}
    with engine.connect() as conn:
        assert len(conn.execute(select(vocab_items)).all()) == 1
        assert len(conn.execute(select(source_items)).all()) == 1


def test_changed_meaning_stages_updated_pending_approval_without_overwriting(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [_row(meanings="confirm; verify; double-check")])
    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"updated_pending_approval": 1}
    with engine.connect() as conn:
        meanings = {r[0] for r in conn.execute(select(item_meanings.c.meaning))}
        assert meanings == {"confirm", "verify"}


def test_katakana_kana_edit_is_treated_as_exact_match(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [_row(kana="カクニン")])
    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"unchanged": 1}
    with engine.connect() as conn:
        assert len(conn.execute(select(vocab_items)).all()) == 1


def test_japanese_only_match_is_duplicate_pending_merge(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [_row(kana="べつのかな")])
    result = run_import(engine, wordbank_dir)

    assert result["summary"].get("duplicate_pending_merge") == 1
    with engine.connect() as conn:
        assert len(conn.execute(select(vocab_items)).all()) == 1


def test_kana_only_match_is_duplicate_pending_merge(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [_row(japanese="別の漢字")])
    result = run_import(engine, wordbank_dir)

    assert result["summary"].get("duplicate_pending_merge") == 1
    with engine.connect() as conn:
        assert len(conn.execute(select(vocab_items)).all()) == 1


def test_wholly_new_japanese_and_kana_pair_is_new_item(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [_row(japanese="別の漢字", kana="べつのかな")])
    result = run_import(engine, wordbank_dir)

    # the original row disappeared from work.xlsx in this rewrite, so its
    # source_items association is correctly marked inactive in the same run
    assert result["summary"] == {"new": 1, "inactive": 1}
    with engine.connect() as conn:
        assert len(conn.execute(select(vocab_items)).all()) == 2


def test_same_item_from_second_source_shares_progress(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "work.xlsx", [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(wordbank_dir / "manga.xlsx", [_row()])
    result = run_import(engine, wordbank_dir)

    # work.xlsx is rescanned too on every run, and it's unchanged
    assert result["summary"] == {"added_to_source": 1, "unchanged": 1}
    with engine.connect() as conn:
        assert len(conn.execute(select(vocab_items)).all()) == 1
        source_item_rows = conn.execute(select(source_items)).mappings().all()
        assert len(source_item_rows) == 2
        assert len({r["item_id"] for r in source_item_rows}) == 1
        assert len(conn.execute(select(study_progress)).all()) == 1


def test_added_to_source_with_romaji_conflict_stages_for_approval(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "work.xlsx", [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(wordbank_dir / "manga.xlsx", [_row(romaji="kakunin2")])
    result = run_import(engine, wordbank_dir)

    # work.xlsx is rescanned too on every run, and it's unchanged
    assert result["summary"] == {"updated_pending_approval": 1, "unchanged": 1}
    with engine.connect() as conn:
        # source association is still created despite the field conflict
        assert len(conn.execute(select(source_items)).all()) == 2
        item = conn.execute(select(vocab_items)).mappings().first()
        assert item["romaji"] == "kakunin"


def test_removed_row_marks_source_item_inactive_but_preserves_progress(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row()])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [])
    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"inactive": 1}
    with engine.connect() as conn:
        source_item = conn.execute(select(source_items)).mappings().first()
        assert source_item["is_active"] is False
        assert len(conn.execute(select(vocab_items)).all()) == 1
        assert len(conn.execute(select(study_progress)).all()) == 1


def test_reactivated_row_keeps_original_slot(engine, wordbank_dir):
    path = wordbank_dir / "work.xlsx"
    write_wordbank(path, [_row(), _row(japanese="別の漢字2", kana="べつのかな2")])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [_row(japanese="別の漢字2", kana="べつのかな2")])
    run_import(engine, wordbank_dir)

    write_wordbank(path, [_row(), _row(japanese="別の漢字2", kana="べつのかな2")])
    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"added_to_source": 1, "unchanged": 1}
    with engine.connect() as conn:
        item = conn.execute(
            select(vocab_items).where(vocab_items.c.japanese == "確認")
        ).mappings().first()
        source_item = conn.execute(
            select(source_items).where(source_items.c.item_id == item["id"])
        ).mappings().first()
        assert (source_item["source_level"], source_item["level_position"]) == (1, 1)
        assert source_item["is_active"] is True


def test_level_rolls_over_after_twenty_items(engine, wordbank_dir):
    rows = [_row(japanese=f"item{i}", kana=f"かな{i}") for i in range(21)]
    write_wordbank(wordbank_dir / "work.xlsx", rows)

    run_import(engine, wordbank_dir)

    with engine.connect() as conn:
        slots = {
            (r["source_level"], r["level_position"])
            for r in conn.execute(select(source_items)).mappings().all()
        }
        assert (1, 20) in slots
        assert (2, 1) in slots


def test_invalid_row_does_not_block_valid_rows_in_same_file(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "work.xlsx", [_row(), _row(item_type="bogus")])

    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"new": 1, "error": 1}


def test_missing_items_sheet_logs_file_level_error(engine, wordbank_dir):
    write_wordbank(wordbank_dir / "work.xlsx", [_row()], sheet_name="Vocabulary")

    result = run_import(engine, wordbank_dir)

    assert result["summary"] == {"error": 1}
    with engine.connect() as conn:
        assert len(conn.execute(select(vocab_items)).all()) == 0


def test_no_wordbank_folder_is_a_no_op(engine, tmp_path):
    missing_dir = tmp_path / "does-not-exist"

    result = run_import(engine, missing_dir)

    assert result["summary"] == {}
