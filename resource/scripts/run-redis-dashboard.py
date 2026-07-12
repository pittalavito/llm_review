import shutil
import subprocess
import sys
import webbrowser

from pathlib import Path
from utils import env_value, get_project_root

### CONFIGURATION ###

PROJECT_ROOT = get_project_root()
DASHBOARD_URL = env_value("REDIS_DASHBOARD_URL", "http://localhost:8083")
REDIS_CONTAINER = env_value("REDIS_CONTAINER", "llm-review-redis")
COMMANDER_CONTAINER = env_value("COMMANDER_CONTAINER", "llm-review-redis-commander")
COMPOSE_FILE = PROJECT_ROOT / "resource" / "docker" / "docker-compose.redis.yml"

### EXECUTE ###

docker = shutil.which("docker")
if docker:
    compose_cmd = [docker, "compose"]
else:
    compose = shutil.which("docker-compose")
    if not compose:
        sys.exit("Docker not found: install Docker Desktop to run the Redis dashboard.")
    compose_cmd = [compose]

if docker:
    existing = subprocess.run(
        [
            docker,
            "ps",
            "-a",
            "--filter",
            f"name=^/{REDIS_CONTAINER}$",
            "--filter",
            f"name=^/{COMMANDER_CONTAINER}$",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    existing_names = set(existing.stdout.split())
    if REDIS_CONTAINER in existing_names and COMMANDER_CONTAINER in existing_names:
        start = subprocess.run([docker, "start", REDIS_CONTAINER, COMMANDER_CONTAINER], cwd=PROJECT_ROOT)
        if start.returncode != 0:
            sys.exit(start.returncode)
    else:
        up = subprocess.run(
            compose_cmd + ["-f", str(COMPOSE_FILE), "up", "-d", "redis", "redis-commander"],
            cwd=PROJECT_ROOT,
        )
        if up.returncode != 0:
            sys.exit(up.returncode)
else:
    up = subprocess.run(
        compose_cmd + ["-f", str(COMPOSE_FILE), "up", "-d", "redis", "redis-commander"],
        cwd=PROJECT_ROOT,
    )
    if up.returncode != 0:
        sys.exit(up.returncode)

webbrowser.open(DASHBOARD_URL)
print(f"Redis dashboard available at {DASHBOARD_URL}")
