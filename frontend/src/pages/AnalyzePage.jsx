import React, { useState } from 'react';
import { analyzeTexts } from '../api';

/** Step 1 — paste or upload source + draft texts, then run the analysis. */
export function AnalyzePage({ initial, onAnalyzed, onGoDemo }) {
  const [sourceText, setSourceText] = useState(initial.sourceText);
  const [draftText, setDraftText] = useState(initial.draftText);
  const [sourceLang, setSourceLang] = useState(initial.sourceLang || '');
  const [draftLang, setDraftLang] = useState(initial.draftLang || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sourceFileName, setSourceFileName] = useState('');
  const [draftFileName, setDraftFileName] = useState('');

  const LANGS = [
    { code: '', label: 'Auto-detect' },
    { code: 'en', label: 'English' },
    { code: 'ar', label: 'Arabic' },
    { code: 'ur', label: 'Urdu' },
  ];
  const langSelect = (value, setter) => (
    <select value={value} onChange={(e) => setter(e.target.value)} style={{ flex: 1 }}
      title="Language — the name checker only compares names within one language">
      {LANGS.map((l) => (
        <option key={l.code} value={l.code}>{l.label}</option>
      ))}
    </select>
  );

  const readFile = (setter, setName) => (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setName(file.name);
    const reader = new FileReader();
    reader.onload = () => setter(String(reader.result || ''));
    reader.readAsText(file);
  };

  const UploadIcon = (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );

  const run = async () => {
    setError('');
    setLoading(true);
    try {
      const result = await analyzeTexts({
        source_text: sourceText,
        draft_text: draftText,
        source_lang: sourceLang || undefined,
        draft_lang: draftLang || undefined,
      });
      onAnalyzed(result, { sourceText, draftText, sourceLang, draftLang });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <section className="hero">
        <p className="eyebrow">AI Challenge · Serving Islamic Content</p>
        <h1>One dropped <em>word</em> can reverse a verse.</h1>
        <p className="lede">
          RajiAI is a QA assistant for Islamic translations. It aligns your source
          and draft by meaning, flags risky changes — <strong>negation, numbers,
          names, references</strong> — and every flag is decided by a human expert.
          It never issues verdicts itself.
        </p>
        <ol className="phases">
          <li><span className="ph-n">01</span><span className="ph-t">Upload</span><span className="ph-d">Source + draft go in.</span></li>
          <li><span className="ph-n">02</span><span className="ph-t">Align</span><span className="ph-d">Sentences paired by meaning, across languages.</span></li>
          <li><span className="ph-n">03</span><span className="ph-t">Flag</span><span className="ph-d">Risky changes surface with evidence.</span></li>
          <li><span className="ph-n">04</span><span className="ph-t">Review</span><span className="ph-d">The expert confirms, dismisses, or escalates.</span></li>
          <li><span className="ph-n">05</span><span className="ph-t">Export</span><span className="ph-d">Annotated text + audit log.</span></li>
        </ol>
        <div className="hero-cta">
          <button className="btn" onClick={onGoDemo}>Try a demo case →</button>
          <button className="btn ghost" onClick={() => document.getElementById('analyze-form')?.scrollIntoView({ behavior: 'smooth' })}>
            Run your own analysis
          </button>
        </div>
      </section>

      <div className="card" id="analyze-form">
        <h2><span className="step-n">01</span>Source &amp; draft</h2>
        <p>
          Paste the source passage and its draft translation. RajiAI aligns them
          by meaning and flags risky changes — <em>negation, numbers, names,
          references</em>. <strong>Flags what changed. The expert decides.</strong>
        </p>
        <div className="grid-2">
          <div>
            <label><strong>Source text</strong></label>
            <textarea value={sourceText} onChange={(e) => setSourceText(e.target.value)}
              placeholder="e.g. Neither drowsiness nor sleep overtakes Him." dir="auto" />
            <div className="controls-row">
              {langSelect(sourceLang, setSourceLang)}
              <label className="file-btn" title="Upload a .txt or .md file">
                {UploadIcon}
                <span>{sourceFileName || 'Choose file'}</span>
                <input type="file" accept=".txt,.md" onChange={readFile(setSourceText, setSourceFileName)} />
              </label>
            </div>
          </div>
          <div>
            <label><strong>Draft translation</strong></label>
            <textarea value={draftText} onChange={(e) => setDraftText(e.target.value)}
              placeholder="e.g. اسے اونگھ آتی ہے اور نیند آتی ہے۔" dir="auto" />
            <div className="controls-row">
              {langSelect(draftLang, setDraftLang)}
              <label className="file-btn" title="Upload a .txt or .md file">
                {UploadIcon}
                <span>{draftFileName || 'Choose file'}</span>
                <input type="file" accept=".txt,.md" onChange={readFile(setDraftText, setDraftFileName)} />
              </label>
            </div>
          </div>
        </div>
        {error && <p style={{ color: 'var(--red)' }}>⚠ {error}</p>}
        <div style={{ marginTop: '1rem' }}>
          <button className="btn" onClick={run} disabled={loading || !sourceText.trim() || !draftText.trim()}>
            {loading ? 'Analyzing…' : 'Run analysis →'}
          </button>
        </div>
      </div>

      <div className="card">
        <h2>Safety boundaries</h2>
        <ul className="boundary-list">
          <li><strong>No guessing</strong> — uncertain alignments go to an unchecked queue, never auto-approved.</li>
          <li><strong>No correctness verdicts</strong> — flags carry evidence of <em>what changed</em>, never “correct / incorrect”.</li>
          <li><strong>No silent approval</strong> — every flag stays visibly open until a reviewer resolves it.</li>
        </ul>
      </div>
    </div>
  );
}
