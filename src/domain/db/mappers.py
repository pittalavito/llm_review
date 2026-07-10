"""Explicit mapping between Pydantic domain models and SQLModel rows.

record_to_rows extracts analytical facts (ratings, decisions, latency,
tokens) into typed columns; extraction is defensive — malformed or missing
data yields NULL, never an insert failure. rows_to_record reconstructs the
RunRecord from the verbatim JSON columns so API responses stay identical to
the legacy file-based repository.
"""
from models.run_record import AgentRun, RunRecord

from domain.db.tables import AgentRunTable, RunAgentConfigTable, RunTable


def record_to_rows(
    record: RunRecord,
) -> tuple[RunTable, list[AgentRunTable], list[RunAgentConfigTable]]:
    graph_config = record.graph_config or {}
    meta_review = record.meta_review or {}
    
    run_row = RunTable(
        run_id=record.run_id,
        timestamp=record.timestamp,
        paper_path=record.paper_path,
        run_description=record.run_description,
        decision=record.decision,
        total_rounds=record.total_rounds,
        max_rounds=_as_int_in_range(graph_config.get("max_rounds"), 1, None),
        meta_overall_score=_as_int_in_range(meta_review.get("overall_score"), 1, 10),
        reviews=record.reviews,
        meta_review=record.meta_review,
        area_chair_response=record.area_chair_response,
        author_response=record.author_response,
        retrieval_metadata=record.retrieval_metadata,
        graph_config=graph_config,
    )
    agent_rows = [_agent_run_to_row(record.run_id, ar) for ar in record.agent_runs]
    config_rows = _config_rows(record.run_id, graph_config)
    return run_row, agent_rows, config_rows


def rows_to_record(run_row: RunTable, agent_rows: list[AgentRunTable]) -> RunRecord:
    """Rebuild the domain model from JSON columns (agent_rows already
    ordered by id, i.e. original list order)."""
    return RunRecord(
        run_id=run_row.run_id,
        timestamp=run_row.timestamp,
        paper_path=run_row.paper_path,
        run_description=run_row.run_description,
        decision=run_row.decision,
        total_rounds=run_row.total_rounds,
        reviews=run_row.reviews,
        meta_review=run_row.meta_review,
        area_chair_response=run_row.area_chair_response,
        author_response=run_row.author_response,
        retrieval_metadata=run_row.retrieval_metadata,
        graph_config=run_row.graph_config,
        agent_runs=[row_to_agent_run(row) for row in agent_rows],
    )


def row_to_agent_run(row: AgentRunTable) -> AgentRun:
    return AgentRun(
        agent=row.agent,
        round=row.round,
        input_message=row.input_message,
        context_used=row.context_used,
        response_payload=row.response_payload,
        prompt_trace=row.prompt_trace,
        runtime_trace=row.runtime_trace,
    )


# ---------------------------------------------------------------------------
# Analytics extraction (defensive: None on anything unexpected)
# ---------------------------------------------------------------------------

def _agent_run_to_row(run_id: str, ar: AgentRun) -> AgentRunTable:
    payload = ar.response_payload if isinstance(ar.response_payload, dict) else {}
    runtime_trace = ar.runtime_trace if isinstance(ar.runtime_trace, dict) else {}
    metrics = runtime_trace.get("metrics")
    input_tokens, output_tokens, total_tokens = _extract_tokens(
        runtime_trace.get("provider_usage")
    )
    return AgentRunTable(
        run_id=run_id,
        agent=str(ar.agent),
        round=ar.round,
        input_message=ar.input_message,
        context_used=ar.context_used,
        response_payload=ar.response_payload,
        prompt_trace=ar.prompt_trace,
        runtime_trace=ar.runtime_trace,
        rating=_as_int_in_range(payload.get("rating"), 1, 10),
        confidence=_as_int_in_range(payload.get("confidence"), 1, 5),
        overall_score=_as_int_in_range(payload.get("overall_score"), 1, 10),
        decision=_as_str(payload.get("decision") or payload.get("recommendation")),
        latency_ms=_as_float(metrics.get("latency_ms") if isinstance(metrics, dict) else None),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _config_rows(run_id: str, graph_config: dict) -> list[RunAgentConfigTable]:
    rows: list[RunAgentConfigTable] = []
    seen: set[str] = set()
    agents = graph_config.get("agents")
    if not isinstance(agents, list):
        return rows
    for entry in agents:
        if not isinstance(entry, dict):
            continue
        agent_name = _as_str(entry.get("agent_name"))
        model = _as_str(entry.get("model"))
        temperature = _as_float(entry.get("temperature"))
        # UNIQUE (run_id, agent_name) and NOT NULL columns: skip rows the
        # constraints would reject instead of failing the whole save.
        if not agent_name or agent_name in seen or not model:
            continue
        if temperature is None or not 0 <= temperature <= 2:
            continue
        seen.add(agent_name)
        persona = entry.get("reviewer_persona")
        persona = persona if isinstance(persona, dict) else {}
        rows.append(RunAgentConfigTable(
            run_id=run_id,
            agent_name=agent_name,
            model=model,
            temperature=temperature,
            prompt_version=_as_str(entry.get("prompt_version")),
            persona_commitment=_as_str(persona.get("commitment")),
            persona_intention=_as_str(persona.get("intention")),
            persona_knowledgeability=_as_str(persona.get("knowledgeability")),
            persona_focus=_as_str(persona.get("focus")),
            area_chair_style=_as_str(entry.get("area_chair_style")),
        ))
    return rows


def _extract_tokens(usage) -> tuple[int | None, int | None, int | None]:
    """Token counts from provider_usage; key names vary by provider."""
    if not isinstance(usage, dict):
        return None, None, None
    input_tokens = _as_int(usage.get("input_tokens", usage.get("prompt_tokens")))
    output_tokens = _as_int(usage.get("output_tokens", usage.get("completion_tokens")))
    total_tokens = _as_int(usage.get("total_tokens"))
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    return input_tokens, output_tokens, total_tokens


def _as_int(value) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _as_int_in_range(value, low: int, high: int | None) -> int | None:
    number = _as_int(value)
    if number is None or number < low or (high is not None and number > high):
        return None
    return number


def _as_float(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _as_str(value) -> str | None:
    return value if isinstance(value, str) and value else None
