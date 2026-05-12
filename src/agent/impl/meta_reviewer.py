from agent.base import BaseAgent
from models.agent import AgentName, MetaReviewResponse

class MetaReviewerAgent(BaseAgent[MetaReviewResponse]):
    AGENT_NAME = AgentName.META_REVIEWER
    SYSTEM_PROMPT = (
        "You are an academic meta-reviewer. "
        "You receive the reviews from three peer reviewers "
        "and must produce an aggregated assessment with a recommendation for the Area Chair. "
        "The recommendation must be one of: accept, minor_revision, major_revision, reject. "
        "Consider the ratings, reasons for acceptance/rejection, and overall consensus. "
        "Be concise, fair, and justify your recommendation. Use a maximum of 500 words in the textual content."
    )
    RESPONSE_SCHEMA = MetaReviewResponse
