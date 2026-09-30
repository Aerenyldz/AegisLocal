$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

if (-not (Test-Path $python)) {
    Write-Host "Ilk kurulum: Python sanal ortami olusturuluyor..."
    python -m venv (Join-Path $backend ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Python sanal ortami olusturulamadi." }
    & $python -m pip install -r (Join-Path $backend "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Backend bagimliliklari kurulamadi." }
}

if (-not (Test-Port 8000)) {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "Set-Location '$root'; & '$python' -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000"
    )
}

if (-not (Test-Port 5500)) {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "Set-Location '$root'; & '$python' -m http.server 5500 --directory scripts\web"
    )
}

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 1
        if ($health.service -eq "AegisLocal") {
            $ready = $true
            break
        }
    } catch {
    }
    Start-Sleep -Seconds 1
}

if (-not $ready) { throw "AegisLocal API 8000 portunda hazir degil." }

Start-Process "http://127.0.0.1:5500/demo.html"
Write-Host ""
Write-Host "AegisLocal hazir."
Write-Host "Demo      : http://127.0.0.1:5500/demo.html"
Write-Host "Swagger   : http://127.0.0.1:8000/docs"
Write-Host "Dashboard : http://127.0.0.1:5500/audit-dashboard.html"
Write-Host ""
Write-Host "API ve web sunucusu ayri PowerShell pencerelerinde calisiyor."
