from enum import StrEnum


class LlmModelName(StrEnum):
    MOCK = "mock"
    OLLAMA_TINYLLAMA = "tinyllama:1.1b"
    OLLAMA_LLAMA32 = "llama3.2:3b"
    OLLAMA_GROQ_TOOL_USE = "llama3-groq-tool-use"
    OLLAMA_GEMMA_4 = "gemma4"

    def is_ollama(self) -> bool:
        return self in {self.OLLAMA_TINYLLAMA, self.OLLAMA_LLAMA32, self.OLLAMA_GROQ_TOOL_USE, self.OLLAMA_GEMMA_4}

    def is_mock(self) -> bool:
        return self == self.MOCK


class AgentName(StrEnum):
    SOUNDNESS_REVIEWER = "soundness_reviewer"
    PRESENTATION_REVIEWER = "presentation_reviewer"
    CONTRIBUTION_REVIEWER = "contribution_reviewer"
    META_REVIEWER = "meta_reviewer"
    REFINEMENT_AGENT = "refinement_agent"


class ReviewDecision(StrEnum):
    ACCEPT = "accept"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    REJECT = "reject"