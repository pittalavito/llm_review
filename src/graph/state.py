import operator
from typing import Annotated, TypedDict


class ReviewState(TypedDict):
    # Path relativo al paper — abilita il RAG per-agente
    paper_path: str | None

    # top_k da usare nel RAG (None = usa il default del servizio)
    rag_top_k: int | None

    # Metadata dell'indicizzazione (impostati da invoke_from_file, non dai nodi)
    retrieval_metadata: dict | None

    # Review prodotte dai 3 reviewer — accumulate su tutti i round
    reviews: Annotated[list, operator.add]

    # Output del meta-reviewer (sovrascritto ad ogni round)
    meta_review: dict | None

    # Decisione del meta-reviewer: accept | minor_revision | major_revision | reject
    decision: str | None

    # Note di revisione prodotte dal refinement agent (sovrascritte ad ogni round)
    revision_notes: str | None
