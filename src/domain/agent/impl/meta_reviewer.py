from domain.agent.base import BaseAgent
from domain.agent.prompting.meta_reviewer import build_system_prompt
from models.agent import AgentName, MetaReviewResponse

class MetaReviewerAgent(BaseAgent[MetaReviewResponse]):
    AGENT_NAME = AgentName.META_REVIEWER
    SYSTEM_PROMPT = build_system_prompt()
    RESPONSE_SCHEMA = MetaReviewResponse

    def __init__(
        self, 
        client, 
        context_provider=None, 
        base_template: str | None = None
    ):
        if base_template:
            self.SYSTEM_PROMPT = build_system_prompt(base_template)
        super().__init__(client, context_provider)
