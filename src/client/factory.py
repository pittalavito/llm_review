from typing import Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from client.mock_chat import MockChatModel
from config import Config
from models.agent import LlmModelName

def _build_mock(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    return MockChatModel()


def _build_ollama(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    return ChatOllama(
        model=model,
        base_url=config.ollama_url,
        temperature=temperature,
        num_predict=config.ollama_num_predict,
        keep_alive=config.ollama_keep_alive,
    )

def _build_openai(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    if not config.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured.")
    return ChatOpenAI(model=model, api_key=config.openai_api_key, temperature=temperature)


def _build_anthropic(model: LlmModelName, temperature: float, config: Config) -> BaseChatModel:
    if not config.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured.")
    return ChatAnthropic(model=model, api_key=config.anthropic_api_key, temperature=temperature)


CLIENT_FACTORIES: list[tuple[Callable[[LlmModelName], bool], Callable[..., BaseChatModel]]] = [
    (LlmModelName.is_mock, _build_mock),
    (LlmModelName.is_ollama, _build_ollama),
    (LlmModelName.is_openai, _build_openai),
    (LlmModelName.is_anthropic, _build_anthropic)
]
