import logging

from threading import RLock

from langchain_core.language_models.chat_models import BaseChatModel

from agent.base import BaseAgent
from agent.impl.area_chair_agent import AreaChairAgent
from agent.impl.author_agent import AuthorAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.reviewer_agent import ReviewerAgent
from client.factory import CLIENT_FACTORIES
from config import Config
from graph.config import GraphAgentConfig
from models.agent import AgentName, AgentResponse, AreaChairStyle, LlmModelName, ReviewerPersona
from service.retrieval_context_provider import RetrievalContextProvider


logger = logging.getLogger(__name__)

_LOGGER_PREFIX = "[AgentService]"

_REVIEWER_NAMES = {AgentName.REVIEWER_1, AgentName.REVIEWER_2, AgentName.REVIEWER_3}

_AGENT_CLASSES: dict[AgentName, type[BaseAgent]] = {
    AgentName.REVIEWER_1: ReviewerAgent,
    AgentName.REVIEWER_2: ReviewerAgent,
    AgentName.REVIEWER_3: ReviewerAgent,
    AgentName.META_REVIEWER: MetaReviewerAgent,
    AgentName.AREA_CHAIR: AreaChairAgent,
    AgentName.AUTHOR_AGENT:  AuthorAgent,
}

class AgentService:

    def __init__(self, config: Config):
        self.config = config
        self._cache_lock = RLock()
        self._client_cache: dict[tuple[LlmModelName, float], BaseChatModel] = {}
        self._agent_cache: dict[tuple, BaseAgent] = {}

    def init_client(self, model: LlmModelName, temperature: float) -> BaseChatModel:
        key = (model, self._normalize_temperature(temperature))
        if key in self._client_cache:
            logger.info(f"{_LOGGER_PREFIX} Client cache hit model={model} temp={key[1]}")
            return self._client_cache[key]
        with self._cache_lock:
            if key not in self._client_cache:
                self._client_cache[key] = self._create_client(model, key[1])
            return self._client_cache[key]

    def init_agent(
        self,
        name: AgentName,
        model: LlmModelName,
        temperature: float,
        retrieval_service=None,
        top_k: int | None = None,
        reviewer_persona: ReviewerPersona | None = None,
        area_chair_style: AreaChairStyle | None = None,
    ) -> BaseAgent:
        key = self._agent_cache_key(name, model, temperature, reviewer_persona, area_chair_style)
        if key in self._agent_cache:
            logger.info(f"{_LOGGER_PREFIX} Agent cache hit name={name} model={model}")
            return self._agent_cache[key]

        with self._cache_lock:
            if key in self._agent_cache:
                return self._agent_cache[key]
            client = self.init_client(model, temperature)
            agent = self._build_agent(name, client, reviewer_persona, area_chair_style)
            agent._context_provider = self._build_context_provider(type(agent), retrieval_service, agent)
            self._agent_cache[key] = agent
            return agent

    def init_agents_from_graph_config(self, agents_config: GraphAgentConfig, retrieval_service=None) -> dict[AgentName, BaseAgent]:
        return {
            a.agent_name: self.init_agent(
                a.agent_name, a.model, a.temperature, retrieval_service,
                reviewer_persona=a.reviewer_persona,
                area_chair_style=a.area_chair_style,
            )
            for a in agents_config.agents
        }

    def invoke_client(self, model: LlmModelName, temperature: float, message: str) -> str:
        return self.init_client(model, temperature).invoke(message).content

    def run_agent(self, name: AgentName, model: LlmModelName, temperature: float, message: str) -> AgentResponse:
        return self.init_agent(name, model, temperature).run(message)

    @staticmethod
    def build_prompt_preview(name: AgentName, message: str) -> dict:
        """Build prompt preview for a given agent — no LLM instantiation needed."""
        return AgentService.get_agent_class(name).build_preview(message)

    @staticmethod
    def get_agent_class(name: AgentName) -> type[BaseAgent]:
        try:
            return _AGENT_CLASSES[name]
        except KeyError as exc:
            raise ValueError(f"Unsupported agent name: {name}") from exc

    def _normalize_temperature(self, temperature: float) -> float:
        return round(float(temperature), 3)

    def _agent_cache_key(self, name, model, temperature, persona, style) -> tuple:
        persona_key = (
            (persona.commitment, persona.intention, persona.knowledgeability, persona.focus)
            if persona else None
        )
        return (name, model, self._normalize_temperature(temperature), persona_key, style)

    def _build_agent(self, name: AgentName, client: BaseChatModel, persona: ReviewerPersona | None, style: AreaChairStyle | None) -> BaseAgent:
        agent_class = self.get_agent_class(name)
        if name in _REVIEWER_NAMES:
            return agent_class(client=client, agent_name=name, persona=persona)
        if name == AgentName.AREA_CHAIR and style is not None:
            return agent_class(client=client, style=style)
        return agent_class(client=client)

    def _create_client(self, model: LlmModelName, temperature: float) -> BaseChatModel:
        for predicate, factory in CLIENT_FACTORIES:
            if predicate(model):
                logger.info(f"{_LOGGER_PREFIX} Building {factory.__name__} model={model} temp={temperature}")
                return factory(model, temperature, self.config)
        raise ValueError(f"Unsupported LLM model: {model}")

    def _build_context_provider(
        self,
        agent_class: type[BaseAgent],
        retrieval_service,
        agent_instance: BaseAgent | None = None,
    ) -> RetrievalContextProvider | None:
        if agent_class.RAG_QUERY == "" or retrieval_service is None:
            return None

        focus_terms = getattr(agent_instance, "rag_focus_terms", "") if agent_instance else ""
        focus_sections = getattr(agent_instance, "rag_focus_sections", []) if agent_instance else []
        sections = focus_sections or agent_class.RAG_SECTIONS

        return RetrievalContextProvider(
            retrieval_service=retrieval_service,
            query=agent_class.RAG_QUERY,
            sections=sections,
            query_suffix=focus_terms
        )
