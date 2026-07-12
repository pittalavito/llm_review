from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Directory paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parents[1]

UI_REACT_DIST_DIR = _ROOT / "ui-react" / "dist"
RESOURCE_DIR = _ROOT / "resource"

OPENREVIEW_INDEX_DIR = RESOURCE_DIR / "open-review-index.json"
OPENREVIEW_DIR = RESOURCE_DIR / "openreview"

PAPERS_DIR = RESOURCE_DIR / "papers"

DB_DIR = RESOURCE_DIR / "db"

def get_openreview_index_dir() -> Path:
    """Get the OpenReview index path."""
    return OPENREVIEW_INDEX_DIR


def get_openreview_dir() -> Path:
    """Get the OpenReview directory path."""
    return OPENREVIEW_DIR


def get_papers_dir() -> Path:
    """Get the papers directory path."""
    return PAPERS_DIR.resolve()


def get_db_dir() -> Path:
    """Get the database directory path."""
    return DB_DIR.resolve()

# ---------------------------------------------------------------------------
# Configuration class
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
    app_version: str = "0.2.0"
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
    database_url: str | None = None   
    db_echo: bool = False

    # --- Redis ---
    redis_url: str | None = None       
    redis_index_ttl_seconds: int = 0

    # --- Retrieval ---
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 150
    rag_top_k_default: int = 10
    rag_max_context_chars: int = 12_000
    rag_strategy_version: str = "bm25-v3-section"
        
