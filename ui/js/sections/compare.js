/**
 * sections/compare.js — Human vs LLM review comparison.
 */

import { listComparablePapers, comparePaper } from '../api.js';

const DECISION_BADGE = {
  accept:         { label: 'ACCEPT',         cls: 'badge--accept' },
  minor_revision: { label: 'MINOR REVISION', cls: 'badge--minor' },
  major_revision: { label: 'MAJOR REVISION', cls: 'badge--major' },
  reject:         { label: 'REJECT',         cls: 'badge--reject' },
};

// ---------------------------------------------------------------------------
export function render() {
  const el = document.createElement('div');
  el.className = 'section comparison';
  el.innerHTML = `
    <h2 class="section__title">Confronto Review</h2>
    <p class="section__desc">
      Seleziona un paper dall'indice OpenReview per confrontare le review umane con quelle generate dal sistema.
    </p>
    <div id="cmp-error" class="error-msg" hidden></div>
    <div class="cmp-controls">
      <div class="form-group">
        <label class="form-label" for="cmp-paper-select">Paper</label>
        <select id="cmp-paper-select" class="form-select">
          <option value="">-- Caricamento… --</option>
        </select>
      </div>
      <button id="cmp-run-btn" class="btn btn--primary" disabled>Confronta</button>
    </div>
    <div id="cmp-result"></div>
  `;
  return el;
}

// ---------------------------------------------------------------------------
export async function mount(el) {
  const sel      = el.querySelector('#cmp-paper-select');
  const btn      = el.querySelector('#cmp-run-btn');
  const resultEl = el.querySelector('#cmp-result');
  const errorEl  = el.querySelector('#cmp-error');

  // populate paper list
  try {
    const papers = await listComparablePapers();
    sel.innerHTML = '<option value="">-- Seleziona paper --</option>' +
      papers.map(p => `<option value="${p.paper_path}">[${p.conference}] ${p.title}</option>`).join('');
    btn.disabled = false;
  } catch (e) {
    showError(errorEl, `Errore nel caricare i paper: ${e.message}`);
  }

  btn.addEventListener('click', async () => {
    const paperPath = sel.value;
    if (!paperPath) return;
    hideError(errorEl);
    resultEl.innerHTML = '<p class="cmp-loading">Caricamento dati OpenReview e confronto in corso…</p>';
    btn.disabled = true;
    try {
      const data = await comparePaper(paperPath);
      renderComparison(resultEl, data);
    } catch (e) {
      showError(errorEl, `Errore: ${e.message}`);
      resultEl.innerHTML = '';
    } finally {
      btn.disabled = false;
    }
  });
}

// ---------------------------------------------------------------------------
// Main render
// ---------------------------------------------------------------------------

function renderComparison(container, data) {
  const humanBadge = decisionBadge(data.human_decision);

  container.innerHTML = `
    <div class="cmp-paper-header">
      <div class="cmp-paper-title">${escapeHtml(data.title)}</div>
      <div class="cmp-paper-meta">
        <span>${escapeHtml(data.conference)}</span>
        <span>Forum: <code>${escapeHtml(data.forum_id)}</code></span>
        <span>Decisione umana: <span class="badge ${humanBadge.cls}">${humanBadge.label}</span></span>
        <span>${data.human_reviews.length} reviewer umani</span>
      </div>
    </div>

    ${renderRunTabs(data.run_comparisons)}
    ${renderRunPanels(data.run_comparisons, data.human_reviews)}
  `;

  // tab switching
  container.querySelectorAll('.cmp-run-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      container.querySelectorAll('.cmp-run-tab').forEach(t => t.classList.remove('is-active'));
      container.querySelectorAll('.cmp-run-panel').forEach(p => p.classList.remove('is-active'));
      tab.classList.add('is-active');
      const idx = tab.dataset.runIdx;
      container.querySelector(`[data-panel-idx="${idx}"]`).classList.add('is-active');
    });
  });
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

function renderRunTabs(runs) {
  if (!runs.length) return '<p class="muted">Nessun run trovato per questo paper.</p>';
  return `
    <div class="cmp-run-tabs">
      ${runs.map((rc, i) => {
        const badge = decisionBadge(rc.llm_decision || '');
        const active = i === 0 ? 'is-active' : '';
        return `<button class="cmp-run-tab ${active}" data-run-idx="${i}">
          Run ${i + 1} · <span class="badge badge--sm ${badge.cls}">${badge.label}</span>
        </button>`;
      }).join('')}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Panels
// ---------------------------------------------------------------------------

function renderRunPanels(runs, humanReviews) {
  return runs.map((rc, i) => {
    const active = i === 0 ? 'is-active' : '';
    const matchHtml = rc.decision_match
      ? '<span class="cmp-match-yes">✓ Decisione concordante</span>'
      : '<span class="cmp-match-no">✗ Decisione discordante</span>';
    const humanBadge = decisionBadge(runs[0]?.review_comparisons?.[0]?.human?.rating_label || '');
    const llmBadge   = decisionBadge(rc.llm_decision || '');

    return `
      <div class="cmp-run-panel ${active}" data-panel-idx="${i}">
        <div class="cmp-run-summary">
          <span><strong>Run:</strong> ${escapeHtml(rc.run_description || rc.run_id)}</span>
          <span><strong>LLM:</strong> <span class="badge badge--sm ${llmBadge.cls}">${llmBadge.label}</span></span>
          ${matchHtml}
          <span class="muted">${rc.human_review_count} umane · ${rc.llm_review_count} LLM</span>
        </div>

        <div class="cmp-section-label">Review pair a confronto</div>
        ${rc.review_comparisons.map((pair, j) => renderPair(pair, j)).join('')}

        ${renderMetaSection(rc)}
      </div>
    `;
  }).join('');
}

// ---------------------------------------------------------------------------
// Single review pair
// ---------------------------------------------------------------------------

function renderPair(pair, idx) {
  const h = pair.human;
  const l = pair.llm;

  const deltaHtml = (() => {
    if (pair.rating_delta === null || pair.rating_delta === undefined) return '';
    const d = pair.rating_delta;
    const cls = d > 0 ? 'cmp-delta--pos' : d < 0 ? 'cmp-delta--neg' : 'cmp-delta--zero';
    const sign = d > 0 ? '+' : '';
    return `<span class="cmp-delta ${cls}">Δ ${sign}${d}</span>`;
  })();

  return `
    <div class="cmp-pair">
      <div class="cmp-pair-header">
        <span class="cmp-pair-index">#${idx + 1}</span>
        ${h ? `<span class="muted">${escapeHtml(h.reviewer_id)}</span>` : ''}
        ${l ? `<span class="muted">${escapeHtml(l.agent)}</span>` : ''}
        ${deltaHtml}
      </div>

      <div class="cmp-col">
        <div class="cmp-col-title">Revisore Umano</div>
        ${h ? renderHumanCol(h) : '<p class="cmp-missing">Nessun revisore umano per questa posizione.</p>'}
      </div>

      <div class="cmp-col">
        <div class="cmp-col-title">Revisore LLM</div>
        ${l ? renderLlmCol(l) : '<p class="cmp-missing">Nessun revisore LLM per questa posizione.</p>'}
      </div>
    </div>
  `;
}

function renderHumanCol(h) {
  return `
    ${h.rating !== null && h.rating !== undefined
      ? `<span class="cmp-score">${h.rating}/10<span class="cmp-score-conf"> · conf ${h.confidence ?? '?'}/5</span></span>`
      : ''}
    ${h.rating_label ? `<div class="cmp-text" style="font-size:var(--text-xs);color:var(--c-text-muted);margin-bottom:var(--s-3)">${escapeHtml(h.rating_label)}</div>` : ''}
    ${field('Sommario paper', h.summary)}
    ${field('Punti di forza', h.strengths)}
    ${field('Debolezze', h.weaknesses)}
    ${field('Revisione completa', h.full_text)}
    ${field('Domande / Note', h.questions)}
  `;
}

function renderLlmCol(l) {
  const acceptance = (l.reasons_for_acceptance || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
  const rejection  = (l.reasons_for_rejection  || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
  const suggestions = (l.suggestions           || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');

  return `
    ${l.rating !== null && l.rating !== undefined
      ? `<span class="cmp-score">${l.rating}/10<span class="cmp-score-conf"> · conf ${l.confidence ?? '?'}/5</span></span>`
      : ''}
    ${field('Sommario', l.summary)}
    ${field('Significato e novità', l.significance_and_novelty)}
    ${acceptance ? `<div class="cmp-field-label">Motivi accettazione</div><ul class="cmp-list">${acceptance}</ul>` : ''}
    ${rejection  ? `<div class="cmp-field-label">Motivi rifiuto</div><ul class="cmp-list">${rejection}</ul>` : ''}
    ${suggestions ? `<div class="cmp-field-label">Suggerimenti</div><ul class="cmp-list">${suggestions}</ul>` : ''}
  `;
}

// ---------------------------------------------------------------------------
// Meta review + Area Chair
// ---------------------------------------------------------------------------

function renderMetaSection(rc) {
  if (!rc.human_meta_review && !rc.llm_meta_review && !rc.llm_area_chair) return '';

  const hm = rc.human_meta_review;
  const lm = rc.llm_meta_review;
  const ac = rc.llm_area_chair;

  const keyPoints = (lm?.key_points || []).map(k => `<li>${escapeHtml(k)}</li>`).join('');

  return `
    <div class="cmp-section-label">Meta Review</div>
    <div class="cmp-meta-grid">
      <div class="cmp-meta-col">
        <div class="cmp-meta-col-title">Area Chair Umano</div>
        ${hm ? `
          ${field('Testo', hm.text)}
          ${field('Raccomandazione', hm.recommendation)}
        ` : '<p class="cmp-missing">Non disponibile.</p>'}
      </div>
      <div class="cmp-meta-col">
        <div class="cmp-meta-col-title">Meta Reviewer LLM</div>
        ${lm ? `
          ${lm.overall_score !== null && lm.overall_score !== undefined
            ? `<span class="cmp-score">${lm.overall_score}/10</span>` : ''}
          ${field('Sommario', lm.summary)}
          ${keyPoints ? `<div class="cmp-field-label">Punti chiave</div><ul class="cmp-list">${keyPoints}</ul>` : ''}
          ${field('Raccomandazione', lm.recommendation)}
        ` : '<p class="cmp-missing">Non disponibile.</p>'}
      </div>
    </div>

    ${ac ? `
      <div class="cmp-section-label">Area Chair LLM</div>
      <div class="cmp-run-summary">
        ${ac.decision ? `<span><strong>Decisione:</strong> <span class="badge badge--sm ${decisionBadge(ac.decision).cls}">${decisionBadge(ac.decision).label}</span></span>` : ''}
        ${ac.confidence != null ? `<span><strong>Confidence:</strong> ${ac.confidence}/5</span>` : ''}
        ${ac.justification ? `<span class="muted" style="flex:1">${escapeHtml(ac.justification)}</span>` : ''}
      </div>
    ` : ''}
  `;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function field(label, value) {
  if (!value) return '';
  return `
    <div class="cmp-field-label">${label}</div>
    <div class="cmp-text">${escapeHtml(String(value))}</div>
  `;
}

function decisionBadge(decision) {
  const key = (decision || '').toLowerCase().replace(/ /g, '_');
  return DECISION_BADGE[key] || { label: (decision || 'UNKNOWN').toUpperCase(), cls: 'badge--unknown' };
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
