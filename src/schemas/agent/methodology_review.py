from pydantic import BaseModel, Field


class MethodologyReviewResponse(BaseModel):
    summary: str = Field(min_length=1, max_length=2_000)
    strengths: list[str] = Field(min_length=1, max_length=10)
    weaknesses: list[str] = Field(min_length=1, max_length=10)
    reproducibility_score: int = Field(ge=1, le=5)
    confidence: int = Field(ge=1, le=5)
    suggestions: list[str] = Field(min_length=1, max_length=10)
