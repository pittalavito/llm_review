from graph.nodes._factory import targeted_rebuttal
from graph.state import ReviewState
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

_FOCUS_MODIFIER = {
    ReviewerFocus.SOUNDNESS: "Focus: theoretical soundness - proofs, assumptions, mathematical rigor.",
    ReviewerFocus.EMPIRICAL: "Focus: empirical validation - experiments, baselines, reproducibility.",
    ReviewerFocus.NOVELTY: "Focus: novelty and impact - originality, related work, field influence.",
}

_FOCUS_RAG_TERMS = {
    ReviewerFocus.SOUNDNESS: "theorem proof lemma assumption formal analysis mathematical rigor",
    ReviewerFocus.EMPIRICAL: "experiment results evaluation baseline dataset reproducibility ablation",
    ReviewerFocus.NOVELTY: "related work novelty contribution state of the art impact limitation",
}

_FOCUS_RAG_SECTIONS = {
    ReviewerFocus.SOUNDNESS: ["methods", "related_work"],
    ReviewerFocus.EMPIRICAL: ["experiments", "results"],
    ReviewerFocus.NOVELTY: ["introduction", "related_work", "conclusion"],
}

_BASE_SYSTEM_PROMPT = (
    "You are a peer reviewer for an ML/NLP conference. "
    "Evaluate the paper critically and specifically. "
    "Be concrete, professional. Max 300 words."
)


def build_system_prompt(persona: ReviewerPersona) -> str:
    return (
        f"{_BASE_SYSTEM_PROMPT} "
        f"{_FOCUS_MODIFIER[persona.focus]} "
        f"{_COMMITMENT_MODIFIER[persona.commitment]} "
        f"{_INTENTION_MODIFIER[persona.intention]} "
        f"{_KNOWLEDGEABILITY_MODIFIER[persona.knowledgeability]}"
    )


def get_rag_focus(persona: ReviewerPersona) -> tuple[str, list[str]]:
    return _FOCUS_RAG_TERMS[persona.focus], _FOCUS_RAG_SECTIONS[persona.focus]


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
