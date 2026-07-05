from dataclasses import dataclass, field

from graph.state import ReviewState, targeted_rebuttal
from models.agent import (
    AgentName,
    ReviewerCommitment,
    ReviewerFocus,
    ReviewerIntention,
    ReviewerKnowledgeability,
    ReviewerPersona,
)

_COMMITMENT_MODIFIER = {
    ReviewerCommitment.RESPONSIBLE: "Be thorough and constructive.",
    ReviewerCommitment.IRRESPONSIBLE: "Be brief and superficial.",
}

_INTENTION_MODIFIER = {
    ReviewerIntention.BENIGN: "Help the authors improve their work.",
    ReviewerIntention.MALICIOUS: "Look for reasons to reject.",
}

_KNOWLEDGEABILITY_MODIFIER = {
    ReviewerKnowledgeability.KNOWLEDGEABLE: "You are an expert; identify subtle technical issues.",
    ReviewerKnowledgeability.UNKNOWLEDGEABLE: "You have limited expertise in this area.",
}

@dataclass(frozen=True)
class FocusProfile:
    """Prompt modifier plus RAG hints tied to a reviewer focus."""
    modifier: str
    rag_terms: str
    rag_sections: list[str] = field(default_factory=list)


_FOCUS_PROFILES = {
    ReviewerFocus.SOUNDNESS: FocusProfile(
        modifier="Focus: theoretical soundness - proofs, assumptions, mathematical rigor.",
        rag_terms="theorem proof lemma assumption formal analysis mathematical rigor",
        rag_sections=["methods", "related_work"],
    ),
    ReviewerFocus.EMPIRICAL: FocusProfile(
        modifier="Focus: empirical validation - experiments, baselines, reproducibility.",
        rag_terms="experiment results evaluation baseline dataset reproducibility ablation",
        rag_sections=["experiments", "results"],
    ),
    ReviewerFocus.NOVELTY: FocusProfile(
        modifier="Focus: novelty and impact - originality, related work, field influence.",
        rag_terms="related work novelty contribution state of the art impact limitation",
        rag_sections=["introduction", "related_work", "conclusion"],
    ),
}

_BASE_SYSTEM_PROMPT_V1 = (
    "You are a peer reviewer for the International Conference on Learning Representations (ICLR). "
    "ICLR values rigorous theory, strong empirical evaluation, and advances in representation "
    "learning, deep learning, and reinforcement learning. "
    "Use the ICLR rating scale: 10=strong accept, 8=accept, "
    "6=marginally above threshold, 5=marginally below threshold, 3=reject, 1=strong reject. "
    "Be concrete and specific. Max 400 words."
)

_BASE_SYSTEM_PROMPT_V2 = (
    "You are a peer reviewer for the International Conference on Learning Representations (ICLR). "
    "ICLR values rigorous theory, strong empirical evaluation, and advances in representation "
    "learning, deep learning, and reinforcement learning. "
    "Use the ICLR rating scale: 10=strong accept, 8=accept, "
    "6=marginally above threshold, 5=marginally below threshold, 3=reject, 1=strong reject. "
    "Be skeptical of claimed theoretical guarantees: if the paper asserts a property "
    "(e.g. identifiability, convergence, optimality) verify that the stated assumptions "
    "actually entail it, and treat any unaddressed gap as a serious weakness, not a minor one. "
    "Calibrate ratings realistically: most ICLR submissions score 3-6; reserve 8-10 for "
    "contributions with no significant unaddressed flaws. "
    "Be concrete and specific. Max 400 words."
)


def build_system_prompt(persona: ReviewerPersona) -> str:
    return (
        f"{_BASE_SYSTEM_PROMPT_V1} "
        f"{_FOCUS_PROFILES[persona.focus].modifier} "
        f"{_COMMITMENT_MODIFIER[persona.commitment]} "
        f"{_INTENTION_MODIFIER[persona.intention]} "
        f"{_KNOWLEDGEABILITY_MODIFIER[persona.knowledgeability]}"
    )


def get_rag_focus(persona: ReviewerPersona) -> tuple[str, list[str]]:
    profile = _FOCUS_PROFILES[persona.focus]
    return profile.rag_terms, profile.rag_sections


def build_message(state: ReviewState, agent_name: AgentName) -> str:
    message = "Analyze the paper and provide a structured review."
    author_response = state.get("author_response")
    if not author_response:
        return message

    rebuttal = targeted_rebuttal(author_response, agent_name)
    if rebuttal:
        message += f"\n\nAuthor's response to your review:\n{rebuttal}"

    revised = author_response.get("revised_sections", [])
    if revised:
        sections_text = "\n\n".join(
            f"[Revised {s['section_name'].upper()}]\n{s['content']}" for s in revised
        )
        message += f"\n\nRevised paper sections submitted by the author:\n{sections_text}"
    return message
