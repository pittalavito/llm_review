import logging

from fastapi import APIRouter, HTTPException

from schemas.controller import HealthResponse, TestLlmRequest, TestLlmResponse
from schemas.enums import LlmModelName

from container import CONTAINER, CONFIG

logger = logging.getLogger(__name__)
router = APIRouter()

URL_HEALTH = "/health"
URL_MODELS = "/models"
URL_TEST_LLM = "/test-llm"
URL_TEST_AGENT = "/test-agent"

@router.get(URL_HEALTH, response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=CONFIG.app_version)


@router.get(URL_MODELS)
def list_models() -> list[LlmModelName]:
    return CONTAINER.list_llm_models()


@router.post(URL_TEST_LLM, response_model=TestLlmResponse)
def test_llm(req: TestLlmRequest) -> TestLlmResponse:
    try:
        llm_client = CONTAINER.get_llm_model(req.llm_model)
        response = llm_client.generate(req.message)
        return TestLlmResponse(response=response)
    except Exception as exc:
        logger.exception("LLM call failed for model '%s'", req.llm_model)
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}") from exc


@router.get(URL_TEST_AGENT)
def list_test_agents() -> list[str]:
    return ["Agent testing endpoint - to be implemented"]


@router.post(URL_TEST_AGENT)
def test_agent() -> str:
    return "Agent testing endpoint - to be implemented"