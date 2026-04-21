
from agent.base import BaseAgent
from models.agent import AgentName, ContributionReviewResponse

class ContributionReviewerAgent(BaseAgent[ContributionReviewResponse]):
    AGENT_NAME = AgentName.CONTRIBUTION_REVIEWER
    RAG_SECTIONS = ["abstract", "introduction", "related_work"]
    RAG_QUERY = (
        "novelty originality contribution innovation state of the art prior work "
        "comparison limitations future work impact significance"
    )
    SYSTEM_PROMPT = (
        "You are a scientific reviewer specializing in evaluating the original contribution of academic papers. "
        "Evaluate originality, relevance relative to the state of the art, and potential impact on the scientific community. "
        "Provide concrete and specific observations. Maintain a professional tone. "
        "Use a maximum of 400 words in the textual content."
    )
    RESPONSE_SCHEMA = ContributionReviewResponse
