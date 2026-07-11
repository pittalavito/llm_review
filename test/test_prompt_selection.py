"""
Prompt-version selection at compile time:
  - default config (v1) -> agents get the seeded V1 base
  - reviewer prompt_version=v2 -> SYSTEM_PROMPT built on the V2 template
  - unknown or inactive label -> ValueError
  - cache: same agent with different prompt_version -> distinct instances
"""
import pytest

from domain.agent.prompting.reviewer import _BASE_SYSTEM_PROMPT_V2
from domain.agent.prompting.catalog import DEFAULT_PROMPT_SEEDS
from config import Config

from domain.db.engine import create_db_engine
from domain.db.prompt_repository import PromptRepository

from models.agent import AgentName
from models.graph import GraphAgentConfig

from service.agent_service import AgentService


@pytest.fixture()
def prompt_repo(tmp_path):
    config = Config(database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    engine = create_db_engine(config)
    repo = PromptRepository(engine)
    repo.seed_defaults(DEFAULT_PROMPT_SEEDS)
    return repo


@pytest.fixture()
def service():
    return AgentService(Config())


def _config_with_reviewer_version(label: str) -> GraphAgentConfig:
    config = GraphAgentConfig.default_config()
    for agent in config.agents:
        if agent.agent_name == AgentName.REVIEWER_1:
            agent.prompt_version = label
    return config


class TestPromptSelection:

    def test_default_config_uses_v1_template(self, service, prompt_repo):
        agents = service.init_agents_from_graph_config(
            GraphAgentConfig.default_config(), prompt_repository=prompt_repo
        )
        v1 = prompt_repo.get_by_role_label("reviewer", "v1").template
        assert agents[AgentName.REVIEWER_1].SYSTEM_PROMPT.startswith(v1)

    def test_reviewer_v2_selection_changes_system_prompt(self, service, prompt_repo):
        agents = service.init_agents_from_graph_config(
            _config_with_reviewer_version("v2"), prompt_repository=prompt_repo
        )
        assert agents[AgentName.REVIEWER_1].SYSTEM_PROMPT.startswith(_BASE_SYSTEM_PROMPT_V2)
        # The other reviewers stay on v1.
        assert not agents[AgentName.REVIEWER_2].SYSTEM_PROMPT.startswith(_BASE_SYSTEM_PROMPT_V2)

    def test_unknown_label_raises(self, service, prompt_repo):
        with pytest.raises(ValueError, match="not available"):
            service.init_agents_from_graph_config(
                _config_with_reviewer_version("v99"), prompt_repository=prompt_repo
            )

    def test_inactive_label_raises(self, service, prompt_repo):
        row = prompt_repo.get_by_role_label("reviewer", "v2")
        prompt_repo.update_meta(row.id, is_active=False)
        with pytest.raises(ValueError, match="not available"):
            service.init_agents_from_graph_config(
                _config_with_reviewer_version("v2"), prompt_repository=prompt_repo
            )

    def test_no_repository_falls_back_to_code_default(self, service):
        agents = service.init_agents_from_graph_config(GraphAgentConfig.default_config())
        assert agents[AgentName.REVIEWER_1].SYSTEM_PROMPT  # code V1, no DB involved

    def test_cache_distinguishes_prompt_versions(self, service, prompt_repo):
        v1_agents = service.init_agents_from_graph_config(
            GraphAgentConfig.default_config(), prompt_repository=prompt_repo
        )
        v2_agents = service.init_agents_from_graph_config(
            _config_with_reviewer_version("v2"), prompt_repository=prompt_repo
        )
        assert v1_agents[AgentName.REVIEWER_1] is not v2_agents[AgentName.REVIEWER_1]
        assert v1_agents[AgentName.REVIEWER_2] is v2_agents[AgentName.REVIEWER_2]
