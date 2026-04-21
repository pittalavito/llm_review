from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service.retrieval_service import RetrievalService


class BM25ContextProvider:
    """Implementazione del ContextProvider Protocol basata su BM25.
    Configurata con query e sezioni specifiche dell'agente.
    L'agente non conosce né RetrievalService né BM25 — riceve solo get_context().
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        query: str,
        sections: list[str] | None = None,
        top_k: int | None = None,
    ):
        self._retrieval = retrieval_service
        self._query = query
        self._sections = sections or []
        self._top_k = top_k

    def get_context(self, paper_path: str) -> str:
        return self._retrieval.retrieve_for_agent(
            paper_path=paper_path,
            query=self._query,
            sections=self._sections,
            top_k=self._top_k,
        )
