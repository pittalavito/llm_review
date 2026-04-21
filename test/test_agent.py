"""
Unit tests for the agent layer:
  - BaseAgent (via a concrete stub)
  - AgentResponse serialization
  - ContextProvider integration
  - build_preview (no LLM needed)
  - MockChatModel wiring with each concrete agent
"""
import sys
import pytest

sys.path.insert(0, "src")

from pydantic import BaseModel
from models.agent import (
    AgentName,
    AgentResponse,
    RawResponse,
    SoundnessReviewResponse,
    ContributionReviewResponse,
    PresentationReviewResponse,
    MetaReviewResponse,
    RefinementResponse,
)
from agent.base import BaseAgent
from agent.impl.soundness_reviewer import SoundnessReviewerAgent
from agent.impl.contribution_reviewer import ContributionReviewerAgent
from agent.impl.presentation_reviewer import PresentationReviewerAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.refinement import RefinementAgent
from client.mock_chat import MockChatModel


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class SimpleResponse(BaseModel):
    value: str


class ConcreteAgent(BaseAgent[SimpleResponse]):
    """Minimal concrete agent for testing BaseAgent behaviour."""
    AGENT_NAME = AgentName.SOUNDNESS_REVIEWER
    SYSTEM_PROMPT = "You are a test agent."
    RESPONSE_SCHEMA = SimpleResponse
    RAG_QUERY = "test query"
    RAG_SECTIONS = ["methods"]


class NoSchemaAgent(BaseAgent[RawResponse]):
    """Agent with no structured output schema."""
    AGENT_NAME = AgentName.SOUNDNESS_REVIEWER
    SYSTEM_PROMPT = "Raw response agent."
    RESPONSE_SCHEMA = None
    RAG_QUERY = ""
    RAG_SECTIONS = []


class FakeContextProvider:
    def __init__(self, context: str = "chunk #1: relevant text"):
        self._context = context

    def get_context(self, paper_path: str) -> str:
        return self._context


# ---------------------------------------------------------------------------
# MockChatModel that returns a SimpleResponse JSON
# ---------------------------------------------------------------------------

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda


class SimpleResponseMock(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "simple-mock"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content='{"value": "ok"}'))])

    def with_structured_output(self, schema, **kwargs):
        if schema is SimpleResponse:
            return RunnableLambda(lambda _: SimpleResponse(value="ok"))
        return super().with_structured_output(schema, **kwargs)


# ---------------------------------------------------------------------------
# AgentResponse
# ---------------------------------------------------------------------------

class TestAgentResponse:

    def test_to_dict_contains_agent(self):
        r = AgentResponse(agent=AgentName.SOUNDNESS_REVIEWER, payload=SimpleResponse(value="x"))
        d = r.to_dict()
        assert d["agent"] == AgentName.SOUNDNESS_REVIEWER

    def test_to_dict_contains_payload(self):
        r = AgentResponse(agent=AgentName.SOUNDNESS_REVIEWER, payload=SimpleResponse(value="hello"))
        d = r.to_dict()
        assert d["payload"]["value"] == "hello"

    def test_to_json_is_string(self):
        r = AgentResponse(agent=AgentName.SOUNDNESS_REVIEWER, payload=SimpleResponse(value="x"))
        assert isinstance(r.to_json(), str)

    def test_to_json_roundtrip(self):
        import json
        r = AgentResponse(agent=AgentName.SOUNDNESS_REVIEWER, payload=SimpleResponse(value="roundtrip"))
        data = json.loads(r.to_json())
        assert data["payload"]["value"] == "roundtrip"


# ---------------------------------------------------------------------------
# BaseAgent — core behaviour
# ---------------------------------------------------------------------------

class TestBaseAgent:

    @pytest.fixture
    def agent(self):
        return ConcreteAgent(client=SimpleResponseMock())

    def test_run_returns_agent_response(self, agent):
        result = agent.run("analyse this paper")
        assert isinstance(result, AgentResponse)

    def test_run_payload_type(self, agent):
        result = agent.run("analyse this paper")
        assert isinstance(result.payload, SimpleResponse)

    def test_run_empty_message_raises(self, agent):
        with pytest.raises(ValueError):
            agent.run("   ")

    def test_run_agent_name_propagated(self, agent):
        result = agent.run("analyse this paper")
        assert result.agent == AgentName.SOUNDNESS_REVIEWER

    def test_run_without_paper_path_no_context(self, agent):
        # No paper_path → context block is empty → still works
        result = agent.run("analyse this paper")
        assert result is not None

    def test_run_with_context_provider(self):
        provider = FakeContextProvider("important finding from methods section")
        agent = ConcreteAgent(client=SimpleResponseMock(), context_provider=provider)
        result = agent.run("analyse this paper", paper_path="paper.pdf")
        assert isinstance(result.payload, SimpleResponse)

    def test_run_without_context_provider_ignores_paper_path(self):
        agent = ConcreteAgent(client=SimpleResponseMock(), context_provider=None)
        result = agent.run("analyse this paper", paper_path="paper.pdf")
        assert isinstance(result.payload, SimpleResponse)


# ---------------------------------------------------------------------------
# _format_context_block
# ---------------------------------------------------------------------------

class TestFormatContextBlock:

    def test_empty_string_returns_empty(self):
        assert ConcreteAgent._format_context_block("") == ""

    def test_whitespace_returns_empty(self):
        assert ConcreteAgent._format_context_block("   ") == ""

    def test_non_empty_includes_header(self):
        block = ConcreteAgent._format_context_block("some context")
        assert "RETRIEVED CONTEXT:" in block

    def test_non_empty_includes_content(self):
        block = ConcreteAgent._format_context_block("some context")
        assert "some context" in block

    def test_non_empty_ends_with_separator(self):
        block = ConcreteAgent._format_context_block("some context")
        assert block.endswith("---\n\n")


# ---------------------------------------------------------------------------
# build_preview (classmethod — no LLM instance)
# ---------------------------------------------------------------------------

class TestBuildPreview:

    def test_returns_dict_with_expected_keys(self):
        preview = ConcreteAgent.build_preview("review this paper")
        assert "system_prompt" in preview
        assert "message_section" in preview
        assert "full_prompt" in preview
        assert "schema_instructions" in preview

    def test_system_prompt_in_preview(self):
        preview = ConcreteAgent.build_preview("review this paper")
        assert "test agent" in preview["system_prompt"]

    def test_message_in_preview(self):
        preview = ConcreteAgent.build_preview("review this paper")
        assert "review this paper" in preview["message_section"]

    def test_schema_instructions_not_empty_when_schema_set(self):
        preview = ConcreteAgent.build_preview("review this paper")
        assert preview["schema_instructions"] != ""

    def test_no_schema_agent_schema_instructions_empty(self):
        preview = NoSchemaAgent.build_preview("review this paper")
        assert preview["schema_instructions"] == ""

    def test_context_injected_into_preview(self):
        preview = ConcreteAgent.build_preview("review this paper", context="relevant context chunk")
        assert "relevant context chunk" in preview["message_section"]


# ---------------------------------------------------------------------------
# Concrete agents with MockChatModel
# ---------------------------------------------------------------------------

class TestConcreteAgentsWithMock:

    @pytest.fixture
    def mock_llm(self):
        return MockChatModel()

    def test_soundness_reviewer_returns_typed_payload(self, mock_llm):
        agent = SoundnessReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert isinstance(result.payload, SoundnessReviewResponse)

    def test_contribution_reviewer_returns_typed_payload(self, mock_llm):
        agent = ContributionReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert isinstance(result.payload, ContributionReviewResponse)

    def test_presentation_reviewer_returns_typed_payload(self, mock_llm):
        agent = PresentationReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert isinstance(result.payload, PresentationReviewResponse)

    def test_meta_reviewer_returns_typed_payload(self, mock_llm):
        agent = MetaReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert isinstance(result.payload, MetaReviewResponse)

    def test_refinement_returns_typed_payload(self, mock_llm):
        agent = RefinementAgent(client=mock_llm)
        result = agent.run("refine this paper")
        assert isinstance(result.payload, RefinementResponse)

    def test_soundness_reviewer_agent_name(self, mock_llm):
        agent = SoundnessReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert result.agent == AgentName.SOUNDNESS_REVIEWER

    def test_meta_reviewer_decision_field(self, mock_llm):
        agent = MetaReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert result.payload.decision in {"accept", "minor_revision", "major_revision", "reject"}

    def test_to_json_serializable(self, mock_llm):
        import json
        agent = SoundnessReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        data = json.loads(result.to_json())
        assert "payload" in data
