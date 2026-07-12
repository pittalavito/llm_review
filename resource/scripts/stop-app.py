import sys
import psutil

PREVIEW = "--preview" in sys.argv

def is_target(proc: psutil.Process) -> bool:
    try:
        cmdline = proc.cmdline()
        joined = " ".join(cmdline)
        return (
            "uvicorn" in joined
            and "main:app" in joined
            and "--app-dir" in joined
            and "src" in joined
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

targets = [p for p in psutil.process_iter() if is_target(p)]

if not targets:
    print("No running app instances found.")
    sys.exit(0)

print(f"Found {len(targets)} app process(es):")
for proc in targets:
    try:
        print(f"- PID={proc.pid} Name={proc.name()}")
        if PREVIEW:
            print("  Preview: would stop this process")
        else:
            proc.kill()
            print("  Stopped")
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        print(f"  Warning: could not stop process: {e}")

if PREVIEW:
    print("Preview completed. No process was terminated.")
else:
    print("Stop completed.")
