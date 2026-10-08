$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

$sourcePath = Join-Path `
    $root `
    "..\app\frontend\src\assets\js\generated\baseball-dashboard.js"

$outputPath = Join-Path `
    $root `
    "src\data\baseball-dashboard.json"

if(-not (Test-Path $sourcePath)){
    throw "Baseball dashboard source was not found: $sourcePath"
}

$source = Get-Content $sourcePath -Raw

$prefix = "const ALL_DATA="
$marker = "document.addEventListener("

$start = $source.IndexOf($prefix)

if($start -lt 0){
    throw "Could not locate ALL_DATA declaration."
}

$payloadStart = $start + $prefix.Length
$markerIndex = $source.IndexOf($marker, $payloadStart)

if($markerIndex -lt 0){
    throw "Could not locate DOMContentLoaded listener after ALL_DATA."
}

$json = $source.Substring(
    $payloadStart,
    $markerIndex - $payloadStart
).Trim()

$json = $json.TrimEnd(";").Trim()

try {
    $null = $json | ConvertFrom-Json
}
catch {
    throw "Extracted ALL_DATA is not valid JSON. $($_.Exception.Message)"
}

$json | Set-Content $outputPath -Encoding utf8

Write-Host "DATA EXTRACTION: PASS"
Write-Host "JSON: VALID"
