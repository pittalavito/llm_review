[CmdletBinding()]
param(
    [switch]$Preview,
    [switch]$IncludeVenv
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$excludePattern = [regex]::Escape("\.venv\")

$cacheDirs = Get-ChildItem -Path . -Directory -Recurse -Force |
    Where-Object {
        $_.Name -in @("__pycache__", ".pytest_cache") -and
        ($IncludeVenv -or $_.FullName -notmatch $excludePattern)
    }

$bytecodeFiles = Get-ChildItem -Path . -File -Recurse -Force |
    Where-Object {
        $_.Extension -in @(".pyc", ".pyo") -and
        ($IncludeVenv -or $_.FullName -notmatch $excludePattern)
    }

Write-Host "Scan root: $projectRoot"
Write-Host "Include .venv: $IncludeVenv"

if (($cacheDirs.Count + $bytecodeFiles.Count) -eq 0) {
    Write-Host "No Python cache artifacts found in project scope."
    exit 0
}

Write-Host "Found $($cacheDirs.Count) cache directories and $($bytecodeFiles.Count) bytecode files."

foreach ($dir in $cacheDirs) {
    Remove-Item -Path $dir.FullName -Recurse -Force -WhatIf:$Preview
}

foreach ($file in $bytecodeFiles) {
    Remove-Item -Path $file.FullName -Force -WhatIf:$Preview
}

if ($Preview) {
    Write-Host "Preview completed. No files were deleted."
} else {
    Write-Host "Cleanup completed."
}
