/**
 * sections/graphcompile.js — Configure and compile the review graph.
 * Layout:
 *   1. Config compilata (read-only, current state)
 *   2. Nuova configurazione (form, pre-filled with current or defaults)
 */

import { listModels, compileGraph, getGraphConfig } from '../api.js';

const AGENT_LABELS = {
  soundness_reviewer:    '🔬 Soundness Reviewer',
  presentation_reviewer: '🎨 Presentation Reviewer',
  contribution_reviewer: '📐 Contribution Reviewer',
  meta_reviewer:         '📋 Meta Reviewer',
  author_agent:          '✍️  Author Agent',
};

const AGENT_NAMES = Object.keys(AGENT_LABELS);
const DEFAULT_MODEL = 'mock';
const DEFAULT_TEMP  = 0.7;

// ---------------------------------------------------------------------------
// render
// ---------------------------------------------------------------------------

export function render() {
  const el = document.createElement('div');
  el.className = 'section';
  el.innerHTML = `
    <h2 class="section__title">Graph Compile</h2>
    <p class="section__desc">Visualizza la configurazione attiva e compilane una nuova.</p>

    <!-- 1. Config compilata corrente -->
    <div class="gr-card" id="gc-current-card">
      <div class="gr-card-title">Config compilata</div>
      <div id="gc-current-body">
        <p class="muted">Caricamento…</p>
      </div>
    </div>

    <!-- 2. Nuova configurazione -->
    <div class="gr-card">
      <div class="gr-card-title">Nuova configurazione</div>

      <div class="gr-globals">
        <div class="form-group form-group--inline">
          <label class="form-label">Max rounds</label>
          <input id="gc-max-rounds" type="number" class="form-input" value="2" min="1" max="5" />
        </div>
      </div>

      <div class="gr-agents-table">
        <div class="gr-agents-header">
          <span>Agente</span><span>Modello</span><span>Temp</span>
        </div>
        <div id="gc-agents-rows"></div>
      </div>

      <div class="gr-card-footer">
        <button id="gc-compile-btn" class="btn btn--secondary" disabled>⚙ Compila</button>
        <span id="gc-status" class="gr-status"></span>
      </div>
      <div id="gc-error" class="error-msg" hidden></div>
    </div>
  `;
  return el;
}

// ---------------------------------------------------------------------------
// mount
// ---------------------------------------------------------------------------

export async function mount(el) {
  const currentBody = el.querySelector('#gc-current-body');
  const agentRows   = el.querySelector('#gc-agents-rows');
  const maxRoundsEl = el.querySelector('#gc-max-rounds');
  const compileBtn  = el.querySelector('#gc-compile-btn');
  const status      = el.querySelector('#gc-status');
  const errorDiv    = el.querySelector('#gc-error');

  // Load models + current config in parallel
  let models = [], currentConfig = null;
  try {
    [models, currentConfig] = await Promise.all([listModels(), getGraphConfig()]);
  } catch (e) {
    showError(errorDiv, `Errore caricamento: ${e.message}`);
    currentBody.innerHTML = '<p class="muted">Non disponibile.</p>';
    return;
  }

  // 1. Render current compiled config
  renderCompiledConfig(currentBody, currentConfig);

  // 2. Pre-fill new config form with current config (or defaults)
  const prefill = currentConfig || defaultConfig();
  maxRoundsEl.value = prefill.max_rounds ?? 2;

  agentRows.innerHTML = AGENT_NAMES.map(name => {
    const existing = prefill.agents?.find(a => a.agent_name === name);
    const model    = existing?.model       ?? DEFAULT_MODEL;
    const temp     = existing?.temperature ?? DEFAULT_TEMP;
    return `
      <div class="gr-agent-row" data-agent="${name}">
        <span class="gr-agent-name">${AGENT_LABELS[name]}</span>
        <select class="form-select gr-model-sel">
          ${models.map(m => `<option value="${m}" ${m === model ? 'selected' : ''}>${m}</option>`).join('')}
        </select>
        <input type="number" class="form-input gr-temp-inp"
               value="${temp}" min="0" max="2" step="0.1" />
      </div>
    `;
  }).join('');

  compileBtn.disabled = false;

  // Compile
  compileBtn.addEventListener('click', async () => {
    hideError(errorDiv);
    compileBtn.disabled = true;
    status.textContent = '⏳ Compilazione…';
    status.className = 'gr-status';

    const agentConfigs = AGENT_NAMES.map(name => {
      const row = agentRows.querySelector(`[data-agent="${name}"]`);
      return {
        agent_name:  name,
        model:       row.querySelector('.gr-model-sel').value,
        temperature: parseFloat(row.querySelector('.gr-temp-inp').value),
      };
    });

    const newConfig = {
      agents:     agentConfigs,
      max_rounds: parseInt(maxRoundsEl.value, 10),
    };

    try {
      await compileGraph(newConfig);
      status.textContent = '✅ Grafo compilato';
      status.className = 'gr-status gr-status--ok';
      // Refresh the "compiled" card with the new config
      renderCompiledConfig(currentBody, newConfig);
    } catch (e) {
      status.textContent = '';
      showError(errorDiv, e.message);
    } finally {
      compileBtn.disabled = false;
    }
  });
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderCompiledConfig(container, config) {
  if (!config) {
    container.innerHTML = `<p class="gr-no-config">Nessun grafo compilato.</p>`;
    return;
  }
  const agents    = config.agents || [];
  const maxRounds = config.max_rounds ?? '?';
  const rows = agents.map(a => `
    <tr>
      <td>${AGENT_LABELS[a.agent_name] || a.agent_name}</td>
      <td><code>${a.model}</code></td>
      <td>${a.temperature}</td>
    </tr>
  `).join('');
  container.innerHTML = `
    <p class="gr-config-meta">Max rounds: <strong>${maxRounds}</strong></p>
    <table class="gr-config-table">
      <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function defaultConfig() {
  return {
    max_rounds: 2,
    agents: AGENT_NAMES.map(name => ({
      agent_name:  name,
      model:       DEFAULT_MODEL,
      temperature: DEFAULT_TEMP,
    })),
  };
}

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
