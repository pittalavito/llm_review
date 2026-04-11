import logging

from langchain_ollama import OllamaLLM

from clients.llm.base_llm_client import BaseLLMClient
from schemas.enums import LlmModelName


logger = logging.getLogger(__name__)

class OllamaLllmClient(BaseLLMClient):
    """LLM client backed by a local Ollama instance via langchain-ollama."""

    def __init__(self, model: LlmModelName, base_url: str):
        self._llm = OllamaLLM(model=model, base_url=base_url)

    def generate(self, prompt: str) -> str:
        logger.debug("Generating response from Ollama model '%s' for prompt: %.20s…", self._llm.model, prompt)        
        return self._llm.invoke(prompt)
