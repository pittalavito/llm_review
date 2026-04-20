import json
from typing import Any

from pydantic import BaseModel, Field

from agent.models.enums import AgentName


class AgentStructuredOutput(BaseModel):
    agent: AgentName
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: str) -> "AgentStructuredOutput":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Agent returned invalid JSON: {exc}") from exc
        try:
            return cls.model_validate(data)
        except Exception as exc:
            raise ValueError(f"Agent output does not match schema: {exc}") from exc
