"""Sentence segmentation for Arabic, Urdu, and English text.

Splits on sentence terminators common across the three scripts:
  English : . ! ?
  Arabic  : ۔ (U+06D4) ؟ (U+061F) — also the ASCII set above
  Urdu    : same as Arabic plus ASCII

Newlines always break sentences. A small abbreviation guard avoids
splitting after common Latin abbreviations like "e.g." or "St.".
"""

import re

# Terminators that end a sentence in our supported scripts.
_TERMINATORS = ".!?\u06d4\u061f"  # . ! ? ۔ ؟

# Common abbreviations that should not trigger a split.
_ABBREVS = {
    "e.g", "i.e", "etc", "vs", "st", "dr", "mr", "mrs", "ms", "sr", "jr",
    "prof", "gen", "rep", "sen", "vol", "pp", "p",
}

_SPLIT_RE = re.compile(r"(?<=[%s])\s+|\n+" % re.escape(_TERMINATORS))

# Tanzil-style verse-number prefixes ("12|4|...") from downloaded Quran
# text/translation files. Stripped before segmentation so they don't pollute
# embeddings, display, or the number checker with false "dropped number" flags.
_VERSE_PREFIX_RE = re.compile(r"(?m)^\d+\|\d+\|")


def _looks_like_abbrev(text: str, cut: int) -> bool:
    """True if the split point falls right after a known abbreviation."""
    before = text[:cut]
    m = re.search(r"([A-Za-z]{1,4})\.$", before)
    return bool(m and m.group(1).lower() in _ABBREVS)


def segment(text: str) -> list[str]:
    """Split *text* into sentence strings, keeping terminators attached."""
    text = (text or "").strip()
    if not text:
        return []
    # Drop verse-number prefixes so pasted Tanzil-format files behave
    # like clean text (no fake numbers, no embedding noise).
    text = _VERSE_PREFIX_RE.sub("", text)

    parts: list[str] = []
    start = 0
    for m in _SPLIT_RE.finditer(text):
        cut = m.start()
        if _looks_like_abbrev(text, cut):
            continue
        chunk = text[start:cut].strip()
        if chunk:
            parts.append(chunk)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts
