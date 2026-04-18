import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from adapter.agent_output_adapter import AgentOutputAdapter


def test_to_structured_output_parses_valid_payload():
    raw = json.dumps({"agent": "methodology_reviewer", "payload": {"summary": "ok"}})

    result = AgentOutputAdapter.to_structured_output(raw)

    assert result.agent == "methodology_reviewer"
    assert result.payload["summary"] == "ok"


def test_to_structured_output_raises_on_invalid_json():
    with pytest.raises(ValueError):
        AgentOutputAdapter.to_structured_output("not-json")


def test_to_structured_outputs_parses_multiple_items():
    raw_outputs = [
        json.dumps({"agent": "methodology_reviewer", "payload": {"summary": "first"}}),
        json.dumps({"agent": "test_tool_agent", "payload": {"analysis": "second"}}),
    ]

    results = AgentOutputAdapter.to_structured_outputs(raw_outputs)

    assert len(results) == 2
    assert results[0].agent == "methodology_reviewer"
    assert results[1].agent == "test_tool_agent"
