import shutil
import subprocess
import sys

from utils import env_value, get_project_root

### CONFIGURATION ###

PROJECT_ROOT = get_project_root()
PORT = env_value("APP_PORT", "8081")
HOST = env_value("APP_HOST", "0.0.0.0")

### EXECUTE ###

uv = shutil.which("uv")
if uv:
    cmd_prefix = [uv]
else:
    cmd_prefix = [sys.executable, "-m", "uv"]

sync = subprocess.run(cmd_prefix + ["sync", "--no-install-project"], cwd=PROJECT_ROOT)
if sync.returncode != 0:
    sys.exit(sync.returncode)

result = subprocess.run(
    cmd_prefix + ["run", "uvicorn", "main:app", "--app-dir", "src", "--reload",
                  "--host", HOST, "--port", PORT],
    cwd=PROJECT_ROOT,
)
sys.exit(result.returncode)
