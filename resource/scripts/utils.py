"""Shared helpers for the operational scripts in resource/scripts/."""
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def get_project_root() -> Path:
    return PROJECT_ROOT


def env_value(name: str, default: str) -> str:
    env_value = os.environ.get(name, default)
    if env_value == default:
        print(f"WARNING: Environment variable {name} not set, using default: {default}")
    return env_value
