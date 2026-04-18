from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Directory paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).parents[1]

UI_DIR = _ROOT / "ui"
RESOURCE_DIR = _ROOT / "resource"
PAPERS_DIR = RESOURCE_DIR / "papers"
RAG_INDEX_DIR = RESOURCE_DIR / "rag-index"

# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Configuration class for the application. Loads settings from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # --- App ---
    app_name: str = "llm-review"
    app_version: str = "0.1.0"

    # --- Ollama ---
    ollama_url: str = "http://localhost:11434"

    # --- Retrieval ---
    rag_chunk_size: int = 1_200
    rag_chunk_overlap: int = 200
    rag_top_k_default: int = 6
    rag_max_context_chars: int = 12_000
    rag_strategy_version: str = "bm25-v1"
