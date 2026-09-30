[CmdletBinding()]
param(
    [switch]$NoClean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$SourceRoot  = Join-Path $ProjectRoot 'src'
$PagesRoot   = Join-Path $SourceRoot 'pages'
$Components  = Join-Path $SourceRoot 'components'
$AssetsRoot  = Join-Path $SourceRoot 'assets'
$DataRoot    = Join-Path $SourceRoot 'data'
$PublicRoot  = Join-Path $SourceRoot 'public'
$DistRoot    = Join-Path $ProjectRoot 'dist'

foreach ($required in @($SourceRoot, $PagesRoot, $AssetsRoot)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "Required source path is missing: $required"
    }
}

if ((Test-Path -LiteralPath $DistRoot) -and -not $NoClean) {
    Remove-Item -LiteralPath $DistRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $DistRoot -Force | Out-Null

function Copy-DirectoryContents {
    param(
        [Parameter(Mandatory)][string]$Source,
        [Parameter(Mandatory)][string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) { return }
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
    }
}

# Pages publish at the site root so existing URLs remain unchanged.
Get-ChildItem -LiteralPath $PagesRoot -File -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $DistRoot $_.Name) -Force
}

# nav.html is an existing runtime component loaded by assets/js/shared/nav.js.
if (Test-Path -LiteralPath (Join-Path $Components 'nav.html')) {
    Copy-Item -LiteralPath (Join-Path $Components 'nav.html') -Destination (Join-Path $DistRoot 'nav.html') -Force
}

Copy-DirectoryContents -Source $AssetsRoot -Destination (Join-Path $DistRoot 'assets')
Copy-DirectoryContents -Source $DataRoot   -Destination (Join-Path $DistRoot 'data')

# Root passthrough files: .nojekyll, JSON files, etc.
if (Test-Path -LiteralPath $PublicRoot) {
    Get-ChildItem -LiteralPath $PublicRoot -File -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $DistRoot $_.Name) -Force
    }
}

# ---------------- Validation ----------------
$errors = [System.Collections.Generic.List[string]]::new()

if (-not (Test-Path -LiteralPath (Join-Path $DistRoot 'index.html'))) {
    $errors.Add('dist/index.html is missing.')
}
if (-not (Test-Path -LiteralPath (Join-Path $DistRoot 'nav.html'))) {
    $errors.Add('dist/nav.html is missing.')
}

$attrPattern = '(?i)\b(?:href|src)=["'']([^"'']+)["'']'
$inlineStylePattern = '(?is)<style(?:\s[^>]*)?>'
$inlineScriptPattern = '(?is)<script(?![^>]*\bsrc\s*=)[^>]*>'

Get-ChildItem -LiteralPath $DistRoot -File -Force | ForEach-Object {
    $file = $_
    $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction SilentlyContinue
    if (-not [string]::IsNullOrWhiteSpace($text) -and $text -match '(?i)<html') {
        if ($text -match $inlineStylePattern) {
            $errors.Add("$($file.Name): inline <style> block found.")
        }
        if ($text -match $inlineScriptPattern) {
            $errors.Add("$($file.Name): inline executable <script> found.")
        }

        foreach ($match in [regex]::Matches($text, $attrPattern)) {
            $url = $match.Groups[1].Value
            if ($url -match '^(?:#|https?:|mailto:|tel:|javascript:|data:|//)') { continue }

            $clean = ($url -split '[?#]', 2)[0]
            if ([string]::IsNullOrWhiteSpace($clean)) { continue }

            $candidate = Join-Path $file.DirectoryName $clean
            if (-not (Test-Path -LiteralPath $candidate)) {
                $errors.Add("$($file.Name): missing local reference '$url'.")
            }
        }
    }
}

if ($errors.Count -gt 0) {
    Write-Host "BUILD FAILED ($($errors.Count) validation error(s))" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    throw 'Build validation failed.'
}

$pageCount = (Get-ChildItem -LiteralPath $PagesRoot -File -Force).Count
$assetCount = (Get-ChildItem -LiteralPath (Join-Path $DistRoot 'assets') -File -Recurse -Force).Count

Write-Host "BUILD OK" -ForegroundColor Green
Write-Host "Pages:  $pageCount"
Write-Host "Assets: $assetCount"
Write-Host "Output: $DistRoot"
