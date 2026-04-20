
import logging

from threading import RLock
from config import Config
from llm_client.base_client import BaseLLMClient
from llm_client.mock_client import MockLLMClient
from llm_client.ollama_client import OllamaLLMClient
from models.agent import AgentName, LlmModelName
from agent.base import BaseAgent
from agent.impl.contribution_reviewer import ContributionReviewerAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.presentation_reviewer import PresentationReviewerAgent
from agent.impl.refinement import RefinementAgent
from agent.impl.soundness_reviewer import SoundnessReviewerAgent


logger = logging.getLogger(__name__)


class AgentService:

    def __init__(self, config: Config):
        self.config = config
        self._cache_lock = RLock()
        self._client_cache: dict[tuple[LlmModelName, float], object] = {}
        self._agent_cache: dict[tuple[AgentName, LlmModelName, float], BaseAgent] = {}
            
 
    def init_client(self, model: LlmModelName, temperature: float):
        normalized_temp = self._normalize_temperature(temperature)
        key = (model, normalized_temp)
        cached = self._client_cache.get(key)
        
        if cached is not None:
            return cached

        with self._cache_lock:
            normalized_temp = self._normalize_temperature(temperature)
            key = (model, normalized_temp)
            cached = self._client_cache.get(key)
            
            if cached is not None:
                return cached
            
            config = self.config
            client = self._create_client(model, normalized_temp, config)
            self._client_cache[key] = client
            return client

    
    def init_agent(self, name: AgentName, model: LlmModelName, temperature: float) -> BaseAgent:
        normalized_temp = self._normalize_temperature(temperature)
        key = (name, model, normalized_temp)
        cached = self._agent_cache.get(key)
        
        if cached is not None:
            return cached

        with self._cache_lock:
            normalized_temp = self._normalize_temperature(temperature)
            key = (name, model, normalized_temp)
            cached = self._agent_cache.get(key)
            
            if cached is not None:
                return cached
            
            client = self.init_client(model, normalized_temp)
            agent = self._create_agent(name, client)
            self._agent_cache[key] = agent
            return agent

    
    def invoke_client(self, model: LlmModelName, temperature: float, message: str) -> str:
        client = self.init_client(model, temperature)
        return client.invoke(message)

    
    def run_agent(self, name: AgentName, model: LlmModelName, temperature: float, message: str) -> str:
        agent = self.init_agent(name, model, temperature)
        return agent.run(message)

    
    @staticmethod
    def _normalize_temperature(temperature: float) -> float:
        return round(float(temperature), 3)
    
    
    @staticmethod
    def _create_client(model: LlmModelName, temperature: float, config: Config) -> BaseLLMClient:
        if model.is_mock():
            return MockLLMClient()
        elif model.is_ollama():
            return OllamaLLMClient(
                model=model,
                base_url=config.ollama_url,
                temperature=temperature,
                num_predict=config.ollama_num_predict,
                keep_alive=config.ollama_keep_alive,
            )
        else:
            raise ValueError(f"Unsupported LLM model: {model}")
    
    
    @staticmethod
    def _create_agent(name: AgentName, client: BaseLLMClient) -> BaseAgent:
        _REGISTRY: dict[AgentName, type[BaseAgent]] = {
            AgentName.SOUNDNESS_REVIEWER: SoundnessReviewerAgent,
            AgentName.PRESENTATION_REVIEWER: PresentationReviewerAgent,
            AgentName.CONTRIBUTION_REVIEWER: ContributionReviewerAgent,
            AgentName.META_REVIEWER: MetaReviewerAgent,
            AgentName.REFINEMENT_AGENT: RefinementAgent,
        }
        
        agent_class = _REGISTRY.get(name)
        if agent_class is None:
            raise ValueError(f"Unsupported agent name: {name}")
        return agent_class(llm=client)
    