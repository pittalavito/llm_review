$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (Get-Command uv -ErrorAction SilentlyContinue) {
	& uv sync --extra dev --no-install-project
	& uv run pytest -v
	exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
	& python -m uv sync --extra dev --no-install-project
	& python -m uv run pytest -v
	exit $LASTEXITCODE
}

Write-Error "uv non trovato. Installa con: pip install uv"
exit 1
