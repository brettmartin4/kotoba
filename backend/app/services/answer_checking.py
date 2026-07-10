import re
from typing import Iterable, Literal

from app.services.text_normalization import normalize_japanese, normalize_kana

_ARTICLES = {"a", "an", "the"}
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)

MeaningGrade = Literal["correct", "typo_warning", "incorrect"]

# Conservative typo tolerance (spec 12.2 gives no exact numbers): no tolerance
# below 3 characters (too easy to false-positive on short unrelated words like
# "go"/"no"), then 1 edit for short words and 2 for longer ones.
_MIN_LENGTH_FOR_TYPO_TOLERANCE = 3
_SHORT_WORD_MAX_LENGTH = 6
_SHORT_WORD_ALLOWED_DISTANCE = 1
_LONG_WORD_ALLOWED_DISTANCE = 2


def normalize_meaning_answer(text: str) -> str:
    """Fuller normalization than text_normalization.normalize_meaning: also strips
    punctuation and common articles, per spec 12.1. Used for answer-checking only,
    not for the import-time storage/dedup key."""
    if not text:
        return ""
    lowered = text.strip().lower()
    stripped = _PUNCTUATION_RE.sub("", lowered)
    tokens = [token for token in stripped.split() if token not in _ARTICLES]
    return " ".join(tokens)


def check_meaning_answer(submitted: str, accepted_meanings: Iterable[str]) -> bool:
    normalized_submitted = normalize_meaning_answer(submitted)
    if not normalized_submitted:
        return False
    accepted = {normalize_meaning_answer(meaning) for meaning in accepted_meanings}
    return normalized_submitted in accepted


def check_japanese_answer(
    submitted: str,
    accepted_display_forms: Iterable[str],
    accepted_kana_forms: Iterable[str],
) -> bool:
    """Accepts the display (kanji/kana) form or the kana reading (katakana/hiragana
    folded). Romaji is rejected implicitly: it never appears in either accepted set,
    and coincidental collisions are not possible since the scripts don't overlap."""
    normalized_display = normalize_japanese(submitted)
    normalized_kana = normalize_kana(submitted)
    if not normalized_display and not normalized_kana:
        return False

    display_set = {normalize_japanese(form) for form in accepted_display_forms}
    kana_set = {normalize_kana(form) for form in accepted_kana_forms}
    return normalized_display in display_set or normalized_kana in kana_set


def _levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i]
        for j, char_b in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            substitute_cost = previous_row[j - 1] + (0 if char_a == char_b else 1)
            current_row.append(min(insert_cost, delete_cost, substitute_cost))
        previous_row = current_row
    return previous_row[-1]


def _is_close_meaning(normalized_submitted: str, normalized_accepted: str) -> bool:
    length = max(len(normalized_submitted), len(normalized_accepted))
    if length < _MIN_LENGTH_FOR_TYPO_TOLERANCE:
        return False

    distance = _levenshtein_distance(normalized_submitted, normalized_accepted)
    if distance == 0:
        return False  # exact match is handled separately, not "close"

    allowed = _SHORT_WORD_ALLOWED_DISTANCE if length <= _SHORT_WORD_MAX_LENGTH else _LONG_WORD_ALLOWED_DISTANCE
    return distance <= allowed


def grade_meaning_answer(submitted: str, accepted_meanings: Iterable[str]) -> MeaningGrade:
    """Three-way grade for review meaning prompts (English typo tolerance per spec
    12.2). Lesson quizzes intentionally keep using the strict check_meaning_answer
    above instead of this -- Phase 3 is exact-match-only by design."""
    normalized_submitted = normalize_meaning_answer(submitted)
    if not normalized_submitted:
        return "incorrect"

    normalized_accepted = [normalize_meaning_answer(meaning) for meaning in accepted_meanings]
    if normalized_submitted in normalized_accepted:
        return "correct"

    if any(_is_close_meaning(normalized_submitted, accepted) for accepted in normalized_accepted):
        return "typo_warning"

    return "incorrect"
