from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel


class BaseLLMClient(ABC):
    """Base interface for any LLM client (OpenAI, Ollama, HF, etc.)."""

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        raise NotImplementedError()

    def get_chat_model(self) -> BaseChatModel:
        raise NotImplementedError("This client does not support chat model access.")

    def supports_tool_calling(self) -> bool:
        return False