
import asyncio

from fastapi import Request
from service.graph_service import GraphService
from service.llm_service import LlmService
from settings import Settings


class Container:
    """DI container for configuration and LLM client registry."""
    def __init__(self, settings: Settings):        
        self.settings = settings
        self.llm_service = LlmService(settings)
        self.graph_service = GraphService()

def inject_container(request: Request) -> Container:
    """Dependency to retrieve the DI container from the request state."""
    return request.app.state.container

def inject_settings(request: Request) -> Settings:
    """Dependency to retrieve the application settings from the container."""
    container = inject_container(request)
    return container.settings   

def inject_llm_service(request: Request) -> LlmService:
    """Dependency to retrieve the LLM service from the container."""
    container = inject_container(request)
    return container.llm_service

def inject_graph_service(request: Request) -> GraphService:
    """Dependency to retrieve the Graph service from the container."""
    container = inject_container(request)
    return container.graph_service