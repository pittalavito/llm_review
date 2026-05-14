from agent.base import BaseAgent
from agent.prompting.meta_reviewer import build_message
from graph.nodes._factory import make_node
from graph.state import ReviewState


def _build_message(state: ReviewState) -> str:
    return build_message(state)


def _update(state, response, run) -> dict:
    return {
        "meta_review": response.payload.model_dump(),
        "current_round": state["current_round"] + 1,
        "agent_runs": [run.model_dump()],
    }


def meta_node(agent: BaseAgent):
    return make_node(agent, _build_message, _update)
