import logging

from adapter.agent_output_adapter import AgentOutputAdapter
from container import inject_graph_service, inject_llm_service, inject_open_review_service, inject_retrieval_service, inject_settings
from fastapi import APIRouter, HTTPException, Request
from schemas.agent.agent_output import AgentStructuredOutput
from schemas.controller.dev_controller import (
    GraphCompileRequest,
    GraphRunFileRequest,
    GraphRunRequest,
    GraphRunResponse,
    HealthResponse,
    OpenReviewSearchRequest,
    RetrievalMetadata,
    TestAgentRequest,
    TestModelRequest,
    TestModelResponse,
)
from schemas.enums import AgentName, LlmModelName
from schemas.open_review import PaperSearchResult, PaperSummary
from service.graph_service import GraphService
from service.llm_service import LlmService
from service.open_review_service import OpenReviewService
from service.retrieval_service import RetrievalService

DEV_PREFIX = "/dev"
URL_HEALTH = "/health"
URL_MODELS = "/models"
URL_TEST_MODEL = "/test-llm"
URL_AGENTS = "/agents"
URL_GRAPH_CONFIG = "/graph-config"
URL_GRAPH_RUN = "/graph-run"
URL_GRAPH_RUN_FILE = "/graph-run-file"
URL_OPEN_REVIEW_SUMMARY = "/openreview/papers/{paper_id}/summary"
URL_OPEN_REVIEW_SEARCH = "/openreview/papers/search"

logger = logging.getLogger(__name__)
router = APIRouter(prefix=DEV_PREFIX, tags=["dev"])


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


@router.post(URL_AGENTS, response_model=AgentStructuredOutput)
def test_agent(request: Request, body: TestAgentRequest) -> AgentStructuredOutput:
    try:
        service: LlmService = inject_llm_service(request)
        raw_result = service.test_agent(name=body.name, model=body.model, temperature=body.temperature, message=body.message)
        return AgentOutputAdapter.to_structured_output(raw_result)
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
        reviews = AgentOutputAdapter.to_structured_outputs(result.get("reviews", []))
        result["reviews"] = [item.model_dump() for item in reviews]
        return GraphRunResponse(reviews=reviews, raw_result=result)
    except ValueError as exc:
        logger.exception("Graph run validation failed")
        raise HTTPException(status_code=400, detail=f"Graph error: {exc}") from exc
    except Exception as exc:
        logger.exception("Graph run failed")
        raise HTTPException(status_code=500, detail=f"Graph error: {exc}") from exc


@router.post(URL_GRAPH_RUN_FILE, response_model=GraphRunResponse)
def run_graph_from_file(request: Request, body: GraphRunFileRequest) -> GraphRunResponse:
    try:
        graph_service: GraphService = inject_graph_service(request)
        retrieval_service: RetrievalService = inject_retrieval_service(request)
        result, retrieval_metadata = graph_service.invoke_from_file(
            retrieval_service=retrieval_service,
            paper_path=body.paper_path,
            top_k=body.top_k,
            force_reindex=body.force_reindex,
        )
        reviews = AgentOutputAdapter.to_structured_outputs(result.get("reviews", []))
        result["reviews"] = [item.model_dump() for item in reviews]
        return GraphRunResponse(
            reviews=reviews,
            raw_result=result,
            retrieval=RetrievalMetadata(**retrieval_metadata),
        )
    except ValueError as exc:
        logger.exception("Graph run-from-file validation failed")
        raise HTTPException(status_code=400, detail=f"Graph error: {exc}") from exc
    except Exception as exc:
        logger.exception("Graph run-from-file failed")
        raise HTTPException(status_code=500, detail=f"Graph error: {exc}") from exc


@router.get(URL_OPEN_REVIEW_SUMMARY, response_model=PaperSummary)
def get_openreview_paper_summary(request: Request, paper_id: str) -> PaperSummary:
    try:
        service: OpenReviewService = inject_open_review_service(request)
        summary = service.get_paper_summary(paper_id)
        if summary is None:
            raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found.")
        return summary
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("OpenReview summary retrieval failed for paper '%s'", paper_id)
        raise HTTPException(status_code=500, detail=f"OpenReview error: {exc}") from exc


@router.post(URL_OPEN_REVIEW_SEARCH, response_model=list[PaperSearchResult])
def search_openreview_papers(request: Request, body: OpenReviewSearchRequest) -> list[PaperSearchResult]:
    try:
        service: OpenReviewService = inject_open_review_service(request)
        return service.search_papers(keyword=body.keyword, venue_id=body.venue_id, limit=body.limit)
    except Exception as exc:
        logger.exception("OpenReview search failed for keyword '%s' on venue '%s'", body.keyword, body.venue_id)
        raise HTTPException(status_code=500, detail=f"OpenReview error: {exc}") from exc
