// Minimal API client. In dev, Vite proxies /api to localhost:8000.
// For a production build, set VITE_API_URL to the backend origin.
const BASE = import.meta.env.VITE_API_URL || '';

export async function analyzeTexts(payload) {
  const res = await fetch(`${BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Analysis failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export async function fetchDemoCases() {
  const res = await fetch(`${BASE}/api/demo-cases`);
  if (!res.ok) throw new Error(`Could not load demo cases (${res.status})`);
  const data = await res.json();
  return data.cases;
}

export async function fetchHealth() {
  const res = await fetch(`${BASE}/api/health`);
  if (!res.ok) throw new Error('Backend unreachable');
  return res.json();
}
