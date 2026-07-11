/** Port of ui/js/sections/testllm.js — single-turn LLM chat tester. */
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { listModels, testLlm } from '../api/client';
import TemperatureSlider from '../components/TemperatureSlider';
import { useOptions } from '../components/useOptions';

interface Bubble {
  role: 'user' | 'bot';
  text: string;
  isError?: boolean;
}

export default function TestLlm() {
  const { options: models, error: modelsError } = useOptions(listModels);
  const [model, setModel] = useState('');
  const [temperature, setTemperature] = useState(1);
  const [message, setMessage] = useState('');
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [locked, setLocked] = useState(false);

  const messagesRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Default to the first model once loaded (vanilla behavior).
  useEffect(() => {
    if (!model && models.length > 0) setModel(models[0]);
  }, [models, model]);

  // Auto-scroll on new bubbles / loading indicator.
  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [bubbles, locked]);

  useEffect(() => { inputRef.current?.focus(); }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = message.trim();
    if (!text || locked) return;

    setMessage('');
    setLocked(true);
    setBubbles((prev) => [...prev, { role: 'user', text }]);

    try {
      const data = await testLlm(text, model || 'mock', temperature);
      const reply = typeof data === 'string' ? data : JSON.stringify(data);
      setBubbles((prev) => [...prev, { role: 'bot', text: reply }]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setBubbles((prev) => [...prev, { role: 'bot', text: `Error: ${msg}`, isError: true }]);
    } finally {
      setLocked(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className="test-llm-section">
      <div className="test-llm-model-bar">
        <label className="test-llm-model-bar__label" htmlFor="model-select">Test LLM:</label>
        <select
          className="test-llm-model-bar__select"
          id="model-select"
          value={model}
          disabled={locked}
          onChange={(e) => setModel(e.target.value)}
        >
          {modelsError && <option value="">Error loading</option>}
          {!modelsError && models.length === 0 && <option value="">Loading…</option>}
          {models.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>

        <label className="test-llm-model-bar__label" htmlFor="temperature-input">Temperature:</label>
        <TemperatureSlider
          id="temperature-input"
          min={0.1}
          max={1}
          value={temperature}
          onChange={setTemperature}
          disabled={locked}
          inputClassName="test-llm-model-bar__temperature"
          valueClassName="test-llm-model-bar__temperature-value"
        />
      </div>

      <div className="test-llm-messages" ref={messagesRef}>
        {bubbles.length === 0 && !locked && (
          <div className="test-llm-welcome">
            <span className="test-llm-welcome__icon">📝</span>
            <h3 className="test-llm-welcome__heading">Session</h3>
            <p className="test-llm-welcome__text">Submit a message to test the LLM.</p>
          </div>
        )}
        {bubbles.map((bubble, i) => (
          <div
            key={i}
            className={
              `test-llm-bubble test-llm-bubble--${bubble.role}` +
              (bubble.isError ? ' test-llm-bubble--error' : '')
            }
          >
            {bubble.text}
          </div>
        ))}
        {locked && (
          <div className="test-llm-bubble test-llm-bubble--bot">
            <span className="loading-dots"><span></span><span></span><span></span></span>
          </div>
        )}
      </div>

      <form className="test-llm-input-bar" noValidate onSubmit={onSubmit}>
        <input
          ref={inputRef}
          className="test-llm-input"
          type="text"
          placeholder="Enter text to test…"
          autoComplete="off"
          maxLength={2000}
          value={message}
          disabled={locked}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button className="btn btn--primary test-llm-send-btn" type="submit" disabled={locked}>
          Test
        </button>
      </form>
    </div>
  );
}
