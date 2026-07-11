from domain.agent.base import BaseAgent
from domain.agent.prompting.area_chair import build_system_prompt
from models.agent import AgentName, AreaChairResponse, AreaChairStyle


class AreaChairAgent(BaseAgent[AreaChairResponse]):
    AGENT_NAME = AgentName.AREA_CHAIR
    RESPONSE_SCHEMA = AreaChairResponse
    RAG_QUERY = ""

    def __init__(
        self, 
        client, 
        context_provider=None, 
        style: AreaChairStyle = AreaChairStyle.INCLUSIVE,
        base_template: str | None = None
    ):
        self.SYSTEM_PROMPT = build_system_prompt(style, base_template)
        super().__init__(client, context_provider)
