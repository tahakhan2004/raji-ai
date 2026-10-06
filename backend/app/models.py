"""Pydantic models for the RajiAI API.

Safety note: flags carry *evidence* (what changed) and a review status.
The backend never issues correctness verdicts — those belong to the
human reviewer in the frontend.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

FlagType = Literal["negation", "numbers", "names", "references"]
Severity = Literal["high", "medium", "low"]
# Backend-side lifecycle: every flag starts "open". The reviewer resolves
# it in the frontend to one of the tri-state outcomes below.
FlagStatus = Literal["open", "confirmed", "false_alarm", "needs_review"]
PairStatus = Literal["checked", "unchecked"]


class AnalyzeRequest(BaseModel):
    source_text: str = Field(..., description="Source-language passage text.")
    draft_text: str = Field(..., description="Draft translation text to QA.")
    source_lang: Optional[str] = Field(
        None, description="BCP-47-ish hint, e.g. 'en', 'ar', 'ur'. Optional."
    )
    draft_lang: Optional[str] = Field(None, description="Same as above, for draft.")


class Flag(BaseModel):
    id: str
    type: FlagType
    severity: Severity
    source_span: str = Field(
        "", description="Substring in the source sentence backing the flag."
    )
    draft_span: str = Field(
        "", description="Substring in the draft sentence backing the flag."
    )
    evidence: str = Field(
        ..., description="Short human-readable description of WHAT changed. "
        "Never a correctness verdict."
    )
    status: FlagStatus = "open"


class AlignedPair(BaseModel):
    index: int
    source_text: str
    draft_text: str
    similarity: float
    status: PairStatus
    flags: List[Flag] = []


class AnalysisMeta(BaseModel):
    aligner: str = Field(
        ..., description="'sbert-multilingual' or 'tfidf-fallback'."
    )
    source_sentences: int
    draft_sentences: int
    checked_pairs: int
    unchecked_pairs: int
    total_flags: int


class AnalyzeResponse(BaseModel):
    pairs: List[AlignedPair]
    meta: AnalysisMeta
