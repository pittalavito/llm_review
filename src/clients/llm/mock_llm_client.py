from clients.llm.base_llm_client import BaseLLMClient

MOCK_RESPONSE_PREFIX = "Here is a mock response for your prompt: "


class MockLLMClient(BaseLLMClient):
    """Mock client for testing the entire flow without external dependencies."""

    def call(self, prompt: str) -> str:
        return f"{MOCK_RESPONSE_PREFIX}{prompt}"