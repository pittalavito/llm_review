from fastapi import Request
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
        version = self._config.app_version
        return {"status": "ok", "version": version}
    
    
    def test_llm(self, model, temperature, message) -> str:
        agent_service: AgentService = self._agent_service
        return agent_service.invoke_client(model, temperature, message)
    
    
    def test_agent(self, name, model, temperature, message) -> str:
        agent_service: AgentService = self._agent_service
        return agent_service.run_agent(name, model, temperature, message)
    
    
    def compile_graph(self, graph_llm_config: GraphAgentConfig):        
        agent_service: AgentService = self._agent_service
        graph_service: GraphService = self._graph_service

        if graph_llm_config is None:
            graph_llm_config = graph_service.default_config()            
            
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
