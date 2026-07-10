"""SQLModel table definitions.

Design principle: analytical facts live in typed, constrained, indexed
columns (queryable via SQL); full payloads are preserved verbatim in JSON
columns (audit and byte-level API fidelity). Enum-like columns are plain
strings guarded by SQL CHECK constraints — the project StrEnums come from
pypdf.constants and do not map safely onto SQLAlchemy Enum types.

These classes are deliberately separate from the Pydantic domain models in
models/run_record.py: RunRecord/AgentRun stay API-frozen, mapping happens
explicitly in db/mappers.py.
"""

from sqlalchemy import JSON, CheckConstraint, Column, ForeignKey, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

_AGENT_NAMES_SQL = ("('reviewer_1','reviewer_2','reviewer_3','meta_reviewer','area_chair','author_agent')")
_AGENT_ROLES_SQL = "('reviewer','meta_reviewer','area_chair','author_agent')"


class RunTable(SQLModel, table=True):
    """One row per review-graph execution."""

    __tablename__ = "run"
    __table_args__ = (
        CheckConstraint("total_rounds >= 0", name="ck_run_total_rounds"),
        CheckConstraint("max_rounds IS NULL OR max_rounds >= 1", name="ck_run_max_rounds"),
        CheckConstraint("meta_overall_score IS NULL OR meta_overall_score BETWEEN 1 AND 10", name="ck_run_meta_overall_score"),
    )

    run_id: str = Field(primary_key=True) 
    timestamp: str = Field(index=True)    
    paper_path: str = Field(index=True)
    run_description: str | None = None
    decision: str | None = Field(default=None, index=True)
    total_rounds: int
    max_rounds: int | None = None          
    meta_overall_score: int | None = None
    reviews: list | None = Field(default=None, sa_column=Column(JSON))
    meta_review: dict | None = Field(default=None, sa_column=Column(JSON))
    area_chair_response: dict | None = Field(default=None, sa_column=Column(JSON))
    author_response: dict | None = Field(default=None, sa_column=Column(JSON))
    retrieval_metadata: dict | None = Field(default=None, sa_column=Column(JSON))
    graph_config: dict = Field(sa_column=Column(JSON, nullable=False))


class AgentRunTable(SQLModel, table=True):
    """One row per agent invocation (N per run). `id` preserves the original
    list order so the API can reconstruct agent_runs byte-identically."""

    __tablename__ = "agent_run"
    __table_args__ = (
        CheckConstraint(f"agent IN {_AGENT_NAMES_SQL}", name="ck_agent_run_agent"),
        CheckConstraint('"round" >= 0', name="ck_agent_run_round"),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 10", name="ck_agent_run_rating"),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 1 AND 5", name="ck_agent_run_confidence"),
        CheckConstraint("overall_score IS NULL OR overall_score BETWEEN 1 AND 10", name="ck_agent_run_overall_score"),
        Index("ix_agent_run_run_agent_round", "run_id", "agent", "round"),
    )

    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(sa_column=Column(ForeignKey("run.run_id", ondelete="CASCADE"), nullable=False))
    agent: str
    round: int
    input_message: str
    context_used: str | None = None
    response_payload: dict = Field(sa_column=Column(JSON, nullable=False))
    prompt_trace: dict | None = Field(default=None, sa_column=Column(JSON))
    runtime_trace: dict | None = Field(default=None, sa_column=Column(JSON))
    rating: int | None = None       
    confidence: int | None = None     
    overall_score: int | None = None 
    decision: str | None = None   
    latency_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class PromptVersionTable(SQLModel, table=True):
    """Registry of base system-prompt templates. Versions are immutable:
    a new text means a new row (new version_label); only description and
    is_active may change afterwards — the run -> version audit trail relies
    on it. Persona/style modifiers are code-side composition, not versions."""

    __tablename__ = "prompt_version"
    __table_args__ = (
        CheckConstraint(f"agent_role IN {_AGENT_ROLES_SQL}", name="ck_prompt_version_role"),
        UniqueConstraint("agent_role", "version_label", name="uq_prompt_role_label"),
    )

    id: int | None = Field(default=None, primary_key=True)
    agent_role: str
    version_label: str          
    template: str               
    template_hash: str       
    description: str | None = None
    created_at: str         
    is_active: bool = True


class RunAgentConfigTable(SQLModel, table=True):
    """Per-agent LLM configuration for a run, normalized from
    graph_config.agents (the verbatim copy stays in run.graph_config)."""

    __tablename__ = "run_agent_config"
    __table_args__ = (
        CheckConstraint(f"agent_name IN {_AGENT_NAMES_SQL}", name="ck_rac_agent_name"),
        CheckConstraint("temperature BETWEEN 0 AND 2", name="ck_rac_temperature"),
        UniqueConstraint("run_id", "agent_name", name="uq_rac_run_agent"),
    )
    
    model_config = {"protected_namespaces": ()}
    id: int | None = Field(default=None, primary_key=True)
    run_id: str = Field(sa_column=Column(ForeignKey("run.run_id", ondelete="CASCADE"), nullable=False))
    agent_name: str
    model: str = Field(index=True)
    temperature: float
    prompt_version: str | None = None
    prompt_version_id: int | None = Field(default=None, sa_column=Column(ForeignKey("prompt_version.id"), nullable=True))
    persona_commitment: str | None = None
    persona_intention: str | None = None
    persona_knowledgeability: str | None = None
    persona_focus: str | None = None
    area_chair_style: str | None = None
