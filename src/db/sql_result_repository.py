"""SQL-backed run persistence.

Same public contract as the legacy file-based ResultRepository (build_run_id,
save, list, get) so the service layer swaps backends without behavioral
changes, plus SQL-side filtering for agent runs.
"""
from __future__ import annotations  # lazy annotations: the list() method shadows builtin list

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from models.agent import AgentName
from models.run_record import AgentRun, RunRecord, RunSummary

from db.mappers import record_to_rows, row_to_agent_run, rows_to_record
from db.tables import AgentRunTable, RunTable

logger = logging.getLogger(__name__)


class SqlResultRepository:

    def __init__(self, engine: Engine):
        self._engine = engine

    # ------------------------------------------------------------------
    # Public API (legacy-compatible)
    # ------------------------------------------------------------------

    @staticmethod
    def build_run_id(paper_path: str) -> str:
        """Build a run_id from current timestamp and paper filename."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        stem = Path(paper_path).stem
        safe = re.sub(r"[^\w\-]", "_", stem)[:40]
        return f"{ts}_{safe}"

    def save(self, record: RunRecord) -> str:
        """Persist a RunRecord transactionally. Returns the run_id.

        Saving an existing run_id replaces it (run_id has 1-second
        resolution and the legacy file store silently overwrote)."""
        run_row, agent_rows, config_rows = record_to_rows(record)
        with Session(self._engine) as session:
            existing = session.get(RunTable, record.run_id)
            if existing is not None:
                session.delete(existing)  # children removed by FK cascade
                session.flush()
            session.add(run_row)
            # No ORM relationships between the tables: flush the parent first
            # so the children's FK sees it.
            session.flush()
            session.add_all(agent_rows)
            session.add_all(config_rows)
            session.commit()
        logger.info("Run saved: %s", record.run_id)
        return record.run_id

    def list(self) -> list[RunSummary]:
        """Return all run summaries, most recent first.

        Ordered by run_id (== legacy filename ordering); only summary
        columns are read, no JSON payloads."""
        statement = select(
            RunTable.run_id,
            RunTable.timestamp,
            RunTable.paper_path,
            RunTable.run_description,
            RunTable.decision,
            RunTable.total_rounds,
        ).order_by(RunTable.run_id.desc())
        with Session(self._engine) as session:
            rows = session.exec(statement).all()
        return [
            RunSummary(
                run_id=row.run_id,
                timestamp=row.timestamp,
                paper_path=row.paper_path,
                run_description=row.run_description,
                decision=row.decision,
                total_rounds=row.total_rounds,
            )
            for row in rows
        ]

    def get(self, run_id: str) -> RunRecord:
        """Load a full RunRecord by run_id. Raises ValueError if not found."""
        with Session(self._engine) as session:
            run_row = session.get(RunTable, run_id)
            if run_row is None:
                raise ValueError(f"Run not found: {run_id}")
            agent_rows = session.exec(
                select(AgentRunTable)
                .where(AgentRunTable.run_id == run_id)
                .order_by(AgentRunTable.id)
            ).all()
            return rows_to_record(run_row, list(agent_rows))

    def get_agent_runs(
        self,
        run_id: str,
        agent_name: AgentName | None = None,
        round_index: int | None = None,
    ) -> list[AgentRun]:
        """Agent traces for a run, filtered in SQL. Raises ValueError if the
        run does not exist."""
        with Session(self._engine) as session:
            if session.get(RunTable, run_id) is None:
                raise ValueError(f"Run not found: {run_id}")
            statement = select(AgentRunTable).where(AgentRunTable.run_id == run_id)
            if agent_name is not None:
                statement = statement.where(AgentRunTable.agent == str(agent_name))
            if round_index is not None:
                statement = statement.where(AgentRunTable.round == round_index)
            rows = session.exec(statement.order_by(AgentRunTable.id)).all()
            return [row_to_agent_run(row) for row in rows]
