$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Python virtual environment bulunamadi, olusturuluyor..."
    python -m venv (Join-Path $backend ".venv")
    if ($LASTEXITCODE -ne 0) {
        throw "Python virtual environment olusturulamadi."
    }
    & $python -m pip install -r (Join-Path $backend "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Python bagimliliklari kurulamadı."
    }
}

function Test-Port($port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
}

if (-not (Test-Port 8001)) {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "Set-Location '$root'; & '$python' -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001"
    )
}

if (-not (Test-Port 5500)) {
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-ExecutionPolicy", "Bypass", "-Command",
        "Set-Location '$root'; & '$python' -m http.server 5500 --directory scripts"
    )
}

$ready = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $health = Invoke-RestMethod `
            -Uri "http://127.0.0.1:8001/health" `
            -TimeoutSec 1
        if ($health.service -eq "AegisLocal") {
            $ready = $true
            break
        }
    } catch {
    }
    Start-Sleep -Seconds 1
}
if (-not $ready) {
    throw "AegisLocal API 8001 portunda hazir degil."
}

Start-Process "http://127.0.0.1:5500/letter-challenge.html"
Write-Host "AegisLocal harf challenge acildi."
Write-Host "API: http://127.0.0.1:8001"
Write-Host "UI : http://127.0.0.1:5500/letter-challenge.html"
