"""
PaperRepository tests:
  - seed classifies OPEN_REVIEW (in index) vs OTHER (folder-only)
  - num_review = live count of runs for the paper
  - seed is idempotent (no duplicate rows; counts refreshed)
  - get_by_path, list_openreview, list_paths
"""
import json

import pytest

from config import Config
from domain.db.engine import create_db_engine
from domain.db.paper_repository import PaperRepository
from domain.db.result_repository import ResultRepository
from models.paper import PaperType

from test_db_repository import make_record


@pytest.fixture()
def engine(tmp_path):
    config = Config(database_url=f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    return create_db_engine(config)


@pytest.fixture()
def papers_dir(tmp_path):
    directory = tmp_path / "papers"
    directory.mkdir()
    (directory / "in_index.pdf").write_text("pdf", encoding="utf-8")
    (directory / "folder_only.pdf").write_text("pdf", encoding="utf-8")
    return directory


@pytest.fixture()
def index_path(tmp_path):
    path = tmp_path / "open-review-index.json"
    path.write_text(json.dumps([
        {
            "paper_path": "in_index",  # stem, matches in_index.pdf
            "title": "A Paper In The Index",
            "openreview_forum_id": "forum123",
            "openreview_api_version": "v2",
            "conference": "ICLR 2022",
            "decision": "Accept",
        },
    ]), encoding="utf-8")
    return path


def save_runs(engine, paper_path: str, n: int) -> None:
    repo = ResultRepository(engine)
    for i in range(n):
        record = make_record(f"run-{paper_path}-{i}")
        record.paper_path = paper_path
        repo.save(record)


class TestSeed:

    def test_classifies_open_review_and_other(self, engine, papers_dir, index_path):
        repo = PaperRepository(engine)
        assert repo.seed_from_sources(papers_dir, index_path) == 2

        by_path = {p.paper_path: p for p in repo.list()}
        assert by_path["in_index.pdf"].paper_type == PaperType.OPEN_REVIEW
        assert by_path["in_index.pdf"].open_review_id == "forum123"
        assert by_path["in_index.pdf"].conference == "ICLR 2022"
        assert by_path["in_index.pdf"].openreview_api_version == "v2"
        assert by_path["in_index.pdf"].paper_name == "A Paper In The Index"
        assert by_path["folder_only.pdf"].paper_type == PaperType.OTHER
        assert by_path["folder_only.pdf"].open_review_id is None
        assert by_path["folder_only.pdf"].paper_name == "folder_only"

    def test_num_review_counts_runs(self, engine, papers_dir, index_path):
        save_runs(engine, "in_index.pdf", 3)
        repo = PaperRepository(engine)
        repo.seed_from_sources(papers_dir, index_path)
        by_path = {p.paper_path: p for p in repo.list()}
        assert by_path["in_index.pdf"].num_review == 3
        assert by_path["folder_only.pdf"].num_review == 0

    def test_num_review_is_live_after_seed(self, engine, papers_dir, index_path):
        repo = PaperRepository(engine)
        repo.seed_from_sources(papers_dir, index_path)
        # runs added after the seed are still reflected on read
        save_runs(engine, "folder_only.pdf", 2)
        by_path = {p.paper_path: p for p in repo.list()}
        assert by_path["folder_only.pdf"].num_review == 2

    def test_idempotent_no_duplicates(self, engine, papers_dir, index_path):
        repo = PaperRepository(engine)
        repo.seed_from_sources(papers_dir, index_path)
        assert repo.seed_from_sources(papers_dir, index_path) == 0
        assert len(repo.list()) == 2

    def test_missing_index_file_makes_all_other(self, engine, papers_dir, tmp_path):
        repo = PaperRepository(engine)
        repo.seed_from_sources(papers_dir, tmp_path / "missing.json")
        assert {p.paper_type for p in repo.list()} == {PaperType.OTHER}


class TestReads:

    @pytest.fixture()
    def seeded(self, engine, papers_dir, index_path):
        repo = PaperRepository(engine)
        repo.seed_from_sources(papers_dir, index_path)
        return repo

    def test_list_paths_sorted(self, seeded):
        assert seeded.list_paths() == ["folder_only.pdf", "in_index.pdf"]

    def test_list_openreview_only(self, seeded):
        papers = seeded.list_openreview()
        assert [p.paper_path for p in papers] == ["in_index.pdf"]

    def test_get_by_path(self, seeded):
        assert seeded.get_by_path("in_index.pdf").open_review_id == "forum123"

    def test_get_by_path_missing_raises(self, seeded):
        with pytest.raises(ValueError):
            seeded.get_by_path("nope.pdf")
