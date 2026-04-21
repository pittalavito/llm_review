
from agent.base import BaseAgent
from models.agent import AgentName, PresentationReviewResponse 

class PresentationReviewerAgent(BaseAgent[PresentationReviewResponse]):
    AGENT_NAME = AgentName.PRESENTATION_REVIEWER
    RAG_SECTIONS = []  # entire document — evaluates global structure
    RAG_QUERY = (
        "abstract introduction related work background figures tables notation "
        "clarity writing structure organization conclusion"
    )
    SYSTEM_PROMPT = (
        "You are a scientific reviewer specializing in the presentation quality of academic papers. "
        "Evaluate expository clarity, logical structure, quality of figures, and writing. "
        "Provide concrete and specific observations. Maintain a professional tone. "
        "Use a maximum of 400 words in the textual content."
    )
    RESPONSE_SCHEMA = PresentationReviewResponse
