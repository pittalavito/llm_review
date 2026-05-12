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
    # Only used when agent_name in {REVIEWER_1, REVIEWER_2, REVIEWER_3}
    reviewer_persona: ReviewerPersona | None = None
    # Only used when agent_name == AREA_CHAIR
    area_chair_style: AreaChairStyle | None = None


class GraphAgentConfig(BaseModel):
    agents: list[AgentLLMConfig]
    max_rounds: int = Field(default=2, ge=1, le=5)

    @staticmethod
    def default_config() -> "GraphAgentConfig":
        _DEFAULT_MODEL = LlmModelName.MOCK
        _DEFAULT_TEMPERATURE = 0.1
        # Each reviewer covers a distinct evaluation angle so the three reviews are complementary.
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
        return GraphAgentConfig(agents=agents, max_rounds=2)
