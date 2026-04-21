
from agent.base import BaseAgent
from models.agent import AgentName, MetaReviewResponse

class MetaReviewerAgent(BaseAgent[MetaReviewResponse]):
    AGENT_NAME = AgentName.META_REVIEWER
    SYSTEM_PROMPT = (
        "Sei un meta-revisore accademico. "
        "Ricevi le review di tre revisori specializzati (solidità, presentazione, contributo) "
        "e devi produrre una valutazione aggregata con una decisione finale. "
        "La decisione deve essere una tra: accept, minor_revision, major_revision, reject. "
        "Sii sintetico, equo e giustifica la decisione. Usa max 500 parole nel contenuto testuale."
    )
    RESPONSE_SCHEMA = MetaReviewResponse
    MESSAGE_LABEL = "Reviews"
