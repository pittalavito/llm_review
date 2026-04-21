import json
import logging

from abc import ABC
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from models.agent import AgentName, AgentResponse

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

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.name = self.AGENT_NAME
        self._prompt = ChatPromptTemplate.from_messages([
            ("system", self.SYSTEM_PROMPT),
            ("human", "{message}"),
        ])
        self._chain: Runnable = self._build_chain(llm)

    def _build_chain(self, llm: BaseChatModel) -> Runnable:
        if self.RESPONSE_SCHEMA is not None:
            return self._prompt | llm.with_structured_output(self.RESPONSE_SCHEMA)
        return self._prompt | llm

    def run(self, message: str) -> str:
        normalized = message.strip()
        if not normalized:
            raise ValueError("Message must not be empty.")

        logger.info("Running agent '%s'", self.name)

        try:
            result = self._chain.invoke({"message": normalized})
        except Exception as exc:
            raise AgentValidationError(str(exc)) from exc

        if isinstance(result, BaseModel):
            payload = result.model_dump()
        else:
            payload = {"response": str(result.content)}

        envelope = AgentResponse(agent=self.name, payload=payload)
        return envelope.model_dump_json(ensure_ascii=False)

    def get_prompt_preview(self, message: str) -> str:
        """Format the actual messages sent to the LLM (for UI preview)."""
        messages = self._prompt.format_messages(message=message)
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
