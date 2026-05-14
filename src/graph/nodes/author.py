from agent.base import BaseAgent
from agent.prompting.author import build_message
from graph.nodes._factory import make_node
from graph.state import ReviewState


def _build_message(state: ReviewState) -> str:
    return build_message(state)


def _update(state, response, run) -> dict:
    payload = response.payload
    return {
        "author_response": payload.model_dump(),
        "revised_sections": {s.section_name: s.content for s in payload.revised_sections},
        "agent_runs": [run.model_dump()],
    }


def author_node(agent: BaseAgent):
    return make_node(agent, _build_message, _update, use_paper_path=True, round_offset=-1)
