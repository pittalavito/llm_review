// docs/js/data.js — Fetch + transform review runs from GitHub raw content.
//
// Configuration is read from <meta name="gh-*"> tags in index.html so it can
// be updated without rebuilding the JS bundle.
//
// Strategy:
//   1. Fetch <results-path>/<index-file> for the file listing (no rate limit).
//   2. Fetch each JSON file in parallel from raw.githubusercontent.com.
//   3. Transform the raw record into the shape consumed by app.js.

// ─── Config from <meta> tags ──────────────────────────
function meta(name, fallback = '') {
  const el = document.querySelector(`meta[name="${name}"]`);
  return (el && el.content) || fallback;
}

const OWNER         = meta('gh-owner',         'pittalavito');
const REPO          = meta('gh-repo',          'llm_review');
const BRANCH        = meta('gh-branch',        'main');
const RESULTS_PATH  = meta('gh-results-path',  'resource/results');
const INDEX_FILE    = meta('gh-index-file',    'index.json');

const RAW_BASE = `https://raw.githubusercontent.com/${OWNER}/${REPO}/${BRANCH}/${RESULTS_PATH}`;

// ─── Helpers ──────────────────────────────────────────
function truncate(str, max = 1500) {
  if (typeof str !== 'string') return str;
  return str.length > max ? str.slice(0, max) + '…' : str;
}

function stripPayload(payload) {
  if (!payload || typeof payload !== 'object') return payload;
  const out = {};
  for (const [k, v] of Object.entries(payload)) {
    out[k] = typeof v === 'string' ? truncate(v) : v;
  }
  return out;
}

/**
 * Reviews come as an array of JSON strings, each with shape:
 *   { agent, payload, input_message, context_used }
 * Parse them defensively.
 */
function parseReviews(rawReviews) {
  if (!Array.isArray(rawReviews)) return [];
  const out = [];
  for (const item of rawReviews) {
    let obj = item;
    if (typeof item === 'string') {
      try { obj = JSON.parse(item); }
      catch { out.push({ agent: 'unknown', payload: { raw: truncate(item) } }); continue; }
    }
    if (!obj || typeof obj !== 'object') continue;
    out.push({
      agent:         obj.agent ?? obj.agent_name ?? 'unknown',
      payload:       stripPayload(obj.payload || {}),
      input_message: obj.input_message ?? '',
      context_used:  truncate(obj.context_used ?? '', 2500),
    });
  }
  return out;
}

/**
 * graph_config.agents is an array of:
 *   { agent_name, model, temperature, reviewer_persona?, area_chair_style? }
 */
function normalizeGraphConfig(gc) {
  if (!gc || typeof gc !== 'object') return { agents: [], max_rounds: null };
  const agents = Array.isArray(gc.agents) ? gc.agents : [];
  return {
    max_rounds: gc.max_rounds ?? null,
    agents: agents.map(a => ({
      agent_name:       a.agent_name ?? 'unknown',
      model:            a.model ?? '',
      temperature:      a.temperature ?? null,
      reviewer_persona: a.reviewer_persona ?? null,
      area_chair_style: a.area_chair_style ?? null,
    })),
  };
}

function transformRun(data, sourceFile) {
  return {
    source_file:         sourceFile,
    run_id:              data.run_id ?? sourceFile.replace(/\.json$/i, ''),
    timestamp:           data.timestamp ?? '',
    paper_path:          data.paper_path ?? '',
    decision:            (data.area_chair_response && data.area_chair_response.decision)
                          ?? data.decision
                          ?? '',
    total_rounds:        data.total_rounds ?? 1,
    graph_config:        normalizeGraphConfig(data.graph_config),
    reviews:             parseReviews(data.reviews),
    meta_review:         data.meta_review ?? null,
    area_chair_response: data.area_chair_response ?? null,
    author_response:     data.author_response ?? null,
    retrieval_metadata:  data.retrieval_metadata ?? null,
  };
}

// ─── Public API ───────────────────────────────────────

async function fetchIndex() {
  const url = `${RAW_BASE}/${INDEX_FILE}`;
  const res = await fetch(url, { cache: 'no-cache' });
  if (!res.ok) {
    throw new Error(`Cannot fetch index (${res.status}): ${url}`);
  }
  const data = await res.json();
  const files = Array.isArray(data) ? data : data.files;
  if (!Array.isArray(files)) {
    throw new Error(`Malformed index.json at ${url}`);
  }
  return files.filter(f => typeof f === 'string' && f.endsWith('.json'));
}

export async function loadRuns() {
  const CACHE_KEY = `llm_review_runs::${OWNER}/${REPO}@${BRANCH}`;
  const CACHE_TTL = 5 * 60 * 1000;

  const cached = sessionStorage.getItem(CACHE_KEY);
  if (cached) {
    try {
      const { ts, data } = JSON.parse(cached);
      if (Date.now() - ts < CACHE_TTL) return data;
    } catch { /* ignore */ }
  }

  const files = await fetchIndex();

  const runs = (await Promise.all(files.map(async f => {
    const url = `${RAW_BASE}/${f}`;
    const res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) {
      console.warn(`Skipping ${f}: HTTP ${res.status}`);
      return null;
    }
    try {
      return transformRun(await res.json(), f);
    } catch (e) {
      console.warn(`Skipping ${f}: parse error`, e);
      return null;
    }
  }))).filter(Boolean);

  runs.sort((a, b) => (b.timestamp || '').localeCompare(a.timestamp || ''));

  try { sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data: runs })); }
  catch { /* quota exceeded — ignore */ }

  return runs;
}

export const _config = { OWNER, REPO, BRANCH, RESULTS_PATH, INDEX_FILE, RAW_BASE };
