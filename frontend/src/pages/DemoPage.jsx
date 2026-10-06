import React, { useEffect, useState } from 'react';
import { fetchDemoCases } from '../api';

/** Step 3 — pre-loaded planted-error demo cases. */
export function DemoPage({ onLoadDemo }) {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [runningId, setRunningId] = useState(null);

  useEffect(() => {
    fetchDemoCases()
      .then(setCases)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const load = async (c) => {
    setRunningId(c.id);
    try {
      await onLoadDemo(c);
    } finally {
      setRunningId(null);
    }
  };

  if (loading) return <div className="card"><p>Loading demo cases…</p></div>;
  if (error) return <div className="card"><p style={{ color: 'var(--red)' }}>⚠ {error}</p></div>;

  return (
    <div>
      <div className="card">
        <h2><span className="step-n">03</span>Demo cases</h2>
        <p>
          Planted-error cases plus one clean control. Loading a case runs the
          full analysis so you can review the flags it produces.
        </p>
      </div>
      {cases.map((c) => (
        <div className="card demo-case" key={c.id}>
          <h3 style={{ marginTop: 0 }}>{c.title}</h3>
          <p>{c.description}</p>
          <p className="expected">
            Expected flags: {c.expected_flags.length > 0 ? c.expected_flags.join(', ').toUpperCase() : 'none (clean control)'}
          </p>
          <details>
            <summary style={{ cursor: 'pointer', color: 'var(--muted)' }}>Preview texts</summary>
            <p><strong>Source ({c.source_lang}):</strong> <span dir="auto">{c.source_text}</span></p>
            <p><strong>Draft ({c.draft_lang}):</strong> <span dir="auto">{c.draft_text}</span></p>
          </details>
          <div style={{ marginTop: '0.75rem' }}>
            <button className="btn" onClick={() => load(c)} disabled={runningId === c.id}>
              {runningId === c.id ? 'Analyzing…' : 'Load & analyze →'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
