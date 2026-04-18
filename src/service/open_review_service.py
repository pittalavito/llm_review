import json
import logging
from typing import Optional

from clients.paper.open_review_client import OpenReviewClient
from schemas.open_review import PaperSearchResult, PaperSummary
from settings import PAPERS_DIR

logger = logging.getLogger(__name__)

class OpenReviewService:
    
    def __init__(self):
        self._client: OpenReviewClient | None = None
        PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    @property
    def client(self) -> OpenReviewClient:
        if self._client is None:
            self._client = OpenReviewClient()
        return self._client

    def download_paper(self, paper_id: str) -> bool:
        """
        Downloads a complete paper (metadata + review + PDF) and saves it to disk.
        Returns True if the download was successful.
        """
        logger.info("Downloading paper: %s", paper_id)

        # 1. Retrieve submission metadata
        submission = self.client.get_submission(paper_id)
        if not submission:
            logger.warning("Paper %s not found.", paper_id)
            return False

        logger.info("Title: %s", submission.title)

        # 2. Retrieve reviews
        reviews = self.client.get_reviews(paper_id)
        logger.info("Reviews found: %d", len(reviews))

        # 3. Retrieve decision
        decision = self.client.get_decision(paper_id)
        logger.info("Decision: %s", decision.decision if decision else None)

        # 4. Create paper folder
        paper_dir = PAPERS_DIR / paper_id
        paper_dir.mkdir(parents=True, exist_ok=True)

        # 5. Save reviews.json
        data = {
            **submission.model_dump(),
            "decision": decision.decision if decision else None,
            "reviews": [r.model_dump() for r in reviews],
        }
        reviews_path = paper_dir / "reviews.json"
        with open(reviews_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Saved: %s", reviews_path)

        # 6. Download and save PDF
        pdf_bytes = self.client.download_pdf(submission.pdf_path)
        if pdf_bytes:
            pdf_path = paper_dir / "paper.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)
            logger.info("Saved: %s", pdf_path)
        else:
            logger.warning("PDF not available for paper %s.", paper_id)

        return True

    def download_papers(self, paper_ids: list[str]) -> None:
        """Download a list of papers."""
        success = 0
        for paper_id in paper_ids:
            if self.download_paper(paper_id):
                success += 1
        logger.info("Completed: %d/%d papers downloaded.", success, len(paper_ids))

    def get_paper_summary(self, paper_id: str) -> Optional[PaperSummary]:
        """Returns metadata + review ratings + decision for a paper without downloading it."""
        logger.info("Fetching summary for paper: %s", paper_id)
        return self.client.get_paper_summary(paper_id)

    def search_papers(self, keyword: str, venue_id: str, limit: int = 10) -> list[PaperSearchResult]:
        """Search for papers by keyword in a specific venue."""
        logger.info("Searching papers with keyword='%s' venue_id='%s' limit=%d", keyword, venue_id, limit)
        return self.client.search_papers(keyword, venue_id, limit)