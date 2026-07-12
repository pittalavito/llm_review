import shutil
import subprocess
import sys

from pathlib import Path
from utils import get_project_root

### CONFIGURATION ###

PROJECT_ROOT = get_project_root()

### EXECUTE ###

uv = shutil.which("uv")
if not uv:
    print("Error: uv not found. Install it from https://docs.astral.sh/uv/getting-started/installation/")
    sys.exit(1)

venv = subprocess.run([uv, "venv"], cwd=PROJECT_ROOT)
if venv.returncode != 0:
    sys.exit(venv.returncode)

sync = subprocess.run([uv, "sync"], cwd=PROJECT_ROOT)
sys.exit(sync.returncode)
