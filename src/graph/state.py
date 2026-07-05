import json
import operator
from typing import Annotated, TypedDict


class ReviewState(TypedDict):
    # Relative path to the paper — enables per-agent RAG
    paper_path: str | None

    # Indexing metadata
    retrieval_metadata: dict | None

    # Reviews produced by the 3 reviewers — accumulated across all rounds
    reviews: Annotated[list, operator.add]

    # Output of the meta-reviewer (overwritten each round)
    meta_review: dict | None

    # Output of the area chair — final binding decision (overwritten each round)
    area_chair_response: dict | None

    # Current decision: accept | minor_revision | major_revision | reject (set by area chair)
    decision: str | None

    # Author rebuttal and revised sections produced by the author agent (overwritten each round)
    author_response: dict | None

    # Revised paper sections extracted from author_response for easy injection into reviewers
    revised_sections: dict | None

    # Current round counter (incremented by the meta-reviewer)
    current_round: int

    # Maximum number of revision rounds before forcing termination
    max_rounds: int

    # Agent invocation history — accumulated across all rounds
    agent_runs: Annotated[list, operator.add]


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
