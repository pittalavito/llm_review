from domain.agent.base import BaseAgent
from domain.agent.prompting.reviewer import build_system_prompt, get_rag_focus
from models.agent import (
    AgentName,
    ReviewerPersona,
    ReviewerResponse,
)

_DEFAULT_PERSONA = ReviewerPersona()


class ReviewerAgent(BaseAgent[ReviewerResponse]):
    RESPONSE_SCHEMA = ReviewerResponse
    RAG_SECTIONS = []
    RAG_QUERY = None

    rag_focus_terms: str = ""
    rag_focus_sections: list[str] = []

    def __init__(
        self,
        client,
        context_provider=None,
        persona: ReviewerPersona | None = None,
        agent_name: AgentName = AgentName.REVIEWER_1,
        base_template: str | None = None,
    ):
        self.AGENT_NAME = agent_name
        p = persona or _DEFAULT_PERSONA
        self.SYSTEM_PROMPT = build_system_prompt(p, base_template)
        self.rag_focus_terms, self.rag_focus_sections = get_rag_focus(p)
        super().__init__(client, context_provider)
