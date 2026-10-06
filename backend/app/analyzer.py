"""Analysis orchestration: segment → align → check.

Pipeline:
  1. Split source and draft into sentences (segmentation).
  2. Align sentences by meaning (alignment).
  3. Run the four rule checkers on each aligned pair.
  4. Sentences that could not be aligned become "unchecked" pairs —
     surfaced to the reviewer, never silently approved.
"""

from . import alignment, checkers, segmentation
from .models import AlignedPair, AnalyzeResponse, AnalysisMeta, Flag


def analyze(
    source_text: str,
    draft_text: str,
    source_lang: str | None = None,
    draft_lang: str | None = None,
) -> AnalyzeResponse:
    src_sentences = segmentation.segment(source_text)
    draft_sentences = segmentation.segment(draft_text)

    pairs_idx, unchecked_src, unchecked_draft = alignment.align(
        src_sentences, draft_sentences
    )

    pairs: list[AlignedPair] = []
    total_flags = 0

    for index, (i, j, score) in enumerate(pairs_idx):
        raw_flags = checkers.run_checkers(
            src_sentences[i],
            draft_sentences[j],
            source_lang=source_lang,
            draft_lang=draft_lang,
        )
        flags = [
            Flag(
                id=f"p{index}-{f['type']}-{n}",
                type=f["type"],
                severity=f["severity"],
                source_span=f.get("source_span", ""),
                draft_span=f.get("draft_span", ""),
                evidence=f["evidence"],
                status="open",
            )
            for n, f in enumerate(raw_flags)
        ]
        total_flags += len(flags)
        pairs.append(
            AlignedPair(
                index=index,
                source_text=src_sentences[i],
                draft_text=draft_sentences[j],
                similarity=round(score, 3),
                status="checked",
                flags=flags,
            )
        )

    # Unchecked singletons: shown to the reviewer, never auto-approved.
    for i in unchecked_src:
        pairs.append(
            AlignedPair(
                index=len(pairs),
                source_text=src_sentences[i],
                draft_text="",
                similarity=0.0,
                status="unchecked",
                flags=[],
            )
        )
    for j in unchecked_draft:
        pairs.append(
            AlignedPair(
                index=len(pairs),
                source_text="",
                draft_text=draft_sentences[j],
                similarity=0.0,
                status="unchecked",
                flags=[],
            )
        )

    unchecked_pairs = len(unchecked_src) + len(unchecked_draft)
    meta = AnalysisMeta(
        aligner=alignment.aligner_name(),
        source_sentences=len(src_sentences),
        draft_sentences=len(draft_sentences),
        checked_pairs=len(pairs_idx),
        unchecked_pairs=unchecked_pairs,
        total_flags=total_flags,
    )
    return AnalyzeResponse(pairs=pairs, meta=meta)
