from typing import Optional

from pydantic import BaseModel


class PaperSubmission(BaseModel):
    id: str
    title: str
    abstract: str
    keywords: list[str]
    venue: str
    venueid: str
    pdf_path: str


class PaperReview(BaseModel):
    id: str
    date: Optional[int] = None
    summary: str
    strengths: str
    weaknesses: str
    soundness: str
    presentation: str
    contribution: str
    rating: str
    confidence: str
    recommendation: str


class PaperDecision(BaseModel):
    paper_id: str
    decision: Optional[str]


class PaperSearchResult(BaseModel):
    id: str
    title: str
    abstract: str
    keywords: list[str]
    venue: str


class PaperReviewSummary(BaseModel):
    rating: str
    confidence: str
    soundness: str


class PaperSummary(BaseModel):
    id: str
    title: str
    abstract: str
    keywords: list[str]
    venue: str
    venueid: str
    pdf_path: str
    decision: Optional[str]
    num_reviews: int
    review_summary: list[PaperReviewSummary]
