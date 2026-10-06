import React, { useEffect, useState } from 'react';
import './styles.css';
import { analyzeTexts, fetchHealth } from './api';
import { AnalyzePage } from './pages/AnalyzePage';
import { ReviewPage } from './pages/ReviewPage';
import { DemoPage } from './pages/DemoPage';
import { ExportPage } from './pages/ExportPage';

const TABS = [
  { id: 'analyze', n: '01', label: 'Analyze' },
  { id: 'review', n: '02', label: 'Review' },
  { id: 'demo', n: '03', label: 'Demo' },
  { id: 'export', n: '04', label: 'Export' },
];

export default function App() {
  const [tab, setTab] = useState('analyze');
  const [texts, setTexts] = useState({ sourceText: '', draftText: '', sourceLang: '', draftLang: '' });
  const [analysis, setAnalysis] = useState(null);
  // resolutions: { [flagId]: { state: 'confirmed'|'false_alarm'|'needs_review', comment, reviewedAt } }
  // A flag with no entry (or no state) is OPEN — never auto-resolved.
  const [resolutions, setResolutions] = useState({});
  const [backendStatus, setBackendStatus] = useState('checking…');

  useEffect(() => {
    fetchHealth()
      .then((h) => setBackendStatus(`online · aligner: ${h.aligner}`))
      .catch(() => setBackendStatus('offline — start the FastAPI backend on :8000'));
  }, []);

  const handleAnalyzed = (result, usedTexts) => {
    setAnalysis(result);
    setTexts(usedTexts);
    setResolutions({}); // fresh review session
    setTab('review');
  };

  const handleLoadDemo = async (demoCase) => {
    const usedTexts = {
      sourceText: demoCase.source_text,
      draftText: demoCase.draft_text,
      sourceLang: demoCase.source_lang,
      draftLang: demoCase.draft_lang,
    };
    const result = await analyzeTexts({
      source_text: demoCase.source_text,
      draft_text: demoCase.draft_text,
      source_lang: demoCase.source_lang,
      draft_lang: demoCase.draft_lang,
    });
    handleAnalyzed(result, usedTexts);
  };

  const handleResolve = (flagId, state) => {
    setResolutions((prev) => ({
      ...prev,
      [flagId]: {
        state,
        comment: prev[flagId]?.comment || '',
        reviewedAt: new Date().toISOString(),
      },
    }));
  };

  const handleComment = (flagId, comment) => {
    setResolutions((prev) => ({
      ...prev,
      [flagId]: {
        state: prev[flagId]?.state,
        comment,
        reviewedAt: prev[flagId]?.reviewedAt,
      },
    }));
  };

  return (
    <div>
      <header className="app-header">
        <div className="brand">
          <span className="wordmark">Raji<em>AI</em></span>
          <p className="slogan">Flags what changed. The expert decides.</p>
        </div>
        <span className="status-pill">backend · {backendStatus}</span>
      </header>
      <nav className="nav">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'active' : ''}
            disabled={(t.id === 'review' || t.id === 'export') && !analysis}
            onClick={() => setTab(t.id)}
          >
            <span className="step-n">{t.n}</span>{t.label}
          </button>
        ))}
      </nav>
      <main>
        {tab === 'analyze' && <AnalyzePage initial={texts} onAnalyzed={handleAnalyzed} onGoDemo={() => setTab('demo')} />}
        {tab === 'review' && (
          <ReviewPage analysis={analysis} resolutions={resolutions}
            onResolve={handleResolve} onComment={handleComment} />
        )}
        {tab === 'demo' && <DemoPage onLoadDemo={handleLoadDemo} />}
        {tab === 'export' && <ExportPage analysis={analysis} resolutions={resolutions} texts={texts} />}
        <p className="footer-note">
          RajiAI is a QA assistant for Islamic translations. It flags risky changes
          with evidence and never declares a translation religiously correct —
          that judgment belongs to a qualified human expert.
        </p>
      </main>
    </div>
  );
}
