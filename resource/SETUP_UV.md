# Backend Setup (uv)

Use this workflow on Windows, macOS, and Linux.

## Requirements
- Python 3.12+
- uv

```bash
python -m pip install uv
```

## Install dependencies
```bash
cd llm_review
python -m uv sync --extra dev --no-install-project
```

## Run API
```bash
./scripts/run-app.ps1
```

## Run tests
```bash
./scripts/run-test.ps1
```

## Clean cache (optional)
```bash
./scripts/clean-cache.ps1 -Preview
./scripts/clean-cache.ps1
```

## Dependency commands
```bash
python -m uv add <package>
python -m uv add --dev <package>
python -m uv remove <package>
python -m uv lock
```
