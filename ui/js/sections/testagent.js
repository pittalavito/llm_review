/**
 * sections/testagent.js — Test Agent section.
 */

import {
  listAgents,
  listModels,
  previewAgentPrompt,
  testAgent,
} from '../api.js';

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
  if (summary) {
    sections.push(`Summary\n${summary}`);
  }

  const strengths = formatList('Strengths', payload.strengths);
  if (strengths) sections.push(strengths);

  const weaknesses = formatList('Weaknesses', payload.weaknesses);
  if (weaknesses) sections.push(weaknesses);

  const recommendations = formatList('Recommendations', payload.recommendations);
  if (recommendations) sections.push(recommendations);

  const confidence = asText(payload.confidence);
  if (confidence) {
    sections.push(`Confidence\n${confidence}`);
  }

  if (sections.length === 1) {
    sections.push(JSON.stringify(payload, null, 2));
  }
  return sections.join('\n\n');
}

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
        <button class="btn btn--secondary" id="test-agent-preview-btn" type="button">Preview Prompt</button>
        <button class="btn btn--primary" id="test-agent-post-btn" type="submit">Run Agent</button>
      </div>
    </form>

    <div class="card test-agent-prompt-card" id="test-agent-prompt-card" hidden>
      <div class="card__header">
        <span class="badge badge--info" id="test-agent-prompt-badge">Prompt Preview</span>
        <span class="card__title" id="test-agent-prompt-title">Assembled Prompt</span>
      </div>
      <div class="card__body test-agent-prompt-card__body">
        <div class="test-agent-prompt-section" id="test-agent-prompt-section-system">
          <details open>
            <summary class="test-agent-prompt-section__title">System Prompt</summary>
            <pre class="test-agent-prompt-section__body" id="test-agent-prompt-system"></pre>
          </details>
        </div>
        <div class="test-agent-prompt-section" id="test-agent-prompt-section-schema">
          <details open>
            <summary class="test-agent-prompt-section__title">Format Rules &amp; JSON Schema</summary>
            <pre class="test-agent-prompt-section__body" id="test-agent-prompt-schema"></pre>
          </details>
        </div>
        <div class="test-agent-prompt-section">
          <details open>
            <summary class="test-agent-prompt-section__title">Message Section</summary>
            <pre class="test-agent-prompt-section__body" id="test-agent-prompt-message"></pre>
          </details>
        </div>
        <div class="test-agent-prompt-section">
          <details>
            <summary class="test-agent-prompt-section__title">Full Prompt (assembled)</summary>
            <pre class="test-agent-prompt-section__body" id="test-agent-prompt-full"></pre>
          </details>
        </div>
      </div>
    </div>

    <div class="card test-agent-response" id="test-agent-response" hidden>
      <div class="card__header">
        <span class="badge" id="test-agent-response-badge"></span>
        <span class="card__title" id="test-agent-response-title">Response</span>
      </div>
      <div class="card__body test-agent-response__body">
        <pre id="test-agent-response-body"></pre>
        <details class="test-agent-raw-output" id="test-agent-raw-output" hidden>
          <summary class="test-agent-raw-output__summary">Raw LLM output</summary>
          <pre class="test-agent-raw-output__body" id="test-agent-raw-output-body"></pre>
        </details>
      </div>
    </div>
  `;
  return el;
}

/** @param {HTMLElement} container */
export function mount(container) {
  const form = container.querySelector('#test-agent-form');
  const postBtn = container.querySelector('#test-agent-post-btn');
  const previewBtn = container.querySelector('#test-agent-preview-btn');
  const agentSelect = container.querySelector('#test-agent-agent');
  const modelSelect = container.querySelector('#test-agent-model');
  const temperatureInput = container.querySelector('#test-agent-temperature');
  const temperatureValue = container.querySelector('#test-agent-temperature-value');
  const messageInput = container.querySelector('#test-agent-message');
  const messageCounter = container.querySelector('#test-agent-message-counter');

  const promptCard = container.querySelector('#test-agent-prompt-card');
  const promptTitle = container.querySelector('#test-agent-prompt-title');
  const promptSystem = container.querySelector('#test-agent-prompt-system');
  const promptSchema = container.querySelector('#test-agent-prompt-schema');
  const promptMessage = container.querySelector('#test-agent-prompt-message');
  const promptFull = container.querySelector('#test-agent-prompt-full');

  const responseCard = container.querySelector('#test-agent-response');
  const responseBadge = container.querySelector('#test-agent-response-badge');
  const responseTitle = container.querySelector('#test-agent-response-title');
  const responseBody = container.querySelector('#test-agent-response-body');
  const rawOutputDetails = container.querySelector('#test-agent-raw-output');
  const rawOutputBody = container.querySelector('#test-agent-raw-output-body');

  function setLoading(loading) {
    postBtn.disabled = loading;
    previewBtn.disabled = loading;
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

  function showResponse(title, data, rawOutput = null, isError = false) {
    responseTitle.textContent = title;
    responseBody.textContent = isError
      ? (typeof data === 'string' ? data : JSON.stringify(data, null, 2))
      : formatAgentResponse(data);
    responseBadge.textContent = isError ? 'Error' : 'Completed';
    responseBadge.className = isError ? 'badge badge--error' : 'badge badge--success';
    responseCard.classList.toggle('test-agent-response--error', isError);

    if (rawOutput) {
      rawOutputBody.textContent = rawOutput;
      rawOutputDetails.hidden = false;
    } else {
      rawOutputDetails.hidden = true;
      rawOutputBody.textContent = '';
    }

    responseCard.hidden = false;
  }

  function showPromptPreview(agent, data) {
    promptTitle.textContent = `Prompt for ${agent}`;
    promptSystem.textContent = data.system_prompt || '(empty)';
    promptSchema.textContent = data.schema_instructions || '(none)';
    promptMessage.textContent = data.message_section || '(empty)';
    promptFull.textContent = data.full_prompt || '(empty)';
    promptCard.hidden = false;
  }

  temperatureInput.addEventListener('input', renderTemperatureValue);
  messageInput.addEventListener('input', renderMessageCounter);
  renderTemperatureValue();
  renderMessageCounter();

  previewBtn.addEventListener('click', async () => {
    const message = messageInput.value.trim();
    if (!agentSelect.value) {
      showResponse('Configuration error', 'Select an agent before previewing the prompt.', null, true);
      return;
    }
    if (!message) {
      showResponse('Validation error', 'Add some text before previewing the prompt.', null, true);
      return;
    }

    setLoading(true);
    promptCard.hidden = true;
    try {
      const data = await previewAgentPrompt({ name: agentSelect.value, message });
      showPromptPreview(agentSelect.value, data);
    } catch (err) {
      showResponse('Prompt preview failed', err.message, null, true);
    } finally {
      setLoading(false);
    }
  });

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
      showResponse('Agent run failed', err.message, err.llmRawOutput || null, true);
    } finally {
      setLoading(false);
    }
  });

  messageInput.focus();
}
