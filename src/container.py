import logging

from fastapi import Request
from service.llm_remote_service import LLMRemoteService
from settings import Settings
from schemas.enums import LlmModelName

class Container:
    """DI container for configuration and LLM client registry."""
    def __init__(self, settings: Settings):        
        self.settings = settings
        self.llm_remote_service = LLMRemoteService(settings)


def get_container(request: Request) -> Container:
    """Dependency to retrieve the DI container from the request state."""
    return request.app.state.container

def get_settings(request: Request) -> Settings:
    """Dependency to retrieve the application settings from the container."""
    container = get_container(request)
    return container.settings   

def get_llm_remote_service(request: Request) -> LLMRemoteService:
    """Dependency to retrieve the LLM client for a given model name."""
    container = get_container(request)
    return container.llm_remote_service