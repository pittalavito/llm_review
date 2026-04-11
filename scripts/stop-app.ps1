[CmdletBinding()]
param(
    [switch]$Preview
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$targets = Get-CimInstance Win32_Process | Where-Object {
    $cmd = $_.CommandLine
    if ([string]::IsNullOrWhiteSpace($cmd)) {
        return $false
    }

    # Match processes started by run-app.ps1 (uv run uvicorn / python -m uv run uvicorn)
    ($cmd -match "uvicorn\s+main:app" -or $cmd -match "-m\s+uvicorn\s+main:app") -and
    $cmd -match "--app-dir\s+src"
}

if (-not $targets) {
    Write-Host "No running app instances found."
    exit 0
}

Write-Host "Found $($targets.Count) app process(es):"
foreach ($proc in $targets) {
    Write-Host "- PID=$($proc.ProcessId) Name=$($proc.Name)"

    if ($Preview) {
        Write-Host "  Preview: would stop this process"
        continue
    }

    Stop-Process -Id $proc.ProcessId -Force
    Write-Host "  Stopped"
}

if ($Preview) {
    Write-Host "Preview completed. No process was terminated."
} else {
    Write-Host "Stop completed."
}
