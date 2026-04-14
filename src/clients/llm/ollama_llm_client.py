import logging

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from clients.llm.base_llm_client import BaseLLMClient
from schemas.enums import LlmModelName

logger = logging.getLogger(__name__)

_TOOL_CALLING_MODELS = {
    LlmModelName.OLLAMA_LLAMA32,
}


class OllamaLLMClient(BaseLLMClient):
    """LLM client backed by a local Ollama instance via langchain-ollama."""

    def __init__(self, model: LlmModelName, base_url: str, temperature: float = 0):
        self._model = model
        self._llm = ChatOllama(model=model, base_url=base_url, temperature=temperature)
        logger.info("Initialized OllamaLLMClient with model '%s', base_url '%s', and temperature '%s'", model, base_url, temperature)

    def invoke(self, prompt: str) -> str:
        trunceted_size = 30
        truncated_prompt = (prompt[:trunceted_size] + '...') if len(prompt) > trunceted_size else prompt
        logger.info("Invoking OllamaLLMClient with model '%s' and temperature '%s' and prompt: %s", self._model, self._llm.temperature, truncated_prompt)
        return self._llm.invoke(prompt).content

    def get_chat_model(self) -> BaseChatModel:
        return self._llm

    def supports_tool_calling(self) -> bool:
        return self._model in _TOOL_CALLING_MODELS
