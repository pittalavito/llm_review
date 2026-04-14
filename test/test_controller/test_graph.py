import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from fastapi.testclient import TestClient
from main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


GRAPH_CONFIG = {
    "methodology_reviewer_agent": "methodology_reviewer",
    "methodology_reviewer_model": "mock",
    "methodology_reviewer_temperature": 0.4,
    "max_iterations": 2,
    "max_tokens": 256,
}


def test_get_graph_config_returns_null_before_compile(client):
    response = client.get("/graph-config")
    assert response.status_code == 200
    assert response.json() is None


def test_put_graph_config_compiles_and_persists_config(client):
    compile_response = client.put("/graph-config", json=GRAPH_CONFIG)
    assert compile_response.status_code == 200
    assert compile_response.json() == GRAPH_CONFIG

    get_response = client.get("/graph-config")
    assert get_response.status_code == 200
    assert get_response.json() == GRAPH_CONFIG


def test_run_graph_requires_compiled_graph(client):
    response = client.post("/graph-run", json={"paper": "A short paper abstract."})
    assert response.status_code == 400
    assert "Graph error:" in response.json()["detail"]


def test_run_graph_returns_reviews_after_compile(client):
    compile_response = client.put("/graph-config", json=GRAPH_CONFIG)
    assert compile_response.status_code == 200

    run_response = client.post(
        "/graph-run",
        json={"paper": "This paper studies a method and reports two experiments."},
    )
    assert run_response.status_code == 200

    data = run_response.json()
    assert isinstance(data["reviews"], list)
    assert len(data["reviews"]) == 1
    assert isinstance(data["reviews"][0], str)
    assert data["reviews"][0]
    assert data["raw_result"]["paper"] == "This paper studies a method and reports two experiments."
    assert data["raw_result"]["reviews"] == data["reviews"]


def test_run_graph_rejects_blank_paper(client):
    response = client.post("/graph-run", json={"paper": "   "})
    assert response.status_code == 422
    assert "paper" in response.json()["detail"][0]["loc"]
