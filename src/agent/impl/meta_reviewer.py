
from agent.base import BaseAgent
from models.agent import AgentName, MetaReviewResponse

class MetaReviewerAgent(BaseAgent[MetaReviewResponse]):
    AGENT_NAME = AgentName.META_REVIEWER
    SYSTEM_PROMPT = (
        "You are an academic meta-reviewer. "
        "You receive the reviews from three specialized reviewers (soundness, presentation, contribution) "
        "and must produce an aggregated assessment with a final decision. "
        "The decision must be one of: accept, minor_revision, major_revision, reject. "
        "Be concise, fair, and justify the decision. Use a maximum of 500 words in the textual content."
    )
    RESPONSE_SCHEMA = MetaReviewResponse
