/**
 * sections/storico.js — Review History section.
 * Lists past graph runs and allows exploring per-agent traces.
 */

import { listRuns, getRun } from '../api.js';

const AGENT_LABELS = {
  reviewer_1:    '🔬 Reviewer 1',
  reviewer_2:    '🔬 Reviewer 2',
  reviewer_3:    '🔬 Reviewer 3',
  meta_reviewer: '📋 Meta Reviewer',
  area_chair:    '🪑 Area Chair',
  author_agent:  '✍️  Author Agent',
};

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
  el.className = 'section storico';
  el.innerHTML = `
    <div class="storico-header">
      <h2 class="section__title">Storico Review</h2>
      <button id="sto-refresh" class="btn btn--ghost">🔄 Aggiorna</button>
    </div>
    <p class="section__desc">Esplora i run passati — espandi ogni agente per vedere input, contesto RAG e risposta.</p>
    <div id="sto-error" class="error-msg" hidden></div>
    <div id="sto-list" class="sto-list"></div>
    <div id="sto-detail" class="sto-detail" hidden></div>
  `;
  return el;
}

// ---------------------------------------------------------------------------
// mount
// ---------------------------------------------------------------------------

export async function mount(el) {
  const listPane   = el.querySelector('#sto-list');
  const detailPane = el.querySelector('#sto-detail');
  const errorDiv   = el.querySelector('#sto-error');
  const refreshBtn = el.querySelector('#sto-refresh');

  const loadList = async () => {
    listPane.innerHTML = '<p class="muted">Caricamento…</p>';
    detailPane.hidden = true;
    hideError(errorDiv);
    try {
      const runs = await listRuns();
      renderList(listPane, runs, onRunClick);
    } catch (e) {
      showError(errorDiv, `Errore: ${e.message}`);
      listPane.innerHTML = '';
    }
  };

  const onRunClick = async (runId) => {
    detailPane.hidden = true;
    detailPane.innerHTML = '<p class="muted">Caricamento dettaglio…</p>';
    detailPane.hidden = false;
    detailPane.scrollIntoView({ behavior: 'smooth', block: 'start' });
    try {
      const record = await getRun(runId);
      renderDetail(detailPane, record);
    } catch (e) {
      detailPane.innerHTML = `<p class="error-msg">${e.message}</p>`;
    }
  };

  refreshBtn.addEventListener('click', loadList);
  await loadList();
}

// ---------------------------------------------------------------------------
// List rendering
// ---------------------------------------------------------------------------

function renderList(container, runs, onRunClick) {
  if (!runs.length) {
    container.innerHTML = '<p class="muted">Nessun run trovato. Esegui il pipeline dalla sezione Graph Run.</p>';
    return;
  }

  container.innerHTML = runs.map(run => {
    const decision = (run.decision || 'unknown').toLowerCase();
    const badge    = DECISION_BADGE[decision] || { label: decision.toUpperCase(), cls: 'badge--unknown' };
    const ts       = formatTimestamp(run.timestamp);
    const rounds   = run.total_rounds;
    return `
      <div class="sto-row" data-run-id="${run.run_id}">
        <span class="sto-ts">${ts}</span>
        <span class="sto-paper">${run.paper_path}</span>
        <span class="badge ${badge.cls}">${badge.label}</span>
        <span class="sto-rounds">${rounds} round${rounds !== 1 ? 's' : ''}</span>
        <button class="btn btn--ghost btn--sm sto-open-btn">Esplora →</button>
      </div>
    `;
  }).join('');

  container.querySelectorAll('.sto-open-btn').forEach(btn => {
    const row   = btn.closest('.sto-row');
    const runId = row.dataset.runId;
    btn.addEventListener('click', () => onRunClick(runId));
  });
}

// ---------------------------------------------------------------------------
// Detail rendering
// ---------------------------------------------------------------------------

function renderDetail(container, record) {
  const decision = (record.decision || 'unknown').toLowerCase();
  const badge    = DECISION_BADGE[decision] || { label: decision.toUpperCase(), cls: 'badge--unknown' };
  const ts       = formatTimestamp(record.timestamp);

  // Group agent_runs by round
  const byRound = {};
  for (const ar of (record.agent_runs || [])) {
    const r = ar.round ?? 0;
    if (!byRound[r]) byRound[r] = [];
    byRound[r].push(ar);
  }

  const roundsHtml = Object.entries(byRound)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([round, runs]) => renderRound(Number(round), runs))
    .join('');

  container.innerHTML = `
    <div class="sto-detail-header">
      <button id="sto-back-btn" class="btn btn--ghost btn--sm">← Storico</button>
      <span class="badge ${badge.cls}">${badge.label}</span>
      <span class="sto-detail-meta">${ts} · ${record.paper_path} · ${record.total_rounds} round${record.total_rounds !== 1 ? 's' : ''}</span>
    </div>
    ${renderGraphConfig(record.graph_config)}
    ${roundsHtml}
    ${record.author_response ? renderAuthorResponse(record.author_response) : ''}
  `;

  container.querySelector('#sto-back-btn').addEventListener('click', () => {
    container.hidden = true;
  });
}

function renderGraphConfig(config) {
  if (!config) return '';
  const agents  = config.agents || [];
  const maxRounds = config.max_rounds ?? '?';
  const rows = agents.map(a => {
    let persona = '';
    if (a.reviewer_persona) {
      const p = a.reviewer_persona;
      persona = `${p.commitment} · ${p.intention} · ${p.knowledgeability}`;
    } else if (a.area_chair_style) {
      persona = a.area_chair_style;
    }
    return `
    <tr>
      <td>${AGENT_LABELS[a.agent_name] || a.agent_name}</td>
      <td><code>${a.model}</code></td>
      <td>${a.temperature}</td>
      <td class="muted">${persona}</td>
    </tr>
  `;
  }).join('');
  return `
    <details class="sto-config-block">
      <summary class="sto-config-summary">⚙️ Configurazione agenti · max rounds: ${maxRounds}</summary>
      <table class="sto-config-table">
        <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th><th>Persona / Style</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </details>
  `;
}

function renderRound(round, agentRuns) {
  const runsHtml = agentRuns.map(ar => renderAgentTrace(ar)).join('');
  return `
    <div class="sto-round">
      <div class="sto-round-title">Round ${round + 1}</div>
      ${runsHtml}
    </div>
  `;
}

function renderAgentTrace(ar) {
  const label   = AGENT_LABELS[ar.agent] || ar.agent;
  const payload = ar.response_payload || {};
  const summary = payload.summary || payload.rebuttal || '';
  const rating  = payload.rating ?? null;
  const recommendation = payload.recommendation ?? null;
  const decision = payload.decision ?? null;
  const displayDecision = recommendation || decision;

  const contextSection = ar.context_used
    ? `<details class="trace-section">
        <summary>📄 Context RAG</summary>
        <pre class="trace-pre">${escapeHtml(ar.context_used)}</pre>
       </details>`
    : `<div class="trace-section trace-section--empty">Nessun contesto RAG.</div>`;

  const acceptanceHtml = (payload.reasons_for_acceptance || []).map(s => `<li>${s}</li>`).join('');
  const rejectionHtml  = (payload.reasons_for_rejection  || []).map(w => `<li>${w}</li>`).join('');
  const suggestionsHtml = (payload.suggestions || []).map(s => `<li>${s}</li>`).join('');
  const changesHtml    = (payload.key_changes || []).map(c => `<li>${c}</li>`).join('');

  const decisionBadge = displayDecision
    ? `<span class="badge badge--sm ${(DECISION_BADGE[displayDecision] || {cls:''}).cls}">${displayDecision}</span>`
    : '';

  return `
    <details class="sto-agent-trace">
      <summary class="sto-agent-summary">
        <span>${label}</span>
        ${rating !== null ? `<span class="gr-score">${rating}/10</span>` : ''}
        ${decisionBadge}
      </summary>
      <div class="sto-agent-body">

        <details class="trace-section">
          <summary>💬 Input inviato</summary>
          <pre class="trace-pre">${escapeHtml(ar.input_message || '')}</pre>
        </details>

        ${contextSection}

        <details class="trace-section" open>
          <summary>✅ Risposta</summary>
          <div class="trace-response">
            ${summary ? `<p><strong>Summary:</strong> ${summary}</p>` : ''}
            ${payload.significance_and_novelty ? `<p><strong>Significance &amp; Novelty:</strong> ${payload.significance_and_novelty}</p>` : ''}
            ${rating !== null ? `<p><strong>Rating:</strong> ${rating}/10</p>` : ''}
            ${payload.confidence != null ? `<p><strong>Confidence:</strong> ${payload.confidence}/5</p>` : ''}
            ${displayDecision ? `<p><strong>Decision/Recommendation:</strong> ${displayDecision}</p>` : ''}
            ${payload.justification ? `<p><strong>Justification:</strong> ${payload.justification}</p>` : ''}
            ${acceptanceHtml ? `<p><strong>Reasons for acceptance:</strong></p><ul>${acceptanceHtml}</ul>` : ''}
            ${rejectionHtml  ? `<p><strong>Reasons for rejection:</strong></p><ul>${rejectionHtml}</ul>` : ''}
            ${suggestionsHtml ? `<p><strong>Suggestions:</strong></p><ul>${suggestionsHtml}</ul>` : ''}
            ${changesHtml    ? `<p><strong>Key changes:</strong></p><ul>${changesHtml}</ul>` : ''}
            ${!summary && rating === null && !displayDecision && !acceptanceHtml ? `<pre class="trace-pre">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>` : ''}
          </div>
        </details>

      </div>
    </details>
  `;
}

function renderAuthorResponse(authorResponse) {
  const rebuttal = authorResponse.rebuttal || '';
  const keyChanges = (authorResponse.key_changes || []).map(c => `<li>${c}</li>`).join('');
  const sections = authorResponse.revised_sections || [];
  const revisedSections = sections.map(s => `
      <details class="trace-section">
        <summary>[Revised ${(s.section_name || '').toUpperCase()}]</summary>
        <pre class="trace-pre">${escapeHtml(s.content || '')}</pre>
      </details>
    `).join('');
  const rebuttals = (authorResponse.reviewer_rebuttals || []).map(r => `
      <details class="trace-section">
        <summary>${r.reviewer_name}</summary>
        <p>${escapeHtml(r.response || '')}</p>
      </details>
    `).join('');
  return `
    <div class="sto-round">
      <div class="sto-round-title">✍️ Author Response</div>
      ${rebuttal ? `<p class="sto-revision-notes"><strong>General Rebuttal:</strong> ${rebuttal}</p>` : ''}
      ${rebuttals ? `<p><strong>Per-Reviewer Rebuttals:</strong></p>${rebuttals}` : ''}
      ${keyChanges ? `<p><strong>Key Changes:</strong></p><ul>${keyChanges}</ul>` : ''}
      ${revisedSections}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' });
  } catch { return iso; }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function showError(el, msg) { el.textContent = msg; el.hidden = false; }
function hideError(el)      { el.hidden = true; }
