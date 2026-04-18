$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (Get-Command uv -ErrorAction SilentlyContinue) {
	& uv sync --no-install-project
	& uv run uvicorn main:app --app-dir src --reload --host 0.0.0.0 --port 8080
	exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
	& python -m uv sync --no-install-project
	& python -m uv run uvicorn main:app --app-dir src --reload --host 0.0.0.0 --port 8080
	exit $LASTEXITCODE
}

Write-Error "uv non trovato. Installa con: pip install uv"
exit 1
