"""Import legacy JSON run files into the SQLite database.

Usage:
    uv run python resource/scripts/import-runs.py [--results-dir PATH] [--database-url URL]

Idempotent: already-imported run_ids are skipped, so re-running is safe.
"""
import argparse
import logging
import sys
from pathlib import Path

from _env import PROJECT_ROOT

# The domain code lives under src/ (imported as top-level packages).
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config import Config, RESOURCE_DIR  # noqa: E402
from domain.db.engine import create_db_engine  # noqa: E402
from domain.db.import_legacy import import_results_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Import legacy JSON runs into SQLite.")
    parser.add_argument("--results-dir", type=Path, default=RESOURCE_DIR / "results")
    parser.add_argument("--database-url", default=None,
                        help="Overrides DATABASE_URL (default: resource/db/llm-review.sqlite)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    config = Config()
    if args.database_url:
        config = config.model_copy(update={"database_url": args.database_url})

    engine = create_db_engine(config)
    report = import_results_dir(engine, args.results_dir)
    print(report)
    if report.failed_files:
        print("failed files:", ", ".join(report.failed_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
