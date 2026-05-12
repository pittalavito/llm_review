import sys

from agent.prompting.area_chair import build_system_prompt as build_area_chair_system_prompt
from agent.prompting.author import build_system_prompt as build_author_system_prompt
from agent.prompting.meta_reviewer import build_system_prompt as build_meta_reviewer_system_prompt
from agent.prompting.reviewer import build_system_prompt as build_reviewer_system_prompt
from agent.prompting.reviewer import get_rag_focus as get_reviewer_rag_focus
from models.agent import (
    AreaChairStyle,
    ReviewerCommitment,
    ReviewerFocus,
    ReviewerIntention,
    ReviewerKnowledgeability,
    ReviewerPersona,
)

sys.path.insert(0, "src")


class TestPromptBuilders:

    def test_reviewer_prompt_changes_with_persona(self):
        benign = ReviewerPersona(intention=ReviewerIntention.BENIGN)
        malicious = ReviewerPersona(intention=ReviewerIntention.MALICIOUS)

        benign_prompt = build_reviewer_system_prompt(benign)
        malicious_prompt = build_reviewer_system_prompt(malicious)

        assert benign_prompt != malicious_prompt
        assert "reject" in malicious_prompt.lower()

    def test_reviewer_prompt_contains_focus_modifier(self):
        persona = ReviewerPersona(focus=ReviewerFocus.EMPIRICAL)
        prompt = build_reviewer_system_prompt(persona)

        assert "empirical validation" in prompt.lower()

    def test_reviewer_rag_focus_returns_terms_and_sections(self):
        persona = ReviewerPersona(focus=ReviewerFocus.SOUNDNESS)
        terms, sections = get_reviewer_rag_focus(persona)

        assert "theorem" in terms
        assert sections == ["methods", "related_work"]

    def test_area_chair_prompt_changes_by_style(self):
        authoritarian = build_area_chair_system_prompt(AreaChairStyle.AUTHORITARIAN)
        conformist = build_area_chair_system_prompt(AreaChairStyle.CONFORMIST)

        assert authoritarian != conformist
        assert "override" in authoritarian.lower() or "own" in authoritarian.lower()
        assert "consensus" in conformist.lower() or "defer" in conformist.lower()

    def test_meta_reviewer_prompt_contains_recommendation_space(self):
        prompt = build_meta_reviewer_system_prompt()
        assert "minor_revision" in prompt
        assert "major_revision" in prompt

    def test_author_prompt_contains_three_tasks(self):
        prompt = build_author_system_prompt()
        assert "1." in prompt
        assert "2." in prompt
        assert "3." in prompt

    def test_all_reviewer_persona_axes_are_supported(self):
        persona = ReviewerPersona(
            commitment=ReviewerCommitment.RESPONSIBLE,
            intention=ReviewerIntention.BENIGN,
            knowledgeability=ReviewerKnowledgeability.KNOWLEDGEABLE,
            focus=ReviewerFocus.NOVELTY,
        )
        prompt = build_reviewer_system_prompt(persona)
        assert "novelty and impact" in prompt.lower()
