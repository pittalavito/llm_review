"""Shared helpers for the operational scripts in resource/scripts/."""
import os
import subprocess
import shutil

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


def build_ui() -> None:
    """Build the React UI so FastAPI can serve it at / (ui-react/dist).
    Best-effort: if npm is missing or the build fails, warn and continue —
    the backend still serves the API, only the bundled UI is unavailable
    (use `npm run dev` for the frontend in that case).
    """

    _SKIP_UI_BUILD = env_value("SKIP_UI_BUILD", "false").lower() in {"1", "true", "yes"}
    _UI_DIR = PROJECT_ROOT / "ui-react"

    
    if _SKIP_UI_BUILD:
        print("Skipping UI build (SKIP_UI_BUILD set).")
        return
    if not _UI_DIR.is_dir():
        print(f"UI folder not found ({_UI_DIR}) — skipping UI build.")
        return

    npm = shutil.which("npm")
    if npm is None:
        print("WARNING: npm not found — skipping UI build (API still served).")
        return

    if not (_UI_DIR / "node_modules").is_dir():
        print("Installing UI dependencies (npm install)...")
        if subprocess.run([npm, "install"], cwd=_UI_DIR).returncode != 0:
            print("WARNING: npm install failed — skipping UI build.")
            return

    print("Building UI (npm run build)...")
    if subprocess.run([npm, "run", "build"], cwd=_UI_DIR).returncode != 0:
        print("WARNING: UI build failed — API still served, bundled UI unavailable.")