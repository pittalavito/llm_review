"""Backward-compatible alias: SqlResultRepository = ResultRepository."""

from domain.db.result_repository import ResultRepository as SqlResultRepository

__all__ = ["SqlResultRepository"]
