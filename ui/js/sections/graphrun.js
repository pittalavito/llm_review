/**
 * sections/graphrun.js — Graph Run section.
 * The compiled config table becomes editable in-place when "Ricompila" is clicked.
 */

import { listPapers, listModels, getGraphConfig, compileGraph, runGraph, listPromptVersions } from '../api.js';

const AGENT_LABELS = {
  reviewer_1:   '👤 Reviewer 1',
  reviewer_2:   '👤 Reviewer 2',
  reviewer_3:   '👤 Reviewer 3',
  meta_reviewer: '📋 Meta Reviewer',
  area_chair:    '🏛️ Area Chair',
  author_agent:  '✍️  Author Agent',
};

const REVIEWER_NAMES = ['reviewer_1', 'reviewer_2', 'reviewer_3'];
const AGENT_NAMES    = Object.keys(AGENT_LABELS);

const DECISION_BADGE = {
  accept:         { label: 'ACCEPT',         cls: 'badge--accept' },
  minor_revision: { label: 'MINOR REVISION', cls: 'badge--minor' },
  major_revision: { label: 'MAJOR REVISION', cls: 'badge--major' },
  reject:         { label: 'REJECT',         cls: 'badge--reject' },
};

const COMMITMENT_OPTIONS   = ['responsible', 'irresponsible'];
const INTENTION_OPTIONS    = ['benign', 'malicious'];
const KNOWLEDGE_OPTIONS    = ['knowledgeable', 'unknowledgeable'];
const FOCUS_OPTIONS        = ['soundness', 'empirical', 'novelty'];
const AC_STYLE_OPTIONS     = ['inclusive', 'conformist', 'authoritarian'];

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

      <div class="form-group">
        <label class="form-label" for="gr-run-description">Descrizione run</label>
        <textarea
          id="gr-run-description"
          class="form-textarea"
          rows="3"
          maxlength="200"
          placeholder="Inserisci una breve descrizione del run (max 200 caratteri)..."
        ></textarea>
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
  const runDescriptionEl = el.querySelector('#gr-run-description');

  let currentConfig = null;
  let models        = [];
  let editMode      = false;
  let versionsByRole = {};

  let papers = [];
  try {
    let promptVersions = [];
    [papers, models, currentConfig, promptVersions] = await Promise.all([
      listPapers(), listModels(), getGraphConfig(),
      listPromptVersions().catch(() => []),
    ]);
    versionsByRole = groupVersionsByRole(promptVersions);
  } catch (e) {
    configBody.innerHTML = `<p class="error-msg">Errore: ${e.message}</p>`;
    return;
  }

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
    renderEditable(configBody, prefill, models, versionsByRole);
    actionBtn.textContent = '⚙ Compila';
    actionBtn.className   = 'btn btn--secondary btn--sm';
    cancelBtn.hidden      = false;
    hideError(compileError);
    compileStatus.textContent = '';
  }

  enterReadOnly();

  paperSel.innerHTML = papers.length
    ? papers.map(p => `<option value="${p}">${p}</option>`).join('')
    : '<option value="">Nessun paper disponibile</option>';

  if (currentConfig) {
    runBtn.disabled = false;
    runStatus.textContent = 'Pronto';
    runStatus.className = 'gr-status gr-status--ok';
  } else {
    runStatus.textContent = 'Nessun grafo compilato';
    runStatus.className = 'gr-status';
  }

  actionBtn.addEventListener('click', async () => {
    if (!editMode) { enterEditMode(); return; }

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

  cancelBtn.addEventListener('click', () => enterReadOnly());

  runBtn.addEventListener('click', async () => {
    const paper = paperSel.value;
    const runDescription = runDescriptionEl.value.trim();
    if (!paper) { showError(runError, 'Seleziona un paper.'); return; }
    if (!runDescription) { showError(runError, 'Inserisci una descrizione del run.'); return; }

    hideError(runError);
    runBtn.disabled = true;
    runStatus.textContent = '⏳ Running…';
    runStatus.className   = 'gr-status';
    el.querySelector('#gr-result').hidden = true;

    try {
      const result = await runGraph({
        paper_path:    paper,
        run_description: runDescription,
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
  const rows = (config.agents || []).map(a => {
    let extra = '';
    if (REVIEWER_NAMES.includes(a.agent_name) && a.reviewer_persona) {
      const p = a.reviewer_persona;
      extra = `<small>${p.focus ?? 'soundness'} · ${p.commitment} · ${p.intention} · ${p.knowledgeability}</small>`;
    } else if (a.agent_name === 'area_chair' && a.area_chair_style) {
      extra = `<small>${a.area_chair_style}</small>`;
    }
    return `
      <tr>
        <td>${AGENT_LABELS[a.agent_name] || a.agent_name}</td>
        <td><code>${a.model}</code></td>
        <td>${a.temperature}</td>
        <td><code>${a.prompt_version ?? 'v1'}</code></td>
        <td>${extra}</td>
      </tr>
    `;
  }).join('');
  container.innerHTML = `
    <p class="gr-config-meta">Max rounds: <strong>${config.max_rounds ?? '?'}</strong></p>
    <table class="gr-config-table">
      <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th><th>Prompt</th><th>Persona / Stile</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

// ---------------------------------------------------------------------------
// Config table — editable in-place
// ---------------------------------------------------------------------------

function renderEditable(container, config, models, versionsByRole = {}) {
  const maxRounds = config.max_rounds ?? 2;
  const rows = AGENT_NAMES.map(name => {
    const existing = config.agents?.find(a => a.agent_name === name);
    const model    = existing?.model       ?? 'mock';
    const temp     = existing?.temperature ?? 0.7;

    const role       = roleForAgent(name);
    const selectedPv = existing?.prompt_version ?? 'v1';
    // Keep the currently-selected label visible even if it was deactivated.
    const pvOptions  = (versionsByRole[role] || []).includes(selectedPv)
      ? versionsByRole[role]
      : [selectedPv, ...(versionsByRole[role] || [])];
    const promptCell = `
      <td>
        <select class="form-select gr-prompt-sel" style="width:auto;font-size:0.75rem">
          ${pvOptions.map(v => `<option value="${v}" ${v === selectedPv ? 'selected' : ''}>${v}</option>`).join('')}
        </select>
      </td>
    `;

    let extraCell = '<td></td>';

    if (REVIEWER_NAMES.includes(name)) {
      const p = existing?.reviewer_persona || {};
      const focus          = p.focus          ?? 'soundness';
      const commitment     = p.commitment     ?? 'responsible';
      const intention      = p.intention      ?? 'benign';
      const knowledgeability = p.knowledgeability ?? 'knowledgeable';
      extraCell = `
        <td>
          <select class="form-select gr-persona-focus" style="width:auto;font-size:0.75rem">
            ${FOCUS_OPTIONS.map(o => `<option ${o === focus ? 'selected' : ''}>${o}</option>`).join('')}
          </select>
          <select class="form-select gr-persona-commitment" style="width:auto;font-size:0.75rem">
            ${COMMITMENT_OPTIONS.map(o => `<option ${o === commitment ? 'selected' : ''}>${o}</option>`).join('')}
          </select>
          <select class="form-select gr-persona-intention" style="width:auto;font-size:0.75rem">
            ${INTENTION_OPTIONS.map(o => `<option ${o === intention ? 'selected' : ''}>${o}</option>`).join('')}
          </select>
          <select class="form-select gr-persona-knowledge" style="width:auto;font-size:0.75rem">
            ${KNOWLEDGE_OPTIONS.map(o => `<option ${o === knowledgeability ? 'selected' : ''}>${o}</option>`).join('')}
          </select>
        </td>
      `;
    } else if (name === 'area_chair') {
      const style = existing?.area_chair_style ?? 'inclusive';
      extraCell = `
        <td>
          <select class="form-select gr-ac-style" style="width:auto;font-size:0.75rem">
            ${AC_STYLE_OPTIONS.map(o => `<option ${o === style ? 'selected' : ''}>${o}</option>`).join('')}
          </select>
        </td>
      `;
    }

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
                 value="${temp}" min="0" max="2" step="0.1" style="width:5rem"/>
        </td>
        ${promptCell}
        ${extraCell}
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
      <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th><th>Prompt</th><th>Persona / Stile</th></tr></thead>
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

    const entry = {
      agent_name:  name,
      model:       row.querySelector('.gr-model-sel').value,
      temperature: parseFloat(row.querySelector('.gr-temp-inp').value),
      prompt_version: row.querySelector('.gr-prompt-sel')?.value ?? 'v1',
    };

    if (REVIEWER_NAMES.includes(name)) {
      entry.reviewer_persona = {
        focus:          row.querySelector('.gr-persona-focus').value,
        commitment:     row.querySelector('.gr-persona-commitment').value,
        intention:      row.querySelector('.gr-persona-intention').value,
        knowledgeability: row.querySelector('.gr-persona-knowledge').value,
      };
    } else if (name === 'area_chair') {
      entry.area_chair_style = row.querySelector('.gr-ac-style').value;
    }

    return entry;
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
    ${result.area_chair_response ? renderAreaChairResponse(result.area_chair_response) : ''}
    ${result.author_response     ? renderAuthorResponse(result.author_response)         : ''}
    ${renderReviewsList(result.reviews || [])}
  `;

  pane.hidden = false;
  pane.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderMetaSummary(meta) {
  if (!meta.summary) return '';
  const score     = meta.overall_score ? `⭐ ${meta.overall_score}/10` : '';
  const rec       = meta.recommendation ? `Raccomandazione: <strong>${meta.recommendation}</strong>` : '';
  const keyPoints = (meta.key_points || []).map(p => `<li>${p}</li>`).join('');
  return `
    <div class="gr-block">
      <div class="gr-block-title">📋 Meta Review ${score}</div>
      ${rec ? `<p class="gr-block-text">${rec}</p>` : ''}
      <p class="gr-block-text">${meta.summary}</p>
      ${keyPoints ? `<ul class="gr-key-points">${keyPoints}</ul>` : ''}
    </div>
  `;
}

function renderAreaChairResponse(ac) {
  if (!ac.decision) return '';
  const badge = DECISION_BADGE[ac.decision] || { label: ac.decision.toUpperCase(), cls: 'badge--unknown' };
  return `
    <div class="gr-block gr-block--ac">
      <div class="gr-block-title">🏛️ Area Chair Decision &nbsp;<span class="badge ${badge.cls}">${badge.label}</span></div>
      ${ac.summary      ? `<p class="gr-block-text">${ac.summary}</p>`                            : ''}
      ${ac.justification ? `<p class="gr-block-text"><em>${ac.justification}</em></p>`            : ''}
      ${ac.confidence   ? `<p class="gr-block-text">Confidence: ${ac.confidence}/5</p>`          : ''}
    </div>
  `;
}

function renderAuthorResponse(authorResponse) {
  const rebuttal   = authorResponse.rebuttal    || '';
  const keyChanges = (authorResponse.key_changes || []).map(c => `<li>${c}</li>`).join('');
  const rebuttals  = (authorResponse.reviewer_rebuttals || []).map(r => `
    <details class="gr-revised-section">
      <summary>Risposta a ${r.reviewer_name}</summary>
      <p class="gr-block-text">${r.response || ''}</p>
    </details>
  `).join('');
  const sections   = (authorResponse.revised_sections || []).map(s => `
    <details class="gr-revised-section">
      <summary>[Revised ${(s.section_name || '').toUpperCase()}]</summary>
      <p class="gr-block-text">${s.content || ''}</p>
    </details>
  `).join('');
  return `
    <div class="gr-block gr-block--notes">
      <div class="gr-block-title">✍️ Author Response</div>
      ${rebuttal  ? `<p class="gr-block-text"><strong>Rebuttal:</strong> ${rebuttal}</p>` : ''}
      ${rebuttals}
      ${keyChanges ? `<p><strong>Key changes:</strong></p><ul>${keyChanges}</ul>`        : ''}
      ${sections}
    </div>
  `;
}

function renderReviewsList(reviews) {
  if (!reviews.length) return '';
  const items = reviews.map((raw, i) => {
    let data;
    try { data = JSON.parse(raw); } catch { return ''; }
    const label   = AGENT_LABELS[data.agent] || data.agent || `Review ${i + 1}`;
    const payload = data.payload || {};
    const rating  = payload.rating ?? null;
    const conf    = payload.confidence ?? null;
    const acceptance = (payload.reasons_for_acceptance || []).map(s => `<li>${s}</li>`).join('');
    const rejection  = (payload.reasons_for_rejection  || []).map(w => `<li>${w}</li>`).join('');
    const suggestions= (payload.suggestions            || []).map(s => `<li>${s}</li>`).join('');
    return `
      <details class="gr-review">
        <summary class="gr-review-summary">
          <span>${label}</span>
          ${rating !== null ? `<span class="gr-score">${rating}/10</span>` : ''}
          ${conf   !== null ? `<span class="gr-conf">conf ${conf}/5</span>` : ''}
        </summary>
        <div class="gr-review-body">
          ${payload.summary               ? `<p>${payload.summary}</p>`                                                 : ''}
          ${payload.significance_and_novelty ? `<p><strong>Significance & Novelty:</strong> ${payload.significance_and_novelty}</p>` : ''}
          ${acceptance ? `<div class="gr-list-title">Reasons for Acceptance</div><ul>${acceptance}</ul>` : ''}
          ${rejection  ? `<div class="gr-list-title">Reasons for Rejection</div><ul>${rejection}</ul>`  : ''}
          ${suggestions? `<div class="gr-list-title">Suggestions</div><ul>${suggestions}</ul>`          : ''}
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
    agents: [
      ...REVIEWER_NAMES.map(name => ({
        agent_name: name, model: 'mock', temperature: 0.7,
        reviewer_persona: { commitment: 'responsible', intention: 'benign', knowledgeability: 'knowledgeable' },
      })),
      { agent_name: 'meta_reviewer', model: 'mock', temperature: 0.7 },
      { agent_name: 'area_chair',    model: 'mock', temperature: 0.7, area_chair_style: 'inclusive' },
      { agent_name: 'author_agent',  model: 'mock', temperature: 0.7 },
    ],
  };
}

function roleForAgent(name) {
  return REVIEWER_NAMES.includes(name) ? 'reviewer' : name;
}

/** {role: [labels...]} from GET /prompts (active versions only). */
function groupVersionsByRole(versions) {
  const byRole = {};
  for (const v of versions) {
    (byRole[v.agent_role] ??= []).push(v.version_label);
  }
  for (const role of Object.keys(byRole)) byRole[role].sort();
  return byRole;
}

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
