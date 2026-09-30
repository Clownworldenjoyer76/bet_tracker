[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

$PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($PythonLauncher) {
    & py -3 -m venv ".venv"
}
elseif ($PythonCommand) {
    & python -m venv ".venv"
}
else {
    throw "Python 3 was not found on PATH."
}

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "Installing Django..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

Write-Host "Validating the migrated frontend..."
& $Python (Join-Path $ProjectRoot "scripts\sync_frontend.py")

Write-Host "Running Django system checks..."
& $Python (Join-Path $ProjectRoot "manage.py") check

Write-Host "Creating the temporary local foundation database..."
& $Python (Join-Path $ProjectRoot "manage.py") migrate --noinput

Write-Host "Running compatibility tests..."
& $Python (Join-Path $ProjectRoot "manage.py") test

Write-Host ""
Write-Host "DJANGO FOUNDATION READY"
Write-Host "Project: $ProjectRoot"
Write-Host ""
Write-Host "Start it with:"
Write-Host 'powershell -ExecutionPolicy Bypass -File ".\run_local.ps1"'
Write-Host ""
Write-Host "Then open: http://127.0.0.1:8000/"
