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
import json

from pydantic import BaseModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from agent.base import BaseAgent
from agent.impl.reviewer_agent import ReviewerAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.area_chair_agent import AreaChairAgent
from agent.impl.author_agent import AuthorAgent
from client.mock_chat import MockChatModel
from models.agent import (
    AgentName,
    AgentResponse,
    AreaChairResponse,
    AreaChairStyle,
    RawResponse,
    ReviewerCommitment,
    ReviewerIntention,
    ReviewerKnowledgeability,
    ReviewerPersona,
    ReviewerResponse,
    MetaReviewResponse,
    AuthorResponse,
)

sys.path.insert(0, "src")

# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

class SimpleResponse(BaseModel):
    value: str


class ConcreteAgent(BaseAgent[SimpleResponse]):
    """Minimal concrete agent for testing BaseAgent behaviour."""
    AGENT_NAME = AgentName.REVIEWER_1
    SYSTEM_PROMPT = "You are a test agent."
    RESPONSE_SCHEMA = SimpleResponse
    RAG_QUERY = "test query"
    RAG_SECTIONS = ["methods"]


class NoSchemaAgent(BaseAgent[RawResponse]):
    """Agent with no structured output schema."""
    AGENT_NAME = AgentName.REVIEWER_1
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
        r = AgentResponse(agent=AgentName.REVIEWER_1, payload=SimpleResponse(value="x"))
        d = r.to_dict()
        assert d["agent"] == AgentName.REVIEWER_1

    def test_to_dict_contains_payload(self):
        r = AgentResponse(agent=AgentName.REVIEWER_1, payload=SimpleResponse(value="hello"))
        d = r.to_dict()
        assert d["payload"]["value"] == "hello"

    def test_to_json_is_string(self):
        r = AgentResponse(agent=AgentName.REVIEWER_1, payload=SimpleResponse(value="x"))
        assert isinstance(r.to_json(), str)

    def test_to_json_roundtrip(self):
        r = AgentResponse(agent=AgentName.REVIEWER_1, payload=SimpleResponse(value="roundtrip"))
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
        assert result.agent == AgentName.REVIEWER_1

    def test_run_without_paper_path_no_context(self, agent):
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

    def test_run_contains_runtime_metrics(self, agent):
        result = agent.run("analyse this paper")
        runtime = result.runtime_trace or {}
        metrics = runtime.get("metrics") or {}
        assert metrics.get("latency_ms") is not None
        assert metrics.get("started_at")
        assert metrics.get("ended_at")


class UsageMetadataMock(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "usage-mock"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        msg = AIMessage(
            content="ok",
            usage_metadata={"input_tokens": 12, "output_tokens": 7, "total_tokens": 19},
            response_metadata={"model_name": "usage-mock-model"},
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])


class TestProviderUsageTrace:

    def test_provider_usage_is_extracted(self):
        agent = NoSchemaAgent(client=UsageMetadataMock())
        result = agent.run("hello")
        runtime = result.runtime_trace or {}
        usage = runtime.get("provider_usage") or {}
        assert usage.get("total_tokens") == 19

    def test_provider_metadata_is_extracted(self):
        agent = NoSchemaAgent(client=UsageMetadataMock())
        result = agent.run("hello")
        runtime = result.runtime_trace or {}
        metadata = runtime.get("provider_metadata") or {}
        assert metadata.get("model_name") == "usage-mock-model"


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

    def test_reviewer_1_returns_typed_payload(self, mock_llm):
        agent = ReviewerAgent(client=mock_llm, agent_name=AgentName.REVIEWER_1)
        result = agent.run("review this paper")
        assert isinstance(result.payload, ReviewerResponse)

    def test_reviewer_2_returns_typed_payload(self, mock_llm):
        agent = ReviewerAgent(client=mock_llm, agent_name=AgentName.REVIEWER_2)
        result = agent.run("review this paper")
        assert isinstance(result.payload, ReviewerResponse)

    def test_reviewer_3_returns_typed_payload(self, mock_llm):
        agent = ReviewerAgent(client=mock_llm, agent_name=AgentName.REVIEWER_3)
        result = agent.run("review this paper")
        assert isinstance(result.payload, ReviewerResponse)

    def test_meta_reviewer_returns_typed_payload(self, mock_llm):
        agent = MetaReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert isinstance(result.payload, MetaReviewResponse)

    def test_author_agent_returns_typed_payload(self, mock_llm):
        agent = AuthorAgent(client=mock_llm)
        result = agent.run("respond to these reviews")
        assert isinstance(result.payload, AuthorResponse)

    def test_reviewer_agent_name_propagated(self, mock_llm):
        agent = ReviewerAgent(client=mock_llm, agent_name=AgentName.REVIEWER_2)
        result = agent.run("review this paper")
        assert result.agent == AgentName.REVIEWER_2

    def test_reviewer_response_has_rating(self, mock_llm):
        agent = ReviewerAgent(client=mock_llm, agent_name=AgentName.REVIEWER_1)
        result = agent.run("review this paper")
        assert 1 <= result.payload.rating <= 10

    def test_area_chair_returns_typed_payload(self, mock_llm):
        agent = AreaChairAgent(client=mock_llm)
        result = agent.run("make a decision")
        assert isinstance(result.payload, AreaChairResponse)

    def test_area_chair_decision_field(self, mock_llm):
        agent = AreaChairAgent(client=mock_llm)
        result = agent.run("make a decision")
        assert result.payload.decision in {"accept", "minor_revision", "major_revision", "reject"}

    def test_meta_reviewer_recommendation_field(self, mock_llm):
        agent = MetaReviewerAgent(client=mock_llm)
        result = agent.run("review this paper")
        assert result.payload.recommendation in {"accept", "minor_revision", "major_revision", "reject"}

    def test_to_json_serializable(self, mock_llm):
        agent = ReviewerAgent(client=mock_llm, agent_name=AgentName.REVIEWER_1)
        result = agent.run("review this paper")
        data = json.loads(result.to_json())
        assert "payload" in data


# ---------------------------------------------------------------------------
# Reviewer persona (bias experiments)
# ---------------------------------------------------------------------------

class TestReviewerPersona:

    @pytest.fixture
    def mock_llm(self):
        return MockChatModel()

    def test_malicious_persona_system_prompt_contains_biased(self, mock_llm):
        persona = ReviewerPersona(intention=ReviewerIntention.MALICIOUS)
        agent = ReviewerAgent(client=mock_llm, persona=persona, agent_name=AgentName.REVIEWER_1)
        assert "reject" in agent.SYSTEM_PROMPT.lower()

    def test_irresponsible_persona_system_prompt_contains_superficial(self, mock_llm):
        persona = ReviewerPersona(commitment=ReviewerCommitment.IRRESPONSIBLE)
        agent = ReviewerAgent(client=mock_llm, persona=persona, agent_name=AgentName.REVIEWER_1)
        assert "superficial" in agent.SYSTEM_PROMPT.lower() or "rushed" in agent.SYSTEM_PROMPT.lower()

    def test_unknowledgeable_persona_system_prompt_contains_limited(self, mock_llm):
        persona = ReviewerPersona(knowledgeability=ReviewerKnowledgeability.UNKNOWLEDGEABLE)
        agent = ReviewerAgent(client=mock_llm, persona=persona, agent_name=AgentName.REVIEWER_1)
        assert "limited" in agent.SYSTEM_PROMPT.lower()

    def test_different_personas_produce_different_prompts(self, mock_llm):
        benign = ReviewerAgent(
            client=mock_llm,
            persona=ReviewerPersona(intention=ReviewerIntention.BENIGN),
            agent_name=AgentName.REVIEWER_1,
        )
        malicious = ReviewerAgent(
            client=mock_llm,
            persona=ReviewerPersona(intention=ReviewerIntention.MALICIOUS),
            agent_name=AgentName.REVIEWER_1,
        )
        assert benign.SYSTEM_PROMPT != malicious.SYSTEM_PROMPT

    def test_area_chair_authoritarian_style(self, mock_llm):
        agent = AreaChairAgent(client=mock_llm, style=AreaChairStyle.AUTHORITARIAN)
        assert "own" in agent.SYSTEM_PROMPT.lower() or "override" in agent.SYSTEM_PROMPT.lower()

    def test_area_chair_conformist_style(self, mock_llm):
        agent = AreaChairAgent(client=mock_llm, style=AreaChairStyle.CONFORMIST)
        assert "defer" in agent.SYSTEM_PROMPT.lower() or "consensus" in agent.SYSTEM_PROMPT.lower()

    def test_area_chair_inclusive_style(self, mock_llm):
        agent = AreaChairAgent(client=mock_llm, style=AreaChairStyle.INCLUSIVE)
        assert "all" in agent.SYSTEM_PROMPT.lower() or "balanced" in agent.SYSTEM_PROMPT.lower()
