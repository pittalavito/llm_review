import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from models.run_record import RunRecord, RunSummary

logger = logging.getLogger(__name__)

_FILENAME_RE = re.compile(r"^[\w\-\.]+\.json$")


class ResultRepository:

    def __init__(self, results_dir: Path):
        self._dir = results_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def build_run_id(paper_path: str) -> str:
        """Build a run_id from current timestamp and paper filename."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        stem = Path(paper_path).stem
        safe = re.sub(r"[^\w\-]", "_", stem)[:40]
        return f"{ts}_{safe}"

    def save(self, record: RunRecord) -> str:
        """Persist a RunRecord as JSON. Returns the filename."""
        filename = f"{record.run_id}.json"
        path = self._dir / filename
        path.write_text(record.model_dump_json(indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Run saved: %s", filename)
        return filename

    def list(self) -> list[RunSummary]:
        """Return all run summaries sorted by timestamp descending."""
        summaries = []
        for path in sorted(self._dir.glob("*.json"), reverse=True):
            if not _FILENAME_RE.match(path.name):
                continue
            try:
                record = self._load_record(path)
                summaries.append(RunSummary(
                    run_id=record.run_id,
                    timestamp=record.timestamp,
                    paper_path=record.paper_path,
                    run_description=record.run_description,
                    decision=record.decision,
                    total_rounds=record.total_rounds,
                ))
            except Exception:
                logger.warning("Skipping corrupt run file: %s", path.name)
        return summaries

    def get(self, run_id: str) -> RunRecord:
        """Load a full RunRecord by run_id. Raises ValueError if not found."""
        path = self._dir / f"{run_id}.json"
        if not path.exists():
            raise ValueError(f"Run not found: {run_id}")
        return self._load_record(path)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _load_record(self, path: Path) -> RunRecord:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RunRecord.model_validate(data)
