from pydantic import BaseModel
from models.agent import AgentName


class AgentRun(BaseModel):
    """Traccia completa di una singola invocazione agente."""
    agent: AgentName
    round: int                   # 0-based
    input_message: str
    context_used: str | None     # chunk RAG iniettati (se presenti)
    response_payload: dict       # risposta strutturata


class RunRecord(BaseModel):
    """Record completo di un'esecuzione del grafo di review."""
    run_id: str                  # es. "2026-04-21T14-32-00_paper-name"
    timestamp: str               # ISO 8601
    paper_path: str
    decision: str | None
    total_rounds: int
    meta_review: dict | None
    revision_notes: str | None
    retrieval_metadata: dict | None
    graph_config: dict
    agent_runs: list[AgentRun]


class RunSummary(BaseModel):
    """Versione leggera di RunRecord per la lista storico."""
    run_id: str
    timestamp: str
    paper_path: str
    decision: str | None
    total_rounds: int
