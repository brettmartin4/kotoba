from app.services.answer_checking import (
    check_japanese_answer,
    check_meaning_answer,
    grade_meaning_answer,
    normalize_meaning_answer,
)


def test_normalize_meaning_answer_strips_case_punctuation_and_articles():
    assert normalize_meaning_answer("The Confirm!") == "confirm"
    assert normalize_meaning_answer("a check.") == "check"
    assert normalize_meaning_answer("  Verify   now ") == "verify now"


def test_check_meaning_answer_accepts_any_accepted_meaning():
    accepted = ["confirm", "verify", "check"]
    assert check_meaning_answer("Confirm", accepted) is True
    assert check_meaning_answer("the verify", accepted) is True
    assert check_meaning_answer("wrong answer", accepted) is False


def test_check_meaning_answer_rejects_blank_submission():
    assert check_meaning_answer("   ", ["confirm"]) is False
    assert check_meaning_answer("", ["confirm"]) is False


def test_check_japanese_answer_accepts_display_form():
    assert check_japanese_answer("確認", ["確認"], ["かくにん"]) is True


def test_check_japanese_answer_accepts_kana_form():
    assert check_japanese_answer("かくにん", ["確認"], ["かくにん"]) is True


def test_check_japanese_answer_folds_katakana_to_hiragana():
    assert check_japanese_answer("カクニン", ["確認"], ["かくにん"]) is True


def test_check_japanese_answer_rejects_romaji():
    assert check_japanese_answer("kakunin", ["確認"], ["かくにん"]) is False


def test_check_japanese_answer_rejects_wrong_word():
    assert check_japanese_answer("了解", ["確認"], ["かくにん"]) is False


def test_check_japanese_answer_rejects_blank_submission():
    assert check_japanese_answer("", ["確認"], ["かくにん"]) is False


def test_check_japanese_answer_width_normalizes():
    # fullwidth ASCII in a kana-only item's display form (e.g. numerals) should
    # still match after NFKC folding via normalize_japanese reuse
    assert check_japanese_answer("Ａ", ["Ａ"], ["あ"]) is True
    assert check_japanese_answer("A", ["Ａ"], ["あ"]) is True


def test_grade_meaning_answer_exact_match_is_correct():
    assert grade_meaning_answer("Confirm", ["confirm", "verify"]) == "correct"
    assert grade_meaning_answer("the verify", ["confirm", "verify"]) == "correct"


def test_grade_meaning_answer_rejects_blank_submission():
    assert grade_meaning_answer("", ["confirm"]) == "incorrect"
    assert grade_meaning_answer("   ", ["confirm"]) == "incorrect"


def test_grade_meaning_answer_short_word_one_substitution_is_typo_warning():
    # "check" -> "cheek": single substitution, length 5 (<=6 -> allowed distance 1)
    assert grade_meaning_answer("cheek", ["check"]) == "typo_warning"


def test_grade_meaning_answer_short_word_two_substitutions_is_incorrect():
    # "check" -> "chxxk": two substitutions, length 5 (<=6 -> allowed distance 1, so 2 fails)
    assert grade_meaning_answer("chxxk", ["check"]) == "incorrect"


def test_grade_meaning_answer_long_word_two_edits_is_typo_warning():
    # "beautiful" -> "beautif": two deletions, length 9 (>6 -> allowed distance 2)
    assert grade_meaning_answer("beautif", ["beautiful"]) == "typo_warning"


def test_grade_meaning_answer_long_word_three_edits_is_incorrect():
    # "beautiful" -> "beauti": three deletions, length 9 (>6 -> allowed distance 2, so 3 fails)
    assert grade_meaning_answer("beauti", ["beautiful"]) == "incorrect"


def test_grade_meaning_answer_short_words_get_no_typo_tolerance():
    # "go" vs "no": one substitution but both under the 3-character minimum length
    assert grade_meaning_answer("no", ["go"]) == "incorrect"


def test_grade_meaning_answer_checks_closeness_against_every_accepted_meaning():
    assert grade_meaning_answer("cheek", ["verify", "check"]) == "typo_warning"
