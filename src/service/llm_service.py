
from agent.base_agent import BaseAgent
from agent.methodology_review import MethodologyReviewerAgent
from agent.test_tool_agent import TestToolAgent
from clients.llm.base_llm_client import BaseLLMClient
from clients.llm.mock_llm_client import MockLLMClient
from clients.llm.ollama_llm_client import OllamaLLMClient
from settings import Settings
from schemas.enums import AgentName, LlmModelName


class LlmService:

    def __init__(self, settings: Settings):
        """Initialize the LLM service with the given settings."""
        self.settings = settings

    def list_models(self) -> list[LlmModelName]:
        """List all available LLM models."""
        return list(LlmModelName)
    
    def list_agents(self) -> list[AgentName]:
        """List all available agents."""
        return list(AgentName)

    def init_client(self, model: LlmModelName, temperature: float) -> BaseLLMClient:
        """Initialize an LLM client based on the model and temperature."""
        if model.is_mock():
            return MockLLMClient()
        elif model.is_ollama():
            base_url = self.settings.ollama_url
            return OllamaLLMClient(model=model, base_url=base_url, temperature=temperature)
        else:
            raise ValueError(f"Unsupported LLM model: {model}")

    def init_agent(self, name: AgentName, model: LlmModelName, temperature: float) -> BaseAgent:
        """Initialize an agent based on the name, model, and temperature."""
        client = self.init_client(model, temperature)
        if name == AgentName.METHODOLOGY_REVIEWER:
            return MethodologyReviewerAgent(llm=client)
        if name == AgentName.TEST_TOOL_AGENT:
            return TestToolAgent(llm=client)
        raise ValueError(f"Unsupported agent name: {name}")


    def test_client(self, model: LlmModelName, temperature: float, message: str) -> str:
        """Test an LLM client by invoking it with a message."""
        client = self.init_client(model, temperature)
        return client.invoke(message)
    
    
    def test_agent(self, name: AgentName, model: LlmModelName, temperature: float, message: str) -> str:
        """Test an agent by initializing it and invoking it with a message."""
        agent = self.init_agent(name, model, temperature)
        return agent.run(message)
    