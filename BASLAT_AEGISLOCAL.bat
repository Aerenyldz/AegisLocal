@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launchers\start-aegis.ps1"
if errorlevel 1 (
  echo.
  echo AegisLocal baslatilamadi. Python kurulumunu ve hata mesajini kontrol edin.
  pause
)
endlocal
