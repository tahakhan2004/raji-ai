import React from 'react';
import { buildAuditCsv, buildAuditJson, buildCorrectedText, resolutionState } from '../exporters';

/**
 * Step 4 — export.
 * RajiAI never rewrites the translation (no guessing). The "corrected text"
 * is the draft with reviewer decisions applied as inline annotations:
 * confirmed issues are marked for the translator to fix, open / needs-review
 * items stay visibly pending, false alarms are left clean.
 * The audit log records every flag, its tri-state resolution, reviewer
 * comment, and timestamps — as JSON and CSV.
 */

function download(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function ExportPage({ analysis, resolutions, texts }) {
  if (!analysis) {
    return (
      <div className="card">
        <h2><span className="step-n">04</span>Export</h2>
        <p>No analysis yet. Run an analysis first.</p>
      </div>
    );
  }

  const allFlags = analysis.pairs.flatMap((p) => p.flags);
  const counts = { open: 0, confirmed: 0, false_alarm: 0, needs_review: 0 };
  for (const f of allFlags) counts[resolutionState(resolutions, f.id)] += 1;

  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');

  return (
    <div>
      <div className="card">
        <h2><span className="step-n">04</span>Export</h2>
        <div className="kpi-row">
          <div className="kpi"><div className="num" style={{ color: '#92400e' }}>{counts.open}</div><div className="lbl">open</div></div>
          <div className="kpi"><div className="num" style={{ color: 'var(--red)' }}>{counts.confirmed}</div><div className="lbl">confirmed</div></div>
          <div className="kpi"><div className="num">{counts.false_alarm}</div><div className="lbl">false alarm</div></div>
          <div className="kpi"><div className="num" style={{ color: 'var(--blue)' }}>{counts.needs_review}</div><div className="lbl">needs review</div></div>
        </div>
        {counts.open > 0 && (
          <div className="open-banner">
            ⚠ <strong>{counts.open} flag(s) were never reviewed.</strong> They are
            exported as <em>open</em> — nothing is silently approved or auto-resolved.
          </div>
        )}
        <p style={{ color: 'var(--muted)', fontSize: '0.92rem' }}>
          RajiAI does not rewrite translations. The “corrected text” below is your
          draft with reviewer decisions applied as inline annotations, so a
          translator knows exactly what to fix.
        </p>
        <div className="export-list">
          <button className="btn" onClick={() =>
            download(`raji-ai-corrected-${stamp}.txt`, buildCorrectedText(analysis, resolutions), 'text/plain')}>
            ⬇ Corrected text (.txt)
          </button>
          <button className="btn secondary" onClick={() =>
            download(`raji-ai-audit-${stamp}.json`, buildAuditJson(analysis, resolutions, texts), 'application/json')}>
            ⬇ Audit log (.json)
          </button>
          <button className="btn secondary" onClick={() =>
            download(`raji-ai-audit-${stamp}.csv`, buildAuditCsv(analysis, resolutions), 'text/csv')}>
            ⬇ Audit log (.csv)
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Preview — corrected text</h3>
        <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
          {buildCorrectedText(analysis, resolutions)}
        </pre>
      </div>
    </div>
  );
}
