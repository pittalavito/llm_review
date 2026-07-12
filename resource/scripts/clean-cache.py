import shutil
import sys

from pathlib import Path
from utils import get_project_root


### CONFIGURATION ###

PREVIEW = "--preview" in sys.argv
INCLUDE_VENV = "--include-venv" in sys.argv
PROJECT_ROOT = get_project_root()

### HELPERS ###

def is_excluded(path: Path) -> bool:
    return not INCLUDE_VENV and ".venv" in path.parts

### EXECUTE ###

cache_dirs = [
    p for p in PROJECT_ROOT.rglob("*")
    if p.is_dir()
    and p.name in ("__pycache__", ".pytest_cache")
    and not is_excluded(p)
]

bytecode_files = [
    p for p in PROJECT_ROOT.rglob("*")
    if p.is_file()
    and p.suffix in (".pyc", ".pyo")
    and not is_excluded(p)
]

print(f"Scan root: {PROJECT_ROOT}")
print(f"Include .venv: {INCLUDE_VENV}")

if not cache_dirs and not bytecode_files:
    print("No Python cache artifacts found in project scope.")
    sys.exit(0)

print(f"Found {len(cache_dirs)} cache directories and {len(bytecode_files)} bytecode files.")

for p in cache_dirs:
    print(f"  {'[PREVIEW]' if PREVIEW else 'Removing'} {p}")
    if not PREVIEW:
        shutil.rmtree(p)

for p in bytecode_files:
    print(f"  {'[PREVIEW]' if PREVIEW else 'Removing'} {p}")
    if not PREVIEW:
        p.unlink()

if PREVIEW:
    print("Preview completed. No files were deleted.")
else:
    print("Cleanup completed.")
