from pydantic import BaseModel, Field

from models.agent import AgentName, LlmModelName


class AgentLLMConfig(BaseModel):
    agent_name: AgentName
    model: LlmModelName
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class GraphAgentConfig(BaseModel):
    agents: list[AgentLLMConfig]
    
    @staticmethod
    def default_config() -> "GraphAgentConfig":
        _DEFAULT_MODEL = LlmModelName.OLLAMA_LLAMA32
        _DEFAULT_TEMPERATURE = 0.1
        
        agents: list[AgentLLMConfig] = []
        for name in list(AgentName):
            config = AgentLLMConfig(agent_name=name, model=_DEFAULT_MODEL, temperature=_DEFAULT_TEMPERATURE)    
            agents.append(config)    
        return GraphAgentConfig(agents=agents) 