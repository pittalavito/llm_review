import logging

from config import Config

from clients.llm.base_llm_client import BaseLLMClient
from clients.llm.mock_llm_client import MockLLMClient
from clients.llm.ollama_llm_client import OllamaLllmClient

from schemas.enums import LlmModelName

logger = logging.getLogger(__name__)

class Container:
    """DI container for configuration and LLM client registry."""

    def __init__(self):        
        ollama_url = CONFIG.ollama_url

        # Init global LLM clients
        self.llm_models: dict[LlmModelName, BaseLLMClient] = {}
        self.llm_models[LlmModelName.MOCK] = MockLLMClient()
        self.llm_models[LlmModelName.OLLAMA_TYNYLLAMA] = OllamaLllmClient(
            model=LlmModelName.OLLAMA_TYNYLLAMA,
            base_url=ollama_url,
        )
        self.llm_models[LlmModelName.OLLAMA_LLAMA32] = OllamaLllmClient(
            model=LlmModelName.OLLAMA_LLAMA32,
            base_url=ollama_url,
        )
        
        # Init agent registry here when needed
        
    # LLM access methods
    def list_llm_models(self) -> list[LlmModelName]:
        return list(self.llm_models.keys())

    def get_llm_model(self, name: LlmModelName) -> BaseLLMClient:
        model = self.llm_models.get(name)
        if model is None:
            logger.warning("Requested LLM model '%s' not found, using mock", name)
            return self.llm_models.get(LlmModelName.MOCK)
        return model

CONFIG: Config = Config()
CONTAINER: Container = Container()