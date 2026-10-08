<#
  deploy-react-to-production.ps1
  ONE-WAY: G:\bet_tracker\react\react-dist  ->  G:\bet_tracker\app\frontend\dist
  - Default is DRY RUN. Nothing changes without -Apply.
  - Touches ONLY production dist. Never touches app\frontend\src. Never commits or pushes.
  - Copies ONLY an explicit allowlist (page shells, Vite root assets, 6 history CSVs, analytics.js, nav.js, nav.html);
    a denylist is asserted on every destination.
  - Backups, manifests and logs are written ONLY under C:\Users\Mat\Downloads.
  Usage:
    ...\deploy-react-to-production.ps1                       (dry run)
    ...\deploy-react-to-production.ps1 -Apply                (deploy)
    ...\deploy-react-to-production.ps1 -Apply -CleanOldAssets (deploy, then remove obsolete Vite root assets after verification)
    ...\deploy-react-to-production.ps1 -Apply -SkipNav       (deploy without nav.html; explicit choice; nav.js is still deployed)
    ...\deploy-react-to-production.ps1 -Rollback <manifest.json>          (rollback dry run)
    ...\deploy-react-to-production.ps1 -Rollback <manifest.json> -Apply   (rollback)
#>
[CmdletBinding()]
param(
  [switch]$Apply,
  [switch]$CleanOldAssets,
  [switch]$SkipNav,
  [string]$Rollback,
  [string]$BaseUrl   = 'http://127.0.0.1:8000',
  [string]$PublicUrl = 'https://api.sportsmodelhub.com'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ReactRoot = 'G:\bet_tracker\react'
$Src       = Join-Path $ReactRoot 'react-dist'
$Dst       = 'G:\bet_tracker\app\frontend\dist'
$OutRoot   = 'C:\Users\Mat\Downloads'
$Stamp     = Get-Date -Format 'yyyyMMdd_HHmmss'

# ---------------- ALLOWLIST ----------------
$Pages = @(
  'games_today.html','live_scores.html','final_scores.html','news.html','injury_tracker.html',
  'transactions.html','teams.html','players.html','standings.html','the_picks.html',
  'prop_engine.html','props_nfl.html','kelly_calculator.html','bet_history.html','bet_history_daily.html',
  'mlb_dashboard.html','baseball_dashboard.html','model_validation.html','manual_data.html','manual_venue_data.html',
  'pipeline_health.html','nba_dashboard.html','ncaam_dashboard.html','basketball_dashboard.html','wnba_dashboard.html',
  'nfl_dashboard.html','ufc_dashboard.html','nhl_dashboard.html','soccer_dashboard.html'
)
$HistoryFiles   = @('MLB.csv','MLB_LINEUPS.csv','WNBA.csv','NHL.csv','SOCCER.csv','UFC.csv')
$AnalyticsRel   = 'assets\js\shared\analytics.js'
$NavRel         = 'nav.html'
$NavJsRel       = 'assets\js\shared\nav.js'
# Shells that exist in react-dist but are intentionally NOT deployed
$NeverDeployShells = @('index.html','account.html')

# ---------------- DENYLIST (asserted on every destination) ----------------
$DenyRegex = @(
  '^(index|account|contact|about|accessibility|disclaimer|faq|methodology|privacy|responsible_gambling|terms|mat)\.html$',
  '^(football|hockey|mma|ncaaf|ncaab|cfl|bundesliga|epl|laliga|ligue1|mls|seriea)_dashboard\.html$',
  '^(nhl|soccer|ufc)_pipeline_health\.html$',
  '^\.nojekyll$', '^basketball\.json$', '^news$',
  '^data(\\|$)', '^assets\\css(\\|$)', '^assets\\images(\\|$)'
)

function Test-Denied([string]$rel) {
  if ($rel -match '\.\.') { return $true }
  foreach ($rx in $DenyRegex) { if ($rel -match $rx) { return $true } }
  if ($rel -match '^assets\\js(\\|$)' -and $rel -ne $AnalyticsRel -and $rel -ne $NavJsRel) { return $true }
  return $false
}
function Test-AllowedShape([string]$rel, [string]$kind) {
  switch ($kind) {
    'page'    { return ($Pages -contains $rel) }
    'asset'   { return ($rel -match '^assets\\[A-Za-z0-9._-]+$') }
    'history' { return ($rel -match '^history-data\\(MLB|MLB_LINEUPS|WNBA|NHL|SOCCER|UFC)\.csv$') }
    'shared'  { return ($rel -eq $AnalyticsRel -or $rel -eq $NavJsRel) }
    'nav'     { return ($rel -eq $NavRel) }
  }
  return $false
}
function Get-Md5([string]$p) { return (Get-FileHash -LiteralPath $p -Algorithm MD5).Hash }
function Ensure-Dir([string]$d) { if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null } }
function Copy-Safe([string]$s, [string]$d) {
  Ensure-Dir (Split-Path -Parent $d)
  $tmp = $d + '.smh_tmp'
  Copy-Item -LiteralPath $s -Destination $tmp -Force
  Move-Item -LiteralPath $tmp -Destination $d -Force
}
function Rel-Of([string]$full, [string]$root) { return $full.Substring($root.Length).TrimStart('\') }

# =====================================================================
# ROLLBACK MODE
# =====================================================================
if ($Rollback) {
  if (-not (Test-Path -LiteralPath $Rollback)) { throw "Manifest not found: $Rollback" }
  $m = Get-Content -LiteralPath $Rollback -Raw | ConvertFrom-Json
  $mdir = Split-Path -Parent $Rollback
  if ($m.destination -ne $Dst) { throw "Manifest destination '$($m.destination)' does not match $Dst" }
  $acts = New-Object System.Collections.Generic.List[object]
  $bad  = New-Object System.Collections.Generic.List[string]
  foreach ($e in @($m.entries)) {
    $target = Join-Path $Dst $e.rel
    if (Test-Denied $e.rel) { $bad.Add("denylisted path in manifest: $($e.rel)"); continue }
    if ($e.action -eq 'REPLACE') {
      $bk = Join-Path $mdir ('backup\' + $e.rel)
      if (-not (Test-Path -LiteralPath $bk)) { $bad.Add("backup missing: $bk"); continue }
      if ((Get-Md5 $bk) -ne $e.dstMd5Before) { $bad.Add("backup hash mismatch: $bk"); continue }
      $acts.Add([pscustomobject]@{ Op='RESTORE'; Rel=$e.rel; From=$bk; To=$target })
    } elseif ($e.action -eq 'ADD') {
      if (Test-Path -LiteralPath $target) {
        if ((Get-Md5 $target) -ne $e.srcMd5) { $bad.Add("added file changed since deploy, will not delete: $($e.rel)"); continue }
        $acts.Add([pscustomobject]@{ Op='DELETE'; Rel=$e.rel; From=''; To=$target })
      }
    }
  }
  foreach ($r in @($m.removed)) {
    $bk = Join-Path $mdir ('removed\' + $r.rel)
    if (-not (Test-Path -LiteralPath $bk)) { $bad.Add("removed-file backup missing: $bk"); continue }
    $acts.Add([pscustomobject]@{ Op='RESTORE'; Rel=$r.rel; From=$bk; To=(Join-Path $Dst $r.rel) })
  }
  Write-Host "ROLLBACK PLAN from $Rollback"
  $acts | Format-Table Op, Rel -AutoSize | Out-String | Write-Host
  foreach ($b in $bad) { Write-Host "PROBLEM: $b" -ForegroundColor Red }
  if ($bad.Count -gt 0) { Write-Host 'Rollback REFUSED (problems above).' -ForegroundColor Red; exit 1 }
  if (-not $Apply) { Write-Host 'ROLLBACK DRY RUN - nothing changed. Add -Apply to execute.'; exit 0 }
  foreach ($a in $acts) {
    if ($a.Op -eq 'RESTORE') { Copy-Safe $a.From $a.To } else { Remove-Item -LiteralPath $a.To -Force }
  }
  Write-Host 'ROLLBACK APPLIED. Re-check the site and purge Cloudflare URLs for restored unhashed .js/.csv files.' -ForegroundColor Yellow
  exit 0
}

# =====================================================================
# DEPLOY / DRY RUN
# =====================================================================
$Blockers = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]

function Stop-IfBlocked {
  if ($Blockers.Count -gt 0) {
    Write-Host ''
    Write-Host 'BLOCKED - a real -Apply would be REFUSED:' -ForegroundColor Red
    foreach ($b in $Blockers) { Write-Host "  - $b" -ForegroundColor Red }
    foreach ($w in $Warnings) { Write-Host "  (warning) $w" -ForegroundColor Yellow }
    Write-Host 'Nothing was changed.'
    exit 1
  }
}

# ---- 1. path sanity
if (-not (Test-Path -LiteralPath $Src -PathType Container)) { $Blockers.Add("react-dist not found: $Src") }
if (-not (Test-Path -LiteralPath $Dst -PathType Container)) { $Blockers.Add("production dist not found: $Dst") }
if ($Blockers.Count -eq 0) {
  foreach ($f in 'index.html','nav.html') {
    if (-not (Test-Path -LiteralPath (Join-Path $Dst $f))) { $Blockers.Add("production dist is missing $f (unexpected)") }
  }
}
Stop-IfBlocked

# ---- 2. structural validation of react-dist
$jsRefs  = @{}
$cssRefs = @{}
foreach ($p in $Pages) {
  $f = Join-Path $Src $p
  if (-not (Test-Path -LiteralPath $f)) { $Blockers.Add("react-dist missing page shell: $p"); continue }
  if ((Get-Item -LiteralPath $f).Length -lt 100) { $Blockers.Add("shell suspiciously small: $p"); continue }
  $t = [IO.File]::ReadAllText($f)
  if ($t -notmatch '<div id="root">')        { $Blockers.Add("$p has no <div id=""root"">") }
  if ($t -match '/src/main\.tsx')            { $Blockers.Add("$p is an unbuilt dev shell (references /src/main.tsx)") }
  $mj = [regex]::Matches($t, '<script[^>]*type="module"[^>]*src="\./assets/(main-[A-Za-z0-9_-]+\.js)"')
  $mc = [regex]::Matches($t, '<link[^>]*rel="stylesheet"[^>]*href="\./assets/(main-[A-Za-z0-9_-]+\.css)"')
  if ($mj.Count -ne 1) { $Blockers.Add("$p must reference exactly one main-*.js (found $($mj.Count))") } else { $jsRefs[$mj[0].Groups[1].Value] = 1 }
  if ($mc.Count -ne 1) { $Blockers.Add("$p must reference exactly one main-*.css (found $($mc.Count))") } else { $cssRefs[$mc[0].Groups[1].Value] = 1 }
  foreach ($m in [regex]::Matches($t, '(?:src|href)="(\./[^"]+)"')) {
    $rp = Join-Path $Src ($m.Groups[1].Value.Substring(2) -replace '/', '\')
    if (-not (Test-Path -LiteralPath $rp)) { $Blockers.Add("$p references missing local file: $($m.Groups[1].Value)") }
  }
}
if ($jsRefs.Count  -gt 1) { $Blockers.Add("shells reference $($jsRefs.Count) different JS bundles (expected 1): $($jsRefs.Keys -join ', ')") }
if ($cssRefs.Count -gt 1) { $Blockers.Add("shells reference $($cssRefs.Count) different CSS bundles (expected 1): $($cssRefs.Keys -join ', ')") }

$AssetDir = Join-Path $Src 'assets'
$AssetFiles = @()
if (Test-Path -LiteralPath $AssetDir) { $AssetFiles = @(Get-ChildItem -LiteralPath $AssetDir -File) }
if ($AssetFiles.Count -eq 0) { $Blockers.Add('react-dist\assets has no root files') }
foreach ($a in $AssetFiles) { if ($a.Name -notmatch '^[A-Za-z0-9._-]+$') { $Blockers.Add("unexpected asset file name: $($a.Name)") } }
foreach ($n in @($jsRefs.Keys) + @($cssRefs.Keys)) {
  if (-not ($AssetFiles | Where-Object { $_.Name -eq $n })) { $Blockers.Add("referenced bundle not found in react-dist\assets: $n") }
}

foreach ($h in $HistoryFiles) {
  $hp = Join-Path $Src ('history-data\' + $h)
  if (-not (Test-Path -LiteralPath $hp)) { $Blockers.Add("react-dist missing history-data\$h"); continue }
  if ((Get-Item -LiteralPath $hp).Length -lt 50) { $Blockers.Add("history-data\$h is nearly empty") }
  else {
    $first = (Get-Content -LiteralPath $hp -TotalCount 1)
    if ($first -notmatch ',') { $Blockers.Add("history-data\$h first line does not look like a CSV header") }
  }
}

$extraShells = @(Get-ChildItem -LiteralPath $Src -Filter *.html -File | Where-Object { ($Pages -notcontains $_.Name) -and ($NeverDeployShells -notcontains $_.Name) -and ($_.Name -ne 'nav.html') })
foreach ($x in $extraShells) { $Warnings.Add("react-dist has $($x.Name) which is NOT in the allowlist and will NOT be deployed") }

# ---- 3. stale-build guard
$buildFiles = @()
$buildFiles += $Pages | ForEach-Object { Join-Path $Src $_ } | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { Get-Item -LiteralPath $_ }
# only Vite-emitted bundles count as build time (files copied from public\ keep their old mtimes)
$buildFiles += @($AssetFiles | Where-Object { $jsRefs.ContainsKey($_.Name) -or $cssRefs.ContainsKey($_.Name) })
if ($buildFiles.Count -gt 0) {
  $buildTime = ($buildFiles | Sort-Object LastWriteTime | Select-Object -First 1).LastWriteTime
  $srcFiles = @()
  foreach ($d in 'src','public','..\app\frontend\src') {
    $dp = Join-Path $ReactRoot $d
    if (Test-Path -LiteralPath $dp) { $srcFiles += @(Get-ChildItem -LiteralPath $dp -Recurse -File -ErrorAction SilentlyContinue) }
  }
  foreach ($f in 'package.json','package-lock.json','vite.config.ts','tsconfig.json') {
    $fp = Join-Path $ReactRoot $f
    if (Test-Path -LiteralPath $fp) { $srcFiles += Get-Item -LiteralPath $fp }
  }
  $srcFiles += @(Get-ChildItem -LiteralPath $ReactRoot -Filter *.html -File)
  $newest = $srcFiles | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  Write-Host ("Build time (oldest shell/bundle): {0}" -f $buildTime)
  Write-Host ("Newest React source file       : {0}  {1}" -f $newest.LastWriteTime, $newest.FullName)
  if ($newest.LastWriteTime -gt $buildTime) {
    $Blockers.Add("react-dist is STALE: source file newer than the build: $($newest.FullName) ($($newest.LastWriteTime)). Run a fresh successful React build.")
  }
}
# public -> react-dist copies of the unhashed files that will be deployed must match
$pubChecks = @($AnalyticsRel, $NavJsRel, $NavRel) + ($HistoryFiles | ForEach-Object { 'history-data\' + $_ })
foreach ($rel in $pubChecks) {
  $pp = Join-Path (Join-Path $ReactRoot 'public') $rel
  $dp = Join-Path $Src $rel
  if ((Test-Path -LiteralPath $pp) -and (Test-Path -LiteralPath $dp)) {
    if ((Get-Md5 $pp) -ne (Get-Md5 $dp)) { $Blockers.Add("react-dist\$rel differs from public\$rel (build is out of date)") }
  }
}

# ---- 4. analytics.js gate: only the approved smh-league-controls lines may differ
$AnalyticsSkip = $false
$srcAn = Join-Path $Src $AnalyticsRel
$dstAn = Join-Path $Dst $AnalyticsRel
if (-not (Test-Path -LiteralPath $srcAn)) { $Blockers.Add("react-dist missing $AnalyticsRel") }
elseif (-not (Test-Path -LiteralPath $dstAn)) { $Blockers.Add("production dist missing $AnalyticsRel (unexpected)") }
else {
  $sl = [string[]]@([IO.File]::ReadAllLines($srcAn) | ForEach-Object { $_.TrimEnd() })
  $dl = [string[]]@([IO.File]::ReadAllLines($dstAn) | ForEach-Object { $_.TrimEnd() })
  $sSet = [Collections.Generic.HashSet[string]]::new($sl)
  $dSet = [Collections.Generic.HashSet[string]]::new($dl)
  $removed = @($dl | Where-Object { -not $sSet.Contains($_) })
  $added   = @($sl | Where-Object { -not $dSet.Contains($_) })
  if ($removed.Count -gt 0) { $Blockers.Add("analytics.js: $($removed.Count) production line(s) would be lost (first: '$($removed[0].Trim())')") }
  $unapproved = @($added | Where-Object { $_ -notmatch 'smh-league-controls' })
  if ($unapproved.Count -gt 0) { $Blockers.Add("analytics.js: $($unapproved.Count) added line(s) are not the approved smh-league-controls change (first: '$($unapproved[0].Trim())')") }
  if (@($sl | Where-Object { $_ -match 'smh-league-controls' }).Count -eq 0) { $Blockers.Add('react-dist analytics.js does not contain the approved smh-league-controls change (stale or wrong build)') }
  elseif ($removed.Count -eq 0 -and $added.Count -eq 0) { $AnalyticsSkip = $true; $Warnings.Add('production analytics.js already has identical content (ignoring line endings); not copied') }
}

# ---- 4b. nav.js gate: merged React + production requirements must all be present
$srcNavJs = Join-Path $Src $NavJsRel
$dstNavJs = Join-Path $Dst $NavJsRel
if (-not (Test-Path -LiteralPath $srcNavJs)) { $Blockers.Add("react-dist missing $NavJsRel") }
else {
  $nj = [IO.File]::ReadAllText($srcNavJs)
  $mustHave = @(
    'window.SMH_NAV_BASE', 'fetch((window.SMH_NAV_BASE',
    'SMH_FAVICON_START', 'SMH_FAVICON_END',
    'SMH_POSTHOG_LOADER_START', 'SMH_POSTHOG_LOADER_END',
    'SMH_NAV_PREFETCH_START', 'SMH_NAV_PREFETCH_END',
    'SMH_FOOTER_START', 'SMH_FOOTER_END',
    '__smhFooterAdded', 'footer.smh-footer', '/assets/css/footer.css'
  )
  foreach ($tok in $mustHave) { if (-not $nj.Contains($tok)) { $Blockers.Add("nav.js: required content missing: $tok") } }
  $guard = 'if (window.__smhReactNavScriptLoaded) return;'
  $fs = $nj.IndexOf('SMH_FOOTER_START'); $fe = $nj.IndexOf('SMH_FOOTER_END'); $gi = $nj.IndexOf($guard); $ai = $nj.IndexOf('window.__smhFooterAdded')
  if ($gi -lt 0)                                  { $Blockers.Add('nav.js: React footer guard line is missing (React pages would get a duplicate injected footer and production footer.css)') }
  elseif ($fs -lt 0 -or $fe -lt 0 -or $gi -lt $fs -or $gi -gt $fe -or ($ai -ge 0 -and $gi -gt $ai)) { $Blockers.Add('nav.js: React footer guard is not at the start of the footer block') }
  if (Test-Path -LiteralPath $dstNavJs) {
    $pnj = [IO.File]::ReadAllText($dstNavJs)
    foreach ($mk in ([regex]::Matches($pnj, 'SMH_[A-Z_]+_(?:START|END)') | ForEach-Object { $_.Value } | Sort-Object -Unique)) {
      if (-not $nj.Contains($mk)) { $Blockers.Add("nav.js: production marker $mk would be lost") }
    }
  } else { $Warnings.Add("production dist has no $NavJsRel (it will be ADDED)") }
}

# ---- 5. nav.html gate (approved merged behavior)
$NavSkip = [bool]$SkipNav
if ($NavSkip) { $Warnings.Add('nav.html SKIPPED by -SkipNav (production menu will keep legacy Hockey/MMA links)') }
else {
  $srcNav = Join-Path $Src $NavRel
  $dstNav = Join-Path $Dst $NavRel
  if (-not (Test-Path -LiteralPath $srcNav)) { $Blockers.Add('react-dist\nav.html missing') }
  else {
    $t = [IO.File]::ReadAllText($srcNav)
    foreach ($m in [regex]::Matches($t, '<a\b[^>]*nav-dropdown-toggle[^>]*>')) {
      if ($m.Value -match '\bhref\s*=') {
        $dp = [regex]::Match($m.Value, 'data-page="([^"]*)"').Groups[1].Value
        $Blockers.Add("nav.html: dropdown parent '$dp' has an href (parents must not navigate)")
      }
    }
    $need = @(
      @('Admin > Contact Messages link', 'href="https://api\.sportsmodelhub\.com/admin/accounts/contactmessage/"[^>]*data-page="contact_messages"'),
      @('Account uses absolute production URL', 'href="https://api\.sportsmodelhub\.com/account\.html"[^>]*data-page="account"'),
      @('Hockey -> nhl_dashboard.html', 'href="nhl_dashboard\.html"[^>]*data-page="hockey_dashboard"'),
      @('MMA -> ufc_dashboard.html', 'href="ufc_dashboard\.html"[^>]*data-page="mma_dashboard"'),
      @('Info dropdown', 'data-page="info"'),
      @('Admin dropdown', 'data-page="admin"')
    )
    foreach ($n in $need) { if ($t -notmatch $n[1]) { $Blockers.Add("nav.html: missing/incorrect: $($n[0])") } }
    foreach ($ip in 'about','methodology','faq','contact','responsible_gambling','disclaimer','privacy','terms','accessibility') {
      if ($t -notmatch ('href="(?:https://api\.sportsmodelhub\.com/)?' + $ip + '\.html"[^>]*data-page="' + $ip + '"')) { $Blockers.Add("nav.html: Info link missing: $ip") }
    }
    if (Test-Path -LiteralPath $dstNav) {
      $prod = [IO.File]::ReadAllText($dstNav)
      $prodPages = [regex]::Matches($prod, 'data-page="([^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique
      foreach ($x in $prodPages) { if ($t -notmatch ('data-page="' + [regex]::Escape($x) + '"')) { $Blockers.Add("nav.html: production data-page '$x' is missing from the React nav") } }
    }
  }
}

# ---- 6. build the plan
$Plan = New-Object System.Collections.Generic.List[object]
function Add-Plan([string]$rel, [string]$sp, [string]$kind) {
  if (-not (Test-AllowedShape $rel $kind)) { $Blockers.Add("allowlist shape violation: [$kind] $rel"); return }
  if (Test-Denied $rel)                    { $Blockers.Add("DENYLIST hit: $rel"); return }
  $dp = Join-Path $Dst $rel
  $full = [IO.Path]::GetFullPath($dp)
  if (-not $full.StartsWith($Dst + '\', [StringComparison]::OrdinalIgnoreCase)) { $Blockers.Add("destination escapes dist: $rel"); return }
  if (-not (Test-Path -LiteralPath $sp)) { $Blockers.Add("source missing: $sp"); return }
  $sm = Get-Md5 $sp
  $action = 'ADD'; $dm = ''
  if (Test-Path -LiteralPath $dp) { $dm = Get-Md5 $dp; if ($dm -eq $sm) { $action = 'SAME' } else { $action = 'REPLACE' } }
  $Plan.Add([pscustomobject]@{ Action=$action; Kind=$kind; Rel=$rel; Src=$sp; Dst=$dp; SrcMd5=$sm; DstMd5Before=$dm })
}
foreach ($a in $AssetFiles) { Add-Plan ('assets\' + $a.Name) $a.FullName 'asset' }
if (-not $AnalyticsSkip -and (Test-Path -LiteralPath $srcAn)) { Add-Plan $AnalyticsRel $srcAn 'shared' }
if (Test-Path -LiteralPath $srcNavJs) { Add-Plan $NavJsRel $srcNavJs 'shared' }
foreach ($h in $HistoryFiles) { Add-Plan ('history-data\' + $h) (Join-Path $Src ('history-data\' + $h)) 'history' }
if (-not $NavSkip -and (Test-Path -LiteralPath (Join-Path $Src $NavRel))) { Add-Plan $NavRel (Join-Path $Src $NavRel) 'nav' }
foreach ($p in $Pages) { $sp = Join-Path $Src $p; if (Test-Path -LiteralPath $sp) { Add-Plan $p $sp 'page' } }

# ---- 7. obsolete Vite root assets (only evaluated; removed only with -Apply -CleanOldAssets after verification)
$newAssetNames = @($AssetFiles | ForEach-Object { $_.Name })
$Obsolete = @()
$dstAssetDir = Join-Path $Dst 'assets'
if (Test-Path -LiteralPath $dstAssetDir) {
  $otherHtml = @(Get-ChildItem -LiteralPath $Dst -Filter *.html -File | Where-Object { $Pages -notcontains $_.Name })
  $otherText = ($otherHtml | ForEach-Object { [IO.File]::ReadAllText($_.FullName) }) -join "`n"
  foreach ($f in @(Get-ChildItem -LiteralPath $dstAssetDir -File)) {
    if (($newAssetNames -notcontains $f.Name) -and ($f.Name -match '^(main|landing-bg-desktop)-[A-Za-z0-9_-]+\.(js|css|webp)$')) {
      if ($otherText.Contains($f.Name)) { $Warnings.Add("old asset $($f.Name) is still referenced by a non-React page; will not be cleaned") }
      else { $Obsolete += $f }
    }
  }
}

# ---- 8. report plan
$changes = @($Plan | Where-Object { $_.Action -ne 'SAME' })
$sameCt  = @($Plan | Where-Object { $_.Action -eq 'SAME' }).Count
Write-Host ''
Write-Host ('MODE: ' + $(if ($Apply) { 'APPLY' } else { 'DRY RUN' }))
Write-Host "Source     : $Src"
Write-Host "Destination: $Dst"
Write-Host ('Plan: {0} to change ({1} ADD, {2} REPLACE), {3} identical/skipped' -f $changes.Count, @($changes | Where-Object { $_.Action -eq 'ADD' }).Count, @($changes | Where-Object { $_.Action -eq 'REPLACE' }).Count, $sameCt)
$changes | Format-Table Action, Kind, Rel -AutoSize | Out-String | Write-Host
if ($Obsolete.Count -gt 0) {
  Write-Host ('Obsolete Vite root assets (removed only with -Apply -CleanOldAssets after verification): ' + (($Obsolete | ForEach-Object { $_.Name }) -join ', '))
}
foreach ($w in $Warnings) { Write-Host "(warning) $w" -ForegroundColor Yellow }

$purge = @($changes | Where-Object { $_.Kind -in 'shared','history' } | ForEach-Object { $PublicUrl + '/' + ($_.Rel -replace '\\', '/') })
if ($purge.Count -gt 0) {
  Write-Host ''
  Write-Host 'Cloudflare URLs to purge after deployment (unhashed, cacheable):' -ForegroundColor Cyan
  $purge | ForEach-Object { Write-Host "  $_" }
} else { Write-Host 'No unhashed cacheable files change: no Cloudflare purge needed (hashed assets and .html are not cached).' }

Stop-IfBlocked

if (-not $Apply) {
  Write-Host ''
  Write-Host 'DRY RUN COMPLETE - nothing was changed. No blockers found; -Apply would proceed.' -ForegroundColor Green
  exit 0
}

# =====================================================================
# APPLY
# =====================================================================
$Run = Join-Path $OutRoot ("react_deploy_$Stamp")
Ensure-Dir $Run; Ensure-Dir (Join-Path $Run 'backup'); Ensure-Dir (Join-Path $Run 'removed')
$ManifestPath = Join-Path $Run 'manifest.json'

# snapshot of everything that must NOT change
$planRels = @($changes | ForEach-Object { $_.Rel })
$before = @{}
Get-ChildItem -LiteralPath $Dst -Recurse -File | ForEach-Object {
  $r = Rel-Of $_.FullName $Dst
  if ($planRels -notcontains $r) { $before[$r] = Get-Md5 $_.FullName }
}
Write-Host ("Protected snapshot: {0} files hashed" -f $before.Count)

# backups (verified before anything is changed)
foreach ($c in @($changes | Where-Object { $_.Action -eq 'REPLACE' })) {
  $bk = Join-Path $Run ('backup\' + $c.Rel)
  Ensure-Dir (Split-Path -Parent $bk)
  Copy-Item -LiteralPath $c.Dst -Destination $bk -Force
  if ((Get-Md5 $bk) -ne $c.DstMd5Before) { throw "Backup verification failed for $($c.Rel). Nothing was changed." }
}

function Save-Manifest([string]$status, $removedList) {
  $man = [ordered]@{
    created     = (Get-Date).ToString('s')
    status      = $status
    source      = $Src
    destination = $Dst
    entries     = @($changes | ForEach-Object { [ordered]@{ rel=$_.Rel; kind=$_.Kind; action=$_.Action; srcMd5=$_.SrcMd5; dstMd5Before=$_.DstMd5Before } })
    removed     = @($removedList)
    purgeUrls   = @($purge)
  }
  ($man | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
}
Save-Manifest 'applying' @()

# copy order: assets -> shared -> history -> nav -> pages (shells last so they never point at missing files)
$rank = @{ asset=1; shared=2; history=3; nav=4; page=5 }
foreach ($c in @($changes | Sort-Object { $rank[$_.Kind] })) {
  Copy-Safe $c.Src $c.Dst
  Write-Host ("  {0,-8} {1}" -f $c.Action, $c.Rel)
}

# ---- verification
$fails = New-Object System.Collections.Generic.List[string]
foreach ($c in $changes) {
  if (-not (Test-Path -LiteralPath $c.Dst)) { $fails.Add("missing after copy: $($c.Rel)"); continue }
  if ((Get-Md5 $c.Dst) -ne $c.SrcMd5)       { $fails.Add("hash mismatch after copy: $($c.Rel)") }
}
foreach ($p in $Pages) {
  $t = [IO.File]::ReadAllText((Join-Path $Dst $p))
  foreach ($m in [regex]::Matches($t, '(?:src|href)="(\./[^"]+)"')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Dst ($m.Groups[1].Value.Substring(2) -replace '/', '\')))) { $fails.Add("$p references missing file in dist: $($m.Groups[1].Value)") }
  }
}
Get-ChildItem -LiteralPath $Dst -Recurse -File | ForEach-Object {
  $r = Rel-Of $_.FullName $Dst
  if ($r -like '*.smh_tmp') { $fails.Add("leftover temp file: $r"); return }
  if ($before.ContainsKey($r)) { if ((Get-Md5 $_.FullName) -ne $before[$r]) { $fails.Add("PROTECTED FILE CHANGED: $r") } }
  elseif ($planRels -notcontains $r) { $fails.Add("unexpected new file in dist: $r") }
}
foreach ($k in $before.Keys) { if (-not (Test-Path -LiteralPath (Join-Path $Dst $k))) { $fails.Add("PROTECTED FILE MISSING: $k") } }

function Test-Http([string]$path, [string]$mustContain, [string]$ctRegex) {
  $u = $BaseUrl + $path
  try { $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 30 -MaximumRedirection 5 }
  catch { $fails.Add("HTTP FAIL $u : $($_.Exception.Message)"); return }
  if ([int]$r.StatusCode -ne 200) { $fails.Add("HTTP $($r.StatusCode) $u"); return }
  if ($ctRegex) {
    $ct = [string]$r.Headers['Content-Type']
    if ($ct -notmatch $ctRegex) { $fails.Add("Content-Type '$ct' at $u (expected $ctRegex)") }
  }
  if ($mustContain) {
    if (([string]$r.Content) -notmatch $mustContain) { $fails.Add("expected content not found at $u") }
  }
}
Write-Host 'HTTP verification against ' $BaseUrl
try {
  $rz = Invoke-WebRequest -Uri ($BaseUrl + '/readyz') -UseBasicParsing -TimeoutSec 30
  if (([string]$rz.Content | ConvertFrom-Json).status -ne 'ok') { $fails.Add('/readyz status is not ok') }
} catch { $fails.Add("/readyz failed: $($_.Exception.Message)") }
foreach ($p in $Pages) { Test-Http ('/' + $p) 'id="root"' 'text/html' }
foreach ($n in @($jsRefs.Keys))  { Test-Http ('/assets/' + $n) '' 'javascript' }
foreach ($n in @($cssRefs.Keys)) { Test-Http ('/assets/' + $n) '' 'css' }
foreach ($h in $HistoryFiles)    { Test-Http ('/history-data/' + $h) '' '' }
Test-Http '/nav.html' 'nav' ''
Test-Http '/assets/js/shared/analytics.js' 'smh' 'javascript'
Test-Http '/assets/js/shared/nav.js' 'SMH_NAV_BASE' 'javascript'
foreach ($django in '/', '/index.html', '/login.html', '/contact.html') { Test-Http $django '' '' }

if ($fails.Count -gt 0) {
  Save-Manifest 'verify_failed' @()
  Write-Host ''
  Write-Host 'VERIFICATION FAILED:' -ForegroundColor Red
  $fails | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
  Write-Host "Nothing was rolled back automatically. Manifest: $ManifestPath"
  Write-Host "To roll back: & '$PSCommandPath' -Rollback '$ManifestPath' -Apply"
  exit 1
}

# ---- optional cleanup of obsolete Vite root assets (only after successful verification)
$removedList = @()
if ($CleanOldAssets -and $Obsolete.Count -gt 0) {
  Ensure-Dir (Join-Path $Run 'removed\assets')
  foreach ($f in $Obsolete) {
    Copy-Item -LiteralPath $f.FullName -Destination (Join-Path $Run ('removed\assets\' + $f.Name)) -Force
    Remove-Item -LiteralPath $f.FullName -Force
    $removedList += [pscustomobject]@{ rel = ('assets\' + $f.Name) }
    Write-Host ("  REMOVED  assets\{0}" -f $f.Name)
  }
}
Save-Manifest 'applied' $removedList

Write-Host ''
Write-Host 'DEPLOYED AND VERIFIED (hashes + HTTP). Browser testing has NOT been done by this script.' -ForegroundColor Green
Write-Host "Manifest / backups: $Run"
if ($purge.Count -gt 0) { Write-Host 'Purge these in Cloudflare:' -ForegroundColor Cyan; $purge | ForEach-Object { Write-Host "  $_" } }
Write-Host "Rollback: & '$PSCommandPath' -Rollback '$ManifestPath' -Apply"
Write-Host 'Nothing was committed or pushed.'
exit 0