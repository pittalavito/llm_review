import logging

from container import Container, inject_container
from fastapi import APIRouter, Depends, HTTPException
from agent.base import BaseAgent
from agent.builder import PromptBuilder
from models.controller import PreviewPromptRequest, TestAgentRequest, TestLlmRequest
from models.agent import AgentName, LlmModelName, AgentResponse

PREFIX = "/dev"
URL_HEALTH = "/health"
URL_MODELS = "/models"
URL_TEST_MODEL = "/test-llm"
URL_AGENTS = "/agents"
URL_AGENT_PROMPT_PREVIEW = "/agents/prompt-preview"
URL_OPEN_REVIEW_SUMMARY = "/openreview/papers/{paper_id}/summary"
URL_OPEN_REVIEW_SEARCH = "/openreview/papers/search"

logger = logging.getLogger(__name__)
router = APIRouter(prefix=PREFIX, tags=["dev"])


@router.get(URL_HEALTH, response_model=dict)
async def health_check(container: Container = Depends(inject_container)) -> dict:
    return container.health_check()

    
@router.get(URL_MODELS)
def list_models() -> list[LlmModelName]:
    return list(LlmModelName)


@router.post(URL_TEST_MODEL, response_model=str)
def test_llm(body: TestLlmRequest, container: Container = Depends(inject_container)) -> str:
    try:
        return container.test_llm(body.model, body.temperature, body.message)
    except Exception as exc:
        logger.exception("LLM call failed for model '%s'", body.model)
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}") from exc


@router.get(URL_AGENTS)
def list_agents() -> list[AgentName]:
    return list(AgentName)


# da capire se AgentStructuredOutput serve
@router.post(URL_AGENTS, response_model=AgentResponse)
def test_agent(body: TestAgentRequest, container: Container = Depends(inject_container)) -> AgentResponse:
    try:
        raw_result = container.test_agent(body.name, body.model, body.temperature, body.message)
        return AgentResponse.from_raw(raw_result)
    except ValueError as exc:
        logger.exception("Agent validation failed for agent '%s'", body.name)
        raise HTTPException(status_code=400, detail=f"Agent error: {exc}") from exc
    except Exception as exc:
        logger.exception("Agent call failed for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc
    

@router.get(URL_AGENT_PROMPT_PREVIEW)
def agent_prompt_preview(body: PreviewPromptRequest) -> str:
    try:
        modelClass: BaseAgent = body.name.__class__
        return PromptBuilder.build_prompt(
            modelClass.SYSTEM_PROMPT,
            modelClass.RESPONSE_SCHEMA,
            body.message,
            modelClass.MESSAGE_LABEL
        )
    except Exception as exc:
        logger.exception("Failed to get prompt preview for agent '%s'", body.name)
        raise HTTPException(status_code=500, detail=f"Error: {exc}") from exc