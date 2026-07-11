/** Port of ui/js/sections/testrag.js — paper indexing + agent run with RAG. */
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import {
  ApiError,
  getIndexedPaperDetail,
  indexPaper,
  listAgents,
  listIndexedPapers,
  listModels,
  listPapers,
  testAgentWithRetrieval,
} from '../api/client';
import type { AgentName } from '../api/types';
import ResponseCard, { type ResponseState } from '../components/ResponseCard';
import TemperatureSlider from '../components/TemperatureSlider';
import { formatAgentResponse } from '../lib/agentResponse';
import { errorMessage } from '../lib/format';

const basename = (path: string) => path.split(/[\\/]/).pop() ?? path;

interface IndexResultState {
  title: string;
  body: string;
  isError: boolean;
}

export default function TestRag() {
  // Paper selection & indexing
  const [papers, setPapers] = useState<string[]>([]);
  const [papersError, setPapersError] = useState('');
  const [paper, setPaper] = useState('');
  const [forceReindex, setForceReindex] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState<IndexResultState | null>(null);

  // Indexed list + detail
  const [indexed, setIndexed] = useState<string[]>([]);
  const [indexedState, setIndexedState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [indexedError, setIndexedError] = useState('');
  const [selectedIndexed, setSelectedIndexed] = useState('');
  const [detail, setDetail] = useState<{ title: string; body: string } | null>(null);

  // Run form
  const [agents, setAgents] = useState<string[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [agent, setAgent] = useState('');
  const [model, setModel] = useState('');
  const [selectsFailed, setSelectsFailed] = useState(false);
  const [temperature, setTemperature] = useState(0.7);
  const [topK, setTopK] = useState('');
  const [message, setMessage] = useState('');
  const [running, setRunning] = useState(false);
  const [response, setResponse] = useState<ResponseState | null>(null);

  const loadIndexedPapers = useCallback(async () => {
    setIndexedState('loading');
    setDetail(null);
    setSelectedIndexed('');
    try {
      setIndexed(await listIndexedPapers());
      setIndexedState('ready');
    } catch (err) {
      setIndexedError(errorMessage(err));
      setIndexedState('error');
    }
  }, []);

  useEffect(() => {
    listPapers()
      .then((names) => { setPapers(names); if (names.length) setPaper(names[0]); })
      .catch((err) => setPapersError(errorMessage(err)));

    Promise.all([listAgents(), listModels()])
      .then(([agentNames, modelNames]) => {
        setAgents(agentNames);
        setModels(modelNames);
        setAgent(agentNames.includes('contribution_reviewer' as AgentName)
          ? 'contribution_reviewer' : agentNames[0] ?? '');
        setModel(modelNames.includes('mock') ? 'mock' : modelNames[0] ?? '');
      })
      .catch(() => setSelectsFailed(true));

    loadIndexedPapers();
  }, [loadIndexedPapers]);

  async function onIndex() {
    if (!paper) {
      setIndexResult({ title: 'Validation error', body: 'Select a paper first.', isError: true });
      return;
    }
    setIndexing(true);
    setIndexResult(null);
    try {
      const data = await indexPaper({ paper_path: paper, force_reindex: forceReindex });
      setIndexResult({
        title: `Indexed: ${basename(paper)}`,
        body: JSON.stringify(data, null, 2),
        isError: false,
      });
      loadIndexedPapers();
    } catch (err) {
      setIndexResult({ title: 'Index failed', body: errorMessage(err), isError: true });
    } finally {
      setIndexing(false);
    }
  }

  async function onSelectIndexed(paperPath: string) {
    setSelectedIndexed(paperPath);
    setDetail({ title: basename(paperPath), body: 'Loading…' });
    try {
      const data = await getIndexedPaperDetail(paperPath);
      setDetail({ title: basename(paperPath), body: JSON.stringify(data, null, 2) });
    } catch (err) {
      setDetail({ title: basename(paperPath), body: `Error: ${errorMessage(err)}` });
    }
  }

  async function onRun(e: FormEvent) {
    e.preventDefault();
    const text = message.trim();
    if (!paper) { setResponse({ title: 'Validation error', body: 'Select a paper before running.', isError: true, rawOutput: null }); return; }
    if (!agent || !model) { setResponse({ title: 'Configuration error', body: 'Load agents and models before running.', isError: true, rawOutput: null }); return; }
    if (!text) { setResponse({ title: 'Validation error', body: 'Enter a query message.', isError: true, rawOutput: null }); return; }

    const parsedTopK = topK.trim() ? Number.parseInt(topK.trim(), 10) : undefined;

    setRunning(true);
    setResponse(null);
    try {
      const data = await testAgentWithRetrieval({
        name: agent as AgentName,
        model,
        temperature,
        message: text,
        paper_path: paper,
        ...(parsedTopK != null && Number.isFinite(parsedTopK) ? { top_k: parsedTopK } : {}),
      });
      setResponse({
        title: `Result for ${agent} — ${basename(paper)}`,
        body: formatAgentResponse(data, 'retrieval'),
        isError: false,
        rawOutput: null,
      });
    } catch (err) {
      const raw = err instanceof ApiError ? err.llmRawOutput : null;
      setResponse({ title: 'Agent + RAG run failed', body: errorMessage(err), isError: true, rawOutput: raw });
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="test-rag-section">
      <h2 className="section-title">Test RAG</h2>
      <p className="section-description">
        Index a paper, inspect the index, then run an agent with RAG-augmented context.
      </p>

      <div className="test-rag-grid">
        <div className="card test-rag-card">
          <div className="card__header"><span className="card__title">1) Select &amp; Index Paper</span></div>
          <div className="card__body test-rag-card__body">
            <div className="test-rag-field">
              <label className="test-rag-field__label" htmlFor="rag-paper-select">Paper</label>
              <select className="test-rag-field__control" id="rag-paper-select"
                      value={paper} onChange={(e) => setPaper(e.target.value)}>
                {papersError && <option value="">Error: {papersError}</option>}
                {!papersError && papers.length === 0 && <option value="">No papers found</option>}
                {papers.map((name) => <option key={name} value={name}>{name}</option>)}
              </select>
            </div>

            <label className="test-rag-checkbox">
              <input type="checkbox" checked={forceReindex}
                     onChange={(e) => setForceReindex(e.target.checked)} />
              <span>Force reindex</span>
            </label>

            <div className="test-rag-actions">
              <button className="btn btn--secondary" type="button" disabled={indexing} onClick={onIndex}>
                {indexing ? 'Indexing…' : 'Index Paper'}
              </button>
            </div>

            {indexResult && (
              <div className="card test-rag-result">
                <div className="card__header">
                  <span className={`badge badge--${indexResult.isError ? 'error' : 'success'}`}>
                    {indexResult.isError ? 'Error' : 'OK'}
                  </span>
                  <span className="card__title">{indexResult.title}</span>
                </div>
                <div className="card__body"><pre>{indexResult.body}</pre></div>
              </div>
            )}
          </div>
        </div>

        <div className="card test-rag-card">
          <div className="card__header">
            <span className="card__title">2) Index Status</span>
            <button className="btn btn--secondary btn--sm" type="button" onClick={loadIndexedPapers}>
              Refresh
            </button>
          </div>
          <div className="card__body test-rag-card__body">
            <ul className="test-rag-indexed-list">
              {indexedState === 'loading' && <li className="test-rag-indexed-list__empty">Loading…</li>}
              {indexedState === 'error' && (
                <li className="test-rag-indexed-list__empty test-rag-indexed-list__empty--error">
                  {indexedError}
                </li>
              )}
              {indexedState === 'ready' && indexed.length === 0 && (
                <li className="test-rag-indexed-list__empty">No indexed papers yet.</li>
              )}
              {indexedState === 'ready' && indexed.map((name) => (
                <li key={name} title="Click to see index detail"
                    className={
                      `test-rag-indexed-list__item${name === selectedIndexed ? ' test-rag-indexed-list__item--active' : ''}`
                    }
                    onClick={() => onSelectIndexed(name)}>
                  {name}
                </li>
              ))}
            </ul>

            {detail && (
              <div className="card test-rag-result">
                <div className="card__header">
                  <span className="badge badge--info">Detail</span>
                  <span className="card__title">{detail.title}</span>
                </div>
                <div className="card__body"><pre>{detail.body}</pre></div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card test-rag-card test-rag-run-card">
        <div className="card__header"><span className="card__title">3) Run Agent with Retrieval</span></div>
        <div className="card__body">
          <div className="test-rag-model-bar">
            <div className="test-rag-model-bar__group">
              <label className="test-rag-model-bar__label" htmlFor="rag-agent-select">Agent</label>
              <select className="test-rag-model-bar__select" id="rag-agent-select"
                      value={agent} disabled={running} onChange={(e) => setAgent(e.target.value)}>
                {selectsFailed && <option value="">Unavailable</option>}
                {!selectsFailed && agents.length === 0 && <option value="">Loading…</option>}
                {agents.map((name) => <option key={name} value={name}>{name}</option>)}
              </select>
            </div>
            <div className="test-rag-model-bar__group">
              <label className="test-rag-model-bar__label" htmlFor="rag-model-select">Model</label>
              <select className="test-rag-model-bar__select" id="rag-model-select"
                      value={model} disabled={running} onChange={(e) => setModel(e.target.value)}>
                {selectsFailed && <option value="">Unavailable</option>}
                {!selectsFailed && models.length === 0 && <option value="">Loading…</option>}
                {models.map((name) => <option key={name} value={name}>{name}</option>)}
              </select>
            </div>
            <div className="test-rag-model-bar__group test-rag-model-bar__group--temperature">
              <label className="test-rag-model-bar__label" htmlFor="rag-temperature">Temperature</label>
              <div className="test-rag-model-bar__temperature-wrap">
                <TemperatureSlider
                  id="rag-temperature"
                  min={0} max={1} value={temperature} onChange={setTemperature} disabled={running}
                  inputClassName="test-rag-model-bar__temperature"
                  valueClassName="test-rag-model-bar__temperature-value"
                />
              </div>
            </div>
            <div className="test-rag-model-bar__group">
              <label className="test-rag-model-bar__label" htmlFor="rag-top-k">top_k</label>
              <input className="test-rag-model-bar__select" id="rag-top-k" type="number"
                     min={1} max={20} placeholder="default" style={{ width: 80 }}
                     value={topK} onChange={(e) => setTopK(e.target.value)} />
            </div>
          </div>

          <form className="test-rag-form" noValidate onSubmit={onRun}>
            <div className="test-rag-form__header">
              <label className="test-rag-form__label" htmlFor="rag-message">Query / message</label>
              <span className="test-rag-form__counter">{message.length} / 8000</span>
            </div>
            <textarea className="test-rag-form__textarea" id="rag-message" rows={6} maxLength={8000}
                      placeholder="Enter the query to inject into the agent together with RAG context…"
                      value={message} disabled={running} onChange={(e) => setMessage(e.target.value)} />
            <p className="test-rag-form__hint">
              The selected paper will be indexed (if needed) and the top-k retrieved chunks will be
              prepended to the agent's input message.
            </p>
            <div className="test-rag-form__actions">
              <button className="btn btn--primary" type="submit" disabled={running}>
                {running ? 'Running…' : 'Run Agent + RAG'}
              </button>
            </div>
          </form>

          <ResponseCard state={response} prefix="test-rag" />
        </div>
      </div>
    </section>
  );
}
