import logging

from langchain.agents import create_agent

from agent.base_agent import BaseAgent
from clients.llm.mock_llm_client import MOCK_RESPONSE_PREFIX
from clients.llm.base_llm_client import BaseLLMClient
from schemas.enums import AgentName
from tools.text_stats import compute_text_stats

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 8_000


class TestToolAgent(BaseAgent):

    def __init__(self, llm: BaseLLMClient):
        super().__init__(llm=llm, name=AgentName.TEST_TOOL_AGENT)

    @property
    def system_prompt(self) -> str:
        return (
            "You are a helpful assistant that analyzes text safely. "
            "Use the compute_text_stats tool when it is available and summarize the results clearly."
        )

    def run(self, message: str) -> str:
        normalized_message = message.strip()
        if not normalized_message:
            raise ValueError("Message must not be empty.")
        if len(normalized_message) > MAX_MESSAGE_LENGTH:
            raise ValueError(f"Message exceeds the maximum length of {MAX_MESSAGE_LENGTH} characters.")

        if not self.llm.supports_tool_calling():
            logger.warning(
                "Model for agent '%s' does not natively support tool-calling; using safe fallback.",
                self.name,
            )
            return self._run_with_safe_fallback(normalized_message)

        try:
            chat_model = self.llm.get_chat_model()
            app = create_agent(chat_model, [compute_text_stats])
            result = app.invoke(
                {
                    "messages": [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": normalized_message},
                    ]
                }
            )
            return self._extract_response(result)
        except Exception:
            logger.exception(
                "Tool-calling failed for agent '%s'; falling back to direct tool execution.",
                self.name,
            )
            return self._run_with_safe_fallback(normalized_message)

    def _run_with_safe_fallback(self, message: str) -> str:
        tool_result = compute_text_stats.invoke({"text": message})
        fallback_prompt = (
            f"{self.system_prompt}\n\n"
            "The tool has already been executed safely in Python. "
            "Use the result below to answer the user.\n\n"
            f"User message:\n{message}\n\n"
            f"Tool result:\n{tool_result}"
        )
        try:
            response = self.llm.invoke(fallback_prompt).strip()
            if response and not response.startswith(MOCK_RESPONSE_PREFIX):
                return response
        except Exception:
            logger.exception(
                "Fallback summarization failed for agent '%s'; returning raw tool output.",
                self.name,
            )
        return self._format_fallback_response(message, tool_result)

    @staticmethod
    def _format_fallback_response(message: str, tool_result: str) -> str:
        preview = message if len(message) <= 280 else f"{message[:277]}..."
        return (
            "Analysis completed.\n\n"
            f"Text preview:\n{preview}\n\n"
            f"{tool_result}\n\n"
            "Suggested next step:\n"
            "Use these metrics to decide whether the text needs a deeper methodology or content review."
        )

    @staticmethod
    def _extract_response(result: dict) -> str:
        messages = result.get("messages", [])
        if not messages:
            raise ValueError("Agent returned no messages.")

        last_message = messages[-1]
        content = getattr(last_message, "content", last_message)

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            extracted = "\n".join(part for part in text_parts if part).strip()
            if extracted:
                return extracted

        extracted = str(content).strip()
        if not extracted:
            raise ValueError("Agent returned an empty response.")
        return extracted
