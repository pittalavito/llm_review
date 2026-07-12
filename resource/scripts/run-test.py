import shutil
import subprocess
import sys

from pathlib import Path
from utils import get_project_root

### CONFIGURATION ###

PROJECT_ROOT = get_project_root()
COVERAGE_TARGET = str(PROJECT_ROOT / "src")

### EXECUTE ###

uv = shutil.which("uv")
if uv:
    cmd_prefix = [uv]
else:
    cmd_prefix = [sys.executable, "-m", "uv"]

sync = subprocess.run(cmd_prefix + ["sync", "--group", "dev", "--no-install-project"], cwd=PROJECT_ROOT)
if sync.returncode != 0:
    sys.exit(sync.returncode)

result = subprocess.run(
    cmd_prefix + [
        "run",
        "pytest",
        "-v",
        f"--cov={COVERAGE_TARGET}",
        "--cov-report=term-missing",
    ],
    cwd=PROJECT_ROOT,
)
sys.exit(result.returncode)
