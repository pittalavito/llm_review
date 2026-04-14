const BASE_URL = '';

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
 * GET /health
 * @returns {Promise<{ status: string, version: string }>}
 */
export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /models
 * @returns {Promise<string[]>}
 */
export async function listModels() {
  const res = await fetch(`${BASE_URL}/models`);
  await throwForResponse(res);
  return res.json();
}
/**
 * POST /test-llm
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
 * GET /agents
 * @returns {Promise<string[]>}
 */
export async function listAgents() {
  const res = await fetch(`${BASE_URL}/agents`);
  await throwForResponse(res);
  return res.json();
}

/**
 * POST /agents
 * @param {{ name: string, model: string, temperature: number, message: string }} payload
 * @returns {Promise<string>}
 */
export async function testAgent(payload) {
  const res = await fetch(`${BASE_URL}/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  await throwForResponse(res);
  return res.json();
}

/**
 * GET /graph-config
 * @returns {Promise<null | {
 *   methodology_reviewer_agent: string,
 *   methodology_reviewer_model: string,
 *   methodology_reviewer_temperature: number,
 *   max_iterations: number,
 *   max_tokens: number | null,
 * }>}
 */
export async function getGraphConfig() {
  const res = await fetch(`${BASE_URL}/graph-config`);
  await throwForResponse(res);
  return res.json();
}

/**
 * PUT /graph-config
 * @param {{
 *   methodology_reviewer_agent: string,
 *   methodology_reviewer_model: string,
 *   methodology_reviewer_temperature: number,
 *   max_iterations: number,
 *   max_tokens: number | null,
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
 * POST /graph-run
 * @param {{ paper: string }} payload
 * @returns {Promise<{ reviews: string[], raw_result: Record<string, unknown> }>}
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
