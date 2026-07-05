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

    ${renderRunsSummary(data.run_comparisons)}

    <div class="cmp-section-label">Review (umane e LLM, elencate)</div>
    ${renderReviewTable(data.human_reviews, data.run_comparisons)}

    ${renderMetaTable(firstHumanMeta(data.run_comparisons), data.run_comparisons)}
  `;

  // expandable review/meta rows
  container.querySelectorAll('.cmp-row').forEach(row => {
    row.addEventListener('click', () => {
      const detail = row.nextElementSibling;
      if (detail && detail.classList.contains('cmp-detail')) {
        detail.hidden = !detail.hidden;
        row.classList.toggle('is-open', !detail.hidden);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Runs summary (all runs listed, no tabs)
// ---------------------------------------------------------------------------

function renderRunsSummary(runs) {
  if (!runs.length) return '<p class="muted">Nessun run trovato per questo paper.</p>';
  return `
    <div class="cmp-section-label">Run analizzati</div>
    ${runs.map(rc => {
      const badge = decisionBadge(rc.llm_decision || '');
      const match = rc.decision_match
        ? '<span class="cmp-match-yes">✓ concordante</span>'
        : '<span class="cmp-match-no">✗ discordante</span>';
      return `
        <div class="cmp-run-summary">
          <span><strong>Run:</strong> ${escapeHtml(rc.run_description || rc.run_id)}</span>
          <span><strong>LLM:</strong> <span class="badge badge--sm ${badge.cls}">${badge.label}</span></span>
          ${match}
          <span class="muted">${rc.human_review_count} umane · ${rc.llm_review_count} LLM</span>
        </div>
      `;
    }).join('')}
  `;
}

function firstHumanMeta(runs) {
  const rc = (runs || []).find(r => r.human_meta_review);
  return rc ? rc.human_meta_review : null;
}

// ---------------------------------------------------------------------------
// Review table (human + LLM listed, not paired)
// ---------------------------------------------------------------------------

function renderReviewTable(humanReviews, runs) {
  const rows = [...(humanReviews || []).map(renderHumanRow)];
  (runs || []).forEach(rc => {
    const runLabel = rc.run_description || rc.run_id;
    (rc.llm_reviews || []).forEach(l => rows.push(renderLlmRow(l, runLabel)));
  });
  if (!rows.length) return '<p class="cmp-missing">Nessuna review disponibile.</p>';

  return `
    <table class="cmp-table">
      <thead>
        <tr>
          <th class="cmp-th-toggle"></th>
          <th>Tipo</th>
          <th>Run</th>
          <th>Reviewer</th>
          <th class="cmp-num">Rating</th>
          <th class="cmp-num">Confidence</th>
        </tr>
      </thead>
      <tbody>${rows.join('')}</tbody>
    </table>
  `;
}

function renderHumanRow(h) {
  const rating = (h.rating !== null && h.rating !== undefined) ? `${h.rating}/10` : '—';
  const conf   = (h.confidence !== null && h.confidence !== undefined) ? `${h.confidence}/5` : '—';
  return `
    <tr class="cmp-row cmp-row--human">
      <td class="cmp-toggle-cell"><span class="cmp-toggle">▸</span></td>
      <td><span class="cmp-tag cmp-tag--human">Umano</span></td>
      <td class="muted">—</td>
      <td>${escapeHtml(h.reviewer_id || '?')}</td>
      <td class="cmp-num">${rating}</td>
      <td class="cmp-num">${conf}</td>
    </tr>
    <tr class="cmp-detail" hidden>
      <td colspan="6">
        ${h.rating_label ? `<div class="cmp-field-label">Valutazione</div><div class="cmp-text">${escapeHtml(h.rating_label)}</div>` : ''}
        ${field('Sommario paper', h.summary)}
        ${field('Punti di forza', h.strengths)}
        ${field('Debolezze', h.weaknesses)}
        ${field('Revisione completa', h.full_text)}
        ${field('Domande / Note', h.questions)}
      </td>
    </tr>
  `;
}

function renderLlmRow(l, runLabel) {
  const rating = (l.rating !== null && l.rating !== undefined) ? `${l.rating}/10` : '—';
  const conf   = (l.confidence !== null && l.confidence !== undefined) ? `${l.confidence}/5` : '—';
  const acceptance  = (l.reasons_for_acceptance || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
  const rejection   = (l.reasons_for_rejection  || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
  const suggestions = (l.suggestions            || []).map(s => `<li>${escapeHtml(s)}</li>`).join('');
  return `
    <tr class="cmp-row cmp-row--llm">
      <td class="cmp-toggle-cell"><span class="cmp-toggle">▸</span></td>
      <td><span class="cmp-tag cmp-tag--llm">LLM</span></td>
      <td class="muted">${escapeHtml(runLabel || '—')}</td>
      <td>${escapeHtml(l.agent || '?')}</td>
      <td class="cmp-num">${rating}</td>
      <td class="cmp-num">${conf}</td>
    </tr>
    <tr class="cmp-detail" hidden>
      <td colspan="6">
        ${field('Sommario', l.summary)}
        ${field('Significato e novità', l.significance_and_novelty)}
        ${acceptance  ? `<div class="cmp-field-label">Motivi accettazione</div><ul class="cmp-list">${acceptance}</ul>` : ''}
        ${rejection   ? `<div class="cmp-field-label">Motivi rifiuto</div><ul class="cmp-list">${rejection}</ul>` : ''}
        ${suggestions ? `<div class="cmp-field-label">Suggerimenti</div><ul class="cmp-list">${suggestions}</ul>` : ''}
      </td>
    </tr>
  `;
}

// ---------------------------------------------------------------------------
// Meta review + Area Chair
// ---------------------------------------------------------------------------

function renderMetaTable(humanMeta, runs) {
  const rows = [];

  if (humanMeta) rows.push(renderHumanMetaRow(humanMeta));

  (runs || []).forEach(rc => {
    const runLabel = rc.run_description || rc.run_id;
    if (rc.llm_meta_review) rows.push(renderLlmMetaRow(rc.llm_meta_review, runLabel));
    if (rc.llm_area_chair)  rows.push(renderAreaChairRow(rc.llm_area_chair, runLabel));
  });

  if (!rows.length) return '';

  return `
    <div class="cmp-section-label">Meta Review (elencata)</div>
    <table class="cmp-table">
      <thead>
        <tr>
          <th class="cmp-th-toggle"></th>
          <th>Tipo</th>
          <th>Run</th>
          <th>Ruolo</th>
          <th>Valutazione</th>
        </tr>
      </thead>
      <tbody>${rows.join('')}</tbody>
    </table>
  `;
}

function renderHumanMetaRow(hm) {
  return `
    <tr class="cmp-row cmp-row--human">
      <td class="cmp-toggle-cell"><span class="cmp-toggle">▸</span></td>
      <td><span class="cmp-tag cmp-tag--human">Umano</span></td>
      <td class="muted">—</td>
      <td>Area Chair</td>
      <td>${hm.recommendation ? escapeHtml(hm.recommendation) : '—'}</td>
    </tr>
    <tr class="cmp-detail" hidden>
      <td colspan="5">
        ${field('Testo', hm.text)}
        ${field('Raccomandazione', hm.recommendation)}
      </td>
    </tr>
  `;
}

function renderLlmMetaRow(lm, runLabel) {
  const keyPoints = (lm.key_points || []).map(k => `<li>${escapeHtml(k)}</li>`).join('');
  const score = (lm.overall_score !== null && lm.overall_score !== undefined) ? `${lm.overall_score}/10` : '—';
  return `
    <tr class="cmp-row cmp-row--llm">
      <td class="cmp-toggle-cell"><span class="cmp-toggle">▸</span></td>
      <td><span class="cmp-tag cmp-tag--llm">LLM</span></td>
      <td class="muted">${escapeHtml(runLabel || '—')}</td>
      <td>Meta Reviewer</td>
      <td>${score}</td>
    </tr>
    <tr class="cmp-detail" hidden>
      <td colspan="5">
        ${field('Sommario', lm.summary)}
        ${keyPoints ? `<div class="cmp-field-label">Punti chiave</div><ul class="cmp-list">${keyPoints}</ul>` : ''}
        ${field('Raccomandazione', lm.recommendation)}
      </td>
    </tr>
  `;
}

function renderAreaChairRow(ac, runLabel) {
  const badge = decisionBadge(ac.decision || '');
  return `
    <tr class="cmp-row cmp-row--llm">
      <td class="cmp-toggle-cell"><span class="cmp-toggle">▸</span></td>
      <td><span class="cmp-tag cmp-tag--llm">LLM</span></td>
      <td class="muted">${escapeHtml(runLabel || '—')}</td>
      <td>Area Chair</td>
      <td>${ac.decision ? `<span class="badge badge--sm ${badge.cls}">${badge.label}</span>` : '—'}</td>
    </tr>
    <tr class="cmp-detail" hidden>
      <td colspan="5">
        ${ac.confidence != null ? `<div class="cmp-field-label">Confidence</div><div class="cmp-text">${ac.confidence}/5</div>` : ''}
        ${field('Sommario', ac.summary)}
        ${field('Motivazione', ac.justification)}
      </td>
    </tr>
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
