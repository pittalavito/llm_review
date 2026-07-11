import json
import logging

from abc import ABC
from datetime import datetime, timezone
from time import perf_counter
from typing import Generic
from domain.agent.tracing import build_prompt_trace, build_runtime_trace, format_context_block, PROMPT_SEPARATOR
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel
from models.agent import AgentName, AgentResponse, RawResponse, T
from models.protocols import ContextProvider

logger = logging.getLogger(__name__)

_LOGGER_PREFIX = "[BaseAgent]"


class AgentValidationError(ValueError):
    def __init__(self, message: str, raw_output: str = "") -> None:
        super().__init__(message)
        self.raw_output: str = raw_output


class BaseAgent(ABC, Generic[T]):
    AGENT_NAME: AgentName
    SYSTEM_PROMPT: str = ""
    RESPONSE_SCHEMA: type[T] | None = None
    RAG_QUERY: str | None = ""
    RAG_SECTIONS: list[str] = []

    def __init__(
        self, 
        client: BaseChatModel, 
        context_provider: ContextProvider | None = None
    ):
        self.client = client
        self.name = self.AGENT_NAME
        self._context_provider = context_provider
        self._prompt = self._build_prompt_template()
        self._chain: Runnable = self._build_chain(client)

    def run(self, message: str, paper_path: str | None = None) -> AgentResponse[T]:
        normalized = message.strip()
        if not normalized:
            raise ValueError("Message must not be empty.")

        raw_context = self._get_raw_context(paper_path)
        context_block = self._format_context_block(raw_context)
        started_at = datetime.now(timezone.utc)
        t0 = perf_counter()

        logger.info(f"{_LOGGER_PREFIX} Running '{self.name}', ctx_len={len(context_block)}")
        try:
            result = self._chain.invoke({"message": normalized, "context": context_block})
            
        except Exception as exc:
            raise AgentValidationError(str(exc)) from exc

        latency_ms = round((perf_counter() - t0) * 1000, 3)
        ended_at = datetime.now(timezone.utc)
        payload = self._extract_payload(result)
        
        return AgentResponse(
            agent=self.name,
            payload=payload,
            input_message=normalized,
            context_used=raw_context or None,
            prompt_trace=self._build_prompt_trace(normalized, raw_context),
            runtime_trace=self._build_runtime_trace(result=result, started_at=started_at, ended_at=ended_at, latency_ms=latency_ms)
        )

    @classmethod
    def build_preview(cls, message: str, context: str = "", system_prompt_override: str | None = None) -> dict:
        
        prompt = cls._build_prompt_template_for_preview(system_prompt_override=system_prompt_override)
        context_block = cls._format_context_block(context)
        messages = prompt.format_messages(message=message, context=context_block)

        system_content = next((m.content for m in messages if isinstance(m, SystemMessage)), "")
        human_content  = next((m.content for m in messages if isinstance(m, HumanMessage)),  "")
        schema_content = (
            json.dumps(cls.RESPONSE_SCHEMA.model_json_schema(), ensure_ascii=False, indent=2)
            if cls.RESPONSE_SCHEMA else ""
        )

        parts = [s for s in [
            f"[SYSTEM]\n{system_content}" if system_content else "",
            f"[HUMAN]\n{human_content}" if human_content else "",
            f"[SCHEMA — sent via structured output]\n{schema_content}" if schema_content else "",
        ] if s]

        return {
            "system_prompt": system_content,
            "schema_instructions": schema_content,
            "message_section": human_content,
            "full_prompt": PROMPT_SEPARATOR.join(parts)
        }

    def _build_prompt_template(self) -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages([  
            ("system", self.SYSTEM_PROMPT),
            ("human", "{context}{message}"),
        ])

    @classmethod
    def _build_prompt_template_for_preview(cls, system_prompt_override: str | None = None) -> ChatPromptTemplate:
        # classmethod: build_preview runs without an agent instance (no LLM).
        return ChatPromptTemplate.from_messages([
            ("system", system_prompt_override or cls._get_system_prompt_for_preview()),
            ("human", "{context}{message}"),
        ])
        
    @classmethod
    def _get_system_prompt_for_preview(cls) -> str:
        return cls.SYSTEM_PROMPT

    def _build_chain(self, client: BaseChatModel) -> Runnable:
        if self.RESPONSE_SCHEMA is not None:
            return self._prompt | client.with_structured_output(self.RESPONSE_SCHEMA)
        return self._prompt | client

    def _build_prompt_trace(self, message: str, raw_context: str) -> dict:
        return build_prompt_trace(
            system_prompt=self.SYSTEM_PROMPT,
            response_schema=self.RESPONSE_SCHEMA,
            message=message,
            raw_context=raw_context,
        )

    def _build_runtime_trace(self, result, started_at: datetime, ended_at: datetime, latency_ms: float) -> dict:
        return build_runtime_trace(
            llm=self.client,
            context_provider=self._context_provider,
            result=result,
            started_at=started_at,
            ended_at=ended_at,
            latency_ms=latency_ms,
        )

    def _get_raw_context(self, paper_path: str | None) -> str:
        if not paper_path or not self._context_provider:
            return ""
        return self._context_provider.get_context(paper_path)

    @staticmethod
    def _format_context_block(raw_context: str) -> str:
        return format_context_block(raw_context)

    @staticmethod
    def _extract_payload(result) -> BaseModel:
        if isinstance(result, BaseModel):
            return result
        return RawResponse(response=str(result.content))
