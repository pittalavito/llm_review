from fastapi import Request
from config import Config, RESOURCE_DIR
from graph.config import GraphAgentConfig
from service.graph_service import GraphService
from service.agent_service import AgentService
from service.retrieval_service import RetrievalService
from comparison.comparator import ReviewComparator

_INDEX_PATH = RESOURCE_DIR / "open-review-index.json"


class Container:
    """DI container for configuration and service registry."""

    def __init__(self, config: Config):
        self._config = config
        self._agent_service = AgentService(config)
        self._retrieval_service = RetrievalService(config)
        self._graph_service = GraphService(config, self._retrieval_service)
        self._comparator = ReviewComparator(
            results_dir=RESOURCE_DIR / "results",
            index_path=_INDEX_PATH,
            cache_dir=RESOURCE_DIR / "openreview",
        )
    
    
    def health_check(self) -> dict:
        """Simple health check endpoint returning app version."""
        version: str = self._config.app_version
        return {"status": "ok", "version": version}
    
    
    def test_llm(self, model, temperature, message) -> str:
        """Test LLM response for given model, temperature and message."""
        agent_service: AgentService = self._agent_service
        return agent_service.invoke_client(model, temperature, message)
    
    
    def build_agent_prompt(self, name, message) -> dict:
        """Build prompt preview for a given agent — no LLM instantiation needed."""
        agent_class = AgentService.get_agent_class(name)
        return agent_class.build_preview(message)    
    
    
    def test_agent(self, name, model, temperature, message):
        """Test agent response for given agent name, model, temperature and message."""
        return self._agent_service.run_agent(name, model, temperature, message)
    
    
    def list_papers_path(self) -> list[str]:
        """List relative paths of all available paper files."""
        retrieval_service: RetrievalService = self._retrieval_service
        return retrieval_service.list_papers()


    def index_paper(self, paper_path: str, force_reindex: bool = False) -> dict:
        """Build or reuse the BM25 index for a paper. Returns indexing metadata."""
        retrieval_service: RetrievalService = self._retrieval_service
        metadata = retrieval_service.index_paper(paper_path, force_reindex)
        return metadata.model_dump()


    def list_indexed_papers(self) -> list[str]:
        """Return paper_path for every paper that has a persisted BM25 index."""
        retrieval_service: RetrievalService = self._retrieval_service
        return retrieval_service.list_indexed_papers()


    def get_indexed_paper(self, paper_path: str) -> dict:
        """Return index metadata for a specific paper. Raises ValueError if not indexed."""
        retrieval_service: RetrievalService = self._retrieval_service
        info = retrieval_service.get_indexed_paper(paper_path)
        return info.model_dump()


    def test_agent_with_retrieval(self, name, model, temperature, message: str, paper_path: str, top_k: int | None = None):
        """Run an agent using RAG context retrieved from a paper — agent drives its own retrieval."""
        agent = self._agent_service.init_agent(name, model, temperature, self._retrieval_service, top_k=top_k)
        return agent.run(message, paper_path=paper_path)


    def compile_graph(self, graph_config: GraphAgentConfig | None = None) -> None:
        graph_config = graph_config or GraphAgentConfig.default_config()
        agents = self._agent_service.init_agents_from_graph_config(graph_config, self._retrieval_service)
        self._graph_service.compile(agents, graph_config)


    def invoke_graph(
        self,
        paper_path: str,
        run_description: str,
        force_reindex: bool = False,
    ) -> tuple[dict, dict]:
        return self._graph_service.invoke(paper_path, run_description, force_reindex)


    def get_graph_config(self) -> dict | None:
        return self._graph_service.get_graph_config()


    def list_runs(self) -> list:
        return self._graph_service.list_runs()


    def get_run(self, run_id: str) -> dict:
        return self._graph_service.get_run(run_id).model_dump()

    def get_agent_runs(self, run_id: str, agent_name=None, round_index: int | None = None) -> list[dict]:
        return self._graph_service.get_agent_runs(run_id, agent_name=agent_name, round_index=round_index)

    def list_comparable_papers(self) -> list[dict]:
        return self._comparator.list_papers()

    def compare_paper(self, paper_path: str) -> dict:
        return self._comparator.compare_paper(paper_path).model_dump()


def inject_container(request: Request) -> Container:
    return request.app.state.container
