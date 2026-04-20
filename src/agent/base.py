import logging

from abc import ABC
from pydantic import BaseModel
from llm_client.base_client import BaseLLMClient
from agent.adapter import LlmResponseAdapter
from agent.builder import PromptBuilder
from models.agent import AgentName

logger = logging.getLogger(__name__)


class AgentValidationError(ValueError):
    """Raised when all LLM repair attempts fail to produce valid structured output.
    Carries the last raw LLM output so callers can surface it for debugging.
    """
    def __init__(self, message: str, raw_output: str = "") -> None:
        super().__init__(message)
        self.raw_output: str = raw_output


class BaseAgent(ABC):
    AGENT_NAME: AgentName
    SYSTEM_PROMPT: str = ""
    RESPONSE_SCHEMA: type[BaseModel] | None = None
    REPAIR_ATTEMPTS: int = 1
    MESSAGE_LABEL: str = "Message"
    RAG_QUERY: str = ""

    def __init__(self, llm: BaseLLMClient):
        self.llm_client: BaseLLMClient = llm
        self.name = self.AGENT_NAME

    # ragionare se tornare output strutturato 
    def run(self, message: str) -> str:
        """Orchestrates the full agent pipeline:
        normalize → build prompt → call LLM → adapt output → serialize.
        """
        logger.info("Running agent '%s'", self.name)

        """Build full prompt"""
        normalized_message = self._normalize_message(message)
        full_prompt = self._build_prompt(normalized_message)
        logger.info("Built prompt for agent '%s': %s", self.name, full_prompt[:50])

        """Invoke LLM and adapt response"""
        raw_output = self.llm_client.invoke(full_prompt)
        payload = self._adapt_llm_response(full_prompt, raw_output)
        return LlmResponseAdapter.to_structured_output(self.name, payload)
    

    def _normalize_message(self, message: str, max_length: int | None = None) -> str:
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("Message must not be empty.")
        if max_length is not None and len(normalized_message) > max_length:
            raise ValueError(f"Message exceeds the maximum length of {max_length} characters.")
        return normalized_message


    def _build_prompt(self, message: str) -> str:
        return PromptBuilder.build_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            schema=self.RESPONSE_SCHEMA,
            message=message,
            message_label=self.MESSAGE_LABEL,
        )


    def _adapt_llm_response(self, prompt: str, raw_output: str) -> dict:
        """Adapt raw LLM output into a validated dict payload, with optional self-repair attempts."""
        
        schema = self.RESPONSE_SCHEMA
        if schema is None:
            return {"response": raw_output.strip()}

        current_output = raw_output
        attempts = max(0, self.REPAIR_ATTEMPTS)
        last_error: ValueError | None = None

        for attempt in range(attempts + 1):
            try:
                validated = LlmResponseAdapter.parse_json_schema(current_output, schema)
                return validated.model_dump()
            except ValueError as exc:
                logger.warning("Validation failed for agent '%s' output on attempt %d/%d: %s",self.name, attempt + 1, attempts, exc,)
                last_error = exc
                if attempt >= attempts:
                    break
                repair_prompt = PromptBuilder.build_repair_prompt(prompt, current_output, exc)
                current_output = self.llm_client.invoke(repair_prompt)

        final_error = last_error if last_error is not None else ValueError("Invalid structured output.")
        # forse basta solo value error
        raise AgentValidationError(str(final_error), raw_output=current_output) from final_error
