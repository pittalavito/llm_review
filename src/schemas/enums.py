from enum import StrEnum
    
    
class LlmModelName(StrEnum):
    MOCK = "mock"
    OLLAMA_TINYLLAMA = "tinyllama:1.1b"
    OLLAMA_LLAMA32 = "llama3.2:3b"
    OLLAMA_GROQ_TOOL_USE = "llama3-groq-tool-use"
    OLLAMA_GEMMA_4 = "gemma4"
    OPENAPI_GPT_3_5_TURBO = "gpt-3.5-turbo"
    OPENAPI_GPT_4 = "gpt-4"
    
    def is_ollama(self) -> bool:
        return self in {self.OLLAMA_TINYLLAMA, self.OLLAMA_LLAMA32, self.OLLAMA_GROQ_TOOL_USE, self.OLLAMA_GEMMA_4}
    
    def is_openapi(self) -> bool:
        return self in {self.OPENAPI_GPT_3_5_TURBO, self.OPENAPI_GPT_4}
    
    def is_mock(self) -> bool:
        return self == self.MOCK
    
class AgentName(StrEnum):
    TEST_TOOL_AGENT = "test_tool_agent"
    METHODOLOGY_REVIEWER = "methodology_reviewer"
    
class GraphNodeName(StrEnum):
    """Graph node name enum."""
    METHODOLOGY_REVIEWER = "methodology_reviewer"
