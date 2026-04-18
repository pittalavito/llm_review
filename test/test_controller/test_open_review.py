import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from fastapi.testclient import TestClient
from main import app
from schemas.open_review import PaperSearchResult, PaperSummary


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_openreview_summary_endpoint_returns_summary(client, monkeypatch):
    expected_summary = PaperSummary(
        id="paper-1",
        title="A test paper",
        abstract="Abstract",
        keywords=["llm"],
        venue="ICLR",
        venueid="ICLR.cc/2025/Conference",
        pdf_path="/pdf/abc.pdf",
        decision="Accept",
        num_reviews=1,
        review_summary=[{"rating": "8", "confidence": "4", "soundness": "3"}],
    )

    stub_service = SimpleNamespace(
        get_paper_summary=lambda paper_id: expected_summary if paper_id == "paper-1" else None,
    )

    monkeypatch.setattr("controllers.dev_controller.inject_open_review_service", lambda request: stub_service)

    response = client.get("/dev/openreview/papers/paper-1/summary")
    assert response.status_code == 200
    assert response.json() == expected_summary.model_dump()


def test_openreview_summary_endpoint_returns_404_for_missing_paper(client, monkeypatch):
    stub_service = SimpleNamespace(get_paper_summary=lambda paper_id: None)
    monkeypatch.setattr("controllers.dev_controller.inject_open_review_service", lambda request: stub_service)

    response = client.get("/dev/openreview/papers/missing-paper/summary")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_openreview_search_endpoint_returns_results(client, monkeypatch):
    expected_results = [
        PaperSearchResult(
            id="paper-1",
            title="A test paper",
            abstract="Abstract",
            keywords=["llm"],
            venue="ICLR",
        )
    ]

    stub_service = SimpleNamespace(
        search_papers=lambda keyword, venue_id, limit: expected_results,
    )

    monkeypatch.setattr("controllers.dev_controller.inject_open_review_service", lambda request: stub_service)

    response = client.post(
        "/dev/openreview/papers/search",
        json={"keyword": "llm", "venue_id": "ICLR.cc/2025/Conference", "limit": 5},
    )

    assert response.status_code == 200
    assert response.json() == [item.model_dump() for item in expected_results]


def test_openreview_search_endpoint_validates_empty_keyword(client):
    response = client.post(
        "/dev/openreview/papers/search",
        json={"keyword": "   ", "venue_id": "ICLR.cc/2025/Conference", "limit": 5},
    )

    assert response.status_code == 422
    assert "keyword" in response.json()["detail"][0]["loc"]
