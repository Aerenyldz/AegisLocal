param(
    [double]$DurationMinutes = 15,
    [string]$Output = "datasets\raw\human-global.jsonl"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root
python scripts\tools\collect_global_mouse.py `
    --duration-minutes $DurationMinutes `
    --output $Output
