from pydantic import BaseModel, Field


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
