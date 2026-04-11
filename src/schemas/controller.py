from schemas.base import BaseSchema

class HealthResponse(BaseSchema):
    status: str
    version: str

class TestLlmRequest(BaseSchema):
    message: str
    llm_model: str | None = None

class TestLlmResponse(BaseSchema):
    response: str