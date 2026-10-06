"""The four RajiAI rule checkers: NEGATION, NUMBERS, NAMES, REFERENCES.

HARD SAFETY RULE (enforced by code review, not just convention):
checkers may only report *what changed* between the source and draft
spans, with evidence. They must NEVER emit correctness verdicts such as
"correct", "incorrect", "wrong", "mistranslated", or "accurate".

Each checker takes an aligned (source_sentence, draft_sentence) pair and
returns a list of flag dicts (id/type/severity/spans/evidence/status).
"""

import re
from collections import Counter

# ---------------------------------------------------------------------------
# Shared text utilities
# ---------------------------------------------------------------------------

# Arabic-Indic digits ٠١٢٣٤٥٦٧٨٩ (U+0660-U+0669)
_ARABIC_INDIC = {chr(0x0660 + i): str(i) for i in range(10)}
# Extended Arabic-Indic / Persian digits ۰۱۲۳۴۵۶۷۸۹ (U+06F0-U+06F9)
_EXT_ARABIC_INDIC = {chr(0x06F0 + i): str(i) for i in range(10)}
_DIGIT_MAP = {**_ARABIC_INDIC, **_EXT_ARABIC_INDIC}

# Arabic diacritics (tashkeel) stripped before token comparison.
_TASHKEEL_RE = re.compile(r"[\u064b-\u065f\u0670]")

# Small stopword lists so the name checker only considers distinctive tokens.
_STOPWORDS = {
    # English
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "is", "are",
    "was", "were", "it", "he", "she", "they", "his", "her", "their",
    "this", "that", "with", "by", "for", "as", "at", "from", "be",
    # Arabic
    "من", "في", "على", "إلى", "أن", "إن", "هذا", "هذه", "الذي", "التي",
    "هو", "هي", "ما", "لا", "و", "ثم", "قد", "كل", "بين",
    # Urdu
    "کا", "کی", "کے", "کو", "سے", "نے", "میں", "پر", "اور", "یہ", "وہ",
    "ہے", "ہیں", "تھا", "تھی", "جو", "جس",
}


def normalize_digits(text: str) -> str:
    """Map Arabic-Indic and Extended Arabic-Indic digits to ASCII 0-9."""
    return "".join(_DIGIT_MAP.get(ch, ch) for ch in text)


def strip_diacritics(text: str) -> str:
    return _TASHKEEL_RE.sub("", text)


def tokenize(text: str) -> list[str]:
    """Rough word tokens across Latin/Arabic scripts."""
    return re.findall(r"[\w\u0600-\u06ff]+", text, flags=re.UNICODE)


def _is_arabic_script(token: str) -> bool:
    return any("\u0600" <= ch <= "\u06ff" for ch in token)


# ---------------------------------------------------------------------------
# 1. NEGATION
# ---------------------------------------------------------------------------

_NEGATION_MARKERS = {
    "en": ["not", "n't", "cannot", "no", "never", "neither", "nor", "none",
           "nobody", "nothing", "nowhere", "without"],
    "ar": ["لا", "لم", "لن", "ليس", "ليست", "ليسوا", "لست", "لسنا",
           "غير"],
    "ur": ["نہ", "نہیں", "نا", "مت"],
}

# Note: "n't" is handled separately below — a leading \b would never match
# inside contractions ("doesn't", "don't"), since 'n' follows a word char.
_EN_NEG_RE = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in _NEGATION_MARKERS["en"] if m != "n't") + r")\b"
    r"|\w+n't\b",
    flags=re.IGNORECASE,
)


def _strip_wa_prefix(tok: str) -> str:
    """Strip a leading Arabic conjunction wa- (و) before marker matching.

    In Arabic script the conjunction attaches to the following word
    (ولم، ولا، وغير), so without this the negation checker undercounts
    markers in exactly the religious texts RajiAI targets.
    """
    if len(tok) > 1 and tok[0] == "و":
        return tok[1:]
    return tok


def _find_negations(text: str) -> list[str]:
    """Return the negation markers found in *text* (any supported language).

    Counts every occurrence (not just distinct marker types): "لم يلد ولم يولد"
    yields two markers. English markers come from regex matches; Arabic/Urdu
    markers are matched per token, allowing a leading wa- (و) conjunction.

    "إن" and "ما" are NOT standalone negations — إن is emphasis ("indeed")
    or conditional ("if"), ما is often a relative pronoun ("what/which").
    They count only inside the إلا construction ("إن ... إلا" / "ما ... إلا"
    = "nothing but" / "not ... except"), which is a genuine negation.
    """
    found: list[str] = []
    found.extend(m.group(0) for m in _EN_NEG_RE.finditer(text))
    markers = set()
    for lang in ("ar", "ur"):
        markers.update(_NEGATION_MARKERS[lang])
    toks = [strip_diacritics(t) for t in tokenize(text)]
    normed = [_strip_wa_prefix(t) for t in toks]
    for tok in normed:
        if tok in markers:
            found.append(tok)
    # إلا-constructions: one negation per إن/ما that precedes an إلا.
    for idx, tok in enumerate(normed):
        if tok in ("إن", "ما") and "إلا" in normed[idx + 1:]:
            found.append(tok + "...إلا")
    return found


def check_negation(src: str, draft: str) -> list[dict]:
    src_marks = _find_negations(src)
    draft_marks = _find_negations(draft)
    if len(src_marks) == len(draft_marks):
        return []
    if len(draft_marks) < len(src_marks):
        severity = "high"
        evidence = (
            f"Source contains {len(src_marks)} negation marker(s) "
            f"({', '.join(repr(m) for m in src_marks)}); draft contains "
            f"{len(draft_marks)}. A negation present in the source is "
            "missing from the draft, which can reverse the meaning. "
            "Reviewer to decide."
        )
    else:
        severity = "medium"
        evidence = (
            f"Draft contains {len(draft_marks)} negation marker(s) "
            f"({', '.join(repr(m) for m in draft_marks)}); source contains "
            f"{len(src_marks)}. A negation appears in the draft that is not "
            "in the source. Reviewer to decide."
        )
    return [{
        "type": "negation",
        "severity": severity,
        "source_span": src_marks[0] if src_marks else src,
        "draft_span": draft_marks[0] if draft_marks else draft,
        "evidence": evidence,
    }]


# ---------------------------------------------------------------------------
# 2. NUMBERS
# ---------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"\d+")


def _extract_numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(normalize_digits(text))


def check_numbers(src: str, draft: str) -> list[dict]:
    # Verse references (2:255) are owned by the reference checker —
    # blank them so the same change isn't reported twice.
    src_cmp, draft_cmp = _VERSE_RE.sub(" ", src), _VERSE_RE.sub(" ", draft)
    src_nums = _extract_numbers(src_cmp)
    draft_nums = _extract_numbers(draft_cmp)
    if Counter(src_nums) == Counter(draft_nums):
        return []
    flags: list[dict] = []
    src_c, draft_c = Counter(src_nums), Counter(draft_nums)
    # Changed values (same multiset size, different values)
    if len(src_nums) == len(draft_nums) and src_nums != draft_nums:
        flags.append({
            "type": "numbers",
            "severity": "high",
            "source_span": src_nums[0],
            "draft_span": draft_nums[0],
            "evidence": (
                f"Numeric value differs: source has "
                f"{', '.join(src_nums)}; draft has {', '.join(draft_nums)}. "
                "Reviewer to decide."
            ),
        })
        return flags
    # Dropped / added numbers
    for num, count in (src_c - draft_c).items():
        flags.append({
            "type": "numbers",
            "severity": "medium",
            "source_span": num,
            "draft_span": "",
            "evidence": (
                f"Number '{num}' appears {count} time(s) in the source but "
                "is missing from the draft. Reviewer to decide."
            ),
        })
    for num, count in (draft_c - src_c).items():
        flags.append({
            "type": "numbers",
            "severity": "medium",
            "source_span": "",
            "draft_span": num,
            "evidence": (
                f"Number '{num}' appears {count} time(s) in the draft but "
                "not in the source. Reviewer to decide."
            ),
        })
    return flags


# ---------------------------------------------------------------------------
# 3. NAMES (heuristic, conservative)
# ---------------------------------------------------------------------------

_LATIN_NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")


# Pronouns are capitalized mid-sentence in religious English ("Him", "His")
# but are not names; sentence-initial capitalized words are ambiguous, so
# the heuristic conservatively skips them too.
_PRONOUNS = {
    "he", "him", "his", "she", "her", "hers", "they", "them", "their",
    "theirs", "it", "its", "we", "us", "our", "ours", "you", "your",
    "yours", "i", "me", "my", "mine",
}


def _latin_names(text: str) -> set[str]:
    names = set()
    tokens = tokenize(text)
    for pos, tok in enumerate(tokens):
        if not _LATIN_NAME_RE.fullmatch(tok):
            continue
        if pos == 0:
            continue  # sentence-initial: too ambiguous
        low = tok.lower()
        if low in _STOPWORDS or low in _PRONOUNS:
            continue
        names.add(low)
    return names


def _dominant_script(text: str) -> str:
    """'latin', 'arabic', or 'other' by letter count.

    Token-overlap name comparison is only meaningful within one script
    family: without a transliteration lexicon, "Allah" can never match "الله"
    as strings, so cross-script comparison is pure noise.
    """
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return "other"
    latin = sum(1 for ch in letters if "a" <= ch.lower() <= "z")
    arabic = sum(1 for ch in letters if "\u0600" <= ch <= "\u06ff")
    if latin / len(letters) > 0.5:
        return "latin"
    if arabic / len(letters) > 0.5:
        return "arabic"
    return "other"


# Urdu/Arabic orthographic variants normalized before name comparison,
# so اللہ matches الله and رضی matches رضي. (Hamza forms → bare alef is
# standard Arabic NLP normalization.)
_ORTHO_MAP = {
    "ی": "ي", "ے": "ي",
    "ک": "ك",
    "ہ": "ه", "ھ": "ه", "ة": "ه",
    "أ": "ا", "إ": "ا", "آ": "ا",
}


def _normalize_ortho(token: str) -> str:
    return "".join(_ORTHO_MAP.get(ch, ch) for ch in token)


# Stopwords in normalized orthography: Urdu stopwords are stored in Urdu
# spelling (ہے، کی), so they must be normalized too before comparison.
_STOPWORDS_AR_NORM = {_normalize_ortho(w) for w in _STOPWORDS}


def _script_names(text: str) -> set[str]:
    """Candidate distinctive tokens in Arabic/Urdu script."""
    names = set()
    for tok in tokenize(text):
        if not _is_arabic_script(tok):
            continue
        norm = _normalize_ortho(strip_diacritics(tok))
        if len(norm) < 3:
            continue
        if norm in _STOPWORDS or norm in _STOPWORDS_AR_NORM:
            continue
        if normalize_digits(norm).isdigit():
            continue
        names.add(norm)
    return names


def _blank_references(text: str) -> str:
    """Replace reference substrings with spaces so the name checker does not
    double-report tokens that the reference checker already claims
    (e.g. 'Muslim' in 'Sahih Muslim')."""
    for pattern in (_VERSE_RE, _COLLECTION_RE, _PAGEVOL_RE, _SURAH_RE):
        text = pattern.sub(" ", text)
    return text


def _distinctive_tokens(text: str) -> set[str]:
    return _latin_names(_blank_references(text)) | _script_names(_blank_references(text))


def _is_latin_pair(src: str, draft: str) -> bool:
    """True when both sides are predominantly Latin script.

    The dropped-term coverage below only runs for same-language Latin
    pairs: across scripts/languages, raw token overlap is meaningless, and
    the aligner already routes uncertain cross-lingual pairs to the
    unchecked queue instead of force-matching them.
    """
    def latin_ratio(t: str) -> float:
        letters = [ch for ch in t if ch.isalpha()]
        if not letters:
            return 0.0
        latin = sum(1 for ch in letters if "a" <= ch.lower() <= "z")
        return latin / len(letters)

    return latin_ratio(src) > 0.5 and latin_ratio(draft) > 0.5


def _latin_content_terms(text: str) -> set[str]:
    """Distinctive lowercase content words in a Latin-script text.

    Catches dropped ordinary words that the capitalized-name heuristic
    misses — it skips sentence-initial tokens, so a dropped "Say"
    (as in "Say, O Prophet…", Qur'an 112:1) would otherwise go unnoticed.
    Conservative: stopwords, pronouns, short tokens, negation markers,
    numbers, and reference parts are excluded.
    """
    neg_markers = {m.lower() for m in _NEGATION_MARKERS["en"]}
    terms = set()
    for tok in tokenize(_blank_references(text)):
        low = tok.lower()
        if len(low) < 3 or not low.isalpha():
            continue
        if low in _STOPWORDS or low in _PRONOUNS or low in neg_markers:
            continue
        if normalize_digits(low).isdigit():
            continue
        terms.add(low)
    return terms


def check_names(
    src: str,
    draft: str,
    source_lang: str | None = None,
    draft_lang: str | None = None,
) -> list[dict]:
    """Names / key terms are only comparable within one language.

    When the pair's languages are known and differ, the checker stays silent:
    without a transliteration lexicon, token overlap across languages is
    meaningless (verbs like يلد would be reported as "dropped names").
    When languages are unknown, fall back to the same-script heuristic.
    Cross-language name verification is a documented limitation.
    """
    if source_lang and draft_lang:
        if source_lang.strip().lower() != draft_lang.strip().lower():
            return []
    elif _dominant_script(src) != _dominant_script(draft):
        # Cross-script pairs (e.g. Arabic → English): without a
        # transliteration lexicon, "Allah" can never match "الله" as
        # strings, so comparing would flag every pair.
        return []
    src_names = _distinctive_tokens(src)
    draft_names = _distinctive_tokens(draft)
    missing = sorted(src_names - draft_names)
    flags: list[dict] = []
    if missing:
        shown = ", ".join(repr(m) for m in missing[:5])
        if len(missing) > 5:
            shown += f", … (+{len(missing) - 5} more)"
        flags.append({
            "type": "names",
            "severity": "medium",
            "source_span": missing[0],
            "draft_span": "",
            "evidence": (
                f"Distinctive token(s) present in the source but absent from "
                f"the draft: {shown}. This may be a dropped name or key term. "
                "Reviewer to decide."
            ),
        })
    # Dropped ordinary key terms (same-language Latin pairs only).
    if _is_latin_pair(src, draft):
        src_terms = _latin_content_terms(src) - src_names
        draft_terms = _latin_content_terms(draft)
        missing_terms = sorted(src_terms - draft_terms)
        if missing_terms:
            shown = ", ".join(repr(m) for m in missing_terms[:5])
            if len(missing_terms) > 5:
                shown += f", … (+{len(missing_terms) - 5} more)"
            flags.append({
                "type": "names",
                "severity": "low",
                "source_span": missing_terms[0],
                "draft_span": "",
                "evidence": (
                    f"Content word(s) present in the source but absent from "
                    f"the draft: {shown}. This may be a dropped key term "
                    "(the name check only tracks capitalized terms). "
                    "Reviewer to decide."
                ),
            })
    return flags


# ---------------------------------------------------------------------------
# 4. REFERENCES
# ---------------------------------------------------------------------------

# Verse refs like 2:255 (also Arabic-Indic digits ٢:٢٥٥) and "Quran 2:255".
_VERSE_RE = re.compile(r"(?<![\w:])([0-9\u0660-\u0669\u06f0-\u06f9]{1,3}\s*[:\u02d0]\s*[0-9\u0660-\u0669\u06f0-\u06f9]{1,3})(?![\w:])")
# Hadith collections and related markers.
_COLLECTIONS = [
    "bukhari", "muslim", "tirmidhi", "abudawud", "abu dawud", "nasai",
    "nasa'i", "ibn majah", "muwatta", "riyad", "sahih",
    "البخاري", "مسلم", "الترمذي", "أبو داود", "ابو داود", "النسائي",
    "ابن ماجه", "الموطأ", "رواه", "متفق عليه",
]
_COLLECTION_RE = re.compile(
    "|".join(re.escape(c) for c in sorted(_COLLECTIONS, key=len, reverse=True)),
    flags=re.IGNORECASE,
)
# Page / volume markers: p. 12, pp. 3-4, vol. 2, Volume 1, ص ٥, ج ٢
_PAGEVOL_RE = re.compile(
    r"\b(?:pp?|vol(?:ume)?)\.?\s*\d+|\bص\s*[0-9\u0660-\u0669\u06f0-\u06f9]+|\bج\s*[0-9\u0660-\u0669\u06f0-\u06f9]+",
    flags=re.IGNORECASE,
)
# Surah mentions like "Surah Al-Baqarah" / "سورۃ البقرۃ".
_SURAH_RE = re.compile(
    r"\b[sS]urah\s+[A-Za-z'\- ]+|سور[ۃة]\s+[\u0600-\u06ff ]+",
)


def _extract_references(text: str) -> set[str]:
    refs = set()
    norm = normalize_digits(text)
    for m in _VERSE_RE.finditer(norm):
        refs.add("verse:" + re.sub(r"\s+", "", m.group(1)))
    for m in _COLLECTION_RE.finditer(strip_diacritics(text)):
        refs.add("collection:" + m.group(0).lower())
    for m in _PAGEVOL_RE.finditer(norm):
        refs.add("pagevol:" + re.sub(r"\s+", " ", m.group(0)).strip().lower())
    for m in _SURAH_RE.finditer(text):
        refs.add("surah:" + m.group(0).strip().lower())
    return refs


def check_references(src: str, draft: str) -> list[dict]:
    src_refs = _extract_references(src)
    draft_refs = _extract_references(draft)
    if src_refs == draft_refs:
        return []
    flags: list[dict] = []
    # Altered: a verse ref whose chapter:verse value changed.
    src_verses = {r.split(":", 1)[1] for r in src_refs if r.startswith("verse:")}
    draft_verses = {r.split(":", 1)[1] for r in draft_refs if r.startswith("verse:")}
    if src_verses and draft_verses and src_verses != draft_verses:
        flags.append({
            "type": "references",
            "severity": "high",
            "source_span": sorted(src_verses)[0],
            "draft_span": sorted(draft_verses)[0],
            "evidence": (
                f"Verse reference differs: source cites "
                f"{', '.join(sorted(src_verses))}; draft cites "
                f"{', '.join(sorted(draft_verses))}. Reviewer to decide."
            ),
        })
    remaining_src = src_refs - draft_refs
    # Don't double-report the altered verse refs.
    remaining_src = {r for r in remaining_src
                     if not (r.startswith("verse:") and flags)}
    for ref in sorted(remaining_src):
        kind, _, value = ref.partition(":")
        flags.append({
            "type": "references",
            "severity": "medium",
            "source_span": value,
            "draft_span": "",
            "evidence": (
                f"Reference '{value}' ({kind}) appears in the source but "
                "is missing from the draft. Reviewer to decide."
            ),
        })
    return flags


# ---------------------------------------------------------------------------
# Orchestration over the four checkers
# ---------------------------------------------------------------------------

CHECKERS = (
    ("negation", check_negation),
    ("numbers", check_numbers),
    ("names", check_names),
    ("references", check_references),
)

_FORBIDDEN_VERDICT_WORDS = (
    "correct", "incorrect", "wrong", "mistranslated", "accurate",
    "inaccurate", "right", "false translation",
)


def run_checkers(
    src: str,
    draft: str,
    source_lang: str | None = None,
    draft_lang: str | None = None,
) -> list[dict]:
    """Run all four checkers on an aligned pair; returns flag dicts."""
    flags: list[dict] = []
    for name, checker in CHECKERS:
        if name == "names":
            pair_flags = check_names(src, draft, source_lang, draft_lang)
        else:
            pair_flags = checker(src, draft)
        for flag in pair_flags:
            evidence = flag["evidence"]
            lowered = evidence.lower()
            assert not any(w in lowered for w in _FORBIDDEN_VERDICT_WORDS), (
                f"Checker '{flag['type']}' emitted a verdict-like word. "
                "Evidence must describe change only."
            )
            flags.append({**flag, "status": "open"})
    return flags
