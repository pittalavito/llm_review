from agent.base import BaseAgent
from graph.nodes._factory import compact_reviews, last_reviews, make_node
from graph.state import ReviewState


def _build_message(state: ReviewState) -> str:
    return compact_reviews(last_reviews(state))


def _update(state, response, run) -> dict:
    return {
        "meta_review": response.payload.model_dump(),
        "current_round": state["current_round"] + 1,
        "agent_runs": [run.model_dump()],
    }


def meta_node(agent: BaseAgent):
    return make_node(agent, _build_message, _update)
