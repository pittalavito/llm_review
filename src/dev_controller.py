import logging

from container import Container, inject_container
from fastapi import APIRouter, Depends, HTTPException
from graph.config import GraphAgentConfig
from models.controller import (
    GraphRunRequest,
    IndexPaperRequest,
    PreviewPromptRequest,
    TestAgentRequest,
    TestAgentWithRetrievalRequest,
    TestLlmRequest,
)
from models.agent import AgentName, LlmModelName

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dev", tags=["dev"])


def _http_error(exc: Exception, action: str, status: int = 500) -> HTTPException:
    logger.exception("%s failed", action)
    return HTTPException(status_code=status, detail=f"{action} error: {exc}")


@router.get("/health", response_model=dict)
async def health_check(container: Container = Depends(inject_container)) -> dict:
    return container.health_check()


@router.get("/models")
def list_models() -> list[LlmModelName]:
    return list(LlmModelName)


@router.post("/test-llm", response_model=str)
def test_llm(body: TestLlmRequest, container: Container = Depends(inject_container)) -> str:
    try:
        return container.test_llm(body.model, body.temperature, body.message)
    except Exception as exc:
        raise _http_error(exc, f"LLM call (model={body.model})") from exc


@router.get("/agents")
def list_agents() -> list[AgentName]:
    return list(AgentName)


@router.get("/papers")
def list_papers(container: Container = Depends(inject_container)) -> list[str]:
    return container.list_papers_path()


@router.post("/papers/index")
def index_paper(body: IndexPaperRequest, container: Container = Depends(inject_container)) -> dict:
    try:
        return container.index_paper(body.paper_path, body.force_reindex)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Index paper '{body.paper_path}'") from exc


@router.get("/papers/indexed")
def list_indexed_papers(container: Container = Depends(inject_container)) -> list[str]:
    return container.list_indexed_papers()


@router.get("/papers/indexed/detail")
def get_indexed_paper(paper_path: str, container: Container = Depends(inject_container)) -> dict:
    try:
        return container.get_indexed_paper(paper_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Get index for '{paper_path}'") from exc


@router.post("/agents")
def test_agent(body: TestAgentRequest, container: Container = Depends(inject_container)):
    try:
        return container.test_agent(body.name, body.model, body.temperature, body.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        raise _http_error(exc, f"Agent '{body.name}'") from exc


@router.post("/agents/prompt-preview")
def agent_prompt_preview(body: PreviewPromptRequest, container: Container = Depends(inject_container)) -> dict:
    try:
        return container.build_agent_prompt(body.name, body.message)
    except Exception as exc:
        raise _http_error(exc, f"Prompt preview '{body.name}'") from exc


@router.post("/agents/retrieval")
def test_agent_with_retrieval(body: TestAgentWithRetrievalRequest, container: Container = Depends(inject_container)):
    try:
        return container.test_agent_with_retrieval(
            body.name, body.model, body.temperature, body.message, body.paper_path, body.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        raise _http_error(exc, f"Agent-with-retrieval '{body.name}'") from exc


@router.post("/graph/compile", response_model=dict)
def compile_graph(body: GraphAgentConfig | None = None, container: Container = Depends(inject_container)) -> dict:
    try:
        container.compile_graph(body)
        return {"status": "compiled"}
    except Exception as exc:
        raise _http_error(exc, "Graph compile") from exc


@router.get("/graph/config")
def get_graph_config(container: Container = Depends(inject_container)) -> dict | None:
    return container.get_graph_config()


@router.post("/graph/run")
def run_graph(body: GraphRunRequest, container: Container = Depends(inject_container)) -> dict:
    try:
        if body.graph_config:
            container.compile_graph(body.graph_config)
        result, metadata = container.invoke_graph(
            paper_path=body.paper_path,
            force_reindex=body.force_reindex,
        )
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


@router.get("/runs")
def list_runs(container: Container = Depends(inject_container)) -> list:
    return container.list_runs()


@router.get("/runs/{run_id}")
def get_run(run_id: str, container: Container = Depends(inject_container)) -> dict:
    try:
        return container.get_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise _http_error(exc, f"Load run '{run_id}'") from exc
