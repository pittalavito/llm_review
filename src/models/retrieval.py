from typing import Literal

from pydantic import BaseModel, Field


class FileSignature(BaseModel):
    mtime_ns: int
    size: int


class IndexedChunk(BaseModel):
    text: str
    token_counts: dict[str, int]
    length: int = Field(ge=1)
    section: str = "unknown"


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
    section: str = "unknown"


class RetrievalMetadata(BaseModel):
    paper_path: str
    index_status: Literal["rebuilt", "reused"]
    chunk_count_total: int = Field(ge=0)
    chunk_count_retrieved: int = Field(ge=0)
    top_k: int = Field(ge=1, le=20)


class IndexInfo(BaseModel):
    doc_id: str
    paper_path: str
    file_signature: FileSignature
    settings: IndexConfig
    chunk_count: int = Field(ge=0)


