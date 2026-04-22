
from agent.base import BaseAgent
from models.agent import AgentName, AuthorResponse

class AuthorAgent(BaseAgent[AuthorResponse]):
    AGENT_NAME = AgentName.AUTHOR_AGENT
    RAG_SECTIONS = ["methods", "results", "conclusion", "discussion"]
    RAG_QUERY = (
        "weaknesses limitations experimental design reproducibility improvements"
    )
    SYSTEM_PROMPT = (
        "You are the author of a scientific paper that has just received peer reviews. "
        "Your task is to respond to the reviewers' critiques in two ways:\n"
        "1. Write a concise rebuttal defending the validity of your work and clarifying any misunderstandings.\n"
        "2. Revise the weakest sections of your paper to address the most critical concerns. "
        "For each revised section, produce a complete rewritten version of that section's text.\n"
        "Be constructive, precise, and scientific in tone. "
        "Focus on the most impactful weaknesses identified. Use a maximum of 500 words total in the rebuttal."
    )
    RESPONSE_SCHEMA = AuthorResponse
