/**
 * Port of ui/js/sections/storico.js — run history with per-agent traces.
 * All LLM/server text renders through JSX interpolation (auto-escaped):
 * this port closes the stored-XSS surface of the vanilla version.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { getRun, getRunAgentRuns, listRuns } from '../api/client';
import type { AgentRun, GraphAgentConfig, RunRecord, RunSummary } from '../api/types';
import DecisionBadge, { decisionInfo } from '../components/DecisionBadge';
import { errorMessage, formatTimestamp } from '../lib/format';

const AGENT_LABELS: Record<string, string> = {
  reviewer_1:    '🔬 Reviewer 1',
  reviewer_2:    '🔬 Reviewer 2',
  reviewer_3:    '🔬 Reviewer 3',
  meta_reviewer: '📋 Meta Reviewer',
  area_chair:    '🪑 Area Chair',
  author_agent:  '✍️  Author Agent',
};

/** Loose view over response_payload — every field optional (models/agent.py). */
interface ReviewPayload {
  summary?: string;
  rebuttal?: string;
  significance_and_novelty?: string;
  rating?: number | null;
  confidence?: number | null;
  recommendation?: string | null;
  decision?: string | null;
  justification?: string;
  reasons_for_acceptance?: string[];
  reasons_for_rejection?: string[];
  suggestions?: string[];
  key_changes?: string[];
  reviewer_rebuttals?: { reviewer_name?: string; response?: string }[];
  revised_sections?: { section_name?: string; content?: string }[];
}

function sortedUnique<T>(values: T[]): T[] {
  return [...new Set(values)].sort((a, b) => (a > b ? 1 : -1));
}

export default function Storico() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [error, setError] = useState('');
  const [loadingList, setLoadingList] = useState(true);
  const [detail, setDetail] = useState<RunRecord | null>(null);
  const [detailState, setDetailState] = useState<'hidden' | 'loading' | 'ready' | 'error'>('hidden');
  const [detailError, setDetailError] = useState('');
  const detailRef = useRef<HTMLDivElement>(null);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    setDetailState('hidden');
    setError('');
    try {
      setRuns(await listRuns());
    } catch (err) {
      setRuns([]);
      setError(`Errore: ${errorMessage(err)}`);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => { loadList(); }, [loadList]);

  async function onRunClick(runId: string) {
    setDetailState('loading');
    detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    try {
      const [record, agentRuns] = await Promise.all([getRun(runId), getRunAgentRuns(runId)]);
      setDetail({ ...record, agent_runs: agentRuns });
      setDetailState('ready');
    } catch (err) {
      setDetailError(errorMessage(err));
      setDetailState('error');
    }
  }

  return (
    <div className="section storico">
      <div className="storico-header">
        <h2 className="section__title">Storico Review</h2>
        <button className="btn btn--ghost" onClick={loadList}>🔄 Aggiorna</button>
      </div>
      <p className="section__desc">
        Esplora i run passati — espandi ogni agente per vedere input, contesto RAG e risposta.
      </p>
      {error && <div className="error-msg">{error}</div>}

      <div className="sto-list">
        {loadingList && <p className="muted">Caricamento…</p>}
        {!loadingList && runs.length === 0 && !error && (
          <p className="muted">Nessun run trovato. Esegui il pipeline dalla sezione Graph Run.</p>
        )}
        {runs.map((run) => (
          <div className="sto-row" key={run.run_id}>
            <span className="sto-ts">{formatTimestamp(run.timestamp)}</span>
            <div className="sto-main">
              <span className="sto-paper">{run.paper_path}</span>
              <span className="sto-description">
                {run.run_description || <span className="muted">Descrizione non disponibile</span>}
              </span>
            </div>
            <DecisionBadge decision={run.decision} />
            <span className="sto-rounds">
              {run.total_rounds} round{run.total_rounds !== 1 ? 's' : ''}
            </span>
            <button className="btn btn--ghost btn--sm sto-open-btn" onClick={() => onRunClick(run.run_id)}>
              Esplora →
            </button>
          </div>
        ))}
      </div>

      <div className="sto-detail" ref={detailRef} hidden={detailState === 'hidden'}>
        {detailState === 'loading' && <p className="muted">Caricamento dettaglio…</p>}
        {detailState === 'error' && <p className="error-msg">{detailError}</p>}
        {detailState === 'ready' && detail && (
          <RunDetail record={detail} onBack={() => setDetailState('hidden')} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Detail
// ---------------------------------------------------------------------------

function RunDetail({ record, onBack }: { record: RunRecord; onBack: () => void }) {
  const agentRuns = record.agent_runs ?? [];
  const rounds = sortedUnique(agentRuns.map((ar) => Number(ar.round ?? 0)));
  const defaultRound = rounds.length ? rounds[0] : null;

  // Draft filters (applied only on "Applica filtri", vanilla behavior).
  const [draftAgent, setDraftAgent] = useState('');
  const [draftRound, setDraftRound] = useState(defaultRound === null ? '' : String(defaultRound));
  const [applied, setApplied] = useState<{ agent: string | null; round: number | null }>({
    agent: null,
    round: defaultRound,
  });

  const agents = sortedUnique(agentRuns.map((ar) => ar.agent as string));

  function applyFilters() {
    setApplied({
      agent: draftAgent || null,
      round: draftRound === '' ? null : Number(draftRound),
    });
  }

  function resetFilters() {
    setDraftAgent('');
    const roundValue = defaultRound === null ? '' : String(defaultRound);
    setDraftRound(roundValue);
    setApplied({ agent: null, round: defaultRound });
  }

  let filtered = [...agentRuns];
  if (applied.agent) filtered = filtered.filter((ar) => ar.agent === applied.agent);
  if (applied.round !== null) {
    filtered = filtered.filter((ar) => Number(ar.round ?? 0) === applied.round);
  }
  const byRound = new Map<number, AgentRun[]>();
  for (const ar of filtered) {
    const r = Number(ar.round ?? 0);
    if (!byRound.has(r)) byRound.set(r, []);
    byRound.get(r)!.push(ar);
  }
  const groupedRounds = [...byRound.entries()].sort(([a], [b]) => a - b);

  const authorResponse = record.author_response as ReviewPayload | null;

  return (
    <>
      <div className="sto-detail-header">
        <button className="btn btn--ghost btn--sm" onClick={onBack}>← Storico</button>
        <DecisionBadge decision={record.decision} />
        <span className="sto-detail-meta">
          {formatTimestamp(record.timestamp)} · {record.paper_path} · {record.total_rounds} round
          {record.total_rounds !== 1 ? 's' : ''}
        </span>
      </div>
      <p className="sto-detail-description">
        <strong>Descrizione run:</strong>{' '}
        {record.run_description || <span className="muted">Descrizione non disponibile</span>}
      </p>

      <GraphConfigBlock config={record.graph_config} />

      <div className="sto-filters">
        <div className="form-group">
          <label className="form-label" htmlFor="sto-filter-agent">Agente</label>
          <select id="sto-filter-agent" className="form-select" value={draftAgent}
                  onChange={(e) => setDraftAgent(e.target.value)}>
            <option value="">Tutti</option>
            {agents.map((a) => <option key={a} value={a}>{AGENT_LABELS[a] ?? a}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label" htmlFor="sto-filter-round">Round</label>
          <select id="sto-filter-round" className="form-select" value={draftRound}
                  onChange={(e) => setDraftRound(e.target.value)}>
            <option value="">Tutti</option>
            {rounds.map((r) => <option key={r} value={String(r)}>Round {r + 1}</option>)}
          </select>
        </div>
        <div className="sto-filters-actions">
          <button className="btn btn--secondary btn--sm" onClick={applyFilters}>Applica filtri</button>
          <button className="btn btn--ghost btn--sm" onClick={resetFilters}>Reset</button>
        </div>
      </div>

      <div>
        {groupedRounds.length === 0 && (
          <p className="muted">Nessun agent run trovato con i filtri selezionati.</p>
        )}
        {groupedRounds.map(([round, runs]) => (
          <div className="sto-round" key={round}>
            <div className="sto-round-title">Round {round + 1}</div>
            {runs.map((ar, i) => <AgentTrace key={`${ar.agent}-${i}`} run={ar} />)}
          </div>
        ))}
      </div>

      {authorResponse && <AuthorResponseBlock payload={authorResponse} />}
    </>
  );
}

function GraphConfigBlock({ config }: { config: GraphAgentConfig | null }) {
  if (!config) return null;
  return (
    <details className="sto-config-block">
      <summary className="sto-config-summary">
        ⚙️ Configurazione agenti · max rounds: {config.max_rounds ?? '?'}
      </summary>
      <table className="sto-config-table">
        <thead>
          <tr><th>Agente</th><th>Modello</th><th>Temp</th><th>Persona / Style</th></tr>
        </thead>
        <tbody>
          {(config.agents ?? []).map((a) => {
            const p = a.reviewer_persona;
            const persona = p
              ? `${p.focus}, ${p.commitment}, ${p.intention}, ${p.knowledgeability}`
              : a.area_chair_style ?? '';
            return (
              <tr key={a.agent_name}>
                <td>{AGENT_LABELS[a.agent_name] ?? a.agent_name}</td>
                <td><code>{a.model}</code></td>
                <td>{a.temperature}</td>
                <td className="muted">{persona}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Agent trace
// ---------------------------------------------------------------------------

function AgentTrace({ run }: { run: AgentRun }) {
  const payload = (run.response_payload ?? {}) as ReviewPayload;
  const summary = payload.summary || payload.rebuttal || '';
  const rating = payload.rating ?? null;
  const displayDecision = payload.recommendation || payload.decision || null;
  const acceptance = payload.reasons_for_acceptance ?? [];
  const rejection = payload.reasons_for_rejection ?? [];
  const suggestions = payload.suggestions ?? [];
  const changes = payload.key_changes ?? [];
  const isUnstructured = !summary && rating === null && !displayDecision && acceptance.length === 0;

  return (
    <details className="sto-agent-trace">
      <summary className="sto-agent-summary">
        <span>{AGENT_LABELS[run.agent] ?? run.agent}</span>
        {rating !== null && <span className="gr-score">{rating}/10</span>}
        {displayDecision && (
          <span className={`badge badge--sm ${decisionInfo(displayDecision).cls}`}>
            {displayDecision}
          </span>
        )}
      </summary>
      <div className="sto-agent-body">
        <details className="trace-section">
          <summary>💬 Input inviato</summary>
          <pre className="trace-pre">{run.input_message || ''}</pre>
        </details>

        {run.context_used ? (
          <details className="trace-section">
            <summary>📄 Context RAG</summary>
            <pre className="trace-pre">{run.context_used}</pre>
          </details>
        ) : (
          <div className="trace-section trace-section--empty">Nessun contesto RAG.</div>
        )}

        <details className="trace-section" open>
          <summary>✅ Risposta</summary>
          <div className="trace-response">
            {summary && <p><strong>Summary:</strong> {summary}</p>}
            {payload.significance_and_novelty && (
              <p><strong>Significance &amp; Novelty:</strong> {payload.significance_and_novelty}</p>
            )}
            {rating !== null && <p><strong>Rating:</strong> {rating}/10</p>}
            {payload.confidence != null && <p><strong>Confidence:</strong> {payload.confidence}/5</p>}
            {displayDecision && <p><strong>Decision/Recommendation:</strong> {displayDecision}</p>}
            {payload.justification && <p><strong>Justification:</strong> {payload.justification}</p>}
            <TitledList title="Reasons for acceptance" items={acceptance} />
            <TitledList title="Reasons for rejection" items={rejection} />
            <TitledList title="Suggestions" items={suggestions} />
            <TitledList title="Key changes" items={changes} />
            {isUnstructured && (
              <pre className="trace-pre">{JSON.stringify(payload, null, 2)}</pre>
            )}
          </div>
        </details>

        <PromptTraceBlock trace={run.prompt_trace} />
        <RuntimeTraceBlock trace={run.runtime_trace} />
      </div>
    </details>
  );
}

function TitledList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <>
      <p><strong>{title}:</strong></p>
      <ul>{items.map((item, i) => <li key={i}>{item}</li>)}</ul>
    </>
  );
}

function PromptTraceBlock({ trace }: { trace: Record<string, unknown> | null | undefined }) {
  if (!trace) return null;
  const template = (trace.template ?? {}) as { system?: string; variables?: unknown };
  const rendered = (trace.rendered ?? {}) as { full_prompt?: string };
  return (
    <details className="trace-section">
      <summary>🧩 Prompt Trace</summary>
      <div className="trace-response">
        <p><strong>Template system:</strong></p>
        <pre className="trace-pre">{template.system || ''}</pre>
        <p><strong>Template variables:</strong></p>
        <pre className="trace-pre">{JSON.stringify(template.variables ?? {}, null, 2)}</pre>
        <p><strong>Rendered full prompt:</strong></p>
        <pre className="trace-pre">{rendered.full_prompt || ''}</pre>
      </div>
    </details>
  );
}

function RuntimeTraceBlock({ trace }: { trace: Record<string, unknown> | null | undefined }) {
  if (!trace) return null;
  const llm = (trace.llm ?? {}) as { model?: string; class?: string; temperature?: number };
  const metrics = (trace.metrics ?? {}) as {
    latency_ms?: number; started_at?: string; ended_at?: string;
  };
  const usage = trace.provider_usage ?? {};
  const retrieval = trace.retrieval ?? null;
  return (
    <details className="trace-section">
      <summary>📊 Runtime &amp; Tokens</summary>
      <div className="trace-response">
        <p><strong>Model:</strong> {llm.model || llm.class || 'unknown'}</p>
        <p><strong>Temperature:</strong> {llm.temperature ?? 'n/a'}</p>
        <p><strong>Latency:</strong> {metrics.latency_ms ?? 'n/a'} ms</p>
        <p><strong>Started:</strong> {metrics.started_at || ''}</p>
        <p><strong>Ended:</strong> {metrics.ended_at || ''}</p>
        <p><strong>Token usage:</strong></p>
        <pre className="trace-pre">{JSON.stringify(usage, null, 2)}</pre>
        {retrieval != null && (
          <>
            <p><strong>Retrieval trace:</strong></p>
            <pre className="trace-pre">{JSON.stringify(retrieval, null, 2)}</pre>
          </>
        )}
      </div>
    </details>
  );
}

function AuthorResponseBlock({ payload }: { payload: ReviewPayload }) {
  const rebuttals = payload.reviewer_rebuttals ?? [];
  const sections = payload.revised_sections ?? [];
  const keyChanges = payload.key_changes ?? [];
  return (
    <div className="sto-round">
      <div className="sto-round-title">✍️ Author Response</div>
      {payload.rebuttal && (
        <p className="sto-revision-notes"><strong>General Rebuttal:</strong> {payload.rebuttal}</p>
      )}
      {rebuttals.length > 0 && (
        <>
          <p><strong>Per-Reviewer Rebuttals:</strong></p>
          {rebuttals.map((r, i) => (
            <details className="trace-section" key={i}>
              <summary>{r.reviewer_name}</summary>
              <p>{r.response || ''}</p>
            </details>
          ))}
        </>
      )}
      {keyChanges.length > 0 && (
        <>
          <p><strong>Key Changes:</strong></p>
          <ul>{keyChanges.map((c, i) => <li key={i}>{c}</li>)}</ul>
        </>
      )}
      {sections.map((s, i) => (
        <details className="trace-section" key={i}>
          <summary>[Revised {(s.section_name || '').toUpperCase()}]</summary>
          <pre className="trace-pre">{s.content || ''}</pre>
        </details>
      ))}
    </div>
  );
}
