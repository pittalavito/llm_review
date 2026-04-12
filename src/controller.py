import logging

from fastapi import APIRouter, HTTPException, Request
from clients.llm.base_llm_client import BaseLLMClient
from service.llm_remote_service import LLMRemoteService
from schemas.controller import HealthResponse, TestLlmRequest, TestLlmResponse
from schemas.enums import LlmModelName
from container import get_llm_remote_service, get_settings

URL_HEALTH = "/health"
URL_MODELS = "/models"
URL_TEST_LLM = "/test-llm"
URL_TEST_AGENT = "/test-agent"

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(URL_HEALTH, response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    settings = get_settings(request)
    return HealthResponse(status="ok", version=settings.app_version)


@router.get(URL_MODELS)
def list_models(request: Request) -> list[LlmModelName]:
    service: LLMRemoteService = get_llm_remote_service(request)
    return service.list_llm_models()


@router.post(URL_TEST_LLM, response_model=TestLlmResponse)
def test_llm(request: Request, body: TestLlmRequest) -> TestLlmResponse:
    try:
        service: LLMRemoteService = get_llm_remote_service(request)
        client: BaseLLMClient = service.get_llm_model(body.llm_model)        
        response = client.call(body.message)
        return TestLlmResponse(response=response)
    except Exception as exc:
        logger.exception("LLM call failed for model '%s'", body.llm_model)
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}") from exc


@router.get(URL_TEST_AGENT)
def list_test_agents() -> list[str]:
    return ["Agent testing endpoint - to be implemented"]


@router.post(URL_TEST_AGENT)
def test_agent() -> str:
    return "Agent testing endpoint - to be implemented"