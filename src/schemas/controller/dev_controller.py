from typing import Any

from pydantic import BaseModel, Field, field_validator

from schemas.agent.agent_output import AgentStructuredOutput
from schemas.enums import AgentName, LlmModelName


class HealthResponse(BaseModel):
    status: str
    version: str


class TestModelRequest(BaseModel):
    model: LlmModelName
    temperature: float = Field(default=1, ge=0, le=1)
    message: str = Field(min_length=1, max_length=8_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        return stripped


class TestModelResponse(BaseModel):
    response: str


class TestAgentRequest(BaseModel):
    name: AgentName
    model: LlmModelName
    temperature: float = Field(default=1, ge=0, le=1)
    message: str = Field(min_length=1, max_length=8_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        return stripped


class GraphCompileRequest(BaseModel):
    methodology_reviewer_agent: AgentName
    methodology_reviewer_model: LlmModelName
    methodology_reviewer_temperature: float = Field(default=0.7, ge=0, le=1)
    max_iterations: int = Field(default=3, ge=1, le=20)
    max_tokens: int | None = Field(default=None, ge=1)


class GraphRunRequest(BaseModel):
    paper: str = Field(min_length=1, max_length=20_000)

    @field_validator("paper")
    @classmethod
    def validate_paper(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Paper must not be empty.")
        return stripped


class GraphRunFileRequest(BaseModel):
    paper_path: str = Field(min_length=1, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)
    force_reindex: bool = False

    @field_validator("paper_path")
    @classmethod
    def validate_paper_path(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Paper path must not be empty.")
        return stripped


class RetrievalMetadata(BaseModel):
    paper_path: str
    index_status: str
    chunk_count_total: int
    chunk_count_retrieved: int
    top_k: int


class GraphRunResponse(BaseModel):
    reviews: list[AgentStructuredOutput]
    raw_result: dict[str, Any]
    retrieval: RetrievalMetadata | None = None


class OpenReviewSearchRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=200)
    venue_id: str = Field(min_length=1, max_length=300)
    limit: int = Field(default=10, ge=1, le=100)

    @field_validator("keyword", "venue_id")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Value must not be empty.")
        return stripped
