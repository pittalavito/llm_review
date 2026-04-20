from typing import Literal

from pydantic import BaseModel, Field, field_validator


class RetrievalRequest(BaseModel):
    paper_path: str = Field(min_length=1, max_length=500)
    top_k: int | None = Field(default=None, ge=1, le=20)
    force_reindex: bool = False
    query: str | None = Field(default=None, max_length=2_000)

    @field_validator("paper_path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Paper path must not be empty.")
        return stripped

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class FileSignature(BaseModel):
    mtime_ns: int
    size: int


class IndexedChunk(BaseModel):
    text: str
    token_counts: dict[str, int]
    length: int = Field(ge=1)


class IndexConfig(BaseModel):
    chunk_size: int = Field(ge=1)
    chunk_overlap: int = Field(ge=0)
    strategy_version: str = Field(min_length=1, max_length=100)


class Index(BaseModel):
    doc_id: str
    paper_path: str
    file_signature: FileSignature
    settings: IndexConfig
    doc_freq: dict[str, int]
    chunks: list[IndexedChunk]


class RetrievedChunk(BaseModel):
    rank: int = Field(ge=1)
    score: float = Field(ge=0)
    index: int = Field(ge=0)
    text: str


class RetrievalMetadata(BaseModel):
    paper_path: str
    index_status: Literal["rebuilt", "reused"]
    chunk_count_total: int = Field(ge=0)
    chunk_count_retrieved: int = Field(ge=0)
    top_k: int = Field(ge=1, le=20)


class RetrievalResponse(BaseModel):
    context: str
    metadata: RetrievalMetadata
    retrieved_chunks: list[RetrievedChunk]
