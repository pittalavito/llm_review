from pydantic import BaseModel, Field, field_validator

from agent.models.enums import AgentName, LlmModelName

class TestLlmRequest(BaseModel):
    model: LlmModelName
    temperature: float = Field(default=1, ge=0, le=1)
    message: str = Field(min_length=1, max_length=8_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        return stripped
    
    
# estendere TestLlmRequest ?
class TestAgentRequest(TestLlmRequest):
    name: AgentName
    model: LlmModelName
    temperature: float = Field(default=1, ge=0, le=1)
    message: str = Field(min_length=1, max_length=8_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        return stripped


class PreviewPromptRequest(BaseModel):
    name: AgentName
    message: str = Field(min_length=1, max_length=8_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        return stripped


class PreviewPromptResponse(BaseModel):
    agent: AgentName
    system_prompt: str
    schema_instructions: str
    message_section: str
    full_prompt: str


