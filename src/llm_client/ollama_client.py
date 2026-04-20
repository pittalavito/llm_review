import logging

from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama

from client.base_client import BaseLLMClient
from agent.models.enums import LlmModelName

logger = logging.getLogger(__name__)

class OllamaLLMClient(BaseLLMClient):
    """Client LLM backed by un'istanza locale Ollama tramite langchain-ollama."""

    def __init__(
        self,
        model: LlmModelName,
        base_url: str,
        temperature: float = 0,
        num_predict: int = 256,
        keep_alive: str = "10m",
    ):
        self._model = model
        self._llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            num_predict=num_predict,
            keep_alive=keep_alive,
        )
        logger.info(
            "OllamaLLMClient.init : model=%s base_url=%s temperature=%s num_predict=%s keep_alive=%s",
            model,
            base_url,
            temperature,
            num_predict,
            keep_alive,
        )

    def invoke(self, prompt: str) -> str:
        truncated = (prompt[:30] + "...") if len(prompt) > 30 else prompt
        logger.info("OllamaLLMClient.invoke: model=%s prompt='%s'", self._model, truncated)
        return self._llm.invoke(prompt).content
