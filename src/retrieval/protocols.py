from typing import Protocol


class ContextProvider(Protocol):
    """Interfaccia minima per il recupero del contesto RAG da parte degli agenti.
    L'agente non sa cosa c'è dietro — BM25, embedding, full text, mock.
    """

    def get_context(self, paper_path: str) -> str:
        ...
