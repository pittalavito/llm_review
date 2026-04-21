/**
 * sections/graphcompile.js — Configure and compile the review graph.
 */

import { listModels, compileGraph, getGraphConfig } from '../api.js';

const AGENT_LABELS = {
  soundness_reviewer:    '🔬 Soundness Reviewer',
  presentation_reviewer: '🎨 Presentation Reviewer',
  contribution_reviewer: '📐 Contribution Reviewer',
  meta_reviewer:         '📋 Meta Reviewer',
  refinement_agent:      '✏️  Refinement Agent',
};

const AGENT_NAMES = Object.keys(AGENT_LABELS);

// ---------------------------------------------------------------------------
// render
// ---------------------------------------------------------------------------

export function render() {
  const el = document.createElement('div');
  el.className = 'section';
  el.innerHTML = `
    <h2 class="section__title">Graph Compile</h2>
    <p class="section__desc">Configura modello e temperatura per ogni agente e compila il grafo.</p>

    <div class="gr-card">
      <div class="gr-card-title">Configurazione agenti</div>

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
        <button id="gc-compile-btn" class="btn btn--secondary" disabled>⚙ Compila grafo</button>
        <span id="gc-status" class="gr-status"></span>
      </div>
      <div id="gc-error" class="error-msg" hidden></div>
    </div>

    <!-- Config compilata corrente -->
    <div class="gr-card" id="gc-current-card" hidden>
      <div class="gr-card-title">Config compilata</div>
      <div id="gc-current-body"></div>
    </div>
  `;
  return el;
}

// ---------------------------------------------------------------------------
// mount
// ---------------------------------------------------------------------------

export async function mount(el) {
  const agentRows  = el.querySelector('#gc-agents-rows');
  const compileBtn = el.querySelector('#gc-compile-btn');
  const status     = el.querySelector('#gc-status');
  const errorDiv   = el.querySelector('#gc-error');
  const currentCard = el.querySelector('#gc-current-card');
  const currentBody = el.querySelector('#gc-current-body');

  let models = [], currentConfig = null;
  try {
    [models, currentConfig] = await Promise.all([listModels(), getGraphConfig()]);
  } catch (e) {
    showError(errorDiv, `Errore caricamento: ${e.message}`);
    return;
  }

  // Build agent rows
  agentRows.innerHTML = AGENT_NAMES.map(name => `
    <div class="gr-agent-row" data-agent="${name}">
      <span class="gr-agent-name">${AGENT_LABELS[name]}</span>
      <select class="form-select gr-model-sel">
        ${models.map(m => `<option value="${m}" ${m === 'mock' ? 'selected' : ''}>${m}</option>`).join('')}
      </select>
      <input type="number" class="form-input gr-temp-inp" value="0.7" min="0" max="2" step="0.1" />
    </div>
  `).join('');

  compileBtn.disabled = false;

  // Show existing config
  if (currentConfig) renderCurrentConfig(currentCard, currentBody, currentConfig);

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

    const graphConfig = {
      agents:     agentConfigs,
      max_rounds: parseInt(el.querySelector('#gc-max-rounds').value, 10),
    };

    try {
      await compileGraph(graphConfig);
      status.textContent = '✅ Grafo compilato';
      status.className = 'gr-status gr-status--ok';
      renderCurrentConfig(currentCard, currentBody, graphConfig);
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

function renderCurrentConfig(card, body, config) {
  const agents    = config.agents || [];
  const maxRounds = config.max_rounds ?? '?';
  const rows = agents.map(a => `
    <tr>
      <td>${AGENT_LABELS[a.agent_name] || a.agent_name}</td>
      <td><code>${a.model}</code></td>
      <td>${a.temperature}</td>
    </tr>
  `).join('');
  body.innerHTML = `
    <p class="gr-config-meta">Max rounds: <strong>${maxRounds}</strong></p>
    <table class="gr-config-table">
      <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
  card.hidden = false;
}

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
