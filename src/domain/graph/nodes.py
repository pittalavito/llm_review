from __future__ import annotations

from typing import Callable

from domain.agent.base import BaseAgent
from domain.graph.state import ReviewState
from domain.agent.prompting import area_chair, author, meta_reviewer, reviewer

from models.agent import AgentName, ReviewDecision
from models.run_record import AgentRun


MessageBuilder = Callable[[ReviewState], str]
StateUpdater = Callable[[ReviewState, "AgentResponse", AgentRun], dict]


def reviewer_node(agent: BaseAgent):
    def build(state: ReviewState) -> str:
        return reviewer.build_message(state, agent.name)

    def update(state, response, run) -> dict:
        return {"reviews": [response.to_json()], "agent_runs": [run.model_dump()]}

    return _make_node(agent, build, update, use_paper_path=True)


def meta_node(agent: BaseAgent):
    def update(state, response, run) -> dict:
        return {
            "meta_review": response.payload.model_dump(),
            "current_round": state["current_round"] + 1,
            "agent_runs": [run.model_dump()],
        }

    return _make_node(agent, meta_reviewer.build_message, update)


def area_chair_node(agent: BaseAgent):
    def update(state, response, run) -> dict:
        payload = response.payload
        return {
            "area_chair_response": payload.model_dump(),
            "decision": payload.decision,
            "agent_runs": [run.model_dump()],
        }

    return _make_node(agent, area_chair.build_message, update, round_offset=-1)


def author_node(agent: BaseAgent):
    def update(state, response, run) -> dict:
        payload = response.payload
        return {
            "author_response": payload.model_dump(),
            "revised_sections": {s.section_name: s.content for s in payload.revised_sections},
            "agent_runs": [run.model_dump()],
        }

    return _make_node(agent, author.build_message, update, use_paper_path=True, round_offset=-1)
    
    
def area_chair_conditional_edges(state: ReviewState) -> str:
    """After the Area Chair: terminate on accept/minor_revision, else loop to revise."""
    
    terminal_decision = {ReviewDecision.ACCEPT, ReviewDecision.MINOR_REVISION}
    return "accept" if state.get("decision") in terminal_decision else "revise"


def end_loop_conditional_edges(state: ReviewState) -> str:
    """After the Author: keep looping while rounds remain, else end."""
    
    return "end" if state["current_round"] >= state["max_rounds"] else "loop"


def _make_node(
    agent: BaseAgent,
    build_message: MessageBuilder,
    build_update: StateUpdater,
    use_paper_path: bool = False,
    round_offset: int = 0,
):
    """Wrap an agent into a LangGraph node.
    `build_message` produces the human prompt from the current state.
    `build_update` produces the state delta from the agent response.
    `round_offset` adjusts the recorded round (Area Chair / Author run after
    `meta_node` has already incremented `current_round`).
    """
    
    def node(state: ReviewState) -> dict:
        message = build_message(state)
        paper_path = state.get("paper_path") if use_paper_path else None

        response = agent.run(message, paper_path=paper_path)
        run = AgentRun(
            agent=response.agent,
            round=state["current_round"] + round_offset,
            input_message=response.input_message or message,
            context_used=response.context_used,
            response_payload=response.payload.model_dump(),
            prompt_trace=response.prompt_trace,
            runtime_trace=response.runtime_trace,
        )
        return build_update(state, response, run)
    return node