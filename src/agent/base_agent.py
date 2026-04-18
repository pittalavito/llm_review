# src/agents/base_agent.py
from abc import ABC
import json
from typing import TypeVar

from pydantic import BaseModel

from clients.llm.base_llm_client import BaseLLMClient
from schemas.enums import AgentName
from schemas.agent.agent_output import AgentStructuredOutput


SchemaT = TypeVar("SchemaT", bound=BaseModel)


class BaseAgent(ABC):
    SYSTEM_PROMPT: str = ""
    RESPONSE_SCHEMA: type[BaseModel] | None = None
    REPAIR_ATTEMPTS: int = 1
    MESSAGE_LABEL: str = "Message"

    def __init__(self, llm: BaseLLMClient, name: AgentName):
        self.llm = llm
        self.name = name

    @property
    def system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def run(self, message: str) -> str:
        normalized_message = self.normalize_message(message)
        full_prompt = self.build_prompt(normalized_message)
        raw_output = self.llm.invoke(full_prompt)
        payload = self.build_payload(full_prompt, raw_output)
        return self.dump_structured_output(payload)

    def build_prompt(self, message: str) -> str:
        parts: list[str] = []
        if self.SYSTEM_PROMPT.strip():
            parts.append(self.SYSTEM_PROMPT.strip())

        schema_instructions = self.build_schema_instructions()
        if schema_instructions:
            parts.append(schema_instructions)

        parts.append(f"{self.MESSAGE_LABEL}:\n{message}")
        return "\n\n".join(parts)

    def build_schema_instructions(self) -> str:
        schema = self.RESPONSE_SCHEMA
        if schema is None:
            return ""

        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        return (
            "Return only valid JSON UTF-8 without markdown or extra text.\n"
            "Output must match this JSON Schema exactly:\n"
            f"{schema_json}"
        )

    def build_repair_prompt(self, prompt: str, invalid_output: str, error: Exception) -> str:
        return "\n\n".join(
            [
                "Your previous output is invalid.",
                f"Validation error: {error}",
                "Follow the original instructions exactly and return only valid JSON.",
                "Original prompt:",
                prompt,
                "Invalid output:",
                invalid_output,
            ]
        )

    def build_payload(self, prompt: str, raw_output: str) -> dict:
        schema = self.RESPONSE_SCHEMA
        if schema is None:
            return {"response": raw_output.strip()}

        current_output = raw_output
        attempts = max(0, self.REPAIR_ATTEMPTS)
        last_error: ValueError | None = None

        for attempt in range(attempts + 1):
            try:
                validated = self.parse_json_schema(current_output, schema)
                return validated.model_dump()
            except ValueError as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                repair_prompt = self.build_repair_prompt(prompt, current_output, exc)
                current_output = self.llm.invoke(repair_prompt)

        raise last_error if last_error is not None else ValueError("Invalid structured output.")

    def normalize_message(self, message: str, max_length: int | None = None) -> str:
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("Message must not be empty.")
        if max_length is not None and len(normalized_message) > max_length:
            raise ValueError(f"Message exceeds the maximum length of {max_length} characters.")
        return normalized_message

    def dump_structured_output(self, payload: dict) -> str:
        envelope = AgentStructuredOutput(agent=self.name, payload=payload)
        return envelope.model_dump_json(ensure_ascii=False)

    @staticmethod
    def extract_json_candidate(raw_output: str) -> str:
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

    def parse_json_schema(self, raw_output: str, schema: type[SchemaT]) -> SchemaT:
        candidate = self.extract_json_candidate(raw_output)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON output: {exc}") from exc

        try:
            return schema.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"JSON output does not match schema: {exc}") from exc