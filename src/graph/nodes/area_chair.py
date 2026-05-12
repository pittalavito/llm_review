from agent.base import BaseAgent
from agent.prompting.area_chair import build_message
from graph.nodes._factory import make_node
from graph.state import ReviewState


def _build_message(state: ReviewState) -> str:
    return build_message(state)


def _update(state, response, run) -> dict:
    payload = response.payload
    return {
        "area_chair_response": payload.model_dump(),
        "decision": payload.decision,
        "agent_runs": [run.model_dump()],
    }


def area_chair_node(agent: BaseAgent):
    # meta_node already incremented current_round, so AC reports for round - 1.
    return make_node(agent, _build_message, _update, round_offset=-1)
