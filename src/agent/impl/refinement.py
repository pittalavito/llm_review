
from agent.base import BaseAgent
from models.agent import AgentName, RefinementResponse

class RefinementAgent(BaseAgent[RefinementResponse]):
    AGENT_NAME = AgentName.REFINEMENT_AGENT
    RAG_SECTIONS = ["results", "conclusion", "discussion"]
    RAG_QUERY = (
        "limitations weaknesses revision improvements suggestions discussion conclusion"
    )
    SYSTEM_PROMPT = (
        "Sei un agente di raffinamento accademico. "
        "Ricevi il paper originale e la meta-review con la decisione dei revisori. "
        "Il tuo compito è sintetizzare le critiche più importanti e produrre indicazioni concrete "
        "e prioritizzate per migliorare il paper. "
        "Sii specifico e costruttivo. Usa max 500 parole nel contenuto testuale."
    )
    RESPONSE_SCHEMA = RefinementResponse
    MESSAGE_LABEL = "Context"
