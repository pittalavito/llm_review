
from agent.base import BaseAgent
from models.agent import AgentName, RefinementResponse

class RefinementAgent(BaseAgent[RefinementResponse]):
    AGENT_NAME = AgentName.REFINEMENT_AGENT
    RAG_SECTIONS = ["results", "conclusion", "discussion"]
    RAG_QUERY = (
        "limitations weaknesses revision improvements suggestions discussion conclusion"
    )
    SYSTEM_PROMPT = (
        "You are an academic refinement agent. "
        "You receive the original paper and the meta-review containing the reviewers' decision. "
        "Your task is to synthesize the most important critiques and produce concrete, "
        "prioritized guidance for improving the paper. "
        "Be specific and constructive. Use a maximum of 500 words in the textual content."
    )
    RESPONSE_SCHEMA = RefinementResponse
