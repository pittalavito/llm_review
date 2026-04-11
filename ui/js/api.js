const BASE_URL = '';

/**
 * GET /health
 * @returns {Promise<{ status: string, version: string }>}
 */
export async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}

/**
 * GET /models
 * @returns {Promise<string[]>}
 */
export async function listModels() {
  const res = await fetch(`${BASE_URL}/models`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}
/**
 * POST /test-llm
 * @param {string} message
 * @param {string} [llm_model]
 * @returns {Promise<{ response: string }>}
 */
export async function testLlm(message, llm_model = 'mock') {
  const body = { message, llm_model };
  const res = await fetch(`${BASE_URL}/test-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}

/**
 * GET /test-agent
 * @returns {Promise<string[]>}
 */
export async function getTestAgent() {
  const res = await fetch(`${BASE_URL}/test-agent`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}

/**
 * POST /test-agent
 * @returns {Promise<string>}
 */
export async function postTestAgent() {
  const res = await fetch(`${BASE_URL}/test-agent`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}
