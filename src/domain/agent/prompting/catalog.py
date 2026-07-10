"""Default prompt seeds: the hardcoded templates shipped with the code,
registered into the prompt_version table at startup (idempotent upsert by
(agent_role, version_label) — existing rows are never overwritten).
"""
from domain.agent.prompting import reviewer
from domain.agent.prompting import area_chair, author, meta_reviewer

# (agent_role, version_label, template, description)
DEFAULT_PROMPT_SEEDS: list[tuple[str, str, str, str]] = [
    (
        "reviewer", "v1", reviewer._BASE_SYSTEM_PROMPT_V1,
        "Original ICLR reviewer base prompt",
    ),
    (
        "reviewer", "v2", reviewer._BASE_SYSTEM_PROMPT_V2,
        "Skeptical variant: verifies theoretical claims, calibrated ratings",
    ),
    (
        "meta_reviewer", "v1", meta_reviewer._SYSTEM_PROMPT_V1,
        "Original meta-reviewer prompt",
    ),
    (
        "area_chair", "v1", area_chair._BASE_SYSTEM_PROMPT_V1,
        "Original area-chair base prompt",
    ),
    (
        "author_agent", "v1", author._SYSTEM_PROMPT_V1,
        "Original author-agent prompt",
    ),
]
