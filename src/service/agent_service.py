import logging

from threading import RLock
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama

from config import Config
from client.mock_chat import MockChatModel
from retrieval.bm25_context_provider import BM25ContextProvider
from models.agent import AgentName, LlmModelName
from agent.base import BaseAgent
from agent.impl.contribution_reviewer import ContributionReviewerAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.presentation_reviewer import PresentationReviewerAgent
from agent.impl.refinement import RefinementAgent
from agent.impl.soundness_reviewer import SoundnessReviewerAgent

logger = logging.getLogger(__name__)

_REGISTRY: dict[AgentName, type[BaseAgent]] = {
    AgentName.SOUNDNESS_REVIEWER: SoundnessReviewerAgent,
    AgentName.PRESENTATION_REVIEWER: PresentationReviewerAgent,
    AgentName.CONTRIBUTION_REVIEWER: ContributionReviewerAgent,
    AgentName.META_REVIEWER: MetaReviewerAgent,
    AgentName.REFINEMENT_AGENT: RefinementAgent,
}


class AgentService:

    def __init__(self, config: Config):
        self.config = config
        self._cache_lock = RLock()
        self._client_cache: dict[tuple[LlmModelName, float], BaseChatModel] = {}
        self._agent_cache: dict[tuple[AgentName, LlmModelName, float], BaseAgent] = {}

    def init_client(self, model: LlmModelName, temperature: float) -> BaseChatModel:
        key = (model, self._normalize_temperature(temperature))
        if key in self._client_cache:
            return self._client_cache[key]
        with self._cache_lock:
            if key in self._client_cache:
                return self._client_cache[key]
            client = self._create_client(model, key[1], self.config)
            self._client_cache[key] = client
            return client

    def init_agent(self, name: AgentName, model: LlmModelName, temperature: float, retrieval_service=None, top_k: int | None = None) -> BaseAgent:
        key = (name, model, self._normalize_temperature(temperature))
        if key in self._agent_cache:
            return self._agent_cache[key]
        with self._cache_lock:
            if key in self._agent_cache:
                return self._agent_cache[key]
            
            agent_class = self.get_agent_class(name)
            agent = agent_class(
                llm=self.init_client(model, key[2]), 
                context_provider=self._build_context_provider(agent_class, retrieval_service)
            )
              
            self._agent_cache[key] = agent
            return agent

    def invoke_client(self, model: LlmModelName, temperature: float, message: str) -> str:
        client = self.init_client(model, temperature)
        return client.invoke(message).content

    def run_agent(self, name: AgentName, model: LlmModelName, temperature: float, message: str) -> str:
        agent = self.init_agent(name, model, temperature)
        return agent.run(message)

    @staticmethod
    def get_agent_class(name: AgentName) -> type[BaseAgent]:
        agent_class = _REGISTRY.get(name)
        if agent_class is None:
            raise ValueError(f"Unsupported agent name: {name}")
        return agent_class

    @staticmethod
    def _normalize_temperature(temperature: float) -> float:
        return round(float(temperature), 3)

    @staticmethod
    def _create_client(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
        if model.is_mock():
            return MockChatModel()

        if model.is_ollama():
            return ChatOllama(
                model=model,
                base_url=config.ollama_url,
                temperature=temperature,
                num_predict=config.ollama_num_predict,
                keep_alive=config.ollama_keep_alive,
            )

        if model.is_openai():
            from langchain_openai import ChatOpenAI
            if not config.openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured.")
            return ChatOpenAI(
                model=model,
                api_key=config.openai_api_key,
                temperature=temperature,
            )

        if model.is_anthropic():
            from langchain_anthropic import ChatAnthropic
            if not config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured.")
            return ChatAnthropic(
                model=model,
                api_key=config.anthropic_api_key,
                temperature=temperature,
            )

        raise ValueError(f"Unsupported LLM model: {model}")

    def _build_context_provider(self, agent_class: type[BaseAgent], retrieval_service) -> BM25ContextProvider | None:
        if agent_class.RAG_QUERY and retrieval_service:
            return BM25ContextProvider(
                retrieval_service=retrieval_service,
                query=agent_class.RAG_QUERY,
                sections=agent_class.RAG_SECTIONS,
            )
        return None