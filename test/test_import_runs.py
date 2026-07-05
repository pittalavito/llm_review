"""
Legacy JSON import tests:
  - imports every valid file from a results dir
  - idempotent: second run skips everything
  - corrupt files counted as failed without aborting the batch
"""
import json

import pytest

from config import Config
from db.engine import create_db_engine, init_db
from db.import_legacy import import_results_dir
from db.sql_result_repository import SqlResultRepository

from test_db_repository import make_record


@pytest.fixture()
def engine(tmp_path):
    config = Config(database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    engine = create_db_engine(config)
    init_db(engine)
    return engine


@pytest.fixture()
def results_dir(tmp_path):
    directory = tmp_path / "results"
    directory.mkdir()
    for run_id in ("2026-01-01T00-00-00_a", "2026-02-01T00-00-00_b"):
        record = make_record(run_id)
        (directory / f"{run_id}.json").write_text(
            record.model_dump_json(indent=2), encoding="utf-8"
        )
    return directory


class TestImportResultsDir:

    def test_imports_all_valid_files(self, engine, results_dir):
        report = import_results_dir(engine, results_dir)
        assert (report.imported, report.skipped, report.failed) == (2, 0, 0)
        assert len(SqlResultRepository(engine).list()) == 2

    def test_second_run_is_idempotent(self, engine, results_dir):
        import_results_dir(engine, results_dir)
        report = import_results_dir(engine, results_dir)
        assert (report.imported, report.skipped, report.failed) == (0, 2, 0)

    def test_corrupt_file_counted_as_failed_without_aborting(self, engine, results_dir):
        (results_dir / "corrupt.json").write_text("{not json", encoding="utf-8")
        (results_dir / "wrong_shape.json").write_text(json.dumps({"foo": 1}), encoding="utf-8")
        report = import_results_dir(engine, results_dir)
        assert (report.imported, report.skipped, report.failed) == (2, 0, 2)
        assert sorted(report.failed_files) == ["corrupt.json", "wrong_shape.json"]

    def test_imported_record_round_trips(self, engine, results_dir):
        import_results_dir(engine, results_dir)
        repo = SqlResultRepository(engine)
        loaded = repo.get("2026-01-01T00-00-00_a")
        assert loaded.model_dump() == make_record("2026-01-01T00-00-00_a").model_dump()
