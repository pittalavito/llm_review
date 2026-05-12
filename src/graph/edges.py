from graph.state import ReviewState
from models.agent import ReviewDecision


_TERMINAL_DECISIONS = {ReviewDecision.ACCEPT, ReviewDecision.MINOR_REVISION}


def ac_decision(state: ReviewState) -> str:
    """After the Area Chair: terminate on accept/minor_revision, else loop to revise."""
    return "accept" if state.get("decision") in _TERMINAL_DECISIONS else "revise"


def should_loop(state: ReviewState) -> str:
    """After the Author: keep looping while rounds remain, else end."""
    return "end" if state["current_round"] >= state["max_rounds"] else "loop"
