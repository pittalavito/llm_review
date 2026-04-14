from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from clients.llm.base_llm_client import BaseLLMClient

MOCK_RESPONSE_PREFIX = "Here is a mock response for your prompt: "
MOCK_TOOL_CALLING_RESPONSE = "Mock tool-calling response: tool results have been processed."


class MockLLMClient(BaseLLMClient):
    """Mock client for testing the entire flow without external dependencies."""

    def invoke(self, prompt: str) -> str:
        return f"{MOCK_RESPONSE_PREFIX}{prompt}"

    def get_chat_model(self) -> BaseChatModel:
        return FakeListChatModel(responses=[MOCK_TOOL_CALLING_RESPONSE])

    def supports_tool_calling(self) -> bool:
        return False