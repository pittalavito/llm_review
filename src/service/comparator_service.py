import json
import logging

from pathlib import Path

from domain.db.result_repository import ResultRepository

from models.agent import AgentName
from models.comparator import LLMAreaChair, LLMMetaReview, LLMReview, PaperComparison, PaperComparisonResult

from domain.comparator.openreview_client import OpenReviewClient
from domain.comparator.human_review_parser import HumanReviewParser

logger = logging.getLogger(__name__)

_REVIEWER_AGENTS = {AgentName.REVIEWER_1, AgentName.REVIEWER_2, AgentName.REVIEWER_3}
_ACCEPT_KW = {"accept"}
_REJECT_KW = {"reject"}


class ReviewComparatorService:

    def __init__(self, result_repository: ResultRepository, index_path: Path, cache_dir: Path | None = None):
        self._repo = result_repository
        self._index: list[dict] = json.loads(index_path.read_text(encoding="utf-8"))
        self._client = OpenReviewClient(cache_dir=cache_dir)
        self._parser = HumanReviewParser()

    def list_papers(self) -> list[dict]:
        """List all papers in the index with their title and conference."""
        
        return [
            {
                "paper_path": e["paper_path"], 
                "title": e.get("title", ""), 
                "conference": e.get("conference", "")
            }
            for e in self._index
        ]

    def compare_paper(self, paper_path: str) -> PaperComparison:
        entry = self._find_entry(paper_path)
        forum_id: str = entry["openreview_forum_id"]
        api_version: str = entry.get("openreview_api_version", "v1")

        notes = self._client.fetch_notes(forum_id, api_version, cache_name=paper_path)
        human_reviews = self._parser.parse_reviews(notes)
        human_meta = self._parser.parse_meta_review(notes)
        human_decision: str = entry.get("decision") or self._parser.parse_decision(notes) or "unknown"

        run_comparisons: list[PaperComparisonResult] = []
        for run_ref in entry.get("runs_system_promt_v1", []):
            run_id: str = run_ref["run_id"]
            try:
                record = self._repo.get(run_id)
            except ValueError:
                logger.warning("Run not found on disk: %s", run_id)
                continue

            llm_reviews = self._extract_llm_reviews(record)
            llm_meta = self._extract_llm_meta(record)
            llm_ac = self._extract_llm_ac(record)

            run_comparisons.append(PaperComparisonResult(
                run_id=run_id,
                run_description=record.run_description,
                llm_decision=record.decision,
                decision_match=self._decisions_match(human_decision, record.decision),
                human_review_count=len(human_reviews),
                llm_review_count=len(llm_reviews),
                llm_reviews=llm_reviews,
                human_meta_review=human_meta,
                llm_meta_review=llm_meta,
                llm_area_chair=llm_ac,
            ))

        return PaperComparison(
            paper_path=paper_path,
            title=entry.get("title", ""),
            forum_id=forum_id,
            conference=entry.get("conference", ""),
            human_decision=human_decision,
            human_reviews=human_reviews,
            run_comparisons=run_comparisons,
        )

    def _find_entry(self, paper_path: str) -> dict:
        for entry in self._index:
            if entry["paper_path"] == paper_path:
                return entry
        raise ValueError(f"Paper not found in index: {paper_path}")

    def _extract_llm_reviews(self, record) -> list[LLMReview]:
        reviews = []
        for agent_run in record.agent_runs:
            if agent_run.agent not in _REVIEWER_AGENTS:
                continue
            p = agent_run.response_payload
            reviews.append(LLMReview(
                agent=agent_run.agent,
                summary=p.get("summary"),
                significance_and_novelty=p.get("significance_and_novelty"),
                reasons_for_acceptance=p.get("reasons_for_acceptance", []),
                reasons_for_rejection=p.get("reasons_for_rejection", []),
                suggestions=p.get("suggestions", []),
                rating=p.get("rating"),
                confidence=p.get("confidence"),
            ))
        return reviews

    def _extract_llm_meta(self, record) -> LLMMetaReview | None:
        m = record.meta_review
        if not m:
            return None
        return LLMMetaReview(
            summary=m.get("summary"),
            key_points=m.get("key_points", []),
            overall_score=m.get("overall_score"),
            recommendation=m.get("recommendation"),
        )

    def _extract_llm_ac(self, record) -> LLMAreaChair | None:
        ac = record.area_chair_response
        if not ac:
            return None
        return LLMAreaChair(
            summary=ac.get("summary"),
            justification=ac.get("justification"),
            decision=ac.get("decision"),
            confidence=ac.get("confidence"),
        )

    @staticmethod
    def _decisions_match(human: str, llm: str | None) -> bool:
        if not llm:
            return False
        h_accept = any(k in human.lower() for k in _ACCEPT_KW)
        l_accept = any(k in llm.lower() for k in _ACCEPT_KW)
        return h_accept == l_accept
