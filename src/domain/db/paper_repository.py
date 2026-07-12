"""Repository for the paper catalog.

The DB is the source of truth for the paper list at runtime. Rows are seeded
(idempotently) from resource/papers/ + open-review-index.json — the JSON is a
seed-only source now, not read at runtime. num_review reflects the number of
runs recorded for the paper (counted live from the run table on read).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from domain.db.tables import PaperTable, RunTable
from models.paper import Paper, PaperType

logger = logging.getLogger(__name__)

_PAPER_EXTENSIONS = {".pdf", ".txt"}


class PaperRepository:

    def __init__(self, engine: Engine):
        self._engine = engine

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def list(self) -> list[Paper]:
        """All papers, ordered by path, with a live run count as num_review."""
        with Session(self._engine) as session:
            rows = session.exec(select(PaperTable).order_by(PaperTable.paper_path)).all()
            counts = self._run_counts(session)
        return [self._to_model(row, counts.get(row.paper_path, 0)) for row in rows]

    def list_paths(self) -> list[str]:
        """Paper paths only (used by RetrievalService.list_papers)."""
        with Session(self._engine) as session:
            return list(
                session.exec(select(PaperTable.paper_path).order_by(PaperTable.paper_path)).all()
            )

    def list_openreview(self) -> list[Paper]:
        """OpenReview papers only (used by the comparator's paper list)."""
        with Session(self._engine) as session:
            rows = session.exec(
                select(PaperTable)
                .where(PaperTable.paper_type == PaperType.OPEN_REVIEW.value)
                .order_by(PaperTable.paper_path)
            ).all()
            counts = self._run_counts(session)
        return [self._to_model(row, counts.get(row.paper_path, 0)) for row in rows]

    def get_by_path(self, paper_path: str) -> Paper:
        """Raises ValueError if the paper is not in the catalog."""
        with Session(self._engine) as session:
            row = session.exec(
                select(PaperTable).where(PaperTable.paper_path == paper_path)
            ).first()
            if row is None:
                raise ValueError(f"Paper not found: {paper_path}")
            count = self._run_counts(session).get(paper_path, 0)
        return self._to_model(row, count)

    # ------------------------------------------------------------------
    # Seed
    # ------------------------------------------------------------------

    def seed_from_sources(self, papers_dir: Path, index_path: Path) -> int:
        """Idempotently populate the catalog from the papers folder and the
        OpenReview index. Inserts missing papers, refreshes num_review and the
        derived metadata on existing ones. Returns the number inserted."""
        index_by_stem = self._load_index(index_path)
        inserted = 0
        with Session(self._engine) as session:
            existing = {
                row.paper_path: row
                for row in session.exec(select(PaperTable)).all()
            }
            counts = self._run_counts(session)
            for paper_path in self._scan_papers(papers_dir):
                entry = index_by_stem.get(Path(paper_path).stem)
                fields = self._fields_from(paper_path, entry, counts.get(paper_path, 0))
                row = existing.get(paper_path)
                if row is None:
                    session.add(PaperTable(**fields))
                    inserted += 1
                else:
                    for key, value in fields.items():
                        setattr(row, key, value)
                    session.add(row)
            session.commit()
        if inserted:
            logger.info("Paper catalog seeded: %d new paper(s)", inserted)
        return inserted

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _fields_from(paper_path: str, entry: dict | None, run_count: int) -> dict:
        if entry is not None:
            return {
                "paper_path": paper_path,
                "paper_name": entry.get("title") or Path(paper_path).stem,
                "paper_type": PaperType.OPEN_REVIEW.value,
                "open_review_id": entry.get("openreview_forum_id"),
                "conference": entry.get("conference"),
                "openreview_api_version": entry.get("openreview_api_version", "v1"),
                "decision": entry.get("decision"),
                "num_review": run_count,
            }
        return {
            "paper_path": paper_path,
            "paper_name": Path(paper_path).stem,
            "paper_type": PaperType.OTHER.value,
            "open_review_id": None,
            "conference": None,
            "openreview_api_version": None,
            "decision": None,
            "num_review": run_count,
        }

    @staticmethod
    def _scan_papers(papers_dir: Path) -> list[str]:
        papers_dir = papers_dir.resolve()
        return sorted(
            f.relative_to(papers_dir).as_posix()
            for f in papers_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in _PAPER_EXTENSIONS
        )

    @staticmethod
    def _load_index(index_path: Path) -> dict[str, dict]:
        if not index_path.exists():
            return {}
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        return {e["paper_path"]: e for e in entries if e.get("paper_path")}

    @staticmethod
    def _run_counts(session: Session) -> dict[str, int]:
        rows = session.exec(
            select(RunTable.paper_path, func.count()).group_by(RunTable.paper_path)
        ).all()
        return {paper_path: count for paper_path, count in rows}

    @staticmethod
    def _to_model(row: PaperTable, num_review: int) -> Paper:
        return Paper(
            id=row.id,
            paper_path=row.paper_path,
            paper_name=row.paper_name,
            paper_type=PaperType(row.paper_type),
            open_review_id=row.open_review_id,
            conference=row.conference,
            openreview_api_version=row.openreview_api_version,
            decision=row.decision,
            num_review=num_review,
        )
