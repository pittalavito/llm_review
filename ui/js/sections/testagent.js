/**
 * sections/testagent.js — Test Agent section.
 */

import { getTestAgent, postTestAgent } from '../api.js';

/** @returns {HTMLElement} */
export function render() {
  const el = document.createElement('section');
  el.className = 'test-agent-section';
  el.innerHTML = `
    <h2 class="section-title">Test Agent</h2>
    <p class="section-description">Run GET and POST calls on /test-agent endpoint.</p>

    <div class="test-agent-actions">
      <button class="btn btn--primary" id="test-agent-get-btn" type="button">GET /test-agent</button>
      <button class="btn" id="test-agent-post-btn" type="button">POST /test-agent</button>
    </div>

    <div class="card test-agent-response" id="test-agent-response" hidden>
      <div class="card__header">
        <span class="card__title" id="test-agent-response-title">Response</span>
      </div>
      <pre class="card__body" id="test-agent-response-body"></pre>
    </div>
  `;
  return el;
}

/** @param {HTMLElement} container */
export function mount(container) {
  const getBtn = container.querySelector('#test-agent-get-btn');
  const postBtn = container.querySelector('#test-agent-post-btn');
  const responseCard = container.querySelector('#test-agent-response');
  const responseTitle = container.querySelector('#test-agent-response-title');
  const responseBody = container.querySelector('#test-agent-response-body');

  function setLoading(loading) {
    getBtn.disabled = loading;
    postBtn.disabled = loading;
  }

  function showResponse(title, data) {
    responseTitle.textContent = title;
    responseBody.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    responseCard.hidden = false;
  }

  getBtn.addEventListener('click', async () => {
    setLoading(true);
    try {
      const data = await getTestAgent();
      showResponse('GET /test-agent', data);
    } catch (err) {
      showResponse('GET /test-agent error', err.message);
    } finally {
      setLoading(false);
    }
  });

  postBtn.addEventListener('click', async () => {
    setLoading(true);
    try {
      const data = await postTestAgent();
      showResponse('POST /test-agent', data);
    } catch (err) {
      showResponse('POST /test-agent error', err.message);
    } finally {
      setLoading(false);
    }
  });
}
