from typing import Protocol


class RetrievalContextProvider(Protocol):
    """Interfaccia minimale richiesta dal domain per il recupero del contesto RAG."""

    def retrieve_context(
        self,
        paper_path: str,
        top_k: int | None,
        force_reindex: bool,
        query: str | None,
    ) -> dict:
        ...
