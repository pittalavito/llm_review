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
 * GET /dev/graph-config
 * @returns {Promise<null | {
 *   model: string,
 *   temperature: number,
 *   max_iterations: number,
 * }>}
 */
export async function getGraphConfig() {
  const res = await fetch(`${BASE_URL}/graph-config`);
  await throwForResponse(res);
  return res.json();
}

/**
 * PUT /dev/graph-config
 * @param {{
 *   model: string,
 *   temperature: number,
 *   max_iterations: number,
 * }} payload
 */
export async function putGraphConfig(payload) {
  const res = await fetch(`${BASE_URL}/graph-config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/graph-run
 * @param {{ paper: string }} payload
 * @returns {Promise<{
 *   reviews: Array<{ agent: string, payload: Record<string, unknown> }>,
 *   raw_result: Record<string, unknown>
 * }>}
 */
export async function runGraph(payload) {
  const res = await fetch(`${BASE_URL}/graph-run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/graph-run-file
 * @param {{ paper_path: string, top_k?: number, force_reindex?: boolean }} payload
 * @returns {Promise<{
 *   reviews: Array<{ agent: string, payload: Record<string, unknown> }>,
 *   raw_result: Record<string, unknown>,
 *   retrieval: {
 *     paper_path: string,
 *     index_status: string,
 *     chunk_count_total: number,
 *     chunk_count_retrieved: number,
 *     top_k: number,
 *   } | null,
 * }>}
 */
export async function runGraphFromFile(payload) {
  const res = await fetch(`${BASE_URL}/graph-run-file`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /dev/openreview/papers/search
 * @param {{ keyword: string, venue_id: string, limit: number }} payload
 * @returns {Promise<Array<{
 *   id: string,
 *   title: string,
 *   abstract: string,
 *   keywords: string[],
 *   venue: string,
 * }>>}
 */
export async function searchOpenReviewPapers(payload) {
  const res = await fetch(`${BASE_URL}/openreview/papers/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /dev/openreview/papers/{paperId}/summary
 * @param {string} paperId
 * @returns {Promise<{
 *   id: string,
 *   title: string,
 *   abstract: string,
 *   keywords: string[],
 *   venue: string,
 *   venueid: string,
 *   pdf_path: string,
 *   decision: string | null,
 *   num_reviews: number,
 *   review_summary: Array<{ rating: string, confidence: string, soundness: string }>,
 * }>}
 */
export async function getOpenReviewPaperSummary(paperId) {
  const res = await fetch(`${BASE_URL}/openreview/papers/${encodeURIComponent(paperId)}/summary`);
  await throwForResponse(res);
  return res.json();
}
