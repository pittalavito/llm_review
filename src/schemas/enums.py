from enum import StrEnum

class OllamaModelName(StrEnum):
    TINYLLAMA = "tinyllama:1.1b"
    LLAMA32 = "llama3.2:3b"

class OpenApiModelName(StrEnum):
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    GPT_4 = "gpt-4"

class LlmModelName(StrEnum):
    MOCK = "mock"
    OLLAMA_TYNYLLAMA = OllamaModelName.TINYLLAMA
    OLLAMA_LLAMA32 = OllamaModelName.LLAMA32
    OPENAPI_GPT_3_5_TURBO = OpenApiModelName.GPT_3_5_TURBO
    OPENAPI_GPT_4 = OpenApiModelName.GPT_4    

