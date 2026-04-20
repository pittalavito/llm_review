from pydantic import BaseModel, Field

from agent.models.enums import AgentName, LlmModelName


class AgentLLMConfig(BaseModel):
    agent_name: AgentName
    model: LlmModelName
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class GraphAgentConfig(BaseModel):
    agents: list[AgentLLMConfig]