from agent.base import BaseAgent
from agent.prompting.reviewer import build_message
from graph.nodes._factory import MessageBuilder, make_node
from graph.state import ReviewState
from models.agent import AgentName


def _build_message(agent_name: AgentName) -> MessageBuilder:
    def build(state: ReviewState) -> str:
        return build_message(state, agent_name)
    return build


def _update(state, response, run) -> dict:
    return {"reviews": [response.to_json()], "agent_runs": [run.model_dump()]}


def reviewer_node(agent: BaseAgent):
    return make_node(agent, _build_message(agent.name), _update, use_paper_path=True)
