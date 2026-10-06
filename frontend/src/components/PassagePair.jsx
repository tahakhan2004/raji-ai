import React from 'react';
import { FlagCard, HighlightedText } from './FlagCard';

/** One aligned source/draft pair with its flag cards. */
export function PassagePair({ pair, resolutions, onResolve, onComment }) {
  const srcMarks = pair.flags
    .filter((f) => f.source_span)
    .map((f) => ({ span: f.source_span, cls: `hl-${f.type}` }));
  const draftMarks = pair.flags
    .filter((f) => f.draft_span)
    .map((f) => ({ span: f.draft_span, cls: `hl-${f.type}` }));

  if (pair.status === 'unchecked') {
    return (
      <div className="card pair unchecked">
        <div className="pair-head">
          <strong>Pair {pair.index + 1} — UNCHECKED</strong>
        </div>
        <p style={{ marginTop: 0 }}>
          These sentences could not be confidently aligned by meaning, so no
          automated checks were run on them. <strong>Nothing here is approved</strong> —
          please review manually.
        </p>
        <div className="grid-2">
          <div className="sentence">
            <span className="label">Source</span>
            <HighlightedText text={pair.source_text} spans={[]} />
          </div>
          <div className="sentence">
            <span className="label">Draft</span>
            <HighlightedText text={pair.draft_text} spans={[]} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card pair">
      <div className="pair-head">
        <strong>Pair {pair.index + 1}</strong>
        <span className="sim">alignment similarity: {pair.similarity}</span>
      </div>
      <div className="grid-2">
        <div className="sentence">
          <span className="label">Source</span>
          <HighlightedText text={pair.source_text} marks={srcMarks} />
        </div>
        <div className="sentence">
          <span className="label">Draft</span>
          <HighlightedText text={pair.draft_text} marks={draftMarks} />
        </div>
      </div>
      {pair.flags.length === 0 ? (
        <p style={{ color: 'var(--green)' }}>✓ No risky changes detected in this pair.</p>
      ) : (
        pair.flags.map((flag) => (
          <FlagCard
            key={flag.id}
            flag={flag}
            resolution={resolutions[flag.id]}
            onResolve={onResolve}
            onComment={onComment}
          />
        ))
      )}
    </div>
  );
}
