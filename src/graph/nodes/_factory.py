from __future__ import annotations

import json
from typing import Callable

from agent.base import BaseAgent
from graph.state import ReviewState
from models.run_record import AgentRun


MessageBuilder = Callable[[ReviewState], str]
StateUpdater = Callable[[ReviewState, "AgentResponse", AgentRun], dict]  # noqa: F821


# ---------------------------------------------------------------------------
# State accessors — pure functions reused by multiple roles
# ---------------------------------------------------------------------------

def last_reviews(state: ReviewState) -> list[dict]:
    """Return the three most recent reviews as decoded dicts."""
    return [json.loads(r) for r in state["reviews"][-3:]]


def compact_reviews(reviews: list[dict]) -> str:
    """Serialize reviews as a token-efficient block for downstream agents."""
    blocks = []
    for r in reviews:
        p = r.get("payload", {})
        blocks.append(
            f"[{r.get('agent', 'reviewer')}] rating={p.get('rating')}/10 "
            f"confidence={p.get('confidence')}/5\n"
            f"summary: {p.get('summary', '')}\n"
            f"novelty: {p.get('significance_and_novelty', '')}\n"
            f"+: {', '.join(p.get('reasons_for_acceptance') or [])}\n"
            f"-: {', '.join(p.get('reasons_for_rejection') or [])}"
        )
    return "\n\n".join(blocks)


def targeted_rebuttal(author_response: dict, reviewer_name: str) -> str:
    """Pick the rebuttal addressed to `reviewer_name`, falling back to the general one."""
    rebuttals = author_response.get("reviewer_rebuttals", [])
    return next(
        (r["response"] for r in rebuttals if r["reviewer_name"] == reviewer_name),
        author_response.get("rebuttal", ""),
    )


# ---------------------------------------------------------------------------
# Node factory
# ---------------------------------------------------------------------------

def make_node(
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
        )
        return build_update(state, response, run)
    return node
