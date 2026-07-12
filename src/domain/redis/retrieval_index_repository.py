"""Primary store for BM25 RAG indices.

Redis is the store (no more JSON files under resource/). Indices are derived
data — rebuildable from the paper via BM25 — so an in-memory fallback is used
when Redis is unset or unreachable: the app keeps working (rebuild + cache in
RAM), tests run without a Redis server, and nothing is written to disk.
"""
import logging
from hashlib import sha256

import redis

from config import Config
from models.retrieval import Index

logger = logging.getLogger(__name__)

_KEY_PREFIX = "llm-review:rag-index:"


def compute_doc_id(relative_path: str) -> str:
    """Stable id for a paper's index — SHA-256 of its relative path.
    Kept identical to the former file-based repository so ids don't change."""
    return sha256(relative_path.encode("utf-8")).hexdigest()


class RedisIndexRepository:
    """BM25 index store backed by Redis. ttl_seconds <= 0 means no expiry
    (permanent store); a positive value sets a TTL on each key."""

    def __init__(self, client: "redis.Redis", ttl_seconds: int = 0):
        self._client = client
        self._ttl = ttl_seconds

    @staticmethod
    def compute_doc_id(relative_path: str) -> str:
        return compute_doc_id(relative_path)

    def load(self, doc_id: str) -> Index | None:
        raw = self._client.get(_KEY_PREFIX + doc_id)
        if raw is None:
            return None
        try:
            return Index.model_validate_json(raw)
        except Exception:
            logger.warning("Discarding malformed index in Redis: %s", doc_id)
            return None

    def save(self, payload: Index) -> None:
        key = _KEY_PREFIX + payload.doc_id
        value = payload.model_dump_json()
        if self._ttl > 0:
            self._client.set(key, value, ex=self._ttl)
        else:
            self._client.set(key, value)

    def list_indexed(self) -> list[str]:
        """Return paper_path for every index stored in Redis (SCAN + parse)."""
        paper_paths: list[str] = []
        for key in self._client.scan_iter(match=_KEY_PREFIX + "*"):
            raw = self._client.get(key)
            if raw is None:
                continue
            try:
                paper_paths.append(Index.model_validate_json(raw).paper_path)
            except Exception:
                logger.warning("Skipping malformed index in Redis: %s", key)
        return sorted(paper_paths)


class InMemoryIndexRepository:
    """Process-local fallback used when Redis is unavailable. Same contract;
    never raises. Indices live only for the process lifetime (rebuilt on
    demand), which is fine since they are derived from the papers."""

    def __init__(self):
        self._store: dict[str, Index] = {}

    @staticmethod
    def compute_doc_id(relative_path: str) -> str:
        return compute_doc_id(relative_path)

    def load(self, doc_id: str) -> Index | None:
        return self._store.get(doc_id)

    def save(self, payload: Index) -> None:
        self._store[payload.doc_id] = payload

    def list_indexed(self) -> list[str]:
        return sorted(index.paper_path for index in self._store.values())


def build_index_repository(config: Config) -> RedisIndexRepository | InMemoryIndexRepository:
    """Redis-backed store when REDIS_URL is set and reachable; otherwise a
    process-local in-memory repository (unset URL, or Redis down at startup)."""
    if not config.redis_url:
        logger.info("No REDIS_URL — RAG indices kept in memory (not persisted).")
        return InMemoryIndexRepository()
    try:
        client = redis.Redis.from_url(
            config.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=2,
        )
        client.ping()
    except redis.RedisError as exc:
        logger.warning("Redis unreachable (%s) — RAG indices kept in memory.", exc)
        return InMemoryIndexRepository()
    logger.info("RAG index store on Redis: %s", config.redis_url)
    return RedisIndexRepository(client, config.redis_index_ttl_seconds)
