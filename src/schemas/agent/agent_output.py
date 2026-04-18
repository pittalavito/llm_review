from typing import Any

from pydantic import BaseModel, Field

from schemas.enums import AgentName


class AgentStructuredOutput(BaseModel):
    agent: AgentName
    payload: dict[str, Any] = Field(default_factory=dict)
