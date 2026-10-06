"""API tests: health, demo cases, and end-to-end analysis."""

from fastapi.testclient import TestClient

from app import alignment
from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["aligner"] in ("sbert-multilingual", "tfidf-fallback")


def test_demo_cases_load():
    resp = client.get("/api/demo-cases")
    assert resp.status_code == 200
    cases = resp.json()["cases"]
    assert len(cases) == 16
    ids = {c["id"] for c in cases}
    assert {
        "negation-2-255",
        "numbers-99-names",
        "names-dropped-narrator",
        "references-altered",
        "clean-control",
        "negation-partial-neither-nor",
        "negation-added",
        "negation-double-negative",
        "numbers-arabic-indic-changed",
        "numbers-word-dropped",
        "names-transliteration-variant",
        "names-arabic-narrator-dropped",
        "keyterm-say-dropped",
        "references-surah-changed",
        "references-collection-dropped",
        "clean-cross-lingual-simple",
    } <= ids


def test_analyze_2_255_demo_case():
    """POST /api/analyze on the flagship 2:255 case.

    With multilingual embeddings the cross-lingual pair aligns and the
    negation flag fires. With the TF-IDF fallback the pair cannot align and
    must surface as 'unchecked' — never silently approved. Both are correct
    safety behavior; the test branches on the reported aligner.
    """
    payload = {
        "source_text": "Neither drowsiness nor sleep overtakes Him.",
        "draft_text": "اسے اونگھ آتی ہے اور نیند آتی ہے۔",
        "source_lang": "en",
        "draft_lang": "ur",
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "pairs" in body and "meta" in body

    if body["meta"]["aligner"] == "sbert-multilingual":
        checked = [p for p in body["pairs"] if p["status"] == "checked"]
        assert len(checked) == 1
        flags = checked[0]["flags"]
        neg = [f for f in flags if f["type"] == "negation"]
        assert len(neg) == 1
        assert neg[0]["severity"] == "high"
        assert neg[0]["status"] == "open"
    else:
        # Fallback: nothing may be silently approved.
        unchecked = [p for p in body["pairs"] if p["status"] == "unchecked"]
        assert len(unchecked) >= 1
        assert all(p["flags"] == [] for p in unchecked)


def test_analyze_numbers_case_end_to_end():
    payload = {
        "source_text": "Allah has 99 names. اللہ کے ٩٩ نام ہیں۔",
        "draft_text": "Allah has 98 names. اللہ کے ٩٨ نام ہیں۔",
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    flags = [f for p in resp.json()["pairs"] for f in p["flags"]]
    num_flags = [f for f in flags if f["type"] == "numbers"]
    assert len(num_flags) == 2  # ASCII pair + Arabic-Indic pair
    assert all(f["severity"] == "high" for f in num_flags)


def test_analyze_clean_pair_zero_flags():
    payload = {
        "source_text": "And He is the Most High, the Most Great.",
        "draft_text": "And He is the Most High, the Most Great.",
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total_flags"] == 0
    assert body["meta"]["unchecked_pairs"] == 0


def test_analyze_requires_both_texts():
    resp = client.post("/api/analyze", json={"source_text": "x", "draft_text": ""})
    assert resp.status_code == 422


def test_flag_schema():
    """Every flag carries the full contract the frontend needs."""
    payload = {
        "source_text": "See Quran 2:255.",
        "draft_text": "See Quran 2:256.",
    }
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 200
    flags = [f for p in resp.json()["pairs"] for f in p["flags"]]
    assert flags, "expected at least one reference flag"
    for f in flags:
        assert set(f) >= {
            "id", "type", "severity", "source_span",
            "draft_span", "evidence", "status",
        }
        assert f["type"] in ("negation", "numbers", "names", "references")
        assert f["severity"] in ("high", "medium", "low")
        assert f["status"] == "open"


def test_sbert_aligner_active():
    """Documents which aligner is running in this environment."""
    # Informational: ensures we know which branch CI exercises.
    assert alignment.aligner_name() in ("sbert-multilingual", "tfidf-fallback")
