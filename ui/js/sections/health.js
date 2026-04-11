/**
 * sections/health.js — Health Check section.
 *
 * render() — builds and returns the DOM subtree (no side effects).
 * mount(el) — attaches event listeners and business logic.
 */

import { checkHealth } from '../api.js';

/** @returns {HTMLElement} */
export function render() {
  const el = document.createElement('div');
  el.className = 'health-section';
  el.innerHTML = `
    <h2 class="section-title">Health Check</h2>
    <p class="section-description">Verifica lo stato del servizio backend.</p>

    <button class="btn btn--primary" id="health-btn">
      <span>🔍</span> Check Health
    </button>

    <div class="health-response" id="health-response" hidden>
      <div class="card">
        <div class="card__header">
          <span class="badge" id="health-badge"></span>
          <span class="card__title">Response</span>
        </div>
        <pre class="card__body" id="health-json"></pre>
      </div>
    </div>
  `;
  return el;
}

/** @param {HTMLElement} container */
export function mount(container) {
  const btn      = container.querySelector('#health-btn');
  const response = container.querySelector('#health-response');
  const jsonEl   = container.querySelector('#health-json');
  const badge    = container.querySelector('#health-badge');

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Checking…';
    response.hidden = true;

    try {
      const data = await checkHealth();
      jsonEl.textContent = JSON.stringify(data, null, 2);
      badge.textContent  = '✅ OK';
      badge.className    = 'badge badge--success';
    } catch (err) {
      jsonEl.textContent = err.message;
      badge.textContent  = '❌ Error';
      badge.className    = 'badge badge--error';
    } finally {
      response.hidden  = false;
      btn.disabled     = false;
      btn.innerHTML    = '<span>🔍</span> Check Health';
    }
  });
}
