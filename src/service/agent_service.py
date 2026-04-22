import logging

from config import Config

from threading import RLock
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from client.mock_chat import MockChatModel
from graph.config import GraphAgentConfig
from service.retrieval_context_provider import RetrievalContextProvider
from models.agent import AgentName, AgentResponse, LlmModelName
from agent.base import BaseAgent
from agent.impl.contribution_reviewer import ContributionReviewerAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.presentation_reviewer import PresentationReviewerAgent
from agent.impl.author_agent import AuthorAgent
from agent.impl.soundness_reviewer import SoundnessReviewerAgent


logger = logging.getLogger(__name__)

_LOGGER_PREFIX = "[AgentService]"

_REGISTRY: dict[AgentName, type[BaseAgent]] = {
    AgentName.SOUNDNESS_REVIEWER: SoundnessReviewerAgent,
    AgentName.PRESENTATION_REVIEWER: PresentationReviewerAgent,
    AgentName.CONTRIBUTION_REVIEWER: ContributionReviewerAgent,
    AgentName.META_REVIEWER: MetaReviewerAgent,
    AgentName.AUTHOR_AGENT: AuthorAgent,
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
            logger.info(f"{_LOGGER_PREFIX} Client cache hit for model={model}, temperature={temperature}")
            return self._client_cache[key]
        with self._cache_lock:
            if key in self._client_cache:
                logger.info(f"{_LOGGER_PREFIX} Client cache hit for model={model}, temperature={temperature}")
                return self._client_cache[key]
            client = self._create_client(model, key[1], self.config)
            self._client_cache[key] = client
            return client


    def init_agent(self, name: AgentName, model: LlmModelName, temperature: float, retrieval_service=None, top_k: int | None = None) -> BaseAgent:
        key = (name, model, self._normalize_temperature(temperature))
        if key in self._agent_cache:
            logger.info(f"{_LOGGER_PREFIX} Agent cache hit for name={name}, model={model}, temperature={temperature}")
            return self._agent_cache[key]
        with self._cache_lock:
            if key in self._agent_cache:
                logger.info(f"{_LOGGER_PREFIX} Agent cache hit for name={name}, model={model}, temperature={temperature}")
                return self._agent_cache[key]
            client = self.init_client(model, temperature)
            context_provider = self._build_context_provider(self.get_agent_class(name), retrieval_service)  
            agent_class = self.get_agent_class(name)
            agent = agent_class(client=client, context_provider=context_provider)
            self._agent_cache[key] = agent
            return agent


    def init_agents_from_graph_config(self, agents_config: GraphAgentConfig, retrieval_service=None) -> dict[AgentName, BaseAgent]:
        agents = {}
        for a in agents_config.agents:
            agent = self.init_agent(a.agent_name, a.model, a.temperature, retrieval_service)
            agents[a.agent_name] = agent
        return agents    


    def invoke_client(self, model: LlmModelName, temperature: float, message: str) -> str:
        client = self.init_client(model, temperature)
        return client.invoke(message).content


    def run_agent(self, name: AgentName, model: LlmModelName, temperature: float, message: str) -> AgentResponse:
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
            logger.info(f"{_LOGGER_PREFIX} Initializing Ollama client with model={model}, temperature={temperature}")
            return ChatOllama(
                model=model,
                base_url=config.ollama_url,
                temperature=temperature,
                num_predict=config.ollama_num_predict,
                keep_alive=config.ollama_keep_alive,
            )

        if model.is_openai():
            if not config.openai_api_key:
                raise ValueError("OPENAI_API_KEY not configured.")
            logger.info(f"{_LOGGER_PREFIX} Initializing OpenAI client with model={model}, temperature={temperature}")
            return ChatOpenAI(
                model=model,
                api_key=config.openai_api_key,
                temperature=temperature,
            )

        if model.is_anthropic():
            if not config.anthropic_api_key:
                raise ValueError("ANTHROPIC_API_KEY not configured.")
            logger.info(f"{_LOGGER_PREFIX} Initializing Anthropic client with model={model}, temperature={temperature}")
            return ChatAnthropic(
                model=model,
                api_key=config.anthropic_api_key,
                temperature=temperature,
            )

        raise ValueError(f"Unsupported LLM model: {model}")


    def _build_context_provider(self, agent_class: type[BaseAgent], retrieval_service) -> RetrievalContextProvider | None:
        if agent_class.RAG_QUERY and retrieval_service:
            logger.info(f"{_LOGGER_PREFIX} Building RetrievalContextProvider for agent_class={agent_class.__name__}")
            return RetrievalContextProvider(
                retrieval_service=retrieval_service,
                query=agent_class.RAG_QUERY,
                sections=agent_class.RAG_SECTIONS,
            )
        logger.info(f"{_LOGGER_PREFIX} No context provider needed for agent_class={agent_class.__name__}")
        return None