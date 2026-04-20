import logging

from container import Container, inject_container
from fastapi import APIRouter, Depends, HTTPException
from models.controller import IndexPaperRequest, PreviewPromptRequest, TestAgentRequest, TestAgentWithRetrievalRequest, TestLlmRequest
from models.agent import AgentName, LlmModelName, AgentResponse

PREFIX = "/dev"
URL_HEALTH = "/health"
URL_MODELS = "/models"
URL_TEST_MODEL = "/test-llm"
URL_AGENTS = "/agents"
URL_AGENT_PROMPT_PREVIEW = "/agents/prompt-preview"
URL_AGENTS_WITH_RETRIEVAL = "/agents/retrieval"
URL_PAPERS = "/papers"
URL_PAPERS_INDEX = "/papers/index"
URL_PAPERS_INDEXED = "/papers/indexed"
URL_PAPERS_INDEXED_DETAIL = "/papers/indexed/detail"


logger = logging.getLogger(__name__)
router = APIRouter(prefix=PREFIX, tags=["dev"])


@router.get(URL_HEALTH, response_model=dict)
async def health_check(container: Container = Depends(inject_container)) -> dict:
    """Simple health check endpoint returning app version."""
    return container.health_check()

    
@router.get(URL_MODELS)
def list_models() -> list[LlmModelName]:
    """List available LLM models."""
    return list(LlmModelName)


@router.post(URL_TEST_MODEL, response_model=str)
def test_llm(body: TestLlmRequest, container: Container = Depends(inject_container)) -> str:
    """Test LLM response for given model, temperature and message."""
    try:
        return container.test_llm(body.model, body.temperature, body.message)
    except Exception as exc:
        logger.exception("LLM call failed for model '%s'", body.model)
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}") from exc


@router.get(URL_AGENTS)
def list_agents() -> list[AgentName]:
    """List available agents."""
    return list(AgentName)


@router.get(URL_PAPERS)
def list_papers(container: Container = Depends(inject_container)) -> list[str]:
    """List available papers."""
    return container.list_papers_path()


@router.post(URL_PAPERS_INDEX)
def index_paper(body: IndexPaperRequest, container: Container = Depends(inject_container)) -> dict:
    """Build or reuse the BM25 index for a paper."""
    try:
        return container.index_paper(body.paper_path, body.force_reindex)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Index failed for paper '%s'", body.paper_path)
        raise HTTPException(status_code=500, detail=f"Index error: {exc}") from exc


@router.get(URL_PAPERS_INDEXED)
def list_indexed_papers(container: Container = Depends(inject_container)) -> list[str]:
    """List papers that have a persisted BM25 index."""
    return container.list_indexed_papers()


@router.get(URL_PAPERS_INDEXED_DETAIL)
def get_indexed_paper(paper_path: str, container: Container = Depends(inject_container)) -> dict:
    """Return index metadata for a specific paper (no chunks)."""
    try:
        return container.get_indexed_paper(paper_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to get index for paper '%s'", paper_path)
        raise HTTPException(status_code=500, detail=f"Error: {exc}") from exc


@router.post(URL_AGENTS, response_model=AgentResponse)
def test_agent(body: TestAgentRequest, container: Container = Depends(inject_container)) -> AgentResponse:
    """Test agent response for given agent name, model, temperature and message."""
    try:
        raw_result = container.test_agent(body.name, body.model, body.temperature, body.message)
        return AgentResponse.from_raw(raw_result)
    except ValueError as exc:
        logger.exception("Agent validation failed for agent '%s'", body.name)
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        logger.exception("Agent call failed for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
    

@router.post(URL_AGENT_PROMPT_PREVIEW)
def agent_prompt_preview(body: PreviewPromptRequest, container: Container = Depends(inject_container)) -> str:
    try:
        return container.build_agent_prompt(body.name, body.message)
    except Exception as exc:
        logger.exception("Failed to get prompt preview for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Error: {exc}") from exc


@router.post(URL_AGENTS_WITH_RETRIEVAL, response_model=AgentResponse)
def test_agent_with_retrieval(body: TestAgentWithRetrievalRequest, container: Container = Depends(inject_container)) -> AgentResponse:
    """Run an agent with RAG context retrieved from a paper injected into the message."""
    try:
        raw_result = container.test_agent_with_retrieval(
            body.name, body.model, body.temperature, body.message, body.paper_path, body.top_k
        )
        return AgentResponse.from_raw(raw_result)
    except ValueError as exc:
        logger.exception("Agent-with-retrieval validation failed for agent '%s'", body.name)
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        logger.exception("Agent-with-retrieval call failed for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc