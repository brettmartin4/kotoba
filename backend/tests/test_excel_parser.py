import pytest

from app.services.excel_parser import WordBankFileError, parse_workbook
from tests.helpers import DEFAULT_COLUMNS, write_wordbank


def _valid_row(**overrides):
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
        "source_note": "work example",
    }
    row.update(overrides)
    return row


def test_parses_valid_row(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row()])

    parsed = parse_workbook(path)

    assert not parsed.errors
    assert len(parsed.rows) == 1
    row = parsed.rows[0]
    assert row.meanings == ["confirm", "verify"]
    assert len(row.examples) == 1
    assert row.examples[0].japanese == "確認してください。"
    assert row.source_note == "work example"


def test_missing_items_sheet_raises(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row()], sheet_name="Vocabulary")

    with pytest.raises(WordBankFileError, match="items"):
        parse_workbook(path)


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "work.xlsx"
    columns = [c for c in DEFAULT_COLUMNS if c != "romaji"]
    write_wordbank(path, [_valid_row()], columns=columns)

    with pytest.raises(WordBankFileError, match="romaji"):
        parse_workbook(path)


def test_invalid_item_type_is_row_error(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row(item_type="verb")])

    parsed = parse_workbook(path)

    assert not parsed.rows
    assert len(parsed.errors) == 1
    assert "item_type" in parsed.errors[0].message


def test_empty_meanings_is_row_error(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row(meanings="")])

    parsed = parse_workbook(path)

    assert not parsed.rows
    assert len(parsed.errors) == 1


def test_missing_required_field_is_row_error(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row(kana="")])

    parsed = parse_workbook(path)

    assert not parsed.rows
    assert "kana is required" in parsed.errors[0].message


def test_mismatched_example_counts_is_row_error(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row(example_kana="かくにんしてください。; もうひとつ")])

    parsed = parse_workbook(path)

    assert not parsed.rows
    assert len(parsed.errors) == 1
    assert "example_japanese" in parsed.errors[0].message


def test_no_examples_is_valid(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row(example_japanese="", example_kana="", example_english="")])

    parsed = parse_workbook(path)

    assert not parsed.errors
    assert parsed.rows[0].examples == []


def test_kana_only_item_allows_same_value(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row(japanese="しょうがない", kana="しょうがない")])

    parsed = parse_workbook(path)

    assert not parsed.errors
    assert len(parsed.rows) == 1


def test_valid_and_invalid_rows_both_processed(tmp_path):
    path = tmp_path / "work.xlsx"
    write_wordbank(path, [_valid_row(), _valid_row(japanese="", kana="")])

    parsed = parse_workbook(path)

    assert len(parsed.rows) == 1
    assert len(parsed.errors) == 1
