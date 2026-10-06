/**
 * Pure export builders for RajiAI (no JSX, no DOM) — testable with plain node.
 *
 * RajiAI never rewrites the translation (no guessing). The "corrected text"
 * is the draft with reviewer decisions applied as inline annotations:
 * confirmed issues are marked for the translator to fix, open / needs-review
 * items stay visibly pending, false alarms are left clean.
 *
 * Tri-state resolution per flag: 'confirmed' | 'false_alarm' | 'needs_review'.
 * A flag with no resolution entry is 'open' — never auto-resolved.
 */

export function resolutionState(resolutions, flagId) {
  return (resolutions && resolutions[flagId] && resolutions[flagId].state) || 'open';
}

export function buildCorrectedText(analysis, resolutions) {
  const lines = [];
  for (const pair of analysis.pairs) {
    if (pair.status === 'unchecked') {
      if (pair.source_text) lines.push(`\u27E6UNCHECKED \u2014 no automated checks run\u27E7 ${pair.source_text}`);
      if (pair.draft_text) lines.push(`\u27E6UNCHECKED \u2014 no automated checks run\u27E7 ${pair.draft_text}`);
      continue;
    }
    let sentence = pair.draft_text;
    for (const flag of pair.flags) {
      const state = resolutionState(resolutions, flag.id);
      if (state === 'false_alarm') continue;
      const tag =
        state === 'confirmed' ? '\u26A0 CONFIRMED ISSUE'
        : state === 'needs_review' ? '? NEEDS FURTHER REVIEW'
        : '\u2026 OPEN \u2014 not yet reviewed';
      const note = ` \u27E6${tag} \u2014 ${flag.type.toUpperCase()}: ${flag.evidence}\u27E7`;
      if (flag.draft_span) {
        const idx = sentence.toLowerCase().indexOf(flag.draft_span.toLowerCase());
        if (idx !== -1) {
          const cut = idx + flag.draft_span.length;
          sentence = sentence.slice(0, cut) + note + sentence.slice(cut);
          continue;
        }
      }
      sentence += note;
    }
    lines.push(sentence);
  }
  return lines.join('\n');
}

export function buildAuditJson(analysis, resolutions, texts, exportedAt) {
  const stamp = exportedAt || new Date().toISOString();
  return JSON.stringify({
    tool: 'RajiAI',
    exported_at: stamp,
    note: 'Flags what changed. The expert decides. RajiAI issues evidence, never verdicts.',
    source_lang: (texts && texts.sourceLang) || null,
    draft_lang: (texts && texts.draftLang) || null,
    meta: analysis.meta,
    pairs: analysis.pairs.map((pair) => ({
      index: pair.index,
      status: pair.status,
      similarity: pair.similarity,
      source_text: pair.source_text,
      draft_text: pair.draft_text,
      flags: pair.flags.map((flag) => {
        const r = (resolutions && resolutions[flag.id]) || {};
        return {
          ...flag,
          resolution: r.state || 'open',
          reviewer_comment: r.comment || '',
          reviewed_at: r.reviewedAt || null,
        };
      }),
    })),
  }, null, 2);
}

export function csvCell(value) {
  const s = String(value ?? '');
  return `"${s.replace(/"/g, '""')}"`;
}

export function buildAuditCsv(analysis, resolutions) {
  const header = ['flag_id', 'pair_index', 'type', 'severity', 'source_span', 'draft_span',
    'evidence', 'status', 'reviewer_comment', 'reviewed_at'];
  const rows = [header.map(csvCell).join(',')];
  for (const pair of analysis.pairs) {
    for (const flag of pair.flags) {
      const r = (resolutions && resolutions[flag.id]) || {};
      rows.push([
        flag.id, pair.index, flag.type, flag.severity,
        flag.source_span, flag.draft_span, flag.evidence,
        r.state || 'open', r.comment || '', r.reviewedAt || '',
      ].map(csvCell).join(','));
    }
  }
  return rows.join('\n');
}
