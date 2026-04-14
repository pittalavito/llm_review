from agent.base_agent import BaseAgent
from clients.llm.base_llm_client import BaseLLMClient
from schemas.enums import AgentName


class MethodologyReviewer(BaseAgent):
    
    def __init__(self, llm: BaseLLMClient):
        super().__init__(llm=llm, name=AgentName.METHODOLOGY_REVIEWER)

    @property
    def system_prompt(self) -> str:
        return """Sei un reviewer accademico specializzato in metodologia scientifica.
        Analizza il rigore metodologico del paper.
        Valuta: design dello studio, validità degli esperimenti, riproducibilità."""