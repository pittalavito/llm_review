from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from clients.llm.base_llm_client import BaseLLMClient

MOCK_RESPONSE_PREFIX = "Here is a mock response for your prompt: "
MOCK_TOOL_CALLING_RESPONSE = "Mock tool-calling response: tool results have been processed."
METHODOLOGY_JSON_SCHEMA_MARKER = "schema_id: methodology_review_json_v1"


def _is_methodology_prompt(prompt: str) -> bool:
    if METHODOLOGY_JSON_SCHEMA_MARKER in prompt:
        return True

    # Fallback for schema-driven prompts where BaseAgent injects JSON Schema.
    return (
        ("MethodologyReviewPayload" in prompt or "MethodologyReviewResponse" in prompt)
        and "reproducibility_score" in prompt
        and "suggestions" in prompt
    )


class MockLLMClient(BaseLLMClient):
    """Mock client for testing the entire flow without external dependencies."""

    def invoke(self, prompt: str) -> str:
        if _is_methodology_prompt(prompt):
            return (
                '{'
                '"summary":"Methodology is coherent but needs stronger ablation detail.",' 
                '"strengths":["Clear experimental objective","Consistent evaluation protocol"],' 
                '"weaknesses":["Limited sensitivity analysis","Incomplete reproducibility details"],' 
                '"reproducibility_score":3,' 
                '"confidence":4,' 
                '"suggestions":["Add ablation on key components","Provide exact training hyperparameters"]'
                '}'
            )
        return f"{MOCK_RESPONSE_PREFIX}{prompt}"

    def get_chat_model(self) -> BaseChatModel:
        return FakeListChatModel(responses=[MOCK_TOOL_CALLING_RESPONSE])

    def supports_tool_calling(self) -> bool:
        return False