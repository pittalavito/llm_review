from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Base interface for any LLM client (OpenAI, Ollama, HF, etc.)."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError()