
from llm_client.base_client import BaseLLMClient

from models.agent import ContributionReviewResponse, PresentationReviewResponse, SoundnessReviewResponse, MetaReviewResponse, RefinementResponse

MOCK_RESPONSE_PREFIX = "Here is a mock response for your prompt: "

# ---------------------------------------------------------------------------
# Mock responses (keyed by schema class name)
# ---------------------------------------------------------------------------

_MOCK_RESPONSES: dict[str, str] = {
    SoundnessReviewResponse.__name__: (
        '{"summary":"Il paper presenta una metodologia solida con esperimenti ben strutturati.",'
        '"strengths":["Protocollo sperimentale chiaro","Risultati ripetibili"],'
        '"weaknesses":["Analisi di sensitività limitata","Mancano dettagli sugli iperparametri"],'
        '"soundness_score":3,'
        '"confidence":4}'
    ),
    PresentationReviewResponse.__name__: (
        '{"summary":"Il paper è scritto in modo chiaro ma alcune sezioni potrebbero essere semplificate.",'
        '"strengths":["Abstract ben strutturato","Figure informative"],'
        '"weaknesses":["Sezione related work troppo densa","Alcuni grafici poco leggibili"],'
        '"presentation_score":3,'
        '"confidence":4}'
    ),
    ContributionReviewResponse.__name__: (
        '{"summary":"Il contributo è originale e rilevante per la comunità, ma non rivoluzionario.",'
        '"strengths":["Approccio novel al problema","Benchmark su dataset standard"],'
        '"weaknesses":["Comparazione con baseline limitata","Applicabilità non discussa"],'
        '"contribution_score":3,'
        '"confidence":3}'
    ),
    MetaReviewResponse.__name__: (
        '{"summary":"Il paper ha basi solide ma richiede revisioni prima dell\'accettazione.",'
        '"key_points":["Metodologia valida","Presentazione migliorabile","Contributo interessante ma non definitivo"],'
        '"overall_score":3,'
        '"decision":"minor_revision"}'
    ),
    RefinementResponse.__name__: (
        '{"revision_summary":"Il paper necessita di miglioramenti mirati su presentazione e analisi.",'
        '"priority_changes":["Aggiungere analisi di sensitività","Semplificare la sezione related work"],'
        '"suggested_improvements":["Fornire codice pubblico","Aggiungere discussion sulle limitazioni"]}'
    ),
}


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class MockLLMClient(BaseLLMClient):
    """Mock client per testare l'intero flusso senza dipendenze esterne."""

    def invoke(self, prompt: str) -> str:
        for class_name, response in _MOCK_RESPONSES.items():
            if class_name in prompt:
                return response
        return f"{MOCK_RESPONSE_PREFIX}{prompt}"
