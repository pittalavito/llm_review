from agent.base import BaseAgent
from models.agent import AgentName, AreaChairResponse, AreaChairStyle

_STYLE_MODIFIER = {
    AreaChairStyle.AUTHORITARIAN: (
        "You rely primarily on your own expert assessment of the paper. "
        "Reviewer ratings and the meta-reviewer recommendation are secondary inputs — "
        "you may override them if your judgment differs."
    ),
    AreaChairStyle.CONFORMIST: (
        "You defer strongly to the consensus of the reviewer ratings and the meta-reviewer recommendation. "
        "You minimize the influence of your own independent judgment and follow the reviewers' lead."
    ),
    AreaChairStyle.INCLUSIVE: (
        "You carefully consider all available information: individual reviews, the author rebuttal, "
        "the meta-reviewer recommendation, and your own expertise. "
        "You weigh all perspectives before making a balanced final decision."
    ),
}

_BASE_PROMPT = (
    "You are an Area Chair (AC) for a machine learning / NLP conference. "
    "You receive the peer reviews, the author rebuttal, and the meta-reviewer's recommendation. "
    "Your task is to produce the final, binding acceptance decision for the paper. "
    "The decision must be one of: accept, minor_revision, major_revision, reject. "
    "Be fair, concise, and justify your decision clearly."
)

_DEFAULT_STYLE = AreaChairStyle.INCLUSIVE


class AreaChairAgent(BaseAgent[AreaChairResponse]):
    AGENT_NAME = AgentName.AREA_CHAIR
    RESPONSE_SCHEMA = AreaChairResponse
    RAG_QUERY = ""

    def __init__(self, client, context_provider=None, style: AreaChairStyle = _DEFAULT_STYLE):
        self.SYSTEM_PROMPT = f"{_BASE_PROMPT} {_STYLE_MODIFIER[style]}"
        super().__init__(client, context_provider)
