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
        self._agents: dict[AgentName, BaseAgent] = {}
        self._graph = None
        self._lock = threading.Lock()


    def compile(self, graph_agent_config: GraphAgentConfig, agents: dict[AgentName, BaseAgent]) -> None:
        """Crea gli agenti con i client specificati e compila il grafo."""    
        with self._lock:
            self._agents = agents
            
            state = GraphBuilder.build(self._agents)
            self._graph = state.compile()
        
        logger.info("Graph compiled with %d agents, max_rounds=%d", len(graph_agent_config.agents), graph_agent_config.max_rounds)


    def invoke(self, paper_path: str, rag_top_k: int | None = None, force_reindex: bool = False) -> tuple[dict, dict]:
        """Esegue il grafo in modalità RAG. Unico entry point per la review."""
        if self._graph is None:
            raise RuntimeError("Graph not compiled. Call compile_graph() first.")

        _, relative_path, retrieval_metadata = self._retrieval_service.prepare_and_get_text(
            paper_path=paper_path,
            top_k=rag_top_k,
            force_reindex=force_reindex,
        )

        initial_state = self._initial_state(relative_path, rag_top_k, retrieval_metadata)
        result = self._graph.invoke(initial_state)
        return result, retrieval_metadata      

    
    def _initial_state(paper_path: str, rag_top_k: int | None, retrieval_metadata: dict) -> ReviewState:
        return {
            "paper_path": paper_path,
            "rag_top_k": rag_top_k,
            "retrieval_metadata": retrieval_metadata,
            "reviews": [],
            "meta_review": None,
            "decision": None,
            "revision_notes": None,
            "current_round": 0
        }