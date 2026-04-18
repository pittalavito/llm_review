import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from fastapi.testclient import TestClient
from main import app
from settings import PAPERS_DIR


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
    response = client.get("/dev/graph-config")
    assert response.status_code == 200
    assert response.json() is None


def test_put_graph_config_compiles_and_persists_config(client):
    compile_response = client.put("/dev/graph-config", json=GRAPH_CONFIG)
    assert compile_response.status_code == 200
    assert compile_response.json() == GRAPH_CONFIG

    get_response = client.get("/dev/graph-config")
    assert get_response.status_code == 200
    assert get_response.json() == GRAPH_CONFIG


def test_run_graph_requires_compiled_graph(client):
    response = client.post("/dev/graph-run", json={"paper": "A short paper abstract."})
    assert response.status_code == 400
    assert "Graph error:" in response.json()["detail"]


def test_run_graph_returns_reviews_after_compile(client):
    compile_response = client.put("/dev/graph-config", json=GRAPH_CONFIG)
    assert compile_response.status_code == 200

    run_response = client.post(
        "/dev/graph-run",
        json={"paper": "This paper studies a method and reports two experiments."},
    )
    assert run_response.status_code == 200

    data = run_response.json()
    assert isinstance(data["reviews"], list)
    assert len(data["reviews"]) == 1
    assert data["reviews"][0]["agent"] == "methodology_reviewer"
    assert isinstance(data["reviews"][0]["payload"], dict)
    assert data["reviews"][0]["payload"]["summary"]
    assert data["raw_result"]["paper"] == "This paper studies a method and reports two experiments."
    assert data["raw_result"]["reviews"][0]["agent"] == data["reviews"][0]["agent"]


def test_run_graph_rejects_blank_paper(client):
    response = client.post("/dev/graph-run", json={"paper": "   "})
    assert response.status_code == 422
    assert "paper" in response.json()["detail"][0]["loc"]


def test_run_graph_file_returns_retrieval_metadata_and_reuses_index(client):
    compile_response = client.put("/dev/graph-config", json=GRAPH_CONFIG)
    assert compile_response.status_code == 200

    paper_dir = PAPERS_DIR / f"test-{uuid4().hex}"
    paper_dir.mkdir(parents=True, exist_ok=True)
    paper_file = paper_dir / "paper.txt"
    paper_file.write_text(
        "This study evaluates reproducibility using three datasets and ablation experiments.",
        encoding="utf-8",
    )

    payload = {"paper_path": f"{paper_dir.name}/paper.txt", "top_k": 4, "force_reindex": False}
    try:
        first_response = client.post("/dev/graph-run-file", json=payload)
        assert first_response.status_code == 200
        first_data = first_response.json()
        assert first_data["retrieval"]["index_status"] == "rebuilt"
        assert first_data["retrieval"]["chunk_count_total"] >= 1
        assert first_data["retrieval"]["chunk_count_retrieved"] >= 1
        assert first_data["retrieval"]["top_k"] == 4

        second_response = client.post("/dev/graph-run-file", json=payload)
        assert second_response.status_code == 200
        second_data = second_response.json()
        assert second_data["retrieval"]["index_status"] == "reused"
        assert isinstance(second_data["reviews"], list)
        assert len(second_data["reviews"]) == 1
        assert second_data["reviews"][0]["agent"] == "methodology_reviewer"
    finally:
        if paper_file.exists():
            paper_file.unlink()
        if paper_dir.exists():
            paper_dir.rmdir()


def test_run_graph_file_rejects_path_traversal(client):
    compile_response = client.put("/dev/graph-config", json=GRAPH_CONFIG)
    assert compile_response.status_code == 200

    response = client.post(
        "/dev/graph-run-file",
        json={"paper_path": "../secrets.txt", "top_k": 4, "force_reindex": False},
    )
    assert response.status_code == 400
    assert "path traversal" in response.json()["detail"].lower()
