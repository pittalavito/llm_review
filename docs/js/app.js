// docs/js/app.js — Demo SPA: Pipeline, Graph Config, Storico
import { loadRuns } from './data.js';

// ─── State ────────────────────────────────────────────
let runs = [];
let currentSection = 'pipeline';
let selectedRunId = null;

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
function decisionBadge(d) {
  const cls = d === 'accept' ? 'accept'
    : d === 'minor_revision' ? 'minor'
    : d === 'major_revision' ? 'major'
    : d === 'reject' ? 'reject' : 'unknown';
  return `<span class="badge badge--${cls}">${d || 'n/a'}</span>`;
}

function shortPaper(path) {
  if (!path) return '—';
  return path.replace(/^.*[\\/]/, '').replace(/\.pdf$/i, '');
}

function fmtTs(ts) {
  if (!ts) return '—';
  return ts.replace('T', ' ').slice(0, 19);
}

// ─── Section: Pipeline ────────────────────────────────
function renderPipeline() {
  return `
    <div class="section">
      <h2 class="section__title">Review Pipeline Architecture</h2>
      <p class="section__desc">
        Multi-agent peer review pipeline with parallel fan-out to 3 specialized reviewers,
        meta-reviewer aggregation, area chair decision, and iterative author revision loop.
      </p>
      <div class="pipeline-svg-container">
        <object data="pipeline.svg" type="image/svg+xml" style="max-width:720px;width:100%">
          Pipeline SVG
        </object>
      </div>
      <div class="gr-card" style="margin-top:var(--s-6)">
        <div class="gr-card-title">Flow Summary</div>
        <table class="gr-config-table">
          <thead><tr><th>Step</th><th>Agent</th><th>Description</th></tr></thead>
          <tbody>
            <tr><td>1</td><td><code>fan-out</code></td><td>Paper dispatched to 3 reviewers in parallel</td></tr>
            <tr><td>2</td><td><code>reviewer ×3</code></td><td>Soundness · Empirical · Novelty — independent reviews with BM25 RAG</td></tr>
            <tr><td>3</td><td><code>meta-reviewer</code></td><td>Aggregates reviews into summary + rating</td></tr>
            <tr><td>4</td><td><code>area-chair</code></td><td>Decision: accept | minor_revision | major_revision</td></tr>
            <tr><td>5</td><td><code>author</code></td><td>Revision notes + rebuttal (if revise); loops back to reviewers</td></tr>
          </tbody>
        </table>
      </div>
    </div>`;
}

// ─── Section: Graph Config ────────────────────────────
function renderGraphConfig() {
  // Use config from first available run
  const run = runs[0];
  if (!run || !run.graph_config) {
    return `<div class="section"><h2 class="section__title">Graph Config</h2><p class="muted">No runs loaded yet.</p></div>`;
  }
  const gc = run.graph_config;
  const agents = gc.agents || {};
  const rows = Object.entries(agents).map(([name, cfg]) => `
    <tr>
      <td><code>${name}</code></td>
      <td>${cfg.model || '—'}</td>
      <td>${cfg.temperature ?? '—'}</td>
      <td>${cfg.persona || '—'}</td>
    </tr>`).join('');

  return `
    <div class="section">
      <h2 class="section__title">Graph Config</h2>
      <p class="section__desc">Configuration used for the most recent run. Each agent has an LLM model, temperature, and persona axis.</p>
      <div class="gr-card">
        <div class="gr-card-title">Run: ${run.run_id}</div>
        <div class="gr-config-meta">
          <strong>Max rounds:</strong> ${gc.max_rounds ?? '—'} &nbsp;|&nbsp;
          <strong>Paper:</strong> ${shortPaper(run.paper_path)}
        </div>
        <table class="gr-config-table">
          <thead><tr><th>Agent</th><th>Model</th><th>Temp</th><th>Persona</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" class="muted">No agent config</td></tr>'}</tbody>
        </table>
      </div>
    </div>`;
}

// ─── Section: Storico (History) ───────────────────────
function renderStorico() {
  if (selectedRunId) return renderRunDetail();

  const listRows = runs.map(r => `
    <div class="sto-row" data-run="${r.run_id}">
      <span class="sto-ts">${fmtTs(r.timestamp)}</span>
      <span class="sto-paper">${shortPaper(r.paper_path)}</span>
      <span class="sto-rounds">${r.total_rounds} round${r.total_rounds !== 1 ? 's' : ''}</span>
      ${decisionBadge(r.decision)}
      <button class="btn btn--ghost btn--sm">View</button>
    </div>`).join('');

  return `
    <div class="section">
      <h2 class="section__title">Review History</h2>
      <p class="section__desc">All completed pipeline runs. Click a row to see full details.</p>
      ${runs.length ? `<div class="sto-list">${listRows}</div>` : '<p class="muted">No runs available — push review JSONs to resource/results/</p>'}
    </div>`;
}

function renderRunDetail() {
  const run = runs.find(r => r.run_id === selectedRunId);
  if (!run) return '<p class="muted">Run not found</p>';

  // Group reviews by round
  const rounds = {};
  for (const rev of run.reviews) {
    const rn = rev.round || 1;
    if (!rounds[rn]) rounds[rn] = [];
    rounds[rn].push(rev);
  }

  let roundsHtml = '';
  for (const [rn, reviews] of Object.entries(rounds)) {
    const reviewCards = reviews.map(rev => {
      const p = rev.payload || {};
      const summary = p.summary || p.review_text || p.rebuttal || p.raw || '';
      const rating = p.overall_rating ?? p.rating ?? '';
      const confidence = p.confidence ?? '';
      const strengths = p.strengths || [];
      const weaknesses = p.weaknesses || [];

      let bodyHtml = '';
      if (summary) bodyHtml += `<p>${summary}</p>`;
      if (strengths.length) {
        bodyHtml += `<p class="gr-list-title">Strengths</p><ul>${strengths.map(s => `<li>${s}</li>`).join('')}</ul>`;
      }
      if (weaknesses.length) {
        bodyHtml += `<p class="gr-list-title">Weaknesses</p><ul>${weaknesses.map(w => `<li>${w}</li>`).join('')}</ul>`;
      }

      return `
        <details class="gr-review">
          <summary class="gr-review-summary">
            <span>${rev.agent_name}</span>
            ${rating ? `<span class="gr-score">${rating}/10</span>` : ''}
            ${confidence ? `<span class="gr-conf">conf: ${confidence}</span>` : ''}
          </summary>
          <div class="gr-review-body">${bodyHtml || '<p class="muted">No structured payload</p>'}</div>
        </details>`;
    }).join('');

    roundsHtml += `
      <div class="sto-round">
        <div class="sto-round-title">Round ${rn}</div>
        ${reviewCards}
      </div>`;
  }

  return `
    <div class="section">
      <div class="sto-detail-header">
        <button class="btn btn--ghost btn--sm" id="back-btn">← Back</button>
        <h2 class="section__title" style="margin-bottom:0">${run.run_id}</h2>
        ${decisionBadge(run.decision)}
      </div>
      <div class="sto-detail-meta">
        ${fmtTs(run.timestamp)} · ${shortPaper(run.paper_path)} · ${run.total_rounds} round(s)
      </div>
      ${roundsHtml}
    </div>`;
}

// ─── Render & Mount ───────────────────────────────────
function render() {
  const el = document.getElementById('content-area');
  switch (currentSection) {
    case 'pipeline': el.innerHTML = renderPipeline(); break;
    case 'graph-config': el.innerHTML = renderGraphConfig(); break;
    case 'storico': el.innerHTML = renderStorico(); break;
  }
  mount();
}

function mount() {
  // Nav clicks
  document.querySelectorAll('.nav__item[data-section]').forEach(el => {
    el.onclick = () => navigate(el.dataset.section);
  });

  // Storico row clicks
  document.querySelectorAll('.sto-row[data-run]').forEach(el => {
    el.onclick = () => { selectedRunId = el.dataset.run; render(); };
  });

  // Back button
  const back = document.getElementById('back-btn');
  if (back) back.onclick = () => { selectedRunId = null; render(); };
}

// ─── Init ─────────────────────────────────────────────
async function init() {
  const el = document.getElementById('content-area');
  el.innerHTML = '<div class="section"><p class="muted">Loading runs from GitHub…</p></div>';

  try {
    runs = await loadRuns();
  } catch (err) {
    el.innerHTML = `<div class="section"><p class="error-msg">Failed to load runs: ${err.message}</p><p class="muted">Make sure the repo is public and resource/results/ contains JSON files.</p></div>`;
    mount();
    return;
  }

  render();
}

init();
