from models.protocols import ContextProvider
from service.retrieval_service import RetrievalService


class RetrievalContextProvider(ContextProvider):
    """Adapter between RetrievalService and the ContextProvider Protocol.
    Configured with agent-specific queries and sections.
    The agent is unaware of RetrievalService — it only receives get_context().

    query=None means the BM25 query is derived at runtime from the paper's own
    abstract, so retrieval stays grounded in the paper's vocabulary rather than
    a generic keyword list hardcoded in the agent class.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        query: str | None,
        sections: list[str] | None = None,
        top_k: int | None = None,
        query_suffix: str = "",
    ):
        self._retrieval = retrieval_service
        self._query = query              # None = resolve from abstract at call time
        self._sections = sections or []
        self._top_k = top_k
        self._query_suffix = query_suffix  # appended to the resolved query (e.g. focus terms)
        self._last_trace: dict | None = None

    def get_context(self, paper_path: str) -> str:
        base_query = self._query or self._retrieval.extract_abstract(paper_path)
        query = f"{base_query} {self._query_suffix}".strip() if self._query_suffix else base_query
        context = self._retrieval.retrieve_for_agent(
            paper_path=paper_path,
            query=query,
            sections=self._sections,
            top_k=self._top_k,
        )
        self._last_trace = {
            "provider": self.__class__.__name__,
            "paper_path": paper_path,
            "base_query": base_query,
            "query_suffix": self._query_suffix,
            "resolved_query": query,
            "sections": list(self._sections),
            "top_k": self._top_k,
            "context_chars": len(context),
        }
        return context

    def get_last_trace(self) -> dict | None:
        return self._last_trace
