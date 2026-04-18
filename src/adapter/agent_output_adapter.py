import json

from schemas.agent.agent_output import AgentStructuredOutput


class AgentOutputAdapter:
    @staticmethod
    def to_structured_output(raw_output: str) -> AgentStructuredOutput:
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Agent returned invalid JSON output: {exc}") from exc

        try:
            return AgentStructuredOutput.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"Agent output does not match schema: {exc}") from exc

    @staticmethod
    def to_structured_outputs(raw_outputs: list[str]) -> list[AgentStructuredOutput]:
        return [AgentOutputAdapter.to_structured_output(item) for item in raw_outputs]
