import shutil
import subprocess
import sys

from utils import env_value, get_project_root

### CONFIGURATION ###

PROJECT_ROOT = get_project_root()
PORT = env_value("APP_PORT", "8081")
HOST = env_value("APP_HOST", "0.0.0.0")
SKIP_UI_BUILD = env_value("SKIP_UI_BUILD", "false").lower() in {"1", "true", "yes"}

UI_DIR = PROJECT_ROOT / "ui-react"


### UI BUILD ###

def build_ui() -> None:
    """Build the React UI so FastAPI can serve it at / (ui-react/dist).

    Best-effort: if npm is missing or the build fails, warn and continue —
    the backend still serves the API, only the bundled UI is unavailable
    (use `npm run dev` for the frontend in that case).
    """
    if SKIP_UI_BUILD:
        print("Skipping UI build (SKIP_UI_BUILD set).")
        return
    if not UI_DIR.is_dir():
        print(f"UI folder not found ({UI_DIR}) — skipping UI build.")
        return

    npm = shutil.which("npm")
    if npm is None:
        print("WARNING: npm not found — skipping UI build (API still served).")
        return

    if not (UI_DIR / "node_modules").is_dir():
        print("Installing UI dependencies (npm install)...")
        if subprocess.run([npm, "install"], cwd=UI_DIR).returncode != 0:
            print("WARNING: npm install failed — skipping UI build.")
            return

    print("Building UI (npm run build)...")
    if subprocess.run([npm, "run", "build"], cwd=UI_DIR).returncode != 0:
        print("WARNING: UI build failed — API still served, bundled UI unavailable.")


### EXECUTE ###

uv = shutil.which("uv")
if uv:
    cmd_prefix = [uv]
else:
    cmd_prefix = [sys.executable, "-m", "uv"]

sync = subprocess.run(cmd_prefix + ["sync", "--no-install-project"], cwd=PROJECT_ROOT)
if sync.returncode != 0:
    sys.exit(sync.returncode)

build_ui()

result = subprocess.run(
    cmd_prefix + ["run", "uvicorn", "main:app", "--app-dir", "src", "--reload",
                  "--host", HOST, "--port", PORT],
    cwd=PROJECT_ROOT,
)
sys.exit(result.returncode)
