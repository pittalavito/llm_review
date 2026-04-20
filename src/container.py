from fastapi import Request
from agent.base import BaseAgent
from agent.builder import PromptBuilder
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
        """Build the full prompt for a given agent name and user message."""
        agent_class: BaseAgent = AgentService.get_agent_class(name)
        
        system_prompt = agent_class.SYSTEM_PROMPT
        schema = agent_class.RESPONSE_SCHEMA
        message_label = agent_class.MESSAGE_LABEL
        return PromptBuilder.build_prompt(system_prompt, schema, message, message_label)    
    
    
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
        """Run an agent using RAG context retrieved from a paper as additional input."""
        retrieval_service: RetrievalService = self._retrieval_service
        agent_service: AgentService = self._agent_service

        retrieval = retrieval_service.retrieve_context(paper_path, top_k=top_k)
        context: str = retrieval["context"]
        augmented_message = f"{context}\n\n---\n\n{message}"
        return agent_service.run_agent(name, model, temperature, augmented_message)


    def compile_graph(self, graph_llm_config: GraphAgentConfig):        
        agent_service: AgentService = self._agent_service
        graph_service: GraphService = self._graph_service

        if graph_llm_config is None:
            graph_llm_config = GraphAgentConfig.default_config()           
            
        agents = {}
        for conf in graph_llm_config.agents:
            angent = agent_service.init_agent(conf.agent_name, conf.model, conf.temperature)
            agents[conf.agent_name] = angent
        
        graph_service.compile(graph_llm_config, agents) 
    
    
    def invoke_graph(self, input_data):
        graph_service: GraphService = self._graph_service
        return graph_service.invoke(input_data)  


def inject_container(request: Request) -> Container:
    return request.app.state.container
