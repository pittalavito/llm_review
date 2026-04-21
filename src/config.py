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

APP_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
class Config(BaseSettings):
    """Configuration class for the application. Loads settings from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    # --- App ---
    app_name: str = "llm-review"
    app_version: str = "0.1.0"
    app_log_level: str = "INFO"
    llm_debug_json_logs: bool = False

    # --- Ollama ---
    ollama_url: str = "http://localhost:11434"
    ollama_num_predict: int = 2048
    ollama_keep_alive: str = "10m"

    # --- OpenAI ---
    openai_api_key: str | None = None

    # --- Anthropic ---
    anthropic_api_key: str | None = None

    # --- Retrieval ---
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 150
    rag_top_k_default: int = 6
    rag_max_context_chars: int = 12_000
    rag_strategy_version: str = "bm25-v2-section"
