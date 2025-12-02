@echo off
REM Install Windows Service for LoadingTimesheet Backend
REM This script installs pipenv, dependencies, and the Windows service

echo ========================================
echo LoadingTimesheet Service Installer
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

echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python 3.12+ and add it to PATH
    pause
    exit /b 1
)
python --version

echo.
echo [2/6] Installing pipenv...
python -m pip install --upgrade pip
python -m pip install pipenv
if %errorLevel% neq 0 (
    echo ERROR: Failed to install pipenv!
    pause
    exit /b 1
)

echo.
echo [3/6] Installing dependencies with pipenv...
REM Remove existing virtual environment if it exists (to ensure fresh install)
if exist ".venv" (
    echo Removing existing virtual environment...
    rmdir /s /q .venv
)
REM Use current Python version explicitly
pipenv install --python python
if %errorLevel% neq 0 (
    echo ERROR: Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo [4/6] Building React frontend...
cd /d "%SCRIPT_DIR%\..\frontend"
if exist "package.json" (
    REM Check if npm is available
    where npm >nul 2>&1
    if %errorLevel% neq 0 (
        echo WARNING: npm is not installed or not in PATH!
        echo Skipping frontend build.
        echo.
        echo To build frontend later:
        echo   1. Install Node.js from https://nodejs.org/
        echo   2. Run: backend\build_frontend.bat
        echo   3. Or manually: cd frontend ^&^& npm install ^&^& npm run build
    ) else (
        echo Installing frontend dependencies...
        REM Use --legacy-peer-deps to handle dependency conflicts
        call npm install --legacy-peer-deps
        if %errorLevel% neq 0 (
            echo WARNING: Failed to install frontend dependencies!
            echo You may need to build frontend manually later.
        ) else (
            echo Building React app...
            REM Set empty BACKEND_URL since served from same server
            set REACT_APP_BACKEND_URL=
            call npm run build
            if %errorLevel% neq 0 (
                echo WARNING: Failed to build React app!
                echo Frontend will not be served. Build manually with: build_frontend.bat
            ) else (
                echo React app built successfully!
            )
        )
    )
) else (
    echo WARNING: Frontend directory not found. Skipping frontend build.
)
cd /d "%SCRIPT_DIR%"

echo.
echo [5/5] Installing pywin32 (required for Windows service)...
pipenv install pywin32
if %errorLevel% neq 0 (
    echo ERROR: Failed to install pywin32!
    pause
    exit /b 1
)

echo.
echo [6/6] Installing Windows service...
REM Get pipenv Python executable path
for /f "tokens=*" %%i in ('pipenv --py') do set PIPENV_PYTHON=%%i

REM Check if .env file exists
if not exist ".env" (
    echo WARNING: .env file not found!
    echo Creating template .env file...
    (
        echo # PostgreSQL Database Configuration
        echo DB_NAME=timesheet_db
        echo DB_USER=postgres
        echo DB_PASSWORD=postgres
        echo DB_HOST=localhost
        echo DB_PORT=5432
        echo.
        echo # Excel File Configuration
        echo EXCEL_FILE_PATH=C:\path\to\your\TimesheetData.xlsx
        echo.
        echo # CORS Configuration
        echo CORS_ORIGINS=http://localhost:3000
    ) > .env
    echo.
    echo Please edit backend\.env file with your actual configuration before starting the service!
    echo.
    pause
)

REM Install pywin32 service hooks (optional - skipping if not available)
echo Installing pywin32 service hooks...
"%PIPENV_PYTHON%" -c "import pywin32_postinstall; pywin32_postinstall.install()" 2>nul
if %errorLevel% neq 0 (
    echo Note: pywin32_postinstall skipped - service should still work
)

REM Install the service
echo Installing Windows service...
"%PIPENV_PYTHON%" windows_service.py install
if %errorLevel% neq 0 (
    echo ERROR: Failed to install service!
    echo.
    echo Make sure:
    echo 1. You are running as Administrator
    echo 2. .env file is configured correctly
    echo 3. MongoDB is accessible (if using local MongoDB)
    pause
    exit /b 1
)

echo.
echo ========================================
echo Service installed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Make sure backend\.env file is configured
echo 2. Start the service: net start LoadingTimesheetBackend
echo 3. Check status: sc query LoadingTimesheetBackend
echo.
echo To uninstall: uninstall_service.bat
echo.
pause

