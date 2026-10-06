# RajiAI

**Flags what changed. The expert decides.**

RajiAI is an AI-assisted QA tool for Islamic translations. Workflow: **Source → Draft → Review → Publish**.
It aligns a source passage with its draft translation by meaning, then flags risky changes —
**NEGATION · NUMBERS · NAMES · REFERENCES** — with evidence, leaving every judgment to a human expert.

> RajiAI never declares a translation religiously correct. That judgment belongs to a
> qualified human expert.

**Live demo:** [RajiAI Web App](https://raji-ai.vercel.app) · **API:** [RajiAI API](https://khanlala12500000--raji-ai-web.modal.run)

## Safety boundaries (hard requirements)

1. **No guessing** — sentence pairs the aligner cannot confidently match go to an
   *unchecked* queue. They are surfaced to the reviewer, never auto-approved and never flagged.
2. **No correctness verdicts** — checkers report *what changed* (evidence), never
   “correct / incorrect / mistranslated”. This is enforced by an assertion in
   `backend/app/checkers.py::run_checkers`.
3. **No silent approval** — every flag starts `open` and stays visibly open until the
   reviewer resolves it as **confirmed issue**, **false alarm**, or **needs further review**.

## Project structure

```
raji-ai/
├── backend/                 # Python FastAPI service
│   ├── app/
│   │   ├── main.py          # REST API: /api/health, /api/demo-cases, /api/analyze
│   │   ├── analyzer.py      # pipeline: segment → align → check
│   │   ├── segmentation.py  # sentence splitter (Arabic/Urdu/English punctuation)
│   │   ├── alignment.py     # multilingual embeddings, TF-IDF fallback
│   │   ├── checkers.py      # the four rule checkers (evidence only)
│   │   └── models.py        # Pydantic request/response models
│   ├── models/              # vendored paraphrase-multilingual-MiniLM-L12-v2 (offline)
│   └── tests/               # pytest suite (47 tests)
├── frontend/                # React (Vite) + plain CSS
│   └── src/
│       ├── pages/           # Analyze · Review · Demo · Export
│       └── components/      # PassagePair, FlagCard (tri-state resolution)
├── demo-data/
│   └── demo_cases.json      # 14 planted-error cases + 2 clean controls
└── README.md
```

## Cost & hardware: 100% free, CPU-only, no keys

- **No paid APIs, no API keys, no accounts, no external services.** Every part of
  RajiAI runs locally: the rule engine, the embeddings, and the fallback are all
  in-process. There is nowhere to even enter an API key.
- **CPU-only.** The embedding model is `paraphrase-multilingual-MiniLM-L12-v2`
  and is pinned to CPU (`device="cpu"`) — it encodes sentences in seconds on a
  machine with no GPU. No large LLM is used anywhere. A copy of the model is
  vendored at `backend/models/paraphrase-multilingual-MiniLM-L12-v2/`, so the
  aligner works fully offline; install CPU-only torch via
  `pip install --index-url https://download.pytorch.org/whl/cpu torch`
  (the default PyPI torch bundles unused CUDA libraries). Cloning from GitHub
  excludes `backend/models/` (over GitHub's 100 MB file limit); on first run
  with internet access the model downloads automatically from the Hugging Face
  hub, so nothing is lost.
- **Zero-download fallback.** If the embedding model cannot be loaded
  (e.g. not vendored and no network), the character n-gram TF-IDF aligner
  takes over with no model files at all. Cross-lingual pairs then surface as
  *unchecked* rather than being force-aligned.
- **No database.** The API is stateless; review state lives in the browser
  session and leaves the machine only via the reviewer's own audit-log export.

## How it works

1. **Segment** — source and draft are split into sentences, handling `. ! ? ۔ ؟` and newlines.
2. **Align** — sentences are paired by meaning. Primary: multilingual sentence
   embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, cross-lingual). Fallback:
   character n-gram TF-IDF + cosine similarity, so the pipeline always works offline.
   Greedy best-match above a similarity threshold; below threshold → `unchecked`.
3. **Check** — four rule checkers compare each aligned pair:
   - **NEGATION** — marker lists for English (`not`, `never`, `neither`, `nor`, `n't`…),
     Arabic (`لا`, `لم`, `لن`, `ليس`…), Urdu (`نہ`, `نہیں`, `نا`…). High severity when a
     source negation disappears in the draft (can reverse meaning, e.g. Quran 2:255).
     Every occurrence is counted (not just distinct marker types), and the Arabic
     conjunction wa- is stripped before matching, so ولم and ولا count correctly.
   - **NUMBERS** — Arabic-Indic (`٠١٢٣٤٥٦٧٨٩`) and Extended Arabic-Indic (`۰۱۲۳۴۵۶۷۸۹`)
     digits normalized to ASCII before comparing; flags changed/dropped/added values.
   - **NAMES** — heuristic, conservative: capitalized Latin tokens (not sentence-initial,
     not pronouns/stopwords) and distinctive Arabic/Urdu-script tokens; reference
     substrings are blanked first so the reference checker owns them. Names are
     only compared **within one language** (via `source_lang`/`draft_lang`; falls back
     to same-script detection) — without a transliteration lexicon, cross-language
     token overlap is meaningless. Urdu/Arabic orthographic variants are normalized
     (اللہ → الله, ی → ي) before comparison. For same-language Latin-script pairs it
     also flags dropped ordinary key terms (low severity, e.g. a missing "Say"),
     since the capitalized-name heuristic skips sentence-initial tokens.
   - **REFERENCES** — verse refs (`2:255`, incl. `٢:٢٥٥`), hadith collections
     (Bukhari, Muslim, Tirmidhi…), surah mentions, page/volume markers.
4. **Review** — the expert resolves each flag: **confirmed issue / false alarm /
   needs further review**, with an optional comment. Unreviewed flags stay **open**.
5. **Export** — corrected text (draft annotated with reviewer decisions — RajiAI never
   rewrites translations) plus an audit log (JSON + CSV) recording every flag, its
   resolution, comment, and timestamps.

## Run it

### Backend

```bash
cd backend
python3 -m venv .venv
# CPU-only torch (the default PyPI torch ships unused CUDA libraries):
.venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q                # all tests green
.venv/bin/uvicorn app.main:app --reload --port 8000
```

API at `http://localhost:8000` — interactive docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 (proxies /api to :8000)
npm run build    # production build → frontend/dist/
```

To point a production build at a remote backend: `VITE_API_URL=https://your-backend npm run build`.

## API contract

**POST /api/analyze**

```json
{ "source_text": "…", "draft_text": "…", "source_lang": "en", "draft_lang": "ur" }
```

Response: `{ "pairs": [ … ], "meta": { … } }`

Each pair:

```json
{
  "index": 0,
  "source_text": "Neither drowsiness nor sleep overtakes Him.",
  "draft_text": "اسے اونگھ آتی ہے اور نیند آتی ہے۔",
  "similarity": 0.71,
  "status": "checked",
  "flags": [
    {
      "id": "p0-negation-0",
      "type": "negation",
      "severity": "high",
      "source_span": "Neither",
      "draft_span": "اسے اونگھ آتی ہے اور نیند آتی ہے۔",
      "evidence": "Source contains 2 negation marker(s) … Reviewer to decide.",
      "status": "open"
    }
  ]
}
```

- `type`: `negation | numbers | names | references`
- `severity`: `high | medium | low`
- `status` (from backend): always `open`; the reviewer resolves it in the UI to
  `confirmed | false_alarm | needs_review` (recorded in the audit export).
- `status: "unchecked"` pairs carry no flags and must be reviewed manually.

**GET /api/demo-cases** — the 16 demo cases. **GET /api/health** — service + active aligner.

## Demo cases (`demo-data/demo_cases.json`)

14 planted-error cases + 2 clean controls. Every expected flag below was verified
by running the actual checkers (not assumed).

| id | case | expected |
|---|---|---|
| `negation-2-255` | Ayat al-Kursi (Quran 2:255): Urdu draft drops نہ | NEGATION (high) |
| `negation-partial-neither-nor` | only "nor" dropped from "neither/nor" | NEGATION (high) |
| `negation-added` | draft inserts "not" | NEGATION (medium) + NAMES (low, stemming noise) |
| `negation-double-negative` | "not uncommon" → "common" | NEGATION (high) + NAMES (low, stemming noise) |
| `numbers-99-names` | 99 → 98, incl. Arabic-Indic ٩٩ → ٩٨ | NUMBERS (high) |
| `numbers-arabic-indic-changed` | 99 → ٩٨ across digit scripts | NUMBERS (high) |
| `numbers-word-dropped` | number *word* "five" dropped (digits-only limitation) | NAMES (low, key term) |
| `names-dropped-narrator` | “Abu Hurairah” dropped from narration | NAMES (medium) |
| `names-transliteration-variant` | Hurairah → Hurayrah (reviewer decides: same person) | NAMES (medium) |
| `names-arabic-narrator-dropped` | أبي هريرة dropped from Arabic narration | NAMES (medium) |
| `keyterm-say-dropped` | Al-Ikhlas 112:1: "Say" dropped, "Indivisible"→"divisible" | NAMES (medium) + NAMES (low) |
| `references-altered` | 2:255 → 2:256, “Sahih Muslim” dropped | REFERENCES |
| `references-surah-changed` | Surah Al-Baqarah → Surah Al-Imran | REFERENCES (medium) |
| `references-collection-dropped` | "Sahih Muslim" dropped | REFERENCES (medium ×2) |
| `clean-control` | identical source/draft | no flags |
| `clean-cross-lingual-simple` | correct EN→AR translation | no flags |

## Notes & limitations

- The embedding model is vendored at `backend/models/` (~450 MB), so alignment
  works fully offline. If the model files are removed and there is no network,
  the TF-IDF fallback activates automatically and cross-lingual pairs surface
  as *unchecked* rather than being force-aligned. The active aligner is
  reported by `/api/health` and in every analysis response.
- The name checker is intentionally conservative (heuristic proper-noun
  detection) — false alarms are expected and cheap: mark them as such.
  Names are verified only within one language; cross-language name checking
  (e.g. أبو هريرة → "Abu Hurairah") needs a transliteration lexicon and is a
  documented limitation — the reviewer decides those cases.
- RajiAI is a QA assistant, not a religious authority. Every flag is evidence
  for a qualified reviewer to judge.

## Sources & licenses

**Tools & libraries**
- Python / FastAPI (MIT) — backend API
- React + Vite (MIT) — frontend
- sentence-transformers (Apache 2.0) — embedding runtime
- scikit-learn (BSD-3) — TF-IDF fallback aligner
- PyTorch, CPU build (BSD-style) — model inference, CPU only
- pytest (MIT) — test suite

**Embedding model**
- `paraphrase-multilingual-MiniLM-L12-v2` (Apache 2.0), loaded via
  sentence-transformers from the Hugging Face hub. Used only for sentence
  alignment; no text is generated by any model.

**Text sources (demo & testing only)**
- Arabic Quran text: Tanzil project, Uthmani script (tanzil.net).
- English translations in demo cases and test files: Saheeh International
  rendering.
- The 16 demo cases are synthetic planted-error pairs built for this project.

RajiAI's own code is released under the MIT License.

Built solo by Taha Khan for the Bathel AI Challenge — “Serving Islamic Content” track.
