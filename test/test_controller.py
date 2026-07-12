"""
Controller tests for all /llm-review/* HTTP endpoints.
Uses FastAPI TestClient with a pre-built container (mock model, no real LLM).
"""
import sys
import pytest

from main import app
from fastapi.testclient import TestClient
from unittest.mock import patch
from config import Config
from container import Container
from models.agent import AgentName, LlmModelName

sys.path.insert(0, "src")

PAPER_PATH = "2580_when_should_agents_explore_.pdf"


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
    app.state.container = container
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        r = client.get("/llm-review/health")
        assert r.status_code == 200

    def test_health_body_has_status(self, client):
        r = client.get("/llm-review/health")
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TestModelsEndpoint:

    def test_models_returns_200(self, client):
        r = client.get("/llm-review/models")
        assert r.status_code == 200

    def test_models_contains_mock(self, client):
        r = client.get("/llm-review/models")
        assert LlmModelName.MOCK in r.json()


# ---------------------------------------------------------------------------
# Test LLM
# ---------------------------------------------------------------------------

class TestTestLlmEndpoint:

    def test_test_llm_mock_returns_200(self, client):
        r = client.post("/llm-review/test-llm", json={
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "hello",
        })
        assert r.status_code == 200

    def test_test_llm_returns_string(self, client):
        r = client.post("/llm-review/test-llm", json={
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "hello",
        })
        assert isinstance(r.json(), str)

    def test_test_llm_error_returns_500(self, client):
        with patch("service.agent_service.AgentService.invoke_client", side_effect=RuntimeError("boom")):
            r = client.post("/llm-review/test-llm", json={
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
        r = client.get("/llm-review/agents")
        assert r.status_code == 200

    def test_list_agents_contains_all(self, client):
        names = client.get("/llm-review/agents").json()
        for name in AgentName:
            assert name in names

    def test_test_agent_with_mock_returns_200(self, client):
        r = client.post("/llm-review/agents", json={
            "name": AgentName.REVIEWER_1,
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "review this paper",
        })
        assert r.status_code == 200

    def test_test_agent_invalid_name_returns_422(self, client):
        r = client.post("/llm-review/agents", json={
            "name": "nonexistent",
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "test",
        })
        assert r.status_code in {400, 422}

    def test_test_agent_error_returns_500(self, client):
        with patch("service.agent_service.AgentService.run_agent", side_effect=RuntimeError("boom")):
            r = client.post("/llm-review/agents", json={
                "name": AgentName.REVIEWER_1,
                "model": LlmModelName.MOCK,
                "temperature": 0.0,
                "message": "test",
            })
        assert r.status_code == 500

    def test_prompt_preview_returns_200(self, client):
        r = client.post("/llm-review/agents/prompt-preview", json={
            "name": AgentName.REVIEWER_1,
            "message": "review this paper",
        })
        assert r.status_code == 200

    def test_prompt_preview_has_full_prompt(self, client):
        r = client.post("/llm-review/agents/prompt-preview", json={
            "name": AgentName.REVIEWER_1,
            "message": "review this paper",
        })
        assert "full_prompt" in r.json()

    def test_prompt_preview_error_returns_500(self, client):
        with patch("service.agent_service.AgentService.build_prompt_preview", side_effect=RuntimeError("boom")):
            r = client.post("/llm-review/agents/prompt-preview", json={
                "name": AgentName.REVIEWER_1,
                "message": "test",
            })
        assert r.status_code == 500

    def test_agent_with_retrieval_returns_200(self, client):
        r = client.post("/llm-review/agents/retrieval", json={
            "name": AgentName.REVIEWER_1,
            "model": LlmModelName.MOCK,
            "temperature": 0.0,
            "message": "review this",
            "paper_path": PAPER_PATH,
        })
        assert r.status_code == 200

    def test_agent_with_retrieval_value_error_returns_400(self, client):
        with patch("container.Container.test_agent_with_retrieval", side_effect=ValueError("bad paper")):
            r = client.post("/llm-review/agents/retrieval", json={
                "name": AgentName.REVIEWER_1,
                "model": LlmModelName.MOCK,
                "temperature": 0.0,
                "message": "review this",
                "paper_path": "nonexistent.pdf",
            })
        assert r.status_code == 400

    def test_agent_with_retrieval_error_returns_500(self, client):
        with patch("container.Container.test_agent_with_retrieval", side_effect=RuntimeError("boom")):
            r = client.post("/llm-review/agents/retrieval", json={
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
        assert client.get("/llm-review/papers").status_code == 200

    def test_list_papers_returns_list(self, client):
        assert isinstance(client.get("/llm-review/papers").json(), list)

    def test_list_indexed_returns_200(self, client):
        assert client.get("/llm-review/papers/indexed").status_code == 200

    def test_index_paper_invalid_path_returns_400(self, client):
        r = client.post("/llm-review/papers/index", json={"paper_path": "nonexistent/paper.pdf"})
        assert r.status_code == 400

    def test_index_paper_error_returns_500(self, client):
        with patch("service.retrieval_service.RetrievalService.index_paper", side_effect=RuntimeError("boom")):
            r = client.post("/llm-review/papers/index", json={"paper_path": PAPER_PATH})
        assert r.status_code == 500

    def test_get_indexed_detail_valid_paper_returns_200(self, client):
        client.post("/llm-review/papers/index", json={"paper_path": PAPER_PATH, "force_reindex": True})
        r = client.get("/llm-review/papers/indexed/detail", params={"paper_path": PAPER_PATH})
        assert r.status_code == 200
        assert r.json()["paper_path"] == PAPER_PATH

    def test_get_indexed_detail_not_found_returns_404(self, client):
        r = client.get("/llm-review/papers/indexed/detail", params={"paper_path": "nonexistent.pdf"})
        assert r.status_code == 404

    def test_get_indexed_detail_error_returns_500(self, client):
        with patch("service.retrieval_service.RetrievalService.get_indexed_paper", side_effect=RuntimeError("boom")):
            r = client.get("/llm-review/papers/indexed/detail", params={"paper_path": PAPER_PATH})
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class TestGraphEndpoints:

    def test_compile_returns_200(self, client):
        assert client.post("/llm-review/graph/compile", json=None).status_code == 200

    def test_compile_status_compiled(self, client):
        assert client.post("/llm-review/graph/compile", json=None).json()["status"] == "compiled"

    def test_compile_error_returns_500(self, client):
        with patch("container.Container.compile_graph", side_effect=RuntimeError("boom")):
            r = client.post("/llm-review/graph/compile", json=None)
        assert r.status_code == 500

    def test_get_config_returns_200(self, client):
        client.post("/llm-review/graph/compile", json=None)
        assert client.get("/llm-review/graph/config").status_code == 200

    def test_get_config_has_agents(self, client):
        assert "agents" in client.get("/llm-review/graph/config").json()

    def test_run_invalid_paper_returns_error(self, client):
        r = client.post("/llm-review/graph/run", json={
            "paper_path": "nonexistent.pdf",
            "run_description": "Run con paper non valido",
        })
        assert r.status_code in {400, 409, 500}

    def test_run_missing_description_returns_422(self, client):
        r = client.post("/llm-review/graph/run", json={"paper_path": PAPER_PATH})
        assert r.status_code == 422

    def test_run_blank_description_returns_422(self, client):
        r = client.post("/llm-review/graph/run", json={
            "paper_path": PAPER_PATH,
            "run_description": "   ",
        })
        assert r.status_code == 422

    def test_run_not_compiled_returns_409(self, client):
        with patch("container.Container.invoke_graph", side_effect=RuntimeError("Graph not compiled")):
            r = client.post("/llm-review/graph/run", json={
                "paper_path": PAPER_PATH,
                "run_description": "Run senza grafo compilato",
            })
        assert r.status_code == 409

    def test_run_generic_error_returns_500(self, client):
        with patch("container.Container.invoke_graph", side_effect=Exception("boom")):
            r = client.post("/llm-review/graph/run", json={
                "paper_path": PAPER_PATH,
                "run_description": "Run con errore generico",
            })
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class TestRunsEndpoints:

    def test_list_runs_returns_200(self, client):
        assert client.get("/llm-review/runs").status_code == 200

    def test_list_runs_returns_list(self, client):
        assert isinstance(client.get("/llm-review/runs").json(), list)

    def test_list_runs_items_include_run_description(self, client):
        runs = client.get("/llm-review/runs").json()
        if not runs:
            pytest.skip("No runs available to assert run_description field.")
        assert "run_description" in runs[0]

    def test_get_run_not_found_returns_404(self, client):
        assert client.get("/llm-review/runs/nonexistent-run-id").status_code == 404

    def test_get_run_error_returns_500(self, client):
        with patch("service.graph_service.GraphService.get_run", side_effect=RuntimeError("boom")):
            r = client.get("/llm-review/runs/some-run-id")
        assert r.status_code == 500

    def test_get_run_agent_runs_not_found_returns_404(self, client):
        r = client.get("/llm-review/runs/nonexistent-run-id/agent-runs")
        assert r.status_code == 404

    def test_get_run_agent_runs_returns_200(self, client):
        runs = client.get("/llm-review/runs").json()
        assert runs, "Expected at least one run in history for this test"
        run_id = runs[0]["run_id"]
        r = client.get(f"/llm-review/runs/{run_id}/agent-runs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_run_agent_runs_filter_by_agent(self, client):
        runs = client.get("/llm-review/runs").json()
        assert runs, "Expected at least one run in history for this test"
        run_id = runs[0]["run_id"]
        r = client.get(f"/llm-review/runs/{run_id}/agent-runs", params={"agent_name": AgentName.REVIEWER_1})
        assert r.status_code == 200
        for item in r.json():
            assert item["agent"] == AgentName.REVIEWER_1

    def test_get_run_agent_runs_filter_by_round(self, client):
        runs = client.get("/llm-review/runs").json()
        assert runs, "Expected at least one run in history for this test"
        run_id = runs[0]["run_id"]
        r = client.get(f"/llm-review/runs/{run_id}/agent-runs", params={"round_index": 0})
        assert r.status_code == 200
        for item in r.json():
            assert item["round"] == 0

    def test_get_run_agent_runs_error_returns_500(self, client):
        with patch("service.graph_service.GraphService.get_agent_runs", side_effect=RuntimeError("boom")):
            r = client.get("/llm-review/runs/some-run-id/agent-runs")
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# Prompt version endpoints
# ---------------------------------------------------------------------------

class TestPromptEndpoints:

    def test_list_returns_seeded_versions_without_template(self, client):
        r = client.get("/llm-review/prompts")
        assert r.status_code == 200
        versions = r.json()
        pairs = {(v["agent_role"], v["version_label"]) for v in versions}
        assert {("reviewer", "v1"), ("reviewer", "v2"), ("meta_reviewer", "v1")} <= pairs
        assert all("template" not in v for v in versions)

    def test_list_filter_by_role(self, client):
        r = client.get("/llm-review/prompts", params={"agent_role": "reviewer"})
        assert r.status_code == 200
        assert {v["agent_role"] for v in r.json()} == {"reviewer"}

    def test_detail_includes_template(self, client):
        first = client.get("/llm-review/prompts").json()[0]
        r = client.get(f"/llm-review/prompts/{first['id']}")
        assert r.status_code == 200
        assert r.json()["template"]

    def test_detail_missing_returns_404(self, client):
        assert client.get("/llm-review/prompts/99999").status_code == 404

    def test_create_returns_201_then_conflict_409(self, client):
        body = {"agent_role": "reviewer", "version_label": "v97",
                "template": "Test template.", "description": "test"}
        assert client.post("/llm-review/prompts", json=body).status_code == 201
        assert client.post("/llm-review/prompts", json=body).status_code == 409

    def test_create_invalid_role_returns_422(self, client):
        body = {"agent_role": "banana", "version_label": "v1", "template": "x"}
        assert client.post("/llm-review/prompts", json=body).status_code == 422

    def test_patch_updates_metadata_only(self, client):
        created = client.post("/llm-review/prompts", json={
            "agent_role": "reviewer", "version_label": "v98", "template": "Immutable text.",
        }).json()
        r = client.patch(f"/llm-review/prompts/{created['id']}",
                         json={"description": "updated", "is_active": False})
        assert r.status_code == 200
        assert r.json()["description"] == "updated"
        assert r.json()["is_active"] is False
        assert r.json()["template"] == "Immutable text."

    def test_patch_missing_returns_404(self, client):
        assert client.patch("/llm-review/prompts/99999", json={"description": "x"}).status_code == 404

    def test_preview_with_version_uses_that_template(self, client):
        r = client.post("/llm-review/agents/prompt-preview", json={
            "name": AgentName.REVIEWER_1, "message": "Review this.", "prompt_version": "v2",
        })
        assert r.status_code == 200
        assert "skeptical" in r.json()["system_prompt"].lower()

    def test_preview_unknown_version_returns_400(self, client):
        r = client.post("/llm-review/agents/prompt-preview", json={
            "name": AgentName.REVIEWER_1, "message": "Review this.", "prompt_version": "v99",
        })
        assert r.status_code == 400

    def test_compile_with_unknown_prompt_version_returns_400(self, client):
        config = client.get("/llm-review/graph/config").json()
        assert config, "graph should be compiled by the fixture"
        config["agents"][0]["prompt_version"] = "v99"
        assert client.post("/llm-review/graph/compile", json=config).status_code == 400

    def test_compile_with_v2_reviewer_succeeds_and_shows_in_config(self, client):
        config = client.get("/llm-review/graph/config").json()
        for agent in config["agents"]:
            if agent["agent_name"] == "reviewer_1":
                agent["prompt_version"] = "v2"
        assert client.post("/llm-review/graph/compile", json=config).status_code == 200
        updated = client.get("/llm-review/graph/config").json()
        by_name = {a["agent_name"]: a for a in updated["agents"]}
        assert by_name["reviewer_1"]["prompt_version"] == "v2"
        assert by_name["reviewer_2"]["prompt_version"] == "v1"


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

class TestBackupEndpoint:

    def test_returns_zip_attachment(self, client):
        import io
        import zipfile

        r = client.get("/llm-review/backup")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"
        disposition = r.headers["content-disposition"]
        assert disposition.startswith("attachment; filename=")
        assert disposition.endswith('.zip"')

        archive = zipfile.ZipFile(io.BytesIO(r.content))
        names = archive.namelist()
        assert "manifest.json" in names
        # one subfolder per table, seeded prompt versions present
        assert any(n.startswith("prompt_version/") for n in names)

    def test_error_returns_500(self, client):
        with patch(
            "service.backup_service.BackupService.build_zip",
            side_effect=RuntimeError("boom"),
        ):
            r = client.get("/llm-review/backup")
        assert r.status_code == 500
