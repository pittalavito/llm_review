from agent.base import BaseAgent
from models.agent import AgentName, SoundnessReviewResponse

class SoundnessReviewerAgent(BaseAgent[SoundnessReviewResponse]):
    AGENT_NAME = AgentName.SOUNDNESS_REVIEWER
    RAG_SECTIONS = ["methods", "experiments", "results"]
    RAG_QUERY = (
        "experimental design methodology statistical analysis validity threats "
        "reproducibility datasets baselines evaluation metrics ablation study"
    )
    SYSTEM_PROMPT = (
        "You are a scientific reviewer specializing in the methodological soundness of academic papers. "
        "Evaluate the validity of experiments, statistical rigor, and whether conclusions are supported by the data. "
        "Provide concrete and specific observations. Maintain a professional tone. "
        "Use a maximum of 400 words in the textual content."
    )
    RESPONSE_SCHEMA = SoundnessReviewResponse
