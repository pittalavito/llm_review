"""Import legacy JSON run files into the SQLite database.

Usage:
    uv run python scripts/import-runs.py [--results-dir PATH] [--database-url URL]

Idempotent: already-imported run_ids are skipped, so re-running is safe.
"""
import argparse
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from config import Config, RESULTS_DIR  # noqa: E402
from db.engine import create_db_engine, init_db  # noqa: E402
from db.import_legacy import import_results_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy JSON runs into SQLite.")
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--database-url", default=None,
                        help="Overrides DATABASE_URL (default: resource/db/llm-review.sqlite)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = Config()
    if args.database_url:
        config = config.model_copy(update={"database_url": args.database_url})

    engine = create_db_engine(config)
    init_db(engine)
    report = import_results_dir(engine, args.results_dir)
    print(report)
    if report.failed_files:
        print("failed files:", ", ".join(report.failed_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
