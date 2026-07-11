"""
CachedIndexRepository / build_index_repository tests (fakeredis, no server):
  - factory returns the plain file repository when redis_url is unset
  - factory falls back to file-only when Redis is unreachable
  - cache miss reads the file and populates the key (with TTL)
  - cache hit does not touch the file repository
  - save writes the file first, then caches
  - Redis errors degrade to file behavior with a single warning
"""
import logging

import fakeredis
import pytest
import redis

from config import Config, RAG_INDEX_DIR
from models.retrieval import FileSignature, Index, IndexConfig, IndexedChunk
from domain.retrieval.cache import CachedIndexRepository, build_index_repository
from domain.retrieval.indexing import IndexRepository

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

def make_index(paper_path: str = "paper.pdf") -> Index:
    return Index(
        doc_id=IndexRepository.compute_doc_id(paper_path),
        paper_path=paper_path,
        file_signature=FileSignature(mtime_ns=1, size=100),
        settings=IndexConfig(chunk_size=800, chunk_overlap=150, strategy_version="test-v1"),
        doc_freq={"causal": 2},
        chunks=[IndexedChunk(text="chunk", token_counts={"causal": 1}, length=1)],
    )


class CountingFileRepo(IndexRepository):
    """File repository that counts load() calls."""

    def __init__(self, index_dir):
        super().__init__(index_dir)
        self.load_calls = 0

    def load(self, doc_id):
        self.load_calls += 1
        return super().load(doc_id)


@pytest.fixture()
def file_repo(tmp_path):
    return CountingFileRepo(tmp_path / "rag-index")


@pytest.fixture()
def client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture()
def cached_repo(file_repo, client):
    return CachedIndexRepository(file_repo, client, ttl_seconds=3600)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestBuildIndexRepository:

    def test_no_redis_url_returns_plain_file_repo(self):
        config = Config(redis_url=None)
        repo = build_index_repository(config, RAG_INDEX_DIR)
        assert type(repo) is IndexRepository

    def test_empty_redis_url_returns_plain_file_repo(self):
        config = Config(redis_url="")
        repo = build_index_repository(config, RAG_INDEX_DIR)
        assert type(repo) is IndexRepository

    def test_unreachable_redis_falls_back_to_file_repo(self, caplog):
        config = Config(redis_url="redis://localhost:1/0")  # nothing listens here
        with caplog.at_level(logging.WARNING):
            repo = build_index_repository(config, RAG_INDEX_DIR)
        assert type(repo) is IndexRepository
        assert any("Redis unreachable" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Cache-aside behavior
# ---------------------------------------------------------------------------

class TestCacheAside:

    def test_miss_reads_file_and_populates_cache(self, cached_repo, file_repo, client):
        index = make_index()
        file_repo.save(index)  # only on disk

        loaded = cached_repo.load(index.doc_id)

        assert loaded == index
        assert file_repo.load_calls == 1
        key = f"llm-review:rag-index:{index.doc_id}"
        assert client.get(key) is not None
        assert 0 < client.ttl(key) <= 3600

    def test_hit_does_not_touch_file_repo(self, cached_repo, file_repo):
        index = make_index()
        file_repo.save(index)
        cached_repo.load(index.doc_id)  # miss -> populates cache

        loaded = cached_repo.load(index.doc_id)  # hit

        assert loaded == index
        assert file_repo.load_calls == 1

    def test_missing_everywhere_returns_none(self, cached_repo):
        assert cached_repo.load("deadbeef") is None

    def test_save_writes_file_first_then_caches(self, cached_repo, file_repo, client):
        index = make_index()
        cached_repo.save(index)

        assert file_repo.index_file_path(index.doc_id).exists()
        assert client.get(f"llm-review:rag-index:{index.doc_id}") is not None

    def test_zero_ttl_caches_without_expiry(self, file_repo, client):
        repo = CachedIndexRepository(file_repo, client, ttl_seconds=0)
        index = make_index()
        repo.save(index)
        assert client.ttl(f"llm-review:rag-index:{index.doc_id}") == -1  # no expiry

    def test_list_indexed_delegates_to_files(self, cached_repo, file_repo):
        index = make_index()
        cached_repo.save(index)
        assert cached_repo.list_indexed() == [index.paper_path]


# ---------------------------------------------------------------------------
# Degradation on Redis errors
# ---------------------------------------------------------------------------

class BrokenRedis:
    def get(self, *args, **kwargs):
        raise redis.ConnectionError("boom")

    def set(self, *args, **kwargs):
        raise redis.ConnectionError("boom")


class TestDegradation:

    def test_errors_degrade_to_file_with_single_warning(self, file_repo, caplog):
        repo = CachedIndexRepository(file_repo, BrokenRedis(), ttl_seconds=3600)
        index = make_index()

        with caplog.at_level(logging.WARNING, logger="retrieval.cache"):
            repo.save(index)                          # set fails -> warning
            assert repo.load(index.doc_id) == index   # get fails -> file fallback
            assert repo.load(index.doc_id) == index

        warnings = [r for r in caplog.records if "Redis unavailable" in r.message]
        assert len(warnings) == 1
        assert file_repo.load_calls == 2
