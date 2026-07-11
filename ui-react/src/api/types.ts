/**
 * API payload types, hand-derived from the backend Pydantic models
 * (src/models/*.py). Each type notes its source model.
 */

// ---------------------------------------------------------------------------
// Enum-like unions (models/agent.py)
// ---------------------------------------------------------------------------

export type AgentName =
  | 'reviewer_1' | 'reviewer_2' | 'reviewer_3'
  | 'meta_reviewer' | 'area_chair' | 'author_agent';

export type ReviewDecision = 'accept' | 'minor_revision' | 'major_revision' | 'reject';

export type AreaChairStyle = 'authoritarian' | 'conformist' | 'inclusive';

export type AgentRole = 'reviewer' | 'meta_reviewer' | 'area_chair' | 'author_agent';

// models/agent.py :: ReviewerPersona
export interface ReviewerPersona {
  commitment: 'responsible' | 'irresponsible';
  intention: 'benign' | 'malicious';
  knowledgeability: 'knowledgeable' | 'unknowledgeable';
  focus: 'soundness' | 'empirical' | 'novelty';
}

// ---------------------------------------------------------------------------
// Graph configuration (models/graph.py)
// ---------------------------------------------------------------------------

export interface AgentLLMConfig {
  agent_name: AgentName;
  model: string;
  temperature: number;
  prompt_version: string;
  reviewer_persona?: ReviewerPersona | null;
  area_chair_style?: AreaChairStyle | null;
}

export interface GraphAgentConfig {
  agents: AgentLLMConfig[];
  max_rounds: number;
}

// ---------------------------------------------------------------------------
// Run records (models/run_record.py)
// ---------------------------------------------------------------------------

export interface AgentRun {
  agent: AgentName;
  round: number;
  input_message: string;
  context_used: string | null;
  response_payload: Record<string, unknown>;
  prompt_trace?: Record<string, unknown> | null;
  runtime_trace?: Record<string, unknown> | null;
}

export interface RunSummary {
  run_id: string;
  timestamp: string;
  paper_path: string;
  run_description?: string | null;
  decision: string | null;
  total_rounds: number;
}

export interface RunRecord extends RunSummary {
  reviews?: string[] | null; // JSON-encoded ReviewerResponse strings (double-encoded)
  meta_review: Record<string, unknown> | null;
  area_chair_response?: Record<string, unknown> | null;
  author_response: Record<string, unknown> | null;
  retrieval_metadata: Record<string, unknown> | null;
  graph_config: GraphAgentConfig;
  agent_runs: AgentRun[];
}

// ---------------------------------------------------------------------------
// Prompt versions (db/tables.py :: PromptVersionTable, /prompts endpoints)
// ---------------------------------------------------------------------------

export interface PromptVersionMeta {
  id: number;
  agent_role: AgentRole;
  version_label: string;
  template_hash: string;
  description: string | null;
  created_at: string;
  is_active: boolean;
}

export interface PromptVersion extends PromptVersionMeta {
  template: string;
}

// ---------------------------------------------------------------------------
// Agent responses (models/agent.py :: AgentResponse + prompt preview)
// ---------------------------------------------------------------------------

export interface AgentResponsePayload {
  agent: AgentName;
  payload: Record<string, unknown>;
  input_message?: string | null;
  context_used?: string | null;
  prompt_trace?: Record<string, unknown> | null;
  runtime_trace?: Record<string, unknown> | null;
}

export interface PromptPreview {
  system_prompt: string;
  schema_instructions: string;
  message_section: string;
  full_prompt: string;
}

// ---------------------------------------------------------------------------
// Graph run response (controller.py :: run_graph)
// ---------------------------------------------------------------------------

export interface GraphRunResult {
  decision: string | null;
  current_round: number;
  meta_review: Record<string, unknown> | null;
  reviews: string[];
  author_response: Record<string, unknown> | null;
  retrieval_metadata: Record<string, unknown> | null;
}

// ---------------------------------------------------------------------------
// Comparison (models/comparator.py)
// ---------------------------------------------------------------------------

export interface HumanReview {
  note_id: string;
  reviewer_id: string;
  summary: string | null;
  strengths: string | null;
  weaknesses: string | null;
  full_text: string | null;
  rating: number | null;
  rating_label: string | null;
  confidence: number | null;
  confidence_label: string | null;
  questions: string | null;
}

export interface HumanMetaReview {
  note_id: string;
  text: string | null;
  recommendation: string | null;
}

export interface LLMReview {
  agent: string;
  summary: string | null;
  significance_and_novelty: string | null;
  reasons_for_acceptance: string[];
  reasons_for_rejection: string[];
  suggestions: string[];
  rating: number | null;
  confidence: number | null;
}

export interface LLMMetaReview {
  summary: string | null;
  key_points: string[];
  overall_score: number | null;
  recommendation: string | null;
}

export interface LLMAreaChair {
  summary: string | null;
  justification: string | null;
  decision: string | null;
  confidence: number | null;
}

export interface PaperComparisonResult {
  run_id: string;
  run_description: string | null;
  llm_decision: string | null;
  decision_match: boolean;
  human_review_count: number;
  llm_review_count: number;
  llm_reviews: LLMReview[];
  human_meta_review: HumanMetaReview | null;
  llm_meta_review: LLMMetaReview | null;
  llm_area_chair: LLMAreaChair | null;
}

export interface PaperComparison {
  paper_path: string;
  title: string;
  forum_id: string;
  conference: string;
  human_decision: string;
  human_reviews: HumanReview[];
  run_comparisons: PaperComparisonResult[];
}

export interface ComparablePaper {
  paper_path: string;
  title: string;
  conference: string;
}

// ---------------------------------------------------------------------------
// Misc endpoint payloads
// ---------------------------------------------------------------------------

export interface HealthStatus {
  status: string;
  version: string;
}

export interface IndexPaperResult {
  paper_path: string;
  index_status: string;
  chunk_count_total: number;
  chunk_count_retrieved: number;
  top_k: number;
  [key: string]: unknown;
}
