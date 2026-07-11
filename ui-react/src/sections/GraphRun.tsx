/**
 * Port of ui/js/sections/graphrun.js — compile config (editable in place)
 * and run the review pipeline. LLM result text renders via JSX (escaped).
 */
import { useEffect, useState, type FormEvent } from 'react';
import {
  compileGraph,
  getGraphConfig,
  listPapers,
  listModels,
  listPromptVersions,
  runGraph,
} from '../api/client';
import type {
  AgentLLMConfig,
  AgentName,
  AreaChairStyle,
  GraphAgentConfig,
  GraphRunResult,
  ReviewerPersona,
} from '../api/types';
import DecisionBadge from '../components/DecisionBadge';
import { errorMessage } from '../lib/format';

const AGENT_LABELS: Record<string, string> = {
  reviewer_1:    '👤 Reviewer 1',
  reviewer_2:    '👤 Reviewer 2',
  reviewer_3:    '👤 Reviewer 3',
  meta_reviewer: '📋 Meta Reviewer',
  area_chair:    '🏛️ Area Chair',
  author_agent:  '✍️  Author Agent',
};
const AGENT_NAMES = Object.keys(AGENT_LABELS) as AgentName[];
const REVIEWER_NAMES: string[] = ['reviewer_1', 'reviewer_2', 'reviewer_3'];

const COMMITMENT_OPTIONS = ['responsible', 'irresponsible'];
const INTENTION_OPTIONS = ['benign', 'malicious'];
const KNOWLEDGE_OPTIONS = ['knowledgeable', 'unknowledgeable'];
const FOCUS_OPTIONS = ['soundness', 'empirical', 'novelty'];
const AC_STYLE_OPTIONS = ['inclusive', 'conformist', 'authoritarian'];

const roleForAgent = (name: string) => (REVIEWER_NAMES.includes(name) ? 'reviewer' : name);

const defaultPersona = (p?: ReviewerPersona | null): ReviewerPersona => ({
  focus: p?.focus ?? 'soundness',
  commitment: p?.commitment ?? 'responsible',
  intention: p?.intention ?? 'benign',
  knowledgeability: p?.knowledgeability ?? 'knowledgeable',
});

function buildDraft(config: GraphAgentConfig | null): GraphAgentConfig {
  return {
    max_rounds: config?.max_rounds ?? 2,
    agents: AGENT_NAMES.map((name) => {
      const existing = config?.agents.find((a) => a.agent_name === name);
      const entry: AgentLLMConfig = {
        agent_name: name,
        model: existing?.model ?? 'mock',
        temperature: existing?.temperature ?? 0.7,
        prompt_version: existing?.prompt_version ?? 'v1',
      };
      if (REVIEWER_NAMES.includes(name)) entry.reviewer_persona = defaultPersona(existing?.reviewer_persona);
      if (name === 'area_chair') entry.area_chair_style = existing?.area_chair_style ?? 'inclusive';
      return entry;
    }),
  };
}

export default function GraphRun() {
  const [config, setConfig] = useState<GraphAgentConfig | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [papers, setPapers] = useState<string[]>([]);
  const [versionsByRole, setVersionsByRole] = useState<Record<string, string[]>>({});
  const [loadError, setLoadError] = useState('');
  const [ready, setReady] = useState(false);

  const [editMode, setEditMode] = useState(false);
  const [draft, setDraft] = useState<GraphAgentConfig>(buildDraft(null));
  const [compiling, setCompiling] = useState(false);
  const [compileStatus, setCompileStatus] = useState('');
  const [compileError, setCompileError] = useState('');

  const [paper, setPaper] = useState('');
  const [runDescription, setRunDescription] = useState('');
  const [forceReindex, setForceReindex] = useState(false);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState('');
  const [result, setResult] = useState<GraphRunResult | null>(null);

  useEffect(() => {
    let alive = true;
    Promise.all([
      listPapers(),
      listModels(),
      getGraphConfig(),
      listPromptVersions().catch(() => []),
    ])
      .then(([paperNames, modelNames, currentConfig, promptVersions]) => {
        if (!alive) return;
        setPapers(paperNames);
        if (paperNames.length) setPaper(paperNames[0]);
        setModels(modelNames);
        setConfig(currentConfig);
        const byRole: Record<string, string[]> = {};
        for (const v of promptVersions) {
          (byRole[v.agent_role] ??= []).push(v.version_label);
        }
        for (const role of Object.keys(byRole)) byRole[role].sort();
        setVersionsByRole(byRole);
        setReady(true);
      })
      .catch((err) => { if (alive) setLoadError(`Errore: ${errorMessage(err)}`); });
    return () => { alive = false; };
  }, []);

  function enterEditMode() {
    setDraft(buildDraft(config));
    setEditMode(true);
    setCompileStatus('');
    setCompileError('');
  }

  async function onCompile() {
    setCompiling(true);
    setCompileError('');
    setCompileStatus('⏳ Compilazione…');
    try {
      await compileGraph(draft);
      setConfig(draft);
      setEditMode(false);
      setCompileStatus('✅ Grafo compilato');
    } catch (err) {
      setCompileStatus('');
      setCompileError(errorMessage(err));
    } finally {
      setCompiling(false);
    }
  }

  async function onRun(e: FormEvent) {
    e.preventDefault();
    const description = runDescription.trim();
    if (!paper) { setRunError('Seleziona un paper.'); return; }
    if (!description) { setRunError('Inserisci una descrizione del run.'); return; }

    setRunError('');
    setRunning(true);
    setResult(null);
    try {
      setResult(await runGraph({
        paper_path: paper,
        run_description: description,
        force_reindex: forceReindex,
      }));
    } catch (err) {
      setRunError(errorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="section">
      <h2 className="section__title">Graph Run</h2>
      <p className="section__desc">Esegui il pipeline di review su un paper.</p>

      <div className="gr-card">
        <div className="gr-card-header-row">
          <div className="gr-card-title">Grafo compilato</div>
          <div className="gr-card-actions">
            <button
              className={`btn ${editMode ? 'btn--secondary' : 'btn--ghost'} btn--sm`}
              disabled={compiling || !ready}
              onClick={editMode ? onCompile : enterEditMode}
            >
              {editMode ? '⚙ Compila' : '⚙ Ricompila'}
            </button>
            {editMode && (
              <button className="btn btn--ghost btn--sm" disabled={compiling}
                      onClick={() => setEditMode(false)}>✕ Annulla</button>
            )}
          </div>
        </div>

        {loadError && <p className="error-msg">{loadError}</p>}
        {!loadError && !ready && <p className="muted">Caricamento…</p>}
        {ready && !editMode && <ConfigReadOnly config={config} />}
        {ready && editMode && (
          <ConfigEditor draft={draft} models={models} versionsByRole={versionsByRole}
                        onChange={setDraft} />
        )}
        {compileError && <div className="error-msg">{compileError}</div>}
        <span className={`gr-status${compileStatus.startsWith('✅') ? ' gr-status--ok' : ''}`}
              style={{ marginTop: 'var(--s-2)', display: 'block' }}>
          {compileStatus}
        </span>
      </div>

      <div className="gr-card">
        <div className="gr-card-title">Esegui review</div>
        <form onSubmit={onRun} noValidate>
          <div className="form-group">
            <label className="form-label">Paper</label>
            <select className="form-select" value={paper} onChange={(e) => setPaper(e.target.value)}>
              {papers.length === 0 && <option value="">Nessun paper disponibile</option>}
              {papers.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="gr-run-description">Descrizione run</label>
            <textarea id="gr-run-description" className="form-textarea" rows={3} maxLength={200}
                      placeholder="Inserisci una breve descrizione del run (max 200 caratteri)..."
                      value={runDescription} onChange={(e) => setRunDescription(e.target.value)} />
          </div>
          <div className="gr-globals">
            <div className="form-group form-group--inline">
              <label className="form-label">Force reindex</label>
              <input type="checkbox" className="form-checkbox" checked={forceReindex}
                     onChange={(e) => setForceReindex(e.target.checked)} />
            </div>
          </div>
          <div className="gr-card-footer">
            <button className="btn btn--primary" type="submit" disabled={running || !config}>
              ▶ Run Review
            </button>
            <span className={`gr-status${!running && config ? ' gr-status--ok' : ''}`}>
              {running ? '⏳ Running…' : config ? 'Pronto' : 'Nessun grafo compilato'}
            </span>
          </div>
          {runError && <div className="error-msg">{runError}</div>}
        </form>
      </div>

      {result && <RunResult result={result} />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Config: read-only
// ---------------------------------------------------------------------------

function ConfigReadOnly({ config }: { config: GraphAgentConfig | null }) {
  if (!config) {
    return (
      <p className="gr-no-config">
        Nessun grafo compilato. Premi <strong>Ricompila</strong> per configurarlo.
      </p>
    );
  }
  return (
    <>
      <p className="gr-config-meta">Max rounds: <strong>{config.max_rounds ?? '?'}</strong></p>
      <table className="gr-config-table">
        <thead>
          <tr><th>Agente</th><th>Modello</th><th>Temp</th><th>Prompt</th><th>Persona / Stile</th></tr>
        </thead>
        <tbody>
          {(config.agents ?? []).map((a) => {
            const p = a.reviewer_persona;
            return (
              <tr key={a.agent_name}>
                <td>{AGENT_LABELS[a.agent_name] ?? a.agent_name}</td>
                <td><code>{a.model}</code></td>
                <td>{a.temperature}</td>
                <td><code>{a.prompt_version ?? 'v1'}</code></td>
                <td>
                  {p && (
                    <small>{p.focus ?? 'soundness'} · {p.commitment} · {p.intention} · {p.knowledgeability}</small>
                  )}
                  {!p && a.area_chair_style && <small>{a.area_chair_style}</small>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}

// ---------------------------------------------------------------------------
// Config: editable
// ---------------------------------------------------------------------------

function ConfigEditor({
  draft, models, versionsByRole, onChange,
}: {
  draft: GraphAgentConfig;
  models: string[];
  versionsByRole: Record<string, string[]>;
  onChange: (next: GraphAgentConfig) => void;
}) {
  const updateAgent = (index: number, patch: Partial<AgentLLMConfig>) => {
    const agents = draft.agents.map((a, i) => (i === index ? { ...a, ...patch } : a));
    onChange({ ...draft, agents });
  };
  const updatePersona = (index: number, patch: Partial<ReviewerPersona>) => {
    const current = draft.agents[index].reviewer_persona ?? defaultPersona();
    updateAgent(index, { reviewer_persona: { ...current, ...patch } });
  };

  const smallSelect = { width: 'auto', fontSize: '0.75rem' } as const;

  return (
    <>
      <div className="gr-globals" style={{ marginBottom: 'var(--s-3)' }}>
        <div className="form-group form-group--inline">
          <label className="form-label">Max rounds</label>
          <input type="number" className="form-input" min={1} max={5} value={draft.max_rounds}
                 onChange={(e) => onChange({ ...draft, max_rounds: Number.parseInt(e.target.value, 10) || 1 })} />
        </div>
      </div>
      <table className="gr-config-table gr-config-table--edit">
        <thead>
          <tr><th>Agente</th><th>Modello</th><th>Temp</th><th>Prompt</th><th>Persona / Stile</th></tr>
        </thead>
        <tbody>
          {draft.agents.map((agent, i) => {
            const role = roleForAgent(agent.agent_name);
            const available = versionsByRole[role] ?? [];
            const pvOptions = available.includes(agent.prompt_version)
              ? available
              : [agent.prompt_version, ...available];
            const persona = agent.reviewer_persona;
            return (
              <tr key={agent.agent_name}>
                <td>{AGENT_LABELS[agent.agent_name]}</td>
                <td>
                  <select className="form-select" value={agent.model}
                          onChange={(e) => updateAgent(i, { model: e.target.value })}>
                    {models.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </td>
                <td>
                  <input type="number" className="form-input" style={{ width: '5rem' }}
                         min={0} max={2} step={0.1} value={agent.temperature}
                         onChange={(e) => updateAgent(i, { temperature: Number.parseFloat(e.target.value) || 0 })} />
                </td>
                <td>
                  <select className="form-select" style={smallSelect} value={agent.prompt_version}
                          onChange={(e) => updateAgent(i, { prompt_version: e.target.value })}>
                    {pvOptions.map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                </td>
                <td>
                  {persona && (
                    <>
                      <select className="form-select" style={smallSelect} value={persona.focus}
                              onChange={(e) => updatePersona(i, { focus: e.target.value as ReviewerPersona['focus'] })}>
                        {FOCUS_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                      </select>
                      <select className="form-select" style={smallSelect} value={persona.commitment}
                              onChange={(e) => updatePersona(i, { commitment: e.target.value as ReviewerPersona['commitment'] })}>
                        {COMMITMENT_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                      </select>
                      <select className="form-select" style={smallSelect} value={persona.intention}
                              onChange={(e) => updatePersona(i, { intention: e.target.value as ReviewerPersona['intention'] })}>
                        {INTENTION_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                      </select>
                      <select className="form-select" style={smallSelect} value={persona.knowledgeability}
                              onChange={(e) => updatePersona(i, { knowledgeability: e.target.value as ReviewerPersona['knowledgeability'] })}>
                        {KNOWLEDGE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                      </select>
                    </>
                  )}
                  {agent.agent_name === 'area_chair' && (
                    <select className="form-select" style={smallSelect} value={agent.area_chair_style ?? 'inclusive'}
                            onChange={(e) => updateAgent(i, { area_chair_style: e.target.value as AreaChairStyle })}>
                      {AC_STYLE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                    </select>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </>
  );
}

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------

interface ParsedReview {
  agent?: string;
  payload?: {
    rating?: number | null;
    confidence?: number | null;
    summary?: string;
    significance_and_novelty?: string;
    reasons_for_acceptance?: string[];
    reasons_for_rejection?: string[];
    suggestions?: string[];
  };
}

function RunResult({ result }: { result: GraphRunResult }) {
  const rounds = result.current_round ?? '?';
  const paperPath = (result.retrieval_metadata as { paper_path?: string } | null)?.paper_path ?? '';
  const meta = (result.meta_review ?? {}) as {
    summary?: string; overall_score?: number; recommendation?: string; key_points?: string[];
  };
  const ac = (result as unknown as { area_chair_response?: Record<string, unknown> }).area_chair_response;
  const author = result.author_response as {
    rebuttal?: string; key_changes?: string[];
    reviewer_rebuttals?: { reviewer_name?: string; response?: string }[];
    revised_sections?: { section_name?: string; content?: string }[];
  } | null;

  const reviews: ParsedReview[] = (result.reviews ?? []).flatMap((raw) => {
    try { return [JSON.parse(raw) as ParsedReview]; } catch { return []; }
  });

  return (
    <div className="gr-card gr-result-card">
      <div className="gr-result-header">
        <div className="gr-result-title">Risultato</div>
        <div className="gr-result-meta">
          <DecisionBadge decision={result.decision} />
          <span className="gr-meta-info">{rounds} round{rounds !== 1 ? 's' : ''} · {paperPath}</span>
        </div>
      </div>
      <div className="gr-result-body">
        {meta.summary && (
          <div className="gr-block">
            <div className="gr-block-title">
              📋 Meta Review {meta.overall_score ? `⭐ ${meta.overall_score}/10` : ''}
            </div>
            {meta.recommendation && (
              <p className="gr-block-text">Raccomandazione: <strong>{meta.recommendation}</strong></p>
            )}
            <p className="gr-block-text">{meta.summary}</p>
            {(meta.key_points ?? []).length > 0 && (
              <ul className="gr-key-points">{meta.key_points!.map((k, i) => <li key={i}>{k}</li>)}</ul>
            )}
          </div>
        )}

        {ac && typeof ac.decision === 'string' && (
          <div className="gr-block gr-block--ac">
            <div className="gr-block-title">
              🏛️ Area Chair Decision &nbsp;<DecisionBadge decision={ac.decision as string} />
            </div>
            {typeof ac.summary === 'string' && ac.summary && <p className="gr-block-text">{ac.summary}</p>}
            {typeof ac.justification === 'string' && ac.justification && (
              <p className="gr-block-text"><em>{ac.justification}</em></p>
            )}
            {ac.confidence != null && <p className="gr-block-text">Confidence: {String(ac.confidence)}/5</p>}
          </div>
        )}

        {author && (
          <div className="gr-block gr-block--notes">
            <div className="gr-block-title">✍️ Author Response</div>
            {author.rebuttal && (
              <p className="gr-block-text"><strong>Rebuttal:</strong> {author.rebuttal}</p>
            )}
            {(author.reviewer_rebuttals ?? []).map((r, i) => (
              <details className="gr-revised-section" key={i}>
                <summary>Risposta a {r.reviewer_name}</summary>
                <p className="gr-block-text">{r.response || ''}</p>
              </details>
            ))}
            {(author.key_changes ?? []).length > 0 && (
              <>
                <p><strong>Key changes:</strong></p>
                <ul>{author.key_changes!.map((c, i) => <li key={i}>{c}</li>)}</ul>
              </>
            )}
            {(author.revised_sections ?? []).map((s, i) => (
              <details className="gr-revised-section" key={i}>
                <summary>[Revised {(s.section_name || '').toUpperCase()}]</summary>
                <p className="gr-block-text">{s.content || ''}</p>
              </details>
            ))}
          </div>
        )}

        {reviews.length > 0 && (
          <div className="gr-block">
            <div className="gr-block-title">Reviews ({result.reviews.length})</div>
            {reviews.map((review, i) => {
              const payload = review.payload ?? {};
              return (
                <details className="gr-review" key={i}>
                  <summary className="gr-review-summary">
                    <span>{AGENT_LABELS[review.agent ?? ''] ?? review.agent ?? `Review ${i + 1}`}</span>
                    {payload.rating != null && <span className="gr-score">{payload.rating}/10</span>}
                    {payload.confidence != null && <span className="gr-conf">conf {payload.confidence}/5</span>}
                  </summary>
                  <div className="gr-review-body">
                    {payload.summary && <p>{payload.summary}</p>}
                    {payload.significance_and_novelty && (
                      <p><strong>Significance &amp; Novelty:</strong> {payload.significance_and_novelty}</p>
                    )}
                    <ReviewList title="Reasons for Acceptance" items={payload.reasons_for_acceptance} />
                    <ReviewList title="Reasons for Rejection" items={payload.reasons_for_rejection} />
                    <ReviewList title="Suggestions" items={payload.suggestions} />
                  </div>
                </details>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function ReviewList({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <>
      <div className="gr-list-title">{title}</div>
      <ul>{items.map((item, i) => <li key={i}>{item}</li>)}</ul>
    </>
  );
}
