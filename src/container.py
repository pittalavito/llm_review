from fastapi import Request
from config import Config, get_openreview_index_dir, get_openreview_dir, get_papers_dir

from domain.db.engine import create_db_engine
from domain.agent.prompting.catalog import DEFAULT_PROMPT_SEEDS
from models.graph import GraphAgentConfig

from service.graph_service import GraphService
from service.agent_service import AgentService
from service.retrieval_service import RetrievalService
from service.comparator_service import ReviewComparatorService
from service.repository_service import RepositoryService
from service.backup_service import BackupService

class Container:
    """DI container: builds and exposes the services, plus the few
    operations that genuinely span more than one of them."""

    def __init__(self, config: Config):
        self.config = config
        self.engine = create_db_engine(config)
        
        self.repository_service = RepositoryService(self.engine)
        self.repository_service.seed_defaults(DEFAULT_PROMPT_SEEDS)
        self.repository_service.seed_papers(get_papers_dir(), get_openreview_index_dir())
        
        self.backup_service = BackupService(self.engine, config)

        self.agent_service = AgentService(config)
        self.retrieval_service = RetrievalService(config)
        self.graph_service = GraphService(config, self.retrieval_service, self.repository_service)
        
        self.comparator = ReviewComparatorService(repository_service=self.repository_service, cache_dir=get_openreview_dir())

    def test_agent_with_retrieval(self, name, model, temperature, message: str, paper_path: str, top_k: int | None = None):
        """Run an agent using RAG context retrieved from a paper — agent drives its own retrieval."""
        
        agent = self.agent_service.init_agent(name, model, temperature, self.retrieval_service, top_k=top_k)
        return agent.run(message, paper_path=paper_path)

    def compile_graph(self, graph_config: GraphAgentConfig | None = None) -> None:
        """Compile the graph of agents based on the provided configuration."""
        
        graph_config = graph_config or GraphAgentConfig.default_config()
        agents = self.agent_service.init_agents_from_graph_config(graph_config, self.retrieval_service, self.repository_service)
        self.graph_service.compile(agents, graph_config)

    def invoke_graph(self, paper_path: str, run_description: str, force_reindex: bool = False) -> tuple[dict, dict]:
        """Invoke the compiled graph of agents on a specific paper, returning the results and any retrieval metadata."""
        
        return self.graph_service.invoke(paper_path, run_description, force_reindex)


def inject_container(request: Request) -> Container:
    return request.app.state.container
