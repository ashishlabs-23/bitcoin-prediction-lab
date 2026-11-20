param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8765,
    [ValidateRange(5, 300)]
    [int]$StartupTimeoutSeconds = 75,
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $RepoRoot ".venv_win\Scripts\python.exe"
$Url = "http://127.0.0.1:$Port/"
$ServerProcess = $null
$OldDataMode = $env:DATA_MODE
$OldBtcDataMode = $env:BTC_DATA_MODE
$OldFixtureFlag = $env:BTC_LOCAL_FIXTURE_FEED
$OldHost = $env:BTCOGNITIVE_HOST
$OldPort = $env:PORT
$StartupFailure = $false
$StopRequested = $false
$CancelHandler = $null

function Test-LoopbackPortAvailable([int]$CandidatePort) {
    $Listener = [Net.Sockets.TcpListener]::new(
        [Net.IPAddress]::Parse("127.0.0.1"),
        $CandidatePort
    )
    try {
        $Listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        $Listener.Stop()
    }
}

function Write-ServerLogPaths {
    Write-Host "Server stdout: $StdoutLog" -ForegroundColor Gray
    Write-Host "Server stderr: $StderrLog" -ForegroundColor Gray
}

try {
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        throw "Windows virtual-environment Python not found: $PythonExe. Create or restore .venv_win first."
    }

    Push-Location $RepoRoot
    try {
        & $PythonExe -c "import fastapi, uvicorn"
        if ($LASTEXITCODE -ne 0) {
            throw "FastAPI/Uvicorn dependencies are unavailable in .venv_win. Restore the project's Windows environment before running this launcher."
        }
    } finally {
        Pop-Location
    }

    if (-not (Test-LoopbackPortAvailable $Port)) {
        throw "Port $Port on 127.0.0.1 is already occupied or unavailable. No existing process was stopped or reused. Choose another free port with -Port."
    }

    $LogDir = Join-Path $RepoRoot "logs\local-run"
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    $RunStamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $StdoutLog = Join-Path $LogDir "local-$RunStamp-stdout.log"
    $StderrLog = Join-Path $LogDir "local-$RunStamp-stderr.log"

    $env:DATA_MODE = "fixture"
    $env:BTC_DATA_MODE = "fixture"
    $env:BTC_LOCAL_FIXTURE_FEED = "1"
    $env:BTCOGNITIVE_HOST = "127.0.0.1"
    $env:PORT = [string]$Port

    $Arguments = @(
        "-m", "uvicorn", "api.server:app",
        "--host", "127.0.0.1",
        "--port", [string]$Port,
        "--workers", "1",
        "--access-log"
    )
    Write-Host "Starting BTCognitive in isolated local fixture mode." -ForegroundColor Cyan
    Write-Host "Data lane: DATA_MODE=fixture; BTC_LOCAL_FIXTURE_FEED=1" -ForegroundColor Yellow
    Write-Host "Bind: 127.0.0.1:$Port (one worker; no reload)" -ForegroundColor Gray
    Write-Host "URL: $Url" -ForegroundColor Green
    Write-Host "Waiting up to $StartupTimeoutSeconds seconds for FastAPI and its static frontend..."

    $ServerProcess = Start-Process `
        -FilePath $PythonExe `
        -ArgumentList $Arguments `
        -WorkingDirectory $RepoRoot `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -PassThru

    $Deadline = (Get-Date).AddSeconds($StartupTimeoutSeconds)
    $Ready = $false
    while ((Get-Date) -lt $Deadline) {
        if ($ServerProcess.HasExited) {
            throw "FastAPI exited during startup (exit code $($ServerProcess.ExitCode)). See server logs below."
        }
        try {
            $Page = Invoke-WebRequest -Uri $Url -TimeoutSec 3 -UseBasicParsing
            $Health = Invoke-RestMethod -Uri "$($Url)health" -TimeoutSec 3
            $SystemStatus = $Health.system_status
            $DataMode = if ($null -ne $Health.data_mode) { $Health.data_mode } else { $SystemStatus.data_mode }
            $FixtureEnabled = if ($null -ne $Health.local_fixture_feed_enabled) {
                $Health.local_fixture_feed_enabled
            } else {
                $SystemStatus.local_fixture_feed_enabled
            }
            $PageHasRoot = $Page.Content -match 'id="root"'
            if (($Page.StatusCode -eq 200) -and $PageHasRoot -and ($DataMode -eq "fixture") -and ($FixtureEnabled -eq $true)) {
                $Ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 750
        }
        Start-Sleep -Milliseconds 250
    }

    if (-not $Ready) {
        throw "Startup timed out or the fixture-only health/static-page contract was not ready. See server logs below."
    }

    Write-Host "Ready: $Url" -ForegroundColor Green
    Write-Host "Fixture mode confirmed; market data providers and protected datasets are not enabled by this launcher." -ForegroundColor Yellow
    Write-ServerLogPaths
    if ($OpenBrowser) {
        Start-Process $Url | Out-Null
    }
    Write-Host "Press Ctrl+C to stop the local server." -ForegroundColor Cyan

    $CancelHandler = [ConsoleCancelEventHandler]{
        param($Sender, $EventArgs)
        $EventArgs.Cancel = $true
        $script:StopRequested = $true
    }
    [Console]::add_CancelKeyPress($CancelHandler)
    while (-not $ServerProcess.HasExited -and -not $StopRequested) {
        Start-Sleep -Seconds 1
        $ServerProcess.Refresh()
    }
    if ($StopRequested) {
        Write-Host "Ctrl+C received; stopping the local server..." -ForegroundColor Yellow
    } elseif ($ServerProcess.HasExited -and $ServerProcess.ExitCode -ne 0) {
        throw "FastAPI stopped with exit code $($ServerProcess.ExitCode). See server logs below."
    }
} catch {
    $StartupFailure = $true
    Write-Host "[LOCAL STARTUP ERROR] $($_.Exception.Message)" -ForegroundColor Red
    if ($StdoutLog -or $StderrLog) {
        Write-ServerLogPaths
    }
} finally {
    if ($null -ne $CancelHandler) {
        [Console]::remove_CancelKeyPress($CancelHandler)
    }
    if ($null -ne $ServerProcess) {
        $ServerProcess.Refresh()
        if (-not $ServerProcess.HasExited) {
            Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
        }
    }
    if ($null -eq $OldDataMode) { Remove-Item Env:\DATA_MODE -ErrorAction SilentlyContinue } else { $env:DATA_MODE = $OldDataMode }
    if ($null -eq $OldBtcDataMode) { Remove-Item Env:\BTC_DATA_MODE -ErrorAction SilentlyContinue } else { $env:BTC_DATA_MODE = $OldBtcDataMode }
    if ($null -eq $OldFixtureFlag) { Remove-Item Env:\BTC_LOCAL_FIXTURE_FEED -ErrorAction SilentlyContinue } else { $env:BTC_LOCAL_FIXTURE_FEED = $OldFixtureFlag }
    if ($null -eq $OldHost) { Remove-Item Env:\BTCOGNITIVE_HOST -ErrorAction SilentlyContinue } else { $env:BTCOGNITIVE_HOST = $OldHost }
    if ($null -eq $OldPort) { Remove-Item Env:\PORT -ErrorAction SilentlyContinue } else { $env:PORT = $OldPort }
    if ($ServerProcess -and $ServerProcess.HasExited -and $ServerProcess.ExitCode -eq 0) {
        Write-Host "Local server stopped." -ForegroundColor Gray
    }
}
if ($StartupFailure) {
    exit 1
}
