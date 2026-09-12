@echo off
REM Double-clickable wrapper for start.ps1. Bypasses the PowerShell execution
REM policy for this one run only; nothing is changed machine-wide.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
