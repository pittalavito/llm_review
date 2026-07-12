import shutil
import subprocess
import sys

from _env import PROJECT_ROOT, env_value

port = env_value("APP_PORT", "8081")
host = env_value("APP_HOST", "0.0.0.0")

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
                  "--host", host, "--port", port],
    cwd=PROJECT_ROOT,
)
sys.exit(result.returncode)
