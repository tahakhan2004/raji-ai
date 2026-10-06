"""RajiAI backend — FastAPI service.

Endpoints:
  GET  /api/health       service + aligner status
  GET  /api/demo-cases   planted-error demo cases (demo-data/demo_cases.json)
  POST /api/analyze      {source_text, draft_text, ...} -> aligned pairs + flags

"Flags what changed. The expert decides."
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import alignment, analyzer
from .models import AnalyzeRequest, AnalyzeResponse

log = logging.getLogger(__name__)

app = FastAPI(
    title="RajiAI",
    description="AI-assisted QA for Islamic translations. "
    "Flags what changed. The expert decides.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only; tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_DEMO_PATH = Path(__file__).resolve().parent.parent.parent / "demo-data" / "demo_cases.json"


def _load_demo_cases() -> list[dict]:
    try:
        return json.loads(_DEMO_PATH.read_text(encoding="utf-8"))["cases"]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Cannot load demo cases: {exc}")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "aligner": alignment.aligner_name()}


@app.get("/api/demo-cases")
def demo_cases() -> dict:
    return {"cases": _load_demo_cases()}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze_text(req: AnalyzeRequest) -> AnalyzeResponse:
    if not req.source_text.strip() or not req.draft_text.strip():
        raise HTTPException(
            status_code=422, detail="Both source_text and draft_text are required."
        )
    return analyzer.analyze(
        req.source_text,
        req.draft_text,
        source_lang=req.source_lang,
        draft_lang=req.draft_lang,
    )
