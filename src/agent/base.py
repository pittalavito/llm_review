import json
import logging

from abc import ABC
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from models.agent import AgentName, AgentResponse
from retrieval.protocols import ContextProvider

logger = logging.getLogger(__name__)


class AgentValidationError(ValueError):
    def __init__(self, message: str, raw_output: str = "") -> None:
        super().__init__(message)
        self.raw_output: str = raw_output


class BaseAgent(ABC):
    AGENT_NAME: AgentName
    SYSTEM_PROMPT: str = ""
    RESPONSE_SCHEMA: type[BaseModel] | None = None
    MESSAGE_LABEL: str = "Message"
    RAG_QUERY: str = ""
    RAG_SECTIONS: list[str] = []

    def __init__(self, llm: BaseChatModel, context_provider: ContextProvider | None = None):
        self.llm = llm
        self.name = self.AGENT_NAME
        self._context_provider = context_provider
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{context}{message}"),
        ])
        self._chain: Runnable = self._build_chain(llm)

    def _build_chain(self, llm: BaseChatModel) -> Runnable:
        if self.RESPONSE_SCHEMA is not None:
            return self._prompt | llm.with_structured_output(self.RESPONSE_SCHEMA)
        return self._prompt | llm

    def run(self, message: str, paper_path: str | None = None) -> str:
        normalized = message.strip()
        if not normalized:
            raise ValueError("Message must not be empty.")

        logger.info("Running agent '%s' (paper_path=%s)", self.name, paper_path)

        context_block = ""
        if paper_path and self._context_provider:
            raw_context = self._context_provider.get_context(paper_path)
            if raw_context:
                context_block = f"RETRIEVED CONTEXT:\n{raw_context}\n\n---\n\n"

        try:
            result = self._chain.invoke({"message": normalized, "context": context_block})
        except Exception as exc:
            raise AgentValidationError(str(exc)) from exc

        if isinstance(result, BaseModel):
            payload = result.model_dump()
        else:
            payload = {"response": str(result.content)}

        envelope = AgentResponse(agent=self.name, payload=payload)
        return envelope.model_dump_json(ensure_ascii=False)

    def get_prompt_preview(self, message: str, context: str = "") -> str:
        """Format the actual messages sent to the LLM (for UI preview)."""
        context_block = f"RETRIEVED CONTEXT:\n{context}\n\n---\n\n" if context else ""
        messages = self._prompt.format_messages(message=message, context=context_block)
        parts = []
        for msg in messages:
            role = msg.__class__.__name__.replace("Message", "").upper()
            parts.append(f"[{role}]\n{msg.content}")

        if self.RESPONSE_SCHEMA is not None:
            schema_json = json.dumps(
                self.RESPONSE_SCHEMA.model_json_schema(),
                ensure_ascii=False,
                indent=2,
            )
            parts.append(f"[SCHEMA — sent via structured output]\n{schema_json}")

        return "\n\n---\n\n".join(parts)
