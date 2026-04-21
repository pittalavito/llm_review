"""
Integration tests for the FastAPI layer:
  - Config defaults
  - Container wiring (health_check, agent service, graph compile)
  - HTTP endpoints via TestClient (all /dev/* routes)

All tests use model=mock so no real LLM / file I/O is needed,
except for the paper-related endpoints which require a real PDF to exist.
"""
import sys
import json
import pytest

sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from config import Config
from container import Container
from models.agent import AgentName, LlmModelName


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def config():
    return Config()


@pytest.fixture(scope="module")
def container(config):
    c = Container(config)
    c.compile_graph()
    return c


@pytest.fixture(scope="module")
def client(config, container):
    """FastAPI TestClient with a pre-built container injected into app state."""
    from main import app
    app.state.container = container
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

class TestConfig:

    def test_default_app_name(self, config):
        assert config.app_name == "llm-review"

    def test_default_rag_chunk_size(self, config):
        assert config.rag_chunk_size > 0

    def test_default_rag_chunk_overlap_less_than_chunk_size(self, config):
        assert config.rag_chunk_overlap < config.rag_chunk_size

    def test_default_top_k(self, config):
        assert config.rag_top_k_default > 0

    def test_ollama_url_set(self, config):
        assert config.ollama_url.startswith("http")

    def test_strategy_version_set(self, config):
        assert config.rag_strategy_version != ""


# ---------------------------------------------------------------------------
# Container
# ---------------------------------------------------------------------------

class TestContainer:

    def test_health_check_returns_ok(self, container):
        result = container.health_check()
        assert result["status"] == "ok"

    def test_health_check_returns_version(self, container):
        result = container.health_check()
        assert "version" in result

    def test_list_papers_returns_list(self, container):
        result = container.list_papers_path()
        assert isinstance(result, list)

    def test_list_indexed_papers_returns_list(self, container):
        result = container.list_indexed_papers()
        assert isinstance(result, list)

    def test_build_agent_prompt_returns_dict(self, container):
        result = container.build_agent_prompt(AgentName.SOUNDNESS_REVIEWER, "test message")
        assert "system_prompt" in result
        assert "full_prompt" in result

    def test_test_agent_with_mock_returns_response(self, container):
        result = container.test_agent(
            AgentName.SOUNDNESS_REVIEWER, LlmModelName.MOCK, 0.0, "review this paper"
        )
        assert result is not None

    def test_compile_graph_does_not_raise(self, container):
        container.compile_graph()  # should be idempotent


# ---------------------------------------------------------------------------
# AgentService — client factory
# ---------------------------------------------------------------------------

class TestAgentServiceClientFactory:

    def test_mock_client_created(self, config):
        from service.agent_service import AgentService
        from client.mock_chat import MockChatModel
        svc = AgentService(config)
        client = svc.init_client(LlmModelName.MOCK, 0.0)
        assert isinstance(client, MockChatModel)

    def test_client_cached_on_second_call(self, config):
        from service.agent_service import AgentService
        svc = AgentService(config)
        c1 = svc.init_client(LlmModelName.MOCK, 0.0)
        c2 = svc.init_client(LlmModelName.MOCK, 0.0)
        assert c1 is c2

    def test_openai_raises_without_key(self, config):
        from service.agent_service import AgentService
        svc = AgentService(config)
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            svc.init_client(LlmModelName.OPENAI_GPT4O, 0.0)

    def test_anthropic_raises_without_key(self, config):
        from service.agent_service import AgentService
        svc = AgentService(config)
        with pytest.raises(ValueError, match="ANTHROPIC"):
            svc.init_client(LlmModelName.ANTHROPIC_CLAUDE_SONNET, 0.0)

    def test_get_agent_class_soundness(self):
        from service.agent_service import AgentService
        from agent.impl.soundness_reviewer import SoundnessReviewerAgent
        cls = AgentService.get_agent_class(AgentName.SOUNDNESS_REVIEWER)
        assert cls is SoundnessReviewerAgent

    def test_get_agent_class_unknown_raises(self):
        from service.agent_service import AgentService
        with pytest.raises(ValueError):
            AgentService.get_agent_class("nonexistent_agent")

    def test_run_agent_returns_agent_response(self, config):
        from service.agent_service import AgentService
        from models.agent import AgentResponse
        svc = AgentService(config)
        result = svc.run_agent(AgentName.SOUNDNESS_REVIEWER, LlmModelName.MOCK, 0.0, "analyse this")
        assert isinstance(result, AgentResponse)


# ---------------------------------------------------------------------------
# HTTP endpoints — /dev/*
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        r = client.get("/dev/health")
        assert r.status_code == 200

    def test_health_body_has_status(self, client):
        r = client.get("/dev/health")
        assert r.json()["status"] == "ok"


class TestModelsEndpoint:

    def test_models_returns_200(self, client):
        r = client.get("/dev/models")
        assert r.status_code == 200

    def test_models_contains_mock(self, client):
        r = client.get("/dev/models")
        assert LlmModelName.MOCK in r.json()


class TestAgentsEndpoint:

    def test_list_agents_returns_200(self, client):
        r = client.get("/dev/agents")
        assert r.status_code == 200

    def test_list_agents_contains_all(self, client):
        r = client.get("/dev/agents")
        names = r.json()
        for name in AgentName:
            assert name in names

    def test_test_agent_with_mock(self, client):
        r = client.post("/dev/agents", json={
            "name": AgentName.SOUNDNESS_REVIEWER,
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "review this paper",
        })
        assert r.status_code == 200

    def test_test_agent_invalid_name_returns_400_or_422(self, client):
        r = client.post("/dev/agents", json={
            "name": "nonexistent",
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "test",
        })
        assert r.status_code in {400, 422}

    def test_prompt_preview_returns_200(self, client):
        r = client.post("/dev/agents/prompt-preview", json={
            "name": AgentName.SOUNDNESS_REVIEWER,
            "message": "review this paper",
        })
        assert r.status_code == 200

    def test_prompt_preview_has_full_prompt(self, client):
        r = client.post("/dev/agents/prompt-preview", json={
            "name": AgentName.SOUNDNESS_REVIEWER,
            "message": "review this paper",
        })
        assert "full_prompt" in r.json()


class TestPapersEndpoint:

    def test_list_papers_returns_200(self, client):
        r = client.get("/dev/papers")
        assert r.status_code == 200

    def test_list_papers_returns_list(self, client):
        r = client.get("/dev/papers")
        assert isinstance(r.json(), list)

    def test_list_indexed_returns_200(self, client):
        r = client.get("/dev/papers/indexed")
        assert r.status_code == 200

    def test_index_paper_invalid_path_returns_400(self, client):
        r = client.post("/dev/papers/index", json={
            "paper_path": "nonexistent/paper.pdf",
            "force_reindex": False,
        })
        assert r.status_code == 400

    def test_get_indexed_detail_not_indexed_returns_404(self, client):
        r = client.get("/dev/papers/indexed/detail", params={"paper_path": "nonexistent.pdf"})
        assert r.status_code == 404


class TestGraphEndpoints:

    def test_compile_graph_returns_200(self, client):
        r = client.post("/dev/graph/compile", json=None)
        assert r.status_code == 200

    def test_compile_graph_status_compiled(self, client):
        r = client.post("/dev/graph/compile", json=None)
        assert r.json()["status"] == "compiled"

    def test_run_graph_invalid_paper_returns_400(self, client):
        r = client.post("/dev/graph/run", json={
            "paper_path": "nonexistent/paper.pdf",
            "rag_top_k": None,
            "force_reindex": False,
        })
        assert r.status_code in {400, 409, 500}
