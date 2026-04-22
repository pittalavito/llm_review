import json

from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field
from pypdf.constants import StrEnum

T = TypeVar("T", bound=BaseModel)


##########################################################
### LLM MODEL NAMES ######################################
##########################################################

class LlmModelName(StrEnum):
    MOCK = "mock"
    # Ollama (local)
    OLLAMA_TINYLLAMA = "tinyllama:1.1b"
    OLLAMA_LLAMA32 = "llama3.2:3b"
    OLLAMA_GROQ_TOOL_USE = "llama3-groq-tool-use"
    OLLAMA_GEMMA_4 = "gemma3:4b"
    # OpenAI
    OPENAI_GPT4O = "gpt-4o"
    OPENAI_GPT4O_MINI = "gpt-4o-mini"
    # Anthropic
    ANTHROPIC_CLAUDE_SONNET = "claude-sonnet-4-6"
    ANTHROPIC_CLAUDE_HAIKU = "claude-haiku-4-5-20251001"

    def is_mock(self) -> bool:
        return self == self.MOCK

    def is_ollama(self) -> bool:
        return self in {
            self.OLLAMA_TINYLLAMA, self.OLLAMA_LLAMA32,
            self.OLLAMA_GROQ_TOOL_USE, self.OLLAMA_GEMMA_4,
        }

    def is_openai(self) -> bool:
        return self in {self.OPENAI_GPT4O, self.OPENAI_GPT4O_MINI}

    def is_anthropic(self) -> bool:
        return self in {self.ANTHROPIC_CLAUDE_SONNET, self.ANTHROPIC_CLAUDE_HAIKU}


#########################################################
### AGENT NAMES #########################################
#########################################################

class AgentName(StrEnum):
    SOUNDNESS_REVIEWER = "soundness_reviewer"
    PRESENTATION_REVIEWER = "presentation_reviewer"
    CONTRIBUTION_REVIEWER = "contribution_reviewer"
    META_REVIEWER = "meta_reviewer"
    AUTHOR_AGENT = "author_agent"


##########################################################
### AGENT STRUCTURED OUTPUT MODEL ########################
##########################################################

class RawResponse(BaseModel):
    """Fallback payload for agents without a structured output schema."""
    response: str


class AgentResponse(BaseModel, Generic[T]):
    agent: AgentName
    payload: T
    input_message: str | None = None
    context_used: str | None = None

    def to_json(self) -> str:
        return self.model_dump_json(ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


##########################################################
### REVIEW RESPONSE MODELS ###############################
##########################################################

class BaseReviewResponse(BaseModel):
    """Common fields shared by all specialized review responses."""
    summary: str = Field(min_length=1, max_length=2_000)
    strengths: list[str] = Field(min_length=1, max_length=10)
    weaknesses: list[str] = Field(min_length=1, max_length=10)
    confidence: int = Field(ge=1, le=5)

class SoundnessReviewResponse(BaseReviewResponse):
    """Evaluates scientific soundness: validity of methods, experimental rigor, and support for conclusions."""
    soundness_score: int = Field(ge=1, le=5)

class PresentationReviewResponse(BaseReviewResponse):
    """Evaluates the clarity, structure, and writing quality of the paper."""
    presentation_score: int = Field(ge=1, le=5)

class ContributionReviewResponse(BaseReviewResponse):
    """Evaluates the originality, relevance, and impact of the scientific contribution."""
    contribution_score: int = Field(ge=1, le=5)


##########################################################
### META REVIEW RESPONSE MODELS ##########################
##########################################################

class ReviewDecision(StrEnum):
    ACCEPT = "accept"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    REJECT = "reject"

class MetaReviewResponse(BaseModel):
    """Aggregates the reviews from the three reviewers and produces the final decision."""
    summary: str = Field(min_length=1, max_length=3_000)
    key_points: list[str] = Field(min_length=1, max_length=10)
    overall_score: int = Field(ge=1, le=5)
    decision: ReviewDecision
    
    
###########################################################
### AUTHOR RESPONSE MODEL #################################
###########################################################

class AuthorResponse(BaseModel):
    """Author's rebuttal and revised paper sections in response to reviewer critiques."""
    rebuttal: str = Field(min_length=1, max_length=2_000)
    revised_sections: dict[str, str] = Field(default_factory=dict)
    key_changes: list[str] = Field(min_length=1, max_length=10)