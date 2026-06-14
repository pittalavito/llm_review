import logging

from datetime import datetime, timezone
from threading import RLock
from config import Config, RESULTS_DIR
from models.agent import AgentName
from models.run_record import AgentRun, RunRecord
from agent.base import BaseAgent
from graph.builder import GraphBuilder
from graph.config import GraphAgentConfig
from graph.state import ReviewState
from service.retrieval_service import RetrievalService
from graph.result_repository import ResultRepository


logger = logging.getLogger(__name__)

_LOGGER_PREFIX = "[GraphService]"


class GraphService:

    def __init__(self, config: Config, retrieval_service: RetrievalService):
        self._config = config
        self._retrieval_service = retrieval_service
        self._graph_config: GraphAgentConfig | None = None
        self._graph = None
        self._lock = RLock()
        self._result_repository = ResultRepository(RESULTS_DIR.resolve())

    def compile(self, agents: dict[AgentName, BaseAgent], graph_config: GraphAgentConfig) -> None:
        with self._lock:
            self._graph_config = graph_config
            self._graph = GraphBuilder.build(agents).compile()
        
        logger.info(f"{_LOGGER_PREFIX} Graph compiled — agents={len(agents)} max_rounds={graph_config.max_rounds}")

    def invoke(self, paper_path: str, run_description: str, force_reindex: bool = False) -> tuple[dict, dict]:
        if self._graph is None or self._graph_config is None:
            raise RuntimeError(f"{_LOGGER_PREFIX} Graph not compiled. Call compile_graph() first.")

        metadata = self._retrieval_service.index_paper(paper_path, force_reindex=force_reindex)
        relative_path = metadata.paper_path
        retrieval_metadata = metadata.model_dump()

        initial_state = self._build_initial_state(relative_path, retrieval_metadata)
        result = self._graph.invoke(initial_state)

        self._save_run(result, relative_path, run_description, retrieval_metadata)

        return result, retrieval_metadata

    def get_graph_config(self) -> dict | None:
        if self._graph_config is None:
            return None
        return self._graph_config.model_dump()

    def list_runs(self):
        return self._result_repository.list()

    def get_run(self, run_id: str):
        return self._result_repository.get(run_id)

    def get_agent_runs(self, run_id: str, agent_name: AgentName | None = None, round_index: int | None = None) -> list[dict]:
        record = self._result_repository.get(run_id)
        runs = record.agent_runs

        if agent_name is not None:
            runs = [r for r in runs if r.agent == agent_name]
        if round_index is not None:
            runs = [r for r in runs if r.round == round_index]

        return [r.model_dump() for r in runs]

    def _build_initial_state(self, paper_path: str, retrieval_metadata: dict) -> ReviewState:
        return {
            "paper_path": paper_path,
            "retrieval_metadata": retrieval_metadata,
            "reviews": [],
            "meta_review": None,
            "area_chair_response": None,
            "decision": None,
            "author_response": None,
            "revised_sections": None,
            "current_round": 0,
            "max_rounds": self._graph_config.max_rounds,
            "agent_runs": [],
        }

    def _save_run(self, result: dict, paper_path: str, run_description: str, retrieval_metadata: dict) -> None:
        try:
            run_id = ResultRepository.build_run_id(paper_path)
            agent_runs = [AgentRun.model_validate(r) for r in result.get("agent_runs", [])]
            record = RunRecord(
                run_id=run_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                paper_path=paper_path,
                run_description=run_description,
                decision=result.get("decision"),
                total_rounds=result.get("current_round", 0),
                reviews=result.get("reviews"),
                meta_review=result.get("meta_review"),
                area_chair_response=result.get("area_chair_response"),
                author_response=result.get("author_response"),
                retrieval_metadata=retrieval_metadata,
                graph_config=self._graph_config.model_dump(),
                agent_runs=agent_runs,
            )
            self._result_repository.save(record)
        except Exception:
            logger.exception(f"{_LOGGER_PREFIX} Failed to save run record for paper: {paper_path}")
