from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from models.agent import (
    AreaChairResponse,
    AuthorResponse,
    MetaReviewResponse,
    ReviewerRebuttal,
    ReviewerResponse,
    RevisedSection,
)


_MOCK_INSTANCES: dict[type[BaseModel], BaseModel] = {
    ReviewerResponse: ReviewerResponse(
        summary="Solid approach, clear experiments, reasonable scope.",
        significance_and_novelty="Original contribution with respect to prior art.",
        reasons_for_acceptance=["Rigorous methodology", "Convincing results", "Clear presentation"],
        reasons_for_rejection=["Limited sensitivity analysis", "Weak baseline coverage"],
        suggestions=["Add ablation study", "Expand related work"],
        rating=6,
        confidence=4,
    ),
    MetaReviewResponse: MetaReviewResponse(
        summary="Solid foundations but revisions needed before acceptance.",
        key_points=["Methodology valid", "Presentation improvable", "Contribution interesting"],
        overall_score=6,
        recommendation="minor_revision",
    ),
    AreaChairResponse: AreaChairResponse(
        summary="Reviewer concerns are moderate and addressable; minor revision required.",
        justification="Contribution is valid; concerns can be addressed with limited rework.",
        decision="minor_revision",
        confidence=4,
    ),
    AuthorResponse: AuthorResponse(
        rebuttal="We thank the reviewers; revisions address all major concerns.",
        reviewer_rebuttals=[
            ReviewerRebuttal(reviewer_name=f"reviewer_{i}", response=f"Targeted response to reviewer {i}.")
            for i in (1, 2, 3)
        ],
        revised_sections=[
            RevisedSection(section_name="methods", content="Expanded methods section with hyperparameters."),
            RevisedSection(section_name="results", content="Added sensitivity analysis and extra baselines."),
        ],
        key_changes=["Sensitivity analysis", "Hyperparameter details", "Additional baselines"],
    ),
}

_MOCK_JSON: dict[type[BaseModel], str] = {
    schema: instance.model_dump_json(ensure_ascii=False)
    for schema, instance in _MOCK_INSTANCES.items()
}


class MockChatModel(BaseChatModel):
    """LangChain-compatible mock that returns hardcoded responses without any LLM call."""

    @property
    def _llm_type(self) -> str:
        return "mock"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        content = self._pick_json(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def with_structured_output(self, schema: type[BaseModel], **kwargs) -> Any:
        instance = _MOCK_INSTANCES.get(schema)
        if instance is not None:
            return RunnableLambda(lambda _: instance)
        return super().with_structured_output(schema, **kwargs)

    @staticmethod
    def _pick_json(messages: list[BaseMessage]) -> str:
        combined = " ".join(str(m.content) for m in messages)
        for schema, payload in _MOCK_JSON.items():
            if schema.__name__ in combined:
                return payload
        return "{}"
