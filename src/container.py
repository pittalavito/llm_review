from fastapi import Request
from config import Config, RESOURCE_DIR
from agent.prompting.catalog import DEFAULT_PROMPT_SEEDS
from db.engine import create_db_engine, init_db
from db.prompt_repository import PromptRepository
from db.sql_result_repository import SqlResultRepository
from graph.config import GraphAgentConfig
from service.graph_service import GraphService
from service.agent_service import AgentService
from service.retrieval_service import RetrievalService
from comparison.comparator import ReviewComparator

_INDEX_PATH = RESOURCE_DIR / "open-review-index.json"


class Container:
    """DI container: builds and exposes the services, plus the few
    operations that genuinely span more than one of them."""

    def __init__(self, config: Config):
        self.config = config
        self.engine = create_db_engine(config)
        init_db(self.engine)
        self.result_repository = SqlResultRepository(self.engine)
        self.prompt_repository = PromptRepository(self.engine)
        self.prompt_repository.seed_defaults(DEFAULT_PROMPT_SEEDS)
        self.agent_service = AgentService(config)
        self.retrieval_service = RetrievalService(config)
        self.graph_service = GraphService(config, self.retrieval_service, self.result_repository)
        self.comparator = ReviewComparator(
            result_repository=self.result_repository,
            index_path=_INDEX_PATH,
            cache_dir=RESOURCE_DIR / "openreview",
        )

    def test_agent_with_retrieval(self, name, model, temperature, message: str, paper_path: str, top_k: int | None = None):
        """Run an agent using RAG context retrieved from a paper — agent drives its own retrieval."""
        agent = self.agent_service.init_agent(name, model, temperature, self.retrieval_service, top_k=top_k)
        return agent.run(message, paper_path=paper_path)

    def compile_graph(self, graph_config: GraphAgentConfig | None = None) -> None:
        graph_config = graph_config or GraphAgentConfig.default_config()
        agents = self.agent_service.init_agents_from_graph_config(
            graph_config, self.retrieval_service, self.prompt_repository
        )
        self.graph_service.compile(agents, graph_config)

    def invoke_graph(
        self,
        paper_path: str,
        run_description: str,
        force_reindex: bool = False,
    ) -> tuple[dict, dict]:
        return self.graph_service.invoke(paper_path, run_description, force_reindex)


def inject_container(request: Request) -> Container:
    return request.app.state.container
