import logging
import openreview
import requests

from typing import Optional
from adapter.open_review_adapter import OpenReviewAdapter
from schemas.open_review import PaperDecision, PaperReview, PaperSearchResult, PaperSubmission, PaperSummary

logger = logging.getLogger(__name__)


class OpenReviewClient:
    BASE_URL = "https://api2.openreview.net"
    PDF_BASE_URL = "https://openreview.net"
    USERNAME = "your_username"
    PASSWORD = "ciAomammaguard4come126$"

    def __init__(self):
        self.client = openreview.api.OpenReviewClient(
            baseurl=self.BASE_URL,
            username=self.USERNAME,
            password=self.PASSWORD
        )

    def get_submission(self, paper_id: str) -> Optional[PaperSubmission]:
        """Retrieves the metadata of a paper given its ID."""
        try:
            note = self.client.get_note(paper_id)
            return OpenReviewAdapter.to_submission(paper_id, note.content)
        except Exception as e:
            logger.error("Error retrieving paper %s: %s", paper_id, e)
            return None

    def get_reviews(self, paper_id: str) -> list[PaperReview]:
        """Retrieves all public reviews of a paper."""
        try:
            notes = self.client.get_all_notes(forum=paper_id)
            reviews = []
            for note in notes:
                content = note.content
                if any(k in content for k in ["summary", "soundness", "review", "rating"]):
                    reviews.append(OpenReviewAdapter.to_review(note.id, note.cdate, content))
            return reviews
        except Exception as e:
            logger.error("Error retrieving reviews for %s: %s", paper_id, e)
            return []

    def get_decision(self, paper_id: str) -> Optional[PaperDecision]:
        """Retrieves the final decision (accept/reject)."""
        try:
            notes = self.client.get_all_notes(forum=paper_id)
            for note in notes:
                content = note.content
                if "decision" in content:
                    return OpenReviewAdapter.to_decision(paper_id, content)
            return None
        except Exception as e:
            logger.error("Error retrieving decision for %s: %s", paper_id, e)
            return None

    def get_paper_summary(self, paper_id: str) -> Optional[PaperSummary]:
        """Returns metadata + review ratings + decision without downloading anything."""
        try:
            submission = self.get_submission(paper_id)
            if not submission:
                return None

            reviews = self.get_reviews(paper_id)
            decision = self.get_decision(paper_id)
            return OpenReviewAdapter.to_summary(submission, decision, reviews)
        except Exception as e:
            logger.error("Error getting summary for %s: %s", paper_id, e)
            return None

    def search_papers(self, keyword: str, venue_id: str, limit: int = 10) -> list[PaperSearchResult]:
        """Search for papers by keyword in a specific venue."""
        normalized_keyword = keyword.strip()
        normalized_venue = venue_id.strip()
        if not normalized_keyword or not normalized_venue:
            logger.warning("Skipping search because keyword or venue_id is empty")
            return []
        inv = 'ICLR.cc/2024/Conference/-/Submission';
        try:
            notes = self.client.get_all_notes(content={'venueid': 'NeurIPS.cc/2023/Conference'})

                #invitation='ICLR.cc/2024/Conference/-/Submission')
            #self.client.get_all_notes(
                #content={"keywords": normalized_keyword},
                #invitation=f"{normalized_venue}/-/Submission",
                #limit=limit,
#            )
            return [OpenReviewAdapter.to_search_result(note.id, note.content) for note in notes]
        except Exception as e:
            logger.error("Error searching papers with keyword '%s': %s", normalized_keyword, e)
            return []

    def download_pdf(self, pdf_path: str) -> Optional[bytes]:
        """Downloads the PDF of the paper given the relative path."""
        if not pdf_path:
            return None
        try:
            url = f"{self.PDF_BASE_URL}{pdf_path}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error("Error downloading PDF %s: %s", pdf_path, e)
            return None