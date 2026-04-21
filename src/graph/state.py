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

    # Current decision: accept | minor_revision | major_revision | reject
    decision: str | None

    # Revision notes produced by the refinement agent (overwritten each round)
    revision_notes: str | None

    # Current round counter (incremented by the meta-reviewer)
    current_round: int

    # Maximum number of revision rounds before forcing termination
    max_rounds: int

    # Agent invocation history — accumulated across all rounds
    agent_runs: Annotated[list, operator.add]
