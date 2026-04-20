from agent.base import BaseAgent
from agent.models.review import SoundnessReviewResponse
from agent.models.enums import AgentName


class SoundnessReviewerAgent(BaseAgent):
    AGENT_NAME = AgentName.SOUNDNESS_REVIEWER
    RAG_QUERY = (
        "experimental design methodology statistical analysis validity threats "
        "reproducibility datasets baselines evaluation metrics ablation study"
    )
    SYSTEM_PROMPT = (
        "Sei un revisore scientifico specializzato nella solidità metodologica dei paper accademici. "
        "Valuta la validità degli esperimenti, il rigore statistico e se le conclusioni sono supportate dai dati. "
        "Fornisci osservazioni concrete e specifiche. Mantieni il tono professionale. "
        "Usa max 400 parole nel contenuto testuale."
    )
    RESPONSE_SCHEMA = SoundnessReviewResponse
    MESSAGE_LABEL = "Paper"
