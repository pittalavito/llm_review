from typing import Any, Iterator
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel

from models.agent import (
    ContributionReviewResponse,
    MetaReviewResponse,
    PresentationReviewResponse,
    RefinementResponse,
    SoundnessReviewResponse,
)

_MOCK_INSTANCES: dict[type[BaseModel], BaseModel] = {
    SoundnessReviewResponse: SoundnessReviewResponse(
        summary="Il paper presenta una metodologia solida con esperimenti ben strutturati.",
        strengths=["Protocollo sperimentale chiaro", "Risultati ripetibili"],
        weaknesses=["Analisi di sensitività limitata", "Mancano dettagli sugli iperparametri"],
        soundness_score=3,
        confidence=4,
    ),
    PresentationReviewResponse: PresentationReviewResponse(
        summary="Il paper è scritto in modo chiaro ma alcune sezioni potrebbero essere semplificate.",
        strengths=["Abstract ben strutturato", "Figure informative"],
        weaknesses=["Sezione related work troppo densa", "Alcuni grafici poco leggibili"],
        presentation_score=3,
        confidence=4,
    ),
    ContributionReviewResponse: ContributionReviewResponse(
        summary="Il contributo è originale e rilevante per la comunità, ma non rivoluzionario.",
        strengths=["Approccio novel al problema", "Benchmark su dataset standard"],
        weaknesses=["Comparazione con baseline limitata", "Applicabilità non discussa"],
        contribution_score=3,
        confidence=3,
    ),
    MetaReviewResponse: MetaReviewResponse(
        summary="Il paper ha basi solide ma richiede revisioni prima dell'accettazione.",
        key_points=["Metodologia valida", "Presentazione migliorabile", "Contributo interessante ma non definitivo"],
        overall_score=3,
        decision="minor_revision",
    ),
    RefinementResponse: RefinementResponse(
        revision_summary="Il paper necessita di miglioramenti mirati su presentazione e analisi.",
        priority_changes=["Aggiungere analisi di sensitività", "Semplificare la sezione related work"],
        suggested_improvements=["Fornire codice pubblico", "Aggiungere discussion sulle limitazioni"],
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

    def _pick_json(self, messages: list[BaseMessage]) -> str:
        combined = " ".join(str(m.content) for m in messages)
        for schema, json_str in _MOCK_JSON.items():
            if schema.__name__ in combined:
                return json_str
        return "{}"
