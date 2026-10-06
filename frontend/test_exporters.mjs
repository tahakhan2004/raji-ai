// Smoke test for the export builders (run: node test_exporters.mjs).
// Uses a realistic analysis payload mirroring the backend's /api/analyze shape.
import assert from 'node:assert';
import {
  buildAuditCsv,
  buildAuditJson,
  buildCorrectedText,
  resolutionState,
} from './src/exporters.js';

const analysis = {
  meta: { aligner: 'tfidf-fallback', total_flags: 2 },
  pairs: [
    {
      index: 0,
      status: 'checked',
      similarity: 0.9,
      source_text: 'Allah has 99 names.',
      draft_text: 'Allah has 98 names.',
      flags: [
        {
          id: 'p0-numbers-0', type: 'numbers', severity: 'high',
          source_span: '99', draft_span: '98',
          evidence: "Numeric value differs: source has 99; draft has 98. Reviewer to decide.",
          status: 'open',
        },
      ],
    },
    {
      index: 1,
      status: 'checked',
      similarity: 0.95,
      source_text: 'Narrated by Abu Hurairah.',
      draft_text: 'It was narrated.',
      flags: [
        {
          id: 'p1-names-0', type: 'names', severity: 'medium',
          source_span: 'abu', draft_span: '',
          evidence: 'Distinctive token(s) present in the source but absent from the draft. Reviewer to decide.',
          status: 'open',
        },
      ],
    },
    {
      index: 2, status: 'unchecked', similarity: 0.0,
      source_text: 'Unaligned source.', draft_text: '', flags: [],
    },
  ],
};

const resolutions = {
  'p0-numbers-0': { state: 'confirmed', comment: 'Real error, fix to 99.', reviewedAt: '2026-10-01T12:00:00Z' },
  'p1-names-0': { state: 'false_alarm', comment: '', reviewedAt: '2026-10-01T12:01:00Z' },
};

// resolutionState: tri-state + open default
assert.equal(resolutionState(resolutions, 'p0-numbers-0'), 'confirmed');
assert.equal(resolutionState(resolutions, 'missing-id'), 'open');
assert.equal(resolutionState({}, 'p0-numbers-0'), 'open');

// Corrected text: confirmed annotated, false alarm clean, unchecked marked
const txt = buildCorrectedText(analysis, resolutions);
assert.ok(txt.includes('CONFIRMED ISSUE'), 'confirmed flag must be annotated');
assert.ok(txt.includes('98 \u27E6'), 'annotation inserted after the draft span');
assert.ok(!txt.includes('p1-names-0'), 'false alarm must leave text clean');
assert.ok(txt.includes('UNCHECKED'), 'unchecked pair must be marked');

// Audit JSON: every flag carries resolution + comment + timestamp
const audit = JSON.parse(buildAuditJson(analysis, resolutions, { sourceLang: 'en', draftLang: 'en' }, '2026-10-01T12:05:00Z'));
assert.equal(audit.tool, 'RajiAI');
assert.equal(audit.exported_at, '2026-10-01T12:05:00Z');
const f0 = audit.pairs[0].flags[0];
assert.equal(f0.resolution, 'confirmed');
assert.equal(f0.reviewer_comment, 'Real error, fix to 99.');
assert.equal(f0.reviewed_at, '2026-10-01T12:00:00Z');
assert.equal(audit.pairs[1].flags[0].resolution, 'false_alarm');

// Audit CSV: header + one row per flag, quoted, with all fields
const csv = buildAuditCsv(analysis, resolutions);
const lines = csv.split('\n');
assert.equal(lines.length, 3, 'header + 2 flag rows');
assert.ok(lines[0].startsWith('"flag_id","pair_index"'), 'header present');
assert.ok(lines[1].includes('"confirmed"'), 'tri-state recorded in CSV');
assert.ok(lines[1].includes('"Real error, fix to 99."'), 'comment recorded in CSV');
assert.ok(lines[2].includes('"false_alarm"'), 'false alarm recorded in CSV');

console.log('ALL EXPORTER TESTS PASSED');
