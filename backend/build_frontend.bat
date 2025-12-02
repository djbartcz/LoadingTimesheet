@echo off
REM Build React Frontend for Production
REM This script builds the React app so it can be served by FastAPI

echo ========================================
echo Building React Frontend
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set FRONTEND_DIR=%SCRIPT_DIR%..\frontend

if not exist "%FRONTEND_DIR%" (
    echo ERROR: Frontend directory not found: %FRONTEND_DIR%
    pause
    exit /b 1
)

cd /d "%FRONTEND_DIR%"

if not exist "package.json" (
    echo ERROR: package.json not found in frontend directory!
    pause
    exit /b 1
)

REM Check if npm is available
where npm >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo ERROR: npm is not installed or not in PATH!
    echo.
    echo Please install Node.js from: https://nodejs.org/
    echo After installation, restart Command Prompt and try again.
    echo.
    echo Alternatively, you can build the frontend manually:
    echo   1. Open a new terminal
    echo   2. cd to frontend directory
    echo   3. Run: npm install
    echo   4. Run: npm run build
    echo.
    pause
    exit /b 1
)

echo Installing frontend dependencies...
REM Use --legacy-peer-deps to handle dependency conflicts
call npm install --legacy-peer-deps
if %errorLevel% neq 0 (
    echo ERROR: Failed to install frontend dependencies!
    pause
    exit /b 1
)

echo.
echo Building React app for production...
REM Set REACT_APP_BACKEND_URL to empty or relative path since served from same server
set REACT_APP_BACKEND_URL=
call npm run build
if %errorLevel% neq 0 (
    echo ERROR: Failed to build React app!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Frontend built successfully!
echo ========================================
echo Build output: %FRONTEND_DIR%\build
echo.
echo The React app will be served by FastAPI at http://localhost:8000
echo.
pause

