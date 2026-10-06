"""Tests for meaning-based alignment, including the 'unchecked' safety path."""

from app import alignment


def test_align_pairs_similar_sentences():
    src = ["Allah has 99 names.", "Whoever learns them will enter Paradise."]
    draft = ["Whoever learns them will enter Paradise.", "Allah has 98 names."]
    pairs, unchecked_src, unchecked_draft = alignment.align(src, draft)
    assert unchecked_src == []
    assert unchecked_draft == []
    assert len(pairs) == 2
    # Greedy best-match must recover the reordered pairing.
    mapping = {i: j for i, j, _ in pairs}
    assert mapping[0] == 1
    assert mapping[1] == 0


def test_low_similarity_goes_unchecked_not_silently_approved():
    """Dissimilar sentences must land in the unchecked queue — never flagged,
    never approved."""
    src = ["The cat sat on the mat."]
    draft = ["Quantum mechanics describes particle behavior."]
    pairs, unchecked_src, unchecked_draft = alignment.align(src, draft)
    assert pairs == []
    assert unchecked_src == [0]
    assert unchecked_draft == [0]


def test_align_empty_inputs():
    pairs, u_src, u_draft = alignment.align([], [])
    assert pairs == [] and u_src == [] and u_draft == []


def test_align_one_side_empty():
    pairs, u_src, u_draft = alignment.align(["Hello."], [])
    assert pairs == []
    assert u_src == [0]
    assert u_draft == []


def test_aligner_name_reported():
    name = alignment.aligner_name()
    assert name in ("sbert-multilingual", "tfidf-fallback")


def test_normalize_strips_arabic_diacritics():
    assert alignment._normalize_for_embedding("يُوسُفُ") == "يوسف"
    assert alignment._normalize_for_embedding("قَالَ") == "قال"
    # Quranic marks that survive a naive tashkeel strip but still poison
    # embeddings (measured: v6 sim 0.137 -> 0.684 after removing them).
    assert alignment._normalize_for_embedding("نِعْمَتَهُۥ") == "نعمته"
    assert alignment._normalize_for_embedding("عَلَىٰ") == "على"
    assert alignment._normalize_for_embedding("يُۦنَبَّأُ") == "ينبأ"
    assert alignment._normalize_for_embedding("plain English 123") == "plain English 123"


def test_align_vocalized_arabic_finds_true_translation():
    """Tanzil-style fully vocalized Arabic must align to its real translation.

    Diacritics collapse embedding quality (true-pair similarity 0.38 with vs
    0.83 without), so without normalization the verse misaligns to a
    similar-sounding wrong verse (both are dream descriptions).
    """
    src = [
        "إِذْ قَالَ يُوسُفُ لِأَبِيهِ يَا أَبَتِ إِنِّي رَأَيْتُ أَحَدَ عَشَرَ كَوْكَبًا "
        "وَالشَّمْسَ وَالْقَمَرَ رَأَيْتُهُمْ لِي سَاجِدِينَ"
    ]
    draft_true = (
        "[Of these stories mention] when Joseph said to his father, \"O my father, "
        "indeed I have seen [in a dream] eleven stars and the sun and the moon; "
        "I saw them prostrating to me.\""
    )
    draft_wrong = (
        "And [subsequently] the king said, \"Indeed, I have seen [in a dream] seven "
        "fat cows being eaten by seven [that were] lean.\""
    )
    pairs, _, _ = alignment.align(src, [draft_true, draft_wrong])
    assert len(pairs) == 1
    mapping = {i: j for i, j, _ in pairs}
    assert mapping[0] == 0
