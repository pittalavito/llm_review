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
    OLLAMA_GEMMA_4 = "gemma4"
    OLLAMA_GEMMA_3_4B = "gemma3:4b"
    OLLAMA_MISTRAL_7B = "mistral:7b"
    
    # Aitho (cloud)
    AITHO_QWEN_3_6 = "qwen3.6:27b"
    
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
            self.OLLAMA_TINYLLAMA, 
            self.OLLAMA_LLAMA32,
            self.OLLAMA_GROQ_TOOL_USE, 
            self.OLLAMA_GEMMA_4, 
            self.OLLAMA_GEMMA_3_4B,
            self.OLLAMA_MISTRAL_7B
        }

    def is_openai(self) -> bool:
        return self in {
            self.OPENAI_GPT4O, 
            self.OPENAI_GPT4O_MINI
        }

    def is_anthropic(self) -> bool:
        return self in {
            self.ANTHROPIC_CLAUDE_SONNET, 
            self.ANTHROPIC_CLAUDE_HAIKU
        }
    
    def is_aitho(self) -> bool:
        return self == self.AITHO_QWEN_3_6

#########################################################
### AGENT ROLES #########################################
#########################################################

class AgentRole(StrEnum):
    REVIEWER = "reviewer"
    META_REVIEWER = "meta_reviewer"
    AREA_CHAIR = "area_chair"
    AUTHOR_AGENT = "author_agent"


#########################################################
### AGENT NAMES #########################################
#########################################################

class AgentName(StrEnum):
    REVIEWER_1 = "reviewer_1"
    REVIEWER_2 = "reviewer_2"
    REVIEWER_3 = "reviewer_3"
    META_REVIEWER = "meta_reviewer"
    AREA_CHAIR = "area_chair"
    AUTHOR_AGENT = "author_agent"

    def role(self) -> str:
        """Prompt-versioning role: the three reviewers share one base template."""
        
        if str(self).startswith("reviewer_"):
            return "reviewer"
        return str(self)


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
    prompt_trace: dict[str, Any] | None = None
    runtime_trace: dict[str, Any] | None = None

    def to_json(self) -> str:
        return self.model_dump_json(ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


##########################################################
### REVIEWER FOCUS #######################################
##########################################################

class ReviewerFocus(StrEnum):
    """Primary evaluation angle assigned to a reviewer.
    Each reviewer covers a different dimension of the paper so that
    the three reviews are complementary rather than redundant.
    """
    
    SOUNDNESS = "soundness"   # theoretical correctness, proofs, assumptions
    EMPIRICAL = "empirical"  # experiments, baselines, reproducibility
    NOVELTY = "novelty"    # originality, related work, impact


##########################################################
### REVIEWER PERSONA #####################################
##########################################################

class ReviewerCommitment(StrEnum):
    RESPONSIBLE = "responsible"
    IRRESPONSIBLE = "irresponsible"

class ReviewerIntention(StrEnum):
    BENIGN = "benign"
    MALICIOUS = "malicious"

class ReviewerKnowledgeability(StrEnum):
    KNOWLEDGEABLE = "knowledgeable"
    UNKNOWLEDGEABLE = "unknowledgeable"

class ReviewerPersona(BaseModel):
    commitment: ReviewerCommitment = ReviewerCommitment.RESPONSIBLE
    intention: ReviewerIntention = ReviewerIntention.BENIGN
    knowledgeability: ReviewerKnowledgeability = ReviewerKnowledgeability.KNOWLEDGEABLE
    focus: ReviewerFocus = ReviewerFocus.SOUNDNESS


##########################################################
### REVIEWER RESPONSE MODEL (aligned with AgentReview) ###
##########################################################

class ReviewerResponse(BaseModel):
    """Unified review aligned with AgentReview format: covers soundness, novelty, presentation, and impact."""
    
    summary: str = Field(min_length=1, max_length=600)
    significance_and_novelty: str = Field(min_length=1, max_length=300)
    reasons_for_acceptance: list[str] = Field(min_length=1, max_length=4)
    reasons_for_rejection: list[str] = Field(default_factory=list, max_length=4)
    suggestions: list[str] = Field(default_factory=list, max_length=4)
    rating: int = Field(ge=1, le=10)
    confidence: int = Field(ge=1, le=5)


##########################################################
### META REVIEW RESPONSE MODELS ##########################
##########################################################

class ReviewDecision(StrEnum):
    ACCEPT = "accept"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    REJECT = "reject"

class MetaReviewResponse(BaseModel):
    """Aggregates the three reviews into a summary and recommendation for the Area Chair."""
    
    summary: str = Field(min_length=1, max_length=600)
    key_points: list[str] = Field(min_length=1, max_length=5)
    overall_score: int = Field(ge=1, le=10)
    recommendation: ReviewDecision


##########################################################
### AREA CHAIR MODELS ####################################
##########################################################

class AreaChairStyle(StrEnum):
    AUTHORITARIAN = "authoritarian"
    CONFORMIST = "conformist"
    INCLUSIVE = "inclusive"

class AreaChairResponse(BaseModel):
    """Final binding decision produced by the Area Chair after reading reviews and meta-review."""
    
    summary: str = Field(min_length=1, max_length=400)
    justification: str = Field(min_length=1, max_length=400)
    decision: ReviewDecision
    confidence: int = Field(ge=1, le=5)


###########################################################
### AUTHOR RESPONSE MODEL #################################
###########################################################

class RevisedSection(BaseModel):
    """A single revised paper section produced by the author."""
    
    section_name: str
    content: str

class ReviewerRebuttal(BaseModel):
    """Targeted rebuttal addressed to a specific reviewer."""
    
    reviewer_name: str  # e.g. "reviewer_1"
    response: str = Field(min_length=1, max_length=1_000)

class AuthorResponse(BaseModel):
    """Author's rebuttal, per-reviewer targeted responses, and revised paper sections."""
    
    rebuttal: str = Field(min_length=1, max_length=600)
    reviewer_rebuttals: list[ReviewerRebuttal] = Field(default_factory=list)
    revised_sections: list[RevisedSection] = Field(default_factory=list, max_length=3)
    key_changes: list[str] = Field(min_length=1, max_length=5)