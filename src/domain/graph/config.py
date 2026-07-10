from pydantic import BaseModel, Field

from models.agent import (
    AgentName,
    AreaChairStyle,
    LlmModelName,
    ReviewerFocus,
    ReviewerPersona,
)


class AgentLLMConfig(BaseModel):
    agent_name: AgentName
    model: LlmModelName
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    prompt_version: str = Field(default="v1", min_length=1)
    reviewer_persona: ReviewerPersona | None = None
    area_chair_style: AreaChairStyle | None = None


class GraphAgentConfig(BaseModel):
    agents: list[AgentLLMConfig]
    max_rounds: int = Field(default=2, ge=1, le=5)

    @staticmethod
    def default_config() -> "GraphAgentConfig":
        _DEFAULT_MODEL = LlmModelName.MOCK
        _DEFAULT_TEMPERATURE = 0.4

        agents = [
            AgentLLMConfig(
                agent_name=AgentName.REVIEWER_1,
                model=_DEFAULT_MODEL,
                temperature=_DEFAULT_TEMPERATURE,
                reviewer_persona=ReviewerPersona(focus=ReviewerFocus.SOUNDNESS),
            ),
            AgentLLMConfig(
                agent_name=AgentName.REVIEWER_2,
                model=_DEFAULT_MODEL,
                temperature=_DEFAULT_TEMPERATURE,
                reviewer_persona=ReviewerPersona(focus=ReviewerFocus.EMPIRICAL),
            ),
            AgentLLMConfig(
                agent_name=AgentName.REVIEWER_3,
                model=_DEFAULT_MODEL,
                temperature=_DEFAULT_TEMPERATURE,
                reviewer_persona=ReviewerPersona(focus=ReviewerFocus.NOVELTY),
            ),
        ]
        agents += [
            AgentLLMConfig(agent_name=name, model=_DEFAULT_MODEL, temperature=_DEFAULT_TEMPERATURE)
            for name in (AgentName.META_REVIEWER, AgentName.AUTHOR_AGENT)
        ]
        agents.append(AgentLLMConfig(
            agent_name=AgentName.AREA_CHAIR,
            model=_DEFAULT_MODEL,
            temperature=_DEFAULT_TEMPERATURE,
            area_chair_style=AreaChairStyle.INCLUSIVE,
        ))
        return GraphAgentConfig(agents=agents, max_rounds=1)
