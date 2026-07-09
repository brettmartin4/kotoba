import re
from typing import Iterable

from app.services.text_normalization import normalize_japanese, normalize_kana

_ARTICLES = {"a", "an", "the"}
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)


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
