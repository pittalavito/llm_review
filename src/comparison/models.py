from pydantic import BaseModel


class HumanReview(BaseModel):
    note_id: str
    reviewer_id: str
    summary: str | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    full_text: str | None = None
    rating: int | None = None
    rating_label: str | None = None
    confidence: int | None = None
    confidence_label: str | None = None
    questions: str | None = None


class HumanMetaReview(BaseModel):
    note_id: str
    text: str | None = None
    recommendation: str | None = None


class LLMReview(BaseModel):
    agent: str
    summary: str | None = None
    significance_and_novelty: str | None = None
    reasons_for_acceptance: list[str] = []
    reasons_for_rejection: list[str] = []
    suggestions: list[str] = []
    rating: int | None = None
    confidence: int | None = None


class LLMMetaReview(BaseModel):
    summary: str | None = None
    key_points: list[str] = []
    overall_score: int | None = None
    recommendation: str | None = None


class LLMAreaChair(BaseModel):
    summary: str | None = None
    justification: str | None = None
    decision: str | None = None
    confidence: int | None = None


class ReviewPairComparison(BaseModel):
    index: int
    human: HumanReview | None = None
    llm: LLMReview | None = None
    rating_delta: int | None = None     # llm.rating - human.rating


class PaperComparisonResult(BaseModel):
    run_id: str
    run_description: str | None = None
    llm_decision: str | None = None
    decision_match: bool
    human_review_count: int
    llm_review_count: int
    review_comparisons: list[ReviewPairComparison]
    human_meta_review: HumanMetaReview | None = None
    llm_meta_review: LLMMetaReview | None = None
    llm_area_chair: LLMAreaChair | None = None


class PaperComparison(BaseModel):
    paper_path: str
    title: str
    forum_id: str
    conference: str
    human_decision: str
    human_reviews: list[HumanReview]
    run_comparisons: list[PaperComparisonResult]
