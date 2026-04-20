import json

from typing import Any
from pydantic import BaseModel, Field
from pypdf.constants import StrEnum


##########################################################
### LLM MODEL NAMES ######################################
##########################################################

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


#########################################################
### AGENT NAMES #########################################
#########################################################

class AgentName(StrEnum):
    SOUNDNESS_REVIEWER = "soundness_reviewer"
    PRESENTATION_REVIEWER = "presentation_reviewer"
    CONTRIBUTION_REVIEWER = "contribution_reviewer"
    META_REVIEWER = "meta_reviewer"
    REFINEMENT_AGENT = "refinement_agent"


##########################################################
### AGENT STRUCTURED OUTPUT MODEL ########################
##########################################################

class AgentResponse(BaseModel):
    agent: AgentName
    payload: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, raw: str) -> "AgentResponse":
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Agent returned invalid JSON: {exc}") from exc
        try:
            return cls.model_validate(data)
        except Exception as exc:
            raise ValueError(f"Agent output does not match schema: {exc}") from exc


##########################################################
### REVIEW RESPONSE MODELS ###############################
##########################################################

class BaseReviewResponse(BaseModel):
    """Campi comuni a tutte le review specializzate."""
    summary: str = Field(min_length=1, max_length=2_000)
    strengths: list[str] = Field(min_length=1, max_length=10)
    weaknesses: list[str] = Field(min_length=1, max_length=10)
    confidence: int = Field(ge=1, le=5)

class SoundnessReviewResponse(BaseReviewResponse):
    """Valuta la solidità scientifica: validità dei metodi, rigore sperimentale, supporto delle conclusioni."""
    soundness_score: int = Field(ge=1, le=5)

class PresentationReviewResponse(BaseReviewResponse):
    """Valuta chiarezza, struttura e qualità della scrittura del paper."""
    presentation_score: int = Field(ge=1, le=5)

class ContributionReviewResponse(BaseReviewResponse):
    """Valuta originalità, rilevanza e impatto del contributo scientifico."""
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
    """Aggrega le review dei tre reviewer e produce la decisione finale."""
    summary: str = Field(min_length=1, max_length=3_000)
    key_points: list[str] = Field(min_length=1, max_length=10)
    overall_score: int = Field(ge=1, le=5)
    decision: ReviewDecision
    
    
###########################################################
### REFINEMENT RESPONSE MODEL #############################
###########################################################

class RefinementResponse(BaseModel):
    """Sintetizza le critiche e produce indicazioni concrete per migliorare il paper."""
    revision_summary: str = Field(min_length=1, max_length=2_000)
    priority_changes: list[str] = Field(min_length=1, max_length=10)
    suggested_improvements: list[str] = Field(min_length=1, max_length=10)