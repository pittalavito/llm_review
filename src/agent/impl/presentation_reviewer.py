from agent.base import BaseAgent
from agent.models.review import PresentationReviewResponse
from agent.models.enums import AgentName


class PresentationReviewerAgent(BaseAgent):
    AGENT_NAME = AgentName.PRESENTATION_REVIEWER
    RAG_QUERY = (
        "abstract introduction related work background figures tables notation "
        "clarity writing structure organization conclusion"
    )
    SYSTEM_PROMPT = (
        "Sei un revisore scientifico specializzato nella qualità della presentazione dei paper accademici. "
        "Valuta chiarezza espositiva, struttura logica, qualità delle figure e della scrittura. "
        "Fornisci osservazioni concrete e specifiche. Mantieni il tono professionale. "
        "Usa max 400 parole nel contenuto testuale."
    )
    RESPONSE_SCHEMA = PresentationReviewResponse
    MESSAGE_LABEL = "Paper"
