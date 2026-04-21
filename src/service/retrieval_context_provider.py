from models.protocols import ContextProvider
from service.retrieval_service import RetrievalService


class RetrievalContextProvider(ContextProvider):
    """Adapter between RetrievalService and the ContextProvider Protocol.
    Configured with agent-specific queries and sections.
    The agent is unaware of RetrievalService — it only receives get_context().
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
