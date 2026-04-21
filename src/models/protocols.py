from typing import Protocol


class ContextProvider(Protocol):
    """Minimal interface for RAG context retrieval used by agents.
    The agent does not know what is behind it — BM25, embeddings, full text, or mock.

    Implementations:
        - service.retrieval_context_provider.RetrievalContextProvider
    """

    def get_context(self, paper_path: str) -> str:
        ...
