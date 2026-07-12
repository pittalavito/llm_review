"""
BackupService tests: the in-memory ZIP structure and content.
  - one subfolder per table, with a CSV of scalar columns
  - per-record JSON files only for tables with JSON columns (run, agent_run)
  - CSV-only tables (run_agent_config, prompt_version)
  - manifest with row counts
  - JSON payload fidelity + CSV indexed columns
"""
import csv
import io
import json
import zipfile

import pytest

from config import Config
from domain.db.engine import create_db_engine
from domain.db.result_repository import ResultRepository
from domain.db.prompt_repository import PromptRepository
from domain.agent.prompting.catalog import DEFAULT_PROMPT_SEEDS
from service.backup_service import BackupService

from test_db_repository import make_record

@pytest.fixture()
def engine(tmp_path):
    config = Config(database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    return create_db_engine(config)


@pytest.fixture()
def seeded_engine(engine):
    """A DB with one run (+ agent runs + config) and the default prompts."""
    ResultRepository(engine).save(make_record())
    PromptRepository(engine).seed_defaults(DEFAULT_PROMPT_SEEDS)
    return engine


@pytest.fixture()
def archive(seeded_engine):
    zip_bytes, filename = BackupService(seeded_engine, Config()).build_zip()
    return zipfile.ZipFile(io.BytesIO(zip_bytes)), filename


def _read_csv(archive: zipfile.ZipFile, name: str) -> list[dict]:
    text = archive.read(name).decode("utf-8")
    return list(csv.DictReader(io.StringIO(text)))


class TestArchiveStructure:

    def test_filename_is_zip_with_timestamp(self, archive):
        _, filename = archive
        assert filename.startswith("db-backup_")
        assert filename.endswith(".zip")
        assert ":" not in filename  # Windows-safe

    def test_manifest_lists_all_tables_with_counts(self, archive):
        zf, _ = archive
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["tables"] == {
            "run": 1, "agent_run": 3, "run_agent_config": 2, "prompt_version": 5,
        }
        assert manifest["created_at"]
        assert manifest["app_version"]

    def test_each_table_has_a_csv(self, archive):
        zf, _ = archive
        names = set(zf.namelist())
        for table in ("run", "agent_run", "run_agent_config", "prompt_version"):
            assert f"{table}/{table}.csv" in names

    def test_json_files_only_for_tables_with_json_columns(self, archive):
        zf, _ = archive
        names = zf.namelist()
        assert any(n.startswith("run/") and n.endswith(".json") for n in names)
        assert any(n.startswith("agent_run/") and n.endswith(".json") for n in names)
        # run_agent_config and prompt_version have no JSON columns -> CSV only
        assert not any(n.startswith("run_agent_config/") and n.endswith(".json") for n in names)
        assert not any(n.startswith("prompt_version/") and n.endswith(".json") for n in names)


class TestContent:

    def test_run_json_holds_payload_columns(self, archive):
        zf, _ = archive
        record = make_record()
        payload = json.loads(zf.read(f"run/{record.run_id}.json"))
        assert set(payload) == {
            "reviews", "meta_review", "area_chair_response",
            "author_response", "retrieval_metadata", "graph_config",
        }
        assert payload["meta_review"]["overall_score"] == 8

    def test_run_csv_holds_indexed_columns(self, archive):
        zf, _ = archive
        rows = _read_csv(zf, "run/run.csv")
        assert len(rows) == 1
        row = rows[0]
        assert row["paper_path"] == "test_paper.pdf"
        assert row["decision"] == "accept"
        assert row["total_rounds"] == "1"
        # JSON columns must NOT appear in the CSV
        assert "meta_review" not in row

    def test_agent_run_csv_has_extracted_analytics(self, archive):
        zf, _ = archive
        rows = _read_csv(zf, "agent_run/agent_run.csv")
        reviewer = next(r for r in rows if r["agent"] == "reviewer_1")
        assert reviewer["rating"] == "7"
        assert reviewer["confidence"] == "4"
        assert reviewer["total_tokens"] == "150"

    def test_prompt_version_csv_lists_seeds(self, archive):
        zf, _ = archive
        rows = _read_csv(zf, "prompt_version/prompt_version.csv")
        pairs = {(r["agent_role"], r["version_label"]) for r in rows}
        assert ("reviewer", "v1") in pairs
        assert ("reviewer", "v2") in pairs

    def test_empty_db_still_produces_valid_archive(self, engine):
        zip_bytes, _ = BackupService(engine, Config()).build_zip()
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["tables"]["run"] == 0
        assert "run/run.csv" in zf.namelist()  # header-only CSV
