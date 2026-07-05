"""Populate the SQL schema (db/schema.sql) from existing RunRecord JSON files.

Assumes the target database already exists and the schema is applied.
Uses only the Python standard library (sqlite3) so it can run standalone.

Usage:
    python db/importer.py <sqlite_db_path> <results_dir> [--replace]

Example:
    python db/importer.py runs.db resource/results --replace
"""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger("db.importer")

_REVIEWER_AGENTS = {"reviewer_1", "reviewer_2", "reviewer_3"}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _json(value: Any) -> str | None:
    """Serialize a value to a compact JSON string (or None)."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _extract_tokens(runtime_trace: dict) -> tuple[int | None, int | None, int | None]:
    """Best-effort token extraction from a runtime_trace.provider_usage block."""
    usage = runtime_trace.get("provider_usage")
    if not isinstance(usage, dict):
        return None, None, None
    prompt = usage.get("input_tokens") or usage.get("prompt_tokens")
    completion = usage.get("output_tokens") or usage.get("completion_tokens")
    total = usage.get("total_tokens")
    return prompt, completion, total


# ---------------------------------------------------------------------------
# Per-section inserts
# ---------------------------------------------------------------------------

def _insert_run(conn: sqlite3.Connection, record: dict) -> None:
    graph_config = record.get("graph_config") or {}
    conn.execute(
        """
        INSERT INTO run (
            run_id, timestamp, paper_path, run_description,
            decision, total_rounds, max_rounds, graph_config_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record["run_id"],
            record["timestamp"],
            record["paper_path"],
            record.get("run_description"),
            record.get("decision"),
            record.get("total_rounds", 0),
            graph_config.get("max_rounds"),
            _json(graph_config),
        ),
    )


def _insert_agent_configs(conn: sqlite3.Connection, record: dict) -> None:
    graph_config = record.get("graph_config") or {}
    for cfg in graph_config.get("agents", []):
        persona = cfg.get("reviewer_persona") or {}
        conn.execute(
            """
            INSERT INTO run_agent_config (
                run_id, agent_name, model, temperature,
                reviewer_persona_commitment, reviewer_persona_intention,
                reviewer_persona_knowledgeability, reviewer_persona_focus,
                area_chair_style
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["run_id"],
                cfg["agent_name"],
                cfg["model"],
                cfg["temperature"],
                persona.get("commitment"),
                persona.get("intention"),
                persona.get("knowledgeability"),
                persona.get("focus"),
                cfg.get("area_chair_style"),
            ),
        )


def _insert_reviewer_review(
    conn: sqlite3.Connection, run_id: str, agent_run_id: int,
    reviewer_agent: str, round_index: int, payload: dict,
) -> None:
    cur = conn.execute(
        """
        INSERT INTO reviewer_review (
            run_id, agent_run_id, reviewer_agent, round_index,
            summary, significance_and_novelty, rating, confidence, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            agent_run_id,
            reviewer_agent,
            round_index,
            payload.get("summary", ""),
            payload.get("significance_and_novelty", ""),
            payload.get("rating"),
            payload.get("confidence"),
            _json(payload),
        ),
    )
    review_id = cur.lastrowid
    _kinds = (
        ("acceptance", payload.get("reasons_for_acceptance") or []),
        ("rejection", payload.get("reasons_for_rejection") or []),
        ("suggestion", payload.get("suggestions") or []),
    )
    for kind, items in _kinds:
        for position, text in enumerate(items):
            conn.execute(
                """
                INSERT INTO reviewer_review_point (review_id, kind, position, text)
                VALUES (?, ?, ?, ?)
                """,
                (review_id, kind, position, text),
            )


def _insert_agent_runs(conn: sqlite3.Connection, record: dict) -> dict[str, int]:
    """Insert every agent invocation and its traces.

    Returns a map {agent_name: last agent_run rowid} so snapshot payloads
    (meta_review, area_chair, author) can be linked to their producer.
    """
    run_id = record["run_id"]
    last_agent_run_id: dict[str, int] = {}

    for sequence_index, ar in enumerate(record.get("agent_runs", [])):
        agent_name = ar["agent"]
        round_index = ar.get("round", 0)
        payload = ar.get("response_payload") or {}

        cur = conn.execute(
            """
            INSERT INTO agent_run (
                run_id, agent_name, round_index, sequence_index,
                input_message, context_used, response_payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                agent_name,
                round_index,
                sequence_index,
                ar.get("input_message", ""),
                ar.get("context_used"),
                _json(payload),
            ),
        )
        agent_run_id = cur.lastrowid
        last_agent_run_id[agent_name] = agent_run_id

        _insert_prompt_trace(conn, agent_run_id, ar.get("prompt_trace"))
        _insert_runtime_trace(conn, agent_run_id, ar.get("runtime_trace"))

        if agent_name in _REVIEWER_AGENTS and payload:
            _insert_reviewer_review(
                conn, run_id, agent_run_id, agent_name, round_index, payload
            )

    return last_agent_run_id


def _insert_prompt_trace(
    conn: sqlite3.Connection, agent_run_id: int, prompt_trace: dict | None
) -> None:
    if not prompt_trace:
        return
    rendered = prompt_trace.get("rendered") or {}
    conn.execute(
        """
        INSERT INTO agent_run_prompt_trace (
            agent_run_id, system_prompt, human_prompt, full_prompt, trace_json
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            agent_run_id,
            rendered.get("system"),
            rendered.get("human"),
            rendered.get("full_prompt"),
            _json(prompt_trace),
        ),
    )


def _insert_runtime_trace(
    conn: sqlite3.Connection, agent_run_id: int, runtime_trace: dict | None
) -> None:
    if not runtime_trace:
        return
    llm = runtime_trace.get("llm") or {}
    metrics = runtime_trace.get("metrics") or {}
    prompt_tokens, completion_tokens, total_tokens = _extract_tokens(runtime_trace)

    conn.execute(
        """
        INSERT INTO agent_run_runtime_trace (
            agent_run_id, llm_class, llm_model, llm_temperature,
            started_at, ended_at, latency_ms,
            prompt_tokens, completion_tokens, total_tokens, trace_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_run_id,
            llm.get("class"),
            llm.get("model"),
            llm.get("temperature"),
            metrics.get("started_at"),
            metrics.get("ended_at"),
            metrics.get("latency_ms"),
            prompt_tokens,
            completion_tokens,
            total_tokens,
            _json(runtime_trace),
        ),
    )

    retrieval = runtime_trace.get("retrieval")
    if isinstance(retrieval, dict):
        conn.execute(
            """
            INSERT INTO agent_run_retrieval (
                agent_run_id, provider, paper_path,
                base_query, query_suffix, resolved_query
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                agent_run_id,
                retrieval.get("provider"),
                retrieval.get("paper_path"),
                retrieval.get("base_query"),
                retrieval.get("query_suffix"),
                retrieval.get("resolved_query"),
            ),
        )


def _insert_meta_review(
    conn: sqlite3.Connection, run_id: str, payload: dict | None, agent_run_id: int | None
) -> None:
    if not payload:
        return
    cur = conn.execute(
        """
        INSERT INTO meta_review (
            run_id, agent_run_id, summary, overall_score, recommendation, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            agent_run_id,
            payload.get("summary", ""),
            payload.get("overall_score"),
            payload.get("recommendation"),
            _json(payload),
        ),
    )
    meta_review_id = cur.lastrowid
    for position, text in enumerate(payload.get("key_points") or []):
        conn.execute(
            """
            INSERT INTO meta_review_key_point (meta_review_id, position, text)
            VALUES (?, ?, ?)
            """,
            (meta_review_id, position, text),
        )


def _insert_area_chair(
    conn: sqlite3.Connection, run_id: str, payload: dict | None, agent_run_id: int | None
) -> None:
    if not payload:
        return
    conn.execute(
        """
        INSERT INTO area_chair_response (
            run_id, agent_run_id, summary, justification,
            decision, confidence, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            agent_run_id,
            payload.get("summary", ""),
            payload.get("justification", ""),
            payload.get("decision"),
            payload.get("confidence"),
            _json(payload),
        ),
    )


def _insert_author(
    conn: sqlite3.Connection, run_id: str, payload: dict | None, agent_run_id: int | None
) -> None:
    if not payload:
        return
    cur = conn.execute(
        """
        INSERT INTO author_response (run_id, agent_run_id, rebuttal, payload_json)
        VALUES (?, ?, ?, ?)
        """,
        (run_id, agent_run_id, payload.get("rebuttal", ""), _json(payload)),
    )
    author_id = cur.lastrowid

    for position, item in enumerate(payload.get("reviewer_rebuttals") or []):
        conn.execute(
            """
            INSERT INTO author_reviewer_rebuttal (
                author_response_id, position, reviewer_name, response
            ) VALUES (?, ?, ?, ?)
            """,
            (author_id, position, item.get("reviewer_name", ""), item.get("response", "")),
        )

    for position, item in enumerate(payload.get("revised_sections") or []):
        conn.execute(
            """
            INSERT INTO author_revised_section (
                author_response_id, position, section_name, content
            ) VALUES (?, ?, ?, ?)
            """,
            (author_id, position, item.get("section_name", ""), item.get("content", "")),
        )

    for position, text in enumerate(payload.get("key_changes") or []):
        conn.execute(
            """
            INSERT INTO author_key_change (author_response_id, position, text)
            VALUES (?, ?, ?)
            """,
            (author_id, position, text),
        )


def _insert_retrieval_metadata(conn: sqlite3.Connection, run_id: str, meta: dict | None) -> None:
    if not meta:
        return
    conn.execute(
        """
        INSERT INTO retrieval_run_metadata (
            run_id, paper_path, index_status,
            chunk_count_total, chunk_count_retrieved, top_k, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            meta.get("paper_path"),
            meta.get("index_status"),
            meta.get("chunk_count_total"),
            meta.get("chunk_count_retrieved"),
            meta.get("top_k"),
            _json(meta),
        ),
    )


def _insert_reviews_raw(conn: sqlite3.Connection, run_id: str, reviews: list | None) -> None:
    for position, review in enumerate(reviews or []):
        review_json = review if isinstance(review, str) else _json(review)
        conn.execute(
            """
            INSERT INTO run_review_raw (run_id, position, review_json)
            VALUES (?, ?, ?)
            """,
            (run_id, position, review_json),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def insert_run_record(conn: sqlite3.Connection, record: dict, replace: bool = False) -> None:
    """Insert a single RunRecord (as dict) into all relevant tables.

    With replace=True an existing run with the same run_id is deleted first
    (cascades to all child rows), making re-imports idempotent.
    """
    run_id = record["run_id"]
    if replace:
        conn.execute("DELETE FROM run WHERE run_id = ?", (run_id,))

    _insert_run(conn, record)
    _insert_agent_configs(conn, record)
    last_agent_run_id = _insert_agent_runs(conn, record)

    _insert_meta_review(conn, run_id, record.get("meta_review"),
                        last_agent_run_id.get("meta_reviewer"))
    _insert_area_chair(conn, run_id, record.get("area_chair_response"),
                       last_agent_run_id.get("area_chair"))
    _insert_author(conn, run_id, record.get("author_response"),
                   last_agent_run_id.get("author_agent"))
    _insert_retrieval_metadata(conn, run_id, record.get("retrieval_metadata"))
    _insert_reviews_raw(conn, run_id, record.get("reviews"))


def import_from_dir(db_path: str | Path, results_dir: str | Path, replace: bool = False) -> int:
    """Import every *.json RunRecord in results_dir into the SQLite DB.

    Returns the number of successfully imported runs.
    """
    results_dir = Path(results_dir)
    files = sorted(results_dir.glob("*.json"))
    imported = 0

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        for path in files:
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                with conn:  # transaction per run: commit on success, rollback on error
                    insert_run_record(conn, record, replace=replace)
                imported += 1
                logger.info("Imported %s", path.name)
            except Exception:
                logger.exception("Failed to import %s (skipped)", path.name)
    finally:
        conn.close()

    logger.info("Imported %d/%d runs", imported, len(files))
    return imported


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(description="Import RunRecord JSON files into the SQL schema.")
    parser.add_argument("db_path", help="Path to the target SQLite database (schema already applied).")
    parser.add_argument("results_dir", help="Directory containing RunRecord *.json files.")
    parser.add_argument("--replace", action="store_true",
                        help="Replace existing runs with the same run_id.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    import_from_dir(args.db_path, args.results_dir, replace=args.replace)


if __name__ == "__main__":
    _main()
