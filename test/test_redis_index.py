"""
RAG index store tests (fakeredis, no server):
  - RedisIndexRepository: save->load round-trip, list_indexed via SCAN,
    permanent keys (no TTL), malformed value -> None
  - InMemoryIndexRepository: same contract, missing -> None
  - build_index_repository factory: no/empty url -> in-memory;
    unreachable Redis -> in-memory with a warning
"""
import logging

import fakeredis
import pytest

from config import Config
from models.retrieval import FileSignature, Index, IndexConfig, IndexedChunk
from domain.redis.retrieval_index_repository import (
    InMemoryIndexRepository,
    RedisIndexRepository,
    build_index_repository,
    compute_doc_id,
)


def make_index(paper_path: str = "paper.pdf") -> Index:
    return Index(
        doc_id=compute_doc_id(paper_path),
        paper_path=paper_path,
        file_signature=FileSignature(mtime_ns=1, size=100),
        settings=IndexConfig(chunk_size=800, chunk_overlap=150, strategy_version="test-v1"),
        doc_freq={"causal": 2},
        chunks=[IndexedChunk(text="chunk", token_counts={"causal": 1}, length=1)],
    )


@pytest.fixture()
def client():
    return fakeredis.FakeRedis(decode_responses=True)


# ---------------------------------------------------------------------------
# RedisIndexRepository
# ---------------------------------------------------------------------------

class TestRedisIndexRepository:

    def test_save_then_load_round_trip(self, client):
        repo = RedisIndexRepository(client, ttl_seconds=0)
        index = make_index()
        repo.save(index)
        assert repo.load(index.doc_id) == index

    def test_load_missing_returns_none(self, client):
        assert RedisIndexRepository(client).load("deadbeef") is None

    def test_permanent_by_default_no_ttl(self, client):
        repo = RedisIndexRepository(client, ttl_seconds=0)
        index = make_index()
        repo.save(index)
        assert client.ttl(f"llm-review:rag-index:{index.doc_id}") == -1  # no expiry

    def test_positive_ttl_sets_expiry(self, client):
        repo = RedisIndexRepository(client, ttl_seconds=3600)
        index = make_index()
        repo.save(index)
        assert 0 < client.ttl(f"llm-review:rag-index:{index.doc_id}") <= 3600

    def test_list_indexed_scans_paper_paths(self, client):
        repo = RedisIndexRepository(client)
        repo.save(make_index("b.pdf"))
        repo.save(make_index("a.pdf"))
        assert repo.list_indexed() == ["a.pdf", "b.pdf"]  # sorted

    def test_list_indexed_empty(self, client):
        assert RedisIndexRepository(client).list_indexed() == []

    def test_malformed_value_returns_none(self, client):
        repo = RedisIndexRepository(client)
        client.set("llm-review:rag-index:bad", "{not valid index}")
        assert repo.load("bad") is None


# ---------------------------------------------------------------------------
# InMemoryIndexRepository
# ---------------------------------------------------------------------------

class TestInMemoryIndexRepository:

    def test_save_then_load(self):
        repo = InMemoryIndexRepository()
        index = make_index()
        repo.save(index)
        assert repo.load(index.doc_id) == index

    def test_missing_returns_none(self):
        assert InMemoryIndexRepository().load("nope") is None

    def test_list_indexed_sorted(self):
        repo = InMemoryIndexRepository()
        repo.save(make_index("b.pdf"))
        repo.save(make_index("a.pdf"))
        assert repo.list_indexed() == ["a.pdf", "b.pdf"]

    def test_compute_doc_id_matches_module_function(self):
        assert InMemoryIndexRepository.compute_doc_id("x.pdf") == compute_doc_id("x.pdf")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

class TestBuildIndexRepository:

    def test_no_redis_url_returns_in_memory(self):
        repo = build_index_repository(Config(redis_url=None))
        assert type(repo) is InMemoryIndexRepository

    def test_empty_redis_url_returns_in_memory(self):
        repo = build_index_repository(Config(redis_url=""))
        assert type(repo) is InMemoryIndexRepository

    def test_unreachable_redis_falls_back_to_in_memory(self, caplog):
        config = Config(redis_url="redis://localhost:1/0")  # nothing listens here
        with caplog.at_level(logging.WARNING):
            repo = build_index_repository(config)
        assert type(repo) is InMemoryIndexRepository
        assert any("Redis unreachable" in r.message for r in caplog.records)
