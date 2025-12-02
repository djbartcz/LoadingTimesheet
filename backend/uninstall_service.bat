@echo off
REM Uninstall Windows Service for LoadingTimesheet Backend

echo ========================================
echo LoadingTimesheet Service Uninstaller
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Get script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

echo Stopping service if running...
net stop LoadingTimesheetBackend >nul 2>&1

echo.
echo Uninstalling service...
REM Get pipenv Python executable path
for /f "tokens=*" %%i in ('pipenv --py') do set PIPENV_PYTHON=%%i

"%PIPENV_PYTHON%" windows_service.py remove
if %errorLevel% neq 0 (
    echo ERROR: Failed to uninstall service!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Service uninstalled successfully!
echo ========================================
echo.
pause

