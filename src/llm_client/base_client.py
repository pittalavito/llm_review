from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Interfaccia minima per qualsiasi client LLM."""

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        raise NotImplementedError()
