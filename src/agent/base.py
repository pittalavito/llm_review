import json
import logging

from abc import ABC
from typing import Generic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel
from models.agent import AgentName, AgentResponse, RawResponse, T
from models.protocols import ContextProvider

logger = logging.getLogger(__name__)


_LOGGER_PREFIX = "[BaseAgent]"
_CONTEXT_HEADER = "RETRIEVED CONTEXT:"
_CONTEXT_SEPARATOR = "\n\n---\n\n"
_PROMPT_SEPARATOR = "\n\n---\n\n"


class AgentValidationError(ValueError):
    def __init__(self, message: str, raw_output: str = "") -> None:
        super().__init__(message)
        self.raw_output: str = raw_output


class BaseAgent(ABC, Generic[T]):
    AGENT_NAME: AgentName
    SYSTEM_PROMPT: str = ""
    RESPONSE_SCHEMA: type[T] | None = None
    RAG_QUERY: str = ""
    RAG_SECTIONS: list[str] = []

    def __init__(self, client: BaseChatModel, context_provider: ContextProvider | None = None):
        self.client = client
        self.name = self.AGENT_NAME
        self._context_provider = context_provider
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{context}{message}"),
        ])
        self._chain: Runnable = self._build_chain(client)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, message: str, paper_path: str | None = None) -> AgentResponse[T]:
        normalized = message.strip()
        if not normalized:
            raise ValueError("Message must not be empty.")

        logger.info(f"{_LOGGER_PREFIX} Running agent '{self.name}' with message: {normalized[:20]} (paper_path={paper_path})")

        raw_context = self._get_raw_context(paper_path)
        context_block = self._format_context_block(raw_context)

        try:
            logger.info(f"{_LOGGER_PREFIX} Invoking chain for agent '{self.name}' with message: {normalized[:20]} and context length: {len(context_block)}")
            result = self._chain.invoke({"message": normalized, "context": context_block})
        except Exception as exc:
            raise AgentValidationError(str(exc)) from exc

        payload = self._extract_payload(result)
        logger.info(f"{_LOGGER_PREFIX} Agent '{self.name}' produced raw result: {str(result)[:20]}")        
        return AgentResponse(
            agent=self.name,
            payload=payload,
            input_message=normalized,
            context_used=raw_context or None,
        )

    @classmethod
    def build_preview(cls, message: str, context: str = "") -> dict:
        """Build prompt preview from class constants — no LLM instance needed."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", cls.SYSTEM_PROMPT),
            ("human", "{context}{message}"),
        ])
        context_block = cls._format_context_block(context)
        messages = prompt.format_messages(message=message, context=context_block)

        system_content = cls._extract_message_content(messages, SystemMessage)
        human_content = cls._extract_message_content(messages, HumanMessage)
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
            "full_prompt": _PROMPT_SEPARATOR.join(parts),
        }

    def get_prompt_preview(self, message: str, context: str = "") -> dict:
        """Return prompt parts as a structured dict (for UI preview)."""
        return self.__class__.build_preview(message, context)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_chain(self, client: BaseChatModel) -> Runnable:
        if self.RESPONSE_SCHEMA is not None:
            return self._prompt | client.with_structured_output(self.RESPONSE_SCHEMA)
        return self._prompt | client

    def _get_raw_context(self, paper_path: str | None) -> str:
        if not paper_path or not self._context_provider:
            return ""
        return self._context_provider.get_context(paper_path)

    @staticmethod
    def _format_context_block(raw_context: str) -> str:
        if not raw_context or not raw_context.strip():
            return ""
        return f"{_CONTEXT_HEADER}\n{raw_context}{_CONTEXT_SEPARATOR}"

    @staticmethod
    def _extract_payload(result) -> BaseModel:
        if isinstance(result, BaseModel):
            return result
        return RawResponse(response=str(result.content))

    @staticmethod
    def _extract_message_content(messages: list[BaseMessage], msg_type: type) -> str:
        for msg in messages:
            if isinstance(msg, msg_type):
                return msg.content
        return ""

