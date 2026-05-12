import json

from graph.nodes._factory import last_reviews
from graph.state import ReviewState

_SYSTEM_PROMPT = (
    "You are the author of a scientific paper that has just received peer reviews. "
    "Your task is to respond to the reviewers' critiques in three ways:\n"
    "1. Write a brief general rebuttal summarizing your overall response.\n"
    "2. Write a targeted response to EACH individual reviewer addressing their specific concerns "
    "(use the reviewer's name as provided, e.g. 'reviewer_1').\n"
    "3. Revise the weakest sections of your paper to address the most critical concerns. "
    "For each revised section, produce a complete rewritten version of that section's text.\n"
    "Be constructive, precise, and scientific in tone. "
    "Focus on the most impactful weaknesses identified. Use a maximum of 600 words total."
)


def build_system_prompt() -> str:
    return _SYSTEM_PROMPT


def build_message(state: ReviewState) -> str:
    labeled = [
        f"[{r.get('agent', 'unknown_reviewer').upper()}]\n"
        f"{json.dumps(r['payload'], ensure_ascii=False, indent=2)}"
        for r in last_reviews(state)
    ]
    reviews_block = "\n\n".join(labeled)
    meta = json.dumps(state.get("meta_review") or {}, ensure_ascii=False, indent=2)
    ac = json.dumps(state.get("area_chair_response") or {}, ensure_ascii=False, indent=2)

    return (
        f"You have received the following peer reviews:\n\n{reviews_block}\n\n"
        f"Meta-reviewer summary:\n{meta}\n\n"
        f"Area Chair decision:\n{ac}\n\n"
        "Write a general rebuttal, a targeted response to EACH reviewer by name, "
        "and provide revised versions of the sections that need improvement."
    )
