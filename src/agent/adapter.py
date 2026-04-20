import json

from typing import TypeVar
from pydantic import BaseModel
from models.agent import AgentResponse, AgentName


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LlmResponseAdapter:
    """Adapts raw LLM string output into validated structured domain objects.

    Responsibilities:
    - Extract a JSON candidate from noisy LLM output (markdown fences, extra text)
    - Parse and validate JSON against a Pydantic schema
    - Serialize the validated payload into the AgentResponse envelope
    """

    @staticmethod
    def extract_json_candidate(raw_output: str) -> str:
        """Strip markdown fences and surrounding text, returning the bare JSON object."""
        text = raw_output.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if len(lines) >= 3:
                text = "\n".join(lines[1:-1]).strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in model output.")
        return text[start : end + 1]

    @staticmethod
    def parse_json_schema(raw_output: str, schema: type[SchemaT]) -> SchemaT:
        """Parse raw LLM output and validate it against a Pydantic schema."""
        candidate = LlmResponseAdapter.extract_json_candidate(raw_output)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON output: {exc}") from exc

        try:
            return schema.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"JSON output does not match schema: {exc}") from exc

    @staticmethod
    def to_structured_output(name: AgentName, payload: dict) -> str:
        """Wrap a validated payload dict in the AgentResponse envelope and serialize."""
        envelope = AgentResponse(agent=name, payload=payload)
        return envelope.model_dump_json(ensure_ascii=False)
