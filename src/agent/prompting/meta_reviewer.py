from graph.nodes._factory import compact_reviews, last_reviews
from graph.state import ReviewState

_SYSTEM_PROMPT_V1 = (
    "You are an academic meta-reviewer. "
    "You receive the reviews from three peer reviewers "
    "and must produce an aggregated assessment with a recommendation for the Area Chair. "
    "The recommendation must be one of: accept, minor_revision, major_revision, reject. "
    "Consider the ratings, reasons for acceptance/rejection, and overall consensus. "
    "Be concise, fair, and justify your recommendation. Use a maximum of 500 words in the textual content."
)


def build_system_prompt() -> str:
    return _SYSTEM_PROMPT_V1


def build_message(state: ReviewState) -> str:
    return compact_reviews(last_reviews(state))
