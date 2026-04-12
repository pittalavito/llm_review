import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path so imports resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from fastapi.testclient import TestClient
from main import app
from clients.llm.mock_llm_client import MOCK_RESPONSE_PREFIX


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_models_endpoint(client):
    response = client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "mock" in data


def test_test_llm_endpoint(client):
    response = client.post("/test-llm", json={"message": "ciao"})
    assert response.status_code == 200
    assert response.json()["response"] == f"{MOCK_RESPONSE_PREFIX}ciao"


def test_test_llm_with_explicit_model(client):
    response = client.post("/test-llm", json={"message": "ciao", "llm_model": "mock"})
    assert response.status_code == 200
    assert response.json()["response"] == f"{MOCK_RESPONSE_PREFIX}ciao"


def test_test_llm_with_unknown_model_falls_back(client):
    response = client.post("/test-llm", json={"message": "ciao", "llm_model": "nonexistent"})
    assert response.status_code == 200
    assert response.json()["response"] == f"{MOCK_RESPONSE_PREFIX}ciao"