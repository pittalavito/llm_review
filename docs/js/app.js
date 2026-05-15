// docs/js/app.js — Demo SPA: Pipeline, Graph Config, Storico
import { loadRuns, _config } from './data.js';

// ─── Constants ────────────────────────────────────────
const AGENT_LABELS = {
  reviewer_1:    '🔬 Reviewer 1',
  reviewer_2:    '🔬 Reviewer 2',
  reviewer_3:    '🔬 Reviewer 3',
  meta_reviewer: '📋 Meta Reviewer',
  area_chair:    '🪑 Area Chair',
  author_agent:  '✍️ Author Agent',
};

const DECISION_BADGE = {
  accept:         { label: 'ACCEPT',         cls: 'badge--accept' },
  minor_revision: { label: 'MINOR REVISION', cls: 'badge--minor' },
  major_revision: { label: 'MAJOR REVISION', cls: 'badge--major' },
  reject:         { label: 'REJECT',         cls: 'badge--reject' },
};

// ─── State ────────────────────────────────────────────
let runs = [];
let currentSection = 'pipeline';
let selectedRunId = null;
let selectedConfigRunId = null; // for Graph Config section

// ─── Router ───────────────────────────────────────────
function navigate(section) {
  currentSection = section;
  selectedRunId = null;
  document.querySelectorAll('.nav__item').forEach(el => {
    el.classList.toggle('nav__item--active', el.dataset.section === section);
  });
  render();
}

// ─── Helpers ──────────────────────────────────────────
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function decisionBadge(d) {
  const key = String(d || '').toLowerCase();
  const b = DECISION_BADGE[key] || { label: (d || 'n/a').toUpperCase(), cls: 'badge--unknown' };
  return `<span class="badge ${b.cls}">${b.label}</span>`;
}

function agentLabel(name) {
  return AGENT_LABELS[name] || escapeHtml(name || 'unknown');
}

function shortPaper(path) {
  if (!path) return '—';
  return path.replace(/^.*[\\/]/, '').replace(/\.pdf$/i, '');
}

function fmtTs(ts) {
  if (!ts) return '—';
  return String(ts).replace('T', ' ').slice(0, 19);
}

function renderList(items, label = '') {
  if (!Array.isArray(items) || !items.length) return '';
  const lis = items.map(s => `<li>${escapeHtml(s)}</li>`).join('');
  return `${label ? `<p class="gr-list-title">${label}</p>` : ''}<ul>${lis}</ul>`;
}

function renderPersona(p) {
  if (!p || typeof p !== 'object') return '<span class="muted">—</span>';
  const pills = Object.entries(p)
    .filter(([, v]) => v != null && v !== '')
    .map(([k, v]) => `<span class="persona-pill" title="${escapeHtml(k)}">${escapeHtml(v)}</span>`)
    .join(' ');
  return pills || '<span class="muted">—</span>';
}

// ─── Section: Pipeline ────────────────────────────────
function renderPipeline() {
  return `
    <div class="section">
      <h2 class="section__title">Review Pipeline Architecture</h2>
      <p class="section__desc">
        Multi-agent peer review pipeline: fan-out a 3 reviewer paralleli, meta-reviewer di
        aggregazione, area chair che emette la decisione, e loop iterativo di revisione autore.
      </p>
      <div class="pipeline-svg-container">
        <object data="pipeline.svg" type="image/svg+xml" style="max-width:720px;width:100%">
          Pipeline SVG
        </object>
      </div>
      <div class="gr-card" style="margin-top:var(--s-6)">
        <div class="gr-card-title">Flow Summary</div>
        <table class="gr-config-table">
          <thead><tr><th>Step</th><th>Agente</th><th>Descrizione</th></tr></thead>
          <tbody>
            <tr><td>1</td><td><code>fan-out</code></td><td>Paper dispatched ai 3 reviewer in parallelo</td></tr>
            <tr><td>2</td><td><code>reviewer ×3</code></td><td>Soundness · Empirical · Novelty — review indipendenti con BM25 RAG</td></tr>
            <tr><td>3</td><td><code>meta_reviewer</code></td><td>Aggrega le review in un summary + rating</td></tr>
            <tr><td>4</td><td><code>area_chair</code></td><td>Decisione: accept | minor_revision | major_revision | reject</td></tr>
            <tr><td>5</td><td><code>author_agent</code></td><td>Note di revisione + rebuttal (se revise); loop sui reviewer</td></tr>
          </tbody>
        </table>
      </div>
    </div>`;
}

// ─── Section: Graph Config ────────────────────────────
function renderGraphConfig() {
  if (!runs.length) {
    return `<div class="section"><h2 class="section__title">Graph Config</h2><p class="muted">Nessuna run caricata.</p></div>`;
  }

  const activeId = selectedConfigRunId || runs[0].run_id;
  const run = runs.find(r => r.run_id === activeId) || runs[0];
  const gc = run.graph_config || { agents: [], max_rounds: null };

  const options = runs.map(r => `
    <option value="${escapeHtml(r.run_id)}" ${r.run_id === run.run_id ? 'selected' : ''}>
      ${escapeHtml(r.run_id)}
    </option>`).join('');

  const rows = (gc.agents || []).map(a => {
    const personaOrStyle = a.area_chair_style
      ? `<span class="persona-pill" title="area_chair_style">${escapeHtml(a.area_chair_style)}</span>`
      : renderPersona(a.reviewer_persona);
    return `
      <tr>
        <td>${agentLabel(a.agent_name)}</td>
        <td><code>${escapeHtml(a.model || '—')}</code></td>
        <td>${a.temperature ?? '—'}</td>
        <td>${personaOrStyle}</td>
      </tr>`;
  }).join('');

  return `
    <div class="section">
      <h2 class="section__title">Graph Config</h2>
      <p class="section__desc">Configurazione del grafo per la run selezionata. Ogni agente ha modello, temperatura e persona/style.</p>

      <div class="gr-card">
        <div class="gr-card-header-row">
          <div class="gr-card-title" style="margin:0;padding:0;border:none">Run</div>
          <select id="gc-run-select" class="form-select" style="max-width:380px">${options}</select>
        </div>
        <div class="gr-config-meta" style="margin-top:var(--s-3)">
          <strong>Max rounds:</strong> ${gc.max_rounds ?? '—'} &nbsp;|&nbsp;
          <strong>Paper:</strong> ${escapeHtml(shortPaper(run.paper_path))} &nbsp;|&nbsp;
          <strong>Decision:</strong> ${decisionBadge(run.decision)}
        </div>
        <table class="gr-config-table" style="margin-top:var(--s-4)">
          <thead><tr><th>Agente</th><th>Modello</th><th>Temp</th><th>Persona / Style</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" class="muted">Nessun agente configurato</td></tr>'}</tbody>
        </table>
      </div>
    </div>`;
}

// ─── Section: Storico (History) ───────────────────────
function renderStorico() {
  if (selectedRunId) return renderRunDetail();

  if (!runs.length) {
    return `
      <div class="section">
        <h2 class="section__title">Review History</h2>
        <p class="muted">Nessuna run disponibile — pubblica i JSON in <code>resource/results/</code> e aggiorna <code>index.json</code>.</p>
      </div>`;
  }

  const listRows = runs.map(r => `
    <div class="sto-row" data-run="${escapeHtml(r.run_id)}">
      <span class="sto-ts">${fmtTs(r.timestamp)}</span>
      <span class="sto-paper">${escapeHtml(shortPaper(r.paper_path))}</span>
      ${decisionBadge(r.decision)}
      <span class="sto-rounds">${r.total_rounds} round${r.total_rounds !== 1 ? 's' : ''}</span>
      <button class="btn btn--ghost btn--sm">Esplora →</button>
    </div>`).join('');

  return `
    <div class="section">
      <h2 class="section__title">Review History</h2>
      <p class="section__desc">Tutte le run del pipeline. Clicca una riga per i dettagli completi.</p>
      <div class="sto-list">${listRows}</div>
    </div>`;
}

function renderReviewCard(rev) {
  const p = rev.payload || {};
  const rating = p.rating ?? p.overall_rating;
  const confidence = p.confidence;

  let body = '';
  if (p.summary)                  body += `<p>${escapeHtml(p.summary)}</p>`;
  if (p.significance_and_novelty) body += `<p class="gr-list-title">Significance & Novelty</p><p>${escapeHtml(p.significance_and_novelty)}</p>`;
  body += renderList(p.reasons_for_acceptance, 'Reasons for acceptance');
  body += renderList(p.reasons_for_rejection,  'Reasons for rejection');
  body += renderList(p.strengths,              'Strengths');
  body += renderList(p.weaknesses,             'Weaknesses');
  body += renderList(p.suggestions,            'Suggestions');
  if (p.review_text) body += `<p>${escapeHtml(p.review_text)}</p>`;
  if (p.raw)         body += `<pre class="gr-pre">${escapeHtml(p.raw)}</pre>`;

  let trace = '';
  if (rev.input_message || rev.context_used) {
    trace = `
      <details class="gr-trace">
        <summary>Input & RAG context</summary>
        ${rev.input_message ? `<p class="gr-list-title">Input message</p><pre class="gr-pre">${escapeHtml(rev.input_message)}</pre>` : ''}
        ${rev.context_used  ? `<p class="gr-list-title">Context used</p><pre class="gr-pre">${escapeHtml(rev.context_used)}</pre>`   : ''}
      </details>`;
  }

  return `
    <details class="gr-review" open>
      <summary class="gr-review-summary">
        <span>${agentLabel(rev.agent)}</span>
        ${rating != null      ? `<span class="gr-score">${escapeHtml(rating)}/10</span>` : ''}
        ${confidence != null  ? `<span class="gr-conf">conf: ${escapeHtml(confidence)}</span>` : ''}
      </summary>
      <div class="gr-review-body">
        ${body || '<p class="muted">Payload non strutturato</p>'}
        ${trace}
      </div>
    </details>`;
}

function renderMetaReview(mr) {
  if (!mr) return '';
  return `
    <div class="gr-card">
      <div class="gr-card-title">📋 Meta Review</div>
      ${mr.summary ? `<p>${escapeHtml(mr.summary)}</p>` : ''}
      ${renderList(mr.key_points, 'Key points')}
      <div class="gr-config-meta" style="margin-top:var(--s-3)">
        ${mr.overall_score != null ? `<strong>Overall score:</strong> ${escapeHtml(mr.overall_score)}/10 &nbsp;|&nbsp;` : ''}
        ${mr.recommendation ? `<strong>Recommendation:</strong> ${decisionBadge(mr.recommendation)}` : ''}
      </div>
    </div>`;
}

function renderAreaChair(ac) {
  if (!ac) return '';
  return `
    <div class="gr-card">
      <div class="gr-card-title">🪑 Area Chair</div>
      ${ac.summary       ? `<p>${escapeHtml(ac.summary)}</p>` : ''}
      ${ac.justification ? `<p class="gr-list-title">Justification</p><p>${escapeHtml(ac.justification)}</p>` : ''}
      <div class="gr-config-meta" style="margin-top:var(--s-3)">
        ${ac.decision   ? `<strong>Decision:</strong> ${decisionBadge(ac.decision)} &nbsp;|&nbsp;` : ''}
        ${ac.confidence != null ? `<strong>Confidence:</strong> ${escapeHtml(ac.confidence)}` : ''}
      </div>
    </div>`;
}

function renderAuthorResponse(ar) {
  if (!ar) return '';
  const rebuttals = Array.isArray(ar.reviewer_rebuttals) ? ar.reviewer_rebuttals : [];
  const revised   = Array.isArray(ar.revised_sections)   ? ar.revised_sections   : [];

  const rebuttalsHtml = rebuttals.map(r => `
    <details class="gr-review">
      <summary class="gr-review-summary"><span>↳ ${agentLabel(r.reviewer_name)}</span></summary>
      <div class="gr-review-body"><p>${escapeHtml(r.response || '')}</p></div>
    </details>`).join('');

  const revisedHtml = revised.map(s => `
    <details class="gr-review">
      <summary class="gr-review-summary"><span>📝 ${escapeHtml(s.section_name || 'Section')}</span></summary>
      <div class="gr-review-body"><p>${escapeHtml(s.content || '')}</p></div>
    </details>`).join('');

  return `
    <div class="gr-card">
      <div class="gr-card-title">✍️ Author Response</div>
      ${ar.rebuttal ? `<p>${escapeHtml(ar.rebuttal)}</p>` : ''}
      ${renderList(ar.key_changes, 'Key changes')}
      ${rebuttalsHtml ? `<p class="gr-list-title">Reviewer rebuttals</p>${rebuttalsHtml}` : ''}
      ${revisedHtml   ? `<p class="gr-list-title">Revised sections</p>${revisedHtml}`     : ''}
    </div>`;
}

function renderRetrievalMeta(rm) {
  if (!rm) return '';
  return `
    <div class="gr-config-meta" style="margin-top:var(--s-2)">
      <strong>RAG:</strong>
      paper=<code>${escapeHtml(rm.paper_path || '—')}</code>,
      index=<code>${escapeHtml(rm.index_status || '—')}</code>,
      chunks=${rm.chunk_count_retrieved ?? '—'}/${rm.chunk_count_total ?? '—'},
      top_k=${rm.top_k ?? '—'}
    </div>`;
}

function renderRunDetail() {
  const run = runs.find(r => r.run_id === selectedRunId);
  if (!run) return '<p class="muted">Run non trovata</p>';

  const reviewCards = run.reviews.map(renderReviewCard).join('');

  return `
    <div class="section">
      <div class="sto-detail-header">
        <button class="btn btn--ghost btn--sm" id="back-btn">← Storico</button>
        ${decisionBadge(run.decision)}
        <span class="sto-detail-meta">${fmtTs(run.timestamp)} · ${escapeHtml(shortPaper(run.paper_path))} · ${run.total_rounds} round${run.total_rounds !== 1 ? 's' : ''}</span>
      </div>

      <div class="gr-card">
        <div class="gr-card-title">Run · ${escapeHtml(run.run_id)}</div>
        <div class="gr-config-meta">
          <strong>Source:</strong> <code>${escapeHtml(run.source_file)}</code>
        </div>
        ${renderRetrievalMeta(run.retrieval_metadata)}
      </div>

      <div class="gr-card">
        <div class="gr-card-title">Reviewers</div>
        ${reviewCards || '<p class="muted">Nessuna review</p>'}
      </div>

      ${renderMetaReview(run.meta_review)}
      ${renderAreaChair(run.area_chair_response)}
      ${renderAuthorResponse(run.author_response)}
    </div>`;
}

// ─── Render & Mount ───────────────────────────────────
function render() {
  const el = document.getElementById('content-area');
  switch (currentSection) {
    case 'pipeline':     el.innerHTML = renderPipeline();    break;
    case 'graph-config': el.innerHTML = renderGraphConfig(); break;
    case 'storico':      el.innerHTML = renderStorico();     break;
  }
  mount();
}

function mount() {
  document.querySelectorAll('.nav__item[data-section]').forEach(el => {
    el.onclick = () => navigate(el.dataset.section);
  });

  document.querySelectorAll('.sto-row[data-run]').forEach(el => {
    el.onclick = () => { selectedRunId = el.dataset.run; render(); };
  });

  const back = document.getElementById('back-btn');
  if (back) back.onclick = () => { selectedRunId = null; render(); };

  const gcSel = document.getElementById('gc-run-select');
  if (gcSel) gcSel.onchange = () => { selectedConfigRunId = gcSel.value; render(); };
}

// ─── Init ─────────────────────────────────────────────
async function init() {
  const el = document.getElementById('content-area');
  el.innerHTML = '<div class="section"><p class="muted">Caricamento run da GitHub…</p></div>';

  try {
    runs = await loadRuns();
  } catch (err) {
    const url = `${_config.RAW_BASE}/${_config.INDEX_FILE}`;
    el.innerHTML = `
      <div class="section">
        <h2 class="section__title">Errore caricamento</h2>
        <p class="error-msg">${escapeHtml(err.message)}</p>
        <p class="muted">URL tentato: <code>${escapeHtml(url)}</code></p>
        <p class="muted">Verifica i meta <code>gh-owner/repo/branch</code> in <code>index.html</code>, che il repo sia pubblico, e che <code>${escapeHtml(_config.INDEX_FILE)}</code> esista in <code>${escapeHtml(_config.RESULTS_PATH)}/</code>.</p>
      </div>`;
    mount();
    return;
  }

  render();
}

init();
