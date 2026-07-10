from domain.graph.state import ReviewState, compact_reviews, last_reviews
from models.agent import AreaChairStyle

_STYLE_MODIFIER = {
    AreaChairStyle.AUTHORITARIAN: (
        "You rely primarily on your own expert assessment of the paper. "
        "Reviewer ratings and the meta-reviewer recommendation are secondary inputs - "
        "you may override them if your judgment differs."
    ),
    AreaChairStyle.CONFORMIST: (
        "You defer strongly to the consensus of the reviewer ratings and the meta-reviewer recommendation. "
        "You minimize the influence of your own independent judgment and follow the reviewers' lead."
    ),
    AreaChairStyle.INCLUSIVE: (
        "You carefully consider all available information: individual reviews, the author rebuttal, "
        "the meta-reviewer recommendation, and your own expertise. "
        "You weigh all perspectives before making a balanced final decision."
    ),
}

_BASE_SYSTEM_PROMPT_V1 = (
    "You are an Area Chair (AC) for the International Conference on Learning Representations (ICLR). "
    "You receive the peer reviews, the author rebuttal, and the meta-reviewer's recommendation. "
    "Your task is to produce the final, binding acceptance decision for the paper. "
    "The decision must be one of: accept, minor_revision, major_revision, reject. "
    "Be fair, concise, and justify your decision clearly."
)


def build_system_prompt(style: AreaChairStyle, base_template: str | None = None) -> str:
    return f"{base_template or _BASE_SYSTEM_PROMPT_V1} {_STYLE_MODIFIER[style]}"


def build_message(state: ReviewState) -> str:
    meta = state.get("meta_review") or {}
    meta_block = (
        f"score={meta.get('overall_score')} recommendation={meta.get('recommendation')}\n"
        f"{meta.get('summary', '')}"
    )
    rebuttal_block = ""
    author_response = state.get("author_response")
    if author_response:
        rebuttal_block = f"\n\nAuthor rebuttal:\n{author_response.get('rebuttal', '')}"

    return (
        f"Peer reviews:\n{compact_reviews(last_reviews(state))}\n\n"
        f"Meta-reviewer recommendation:\n{meta_block}"
        f"{rebuttal_block}\n\n"
        "Make the final acceptance decision for this paper."
    )
