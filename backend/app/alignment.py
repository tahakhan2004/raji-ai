"""Meaning-based sentence alignment.

Primary: multilingual sentence embeddings (sentence-transformers,
paraphrase-multilingual-MiniLM-L12-v2) so source and draft can be in
different languages (e.g. English source, Urdu draft).

Fallback: TF-IDF character n-grams + cosine similarity, so the pipeline
always works even when the embedding model cannot be downloaded or loaded
(offline environment).

Greedy best-match pairing above a similarity threshold. Pairs below the
threshold are reported as "unchecked" — never silently approved, never
flagged. That is a deliberate safety property of RajiAI.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
# A vendored copy of the model may live here (fully offline-capable).
# Falls back to the Hugging Face hub name, then to TF-IDF.
_LOCAL_MODEL_DIR = (
    Path(__file__).resolve().parent.parent / "models" / MODEL_NAME
)
SIMILARITY_THRESHOLD = 0.35

_model = None
_model_error: Optional[str] = None

# Arabic diacritics (tashkeel), Quranic annotation signs and tatweel.
# Fully vocalized text — e.g. Tanzil Uthmani — collapses multilingual
# embedding quality: a true AR->EN verse pair scores 0.38 diacritized vs
# 0.83 stripped, and the model can no longer tell the true translation
# from a wrong verse. Measured 2026-10-06: even after the first strip
# pass, leftover marks U+0670 (superscript alef) and U+06E5/U+06E6
# (small waw/yeh) still poisoned embeddings — v6 scored 0.137 against
# its own translation with them, 0.684 without. The undiacritized form
# is what the embedding model saw in training.
_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]"
)


def _normalize_for_embedding(text: str) -> str:
    """Strip Arabic diacritics/tatweel for embedding only.

    Display text and the rule checkers keep the original untouched —
    only the similarity computation sees the normalized form.
    """
    return _DIACRITICS_RE.sub("", text or "")


def _load_sbert():
    """Load the multilingual embedding model once; None if unavailable."""
    global _model, _model_error
    if _model is not None or _model_error is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        # CPU-only by explicit choice: this project must run on machines
        # with no GPU. MiniLM-L12-v2 encodes in seconds on CPU.
        model_path = str(_LOCAL_MODEL_DIR) if _LOCAL_MODEL_DIR.is_dir() else MODEL_NAME
        _model = SentenceTransformer(model_path, device="cpu")
        log.info("Loaded sentence-transformer model %s (CPU)", model_path)
    except Exception as exc:  # offline, missing dep, download failure…
        _model_error = str(exc)
        log.warning("SBERT unavailable (%s); using TF-IDF fallback.", exc)
    return _model


def _sbert_similarities(src: List[str], draft: List[str]):
    import numpy as np

    model = _load_sbert()
    if model is None:
        return None
    src_emb = model.encode(src, normalize_embeddings=True)
    draft_emb = model.encode(draft, normalize_embeddings=True)
    return np.clip(src_emb @ draft_emb.T, 0.0, 1.0)


def _tfidf_similarities(src: List[str], draft: List[str]):
    """Character n-gram TF-IDF cosine similarity (language-agnostic)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    matrix = vectorizer.fit_transform(src + draft)
    sims = cosine_similarity(matrix[: len(src)], matrix[len(src):])
    return sims


def aligner_name() -> str:
    return "sbert-multilingual" if _load_sbert() is not None else "tfidf-fallback"


def align(
    src_sentences: List[str],
    draft_sentences: List[str],
    threshold: float = SIMILARITY_THRESHOLD,
) -> Tuple[List[Tuple[int, int, float]], List[int], List[int]]:
    """Greedy best-match alignment.

    Returns (pairs, unchecked_src_idx, unchecked_draft_idx) where pairs is a
    list of (src_index, draft_index, similarity). Unmatched sentences are
    "unchecked": surfaced to the reviewer, never auto-approved.
    """
    pairs: List[Tuple[int, int, float]] = []
    if not src_sentences or not draft_sentences:
        return pairs, list(range(len(src_sentences))), list(range(len(draft_sentences)))

    # Normalize for similarity only: diacritics-blind embeddings, so fully
    # vocalized Arabic aligns as well as plain Arabic. Originals are kept
    # for display and for the checkers.
    src_norm = [_normalize_for_embedding(s) for s in src_sentences]
    draft_norm = [_normalize_for_embedding(s) for s in draft_sentences]

    sims = _sbert_similarities(src_norm, draft_norm)
    if sims is None:
        sims = _tfidf_similarities(src_norm, draft_norm)

    used_src, used_draft = set(), set()
    # Greedy: repeatedly take the best remaining pair above threshold.
    candidates = [
        (float(sims[i][j]), i, j)
        for i in range(len(src_sentences))
        for j in range(len(draft_sentences))
    ]
    candidates.sort(reverse=True)
    for score, i, j in candidates:
        if score < threshold:
            break
        if i in used_src or j in used_draft:
            continue
        used_src.add(i)
        used_draft.add(j)
        pairs.append((i, j, score))

    pairs.sort(key=lambda p: p[0])
    unchecked_src = [i for i in range(len(src_sentences)) if i not in used_src]
    unchecked_draft = [j for j in range(len(draft_sentences)) if j not in used_draft]
    return pairs, unchecked_src, unchecked_draft
