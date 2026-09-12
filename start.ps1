<#
.SYNOPSIS
    Starts the Lockley backend (Flask, port 5000) and frontend (Vite, port 5174).

.DESCRIPTION
    Run this from the repo root instead of starting each server by hand:

        .\start.ps1

    Both servers share this console, so their logs interleave here and Ctrl+C
    stops both. The backend Python is resolved automatically, so there is no
    need to activate a venv first.

.PARAMETER BackendOnly
    Start only the Flask API.

.PARAMETER FrontendOnly
    Start only the Vite dev server.
#>
[CmdletBinding()]
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = 'Stop'

$Root        = $PSScriptRoot
$BackendDir  = Join-Path $Root 'Backend'
$FrontendDir = Join-Path $Root 'Frontend'
$BackendPort  = 5000
$FrontendPort = 5174

$runBackend  = -not $FrontendOnly
$runFrontend = -not $BackendOnly

function Write-Step($message) { Write-Host "==> $message" -ForegroundColor Cyan }
function Write-Warn($message) { Write-Host "!!  $message" -ForegroundColor Yellow }
function Write-Fail($message) { Write-Host "!!  $message" -ForegroundColor Red }

# Kill the whole process tree: `npm run dev` spawns node as a child, and Flask
# spawns a reloader child when FLASK_DEBUG=1. Stopping only the parent orphans
# them and leaves the port held.
function Stop-Tree($process) {
    if ($null -eq $process) { return }
    try { if ($process.HasExited) { return } } catch { return }
    try {
        Start-Process -FilePath 'taskkill.exe' `
            -ArgumentList '/PID', $process.Id, '/T', '/F' `
            -NoNewWindow -Wait -ErrorAction Stop | Out-Null
    } catch {
        # Already gone, or taskkill lost the race with Ctrl+C. Nothing to do.
    }
}

function Test-PortBusy($port) {
    try {
        $null = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# The venv holds flask/psycopg2/jwt; the system Python does not. Prefer
# Backend\venv, which is the one that is actually provisioned.
function Resolve-BackendPython {
    # Merging a native command's stderr raises NativeCommandError under
    # ErrorActionPreference=Stop, which would abort the whole script on a
    # half-built venv. Only the exit code matters here.
    $ErrorActionPreference = 'Continue'

    $candidates = @(
        (Join-Path $BackendDir 'venv\Scripts\python.exe'),
        (Join-Path $BackendDir '.venv\Scripts\python.exe'),
        (Join-Path $Root '.venv\Scripts\python.exe')
    )
    foreach ($candidate in $candidates) {
        if (-not (Test-Path $candidate)) { continue }
        # A venv can exist but be empty, so confirm the app's imports resolve.
        & $candidate -c 'import flask, psycopg2, jwt' 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { return $candidate }
        Write-Warn "Skipping $candidate (dependencies missing)."
    }
    return $null
}

$backendProcess  = $null
$frontendProcess = $null

try {
    # ---- preflight ---------------------------------------------------------
    if ($runBackend -and (Test-PortBusy $BackendPort)) {
        Write-Fail "Port $BackendPort is already in use - the backend may already be running."
        Write-Host "    Find it with:  Get-NetTCPConnection -LocalPort $BackendPort -State Listen"
        exit 1
    }
    if ($runFrontend -and (Test-PortBusy $FrontendPort)) {
        Write-Fail "Port $FrontendPort is already in use - the frontend may already be running."
        Write-Host "    Find it with:  Get-NetTCPConnection -LocalPort $FrontendPort -State Listen"
        exit 1
    }

    $python = $null
    if ($runBackend) {
        Write-Step 'Locating backend Python...'
        $python = Resolve-BackendPython
        if ($null -eq $python) {
            Write-Fail 'No usable backend virtualenv found.'
            Write-Host '    Create one and install dependencies:'
            Write-Host '      python -m venv Backend\venv'
            Write-Host '      Backend\venv\Scripts\python.exe -m pip install -r Backend\requirements.txt'
            exit 1
        }
        Write-Host "    $python"
    }

    $npm = $null
    if ($runFrontend) {
        $npmCommand = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
        if ($null -eq $npmCommand) { $npmCommand = Get-Command 'npm' -ErrorAction SilentlyContinue }
        if ($null -eq $npmCommand) {
            Write-Fail 'npm was not found on PATH. Install Node.js, then re-run.'
            exit 1
        }
        $npm = $npmCommand.Source

        if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
            Write-Step 'Installing frontend dependencies (first run)...'
            Push-Location $FrontendDir
            try { & $npm install } finally { Pop-Location }
            if ($LASTEXITCODE -ne 0) {
                Write-Fail 'npm install failed.'
                exit 1
            }
        }
    }

    # ---- launch ------------------------------------------------------------
    if ($runBackend) {
        Write-Step "Starting backend on http://localhost:$BackendPort ..."
        $backendProcess = Start-Process -FilePath $python -ArgumentList 'api.py' `
            -WorkingDirectory $BackendDir -NoNewWindow -PassThru
        # Touching Handle makes .NET cache it, so ExitCode is still readable
        # after the process dies. Without this it reads back empty.
        $null = $backendProcess.Handle
    }

    if ($runFrontend) {
        Write-Step "Starting frontend on http://localhost:$FrontendPort ..."
        $frontendProcess = Start-Process -FilePath $npm -ArgumentList 'run', 'dev' `
            -WorkingDirectory $FrontendDir -NoNewWindow -PassThru
        $null = $frontendProcess.Handle
    }

    Write-Host ''
    if ($runFrontend) {
        Write-Host "    Lockley is starting at http://localhost:$FrontendPort" -ForegroundColor Green
    } else {
        Write-Host "    Backend API at http://localhost:$BackendPort" -ForegroundColor Green
    }
    Write-Host '    Press Ctrl+C to stop.' -ForegroundColor DarkGray
    Write-Host ''

    # Hold the console open and surface whichever server dies first, so a
    # crashed backend does not look like a frontend that simply went quiet.
    while ($true) {
        if ($backendProcess -and $backendProcess.HasExited) {
            Write-Warn "Backend exited (code $($backendProcess.ExitCode)). Shutting down."
            break
        }
        if ($frontendProcess -and $frontendProcess.HasExited) {
            Write-Warn "Frontend exited (code $($frontendProcess.ExitCode)). Shutting down."
            break
        }
        Start-Sleep -Milliseconds 400
    }
}
finally {
    # Only announce shutdown if something was actually launched; preflight
    # failures exit through here too.
    if ($backendProcess -or $frontendProcess) {
        Write-Host ''
        Write-Step 'Stopping servers...'
        Stop-Tree $frontendProcess
        Stop-Tree $backendProcess
    }
}
