from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Base interface for any LLM client (OpenAI, Ollama, HF, etc.)."""

    @abstractmethod
    def call(self, prompt: str) -> str:
        raise NotImplementedError()