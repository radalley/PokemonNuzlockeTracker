@echo off
REM Double-clickable wrapper for start.ps1. Bypasses the PowerShell execution
REM policy for this one run only; nothing is changed machine-wide.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
REM A double-clicked window closes the moment the script exits, which hid
REM startup errors such as "port already in use". Keep it open on failure.
if errorlevel 1 (
    echo.
    echo Lockley did not start. Read the message above, then press any key to close.
    pause >nul
)
