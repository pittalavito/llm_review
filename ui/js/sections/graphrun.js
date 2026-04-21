/**
 * sections/graphrun.js — Graph Run section.
 * The compiled config table becomes editable in-place when "Ricompila" is clicked.
 */

import { listPapers, listModels, getGraphConfig, compileGraph, runGraph } from '../api.js';

const AGENT_LABELS = {
  soundness_reviewer:    '🔬 Soundness Reviewer',
  presentation_reviewer: '🎨 Presentation Reviewer',
  contribution_reviewer: '📐 Contribution Reviewer',
  meta_reviewer:         '📋 Meta Reviewer',
  refinement_agent:      '✏️  Refinement Agent',
};

const AGENT_NAMES = Object.keys(AGENT_LABELS);

const DECISION_BADGE = {
  accept:         { label: 'ACCEPT',         cls: 'badge--accept' },
  minor_revision: { label: 'MINOR REVISION', cls: 'badge--minor' },
  major_revision: { label: 'MAJOR REVISION', cls: 'badge--major' },
  reject:         { label: 'REJECT',         cls: 'badge--reject' },
};

// ---------------------------------------------------------------------------
// render
// ---------------------------------------------------------------------------

export function render() {
  const el = document.createElement('div');
  el.className = 'section';
  el.innerHTML = `
    <h2 class="section__title">Graph Run</h2>
    <p class="section__desc">Esegui il pipeline di review su un paper.</p>

    <!-- Config compilata -->
    <div class="gr-card">
      <div class="gr-card-header-row">
        <div class="gr-card-title">Grafo compilato</div>
        <div class="gr-card-actions">
          <button id="gr-action-btn"  class="btn btn--ghost btn--sm">⚙ Ricompila</button>
          <button id="gr-cancel-btn"  class="btn btn--ghost btn--sm" hidden>✕ Annulla</button>
        </div>
      </div>
      <div id="gr-config-body"><p class="muted">Caricamento…</p></div>
      <div id="gr-compile-error" class="error-msg" hidden></div>
      <span id="gr-compile-status" class="gr-status" style="margin-top:var(--s-2);display:block"></span>
    </div>

    <!-- Run -->
    <div class="gr-card">
      <div class="gr-card-title">Esegui review</div>

      <div class="form-group">
        <label class="form-label">Paper</label>
        <select id="gr-paper" class="form-select">
          <option value="">— caricamento papers… —</option>
        </select>
      </div>

      <div class="gr-globals">
        <div class="form-group form-group--inline">
          <label class="form-label">Force reindex</label>
          <input id="gr-force-reindex" type="checkbox" class="form-checkbox" />
        </div>
      </div>

      <div class="gr-card-footer">
        <button id="gr-run-btn" class="btn btn--primary" disabled>▶ Run Review</button>
        <span id="gr-run-status" class="gr-status"></span>
      </div>
      <div id="gr-run-error" class="error-msg" hidden></div>
    </div>

    <!-- Risultato -->
    <div class="gr-card gr-result-card" id="gr-result" hidden>
      <div id="gr-result-header" class="gr-result-header"></div>
      <div id="gr-result-body"   class="gr-result-body"></div>
    </div>
  `;
  return el;
}

// ---------------------------------------------------------------------------
// mount
// ---------------------------------------------------------------------------

export async function mount(el) {
  const configBody    = el.querySelector('#gr-config-body');
  const actionBtn     = el.querySelector('#gr-action-btn');
  const cancelBtn     = el.querySelector('#gr-cancel-btn');
  const compileError  = el.querySelector('#gr-compile-error');
  const compileStatus = el.querySelector('#gr-compile-status');
  const paperSel      = el.querySelector('#gr-paper');
  const runBtn        = el.querySelector('#gr-run-btn');
  const runStatus     = el.querySelector('#gr-run-status');
  const runError      = el.querySelector('#gr-run-error');

  let currentConfig = null;
  let models        = [];
  let editMode      = false;   // false = read-only, true = editing

  // Load all in parallel
  let papers = [];
  try {
    [papers, models, currentConfig] = await Promise.all([listPapers(), listModels(), getGraphConfig()]);
  } catch (e) {
    configBody.innerHTML = `<p class="error-msg">Errore: ${e.message}</p>`;
    return;
  }

  // ── Helpers to switch modes ──
  function enterReadOnly() {
    editMode = false;
    renderReadOnly(configBody, currentConfig);
    actionBtn.textContent = '⚙ Ricompila';
    actionBtn.className   = 'btn btn--ghost btn--sm';
    actionBtn.disabled    = false;
    cancelBtn.hidden      = true;
    compileStatus.textContent = '';
    hideError(compileError);
  }

  function enterEditMode() {
    editMode = true;
    const prefill = currentConfig || defaultConfig();
    renderEditable(configBody, prefill, models);
    actionBtn.textContent = '⚙ Compila';
    actionBtn.className   = 'btn btn--secondary btn--sm';
    cancelBtn.hidden      = false;
    hideError(compileError);
    compileStatus.textContent = '';
  }

  // Initial state
  enterReadOnly();

  // Populate papers
  paperSel.innerHTML = papers.length
    ? papers.map(p => `<option value="${p}">${p}</option>`).join('')
    : '<option value="">Nessun paper disponibile</option>';

  // Enable run if compiled
  if (currentConfig) {
    runBtn.disabled = false;
    runStatus.textContent = 'Pronto';
    runStatus.className = 'gr-status gr-status--ok';
  } else {
    runStatus.textContent = 'Nessun grafo compilato';
    runStatus.className = 'gr-status';
  }

  // ── Action button: Ricompila ↔ Compila ──
  actionBtn.addEventListener('click', async () => {
    if (!editMode) {
      enterEditMode();
      return;
    }

    // === In edit mode: compile ===
    hideError(compileError);
    actionBtn.disabled  = true;
    cancelBtn.disabled  = true;
    compileStatus.textContent = '⏳ Compilazione…';
    compileStatus.className   = 'gr-status';

    try {
      const newConfig = readFormValues(configBody);
      await compileGraph(newConfig);
      currentConfig = newConfig;
      enterReadOnly();
      compileStatus.textContent = '✅ Grafo compilato';
      compileStatus.className   = 'gr-status gr-status--ok';
      runBtn.disabled       = false;
      runStatus.textContent = 'Pronto';
      runStatus.className   = 'gr-status gr-status--ok';
    } catch (e) {
      compileStatus.textContent = '';
      showError(compileError, e.message || String(e));
    } finally {
      actionBtn.disabled = false;
      cancelBtn.disabled = false;
    }
  });

  // ── Annulla ──
  cancelBtn.addEventListener('click', () => {
    enterReadOnly();
  });

  // ── Run ──
  runBtn.addEventListener('click', async () => {
    const paper = paperSel.value;
    if (!paper) { showError(runError, 'Seleziona un paper.'); return; }

    hideError(runError);
    runBtn.disabled = true;
    runStatus.textContent = '⏳ Running…';
    runStatus.className   = 'gr-status';
    el.querySelector('#gr-result').hidden = true;

    try {
      const result = await runGraph({
        paper_path:    paper,
        force_reindex: el.querySelector('#gr-force-reindex').checked,
      });
      runStatus.textContent = '✅ Completato';
      runStatus.className   = 'gr-status gr-status--ok';
      renderResult(el, result);
    } catch (e) {
      runStatus.textContent = '';
      showError(runError, e.message);
    } finally {
      runBtn.disabled = false;
    }
  });
}

// ---------------------------------------------------------------------------
// Config table — read-only
// ---------------------------------------------------------------------------

function renderReadOnly(container, config) {
  if (!config) {
    container.innerHTML = `<p class="gr-no-config">Nessun grafo compilato. Premi <strong>Ricompila</strong> per configurarlo.</p>`;
    return;
  }
  const rows = (config.agents || []).map(a => `
    <tr>
      <td>${AGENT_LABELS[a.agent_name] || a.agent_name}</td>
      <td><code>${a.model}</code></td>
      <td>${a.temperature}</td>
    </tr>
  `).join('');
  container.innerHTML = `
    <p class="gr-config-meta">Max rounds: <strong>${config.max_rounds ?? '?'}</strong></p>
    <table class="gr-config-table">
      <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// ---------------------------------------------------------------------------
// Config table — editable in-place
// ---------------------------------------------------------------------------

function renderEditable(container, config, models) {
  const maxRounds = config.max_rounds ?? 2;
  const rows = AGENT_NAMES.map(name => {
    const existing = config.agents?.find(a => a.agent_name === name);
    const model    = existing?.model       ?? 'mock';
    const temp     = existing?.temperature ?? 0.7;
    return `
      <tr data-agent="${name}">
        <td>${AGENT_LABELS[name]}</td>
        <td>
          <select class="form-select gr-model-sel">
            ${models.map(m => `<option value="${m}" ${m === model ? 'selected' : ''}>${m}</option>`).join('')}
          </select>
        </td>
        <td>
          <input type="number" class="form-input gr-temp-inp"
                 value="${temp}" min="0" max="2" step="0.1" />
        </td>
      </tr>
    `;
  }).join('');

  container.innerHTML = `
    <div class="gr-globals" style="margin-bottom:var(--s-3)">
      <div class="form-group form-group--inline">
        <label class="form-label">Max rounds</label>
        <input id="gr-max-rounds-edit" type="number" class="form-input"
               value="${maxRounds}" min="1" max="5" />
      </div>
    </div>
    <table class="gr-config-table gr-config-table--edit">
      <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function readFormValues(container) {
  const maxRoundsEl = container.querySelector('#gr-max-rounds-edit');
  if (!maxRoundsEl) throw new Error('Form di configurazione non trovato — riapri Ricompila.');

  const maxRounds = parseInt(maxRoundsEl.value, 10);
  const agents = AGENT_NAMES.map(name => {
    const row = container.querySelector(`tr[data-agent="${name}"]`);
    if (!row) throw new Error(`Riga agente non trovata: ${name}`);
    return {
      agent_name:  name,
      model:       row.querySelector('.gr-model-sel').value,
      temperature: parseFloat(row.querySelector('.gr-temp-inp').value),
    };
  });
  return { max_rounds: maxRounds, agents };
}

// ---------------------------------------------------------------------------
// Result rendering
// ---------------------------------------------------------------------------

function renderResult(el, result) {
  const pane   = el.querySelector('#gr-result');
  const header = el.querySelector('#gr-result-header');
  const body   = el.querySelector('#gr-result-body');

  const decision = (result.decision || 'unknown').toLowerCase();
  const badge    = DECISION_BADGE[decision] || { label: decision.toUpperCase(), cls: 'badge--unknown' };
  const rounds   = result.current_round ?? '?';
  const paper    = result.retrieval_metadata?.paper_path ?? '';

  header.innerHTML = `
    <div class="gr-result-title">Risultato</div>
    <div class="gr-result-meta">
      <span class="badge ${badge.cls}">${badge.label}</span>
      <span class="gr-meta-info">${rounds} round${rounds !== 1 ? 's' : ''} · ${paper}</span>
    </div>
  `;

  body.innerHTML = `
    ${renderMetaSummary(result.meta_review || {})}
    ${result.revision_notes ? renderRevisionNotes(result.revision_notes) : ''}
    ${renderReviewsList(result.reviews || [])}
  `;

  pane.hidden = false;
  pane.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderMetaSummary(meta) {
  if (!meta.summary) return '';
  const score     = meta.overall_score ? `⭐ ${meta.overall_score}/5` : '';
  const keyPoints = (meta.key_points || []).map(p => `<li>${p}</li>`).join('');
  return `
    <div class="gr-block">
      <div class="gr-block-title">Meta Review ${score}</div>
      <p class="gr-block-text">${meta.summary}</p>
      ${keyPoints ? `<ul class="gr-key-points">${keyPoints}</ul>` : ''}
    </div>
  `;
}

function renderRevisionNotes(notes) {
  return `
    <div class="gr-block gr-block--notes">
      <div class="gr-block-title">Revision Notes</div>
      <p class="gr-block-text">${notes}</p>
    </div>
  `;
}

function renderReviewsList(reviews) {
  if (!reviews.length) return '';
  const items = reviews.map((raw, i) => {
    let data;
    try { data = JSON.parse(raw); } catch { return ''; }
    const label    = AGENT_LABELS[data.agent] || data.agent || `Review ${i + 1}`;
    const payload  = data.payload || {};
    const score    = payload.soundness_score ?? payload.presentation_score ?? payload.contribution_score ?? null;
    const conf     = payload.confidence ?? null;
    const strengths  = (payload.strengths  || []).map(s => `<li>${s}</li>`).join('');
    const weaknesses = (payload.weaknesses || []).map(w => `<li>${w}</li>`).join('');
    return `
      <details class="gr-review">
        <summary class="gr-review-summary">
          <span>${label}</span>
          ${score !== null ? `<span class="gr-score">${score}/5</span>` : ''}
          ${conf  !== null ? `<span class="gr-conf">conf ${conf}/5</span>` : ''}
        </summary>
        <div class="gr-review-body">
          ${payload.summary ? `<p>${payload.summary}</p>` : ''}
          ${strengths  ? `<div class="gr-list-title">Strengths</div><ul>${strengths}</ul>`   : ''}
          ${weaknesses ? `<div class="gr-list-title">Weaknesses</div><ul>${weaknesses}</ul>` : ''}
        </div>
      </details>
    `;
  }).join('');
  return `
    <div class="gr-block">
      <div class="gr-block-title">Reviews (${reviews.length})</div>
      ${items}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function defaultConfig() {
  return {
    max_rounds: 2,
    agents: AGENT_NAMES.map(name => ({ agent_name: name, model: 'mock', temperature: 0.7 })),
  };
}

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
