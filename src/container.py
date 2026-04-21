from fastapi import Request
from agent.base import BaseAgent
from config import Config
from graph.config import GraphAgentConfig
from service.graph_service import GraphService
from service.agent_service import AgentService
from service.retrieval_service import RetrievalService


class Container:
    """DI container for configuration and service registry."""

    def __init__(self, config: Config):
        self._config = config
        self._agent_service = AgentService(config)
        self._retrieval_service = RetrievalService(config)
        self._graph_service = GraphService(config, self._retrieval_service)
    
    
    def health_check(self) -> dict:
        """Simple health check endpoint returning app version."""
        version: str = self._config.app_version
        return {"status": "ok", "version": version}
    
    
    def test_llm(self, model, temperature, message) -> str:
        """Test LLM response for given model, temperature and message."""
        agent_service: AgentService = self._agent_service
        return agent_service.invoke_client(model, temperature, message)
    
    # il FE non lo mostra bene 
    def build_agent_prompt(self, name, message) -> str:
        """Build the full prompt for a given agent name and user message (UI preview only)."""
        agent_class = AgentService.get_agent_class(name)
        agent_instance = agent_class.__new__(agent_class)
        return agent_instance.get_prompt_preview(message)    
    
    
    def test_agent(self, name, model, temperature, message) -> str:
        """Test agent response for given agent name, model, temperature and message."""
        agent_service: AgentService = self._agent_service
        return agent_service.run_agent(name, model, temperature, message)
    
    
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


    def test_agent_with_retrieval(self, name, model, temperature, message: str, paper_path: str, top_k: int | None = None) -> str:
        """Run an agent using RAG context retrieved from a paper — agent drives its own retrieval."""
        agent_service: AgentService = self._agent_service
        agent = agent_service.init_agent(
            name, model, temperature,
            retrieval_service=self._retrieval_service,
            top_k=top_k,
        )
        return agent.run(message, paper_path=paper_path)


    def compile_graph(self, graph_llm_config: GraphAgentConfig):        
        agent_service: AgentService = self._agent_service
        graph_service: GraphService = self._graph_service

        if graph_llm_config is None:
            graph_llm_config = GraphAgentConfig.default_config()           
            
        agents = {}
        for conf in graph_llm_config.agents:
            agent = agent_service.init_agent(
                conf.agent_name, conf.model, conf.temperature,
                retrieval_service=self._retrieval_service,
            )
            agents[conf.agent_name] = agent
        
        graph_service.compile(graph_llm_config, agents) 
    
    
    def invoke_graph(self, input_data):
        graph_service: GraphService = self._graph_service
        return graph_service.invoke(input_data)  


def inject_container(request: Request) -> Container:
    return request.app.state.container
