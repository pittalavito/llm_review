import json

from datetime import datetime
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate


CONTEXT_HEADER = "RETRIEVED CONTEXT:"
PROMPT_SEPARATOR = "\n\n---\n\n"


def format_context_block(raw_context: str) -> str:
    if not raw_context or not raw_context.strip():
        return ""
    return f"{CONTEXT_HEADER}\n{raw_context}{PROMPT_SEPARATOR}"


def build_prompt_trace(system_prompt: str, response_schema: type | None, message: str, raw_context: str) -> dict[str, Any]:
    context_block = format_context_block(raw_context)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{context}{message}"),
    ])
    messages = prompt.format_messages(message=message, context=context_block)

    system_content = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
    human_content = next((m.content for m in messages if isinstance(m, HumanMessage)), "")
    schema_content = response_schema.model_json_schema() if response_schema else None

    parts = [
        f"[SYSTEM]\n{system_content}" if system_content else "",
        f"[HUMAN]\n{human_content}" if human_content else "",
        f"[SCHEMA - sent via structured output]\n{json.dumps(schema_content, ensure_ascii=False, indent=2)}"
        if schema_content else "",
    ]

    return {
        "template": {
            "system": system_prompt,
            "human": "{context}{message}",
            "variables": {
                "message": message,
                "context": context_block,
            },
        },
        "rendered": {
            "system": system_content,
            "human": human_content,
            "full_prompt": PROMPT_SEPARATOR.join([p for p in parts if p]),
        },
        "schema": schema_content,
    }


def build_runtime_trace(
    llm: Any,
    context_provider: Any,
    result: Any,
    started_at: datetime,
    ended_at: datetime,
    latency_ms: float,
) -> dict[str, Any]:
    return {
        "llm": {
            "class": llm.__class__.__name__,
            "model": getattr(llm, "model", None) or getattr(llm, "model_name", None),
            "temperature": getattr(llm, "temperature", None),
        },
        "metrics": {
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "latency_ms": latency_ms,
        },
        "provider_usage": extract_provider_usage(result),
        "provider_metadata": extract_provider_metadata(result),
        "retrieval": extract_retrieval_trace(context_provider),
    }


def extract_retrieval_trace(context_provider: Any) -> dict[str, Any] | None:
    if context_provider is None:
        return None
    if hasattr(context_provider, "get_last_trace"):
        return context_provider.get_last_trace()
    return {"provider": context_provider.__class__.__name__}


def extract_provider_usage(result: Any) -> dict[str, Any] | None:
    usage = getattr(result, "usage_metadata", None)
    if usage:
        return dict(usage)

    response_metadata = getattr(result, "response_metadata", None) or {}
    token_usage = response_metadata.get("token_usage")
    usage_fallback = response_metadata.get("usage")
    if token_usage:
        return dict(token_usage)
    if usage_fallback:
        return dict(usage_fallback)
    return None


def extract_provider_metadata(result: Any) -> dict[str, Any] | None:
    response_metadata = getattr(result, "response_metadata", None)
    if not response_metadata:
        return None
    return dict(response_metadata)
