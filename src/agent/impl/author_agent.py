from agent.base import BaseAgent
from agent.prompting.author import build_system_prompt
from models.agent import AgentName, AuthorResponse

class AuthorAgent(BaseAgent[AuthorResponse]):
    AGENT_NAME = AgentName.AUTHOR_AGENT
    RAG_SECTIONS = ["methods", "results", "conclusion", "discussion"]
    RAG_QUERY = "weaknesses limitations experimental design reproducibility improvements"
    SYSTEM_PROMPT = build_system_prompt()
    RESPONSE_SCHEMA = AuthorResponse

    def __init__(self, client, context_provider=None, base_template: str | None = None):
        if base_template:
            self.SYSTEM_PROMPT = build_system_prompt(base_template)
        super().__init__(client, context_provider)
