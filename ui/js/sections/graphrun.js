/**
 * sections/graphrun.js — Graph Run section.
 * Allows configuring per-agent models/temperature and running the full review pipeline.
 */

import { listPapers, listModels, runGraph } from '../api.js';

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
// render — pure DOM, no data fetching
// ---------------------------------------------------------------------------

export function render() {
  const el = document.createElement('div');
  el.className = 'section graphrun';
  el.innerHTML = `
    <h2 class="section__title">Graph Run</h2>
    <p class="section__desc">Configura gli agenti e avvia il pipeline completo di peer-review.</p>

    <div class="gr-layout">
      <!-- ── LEFT: config panel ── -->
      <div class="gr-config">
        <div class="form-group">
          <label class="form-label">Paper</label>
          <select id="gr-paper" class="form-select">
            <option value="">— caricamento papers… —</option>
          </select>
        </div>

        <div class="gr-globals">
          <div class="form-group form-group--inline">
            <label class="form-label">Max rounds</label>
            <input id="gr-max-rounds" type="number" class="form-input" value="2" min="1" max="5" />
          </div>
          <div class="form-group form-group--inline">
            <label class="form-label">Top-K RAG</label>
            <input id="gr-top-k" type="number" class="form-input" value="6" min="1" max="20" />
          </div>
        </div>

        <div class="gr-agents-table">
          <div class="gr-agents-header">
            <span>Agente</span><span>Modello</span><span>Temp</span>
          </div>
          <div id="gr-agents-rows"></div>
        </div>

        <button id="gr-run-btn" class="btn btn--primary gr-run-btn" disabled>
          ▶ Run Review
        </button>
        <div id="gr-error" class="error-msg" hidden></div>
      </div>

      <!-- ── RIGHT: result panel ── -->
      <div class="gr-result" id="gr-result" hidden>
        <div id="gr-result-header" class="gr-result-header"></div>
        <div id="gr-result-body" class="gr-result-body"></div>
      </div>
    </div>
  `;
  return el;
}

// ---------------------------------------------------------------------------
// mount — data fetching + event wiring
// ---------------------------------------------------------------------------

export async function mount(el) {
  const paperSel   = el.querySelector('#gr-paper');
  const agentRows  = el.querySelector('#gr-agents-rows');
  const runBtn     = el.querySelector('#gr-run-btn');
  const errorDiv   = el.querySelector('#gr-error');
  const resultPane = el.querySelector('#gr-result');

  // Load papers + models in parallel
  let papers = [], models = [];
  try {
    [papers, models] = await Promise.all([listPapers(), listModels()]);
  } catch (e) {
    showError(errorDiv, `Errore caricamento dati: ${e.message}`);
    return;
  }

  // Populate paper select
  paperSel.innerHTML = papers.length
    ? papers.map(p => `<option value="${p}">${p}</option>`).join('')
    : '<option value="">Nessun paper disponibile</option>';

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

  runBtn.disabled = false;

  // Run
  runBtn.addEventListener('click', async () => {
    const paper = paperSel.value;
    if (!paper) { showError(errorDiv, 'Seleziona un paper.'); return; }

    hideError(errorDiv);
    runBtn.disabled = true;
    runBtn.textContent = '⏳ Running…';
    resultPane.hidden = true;

    const agentConfigs = AGENT_NAMES.map(name => {
      const row  = agentRows.querySelector(`[data-agent="${name}"]`);
      return {
        agent_name:  name,
        model:       row.querySelector('.gr-model-sel').value,
        temperature: parseFloat(row.querySelector('.gr-temp-inp').value),
      };
    });

    const graphConfig = {
      agents:     agentConfigs,
      max_rounds: parseInt(el.querySelector('#gr-max-rounds').value, 10),
    };

    try {
      const result = await runGraph({
        paper_path:    paper,
        rag_top_k:     parseInt(el.querySelector('#gr-top-k').value, 10) || null,
        force_reindex: false,
        graph_config:  graphConfig,
      });
      renderResult(el, result);
    } catch (e) {
      showError(errorDiv, e.message);
    } finally {
      runBtn.disabled = false;
      runBtn.textContent = '▶ Run Review';
    }
  });
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
    <span class="badge ${badge.cls}">${badge.label}</span>
    <span class="gr-meta-info">${rounds} round${rounds !== 1 ? 's' : ''} · ${paper}</span>
  `;

  const meta    = result.meta_review || {};
  const reviews = result.reviews || [];
  const notes   = result.revision_notes;

  body.innerHTML = `
    ${renderMetaSummary(meta)}
    ${notes ? renderRevisionNotes(notes) : ''}
    ${renderReviewsList(reviews)}
  `;

  pane.hidden = false;
  pane.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderMetaSummary(meta) {
  if (!meta.summary) return '';
  const score    = meta.overall_score ? `⭐ ${meta.overall_score}/5` : '';
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
    const agent   = data.agent || `Review ${i + 1}`;
    const label   = AGENT_LABELS[agent] || agent;
    const payload = data.payload || {};
    const summary = payload.summary || '';
    const score   = payload.soundness_score ?? payload.presentation_score ?? payload.contribution_score ?? null;
    const conf    = payload.confidence ?? null;
    const strengths  = (payload.strengths  || []).map(s => `<li>${s}</li>`).join('');
    const weaknesses = (payload.weaknesses || []).map(w => `<li>${w}</li>`).join('');
    return `
      <details class="gr-review">
        <summary class="gr-review-summary">
          ${label}
          ${score !== null ? `<span class="gr-score">${score}/5</span>` : ''}
          ${conf  !== null ? `<span class="gr-conf">conf ${conf}/5</span>` : ''}
        </summary>
        <div class="gr-review-body">
          ${summary ? `<p>${summary}</p>` : ''}
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

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
