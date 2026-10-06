import React from 'react';

/** Render text with each mark's first case-insensitive occurrence wrapped in <mark>. */
export function HighlightedText({ text, marks }) {
  if (!text) return <span style={{ color: '#9ca3af' }}>—</span>;
  let segments = [{ text, cls: null }];
  for (const { span, cls } of marks || []) {
    if (!span) continue;
    const next = [];
    for (const seg of segments) {
      if (seg.cls) { next.push(seg); continue; }
      const idx = seg.text.toLowerCase().indexOf(span.toLowerCase());
      if (idx === -1) { next.push(seg); continue; }
      if (idx > 0) next.push({ text: seg.text.slice(0, idx), cls: null });
      next.push({ text: seg.text.slice(idx, idx + span.length), cls });
      const rest = seg.text.slice(idx + span.length);
      if (rest) next.push({ text: rest, cls: null });
    }
    segments = next;
  }
  return (
    <span dir="auto">
      {segments.map((s, i) =>
        s.cls ? <mark key={i} className={s.cls}>{s.text}</mark>
              : <React.Fragment key={i}>{s.text}</React.Fragment>
      )}
    </span>
  );
}

const STATE_LABEL = {
  confirmed: 'Confirmed issue',
  false_alarm: 'False alarm',
  needs_review: 'Needs further review',
};

/** One flag card: type/severity badges, evidence, tri-state resolution, comment. */
export function FlagCard({ flag, resolution, onResolve, onComment }) {
  const state = resolution?.state; // undefined => still open
  const btnClass = (s, cls) => (state === s ? cls : '');

  return (
    <div className="flag-card">
      <div className="meta-row">
        <span className={`badge type-${flag.type}`}>{flag.type.toUpperCase()}</span>
        <span className={`badge sev-${flag.severity}`}>{flag.severity.toUpperCase()}</span>
        {state ? (
          <span className={`badge status-${state}`}>{STATE_LABEL[state]}</span>
        ) : (
          <span className="badge status-open">OPEN — awaiting review</span>
        )}
        <span className="fid">#{flag.id}</span>
      </div>

      <p className="evidence">{flag.evidence}</p>

      <div className="tri-state" role="group" aria-label={`Resolve flag ${flag.id}`}>
        <button className={btnClass('confirmed', 'sel-confirm')} onClick={() => onResolve(flag.id, 'confirmed')}>
          ✓ Confirm issue
        </button>
        <button className={btnClass('false_alarm', 'sel-false')} onClick={() => onResolve(flag.id, 'false_alarm')}>
          ✕ False alarm
        </button>
        <button className={btnClass('needs_review', 'sel-review')} onClick={() => onResolve(flag.id, 'needs_review')}>
          ? Needs further review
        </button>
      </div>

      <div className="comment-box">
        <textarea
          placeholder="Reviewer comment (optional) — recorded in the audit log…"
          value={resolution?.comment || ''}
          onChange={(e) => onComment(flag.id, e.target.value)}
        />
      </div>

      {resolution?.reviewedAt && (
        <div className="reviewed-at">
          {STATE_LABEL[state]} · {new Date(resolution.reviewedAt).toLocaleString()}
        </div>
      )}
      {!state && (
        <div className="reviewed-at" style={{ color: '#92400e' }}>
          Not yet reviewed — this flag stays open until you decide. Nothing is auto-resolved.
        </div>
      )}
    </div>
  );
}
