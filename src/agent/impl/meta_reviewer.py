from agent.base import BaseAgent
from agent.prompting.meta_reviewer import build_system_prompt
from models.agent import AgentName, MetaReviewResponse

class MetaReviewerAgent(BaseAgent[MetaReviewResponse]):
    AGENT_NAME = AgentName.META_REVIEWER
    SYSTEM_PROMPT = build_system_prompt()
    RESPONSE_SCHEMA = MetaReviewResponse
