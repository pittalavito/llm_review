import shutil
import subprocess
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent

uv = shutil.which("uv")
if not uv:
    print("Error: uv not found. Install it from https://docs.astral.sh/uv/getting-started/installation/")
    sys.exit(1)

venv = subprocess.run([uv, "venv"], cwd=project_root)
if venv.returncode != 0:
    sys.exit(venv.returncode)

sync = subprocess.run([uv, "sync"], cwd=project_root)
sys.exit(sync.returncode)
