from agent.base import BaseAgent
from models.agent import AgentName, AuthorResponse

class AuthorAgent(BaseAgent[AuthorResponse]):
    AGENT_NAME = AgentName.AUTHOR_AGENT
    RAG_SECTIONS = ["methods", "results", "conclusion", "discussion"]
    RAG_QUERY = "weaknesses limitations experimental design reproducibility improvements"
    SYSTEM_PROMPT = (
        "You are the author of a scientific paper that has just received peer reviews. "
        "Your task is to respond to the reviewers' critiques in three ways:\n"
        "1. Write a brief general rebuttal summarizing your overall response.\n"
        "2. Write a targeted response to EACH individual reviewer addressing their specific concerns "
        "(use the reviewer's name as provided, e.g. 'reviewer_1').\n"
        "3. Revise the weakest sections of your paper to address the most critical concerns. "
        "For each revised section, produce a complete rewritten version of that section's text.\n"
        "Be constructive, precise, and scientific in tone. "
        "Focus on the most impactful weaknesses identified. Use a maximum of 600 words total."
    )
    RESPONSE_SCHEMA = AuthorResponse
