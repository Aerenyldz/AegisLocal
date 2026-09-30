# Start AegisLocal API on http://127.0.0.1:8000
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backend = Join-Path $root "backend"
Set-Location $backend

$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv..."
    python -m venv .venv
    & $venvPython -m pip install -r requirements.txt
}

Write-Host "AegisLocal API -> http://127.0.0.1:8000"
Write-Host "Swagger       -> http://127.0.0.1:8000/docs"
Write-Host "Demo UI       -> http://127.0.0.1:5500/demo.html (BASLAT_AEGISLOCAL.bat ile acilir)"
Write-Host ""
& $venvPython -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
