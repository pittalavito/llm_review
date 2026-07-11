/** Port of ui/js/sections/testagent.js — single-agent run + prompt preview. */
import { useEffect, useState, type FormEvent } from 'react';
import { listAgents, listModels, previewAgentPrompt, testAgent, ApiError } from '../api/client';
import type { AgentName, PromptPreview } from '../api/types';
import ResponseCard, { type ResponseState } from '../components/ResponseCard';
import TemperatureSlider from '../components/TemperatureSlider';
import { formatAgentResponse } from '../lib/agentResponse';
import { errorMessage } from '../lib/format';

export default function TestAgent() {
  const [agents, setAgents] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [agent, setAgent] = useState('');
  const [model, setModel] = useState('');
  const [loadFailed, setLoadFailed] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<{ agent: string; data: PromptPreview } | null>(null);
  const [response, setResponse] = useState<ResponseState | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([listAgents(), listModels()])
      .then(([agentNames, modelNames]) => {
        if (!alive) return;
        setAgents(agentNames);
        setModels(modelNames);
        setAgent(agentNames.includes('test_tool_agent' as AgentName) ? 'test_tool_agent' : agentNames[0] ?? '');
        setModel(modelNames.includes('mock') ? 'mock' : modelNames[0] ?? '');
      })
      .catch((err) => {
        if (!alive) return;
        setLoadFailed(true);
        showError('Configuration error', errorMessage(err));
      });
    return () => { alive = false; };
  }, []);

  function showError(title: string, body: string, rawOutput: string | null = null) {
    setResponse({ title, body, isError: true, rawOutput });
  }

  async function onPreview() {
    const text = message.trim();
    if (!agent) { showError('Configuration error', 'Select an agent before previewing the prompt.'); return; }
    if (!text) { showError('Validation error', 'Add some text before previewing the prompt.'); return; }

    setLoading(true);
    setPreview(null);
    try {
      const data = await previewAgentPrompt({ name: agent as AgentName, message: text });
      setPreview({ agent, data });
    } catch (err) {
      showError('Prompt preview failed', errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = message.trim();
    if (!agent || !model) { showError('Configuration error', 'Load agents and models before running the test.'); return; }
    if (!text) { showError('Validation error', 'Add some text before running the agent.'); return; }

    setLoading(true);
    setResponse(null);
    try {
      const data = await testAgent({
        name: agent as AgentName, model, temperature, message: text,
      });
      setResponse({
        title: `Result for ${agent} on ${model}`,
        body: formatAgentResponse(data, 'reviewer'),
        isError: false,
        rawOutput: null,
      });
    } catch (err) {
      const raw = err instanceof ApiError ? err.llmRawOutput : null;
      showError('Agent run failed', errorMessage(err), raw);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="test-agent-section">
      <h2 className="section-title">Test Agent</h2>
      <p className="section-description">
        Choose an agent, select a model, and submit text for a guided analysis run.
      </p>

      <div className="card test-agent-intro">
        <div className="card__header"><span className="card__title">How this test works</span></div>
        <div className="card__body test-agent-intro__body">
          <p className="test-agent-intro__text">
            The tool agent can inspect your text, compute basic statistics, and return a concise
            explanation of the result.
          </p>
          <p className="test-agent-intro__text">
            Use the <strong>mock</strong> model for a quick local check, or switch to an Ollama
            model to test the real integration.
          </p>
        </div>
      </div>

      <div className="test-agent-model-bar">
        <div className="test-agent-model-bar__group">
          <label className="test-agent-model-bar__label" htmlFor="test-agent-agent">Agent</label>
          <select className="test-agent-model-bar__select" id="test-agent-agent"
                  value={agent} disabled={loading} onChange={(e) => setAgent(e.target.value)}>
            {loadFailed && <option value="">Unavailable</option>}
            {!loadFailed && agents.length === 0 && <option value="">Loading…</option>}
            {agents.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </div>
        <div className="test-agent-model-bar__group">
          <label className="test-agent-model-bar__label" htmlFor="test-agent-model">Model</label>
          <select className="test-agent-model-bar__select" id="test-agent-model"
                  value={model} disabled={loading} onChange={(e) => setModel(e.target.value)}>
            {loadFailed && <option value="">Unavailable</option>}
            {!loadFailed && models.length === 0 && <option value="">Loading…</option>}
            {models.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </div>
        <div className="test-agent-model-bar__group test-agent-model-bar__group--temperature">
          <label className="test-agent-model-bar__label" htmlFor="test-agent-temperature">Temperature</label>
          <div className="test-agent-model-bar__temperature-wrap">
            <TemperatureSlider
              id="test-agent-temperature"
              min={0} max={1} value={temperature} onChange={setTemperature} disabled={loading}
              inputClassName="test-agent-model-bar__temperature"
              valueClassName="test-agent-model-bar__temperature-value"
            />
          </div>
        </div>
      </div>

      <form className="test-agent-form" noValidate onSubmit={onSubmit}>
        <div className="test-agent-form__header">
          <label className="test-agent-form__label" htmlFor="test-agent-message">Text to analyze</label>
          <span className="test-agent-form__counter">{message.length} / 8000</span>
        </div>
        <textarea
          className="test-agent-form__textarea" id="test-agent-message" rows={8} maxLength={8000}
          placeholder="Paste an abstract, a review comment, or any text you want the agent to inspect..."
          value={message} disabled={loading} onChange={(e) => setMessage(e.target.value)}
        />
        <p className="test-agent-form__hint">
          Tip: longer text works, but keeping the input focused gives clearer tool output.
        </p>
        <div className="test-agent-form__actions">
          <button className="btn btn--secondary" type="button" disabled={loading} onClick={onPreview}>
            Preview Prompt
          </button>
          <button className="btn btn--primary" type="submit" disabled={loading}>
            {loading ? 'Running…' : 'Run Agent'}
          </button>
        </div>
      </form>

      {preview && (
        <div className="card test-agent-prompt-card">
          <div className="card__header">
            <span className="badge badge--info">Prompt Preview</span>
            <span className="card__title">Prompt for {preview.agent}</span>
          </div>
          <div className="card__body test-agent-prompt-card__body">
            <PromptSection title="System Prompt" text={preview.data.system_prompt || '(empty)'} open />
            <PromptSection title="Format Rules & JSON Schema" text={preview.data.schema_instructions || '(none)'} open />
            <PromptSection title="Message Section" text={preview.data.message_section || '(empty)'} open />
            <PromptSection title="Full Prompt (assembled)" text={preview.data.full_prompt || '(empty)'} />
          </div>
        </div>
      )}

      <ResponseCard state={response} prefix="test-agent" />
    </section>
  );
}

function PromptSection({ title, text, open = false }: { title: string; text: string; open?: boolean }) {
  return (
    <div className="test-agent-prompt-section">
      <details open={open}>
        <summary className="test-agent-prompt-section__title">{title}</summary>
        <pre className="test-agent-prompt-section__body">{text}</pre>
      </details>
    </div>
  );
}
