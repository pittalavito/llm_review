from pydantic import BaseModel
from models.agent import AgentName


class AgentRun(BaseModel):
    """Complete trace of a single agent invocation."""
    agent: AgentName
    round: int                   # 0-based
    input_message: str
    context_used: str | None     # RAG chunks injected (if any)
    response_payload: dict       # structured response
    prompt_trace: dict | None = None
    runtime_trace: dict | None = None


class RunRecord(BaseModel):
    """Complete record of a single review graph execution."""
    run_id: str                  # e.g. "2026-04-21T14-32-00_paper-name"
    timestamp: str               # ISO 8601
    paper_path: str
    decision: str | None
    total_rounds: int
    reviews: list[str] | None = None
    meta_review: dict | None
    area_chair_response: dict | None = None
    author_response: dict | None
    retrieval_metadata: dict | None
    graph_config: dict
    agent_runs: list[AgentRun]


class RunSummary(BaseModel):
    """Lightweight version of RunRecord for the run history list."""
    run_id: str
    timestamp: str
    paper_path: str
    decision: str | None
    total_rounds: int
