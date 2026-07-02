import re
import logging

from comparison.models import HumanReview, HumanMetaReview

logger = logging.getLogger(__name__)

_REVIEW_KW = {"official_review", "official review"}
_META_KW = {"meta_review", "meta review", "metareview"}
_DECISION_KW = {"decision"}


def _extract_int(value: object) -> int | None:
    """Extract leading integer from strings like '6: marginally above...'"""
    if value is None:
        return None
    m = re.match(r"(\d+)", str(value).strip())
    return int(m.group(1)) if m else None


def _get(content: dict, *keys: str) -> str | None:
    for k in keys:
        v = content.get(k)
        if v:
            return v if isinstance(v, str) else str(v)
    return None


def _unwrap(content: dict) -> dict:
    """OpenReview v2 wraps each field as {"value": ...}."""
    return {
        k: (v["value"] if isinstance(v, dict) and "value" in v else v)
        for k, v in content.items()
    }


class HumanReviewParser:

    def parse_reviews(self, notes: list[dict]) -> list[HumanReview]:
        reviews = []
        for note in notes:
            invitation = (note.get("invitation") or "").lower()
            if not any(kw in invitation for kw in _REVIEW_KW):
                continue
            c = _unwrap(note.get("content", {}))
            rating_raw = _get(c, "rating", "recommendation")
            conf_raw = _get(c, "confidence")
            reviews.append(HumanReview(
                note_id=note.get("id", ""),
                reviewer_id=str((note.get("signatures") or ["?"])[0]).split("/")[-1],
                summary=_get(c, "summary_of_the_paper", "summary"),
                strengths=_get(c, "strengths", "strength_and_weaknesses", "strengths_and_weaknesses"),
                weaknesses=_get(c, "weaknesses"),
                full_text=_get(c, "review", "main_review"),
                rating=_extract_int(rating_raw),
                rating_label=rating_raw,
                confidence=_extract_int(conf_raw),
                confidence_label=conf_raw,
                questions=_get(c, "questions", "summary_of_the_review"),
            ))
        return reviews

    def parse_meta_review(self, notes: list[dict]) -> HumanMetaReview | None:
        for note in notes:
            invitation = (note.get("invitation") or "").lower()
            if not any(kw in invitation for kw in _META_KW):
                continue
            c = _unwrap(note.get("content", {}))
            return HumanMetaReview(
                note_id=note.get("id", ""),
                text=_get(c, "metareview", "meta_review", "comment", "summary"),
                recommendation=_get(c, "recommendation", "decision"),
            )
        return None

    def parse_decision(self, notes: list[dict]) -> str | None:
        for note in notes:
            invitation = (note.get("invitation") or "").lower()
            if not any(kw in invitation for kw in _DECISION_KW):
                continue
            c = _unwrap(note.get("content", {}))
            dec = _get(c, "decision", "recommendation")
            if dec:
                return dec
        return None
