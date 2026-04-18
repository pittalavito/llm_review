from agent.base_agent import BaseAgent
from clients.llm.base_llm_client import BaseLLMClient
from schemas.enums import AgentName
from schemas.agent.methodology_review import MethodologyReviewResponse


class MethodologyReviewerAgent(BaseAgent):
    SYSTEM_PROMPT = (
        "Sei un critico specializzato in spettacoli teatrali. "
        "Valuta il rigore metodologico del testo: design dello studio, validità degli esperimenti e riproducibilità. "
        "Fornisci osservazioni concrete, specifiche e utili per migliorare il lavoro. "
        "Mantieni il tono professionale e conciso. "
        "Usa max 500 parole complessive nel contenuto testuale."
    )
    RESPONSE_SCHEMA = MethodologyReviewResponse
    MESSAGE_LABEL = "Paper"

    def __init__(self, llm: BaseLLMClient):
        super().__init__(llm=llm, name=AgentName.METHODOLOGY_REVIEWER)


