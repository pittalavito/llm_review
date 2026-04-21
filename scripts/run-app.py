import shutil
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent

uv = shutil.which("uv")
if uv:
    cmd_prefix = [uv]
else:
    cmd_prefix = [sys.executable, "-m", "uv"]

sync = subprocess.run(cmd_prefix + ["sync", "--no-install-project"], cwd=project_root)
if sync.returncode != 0:
    sys.exit(sync.returncode)

result = subprocess.run(
    cmd_prefix + ["run", "uvicorn", "main:app", "--app-dir", "src", "--reload", "--host", "0.0.0.0", "--port", "8080"],
    cwd=project_root,
)
sys.exit(result.returncode)
