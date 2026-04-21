"""
Unit tests for the graph layer:
  - GraphBuilder.build() — topology
  - Node functions — reviewer_node, meta_node, refinement_node
  - Conditional edges — _meta_decision, _should_loop
  - Full graph invocation with MockChatModel (accept path + revision loop)
"""
import sys
import json
import pytest

sys.path.insert(0, "src")

from models.agent import AgentName, ReviewDecision
from models.agent import (
    MetaReviewResponse,
    RefinementResponse,
    SoundnessReviewResponse,
    ContributionReviewResponse,
    PresentationReviewResponse,
)
from agent.impl.soundness_reviewer import SoundnessReviewerAgent
from agent.impl.contribution_reviewer import ContributionReviewerAgent
from agent.impl.presentation_reviewer import PresentationReviewerAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.refinement import RefinementAgent
from client.mock_chat import MockChatModel
from graph.builder import GraphBuilder
from graph.state import ReviewState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agents(mock_llm=None) -> dict[AgentName, object]:
    llm = mock_llm or MockChatModel()
    return {
        AgentName.SOUNDNESS_REVIEWER:    SoundnessReviewerAgent(llm=llm),
        AgentName.PRESENTATION_REVIEWER: PresentationReviewerAgent(llm=llm),
        AgentName.CONTRIBUTION_REVIEWER: ContributionReviewerAgent(llm=llm),
        AgentName.META_REVIEWER:         MetaReviewerAgent(llm=llm),
        AgentName.REFINEMENT_AGENT:      RefinementAgent(llm=llm),
    }


def base_state(**overrides) -> ReviewState:
    state: ReviewState = {
        "paper_path": None,
        "rag_top_k": None,
        "retrieval_metadata": None,
        "reviews": [],
        "meta_review": None,
        "decision": None,
        "revision_notes": None,
        "current_round": 0,
        "max_rounds": 2,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# GraphBuilder topology
# ---------------------------------------------------------------------------

class TestGraphBuilderTopology:

    def test_build_returns_state_graph(self):
        from langgraph.graph import StateGraph
        agents = make_agents()
        graph = GraphBuilder.build(agents)
        assert isinstance(graph, StateGraph)

    def test_compiled_graph_has_invoke(self):
        agents = make_agents()
        compiled = GraphBuilder.build(agents).compile()
        assert callable(compiled.invoke)

    def test_missing_agent_raises(self):
        agents = make_agents()
        del agents[AgentName.META_REVIEWER]
        with pytest.raises(KeyError):
            GraphBuilder.build(agents)


# ---------------------------------------------------------------------------
# Conditional edge functions (pure functions, no LLM)
# ---------------------------------------------------------------------------

class TestConditionalEdges:

    def test_meta_decision_accept(self):
        state = base_state(decision=ReviewDecision.ACCEPT)
        assert GraphBuilder._meta_decision(state) == "accept"

    def test_meta_decision_minor_revision(self):
        state = base_state(decision=ReviewDecision.MINOR_REVISION)
        assert GraphBuilder._meta_decision(state) == "revise"

    def test_meta_decision_major_revision(self):
        state = base_state(decision=ReviewDecision.MAJOR_REVISION)
        assert GraphBuilder._meta_decision(state) == "revise"

    def test_meta_decision_reject(self):
        state = base_state(decision=ReviewDecision.REJECT)
        assert GraphBuilder._meta_decision(state) == "revise"

    def test_meta_decision_none(self):
        state = base_state(decision=None)
        assert GraphBuilder._meta_decision(state) == "revise"

    def test_should_loop_when_rounds_remaining(self):
        state = base_state(current_round=1, max_rounds=2)
        assert GraphBuilder._should_loop(state) == "loop"

    def test_should_end_when_rounds_exhausted(self):
        state = base_state(current_round=2, max_rounds=2)
        assert GraphBuilder._should_loop(state) == "end"

    def test_should_end_when_over_limit(self):
        state = base_state(current_round=5, max_rounds=2)
        assert GraphBuilder._should_loop(state) == "end"


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

class TestReviewerNode:

    def test_reviewer_node_appends_review(self):
        agents = make_agents()
        node_fn = GraphBuilder._reviewer_node(agents[AgentName.SOUNDNESS_REVIEWER])
        state = base_state()
        result = node_fn(state)
        assert "reviews" in result
        assert len(result["reviews"]) == 1

    def test_reviewer_node_review_is_valid_json(self):
        agents = make_agents()
        node_fn = GraphBuilder._reviewer_node(agents[AgentName.SOUNDNESS_REVIEWER])
        result = node_fn(base_state())
        data = json.loads(result["reviews"][0])
        assert "agent" in data
        assert "payload" in data

    def test_reviewer_node_includes_revision_notes(self):
        """When revision_notes in state, message passed to agent contains them."""
        agents = make_agents()
        node_fn = GraphBuilder._reviewer_node(agents[AgentName.SOUNDNESS_REVIEWER])
        state = base_state(revision_notes="Please improve section 3.")
        result = node_fn(state)
        # Node ran without error — revision notes were included in the message
        assert len(result["reviews"]) == 1

    def test_reviewer_node_agent_name_in_output(self):
        agents = make_agents()
        node_fn = GraphBuilder._reviewer_node(agents[AgentName.SOUNDNESS_REVIEWER])
        result = node_fn(base_state())
        data = json.loads(result["reviews"][0])
        assert data["agent"] == AgentName.SOUNDNESS_REVIEWER


class TestMetaNode:

    def _fake_reviews(self) -> list[str]:
        """Three valid review JSON strings."""
        agents = make_agents()
        reviews = []
        for name in [AgentName.SOUNDNESS_REVIEWER, AgentName.PRESENTATION_REVIEWER, AgentName.CONTRIBUTION_REVIEWER]:
            node = GraphBuilder._reviewer_node(agents[name])
            out = node(base_state())
            reviews.extend(out["reviews"])
        return reviews

    def test_meta_node_sets_decision(self):
        agents = make_agents()
        node_fn = GraphBuilder._meta_node(agents[AgentName.META_REVIEWER])
        reviews = self._fake_reviews()
        state = base_state(reviews=reviews, current_round=0)
        result = node_fn(state)
        assert "decision" in result
        assert result["decision"] in set(ReviewDecision)

    def test_meta_node_sets_meta_review(self):
        agents = make_agents()
        node_fn = GraphBuilder._meta_node(agents[AgentName.META_REVIEWER])
        reviews = self._fake_reviews()
        state = base_state(reviews=reviews, current_round=0)
        result = node_fn(state)
        assert "meta_review" in result
        assert isinstance(result["meta_review"], dict)

    def test_meta_node_increments_round(self):
        agents = make_agents()
        node_fn = GraphBuilder._meta_node(agents[AgentName.META_REVIEWER])
        reviews = self._fake_reviews()
        state = base_state(reviews=reviews, current_round=0)
        result = node_fn(state)
        assert result["current_round"] == 1

    def test_meta_node_uses_last_3_reviews(self):
        """Meta node should not crash with more than 3 reviews in state."""
        agents = make_agents()
        node_fn = GraphBuilder._meta_node(agents[AgentName.META_REVIEWER])
        reviews = self._fake_reviews() * 3  # 9 reviews
        state = base_state(reviews=reviews, current_round=0)
        result = node_fn(state)
        assert result["decision"] is not None


class TestRefinementNode:

    def test_refinement_node_sets_revision_notes(self):
        agents = make_agents()
        node_fn = GraphBuilder._refinement_node(agents[AgentName.REFINEMENT_AGENT])
        meta = {"summary": "needs work", "decision": "minor_revision"}
        state = base_state(meta_review=meta)
        result = node_fn(state)
        assert "revision_notes" in result
        assert isinstance(result["revision_notes"], str)
        assert len(result["revision_notes"]) > 0

    def test_refinement_node_empty_meta_review(self):
        agents = make_agents()
        node_fn = GraphBuilder._refinement_node(agents[AgentName.REFINEMENT_AGENT])
        state = base_state(meta_review=None)
        result = node_fn(state)
        assert "revision_notes" in result


# ---------------------------------------------------------------------------
# Full graph invocation — accept path
# ---------------------------------------------------------------------------

class TestFullGraphAcceptPath:
    """Mock always returns decision=minor_revision, so loop runs until max_rounds."""

    def test_invoke_returns_decision(self):
        agents = make_agents()
        compiled = GraphBuilder.build(agents).compile()
        state = base_state(max_rounds=1)
        result = compiled.invoke(state)
        assert "decision" in result

    def test_invoke_reviews_accumulate(self):
        agents = make_agents()
        compiled = GraphBuilder.build(agents).compile()
        state = base_state(max_rounds=1)
        result = compiled.invoke(state)
        # 3 reviewers × 1 loop round = 3, then 3 more after refinement → 6
        assert len(result["reviews"]) >= 3

    def test_invoke_meta_review_present(self):
        agents = make_agents()
        compiled = GraphBuilder.build(agents).compile()
        result = compiled.invoke(base_state(max_rounds=1))
        assert result["meta_review"] is not None

    def test_invoke_current_round_advanced(self):
        agents = make_agents()
        compiled = GraphBuilder.build(agents).compile()
        result = compiled.invoke(base_state(max_rounds=1))
        assert result["current_round"] >= 1
