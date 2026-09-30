Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment is missing. Run .\setup_local.ps1 first."
}

Set-Location -LiteralPath $ProjectRoot
& $Python manage.py runserver 127.0.0.1:8000
