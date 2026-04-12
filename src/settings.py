from pydantic_settings import BaseSettings, SettingsConfigDict

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
