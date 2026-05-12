from agent.base import BaseAgent
from graph.nodes._factory import compact_reviews, last_reviews, make_node
from graph.state import ReviewState


def _build_message(state: ReviewState) -> str:
    meta = state.get("meta_review") or {}
    meta_block = (
        f"score={meta.get('overall_score')} recommendation={meta.get('recommendation')}\n"
        f"{meta.get('summary', '')}"
    )
    rebuttal_block = ""
    author_response = state.get("author_response")
    if author_response:
        rebuttal_block = f"\n\nAuthor rebuttal:\n{author_response.get('rebuttal', '')}"

    return (
        f"Peer reviews:\n{compact_reviews(last_reviews(state))}\n\n"
        f"Meta-reviewer recommendation:\n{meta_block}"
        f"{rebuttal_block}\n\n"
        "Make the final acceptance decision for this paper."
    )


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
