/**
 * sections/graph.js — Graph configuration and execution section.
 */

import { getGraphConfig, listAgents, listModels, putGraphConfig, runGraph } from '../api.js';

function clampTemperature(value) {
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed)) return 0.7;
  if (parsed < 0) return 0;
  if (parsed > 1) return 1;
  return parsed;
}

function parseOptionalInteger(value) {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const parsed = Number.parseInt(trimmed, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

export function render() {
  const el = document.createElement('section');
  el.className = 'graph-section';
  el.innerHTML = `
    <h2 class="section-title">Graph</h2>
    <p class="section-description">Compile the reviewer graph configuration, then run it on a paper draft or abstract.</p>

    <div class="graph-layout">
      <div class="graph-panel card">
        <div class="card__header">
          <span class="card__title">Graph Configuration</span>
        </div>
        <div class="card__body graph-panel__body">
          <form class="graph-form" id="graph-config-form" novalidate>
            <div class="graph-grid">
              <label class="graph-field">
                <span class="graph-field__label">Methodology Reviewer Agent</span>
                <select class="graph-field__control" id="graph-agent-select">
                  <option value="">Loading…</option>
                </select>
              </label>

              <label class="graph-field">
                <span class="graph-field__label">Methodology Reviewer Model</span>
                <select class="graph-field__control" id="graph-model-select">
                  <option value="">Loading…</option>
                </select>
              </label>

              <label class="graph-field">
                <span class="graph-field__label">Temperature</span>
                <div class="graph-temperature-row">
                  <input
                    class="graph-field__range"
                    id="graph-temperature-input"
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value="0.7"
                  />
                  <span class="graph-temperature-value" id="graph-temperature-value">0.7</span>
                </div>
              </label>

              <label class="graph-field">
                <span class="graph-field__label">Max Iterations</span>
                <input class="graph-field__control" id="graph-iterations-input" type="number" min="1" max="20" value="3" />
              </label>

              <label class="graph-field graph-field--full">
                <span class="graph-field__label">Max Tokens</span>
                <input class="graph-field__control" id="graph-max-tokens-input" type="number" min="1" placeholder="Optional" />
              </label>
            </div>

            <div class="graph-actions">
              <button class="btn btn--primary" id="graph-compile-btn" type="submit">Compile Graph</button>
            </div>
          </form>

          <div class="graph-status card" id="graph-status-card" hidden>
            <div class="card__header">
              <span class="badge" id="graph-status-badge"></span>
              <span class="card__title" id="graph-status-title">Current Configuration</span>
            </div>
            <pre class="card__body" id="graph-status-body"></pre>
          </div>
        </div>
      </div>

      <div class="graph-panel card">
        <div class="card__header">
          <span class="card__title">Run Graph</span>
        </div>
        <div class="card__body graph-panel__body">
          <form class="graph-form" id="graph-run-form" novalidate>
            <div class="graph-field graph-field--full">
              <div class="graph-field__header">
                <span class="graph-field__label">Paper Text</span>
                <span class="graph-field__meta" id="graph-paper-counter">0 / 20000</span>
              </div>
              <textarea
                class="graph-textarea"
                id="graph-paper-input"
                rows="12"
                maxlength="20000"
                placeholder="Paste the paper abstract, review draft, or methodology section you want to evaluate..."
              ></textarea>
            </div>

            <div class="graph-actions">
              <button class="btn btn--primary" id="graph-run-btn" type="submit">Run Graph</button>
            </div>
          </form>

          <div class="graph-result card" id="graph-result-card" hidden>
            <div class="card__header">
              <span class="badge" id="graph-result-badge"></span>
              <span class="card__title" id="graph-result-title">Graph Result</span>
            </div>
            <pre class="card__body" id="graph-result-body"></pre>
          </div>
        </div>
      </div>
    </div>
  `;
  return el;
}

export function mount(container) {
  const configForm = container.querySelector('#graph-config-form');
  const runForm = container.querySelector('#graph-run-form');
  const agentSelect = container.querySelector('#graph-agent-select');
  const modelSelect = container.querySelector('#graph-model-select');
  const temperatureInput = container.querySelector('#graph-temperature-input');
  const temperatureValue = container.querySelector('#graph-temperature-value');
  const iterationsInput = container.querySelector('#graph-iterations-input');
  const maxTokensInput = container.querySelector('#graph-max-tokens-input');
  const compileButton = container.querySelector('#graph-compile-btn');
  const statusCard = container.querySelector('#graph-status-card');
  const statusBadge = container.querySelector('#graph-status-badge');
  const statusTitle = container.querySelector('#graph-status-title');
  const statusBody = container.querySelector('#graph-status-body');
  const paperInput = container.querySelector('#graph-paper-input');
  const paperCounter = container.querySelector('#graph-paper-counter');
  const runButton = container.querySelector('#graph-run-btn');
  const resultCard = container.querySelector('#graph-result-card');
  const resultBadge = container.querySelector('#graph-result-badge');
  const resultTitle = container.querySelector('#graph-result-title');
  const resultBody = container.querySelector('#graph-result-body');

  let graphCompiled = false;

  function setBootstrapLoading(loading) {
    agentSelect.disabled = loading;
    modelSelect.disabled = loading;
    temperatureInput.disabled = loading;
    iterationsInput.disabled = loading;
    maxTokensInput.disabled = loading;
    compileButton.disabled = loading;
    paperInput.disabled = loading || !graphCompiled;
    runButton.disabled = loading || !graphCompiled;
  }

  function setCompileLoading(loading) {
    compileButton.disabled = loading;
    agentSelect.disabled = loading;
    modelSelect.disabled = loading;
    temperatureInput.disabled = loading;
    iterationsInput.disabled = loading;
    maxTokensInput.disabled = loading;
    compileButton.textContent = loading ? 'Compiling…' : 'Compile Graph';
    paperInput.disabled = loading || !graphCompiled;
    runButton.disabled = loading || !graphCompiled;
  }

  function setRunLoading(loading) {
    runButton.disabled = loading || !graphCompiled;
    paperInput.disabled = loading || !graphCompiled;
    runButton.textContent = loading ? 'Running…' : 'Run Graph';
  }

  function setGraphCompiled(compiled) {
    graphCompiled = compiled;
    paperInput.disabled = !compiled;
    runButton.disabled = !compiled;
    runButton.title = compiled ? '' : 'Compile the graph configuration before running it.';
  }

  function showStatus(title, payload, isError = false) {
    statusTitle.textContent = title;
    statusBody.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    statusBadge.textContent = isError ? 'Error' : 'Ready';
    statusBadge.className = isError ? 'badge badge--error' : 'badge badge--success';
    statusCard.hidden = false;
  }

  function showResult(title, payload, isError = false) {
    resultTitle.textContent = title;
    resultBody.textContent = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
    resultBadge.textContent = isError ? 'Error' : 'Completed';
    resultBadge.className = isError ? 'badge badge--error' : 'badge badge--success';
    resultCard.hidden = false;
  }

  function renderTemperatureValue() {
    temperatureValue.textContent = clampTemperature(temperatureInput.value).toFixed(1);
  }

  function renderPaperCounter() {
    paperCounter.textContent = `${paperInput.value.length} / 20000`;
  }

  function applyConfig(config) {
    if (!config) {
      setGraphCompiled(false);
      return;
    }

    agentSelect.value = config.methodology_reviewer_agent;
    modelSelect.value = config.methodology_reviewer_model;
    temperatureInput.value = String(clampTemperature(config.methodology_reviewer_temperature));
    iterationsInput.value = String(config.max_iterations);
    maxTokensInput.value = config.max_tokens == null ? '' : String(config.max_tokens);
    renderTemperatureValue();
    setGraphCompiled(true);
    showStatus('Current Configuration', config);
  }

  function buildConfigPayload() {
    const iterations = Number.parseInt(iterationsInput.value, 10);
    const maxTokens = parseOptionalInteger(maxTokensInput.value);

    return {
      methodology_reviewer_agent: agentSelect.value,
      methodology_reviewer_model: modelSelect.value,
      methodology_reviewer_temperature: clampTemperature(temperatureInput.value),
      max_iterations: Number.isFinite(iterations) ? iterations : 3,
      max_tokens: maxTokens,
    };
  }

  temperatureInput.addEventListener('input', renderTemperatureValue);
  paperInput.addEventListener('input', renderPaperCounter);
  renderTemperatureValue();
  renderPaperCounter();
  setGraphCompiled(false);
  setBootstrapLoading(true);
  showStatus('Loading Graph Setup', 'Loading agents, models, and the current graph configuration...');

  Promise.all([listAgents(), listModels(), getGraphConfig()])
    .then(([agents, models, config]) => {
      agentSelect.innerHTML = '';
      const supportedAgents = agents.filter((agent) => agent === 'methodology_reviewer');
      for (const agent of supportedAgents) {
        const option = document.createElement('option');
        option.value = agent;
        option.textContent = agent;
        agentSelect.appendChild(option);
      }

      modelSelect.innerHTML = '';
      for (const model of models) {
        const option = document.createElement('option');
        option.value = model;
        option.textContent = model;
        modelSelect.appendChild(option);
      }

      if (supportedAgents.includes('methodology_reviewer')) {
        agentSelect.value = 'methodology_reviewer';
      }
      if (models.includes('mock')) {
        modelSelect.value = 'mock';
      }

      applyConfig(config);
      if (!config) {
        showStatus('No Graph Configuration Yet', 'Compile a configuration before running the graph. The run form will unlock automatically after a successful compile.');
      }
    })
    .catch((err) => {
      agentSelect.innerHTML = '<option value="">Unavailable</option>';
      modelSelect.innerHTML = '<option value="">Unavailable</option>';
      setGraphCompiled(false);
      showStatus('Configuration Error', err.message, true);
    })
    .finally(() => {
      setBootstrapLoading(false);
    });

  configForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    if (!agentSelect.value || !modelSelect.value) {
      showStatus('Configuration Error', 'Load agents and models before compiling the graph.', true);
      return;
    }

    setCompileLoading(true);
    try {
      const payload = buildConfigPayload();
      const config = await putGraphConfig(payload);
      applyConfig(config);
      showStatus('Graph Compiled', config);
    } catch (err) {
      setGraphCompiled(false);
      showStatus('Graph Compile Failed', err.message, true);
    } finally {
      setCompileLoading(false);
    }
  });

  runForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const paper = paperInput.value.trim();
    if (!paper) {
      showResult('Validation Error', 'Add some paper text before running the graph.', true);
      return;
    }

    setRunLoading(true);
    resultCard.hidden = true;
    try {
      const result = await runGraph({ paper });
      showResult(`Graph Result (${result.reviews.length} review${result.reviews.length === 1 ? '' : 's'})`, result);
    } catch (err) {
      showResult('Graph Run Failed', err.message, true);
    } finally {
      setRunLoading(false);
    }
  });

  paperInput.focus();
}
