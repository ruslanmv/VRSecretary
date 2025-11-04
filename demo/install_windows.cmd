@echo off
REM demo/install_windows.cmd
REM Simple wrapper to run the PowerShell installer for VRSecretary demo.

set SCRIPT_DIR=%~dp0
set PS_SCRIPT=%SCRIPT_DIR%install_windows.ps1

if not exist "%PS_SCRIPT%" (
    echo Could not find %PS_SCRIPT%
    exit /b 1
)

echo.
echo ===============================================
echo  VRSecretary Demo - Windows Setup (CMD wrapper)
echo ===============================================
echo.

REM Use PowerShell to run the script with relaxed policy for this session only
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%"
