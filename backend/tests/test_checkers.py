"""Unit tests for segmentation and the four rule checkers."""

from app import checkers, segmentation


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def test_segment_english():
    assert segmentation.segment("Hello world. How are you? Fine!") == [
        "Hello world.", "How are you?", "Fine!",
    ]


def test_segment_arabic_urdu_punctuation():
    text = "اللہ کے ٩٩ نام ہیں۔ جو انہیں یاد کرے گا وہ جنت میں داخل ہوگا؟"
    assert segmentation.segment(text) == [
        "اللہ کے ٩٩ نام ہیں۔",
        "جو انہیں یاد کرے گا وہ جنت میں داخل ہوگا؟",
    ]


def test_segment_empty():
    assert segmentation.segment("") == []
    assert segmentation.segment("   ") == []


def test_segment_strips_tanzil_verse_prefixes():
    text = "12|4|إِذْ قَالَ يُوسُفُ لِأَبِيهِ\n12|5|قَالَ يَا بُنَيَّ لَا تَقْصُصْ"
    assert segmentation.segment(text) == [
        "إِذْ قَالَ يُوسُفُ لِأَبِيهِ",
        "قَالَ يَا بُنَيَّ لَا تَقْصُصْ",
    ]


def test_segment_keeps_real_leading_numbers():
    # A genuine leading number that is NOT a verse prefix must survive.
    assert segmentation.segment("99 names of Allah. They are beautiful.") == [
        "99 names of Allah.",
        "They are beautiful.",
    ]


# ---------------------------------------------------------------------------
# Negation
# ---------------------------------------------------------------------------

def test_negation_missing_in_draft_quran_2_255():
    """The flagship case: Ayat al-Kursi without its negation."""
    src = "Neither drowsiness nor sleep overtakes Him."
    draft = "اسے اونگھ آتی ہے اور نیند آتی ہے۔"  # faulty: no نہ
    flags = checkers.check_negation(src, draft)
    assert len(flags) == 1
    assert flags[0]["type"] == "negation"
    assert flags[0]["severity"] == "high"
    # Evidence describes the change; never a verdict.
    assert "missing" in flags[0]["evidence"].lower()


def test_negation_added_in_draft():
    flags = checkers.check_negation("He sleeps.", "He does not sleep.")
    assert len(flags) == 1
    assert flags[0]["severity"] == "medium"


def test_negation_equal_no_flag():
    assert checkers.check_negation("He does not sleep.", "وہ نہیں سوتا۔") == []


def test_negation_evidence_has_no_verdicts():
    flags = checkers.check_negation(
        "Neither drowsiness nor sleep overtakes Him.", "He is awake."
    )
    for f in flags:
        lowered = f["evidence"].lower()
        for word in ("correct", "incorrect", "wrong", "mistranslated"):
            assert word not in lowered


# ---------------------------------------------------------------------------
# Numbers (incl. Arabic-Indic digits)
# ---------------------------------------------------------------------------

def test_numbers_changed_ascii():
    flags = checkers.check_numbers("Allah has 99 names.", "Allah has 98 names.")
    assert len(flags) == 1
    assert flags[0]["type"] == "numbers"
    assert flags[0]["severity"] == "high"
    assert "99" in flags[0]["evidence"] and "98" in flags[0]["evidence"]


def test_numbers_changed_arabic_indic():
    """٩٩ (Arabic-Indic) must normalize to 99 before comparing."""
    flags = checkers.check_numbers("اللہ کے ٩٩ نام ہیں۔", "اللہ کے ٩٨ نام ہیں۔")
    assert len(flags) == 1
    assert flags[0]["type"] == "numbers"
    assert flags[0]["severity"] == "high"


def test_numbers_changed_persian_digits():
    flags = checkers.check_numbers("۹۹ نام", "۹۸ نام")
    assert len(flags) == 1
    assert flags[0]["type"] == "numbers"


def test_numbers_dropped():
    flags = checkers.check_numbers("Read chapter 5.", "Read the chapter.")
    assert len(flags) == 1
    assert flags[0]["severity"] == "medium"
    assert "missing" in flags[0]["evidence"].lower()


def test_numbers_equal_no_flag():
    assert checkers.check_numbers("٩٩ names", "99 names") == []


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

def test_names_dropped():
    src = "Narrated by Abu Hurairah: The Prophet said, 'Learn the Quran.'"
    draft = "It was narrated: The Prophet said, 'Learn the Quran.'"
    flags = checkers.check_names(src, draft)
    assert len(flags) == 1
    assert flags[0]["type"] == "names"
    assert "abu" in flags[0]["evidence"].lower()


def test_names_pronouns_not_flagged():
    """'Him' capitalized mid-sentence is a pronoun, not a name."""
    assert checkers.check_names(
        "Neither drowsiness nor sleep overtakes Him.",
        "اسے اونگھ آتی ہے اور نیند آتی ہے۔",
    ) == []


def test_names_equal_no_flag():
    src = "Narrated by Abu Hurairah."
    assert checkers.check_names(src, src) == []


def test_names_dropped_sentence_initial_term():
    """'Say' dropped from the draft must be flagged even though the
    capitalized-name heuristic skips sentence-initial tokens (Qur'an 112:1)."""
    src = "Say, 'O Prophet, He is Allah, the One, the Indivisible.'"
    draft = "'O Prophet, He is Allah, the One, the divisible.'"
    flags = checkers.check_names(src, draft)
    assert any("say" in f["evidence"].lower() for f in flags)
    assert any(f["severity"] == "low" for f in flags)


def test_names_cross_lingual_no_term_noise():
    """The term-coverage pass stays off for cross-lingual pairs: with no
    Latin-script names on either side, nothing is flagged."""
    assert checkers.check_names(
        "The boy went home early.",
        "لڑکا جلدی گھر گیا۔",
    ) == []


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------

def test_reference_altered():
    flags = checkers.check_references(
        "This is stated in Quran 2:255.", "This is stated in Quran 2:256."
    )
    assert len(flags) == 1
    assert flags[0]["type"] == "references"
    assert flags[0]["severity"] == "high"
    assert "2:255" in flags[0]["evidence"] and "2:256" in flags[0]["evidence"]


def test_reference_dropped_collection():
    flags = checkers.check_references(
        "As explained in Sahih Muslim.", "As explained in the commentary."
    )
    assert any(f["type"] == "references" for f in flags)
    assert any("missing" in f["evidence"].lower() for f in flags)


def test_reference_equal_no_flag():
    src = "See Quran 2:255 and Sahih Muslim, vol. 2."
    assert checkers.check_references(src, src) == []


# ---------------------------------------------------------------------------
# Clean pair + orchestration guard
# ---------------------------------------------------------------------------

def test_clean_pair_zero_flags():
    src = "And He is the Most High, the Most Great."
    assert checkers.run_checkers(src, src) == []


def test_run_checkers_rejects_verdicts():
    """run_checkers asserts no verdict-like language in evidence."""
    checkers.run_checkers(
        "Neither drowsiness nor sleep overtakes Him.",
        "اسے اونگھ آتی ہے اور نیند آتی ہے۔",
    )  # must not raise


def test_negation_wa_prefix_counted():
    """ولم / ولا count via the attached conjunction wa- (Qur'an 112:3)."""
    flags = checkers.check_negation("لم يلد ولم يولد", "He begets and He is born.")
    assert len(flags) == 1
    assert flags[0]["severity"] == "high"
    assert "2 negation" in flags[0]["evidence"]


def test_negation_wa_prefix_clean():
    """Same markers both sides (2 vs 2) → no flag."""
    assert checkers.check_negation(
        "لم يلد ولم يولد", "He neither begets nor is He born."
    ) == []


def test_names_cross_script_skipped():
    """Arabic → English: no transliteration lexicon, so the checker stays
    silent instead of flagging every pair (documented limitation)."""
    assert checkers.check_names("عن أبي هريرة", "from the narrator") == []


def test_names_urdu_arabic_ortho_normalized():
    """اللہ اکبر (Urdu spelling) matches الله أكبر (Arabic spelling) after
    orthographic normalization — no flag on a correct translation."""
    assert checkers.check_names("الله أكبر", "اللہ اکبر") == []


def test_negation_contraction_counts():
    """"doesn't"/"don't"/"can't" must count as negation markers."""
    assert len(checkers._find_negations("He doesn't sleep.")) == 1
    assert len(checkers._find_negations("Don't go there.")) == 1
    flags = checkers.check_negation("He doesn't sleep.", "He sleeps.")
    assert len(flags) == 1 and flags[0]["severity"] == "high"


def test_negation_cannot_counts():
    """"cannot" is a standalone negation marker (no word boundary inside)."""
    assert len(checkers._find_negations("Allah cannot be seen.")) == 1
    flags = checkers.check_negation("Allah cannot be seen.", "Allah can be seen.")
    assert len(flags) == 1 and flags[0]["severity"] == "high"


def test_negation_inna_not_counted_alone():
    """'إن' is emphasis ('indeed') or conditional ('if') — not a negation."""
    # إِنَّ رَبَّكَ عَلِيمٌ حَكِيمٌ — "indeed your Lord is Knowing, Wise": no negation
    assert checkers._find_negations("إِنَّ رَبَّكَ عَلِيمٌ حَكِيمٌ") == []
    # إِن كُنتُمْ فَاعِلِينَ — "if you would do": conditional, no negation
    assert checkers._find_negations("إِن كُنتُمْ فَاعِلِينَ") == []


def test_negation_illa_construction_counts():
    """'إن ... إلا' / 'ما ... إلا' ('nothing but' / 'not ... except') is negation."""
    assert len(checkers._find_negations("إِنْ هَٰذَا إِلَّا مَلَكٌ كَرِيمٌ")) == 1
    assert len(checkers._find_negations("وَمَا يُؤْمِنُ أَكْثَرُهُم بِاللَّهِ إِلَّا وَهُم مُّشْرِكُونَ")) == 1
    # ما without إلا stays uncounted (relative pronoun "what/which")
    assert checkers._find_negations("مَا فَعَلْتُم بِيُوسُفَ") == []
