"""Shared helpers for the operational scripts in resource/scripts/."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def env_value(name: str, default: str) -> str:
    """Read NAME from the process environment, then from the project .env
    file, falling back to the given default. Scripts run outside the app,
    so they cannot rely on pydantic-settings for this."""
    value = os.environ.get(name)
    if value:
        return value
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{name}=") and not stripped.startswith("#"):
                candidate = stripped.split("=", 1)[1].strip()
                if candidate:
                    return candidate
    return default
