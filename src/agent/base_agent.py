# src/agents/base_agent.py
from abc import ABC, abstractmethod

from clients.llm.base_llm_client import BaseLLMClient
from schemas.enums import AgentName


class BaseAgent(ABC):
    def __init__(self, llm: BaseLLMClient, name: AgentName):
        self.llm = llm
        self.name = name
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        pass
    
    def run(self, message: str) -> str:
        full_prompt = f"{self.system_prompt}\n\n{message}"
        return self.llm.invoke(full_prompt)