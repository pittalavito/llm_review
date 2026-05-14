"""
Unit tests for the graph layer:
  - GraphBuilder.build() — topology
  - Node functions — reviewer_node, meta_node, author_node
  - Conditional edges — _ac_decision, _should_loop
  - Full graph invocation with MockChatModel (accept path + revision loop)
"""
import sys
import json
import pytest

from models.agent import AgentName, ReviewDecision
from agent.impl.reviewer_agent import ReviewerAgent
from agent.impl.meta_reviewer import MetaReviewerAgent
from agent.impl.area_chair_agent import AreaChairAgent
from agent.impl.author_agent import AuthorAgent
from client.mock_chat import MockChatModel
from graph.builder import GraphBuilder
from graph.edges import ac_decision, should_loop
from graph.nodes.area_chair import area_chair_node
from graph.nodes.author import author_node
from graph.nodes.meta import meta_node
from graph.nodes.reviewer import reviewer_node
from graph.state import ReviewState
from langgraph.graph import StateGraph


sys.path.insert(0, "src")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_agents(mock_llm=None) -> dict[AgentName, object]:
    llm = mock_llm or MockChatModel()
    return {
        AgentName.REVIEWER_1:    ReviewerAgent(client=llm, agent_name=AgentName.REVIEWER_1),
        AgentName.REVIEWER_2:    ReviewerAgent(client=llm, agent_name=AgentName.REVIEWER_2),
        AgentName.REVIEWER_3:    ReviewerAgent(client=llm, agent_name=AgentName.REVIEWER_3),
        AgentName.META_REVIEWER: MetaReviewerAgent(client=llm),
        AgentName.AREA_CHAIR:    AreaChairAgent(client=llm),
        AgentName.AUTHOR_AGENT:  AuthorAgent(client=llm),
    }


def base_state(**overrides) -> ReviewState:
    state: ReviewState = {
        "paper_path": None,
        "retrieval_metadata": None,
        "reviews": [],
        "meta_review": None,
        "area_chair_response": None,
        "decision": None,
        "author_response": None,
        "revised_sections": None,
        "current_round": 0,
        "max_rounds": 2,
        "agent_runs": [],
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_reviews() -> list[str]:
    """Three reviewer outputs — reused across TestAreaChairNode, TestMetaNode, TestAuthorNode."""
    agents = make_agents()
    reviews = []
    for name in [AgentName.REVIEWER_1, AgentName.REVIEWER_2, AgentName.REVIEWER_3]:
        node = reviewer_node(agents[name])
        reviews.extend(node(base_state())["reviews"])
    return reviews


# ---------------------------------------------------------------------------
# GraphBuilder topology
# ---------------------------------------------------------------------------

class TestGraphBuilderTopology:

    def test_build_returns_state_graph(self):
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

    def test_ac_decision_accept(self):
        state = base_state(decision=ReviewDecision.ACCEPT)
        assert ac_decision(state) == "accept"

    def test_ac_decision_minor_revision(self):
        state = base_state(decision=ReviewDecision.MINOR_REVISION)
        assert ac_decision(state) == "accept"

    def test_ac_decision_major_revision(self):
        state = base_state(decision=ReviewDecision.MAJOR_REVISION)
        assert ac_decision(state) == "revise"

    def test_ac_decision_reject(self):
        state = base_state(decision=ReviewDecision.REJECT)
        assert ac_decision(state) == "revise"

    def test_ac_decision_none(self):
        state = base_state(decision=None)
        assert ac_decision(state) == "revise"

    def test_should_loop_when_rounds_remaining(self):
        state = base_state(current_round=1, max_rounds=2)
        assert should_loop(state) == "loop"

    def test_should_end_when_rounds_exhausted(self):
        state = base_state(current_round=2, max_rounds=2)
        assert should_loop(state) == "end"

    def test_should_end_when_over_limit(self):
        state = base_state(current_round=5, max_rounds=2)
        assert should_loop(state) == "end"


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------

class TestReviewerNode:

    def test_reviewer_node_appends_review(self):
        agents = make_agents()
        node_fn = reviewer_node(agents[AgentName.REVIEWER_1])
        state = base_state()
        result = node_fn(state)
        assert "reviews" in result
        assert len(result["reviews"]) == 1

    def test_reviewer_node_review_is_valid_json(self):
        agents = make_agents()
        node_fn = reviewer_node(agents[AgentName.REVIEWER_1])
        result = node_fn(base_state())
        data = json.loads(result["reviews"][0])
        assert "agent" in data
        assert "payload" in data

    def test_reviewer_node_includes_author_response(self):
        agents = make_agents()
        node_fn = reviewer_node(agents[AgentName.REVIEWER_1])
        state = base_state(author_response={
            "rebuttal": "We have addressed all concerns.",
            "reviewer_rebuttals": [],
            "revised_sections": [{"section_name": "methods", "content": "Updated methods section."}],
            "key_changes": ["Updated methods"],
        })
        result = node_fn(state)
        assert len(result["reviews"]) == 1

    def test_reviewer_node_agent_name_in_output(self):
        agents = make_agents()
        node_fn = reviewer_node(agents[AgentName.REVIEWER_1])
        result = node_fn(base_state())
        data = json.loads(result["reviews"][0])
        assert data["agent"] == AgentName.REVIEWER_1


class TestAreaChairNode:

    def test_ac_node_sets_decision(self, fake_reviews):
        agents = make_agents()
        node_fn = area_chair_node(agents[AgentName.AREA_CHAIR])
        meta = {"summary": "needs work", "recommendation": "minor_revision"}
        state = base_state(meta_review=meta, reviews=fake_reviews, current_round=1)
        result = node_fn(state)
        assert "decision" in result
        assert result["decision"] in set(ReviewDecision)

    def test_ac_node_sets_area_chair_response(self, fake_reviews):
        agents = make_agents()
        node_fn = area_chair_node(agents[AgentName.AREA_CHAIR])
        state = base_state(meta_review={}, reviews=fake_reviews, current_round=1)
        result = node_fn(state)
        assert "area_chair_response" in result
        assert "justification" in result["area_chair_response"]

    def test_ac_node_includes_author_rebuttal_when_present(self, fake_reviews):
        agents = make_agents()
        node_fn = area_chair_node(agents[AgentName.AREA_CHAIR])
        state = base_state(
            meta_review={},
            reviews=fake_reviews,
            current_round=1,
            author_response={"rebuttal": "We addressed all concerns.", "revised_sections": [], "key_changes": []},
        )
        result = node_fn(state)
        assert result["decision"] is not None


class TestMetaNode:

    def test_meta_node_sets_recommendation(self, fake_reviews):
        agents = make_agents()
        node_fn = meta_node(agents[AgentName.META_REVIEWER])
        state = base_state(reviews=fake_reviews, current_round=0)
        result = node_fn(state)
        assert "meta_review" in result
        assert result["meta_review"].get("recommendation") in set(ReviewDecision)

    def test_meta_node_sets_meta_review(self, fake_reviews):
        agents = make_agents()
        node_fn = meta_node(agents[AgentName.META_REVIEWER])
        state = base_state(reviews=fake_reviews, current_round=0)
        result = node_fn(state)
        assert "meta_review" in result
        assert isinstance(result["meta_review"], dict)

    def test_meta_node_increments_round(self, fake_reviews):
        agents = make_agents()
        node_fn = meta_node(agents[AgentName.META_REVIEWER])
        state = base_state(reviews=fake_reviews, current_round=0)
        result = node_fn(state)
        assert result["current_round"] == 1

    def test_meta_node_uses_last_3_reviews(self, fake_reviews):
        agents = make_agents()
        node_fn = meta_node(agents[AgentName.META_REVIEWER])
        state = base_state(reviews=fake_reviews * 3, current_round=0)  # 9 reviews
        result = node_fn(state)
        assert result["meta_review"] is not None


class TestAuthorNode:

    def test_author_node_sets_author_response(self, fake_reviews):
        agents = make_agents()
        node_fn = author_node(agents[AgentName.AUTHOR_AGENT])
        meta = {"summary": "needs work", "recommendation": "minor_revision"}
        state = base_state(meta_review=meta, reviews=fake_reviews, current_round=1)
        result = node_fn(state)
        assert "author_response" in result
        assert isinstance(result["author_response"], dict)
        assert "rebuttal" in result["author_response"]
        assert "revised_sections" in result["author_response"]

    def test_author_node_has_per_reviewer_rebuttals(self, fake_reviews):
        agents = make_agents()
        node_fn = author_node(agents[AgentName.AUTHOR_AGENT])
        state = base_state(meta_review=None, reviews=fake_reviews, current_round=1)
        result = node_fn(state)
        rebuttals = result["author_response"].get("reviewer_rebuttals", [])
        assert isinstance(rebuttals, list)
        assert len(rebuttals) == 3
        names = {r["reviewer_name"] for r in rebuttals}
        assert names == {"reviewer_1", "reviewer_2", "reviewer_3"}

    def test_reviewer_node_uses_targeted_rebuttal(self):
        agents = make_agents()
        node_fn = reviewer_node(agents[AgentName.REVIEWER_1])
        state = base_state(author_response={
            "rebuttal": "general rebuttal",
            "reviewer_rebuttals": [
                {"reviewer_name": "reviewer_1", "response": "targeted for reviewer 1"},
                {"reviewer_name": "reviewer_2", "response": "targeted for reviewer 2"},
            ],
            "revised_sections": [],
            "key_changes": [],
        })
        result = node_fn(state)
        assert len(result["reviews"]) == 1

    def test_author_node_sets_revised_sections(self, fake_reviews):
        agents = make_agents()
        node_fn = author_node(agents[AgentName.AUTHOR_AGENT])
        state = base_state(meta_review=None, reviews=fake_reviews, current_round=1)
        result = node_fn(state)
        assert "revised_sections" in result
        assert isinstance(result["revised_sections"], dict)


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
