/**
 * sections/testrag.js — Test RAG section.
 *
 * Covers the following /llm-review endpoints:
 *   GET  /papers                    → listPapers()
 *   POST /papers/index              → indexPaper()
 *   GET  /papers/indexed            → listIndexedPapers()
 *   GET  /papers/indexed/detail     → getIndexedPaperDetail()
 *   POST /agents/retrieval          → testAgentWithRetrieval()
 */

import {
  listAgents,
  listModels,
  listPapers,
  indexPaper,
  listIndexedPapers,
  getIndexedPaperDetail,
  testAgentWithRetrieval,
} from '../api.js';

// ── helpers ──────────────────────────────────────────────────────────────────

function asText(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value.trim();
  return String(value).trim();
}

function formatList(title, items) {
  if (!Array.isArray(items) || items.length === 0) return '';
  const lines = [title];
  for (const item of items) {
    const content = asText(item);
    if (content) lines.push(`- ${content}`);
  }
  return lines.length > 1 ? lines.join('\n') : '';
}

function formatAgentResponse(data) {
  if (!data || typeof data !== 'object') {
    return typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  }

  const agent = asText(data.agent) || 'unknown_agent';
  const payload = data.payload;
  if (!payload || typeof payload !== 'object') {
    return `[${agent}]\n${JSON.stringify(payload, null, 2)}`;
  }

  const sections = [`[${agent}]`];
  const summary = asText(payload.summary) || asText(payload.analysis);
  if (summary) sections.push(`Summary\n${summary}`);

  const strengths = formatList('Strengths', payload.strengths);
  if (strengths) sections.push(strengths);

  const weaknesses = formatList('Weaknesses', payload.weaknesses);
  if (weaknesses) sections.push(weaknesses);

  const recommendations = formatList('Recommendations', payload.recommendations);
  if (recommendations) sections.push(recommendations);

  const confidence = asText(payload.confidence);
  if (confidence) sections.push(`Confidence\n${confidence}`);

  if (sections.length === 1) sections.push(JSON.stringify(payload, null, 2));
  return sections.join('\n\n');
}

// ── render ───────────────────────────────────────────────────────────────────

/** @returns {HTMLElement} */
export function render() {
  const el = document.createElement('section');
  el.className = 'test-rag-section';
  el.innerHTML = `
    <h2 class="section-title">Test RAG</h2>
    <p class="section-description">Index a paper, inspect the index, then run an agent with RAG-augmented context.</p>

    <!-- ── Paper management ───────────────────────────── -->
    <div class="test-rag-grid">

      <div class="card test-rag-card">
        <div class="card__header">
          <span class="card__title">1) Select &amp; Index Paper</span>
        </div>
        <div class="card__body test-rag-card__body">
          <div class="test-rag-field">
            <label class="test-rag-field__label" for="rag-paper-select">Paper</label>
            <select class="test-rag-field__control" id="rag-paper-select">
              <option value="">Loading…</option>
            </select>
          </div>

          <label class="test-rag-checkbox">
            <input type="checkbox" id="rag-force-reindex" />
            <span>Force reindex</span>
          </label>

          <div class="test-rag-actions">
            <button class="btn btn--secondary" id="rag-index-btn" type="button">Index Paper</button>
          </div>

          <div class="card test-rag-result" id="rag-index-result" hidden>
            <div class="card__header">
              <span class="badge" id="rag-index-badge">Index</span>
              <span class="card__title" id="rag-index-title">Index Result</span>
            </div>
            <div class="card__body">
              <pre id="rag-index-body"></pre>
            </div>
          </div>
        </div>
      </div>

      <div class="card test-rag-card">
        <div class="card__header">
          <span class="card__title">2) Index Status</span>
          <button class="btn btn--secondary btn--sm" id="rag-refresh-indexed-btn" type="button">Refresh</button>
        </div>
        <div class="card__body test-rag-card__body">
          <ul class="test-rag-indexed-list" id="rag-indexed-list">
            <li class="test-rag-indexed-list__empty">Loading…</li>
          </ul>

          <div class="card test-rag-result" id="rag-detail-result" hidden>
            <div class="card__header">
              <span class="badge badge--info">Detail</span>
              <span class="card__title" id="rag-detail-title">Index Detail</span>
            </div>
            <div class="card__body">
              <pre id="rag-detail-body"></pre>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Agent config + run ─────────────────────────── -->
    <div class="card test-rag-card test-rag-run-card">
      <div class="card__header">
        <span class="card__title">3) Run Agent with Retrieval</span>
      </div>
      <div class="card__body">

        <div class="test-rag-model-bar">
          <div class="test-rag-model-bar__group">
            <label class="test-rag-model-bar__label" for="rag-agent-select">Agent</label>
            <select class="test-rag-model-bar__select" id="rag-agent-select">
              <option value="">Loading…</option>
            </select>
          </div>

          <div class="test-rag-model-bar__group">
            <label class="test-rag-model-bar__label" for="rag-model-select">Model</label>
            <select class="test-rag-model-bar__select" id="rag-model-select">
              <option value="">Loading…</option>
            </select>
          </div>

          <div class="test-rag-model-bar__group test-rag-model-bar__group--temperature">
            <label class="test-rag-model-bar__label" for="rag-temperature">Temperature</label>
            <div class="test-rag-model-bar__temperature-wrap">
              <input
                class="test-rag-model-bar__temperature"
                id="rag-temperature"
                type="range"
                min="0"
                max="1"
                step="0.1"
                value="0.7"
              />
              <span class="test-rag-model-bar__temperature-value" id="rag-temperature-value">0.7</span>
            </div>
          </div>

          <div class="test-rag-model-bar__group">
            <label class="test-rag-model-bar__label" for="rag-top-k">top_k</label>
            <input
              class="test-rag-model-bar__select"
              id="rag-top-k"
              type="number"
              min="1"
              max="20"
              placeholder="default"
              style="width: 80px;"
            />
          </div>
        </div>

        <form class="test-rag-form" id="rag-run-form" novalidate>
          <div class="test-rag-form__header">
            <label class="test-rag-form__label" for="rag-message">Query / message</label>
            <span class="test-rag-form__counter" id="rag-message-counter">0 / 8000</span>
          </div>
          <textarea
            class="test-rag-form__textarea"
            id="rag-message"
            rows="6"
            maxlength="8000"
            placeholder="Enter the query to inject into the agent together with RAG context…"
          ></textarea>

          <p class="test-rag-form__hint">The selected paper will be indexed (if needed) and the top-k retrieved chunks will be prepended to the agent's input message.</p>

          <div class="test-rag-form__actions">
            <button class="btn btn--primary" id="rag-run-btn" type="submit">Run Agent + RAG</button>
          </div>
        </form>

        <div class="card test-rag-response" id="rag-response" hidden>
          <div class="card__header">
            <span class="badge" id="rag-response-badge"></span>
            <span class="card__title" id="rag-response-title">Response</span>
          </div>
          <div class="card__body test-rag-response__body">
            <pre id="rag-response-body"></pre>
            <details class="test-rag-raw-output" id="rag-raw-output" hidden>
              <summary class="test-rag-raw-output__summary">Raw LLM output</summary>
              <pre class="test-rag-raw-output__body" id="rag-raw-output-body"></pre>
            </details>
          </div>
        </div>

      </div>
    </div>
  `;
  return el;
}

// ── mount ────────────────────────────────────────────────────────────────────

/** @param {HTMLElement} container */
export function mount(container) {
  // ── DOM refs ──
  const paperSelect = container.querySelector('#rag-paper-select');
  const forceReindexCheckbox = container.querySelector('#rag-force-reindex');
  const indexBtn = container.querySelector('#rag-index-btn');
  const indexResult = container.querySelector('#rag-index-result');
  const indexBadge = container.querySelector('#rag-index-badge');
  const indexTitle = container.querySelector('#rag-index-title');
  const indexBody = container.querySelector('#rag-index-body');

  const indexedList = container.querySelector('#rag-indexed-list');
  const refreshIndexedBtn = container.querySelector('#rag-refresh-indexed-btn');
  const detailResult = container.querySelector('#rag-detail-result');
  const detailTitle = container.querySelector('#rag-detail-title');
  const detailBody = container.querySelector('#rag-detail-body');

  const agentSelect = container.querySelector('#rag-agent-select');
  const modelSelect = container.querySelector('#rag-model-select');
  const temperatureInput = container.querySelector('#rag-temperature');
  const temperatureValue = container.querySelector('#rag-temperature-value');
  const topKInput = container.querySelector('#rag-top-k');

  const form = container.querySelector('#rag-run-form');
  const runBtn = container.querySelector('#rag-run-btn');
  const messageInput = container.querySelector('#rag-message');
  const messageCounter = container.querySelector('#rag-message-counter');

  const responseCard = container.querySelector('#rag-response');
  const responseBadge = container.querySelector('#rag-response-badge');
  const responseTitle = container.querySelector('#rag-response-title');
  const responseBody = container.querySelector('#rag-response-body');
  const rawOutputDetails = container.querySelector('#rag-raw-output');
  const rawOutputBody = container.querySelector('#rag-raw-output-body');

  // ── helpers ──
  function readTemperature() {
    const parsed = Number.parseFloat(temperatureInput.value);
    if (!Number.isFinite(parsed)) return 0.7;
    if (parsed < 0) return 0;
    if (parsed > 1) return 1;
    return parsed;
  }

  function renderTemperatureValue() {
    temperatureValue.textContent = readTemperature().toFixed(1);
  }

  function renderMessageCounter() {
    messageCounter.textContent = `${messageInput.value.length} / 8000`;
  }

  function showIndexResult(title, data, isError) {
    indexTitle.textContent = title;
    indexBody.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    indexBadge.textContent = isError ? 'Error' : 'OK';
    indexBadge.className = isError ? 'badge badge--error' : 'badge badge--success';
    indexResult.hidden = false;
  }

  function showResponse(title, data, rawOutput, isError) {
    responseTitle.textContent = title;
    responseBody.textContent = isError
      ? (typeof data === 'string' ? data : JSON.stringify(data, null, 2))
      : formatAgentResponse(data);
    responseBadge.textContent = isError ? 'Error' : 'Completed';
    responseBadge.className = isError ? 'badge badge--error' : 'badge badge--success';
    responseCard.classList.toggle('test-rag-response--error', isError);

    if (rawOutput) {
      rawOutputBody.textContent = rawOutput;
      rawOutputDetails.hidden = false;
    } else {
      rawOutputDetails.hidden = true;
      rawOutputBody.textContent = '';
    }

    responseCard.hidden = false;
  }

  function setRunLoading(loading) {
    runBtn.disabled = loading;
    agentSelect.disabled = loading;
    modelSelect.disabled = loading;
    temperatureInput.disabled = loading;
    messageInput.disabled = loading;
    runBtn.textContent = loading ? 'Running…' : 'Run Agent + RAG';
  }

  // ── load indexed papers list ──
  function loadIndexedPapers() {
    indexedList.innerHTML = '<li class="test-rag-indexed-list__empty">Loading…</li>';
    detailResult.hidden = true;
    listIndexedPapers()
      .then((papers) => {
        if (!papers.length) {
          indexedList.innerHTML = '<li class="test-rag-indexed-list__empty">No indexed papers yet.</li>';
          return;
        }
        indexedList.innerHTML = '';
        for (const paper of papers) {
          const li = document.createElement('li');
          li.className = 'test-rag-indexed-list__item';
          li.title = 'Click to see index detail';
          li.textContent = paper;
          li.addEventListener('click', () => loadPaperDetail(paper, li));
          indexedList.appendChild(li);
        }
      })
      .catch((err) => {
        indexedList.innerHTML = `<li class="test-rag-indexed-list__empty test-rag-indexed-list__empty--error">${err.message}</li>`;
      });
  }

  // ── load detail for a specific paper ──
  function loadPaperDetail(paperPath, activeEl) {
    container.querySelectorAll('.test-rag-indexed-list__item').forEach(el => {
      el.classList.toggle('test-rag-indexed-list__item--active', el === activeEl);
    });
    detailTitle.textContent = paperPath.split(/[\\/]/).pop();
    detailBody.textContent = 'Loading…';
    detailResult.hidden = false;
    getIndexedPaperDetail(paperPath)
      .then((data) => {
        detailBody.textContent = JSON.stringify(data, null, 2);
      })
      .catch((err) => {
        detailBody.textContent = `Error: ${err.message}`;
      });
  }

  // ── load available papers ──
  listPapers()
    .then((papers) => {
      paperSelect.innerHTML = '';
      if (!papers.length) {
        paperSelect.innerHTML = '<option value="">No papers found</option>';
        return;
      }
      for (const paper of papers) {
        const opt = document.createElement('option');
        opt.value = paper;
        opt.textContent = paper;
        paperSelect.appendChild(opt);
      }
    })
    .catch((err) => {
      paperSelect.innerHTML = `<option value="">Error: ${err.message}</option>`;
    });

  // ── load agents + models ──
  Promise.all([listAgents(), listModels()])
    .then(([agents, models]) => {
      agentSelect.innerHTML = '';
      for (const agent of agents) {
        const opt = document.createElement('option');
        opt.value = agent;
        opt.textContent = agent;
        agentSelect.appendChild(opt);
      }

      modelSelect.innerHTML = '';
      for (const model of models) {
        const opt = document.createElement('option');
        opt.value = model;
        opt.textContent = model;
        modelSelect.appendChild(opt);
      }

      if (agents.includes('contribution_reviewer')) agentSelect.value = 'contribution_reviewer';
      if (models.includes('mock')) modelSelect.value = 'mock';
    })
    .catch((err) => {
      agentSelect.innerHTML = '<option value="">Unavailable</option>';
      modelSelect.innerHTML = '<option value="">Unavailable</option>';
    });

  loadIndexedPapers();

  // ── event listeners ──
  temperatureInput.addEventListener('input', renderTemperatureValue);
  messageInput.addEventListener('input', renderMessageCounter);
  renderTemperatureValue();
  renderMessageCounter();

  refreshIndexedBtn.addEventListener('click', loadIndexedPapers);

  indexBtn.addEventListener('click', async () => {
    const paperPath = paperSelect.value;
    if (!paperPath) {
      showIndexResult('Validation error', 'Select a paper first.', true);
      return;
    }
    indexBtn.disabled = true;
    indexBtn.textContent = 'Indexing…';
    indexResult.hidden = true;
    try {
      const data = await indexPaper({
        paper_path: paperPath,
        force_reindex: forceReindexCheckbox.checked,
      });
      showIndexResult(`Indexed: ${paperPath.split(/[\\/]/).pop()}`, data, false);
      loadIndexedPapers();
    } catch (err) {
      showIndexResult('Index failed', err.message, true);
    } finally {
      indexBtn.disabled = false;
      indexBtn.textContent = 'Index Paper';
    }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const paperPath = paperSelect.value;
    if (!paperPath) {
      showResponse('Validation error', 'Select a paper before running.', null, true);
      return;
    }
    if (!agentSelect.value || !modelSelect.value) {
      showResponse('Configuration error', 'Load agents and models before running.', null, true);
      return;
    }
    const message = messageInput.value.trim();
    if (!message) {
      showResponse('Validation error', 'Enter a query message.', null, true);
      return;
    }

    const rawTopK = topKInput.value.trim();
    const topK = rawTopK ? Number.parseInt(rawTopK, 10) : undefined;

    setRunLoading(true);
    responseCard.hidden = true;
    try {
      const payload = {
        name: agentSelect.value,
        model: modelSelect.value,
        temperature: readTemperature(),
        message,
        paper_path: paperPath,
        ...(topK != null && Number.isFinite(topK) && { top_k: topK }),
      };
      const data = await testAgentWithRetrieval(payload);
      showResponse(
        `Result for ${payload.name} — ${paperPath.split(/[\\/]/).pop()}`,
        data,
        null,
        false,
      );
    } catch (err) {
      showResponse('Agent + RAG run failed', err.message, err.llmRawOutput || null, true);
    } finally {
      setRunLoading(false);
    }
  });
}
