/**
 * Typed HTTP client — 1:1 port of ui/js/api.js.
 * Every function targets the same /llm-review endpoint with the same payload.
 */
import type {
  AgentLLMConfig,
  AgentName,
  AgentResponsePayload,
  ComparablePaper,
  GraphAgentConfig,
  GraphRunResult,
  HealthStatus,
  IndexPaperResult,
  PaperComparison,
  PromptPreview,
  PromptVersion,
  PromptVersionMeta,
  RunRecord,
  RunSummary,
  AgentRun,
} from './types';

const BASE_URL = '/llm-review';

export class ApiError extends Error {
  llmRawOutput: string | null;

  constructor(message: string, llmRawOutput: string | null = null) {
    super(message);
    this.llmRawOutput = llmRawOutput;
  }
}

async function readJsonOrText(response: Response): Promise<unknown> {
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('application/json') ? response.json() : response.text();
}

async function throwForResponse(response: Response): Promise<void> {
  if (response.ok) return;
  const payload = await readJsonOrText(response);
  const detail =
    typeof payload === 'string'
      ? payload
      : (payload as { detail?: unknown })?.detail;
  if (typeof detail === 'string') throw new ApiError(detail);
  if (detail && typeof detail === 'object') {
    const d = detail as { error?: string; llm_raw_output?: string };
    throw new ApiError(d.error ?? JSON.stringify(detail), d.llm_raw_output ?? null);
  }
  throw new ApiError(`HTTP ${response.status} ${response.statusText}`);
}

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const qs = params ? `?${new URLSearchParams(params)}` : '';
  const res = await fetch(`${BASE_URL}${path}${qs}`);
  await throwForResponse(res);
  return res.json() as Promise<T>;
}

async function send<T>(method: 'POST' | 'PATCH', path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  await throwForResponse(res);
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health / catalogs
// ---------------------------------------------------------------------------

export const checkHealth = () => get<HealthStatus>('/health');
export const listModels = () => get<string[]>('/models');
export const listAgents = () => get<AgentName[]>('/agents');
export const listPapers = () => get<string[]>('/papers');

// ---------------------------------------------------------------------------
// LLM / agent testing
// ---------------------------------------------------------------------------

export const testLlm = (message: string, model: string, temperature = 1) =>
  send<string>('POST', '/test-llm', { message, model, temperature });

export interface TestAgentPayload {
  name: AgentName;
  model: string;
  temperature: number;
  message: string;
}

export const testAgent = (payload: TestAgentPayload) =>
  send<AgentResponsePayload>('POST', '/agents', payload);

export const previewAgentPrompt = (payload: {
  name: AgentName;
  message: string;
  prompt_version?: string;
}) => send<PromptPreview>('POST', '/agents/prompt-preview', payload);

export const testAgentWithRetrieval = (
  payload: TestAgentPayload & { paper_path: string; top_k?: number },
) => send<AgentResponsePayload>('POST', '/agents/retrieval', payload);

// ---------------------------------------------------------------------------
// Papers / RAG index
// ---------------------------------------------------------------------------

export const indexPaper = (payload: { paper_path: string; force_reindex?: boolean }) =>
  send<IndexPaperResult>('POST', '/papers/index', payload);

export const listIndexedPapers = () => get<string[]>('/papers/indexed');

export const getIndexedPaperDetail = (paperPath: string) =>
  get<Record<string, unknown>>('/papers/indexed/detail', { paper_path: paperPath });

// ---------------------------------------------------------------------------
// Graph
// ---------------------------------------------------------------------------

export const getGraphConfig = () => get<GraphAgentConfig | null>('/graph/config');

export const compileGraph = (graphConfig: GraphAgentConfig | null = null) =>
  send<{ status: string }>('POST', '/graph/compile', graphConfig);

export const runGraph = (payload: {
  paper_path: string;
  run_description: string;
  force_reindex?: boolean;
  graph_config?: GraphAgentConfig;
}) => send<GraphRunResult>('POST', '/graph/run', payload);

// ---------------------------------------------------------------------------
// Run history
// ---------------------------------------------------------------------------

export const listRuns = () => get<RunSummary[]>('/runs');

export const getRun = (runId: string) =>
  get<RunRecord>(`/runs/${encodeURIComponent(runId)}`);

export const getRunAgentRuns = (
  runId: string,
  filters: { agent_name?: string; round_index?: number } = {},
) => {
  const params: Record<string, string> = {};
  if (filters.agent_name) params.agent_name = filters.agent_name;
  if (Number.isInteger(filters.round_index)) params.round_index = String(filters.round_index);
  return get<AgentRun[]>(`/runs/${encodeURIComponent(runId)}/agent-runs`, params);
};

// ---------------------------------------------------------------------------
// Prompt versions
// ---------------------------------------------------------------------------

export const listPromptVersions = (
  filters: { agent_role?: string; include_inactive?: boolean } = {},
) => {
  const params: Record<string, string> = {};
  if (filters.agent_role) params.agent_role = filters.agent_role;
  if (filters.include_inactive) params.include_inactive = 'true';
  return get<PromptVersionMeta[]>('/prompts', params);
};

export const getPromptVersion = (versionId: number) =>
  get<PromptVersion>(`/prompts/${versionId}`);

export const createPromptVersion = (payload: {
  agent_role: string;
  version_label: string;
  template: string;
  description?: string;
}) => send<PromptVersion>('POST', '/prompts', payload);

export const updatePromptVersion = (
  versionId: number,
  payload: { description?: string; is_active?: boolean },
) => send<PromptVersion>('PATCH', `/prompts/${versionId}`, payload);

// ---------------------------------------------------------------------------
// Comparison
// ---------------------------------------------------------------------------

export const listComparablePapers = () => get<ComparablePaper[]>('/compare/papers');

export const comparePaper = (paperPath: string) =>
  get<PaperComparison>('/compare', { paper_path: paperPath });

export type { AgentLLMConfig };
