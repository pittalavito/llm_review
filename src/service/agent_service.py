import logging

from threading import RLock
from langchain_core.language_models.chat_models import BaseChatModel

from config import Config

from domain.agent.base import BaseAgent
from domain.agent.impl.area_chair_agent import AreaChairAgent
from domain.agent.impl.author_agent import AuthorAgent
from domain.agent.impl.meta_reviewer import MetaReviewerAgent
from domain.agent.impl.reviewer_agent import ReviewerAgent

from domain.client.factory import create_client

from models.agent import AgentName, AgentResponse, AreaChairStyle, LlmModelName, ReviewerPersona
from models.graph import GraphAgentConfig

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
                logger.info(f"{_LOGGER_PREFIX} Creating client model={model} temp={temperature}")
                self._client_cache[key] = create_client(self, model, key[1])
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
        prompt_template: str | None = None,
        prompt_version: str | None = None,
    ) -> BaseAgent:
        key = self._agent_cache_key(
            name, model, temperature, reviewer_persona, area_chair_style, prompt_version
        )
        if key in self._agent_cache:
            logger.info(f"{_LOGGER_PREFIX} Agent cache hit name={name} model={model}")
            return self._agent_cache[key]

        with self._cache_lock:
            if key in self._agent_cache:
                return self._agent_cache[key]
            client = self.init_client(model, temperature)
            agent = self._build_agent(name, client, reviewer_persona, area_chair_style, prompt_template)
            agent._context_provider = self._build_context_provider(type(agent), retrieval_service, agent)
            self._agent_cache[key] = agent
            return agent

    def init_agents_from_graph_config(self, agents_config: GraphAgentConfig, retrieval_service=None, prompt_repository=None) -> dict[AgentName, BaseAgent]:
        """ Initialize agents based on a GraphAgentConfig, optionally using a retrieval service and prompt repository."""
        
        return {
            a.agent_name: self.init_agent(
                a.agent_name, a.model, a.temperature, retrieval_service,
                reviewer_persona=a.reviewer_persona,
                area_chair_style=a.area_chair_style,
                prompt_template=self._resolve_prompt_template(prompt_repository, a),
                prompt_version=a.prompt_version,
            )
            for a in agents_config.agents
        }

    def invoke_client(self, model: LlmModelName, temperature: float, message: str) -> str:
        return self.init_client(model, temperature).invoke(message).content

    def run_agent(self, name: AgentName, model: LlmModelName, temperature: float, message: str) -> AgentResponse:
        return self.init_agent(name, model, temperature).run(message)

    def build_prompt_preview(self, name: AgentName, message: str, system_prompt_override: str | None = None) -> dict:
        """Build prompt preview for a given agent — no LLM instantiation needed."""
        
        return self.get_agent_class(name).build_preview(message, system_prompt_override=system_prompt_override)

    def get_agent_class(self, name: AgentName) -> type[BaseAgent]:
        try:
            return _AGENT_CLASSES[name]
        except KeyError as exc:
            raise ValueError(f"Unsupported agent name: {name}") from exc

    def _resolve_prompt_template(self, prompt_repository, agent_config) -> str | None:
        """Base template from the DB registry; None (code default) when no
        repository is wired. Unknown/inactive label -> ValueError."""
        
        if prompt_repository is None:
            return None
        role = agent_config.agent_name.role()
        return prompt_repository.get_by_role_label(role, agent_config.prompt_version).template

    def _normalize_temperature(self, temperature: float) -> float:
        return round(float(temperature), 3)

    def _agent_cache_key(self, name, model, temperature, persona, style, prompt_version=None) -> tuple:
        persona_key = (
            (persona.commitment, persona.intention, persona.knowledgeability, persona.focus)
            if persona else None
        )
        return (name, model, self._normalize_temperature(temperature), persona_key, style, prompt_version)

    def _build_agent(
        self,
        name: AgentName,
        client: BaseChatModel,
        persona: ReviewerPersona | None,
        style: AreaChairStyle | None,
        prompt_template: str | None = None,
    ) -> BaseAgent:
        """Instantiate an agent based on its name, client, and optional persona/style."""
        
        agent_class = self.get_agent_class(name)
        
        if name in _REVIEWER_NAMES:
            return agent_class(client=client, agent_name=name, persona=persona, base_template=prompt_template)
        if name == AgentName.AREA_CHAIR and style is not None:
            return agent_class(client=client, style=style, base_template=prompt_template)
        
        return agent_class(client=client, base_template=prompt_template)

    def _build_context_provider(
        self,
        agent_class: type[BaseAgent],
        retrieval_service,
        agent_instance: BaseAgent | None = None,
    ) -> RetrievalContextProvider | None:
        """Build a RetrievalContextProvider for the given agent class and instance, if applicable."""
        
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
