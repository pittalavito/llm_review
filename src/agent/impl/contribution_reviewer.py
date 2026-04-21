
from agent.base import BaseAgent
from models.agent import AgentName, ContributionReviewResponse

class ContributionReviewerAgent(BaseAgent):
    AGENT_NAME = AgentName.CONTRIBUTION_REVIEWER
    RAG_SECTIONS = ["abstract", "introduction", "related_work"]
    RAG_QUERY = (
        "novelty originality contribution innovation state of the art prior work "
        "comparison limitations future work impact significance"
    )
    SYSTEM_PROMPT = (
        "Sei un revisore scientifico specializzato nella valutazione del contributo originale dei paper accademici. "
        "Valuta originalità, rilevanza rispetto allo stato dell'arte e impatto potenziale sulla comunità scientifica. "
        "Fornisci osservazioni concrete e specifiche. Mantieni il tono professionale. "
        "Usa max 400 parole nel contenuto testuale."
    )
    RESPONSE_SCHEMA = ContributionReviewResponse
    MESSAGE_LABEL = "Paper"
