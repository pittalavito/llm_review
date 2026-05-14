// docs/js/data.js — Dynamic fetch from GitHub raw content
const OWNER = 'pittalavito';
const REPO = 'llm_review';
const BRANCH = 'main';
const RESULTS_PATH = 'resource/results';

const API_BASE = `https://api.github.com/repos/${OWNER}/${REPO}/contents/${RESULTS_PATH}?ref=${BRANCH}`;
const RAW_BASE = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/${RESULTS_PATH}`;

function stripPayload(payload) {
  if (typeof payload === 'string') {
    try { payload = JSON.parse(payload); }
    catch { return { raw: payload.slice(0, 800) }; }
  }
  if (!payload || typeof payload !== 'object') return payload;
  const stripped = {};
  for (const [k, v] of Object.entries(payload)) {
    if (['context_used', 'prompt_trace', 'runtime_trace', 'rendered'].includes(k)) continue;
    if (typeof v === 'string' && v.length > 1200) {
      stripped[k] = v.slice(0, 1200) + '\u2026';
    } else {
      stripped[k] = v;
    }
  }
  return stripped;
}

function transformRun(data) {
  return {
    run_id: data.run_id ?? '',
    timestamp: data.timestamp ?? '',
    paper_path: data.paper_path ?? '',
    decision: data.decision ?? '',
    total_rounds: data.total_rounds ?? 0,
    graph_config: data.graph_config ?? {},
    reviews: (data.reviews ?? []).map(r => ({
      round: r.round ?? 1,
      agent_name: r.agent_name ?? '',
      payload: stripPayload(r.payload),
    })),
  };
}

/**
 * Fetch all review run JSONs from the GitHub repository.
 * Uses sessionStorage cache (5 min TTL) to avoid hitting API rate limits.
 */
export async function loadRuns() {
  const CACHE_KEY = 'llm_review_runs';
  const CACHE_TTL = 5 * 60 * 1000;

  const cached = sessionStorage.getItem(CACHE_KEY);
  if (cached) {
    const { ts, data } = JSON.parse(cached);
    if (Date.now() - ts < CACHE_TTL) return data;
  }

  // 1. List files via GitHub Contents API
  const listRes = await fetch(API_BASE);
  if (!listRes.ok) throw new Error(`GitHub API ${listRes.status}`);
  const files = await listRes.json();
  const jsonFiles = files.filter(f => f.name.endsWith('.json'));

  // 2. Fetch each JSON from raw.githubusercontent.com in parallel
  const runs = (await Promise.all(
    jsonFiles.map(async f => {
      const res = await fetch(`${RAW_BASE}/${f.name}`);
      if (!res.ok) return null;
      return transformRun(await res.json());
    })
  )).filter(Boolean);

  runs.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));

  // Cache
  try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: runs })); }
  catch { /* quota exceeded — ignore */ }

  return runs;
}
