import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

project_root = Path(__file__).parent.parent

DASHBOARD_URL = "http://localhost:8083"

docker = shutil.which("docker")
if docker:
    compose_cmd = [docker, "compose"]
else:
    compose = shutil.which("docker-compose")
    if not compose:
        sys.exit("Docker not found: install Docker Desktop to run the Redis dashboard.")
    compose_cmd = [compose]

up = subprocess.run(compose_cmd + ["up", "-d", "redis", "redis-commander"], cwd=project_root)
if up.returncode != 0:
    sys.exit(up.returncode)

webbrowser.open(DASHBOARD_URL)
print(f"Redis dashboard available at {DASHBOARD_URL}")
