"""
Controller tests for all /dev/* HTTP endpoints.
Uses FastAPI TestClient with a pre-built container (mock model, no real LLM).
"""
import sys
import pytest

sys.path.insert(0, "src")

from fastapi.testclient import TestClient
from unittest.mock import patch

from config import Config
from container import Container
from models.agent import AgentName, LlmModelName

PAPER_PATH = "2566_Robust_agents_learn_causa.pdf"


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
    from main import app
    app.state.container = container
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        r = client.get("/dev/health")
        assert r.status_code == 200

    def test_health_body_has_status(self, client):
        r = client.get("/dev/health")
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TestModelsEndpoint:

    def test_models_returns_200(self, client):
        r = client.get("/dev/models")
        assert r.status_code == 200

    def test_models_contains_mock(self, client):
        r = client.get("/dev/models")
        assert LlmModelName.MOCK in r.json()


# ---------------------------------------------------------------------------
# Test LLM
# ---------------------------------------------------------------------------

class TestTestLlmEndpoint:

    def test_test_llm_mock_returns_200(self, client):
        r = client.post("/dev/test-llm", json={
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "hello",
        })
        assert r.status_code == 200

    def test_test_llm_returns_string(self, client):
        r = client.post("/dev/test-llm", json={
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "hello",
        })
        assert isinstance(r.json(), str)

    def test_test_llm_error_returns_500(self, client):
        with patch("container.Container.test_llm", side_effect=RuntimeError("boom")):
            r = client.post("/dev/test-llm", json={
                "model": LlmModelName.MOCK,
                "temperature": 0.0,
                "message": "hello",
            })
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class TestAgentsEndpoint:

    def test_list_agents_returns_200(self, client):
        r = client.get("/dev/agents")
        assert r.status_code == 200

    def test_list_agents_contains_all(self, client):
        names = client.get("/dev/agents").json()
        for name in AgentName:
            assert name in names

    def test_test_agent_with_mock_returns_200(self, client):
        r = client.post("/dev/agents", json={
            "name": AgentName.REVIEWER_1,
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "review this paper",
        })
        assert r.status_code == 200

    def test_test_agent_invalid_name_returns_422(self, client):
        r = client.post("/dev/agents", json={
            "name": "nonexistent",
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "test",
        })
        assert r.status_code in {400, 422}

    def test_test_agent_error_returns_500(self, client):
        with patch("container.Container.test_agent", side_effect=RuntimeError("boom")):
            r = client.post("/dev/agents", json={
                "name": AgentName.REVIEWER_1,
                "model": LlmModelName.MOCK,
                "temperature": 0.0,
                "message": "test",
            })
        assert r.status_code == 500

    def test_prompt_preview_returns_200(self, client):
        r = client.post("/dev/agents/prompt-preview", json={
            "name": AgentName.REVIEWER_1,
            "message": "review this paper",
        })
        assert r.status_code == 200

    def test_prompt_preview_has_full_prompt(self, client):
        r = client.post("/dev/agents/prompt-preview", json={
            "name": AgentName.REVIEWER_1,
            "message": "review this paper",
        })
        assert "full_prompt" in r.json()

    def test_prompt_preview_error_returns_500(self, client):
        with patch("container.Container.build_agent_prompt", side_effect=RuntimeError("boom")):
            r = client.post("/dev/agents/prompt-preview", json={
                "name": AgentName.REVIEWER_1,
                "message": "test",
            })
        assert r.status_code == 500

    def test_agent_with_retrieval_returns_200(self, client):
        r = client.post("/dev/agents/retrieval", json={
            "name": AgentName.REVIEWER_1,
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "review this",
            "paper_path": PAPER_PATH,
        })
        assert r.status_code == 200

    def test_agent_with_retrieval_value_error_returns_400(self, client):
        with patch("container.Container.test_agent_with_retrieval", side_effect=ValueError("bad paper")):
            r = client.post("/dev/agents/retrieval", json={
                "name": AgentName.REVIEWER_1,
                "model": LlmModelName.MOCK,
                "temperature": 0.0,
                "message": "review this",
                "paper_path": "nonexistent.pdf",
            })
        assert r.status_code == 400

    def test_agent_with_retrieval_error_returns_500(self, client):
        with patch("container.Container.test_agent_with_retrieval", side_effect=RuntimeError("boom")):
            r = client.post("/dev/agents/retrieval", json={
                "name": AgentName.REVIEWER_1,
                "model": LlmModelName.MOCK,
                "temperature": 0.0,
                "message": "test",
                "paper_path": PAPER_PATH,
            })
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Papers
# ---------------------------------------------------------------------------

class TestPapersEndpoint:

    def test_list_papers_returns_200(self, client):
        assert client.get("/dev/papers").status_code == 200

    def test_list_papers_returns_list(self, client):
        assert isinstance(client.get("/dev/papers").json(), list)

    def test_list_indexed_returns_200(self, client):
        assert client.get("/dev/papers/indexed").status_code == 200

    def test_index_paper_invalid_path_returns_400(self, client):
        r = client.post("/dev/papers/index", json={"paper_path": "nonexistent/paper.pdf"})
        assert r.status_code == 400

    def test_index_paper_error_returns_500(self, client):
        with patch("container.Container.index_paper", side_effect=RuntimeError("boom")):
            r = client.post("/dev/papers/index", json={"paper_path": PAPER_PATH})
        assert r.status_code == 500

    def test_get_indexed_detail_valid_paper_returns_200(self, client):
        client.post("/dev/papers/index", json={"paper_path": PAPER_PATH, "force_reindex": True})
        r = client.get("/dev/papers/indexed/detail", params={"paper_path": PAPER_PATH})
        assert r.status_code == 200
        assert r.json()["paper_path"] == PAPER_PATH

    def test_get_indexed_detail_not_found_returns_404(self, client):
        r = client.get("/dev/papers/indexed/detail", params={"paper_path": "nonexistent.pdf"})
        assert r.status_code == 404

    def test_get_indexed_detail_error_returns_500(self, client):
        with patch("container.Container.get_indexed_paper", side_effect=RuntimeError("boom")):
            r = client.get("/dev/papers/indexed/detail", params={"paper_path": PAPER_PATH})
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class TestGraphEndpoints:

    def test_compile_returns_200(self, client):
        assert client.post("/dev/graph/compile", json=None).status_code == 200

    def test_compile_status_compiled(self, client):
        assert client.post("/dev/graph/compile", json=None).json()["status"] == "compiled"

    def test_compile_error_returns_500(self, client):
        with patch("container.Container.compile_graph", side_effect=RuntimeError("boom")):
            r = client.post("/dev/graph/compile", json=None)
        assert r.status_code == 500

    def test_get_config_returns_200(self, client):
        client.post("/dev/graph/compile", json=None)
        assert client.get("/dev/graph/config").status_code == 200

    def test_get_config_has_agents(self, client):
        assert "agents" in client.get("/dev/graph/config").json()

    def test_run_invalid_paper_returns_error(self, client):
        r = client.post("/dev/graph/run", json={"paper_path": "nonexistent.pdf"})
        assert r.status_code in {400, 409, 500}

    def test_run_not_compiled_returns_409(self, client):
        with patch("container.Container.invoke_graph", side_effect=RuntimeError("Graph not compiled")):
            r = client.post("/dev/graph/run", json={"paper_path": PAPER_PATH})
        assert r.status_code == 409

    def test_run_generic_error_returns_500(self, client):
        with patch("container.Container.invoke_graph", side_effect=Exception("boom")):
            r = client.post("/dev/graph/run", json={"paper_path": PAPER_PATH})
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class TestRunsEndpoints:

    def test_list_runs_returns_200(self, client):
        assert client.get("/dev/runs").status_code == 200

    def test_list_runs_returns_list(self, client):
        assert isinstance(client.get("/dev/runs").json(), list)

    def test_get_run_not_found_returns_404(self, client):
        assert client.get("/dev/runs/nonexistent-run-id").status_code == 404

    def test_get_run_error_returns_500(self, client):
        with patch("container.Container.get_run", side_effect=RuntimeError("boom")):
            r = client.get("/dev/runs/some-run-id")
        assert r.status_code == 500
