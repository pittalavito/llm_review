"""Redis cache-aside layer for BM25 index payloads.

Files under resource/rag-index/ remain the source of truth; Redis is a pure
read accelerator. Any Redis failure degrades transparently to file-only
behavior (one warning, no crash), so the app runs identically with or
without a reachable Redis.
"""

import logging
from pathlib import Path

import redis

from config import Config
from models.retrieval import Index
from domain.retrieval.indexing import IndexRepository

logger = logging.getLogger(__name__)

_KEY_PREFIX = "llm-review:rag-index:"


class CachedIndexRepository:
    """Duck-types IndexRepository: load() tries Redis first, falls back to
    file on miss and repopulates the cache; save() writes the file first
    (source of truth), then caches best-effort."""

    def __init__(self, file_repo: IndexRepository, client: redis.Redis, ttl_seconds: int):
        self._file_repo = file_repo
        self._client = client
        self._ttl = ttl_seconds
        self._warned = False

    # ------------------------------------------------------------------
    # IndexRepository contract
    # ------------------------------------------------------------------

    @staticmethod
    def compute_doc_id(relative_path: str) -> str:
        return IndexRepository.compute_doc_id(relative_path)

    def index_file_path(self, doc_id: str) -> Path:
        return self._file_repo.index_file_path(doc_id)

    def load(self, doc_id: str) -> Index | None:
        cached = self._cache_get(doc_id)
        if cached is not None:
            logger.debug("RAG index cache hit: %s", doc_id)
            return cached
        payload = self._file_repo.load(doc_id)
        if payload is not None:
            self._cache_set(payload)
        return payload

    def save(self, payload: Index) -> None:
        self._file_repo.save(payload)  # file first: source of truth
        self._cache_set(payload)

    def list_indexed(self) -> list[str]:
        # Deliberately reads from disk: the cache never owns the inventory.
        return self._file_repo.list_indexed()

    # ------------------------------------------------------------------
    # Best-effort Redis access
    # ------------------------------------------------------------------

    def _cache_get(self, doc_id: str) -> Index | None:
        try:
            raw = self._client.get(_KEY_PREFIX + doc_id)
        except redis.RedisError:
            self._warn_once()
            return None
        if raw is None:
            return None
        try:
            return Index.model_validate_json(raw)
        except Exception:
            logger.warning("Discarding malformed cached index: %s", doc_id)
            return None

    def _cache_set(self, payload: Index) -> None:
        try:
            key = _KEY_PREFIX + payload.doc_id
            value = payload.model_dump_json()
            if self._ttl > 0:
                self._client.set(key, value, ex=self._ttl)
            else:
                self._client.set(key, value)
        except redis.RedisError:
            self._warn_once()

    def _warn_once(self) -> None:
        if not self._warned:
            logger.warning("Redis unavailable — serving RAG indices from files only.")
            self._warned = True


def build_index_repository(config: Config, index_dir: Path) -> IndexRepository | CachedIndexRepository:
    """File-only repository when REDIS_URL is unset; otherwise the cached
    wrapper — falling back to file-only if Redis is unreachable at startup."""
    file_repo = IndexRepository(index_dir)
    if not config.redis_url:
        return file_repo
    try:
        client = redis.Redis.from_url(
            config.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=2,
        )
        client.ping()
    except redis.RedisError as exc:
        logger.warning("Redis unreachable (%s) — RAG indices served from files only.", exc)
        return file_repo
    logger.info("RAG index cache enabled: %s", config.redis_url)
    return CachedIndexRepository(file_repo, client, config.redis_index_ttl_seconds)
