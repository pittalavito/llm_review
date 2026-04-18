from typing import Any, Optional

from schemas.open_review import (
    PaperDecision,
    PaperReview,
    PaperReviewSummary,
    PaperSearchResult,
    PaperSubmission,
    PaperSummary,
)


class OpenReviewAdapter:
    @staticmethod
    def to_submission(paper_id: str, content: dict[str, Any]) -> PaperSubmission:
        return PaperSubmission(
            id=paper_id,
            title=content.get("title", {}).get("value", ""),
            abstract=content.get("abstract", {}).get("value", ""),
            keywords=content.get("keywords", {}).get("value", []),
            venue=content.get("venue", {}).get("value", ""),
            venueid=content.get("venueid", {}).get("value", ""),
            pdf_path=content.get("pdf", {}).get("value", ""),
        )

    @staticmethod
    def to_review(note_id: str, cdate: Optional[int], content: dict[str, Any]) -> PaperReview:
        return PaperReview(
            id=note_id,
            date=cdate,
            summary=content.get("summary", {}).get("value", ""),
            strengths=content.get("strengths", {}).get("value", ""),
            weaknesses=content.get("weaknesses", {}).get("value", ""),
            soundness=content.get("soundness", {}).get("value", ""),
            presentation=content.get("presentation", {}).get("value", ""),
            contribution=content.get("contribution", {}).get("value", ""),
            rating=content.get("rating", {}).get("value", ""),
            confidence=content.get("confidence", {}).get("value", ""),
            recommendation=content.get("recommendation", {}).get("value", ""),
        )

    @staticmethod
    def to_decision(paper_id: str, content: dict[str, Any]) -> PaperDecision:
        return PaperDecision(
            paper_id=paper_id,
            decision=content.get("decision", {}).get("value", ""),
        )

    @staticmethod
    def to_search_result(note_id: str, content: dict[str, Any]) -> PaperSearchResult:
        return PaperSearchResult(
            id=note_id,
            title=content.get("title", {}).get("value", ""),
            abstract=content.get("abstract", {}).get("value", ""),
            keywords=content.get("keywords", {}).get("value", []),
            venue=content.get("venue", {}).get("value", ""),
        )

    @staticmethod
    def to_review_summary(review: PaperReview) -> PaperReviewSummary:
        return PaperReviewSummary(
            rating=review.rating,
            confidence=review.confidence,
            soundness=review.soundness,
        )

    @staticmethod
    def to_summary(
        submission: PaperSubmission,
        decision: Optional[PaperDecision],
        reviews: list[PaperReview],
    ) -> PaperSummary:
        return PaperSummary(
            id=submission.id,
            title=submission.title,
            abstract=submission.abstract,
            keywords=submission.keywords,
            venue=submission.venue,
            venueid=submission.venueid,
            pdf_path=submission.pdf_path,
            decision=decision.decision if decision else None,
            num_reviews=len(reviews),
            review_summary=[OpenReviewAdapter.to_review_summary(review) for review in reviews],
        )
