from app.services.text_normalization import normalize_japanese, normalize_kana, normalize_meaning


def test_normalize_kana_folds_katakana_to_hiragana():
    assert normalize_kana("カクニン") == normalize_kana("かくにん")


def test_normalize_kana_folds_halfwidth_katakana():
    assert normalize_kana("ｶｸﾆﾝ") == normalize_kana("かくにん")


def test_normalize_japanese_preserves_written_form_distinctions():
    assert normalize_japanese("確認") != normalize_japanese("かくにん")
    assert normalize_japanese("確認") != normalize_japanese("カクニン")


def test_normalize_japanese_nfkc_width_folds():
    assert normalize_japanese("Ａ") == normalize_japanese("A")


def test_normalize_meaning_ignores_case_and_whitespace():
    assert normalize_meaning("  Confirm   Now ") == normalize_meaning("confirm now")


def test_normalize_functions_handle_empty_input():
    assert normalize_japanese("") == ""
    assert normalize_kana(None) == ""
    assert normalize_meaning(None) == ""
