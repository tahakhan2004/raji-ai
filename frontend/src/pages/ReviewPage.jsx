import React from 'react';
import { PassagePair } from '../components/PassagePair';

/** Step 2 — expert review of aligned pairs and tri-state flag resolution. */
export function ReviewPage({ analysis, resolutions, onResolve, onComment }) {
  if (!analysis) {
    return (
      <div className="card">
        <h2><span className="step-n">02</span>Expert review</h2>
        <p>No analysis yet. Run an analysis from the <strong>Analyze</strong> tab or load a demo case first.</p>
      </div>
    );
  }

  const allFlags = analysis.pairs.flatMap((p) => p.flags);
  const openCount = allFlags.filter((f) => !resolutions[f.id]?.state).length;
  const unchecked = analysis.pairs.filter((p) => p.status === 'unchecked').length;

  return (
    <div>
      <div className="card">
        <h2><span className="step-n">02</span>Expert review</h2>
        <div className="kpi-row">
          <div className="kpi"><div className="num">{analysis.pairs.length}</div><div className="lbl">pairs</div></div>
          <div className="kpi"><div className="num">{allFlags.length}</div><div className="lbl">flags</div></div>
          <div className="kpi"><div className="num" style={{ color: '#92400e' }}>{openCount}</div><div className="lbl">open</div></div>
          <div className="kpi"><div className="num">{unchecked}</div><div className="lbl">unchecked</div></div>
          <div className="kpi"><div className="num" style={{ color: 'var(--muted)', fontSize: '1rem' }}>{analysis.meta.aligner}</div><div className="lbl">aligner</div></div>
        </div>
        {(openCount > 0 || unchecked > 0) && (
          <div className="open-banner">
            ⚠ <strong>{openCount} flag(s) still open{unchecked > 0 && `, ${unchecked} pair(s) unchecked`}</strong> —
            nothing is auto-resolved or auto-approved. Each flag needs your decision:
            confirm it as an issue, mark it a false alarm, or send it for further review.
          </div>
        )}
      </div>

      {analysis.pairs.map((pair) => (
        <PassagePair key={pair.index} pair={pair} resolutions={resolutions}
          onResolve={onResolve} onComment={onComment} />
      ))}
    </div>
  );
}
