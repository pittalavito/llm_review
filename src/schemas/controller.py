from typing import Any

from pydantic import BaseModel, Field, field_validator

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


class GraphRunResponse(BaseModel):
    reviews: list[str]
    raw_result: dict[str, Any]