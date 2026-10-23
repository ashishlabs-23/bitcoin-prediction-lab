# BTCognitive — Safe Standalone Prospective Evidence Worker Runner
# ====================================================================
# Runs one complete idempotent cycle of prospective evidence collection:
# 1. Syncs newly closed BTC/USD hourly spot candles from Coinbase.
# 2. Resolves any matured forward forecasts whose horizon has elapsed.
# 3. Issues matched prospective forecasts strictly at the latest closed cutoff.
# 4. Updates structured status telemetry in data/prospective_worker_status.json.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\run_prospective_worker.ps1 [-SyncLive] [-Daemon] [-IntervalSeconds 3600]

param (
    [switch]$SyncLive = $true,
    [switch]$Daemon = $false,
    [int]$IntervalSeconds = 3600
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $RepoRoot ".venv_win\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment Python not found at: $PythonExe"
    exit 1
}

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "BTCognitive Prospective Evidence Worker" -ForegroundColor Cyan
Write-Host "Repo Root : $RepoRoot" -ForegroundColor Gray
Write-Host "Python    : $PythonExe" -ForegroundColor Gray
Write-Host "Sync Live : $SyncLive" -ForegroundColor Gray
Write-Host "Daemon    : $Daemon" -ForegroundColor Gray
Write-Host "====================================================================" -ForegroundColor Cyan

$CmdArgs = @("-m", "engine.prospective_worker")
if ($SyncLive) {
    $CmdArgs += "--sync-live"
}

if ($Daemon) {
    $CmdArgs += @("--daemon", "--interval-seconds", $IntervalSeconds)
    Write-Host "Starting continuous daemon loop (interval: $IntervalSeconds s)..." -ForegroundColor Yellow
} else {
    $CmdArgs += "--once"
    Write-Host "Executing single prospective collection cycle..." -ForegroundColor Green
}

Set-Location $RepoRoot
& $PythonExe @CmdArgs
$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0) {
    Write-Host "[SUCCESS] Prospective evidence cycle completed successfully (Exit 0)." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Prospective worker failed with exit code $ExitCode." -ForegroundColor Red
}

exit $ExitCode
