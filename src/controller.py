import logging

from container import Container, inject_container
from fastapi import APIRouter, Depends, HTTPException, Query

from models.agent import AgentName, LlmModelName
from models.graph import GraphAgentConfig
from models.controller import (GraphRunRequest, IndexPaperRequest, PreviewPromptRequest, PromptVersionCreateRequest, PromptVersionUpdateRequest, TestAgentRequest, TestAgentWithRetrievalRequest, TestLlmRequest)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm-review", tags=["dev"])

URI_HEALTH = "/health"
URI_MODELS = "/models"
URI_TEST_LLM = "/test-llm"
URI_AGENTS = "/agents"
URI_PAPERS = "/papers"
URI_INDEX_PAPER = "/papers/index"
URI_INDEXED_PAPERS = "/papers/indexed"
URI_INDEXED_PAPER_DETAIL = "/papers/indexed/detail"
URI_AGENT_PROMPT_PREVIEW = "/agents/prompt-preview"
URI_AGENT_WITH_RETRIEVAL = "/agents/retrieval"
URI_GRAPH_COMPILE = "/graph/compile"
URI_GRAPH_CONFIG = "/graph/config"
URI_GRAPH_RUN = "/graph/run"
URI_PROMPTS = "/prompts"
URI_PROMPT_VERSION = "/prompts/{version_id}"
URI_PROMPT_VERSION_UPDATE = "/prompts/{version_id}/update"
URI_RUNS = "/runs"
URI_RUNS_ID = "/runs/{run_id}"
URI_RUN_AGENT_RUNS = "/runs/{run_id}/agent-runs"
URI_COMPARE_PAPERS = "/compare/papers"
URI_COMPARE = "/compare"


@router.get(URI_HEALTH, response_model=dict)
async def health_check(container: Container = Depends(inject_container)) -> dict:
    """Health check endpoint to verify the service is running and return the application version."""
    
    return {"status": "ok", "version": container.config.app_version}



@router.get(URI_MODELS)
def list_models() -> list[LlmModelName]:
    """List available LLM models."""
    
    return list(LlmModelName)


@router.post(URI_TEST_LLM, response_model=str)
def test_llm(body: TestLlmRequest, container: Container = Depends(inject_container)) -> str:
    """Test a specific LLM model with a given message and temperature."""
    
    try:
        return container.agent_service.invoke_client(body.model, body.temperature, body.message)
    except Exception as exc:
        raise _http_error(exc, f"LLM call (model={body.model})") from exc


@router.get(URI_AGENTS)
def list_agents() -> list[AgentName]:
    """List available agents."""
    
    return list(AgentName)


@router.get(URI_PAPERS)
def list_papers(container: Container = Depends(inject_container)) -> list[str]:
    """List available papers."""
    
    return container.retrieval_service.list_papers()


@router.post(URI_INDEX_PAPER)
def index_paper(body: IndexPaperRequest, container: Container = Depends(inject_container)) -> dict:
    """Index a paper for retrieval."""
    
    try:
        return container.retrieval_service.index_paper(body.paper_path, body.force_reindex).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Index paper '{body.paper_path}'") from exc


@router.get(URI_INDEXED_PAPERS)
def list_indexed_papers(container: Container = Depends(inject_container)) -> list[str]:
    """List indexed papers."""
    
    return container.retrieval_service.list_indexed_papers()


@router.get(URI_INDEXED_PAPER_DETAIL)
def get_indexed_paper(paper_path: str, container: Container = Depends(inject_container)) -> dict:
    """Get details of an indexed paper."""
    
    try:
        return container.retrieval_service.get_indexed_paper(paper_path).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Get index for '{paper_path}'") from exc


@router.post(URI_AGENTS)
def test_agent(body: TestAgentRequest, container: Container = Depends(inject_container)):
    """Test an agent with a given message and temperature."""
    
    try:
        return container.agent_service.run_agent(body.name, body.model, body.temperature, body.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        raise _http_error(exc, f"Agent '{body.name}'") from exc


@router.post(URI_AGENT_PROMPT_PREVIEW)
def agent_prompt_preview(body: PreviewPromptRequest, container: Container = Depends(inject_container)) -> dict:
    """Preview the prompt for a given agent and message, optionally overriding the system prompt."""
    
    try:
        override = None
        if body.prompt_version:
            agent_role_label = body.name.role()
            prompt_version = body.prompt_version
            override = container.repository_service.get_by_role_label(agent_role_label, prompt_version).template
        
        return container.agent_service.build_prompt_preview(body.name, body.message, override)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Prompt preview '{body.name}'") from exc


@router.post(URI_AGENT_WITH_RETRIEVAL)
def test_agent_with_retrieval(body: TestAgentWithRetrievalRequest, container: Container = Depends(inject_container)):
    """Test an agent with retrieval capabilities, given a message, paper path, and optional top_k context."""
    
    try:
        return container.test_agent_with_retrieval(body.name, body.model, body.temperature, body.message, body.paper_path, body.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        raise _http_error(exc, f"Agent-with-retrieval '{body.name}'") from exc


@router.post(URI_GRAPH_COMPILE, response_model=dict)
def compile_graph(body: GraphAgentConfig | None = None, container: Container = Depends(inject_container)) -> dict:
    """Compile a graph configuration, optionally provided in the request body."""
    
    try:
        container.compile_graph(body)
        return {"status": "compiled"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, "Graph compile") from exc


@router.get(URI_GRAPH_CONFIG)
def get_graph_config(container: Container = Depends(inject_container)) -> dict | None:
    """Retrieve the current graph configuration, if any."""
    
    return container.graph_service.get_graph_config()


@router.post(URI_GRAPH_RUN)
def run_graph(body: GraphRunRequest, container: Container = Depends(inject_container)) -> dict:
    """Run a graph with the provided configuration and paper path."""
    
    try:
        if body.graph_config:
            container.compile_graph(body.graph_config)
        
        result, metadata = container.invoke_graph(paper_path=body.paper_path, run_description=body.run_description, force_reindex=body.force_reindex)
        
        return {
            "decision": result.get("decision"),
            "current_round": result.get("current_round"),
            "meta_review": result.get("meta_review"),
            "reviews": result.get("reviews", []),
            "author_response": result.get("author_response"),
            "retrieval_metadata": metadata,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Graph run '{body.paper_path}'") from exc


@router.get(URI_PROMPTS)
def list_prompt_versions(agent_role: str | None = None, include_inactive: bool = False, container: Container = Depends(inject_container)) -> list[dict]:
    """Registry metadata (template text only in the detail endpoint)."""
    
    rows = container.repository_service.list_prompts(agent_role, include_inactive)
    return [row.model_dump(exclude={"template"}) for row in rows]


@router.get(URI_PROMPT_VERSION)
def get_prompt_version(version_id: int, container: Container = Depends(inject_container)) -> dict:
    """Get details of a specific prompt version by its ID."""
    
    try:
        return container.repository_service.get_prompt(version_id).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(URI_PROMPTS, status_code=201)
def create_prompt_version(body: PromptVersionCreateRequest, container: Container = Depends(inject_container)) -> dict:
    """Register a new immutable prompt version."""
    
    try:
        row = container.repository_service.create_prompt(body.agent_role, body.version_label, body.template, body.description)
        return row.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Create prompt version '{body.agent_role}/{body.version_label}'") from exc


@router.patch(URI_PROMPT_VERSION)
def update_prompt_version(version_id: int, body: PromptVersionUpdateRequest, container: Container = Depends(inject_container)) -> dict:
    """Update description/is_active only — templates are immutable."""
    
    try:
        row = container.repository_service.update_prompt_meta(version_id, description=body.description, is_active=body.is_active)
        return row.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(URI_RUNS)
def list_runs(container: Container = Depends(inject_container)) -> list:
    """List all graph runs."""
    
    return container.graph_service.list_runs()


@router.get(URI_RUNS_ID)
def get_run(run_id: str, container: Container = Depends(inject_container)) -> dict:
    """Get details of a specific graph run by its ID."""
    
    try:
        return container.graph_service.get_run(run_id).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Load run '{run_id}'") from exc


@router.get(URI_COMPARE_PAPERS)
def list_comparable_papers(container: Container = Depends(inject_container)) -> list[dict]:
    """List all comparable papers."""
    
    return container.comparator.list_papers()


@router.get(URI_COMPARE)
def compare_paper(paper_path: str, container: Container = Depends(inject_container)) -> dict:
    """Compare a specific paper and return the comparison results."""
    
    try:
        return container.comparator.compare_paper(paper_path).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Compare paper '{paper_path}'") from exc


@router.get(URI_RUN_AGENT_RUNS)
def get_run_agent_runs(run_id: str, agent_name: AgentName | None = None, round_index: int | None = Query(default=None, ge=0), container: Container = Depends(inject_container)) -> list[dict]:
    """Get agent runs for a specific graph run."""
    
    try:
        return container.graph_service.get_agent_runs(run_id, agent_name=agent_name, round_index=round_index)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Load agent runs for '{run_id}'") from exc


def _http_error(exc: Exception, action: str, status: int = 500) -> HTTPException:
    """Helper function to log and raise an HTTPException for a given action."""
    
    logger.exception("%s failed", action)
    return HTTPException(status_code=status, detail=f"{action} error: {exc}")
