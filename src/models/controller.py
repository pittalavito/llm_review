from pydantic import BaseModel, Field, field_validator

from models.agent import AgentName, LlmModelName
from graph.config import GraphAgentConfig


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


class GraphRunRequest(BaseModel):
    paper_path: str = Field(min_length=1, max_length=500)
    force_reindex: bool = False
    graph_config: GraphAgentConfig | None = None

    @field_validator("paper_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _strip_nonempty(value, "Paper path")
