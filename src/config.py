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
RESULTS_DIR = RESOURCE_DIR / "results"
OPENREVIEW_DIR = RESOURCE_DIR / "openreview"
DB_DIR = RESOURCE_DIR / "db"

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

    # --- Ollama ---
    ollama_url: str | None = None
    ollama_num_predict: int = 2048
    ollama_keep_alive: str = "10m"
    ollama_api_key: str | None = None

    # --- Aitho ---
    aitho_url: str | None = None
    aitho_api_key: str | None = None

    # --- OpenAI ---
    openai_api_key: str | None = None

    # --- Anthropic ---
    anthropic_api_key: str | None = None

    # --- Database ---
    database_url: str | None = None      # None -> sqlite:///{DB_DIR}/llm-review.sqlite
    db_echo: bool = False

    # --- Redis ---
    redis_url: str | None = None         # None -> RAG indices served from files only
    redis_index_ttl_seconds: int = 604_800  # 7 days; 0 = cache entries never expire

    # --- Retrieval ---
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 150
    rag_top_k_default: int = 10
    rag_max_context_chars: int = 12_000
    rag_strategy_version: str = "bm25-v3-section"
