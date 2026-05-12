import json

from agent.base import BaseAgent
from graph.nodes._factory import last_reviews, make_node
from graph.state import ReviewState


def _build_message(state: ReviewState) -> str:
    labeled = [
        f"[{r.get('agent', 'unknown_reviewer').upper()}]\n"
        f"{json.dumps(r['payload'], ensure_ascii=False, indent=2)}"
        for r in last_reviews(state)
    ]
    reviews_block = "\n\n".join(labeled)
    meta = json.dumps(state.get("meta_review") or {}, ensure_ascii=False, indent=2)
    ac = json.dumps(state.get("area_chair_response") or {}, ensure_ascii=False, indent=2)

    return (
        f"You have received the following peer reviews:\n\n{reviews_block}\n\n"
        f"Meta-reviewer summary:\n{meta}\n\n"
        f"Area Chair decision:\n{ac}\n\n"
        "Write a general rebuttal, a targeted response to EACH reviewer by name, "
        "and provide revised versions of the sections that need improvement."
    )


def _update(state, response, run) -> dict:
    payload = response.payload
    return {
        "author_response": payload.model_dump(),
        "revised_sections": {s.section_name: s.content for s in payload.revised_sections},
        "agent_runs": [run.model_dump()],
    }


def author_node(agent: BaseAgent):
    return make_node(agent, _build_message, _update, use_paper_path=True, round_offset=-1)
