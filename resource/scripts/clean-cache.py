import shutil
import sys
from pathlib import Path

preview = "--preview" in sys.argv
include_venv = "--include-venv" in sys.argv
project_root = Path(__file__).resolve().parents[2]

def is_excluded(path: Path) -> bool:
    return not include_venv and ".venv" in path.parts

cache_dirs = [
    p for p in project_root.rglob("*")
    if p.is_dir()
    and p.name in ("__pycache__", ".pytest_cache")
    and not is_excluded(p)
]

bytecode_files = [
    p for p in project_root.rglob("*")
    if p.is_file()
    and p.suffix in (".pyc", ".pyo")
    and not is_excluded(p)
]

print(f"Scan root: {project_root}")
print(f"Include .venv: {include_venv}")

if not cache_dirs and not bytecode_files:
    print("No Python cache artifacts found in project scope.")
    sys.exit(0)

print(f"Found {len(cache_dirs)} cache directories and {len(bytecode_files)} bytecode files.")

for p in cache_dirs:
    print(f"  {'[PREVIEW]' if preview else 'Removing'} {p}")
    if not preview:
        shutil.rmtree(p)

for p in bytecode_files:
    print(f"  {'[PREVIEW]' if preview else 'Removing'} {p}")
    if not preview:
        p.unlink()

if preview:
    print("Preview completed. No files were deleted.")
else:
    print("Cleanup completed.")
