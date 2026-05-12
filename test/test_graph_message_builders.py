from agent.prompting.area_chair import build_message as build_area_chair_message
from agent.prompting.author import build_message as build_author_message
from agent.prompting.meta_reviewer import build_message as build_meta_message
from agent.prompting.reviewer import build_message as build_reviewer_message
from models.agent import AgentName


def _base_state(**overrides):
    state = {
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


class TestGraphMessageBuilders:

    def test_build_reviewer_message_base(self):
        state = _base_state()
        msg = build_reviewer_message(state, AgentName.REVIEWER_1)
        assert "structured review" in msg.lower()

    def test_build_reviewer_message_includes_targeted_rebuttal(self):
        state = _base_state(author_response={
            "rebuttal": "general",
            "reviewer_rebuttals": [
                {"reviewer_name": "reviewer_1", "response": "targeted one"},
            ],
            "revised_sections": [],
            "key_changes": [],
        })
        msg = build_reviewer_message(state, AgentName.REVIEWER_1)
        assert "targeted one" in msg

    def test_build_meta_message_compacts_last_three_reviews(self):
        reviews = [
            '{"agent":"reviewer_1","payload":{"rating":7,"confidence":3,"summary":"s1","significance_and_novelty":"n1","reasons_for_acceptance":[],"reasons_for_rejection":[]}}',
            '{"agent":"reviewer_2","payload":{"rating":8,"confidence":4,"summary":"s2","significance_and_novelty":"n2","reasons_for_acceptance":[],"reasons_for_rejection":[]}}',
            '{"agent":"reviewer_3","payload":{"rating":6,"confidence":2,"summary":"s3","significance_and_novelty":"n3","reasons_for_acceptance":[],"reasons_for_rejection":[]}}',
        ]
        state = _base_state(reviews=reviews)
        msg = build_meta_message(state)
        assert "[reviewer_1]" in msg
        assert "summary:" in msg

    def test_build_author_message_contains_sections(self):
        reviews = [
            '{"agent":"reviewer_1","payload":{"rating":7}}',
            '{"agent":"reviewer_2","payload":{"rating":8}}',
            '{"agent":"reviewer_3","payload":{"rating":6}}',
        ]
        state = _base_state(
            reviews=reviews,
            meta_review={"summary": "meta"},
            area_chair_response={"decision": "minor_revision"},
        )
        msg = build_author_message(state)
        assert "Meta-reviewer summary" in msg
        assert "Area Chair decision" in msg

    def test_build_area_chair_message_contains_meta_and_reviews(self):
        reviews = [
            '{"agent":"reviewer_1","payload":{"rating":7,"confidence":3,"summary":"s1","significance_and_novelty":"n1","reasons_for_acceptance":[],"reasons_for_rejection":[]}}',
            '{"agent":"reviewer_2","payload":{"rating":8,"confidence":4,"summary":"s2","significance_and_novelty":"n2","reasons_for_acceptance":[],"reasons_for_rejection":[]}}',
            '{"agent":"reviewer_3","payload":{"rating":6,"confidence":2,"summary":"s3","significance_and_novelty":"n3","reasons_for_acceptance":[],"reasons_for_rejection":[]}}',
        ]
        state = _base_state(
            reviews=reviews,
            meta_review={"overall_score": 7.0, "recommendation": "minor_revision", "summary": "meta sum"},
            author_response={"rebuttal": "we fixed issues"},
        )
        msg = build_area_chair_message(state)
        assert "Meta-reviewer recommendation" in msg
        assert "Author rebuttal" in msg
