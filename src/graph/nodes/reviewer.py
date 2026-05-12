from agent.base import BaseAgent
from graph.nodes._factory import MessageBuilder, make_node, targeted_rebuttal
from graph.state import ReviewState
from models.agent import AgentName


def _build_message(agent_name: AgentName) -> MessageBuilder:
    def build(state: ReviewState) -> str:
        message = "Analyze the paper and provide a structured review."
        author_response = state.get("author_response")
        if not author_response:
            return message

        rebuttal = targeted_rebuttal(author_response, agent_name)
        if rebuttal:
            message += f"\n\nAuthor's response to your review:\n{rebuttal}"

        revised = author_response.get("revised_sections", [])
        if revised:
            sections_text = "\n\n".join(
                f"[Revised {s['section_name'].upper()}]\n{s['content']}" for s in revised
            )
            message += f"\n\nRevised paper sections submitted by the author:\n{sections_text}"
        return message
    return build


def _update(state, response, run) -> dict:
    return {"reviews": [response.to_json()], "agent_runs": [run.model_dump()]}


def reviewer_node(agent: BaseAgent):
    return make_node(agent, _build_message(agent.name), _update, use_paper_path=True)
