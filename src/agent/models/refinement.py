from pydantic import BaseModel, Field


class RefinementResponse(BaseModel):
    """Sintetizza le critiche e produce indicazioni concrete per migliorare il paper."""

    revision_summary: str = Field(min_length=1, max_length=2_000)
    priority_changes: list[str] = Field(min_length=1, max_length=10)
    suggested_improvements: list[str] = Field(min_length=1, max_length=10)
