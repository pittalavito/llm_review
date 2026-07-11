from typing import Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from domain.client.mock_chat import MockChatModel
from config import Config
from models.agent import LlmModelName

def create_client(self, model: LlmModelName, temperature: float) -> BaseChatModel:        
    """Creates a chat model client based on the specified model and temperature."""
    
    for predicate, factory in _CLIENT_FACTORIES:
        if predicate(model):
            return factory(model, temperature, self.config)
    raise ValueError(f"Unsupported LLM model: {model}")


def _build_mock(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    """Builds a mock chat model for testing purposes."""
    
    return MockChatModel()


def _build_ollama(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    """"Builds an Ollama chat model using the provided configuration."""
    
    return ChatOllama(
        model=model,
        base_url=config.ollama_url,
        temperature=temperature,
        num_predict=config.ollama_num_predict,
        keep_alive=config.ollama_keep_alive,
        api_key=config.ollama_api_key
    )


def _build_aitho(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    """Builds an Aitho chat model using the provided configuration."""
    
    if not config.aitho_api_key:
        raise ValueError("AITHO_API_KEY not configured.")    
    return ChatOpenAI(
        model=model,
        api_key=config.aitho_api_key,
        temperature=temperature,
        base_url=config.aitho_url,
    )
    

def _build_openai(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    """Builds an OpenAI chat model using the provided configuration."""
    
    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured.")
    return ChatOpenAI(
        model=model, 
        api_key=config.openai_api_key, 
        temperature=temperature,
        #reasoning_effort="medium",   # minimal | low | medium | high
    )


def _build_anthropic(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    """Builds an Anthropic chat model using the provided configuration."""
    
    if not config.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured.")
    chat = ChatAnthropic(
        model=model, 
        api_key=config.anthropic_api_key, 
        temperature=temperature
    )       
    return chat

_CLIENT_FACTORIES: list[tuple[Callable[[LlmModelName], bool], Callable[..., BaseChatModel]]] = [
    (LlmModelName.is_mock, _build_mock),
    (LlmModelName.is_ollama, _build_ollama),
    (LlmModelName.is_openai, _build_openai),
    (LlmModelName.is_anthropic, _build_anthropic),
    (LlmModelName.is_aitho, _build_aitho)
]
