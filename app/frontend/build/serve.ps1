[CmdletBinding()]
param(
    [int]$Port = 8080
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot 'dist'

if (-not (Test-Path -LiteralPath (Join-Path $DistRoot 'index.html'))) {
    & (Join-Path $PSScriptRoot 'build.ps1')
}

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    & py -m http.server $Port --directory $DistRoot
    exit $LASTEXITCODE
}

$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & python -m http.server $Port --directory $DistRoot
    exit $LASTEXITCODE
}

throw 'Python was not found. Run any static HTTP server with dist/ as its document root.'
