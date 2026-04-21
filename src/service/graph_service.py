import logging
import threading

from config import Config
from models.agent import AgentName
from agent.base import BaseAgent
from graph.builder import GraphBuilder
from graph.config import GraphAgentConfig
from graph.state import ReviewState
from service.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)


class GraphService:

    def __init__(self, config: Config, retrieval_service: RetrievalService):
        self._config = config
        self._retrieval_service = retrieval_service
        self._graph_config: GraphAgentConfig | None = None
        self._graph = None
        self._lock = threading.Lock()


    def compile(self, agents: dict[AgentName, BaseAgent], graph_config: GraphAgentConfig) -> None:
        with self._lock:
            self._graph_config = graph_config
            self._graph = GraphBuilder.build(agents).compile()
        logger.info(
            "Graph compiled — agents=%d max_rounds=%d",
            len(agents), graph_config.max_rounds,
        )


    def invoke(self, paper_path: str, rag_top_k: int | None = None, force_reindex: bool = False) -> tuple[dict, dict]:
        if self._graph is None or self._graph_config is None:
            raise RuntimeError("Graph not compiled. Call compile_graph() first.")

        metadata = self._retrieval_service.index_paper(paper_path, force_reindex=force_reindex)
        relative_path = metadata.paper_path
        retrieval_metadata = metadata.model_dump()

        initial_state = self._build_initial_state(relative_path, rag_top_k, retrieval_metadata)
        result = self._graph.invoke(initial_state)
        return result, retrieval_metadata


    def _build_initial_state(self, paper_path: str, rag_top_k: int | None, retrieval_metadata: dict) -> ReviewState:
        return {
            "paper_path": paper_path,
            "rag_top_k": rag_top_k,
            "retrieval_metadata": retrieval_metadata,
            "reviews": [],
            "meta_review": None,
            "decision": None,
            "revision_notes": None,
            "current_round": 0,
            "max_rounds": self._graph_config.max_rounds,
        }
