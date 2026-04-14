import logging

from container import inject_graph_service, inject_llm_service, inject_settings
from fastapi import APIRouter, HTTPException, Request
from schemas.controller import (
    GraphCompileRequest,
    GraphRunRequest,
    GraphRunResponse,
    HealthResponse,
    TestAgentRequest,
    TestModelRequest,
    TestModelResponse,
)
from schemas.enums import AgentName, LlmModelName
from service.graph_service import GraphService
from service.llm_service import LlmService

URL_HEALTH = "/health"
URL_MODELS = "/models"
URL_TEST_MODEL = "/test-llm"
URL_AGENTS = "/agents"
URL_GRAPH_CONFIG = "/graph-config"
URL_GRAPH_RUN = "/graph-run"

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(URL_HEALTH, response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    settings = inject_settings(request)
    return HealthResponse(status="ok", version=settings.app_version)


@router.get(URL_MODELS)
def list_models(request: Request) -> list[LlmModelName]:
    service: LlmService = inject_llm_service(request)
    return service.list_models()


@router.post(URL_TEST_MODEL, response_model=TestModelResponse)
def test_llm(request: Request, body: TestModelRequest) -> TestModelResponse:
    try:
        service: LlmService = inject_llm_service(request)
        response = service.test_client(body.model, body.temperature, body.message)
        return TestModelResponse(response=response)
    except Exception as exc:
        logger.exception("LLM call failed for model '%s'", body.model)
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}") from exc


@router.get(URL_AGENTS)
def list_agents(request: Request) -> list[AgentName]:
    service: LlmService = inject_llm_service(request)
    return service.list_agents()


@router.post(URL_AGENTS)
def test_agent(request: Request, body: TestAgentRequest) -> str:
    try:
        service: LlmService = inject_llm_service(request)
        return service.test_agent(name=body.name, model=body.model, temperature=body.temperature, message=body.message)
    except ValueError as exc:
        logger.exception("Agent validation failed for agent '%s'", body.name)
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        logger.exception("Agent call failed for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc


@router.get(URL_GRAPH_CONFIG, response_model=GraphCompileRequest | None)
def get_graph_config(request: Request) -> GraphCompileRequest | None:
    graph_service: GraphService = inject_graph_service(request)
    return graph_service.get_config()


@router.put(URL_GRAPH_CONFIG, response_model=GraphCompileRequest)
async def compile_graph(request: Request, body: GraphCompileRequest) -> GraphCompileRequest:
    try:
        graph_service: GraphService = inject_graph_service(request)
        llm_service: LlmService = inject_llm_service(request)
        await graph_service.compile_graph(body, llm_service)
        return graph_service.get_config()
    except ValueError as exc:
        logger.exception("Graph validation failed during compile")
        raise HTTPException(status_code=400, detail=f"Graph error: {exc}") from exc
    except Exception as exc:
        logger.exception("Graph compile failed")
        raise HTTPException(status_code=500, detail=f"Graph error: {exc}") from exc


@router.post(URL_GRAPH_RUN, response_model=GraphRunResponse)
def run_graph(request: Request, body: GraphRunRequest) -> GraphRunResponse:
    try:
        graph_service: GraphService = inject_graph_service(request)
        result = graph_service.invoke({"paper": body.paper})
        reviews = result.get("reviews", [])
        return GraphRunResponse(reviews=reviews, raw_result=result)
    except ValueError as exc:
        logger.exception("Graph run validation failed")
        raise HTTPException(status_code=400, detail=f"Graph error: {exc}") from exc
    except Exception as exc:
        logger.exception("Graph run failed")
        raise HTTPException(status_code=500, detail=f"Graph error: {exc}") from exc
