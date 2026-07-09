import unicodedata
from typing import Optional

# Fullwidth katakana block that has a direct one-to-one hiragana equivalent
# (excludes U+30FC prolonged sound mark, U+30FB middle dot, etc., which have none).
_KATAKANA_START = 0x30A1
_KATAKANA_END = 0x30F6
_HIRAGANA_OFFSET = 0x60


def normalize_japanese(text: Optional[str]) -> str:
    """NFKC width-fold only. Keeps kanji/hiragana/katakana distinctions intact,
    since duplicate detection must not treat different written forms as identical."""
    if not text:
        return ""
    return unicodedata.normalize("NFKC", text).strip()


def _katakana_to_hiragana(text: str) -> str:
    chars = []
    for ch in text:
        code = ord(ch)
        if _KATAKANA_START <= code <= _KATAKANA_END:
            chars.append(chr(code - _HIRAGANA_OFFSET))
        else:
            chars.append(ch)
    return "".join(chars)


def normalize_kana(text: Optional[str]) -> str:
    """NFKC width-fold plus katakana->hiragana fold, so kana matching treats
    hiragana and katakana spellings of the same reading as identical."""
    if not text:
        return ""
    nfkc = unicodedata.normalize("NFKC", text).strip()
    return _katakana_to_hiragana(nfkc)


def normalize_meaning(text: Optional[str]) -> str:
    """Storage/dedup key for imported meanings, not the fuller answer-checking
    normalization (punctuation/article-stripping) that a later phase will add."""
    if not text:
        return ""
    return " ".join(text.strip().lower().split())
