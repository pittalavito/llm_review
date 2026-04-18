import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from agent.methodology_review import MethodologyReviewerAgent
from clients.llm.base_llm_client import BaseLLMClient
from clients.llm.mock_llm_client import MockLLMClient


class SequenceLLMClient(BaseLLMClient):
    def __init__(self, responses: list[str]):
        self._responses = responses
        self.calls = 0

    def invoke(self, prompt: str) -> str:
        self.calls += 1
        if not self._responses:
            raise RuntimeError("No response configured")
        return self._responses.pop(0)


def test_methodology_agent_returns_valid_json_with_mock_client():
    agent = MethodologyReviewerAgent(llm=MockLLMClient())
    output = agent.run("Paper text about experiments and methodology.")
    data = json.loads(output)
    payload = data["payload"]

    assert data["agent"] == "methodology_reviewer"
    assert set(payload.keys()) == {
        "summary",
        "strengths",
        "weaknesses",
        "reproducibility_score",
        "confidence",
        "suggestions",
    }
    assert isinstance(payload["strengths"], list)
    assert isinstance(payload["weaknesses"], list)


def test_methodology_agent_repairs_once_when_first_output_is_invalid_json():
    llm = SequenceLLMClient(
        responses=[
            "not a json",
            '{"summary":"ok","strengths":["s1"],"weaknesses":["w1"],"reproducibility_score":4,"confidence":3,"suggestions":["x"]}',
        ]
    )
    agent = MethodologyReviewerAgent(llm=llm)

    output = agent.run("Paper text")
    data = json.loads(output)
    payload = data["payload"]

    assert data["agent"] == "methodology_reviewer"
    assert payload["reproducibility_score"] == 4
    assert llm.calls == 2


def test_methodology_agent_raises_after_failed_repair_attempt():
    llm = SequenceLLMClient(responses=["bad", "still bad"])
    agent = MethodologyReviewerAgent(llm=llm)

    with pytest.raises(ValueError):
        agent.run("Paper text")

    assert llm.calls == 2
