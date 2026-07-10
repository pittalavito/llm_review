from typing import Literal

from pydantic import BaseModel, Field, field_validator

from models.agent import AgentName, LlmModelName
from domain.graph.config import GraphAgentConfig

AgentRole = Literal["reviewer", "meta_reviewer", "area_chair", "author_agent"]


def _strip_nonempty(value: str, name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{name} must not be empty.")
    return stripped


class TestLlmRequest(BaseModel):
    model: LlmModelName
    temperature: float = Field(default=1, ge=0, le=1)
    message: str = Field(min_length=1, max_length=8_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _strip_nonempty(value, "Message")


class TestAgentRequest(TestLlmRequest):
    name: AgentName


class PreviewPromptRequest(BaseModel):
    name: AgentName
    message: str = Field(min_length=1, max_length=8_000)
    # Optional prompt version label: previews the DB-registered base template.
    prompt_version: str | None = Field(default=None, max_length=50)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _strip_nonempty(value, "Message")


class IndexPaperRequest(BaseModel):
    paper_path: str = Field(min_length=1, max_length=500)
    force_reindex: bool = False

    @field_validator("paper_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _strip_nonempty(value, "Paper path")


class TestAgentWithRetrievalRequest(BaseModel):
    name: AgentName
    model: LlmModelName
    temperature: float = Field(default=1, ge=0, le=1)
    message: str = Field(min_length=1, max_length=8_000)
    paper_path: str = Field(min_length=1, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _strip_nonempty(value, "Message")

    @field_validator("paper_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _strip_nonempty(value, "Paper path")


class PreviewPromptResponse(BaseModel):
    agent: AgentName
    system_prompt: str
    schema_instructions: str
    message_section: str
    full_prompt: str


class PromptVersionCreateRequest(BaseModel):
    agent_role: AgentRole
    version_label: str = Field(min_length=1, max_length=50)
    template: str = Field(min_length=1, max_length=20_000)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("version_label")
    @classmethod
    def validate_label(cls, value: str) -> str:
        return _strip_nonempty(value, "Version label")

    @field_validator("template")
    @classmethod
    def validate_template(cls, value: str) -> str:
        return _strip_nonempty(value, "Template")


class PromptVersionUpdateRequest(BaseModel):
    """Versions are immutable: only metadata can change, never the template."""
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class GraphRunRequest(BaseModel):
    paper_path: str = Field(min_length=1, max_length=500)
    run_description: str = Field(min_length=1, max_length=200)
    force_reindex: bool = False
    graph_config: GraphAgentConfig | None = None

    @field_validator("paper_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _strip_nonempty(value, "Paper path")

    @field_validator("run_description")
    @classmethod
    def validate_run_description(cls, value: str) -> str:
        return _strip_nonempty(value, "Run description")
