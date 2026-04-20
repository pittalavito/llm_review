from pydantic import BaseModel, Field

from agent.models.enums import ReviewDecision


class MetaReviewResponse(BaseModel):
    """Aggrega le review dei tre reviewer e produce la decisione finale."""

    summary: str = Field(min_length=1, max_length=3_000)
    key_points: list[str] = Field(min_length=1, max_length=10)
    overall_score: int = Field(ge=1, le=5)
    decision: ReviewDecision
