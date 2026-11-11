$ErrorActionPreference="SilentlyContinue"
$root="G:\bet_tracker\app"
$python=Join-Path $root ".venv\Scripts\python.exe"
$env:DJANGO_SETTINGS_MODULE="config.production"
Set-Location $root
function Get-AppSignature {
    $files=Get-ChildItem -LiteralPath $root -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
        $_.FullName -notmatch "\\(frontend|\.venv|__pycache__|\.git)(\\|$)" -and ($_.Extension -in @(".py",".html",".json",".yaml",".yml",".ini",".toml") -or $_.Name -eq ".env")
    } | Sort-Object FullName
    if(-not $files){return ""}
    return (($files | ForEach-Object {"$($_.FullName)|$($_.Length)|$($_.LastWriteTimeUtc.Ticks)"}) -join "`n")
}
function Start-App {
    $psi=New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName=$python
    $psi.WorkingDirectory=$root
    $psi.Arguments="-m waitress --listen=127.0.0.1:8000 --trusted-proxy=127.0.0.1 --trusted-proxy-headers=x-forwarded-proto config.wsgi:application"
    $psi.UseShellExecute=$false
    $psi.CreateNoWindow=$true
    return [Diagnostics.Process]::Start($psi)
}
function Stop-App($Process) {
    if($Process -and -not $Process.HasExited){
        & taskkill.exe /PID $Process.Id /T /F | Out-Null
        $Process.WaitForExit(5000)
    }
}
$sig=Get-AppSignature
$p=$null
while($true){
    if($null -eq $p -or $p.HasExited){$p=Start-App;Start-Sleep -Seconds 2}
    $new=Get-AppSignature
    if($new -ne $sig){$sig=$new;Stop-App $p;Start-Sleep -Seconds 1;$p=Start-App}
    Start-Sleep -Seconds 2
}