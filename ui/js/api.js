const BASE_URL = '/dev';

async function readJsonOrText(response) {
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
}

async function throwForResponse(response) {
  if (response.ok) {
    return;
  }

  const payload = await readJsonOrText(response);
  const detail = typeof payload === 'string'
    ? payload
    : payload?.detail || JSON.stringify(payload);
  throw new Error(detail || `HTTP ${response.status} ${response.statusText}`);
}

/**
 * GET /dev/health
 * @returns {Promise<{ status: string, version: string }>}
 */
export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/models
 * @returns {Promise<string[]>}
 */
export async function listModels() {
  const res = await fetch(`${BASE_URL}/models`);
  await throwForResponse(res);
  return res.json();
}
/**
 * POST /dev/test-llm
 * @param {string} message
 * @param {string} model
 * @param {number} [temperature]
 * @returns {Promise<{ response: string }>}
 */
export async function testLlm(message, model, temperature = 1) {
  const body = { message, model, temperature };
  const res = await fetch(`${BASE_URL}/test-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/agents
 * @returns {Promise<string[]>}
 */
export async function listAgents() {
  const res = await fetch(`${BASE_URL}/agents`);
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/agents
 * @param {{ name: string, model: string, temperature: number, message: string }} payload
 * @returns {Promise<{ agent: string, payload: Record<string, unknown> }>}
 */
export async function testAgent(payload) {
  const res = await fetch(`${BASE_URL}/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await readJsonOrText(res);
    const detail = typeof body === 'string' ? body : body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.error || JSON.stringify(detail) || `HTTP ${res.status} ${res.statusText}`;
    const err = new Error(message);
    err.llmRawOutput = typeof detail === 'object' && detail !== null ? (detail.llm_raw_output ?? null) : null;
    throw err;
  }
  return res.json();
}

/**
 * POST /dev/agents/prompt-preview
 * @param {{ name: string, message: string }} payload
 * @returns {Promise<{ agent: string, system_prompt: string, schema_instructions: string, message_section: string, full_prompt: string }>}
 */
export async function previewAgentPrompt(payload) {
  const res = await fetch(`${BASE_URL}/agents/prompt-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/papers
 * @returns {Promise<string[]>}
 */
export async function listPapers() {
  const res = await fetch(`${BASE_URL}/papers`);
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/papers/index
 * @param {{ paper_path: string, force_reindex?: boolean }} payload
 * @returns {Promise<Record<string, unknown>>}
 */
export async function indexPaper(payload) {
  const res = await fetch(`${BASE_URL}/papers/index`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/papers/indexed
 * @returns {Promise<string[]>}
 */
export async function listIndexedPapers() {
  const res = await fetch(`${BASE_URL}/papers/indexed`);
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/papers/indexed/detail?paper_path=…
 * @param {string} paperPath
 * @returns {Promise<Record<string, unknown>>}
 */
export async function getIndexedPaperDetail(paperPath) {
  const params = new URLSearchParams({ paper_path: paperPath });
  const res = await fetch(`${BASE_URL}/papers/indexed/detail?${params}`);
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/graph/compile
 * @param {object|null} graphConfig
 * @returns {Promise<{ status: string }>}
 */
export async function compileGraph(graphConfig = null) {
  const res = await fetch(`${BASE_URL}/graph/compile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(graphConfig),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/graph/run
 * @param {{ paper_path: string, rag_top_k?: number, force_reindex?: boolean, graph_config?: object }} payload
 * @returns {Promise<object>}
 */
export async function runGraph(payload) {
  const res = await fetch(`${BASE_URL}/graph/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/runs
 * @returns {Promise<Array<{ run_id: string, timestamp: string, paper_path: string, decision: string, total_rounds: number }>>}
 */
export async function listRuns() {
  const res = await fetch(`${BASE_URL}/runs`);
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/runs/{run_id}
 * @param {string} runId
 * @returns {Promise<object>}
 */
export async function getRun(runId) {
  const res = await fetch(`${BASE_URL}/runs/${encodeURIComponent(runId)}`);
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/agents/retrieval
 * @param {{ name: string, model: string, temperature: number, message: string, paper_path: string, top_k?: number }} payload
 * @returns {Promise<{ agent: string, payload: Record<string, unknown> }>}
 */
export async function testAgentWithRetrieval(payload) {
  const res = await fetch(`${BASE_URL}/agents/retrieval`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await readJsonOrText(res);
    const detail = typeof body === 'string' ? body : body?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.error || JSON.stringify(detail) || `HTTP ${res.status} ${res.statusText}`;
    const err = new Error(message);
    err.llmRawOutput = typeof detail === 'object' && detail !== null ? (detail.llm_raw_output ?? null) : null;
    throw err;
  }
  return res.json();
}
