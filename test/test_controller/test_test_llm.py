import sys
from pathlib import Path

import pytest

# Ensure src/ is on the path so imports resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from fastapi.testclient import TestClient
from clients.llm.mock_llm_client import MOCK_RESPONSE_PREFIX
from main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/dev/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_models_endpoint(client):
    response = client.get("/dev/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "mock" in data


def test_test_agent_list_endpoint(client):
    response = client.get("/dev/agents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "test_tool_agent" in data


def test_test_agent_with_mock_model_and_multiline_message(client):
    response = client.post(
        "/dev/agents",
        json={
            "name": "test_tool_agent",
            "model": "mock",
            "temperature": 0.7,
            "message": "Hello world.\nThis is a multiline test message.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "test_tool_agent"
    assert isinstance(data["payload"], dict)
    assert "analysis" in data["payload"]


def test_test_llm_endpoint(client):
    response = client.post("/dev/test-llm", json={"message": "ciao"})
    assert response.status_code == 422
    assert "model" in response.json()["detail"][0]["loc"]


def test_test_llm_with_explicit_model(client):
    response = client.post("/dev/test-llm", json={"message": "ciao", "model": "mock"})
    assert response.status_code == 200
    assert response.json()["response"] == f"{MOCK_RESPONSE_PREFIX}ciao"


def test_test_llm_with_unknown_model_returns_validation_error(client):
    response = client.post("/dev/test-llm", json={"message": "ciao", "model": "nonexistent"})
    assert response.status_code == 422
    assert "model" in response.json()["detail"][0]["loc"]