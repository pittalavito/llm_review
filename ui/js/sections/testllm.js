/**
 * sections/testllm.js — Test LLM section.
 *
 * render() — builds and returns the DOM subtree (no side effects).
 * mount(el) — attaches form logic, sends messages, updates bubble list.
 */

import { testLlm, listModels } from '../api.js';

/** @returns {HTMLElement} */
export function render() {
  const el = document.createElement('div');
  el.className = 'test-llm-section';
  el.innerHTML = `
    <div class="test-llm-model-bar" id="test-llm-model-bar">
      <label class="test-llm-model-bar__label" for="model-select">Test LLM:</label>
      <select class="test-llm-model-bar__select" id="model-select">
        <option value="">Loading…</option>
      </select>

      <label class="test-llm-model-bar__label" for="temperature-input">Temperature:</label>
      <input
        class="test-llm-model-bar__temperature"
        id="temperature-input"
        type="range"
        min="0.1"
        max="1"
        step="0.1"
        value="1"
      />
      <span class="test-llm-model-bar__temperature-value" id="temperature-value">1.0</span>
    </div>

    <div class="test-llm-messages" id="test-llm-messages">
      <div class="test-llm-welcome">
        <span class="test-llm-welcome__icon">📝</span>
        <h3 class="test-llm-welcome__heading">Session</h3>
        <p class="test-llm-welcome__text">Submit a message to test the LLM.</p>
      </div>
    </div>

    <form class="test-llm-input-bar" id="test-llm-form" novalidate>
      <input
        class="test-llm-input"
        id="test-llm-input"
        type="text"
        placeholder="Enter text to test…"
        autocomplete="off"
        maxlength="2000"
      />
      <button class="btn btn--primary test-llm-send-btn" type="submit">
        Test
      </button>
    </form>
  `;
  return el;
}

/** @param {HTMLElement} container */
export function mount(container) {
  const form = container.querySelector('#test-llm-form');
  const input = container.querySelector('#test-llm-input');
  const messages = container.querySelector('#test-llm-messages');
  const sendBtn = form.querySelector('button[type="submit"]');
  const modelSelect = container.querySelector('#model-select');
  const temperatureInput = container.querySelector('#temperature-input');
  const temperatureValue = container.querySelector('#temperature-value');

  // Load available models into the select
  listModels()
    .then(clients => {
      modelSelect.innerHTML = '';
      for (const name of clients) {
        const opt = document.createElement('option');
        opt.value = name;
        opt.textContent = name;
        modelSelect.appendChild(opt);
      }

      if (!modelSelect.value && clients.length > 0) {
        modelSelect.value = clients[0];
      }
    })
    .catch(() => {
      modelSelect.innerHTML = '<option value="">Error loading</option>';
    });

  /**
   * Append a message bubble.
   * @param {string} text
   * @param {'user' | 'bot'} role
   * @returns {HTMLElement}
   */
  function appendBubble(text, role) {
    const welcome = messages.querySelector('.test-llm-welcome');
    if (welcome) welcome.remove();

    const bubble = document.createElement('div');
    bubble.className = `test-llm-bubble test-llm-bubble--${role}`;
    bubble.textContent = text;
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  /** @param {boolean} locked */
  function setLocked(locked) {
    input.disabled = locked;
    sendBtn.disabled = locked;
    modelSelect.disabled = locked;
    temperatureInput.disabled = locked;
  }

  function readTemperature() {
    const parsed = Number.parseFloat(temperatureInput.value);
    if (!Number.isFinite(parsed)) return 1;
    if (parsed < 0.1) return 0.1;
    if (parsed > 1) return 1;
    return parsed;
  }

  function renderTemperatureValue() {
    temperatureValue.textContent = readTemperature().toFixed(1);
  }

  temperatureInput.addEventListener('input', renderTemperatureValue);
  renderTemperatureValue();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const message = input.value.trim();
    if (!message) return;

    input.value = '';
    setLocked(true);

    const selectedModel = modelSelect.value || 'mock';
    const selectedTemperature = readTemperature();
    appendBubble(message, 'user');

    const loadingEl = document.createElement('div');
    loadingEl.className = 'test-llm-bubble test-llm-bubble--bot';
    loadingEl.innerHTML = `
      <span class="loading-dots">
        <span></span><span></span><span></span>
      </span>`;
    messages.appendChild(loadingEl);
    messages.scrollTop = messages.scrollHeight;

    try {
      const data = await testLlm(message, selectedModel, selectedTemperature);
      loadingEl.remove();
      appendBubble(data.response, 'bot');
    } catch (err) {
      loadingEl.remove();
      const errBubble = appendBubble(`Error: ${err.message}`, 'bot');
      errBubble.classList.add('test-llm-bubble--error');
    } finally {
      setLocked(false);
      input.focus();
    }
  });

  input.focus();
}
