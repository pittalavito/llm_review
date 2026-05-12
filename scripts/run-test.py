import shutil
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
coverage_target = str(project_root / "src")

uv = shutil.which("uv")
if uv:
    cmd_prefix = [uv]
else:
    cmd_prefix = [sys.executable, "-m", "uv"]

sync = subprocess.run(cmd_prefix + ["sync", "--group", "dev", "--no-install-project"], cwd=project_root)
if sync.returncode != 0:
    sys.exit(sync.returncode)

result = subprocess.run(
    cmd_prefix + [
        "run",
        "pytest",
        "-v",
        f"--cov={coverage_target}",
        "--cov-report=term-missing",
    ],
    cwd=project_root,
)
sys.exit(result.returncode)
