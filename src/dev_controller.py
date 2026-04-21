import logging

from container import Container, inject_container
from fastapi import APIRouter, Depends, HTTPException
from graph.config import GraphAgentConfig
from models.controller import GraphRunRequest, IndexPaperRequest, PreviewPromptRequest, TestAgentRequest, TestAgentWithRetrievalRequest, TestLlmRequest
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
URL_GRAPH_COMPILE = "/graph/compile"
URL_GRAPH_CONFIG = "/graph/config"
URL_GRAPH_RUN = "/graph/run"
URL_RUNS = "/runs"
URL_RUN_DETAIL = "/runs/{run_id}"


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
        return container.test_llm(
            body.model, 
            body.temperature, 
            body.message
        )
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
        return container.index_paper(
            body.paper_path, 
            body.force_reindex
        )
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


@router.post(URL_AGENTS)
def test_agent(body: TestAgentRequest, container: Container = Depends(inject_container)):
    """Test agent response for given agent name, model, temperature and message."""
    try:
        return container.test_agent(
            body.name, 
            body.model, 
            body.temperature, 
            body.message
        )
    except ValueError as exc:
        logger.exception("Agent validation failed for agent '%s'", body.name)
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        logger.exception("Agent call failed for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
    

@router.post(URL_AGENT_PROMPT_PREVIEW)
def agent_prompt_preview(body: PreviewPromptRequest, container: Container = Depends(inject_container)) -> dict:
    try:
        return container.build_agent_prompt(
            body.name, 
            body.message
        )
    except Exception as exc:
        logger.exception("Failed to get prompt preview for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Error: {exc}") from exc


@router.post(URL_AGENTS_WITH_RETRIEVAL)
def test_agent_with_retrieval(body: TestAgentWithRetrievalRequest, container: Container = Depends(inject_container)):
    """Run an agent with RAG context retrieved from a paper injected into the message."""
    try:
        return container.test_agent_with_retrieval(
            body.name, 
            body.model, 
            body.temperature, 
            body.message, 
            body.paper_path, 
            body.top_k
        )
    except ValueError as exc:
        logger.exception("Agent-with-retrieval validation failed for agent '%s'", body.name)
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        logger.exception("Agent-with-retrieval call failed for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc


@router.post(URL_GRAPH_COMPILE, response_model=dict)
def compile_graph(body: GraphAgentConfig | None = None, container: Container = Depends(inject_container)) -> dict:
    """Compile the review graph with optional config. Uses default config if omitted."""
    try:
        container.compile_graph(body)
        return {"status": "compiled"}
    except Exception as exc:
        logger.exception("Graph compilation failed")
        raise HTTPException(status_code=500, detail=f"Graph compile error: {exc}") from exc


@router.get(URL_GRAPH_CONFIG)
def get_graph_config(container: Container = Depends(inject_container)) -> dict | None:
    """Return the currently compiled graph configuration."""
    return container.get_graph_config()


@router.post(URL_GRAPH_RUN)
def run_graph(body: GraphRunRequest, container: Container = Depends(inject_container)) -> dict:
    """Run the full review pipeline on a paper. Compiles with provided config if given."""
    try:
        if body.graph_config:
            container.compile_graph(body.graph_config)
        result, metadata = container.invoke_graph(
            paper_path=body.paper_path,
            rag_top_k=body.rag_top_k,
            force_reindex=body.force_reindex,
        )
        return {
            "decision": result.get("decision"),
            "current_round": result.get("current_round"),
            "meta_review": result.get("meta_review"),
            "reviews": result.get("reviews", []),
            "revision_notes": result.get("revision_notes"),
            "retrieval_metadata": metadata,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Graph run failed for paper '%s'", body.paper_path)
        raise HTTPException(status_code=500, detail=f"Graph error: {exc}") from exc


@router.get(URL_RUNS)
def list_runs(container: Container = Depends(inject_container)) -> list:
    """List all past graph run summaries (lightweight)."""
    return container.list_runs()


@router.get(URL_RUN_DETAIL)
def get_run(run_id: str, container: Container = Depends(inject_container)) -> dict:
    """Return full detail of a specific run including per-agent traces."""
    try:
        return container.get_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to load run '%s'", run_id)
        raise HTTPException(status_code=500, detail=f"Error: {exc}") from exc