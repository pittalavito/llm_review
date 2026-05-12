from agent.base import BaseAgent
from models.agent import (
    AgentName,
    ReviewerCommitment,
    ReviewerFocus,
    ReviewerIntention,
    ReviewerKnowledgeability,
    ReviewerPersona,
    ReviewerResponse,
)

_COMMITMENT_MODIFIER = {
    ReviewerCommitment.RESPONSIBLE:   "Be thorough and constructive.",
    ReviewerCommitment.IRRESPONSIBLE: "Be brief and superficial.",
}

_INTENTION_MODIFIER = {
    ReviewerIntention.BENIGN:    "Help the authors improve their work.",
    ReviewerIntention.MALICIOUS: "Look for reasons to reject.",
}

_KNOWLEDGEABILITY_MODIFIER = {
    ReviewerKnowledgeability.KNOWLEDGEABLE:   "You are an expert; identify subtle technical issues.",
    ReviewerKnowledgeability.UNKNOWLEDGEABLE: "You have limited expertise in this area.",
}

_FOCUS_MODIFIER = {
    ReviewerFocus.SOUNDNESS: "Focus: theoretical soundness — proofs, assumptions, mathematical rigor.",
    ReviewerFocus.EMPIRICAL: "Focus: empirical validation — experiments, baselines, reproducibility.",
    ReviewerFocus.NOVELTY:   "Focus: novelty and impact — originality, related work, field influence.",
}

_FOCUS_RAG_TERMS = {
    ReviewerFocus.SOUNDNESS: "theorem proof lemma assumption formal analysis mathematical rigor",
    ReviewerFocus.EMPIRICAL: "experiment results evaluation baseline dataset reproducibility ablation",
    ReviewerFocus.NOVELTY:   "related work novelty contribution state of the art impact limitation",
}

_FOCUS_RAG_SECTIONS = {
    ReviewerFocus.SOUNDNESS: ["methods", "related_work"],
    ReviewerFocus.EMPIRICAL: ["experiments", "results"],
    ReviewerFocus.NOVELTY:   ["introduction", "related_work", "conclusion"],
}

_BASE_PROMPT = (
    "You are a peer reviewer for an ML/NLP conference. "
    "Evaluate the paper critically and specifically. "
    "Be concrete, professional. Max 300 words."
)

_DEFAULT_PERSONA = ReviewerPersona()


class ReviewerAgent(BaseAgent[ReviewerResponse]):
    RESPONSE_SCHEMA = ReviewerResponse
    RAG_SECTIONS = []
    RAG_QUERY = None

    rag_focus_terms: str = ""
    rag_focus_sections: list[str] = []

    def __init__(
        self,
        client,
        context_provider=None,
        persona: ReviewerPersona | None = None,
        agent_name: AgentName = AgentName.REVIEWER_1,
    ):
        self.AGENT_NAME = agent_name
        p = persona or _DEFAULT_PERSONA
        self.SYSTEM_PROMPT = (
            f"{_BASE_PROMPT} "
            f"{_FOCUS_MODIFIER[p.focus]} "
            f"{_COMMITMENT_MODIFIER[p.commitment]} "
            f"{_INTENTION_MODIFIER[p.intention]} "
            f"{_KNOWLEDGEABILITY_MODIFIER[p.knowledgeability]}"
        )
        self.rag_focus_terms = _FOCUS_RAG_TERMS[p.focus]
        self.rag_focus_sections = _FOCUS_RAG_SECTIONS[p.focus]
        super().__init__(client, context_provider)
