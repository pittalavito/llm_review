/**
 * sections/testagent.js — Test Agent section.
 */

import { listAgents, listModels, testAgent } from '../api.js';

/** @returns {HTMLElement} */
export function render() {
  const el = document.createElement('section');
  el.className = 'test-agent-section';
  el.innerHTML = `
    <h2 class="section-title">Test Agent</h2>
    <p class="section-description">Choose an agent, select a model, and submit text for a guided analysis run.</p>

    <div class="card test-agent-intro">
      <div class="card__header">
        <span class="card__title">How this test works</span>
      </div>
      <div class="card__body test-agent-intro__body">
        <p class="test-agent-intro__text">The tool agent can inspect your text, compute basic statistics, and return a concise explanation of the result.</p>
        <p class="test-agent-intro__text">Use the <strong>mock</strong> model for a quick local check, or switch to an Ollama model to test the real integration.</p>
      </div>
    </div>

    <div class="test-agent-model-bar">
      <div class="test-agent-model-bar__group">
        <label class="test-agent-model-bar__label" for="test-agent-agent">Agent</label>
        <select class="test-agent-model-bar__select" id="test-agent-agent">
          <option value="">Loading…</option>
        </select>
      </div>

      <div class="test-agent-model-bar__group">
        <label class="test-agent-model-bar__label" for="test-agent-model">Model</label>
        <select class="test-agent-model-bar__select" id="test-agent-model">
          <option value="">Loading…</option>
        </select>
      </div>

      <div class="test-agent-model-bar__group test-agent-model-bar__group--temperature">
        <label class="test-agent-model-bar__label" for="test-agent-temperature">Temperature</label>
        <div class="test-agent-model-bar__temperature-wrap">
          <input
            class="test-agent-model-bar__temperature"
            id="test-agent-temperature"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value="0.7"
          />
          <span class="test-agent-model-bar__temperature-value" id="test-agent-temperature-value">0.7</span>
        </div>
      </div>
    </div>

    <form class="test-agent-form" id="test-agent-form" novalidate>
      <div class="test-agent-form__header">
        <label class="test-agent-form__label" for="test-agent-message">Text to analyze</label>
        <span class="test-agent-form__counter" id="test-agent-message-counter">0 / 8000</span>
      </div>
      <textarea
        class="test-agent-form__textarea"
        id="test-agent-message"
        rows="8"
        maxlength="8000"
        placeholder="Paste an abstract, a review comment, or any text you want the agent to inspect..."
      ></textarea>

      <p class="test-agent-form__hint">Tip: longer text works, but keeping the input focused gives clearer tool output.</p>

      <div class="test-agent-form__actions">
        <button class="btn btn--primary" id="test-agent-post-btn" type="submit">Run Agent</button>
      </div>
    </form>

    <div class="card test-agent-response" id="test-agent-response" hidden>
      <div class="card__header">
        <span class="badge" id="test-agent-response-badge"></span>
        <span class="card__title" id="test-agent-response-title">Response</span>
      </div>
      <pre class="card__body" id="test-agent-response-body"></pre>
    </div>
  `;
  return el;
}

/** @param {HTMLElement} container */
export function mount(container) {
  const form = container.querySelector('#test-agent-form');
  const postBtn = container.querySelector('#test-agent-post-btn');
  const agentSelect = container.querySelector('#test-agent-agent');
  const modelSelect = container.querySelector('#test-agent-model');
  const temperatureInput = container.querySelector('#test-agent-temperature');
  const temperatureValue = container.querySelector('#test-agent-temperature-value');
  const messageInput = container.querySelector('#test-agent-message');
  const messageCounter = container.querySelector('#test-agent-message-counter');
  const responseCard = container.querySelector('#test-agent-response');
  const responseBadge = container.querySelector('#test-agent-response-badge');
  const responseTitle = container.querySelector('#test-agent-response-title');
  const responseBody = container.querySelector('#test-agent-response-body');

  function setLoading(loading) {
    postBtn.disabled = loading;
    agentSelect.disabled = loading;
    modelSelect.disabled = loading;
    temperatureInput.disabled = loading;
    messageInput.disabled = loading;
    postBtn.textContent = loading ? 'Running…' : 'Run Agent';
  }

  function readTemperature() {
    const parsed = Number.parseFloat(temperatureInput.value);
    if (!Number.isFinite(parsed)) return 1;
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

  function showResponse(title, data, isError = false) {
    responseTitle.textContent = title;
    responseBody.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    responseBadge.textContent = isError ? 'Error' : 'Completed';
    responseBadge.className = isError ? 'badge badge--error' : 'badge badge--success';
    responseCard.classList.toggle('test-agent-response--error', isError);
    responseCard.hidden = false;
  }

  temperatureInput.addEventListener('input', renderTemperatureValue);
  messageInput.addEventListener('input', renderMessageCounter);
  renderTemperatureValue();
  renderMessageCounter();

  Promise.all([listAgents(), listModels()])
    .then(([agents, models]) => {
      agentSelect.innerHTML = '';
      for (const agent of agents) {
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

      if (agents.includes('test_tool_agent')) {
        agentSelect.value = 'test_tool_agent';
      }
      if (models.includes('mock')) {
        modelSelect.value = 'mock';
      }
    })
    .catch((err) => {
      agentSelect.innerHTML = '<option value="">Unavailable</option>';
      modelSelect.innerHTML = '<option value="">Unavailable</option>';
      showResponse('Configuration error', err.message, true);
    });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const message = messageInput.value.trim();
    if (!agentSelect.value || !modelSelect.value) {
      showResponse('Configuration error', 'Load agents and models before running the test.', true);
      return;
    }

    if (!message) {
      showResponse('Validation error', 'Add some text before running the agent.', true);
      return;
    }

    setLoading(true);
    responseCard.hidden = true;
    try {
      const payload = {
        name: agentSelect.value,
        model: modelSelect.value,
        temperature: readTemperature(),
        message,
      };
      const data = await testAgent(payload);
      showResponse(`Result for ${payload.name} on ${payload.model}`, data);
    } catch (err) {
      showResponse('Agent run failed', err.message, true);
    } finally {
      setLoading(false);
    }
  });

  messageInput.focus();
}
