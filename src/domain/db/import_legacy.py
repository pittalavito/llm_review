"""One-time import of legacy JSON run files into the SQL database.

Idempotent: run_ids already present in the database are skipped, so the
import can be re-run safely. A malformed file is counted as failed and
logged, never aborting the batch.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from models.run_record import RunRecord

from domain.db.mappers import record_to_rows
from domain.db.tables import RunTable

logger = logging.getLogger(__name__)


@dataclass
class ImportReport:
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    failed_files: list[str] = field(default_factory=list)
    def __str__(self) -> str:
        return f"imported={self.imported} skipped={self.skipped} failed={self.failed}"


def import_results_dir(engine: Engine, results_dir: Path) -> ImportReport:
    """Import every *.json RunRecord under results_dir into the database."""
    
    report = ImportReport()
    
    with Session(engine) as session:
        existing = set(session.exec(select(RunTable.run_id)).all())
        for path in sorted(results_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                record = RunRecord.model_validate(data)
            except Exception:
                logger.warning("Skipping corrupt run file: %s", path.name)
                report.failed += 1
                report.failed_files.append(path.name)
                continue
            if record.run_id in existing:
                report.skipped += 1
                continue
            run_row, agent_rows, config_rows = record_to_rows(record)
            session.add(run_row)
            session.flush() 
            session.add_all(agent_rows)
            session.add_all(config_rows)
            existing.add(record.run_id)
            report.imported += 1
        session.commit()
    logger.info("Legacy import from %s: %s", results_dir, report)
    return report
