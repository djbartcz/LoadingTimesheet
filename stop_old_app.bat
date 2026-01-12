@echo off
REM Stop and Disable Old FastAPI/React App Service

echo ========================================
echo Stopping Old LoadingTimesheet Service
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

echo Stopping service if running...
net stop LoadingTimesheetBackend >nul 2>&1
if %errorLevel% equ 0 (
    echo Service stopped successfully.
) else (
    echo Service was already stopped or doesn't exist.
)

echo.
echo Disabling service...
sc config LoadingTimesheetBackend start= disabled >nul 2>&1
if %errorLevel% equ 0 (
    echo Service disabled successfully - it will not start automatically.
) else (
    echo Service may not exist or already disabled.
)

echo.
echo ========================================
echo Service stopped and disabled!
echo ========================================
echo.
echo To completely uninstall the service, run:
echo   backend\uninstall_service.bat
echo.
pause

