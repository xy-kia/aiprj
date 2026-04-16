@echo off
chcp 936 > nul 2>&1
title Student Job Assistant AI Launcher
echo ========================================
echo     Student Job Assistant AI - Launcher
echo ========================================
echo [INFO] This script will start backend API service and frontend interface
echo [INFO] Supported AI models: OpenAI, Claude, DeepSeek, Kimi, Tongyi Qianwen
echo [INFO] If this window closes too quickly, please run in Command Prompt.
echo.

REM Get the script's directory
cd /d "%~dp0"
echo [INFO] Working directory: %CD%
echo [DEBUG] Script starting...

REM Check Python
echo [CHECK] Checking Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    echo Please install Python 3.8 or higher
    echo Download: https://www.python.org/downloads/
    echo.
    echo Installation tips:
    echo   1. Go to https://www.python.org/downloads/
    echo   2. Download Python 3.9 or higher
    echo   3. During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
echo [DONE] Python found
for /f "tokens=*" %%a in ('python --version 2^>^&1') do echo       %%a

REM Check Node.js
echo [CHECK] Checking Node.js...
node --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found
    echo Please install Node.js 18 or higher
    echo Download: https://nodejs.org/
    echo.
    echo Installation tips:
    echo   1. Go to https://nodejs.org/
    echo   2. Download LTS version ^(18+^)
    echo   3. Install with default settings
    echo.
    pause
    exit /b 1
)
echo [DONE] Node.js found
for /f "tokens=*" %%a in ('node --version') do echo       %%a

REM Check npm - try multiple methods
echo [CHECK] Checking npm...
set "NPM_CHECK_FAILED=1"

REM Method 1: Quick check if npm command exists
where npm >nul 2>&1
if not errorlevel 1 (
    REM Method 2: Try to get npm version with timeout simulation
    echo [INFO] npm found in PATH, checking version...
    set "NPM_VERSION_CHECK=0"

    REM Use a simple echo pipe to avoid hanging
    echo. | npm --version >nul 2>&1
    if not errorlevel 1 (
        set "NPM_CHECK_FAILED=0"
        for /f "tokens=*" %%a in ('npm --version 2^>^&1') do (
            echo [DONE] npm found - version: %%a
        )
    )
)

if "%NPM_CHECK_FAILED%"=="1" (
    echo [ERROR] npm check failed or npm not responding
    echo.
    echo This could be because:
    echo   1. Node.js is not installed
    echo   2. Node.js is installed but npm is not in PATH
    echo   3. npm command is taking too long to respond
    echo.
    echo Solutions:
    echo   1. Install Node.js 18+ from https://nodejs.org/
    echo   2. During installation, check "Add to PATH"
    echo   3. Restart your computer after installation
    echo   4. Or try running this script in Command Prompt
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

REM Check and create virtual environment (optional but recommended)
echo [CHECK] Checking Python environment...

REM Check core Python dependencies
echo [CHECK] Checking Python dependencies...
pip show fastapi > nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing core Python dependencies...
    pip install fastapi uvicorn sqlalchemy pydantic python-dotenv pymysql scikit-learn jieba openai anthropic requests numpy
    if errorlevel 1 (
        echo [ERROR] Failed to install core dependencies
        echo [SUGGESTION] Try running: pip install --upgrade pip
        pause
        exit /b 1
    )
    echo [DONE] Core dependencies installed
) else (
    echo [DONE] Core Python dependencies found
)

REM Check for additional dependencies from requirements.txt
echo [CHECK] Checking backend dependencies...
if exist "backend\requirements.txt" (
    pip install -r backend\requirements.txt > nul 2>&1
    if errorlevel 1 (
        echo [WARNING] Some backend dependencies failed to install, but continuing...
    ) else (
        echo [DONE] Backend dependencies checked
    )
) else (
    echo [WARNING] backend\requirements.txt not found, skipping
)

REM Check and install frontend dependencies
echo [CHECK] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies ^(this may take a few minutes^)...
    cd frontend
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
    cd ..
    echo [DONE] Frontend dependencies installed
) else (
    echo [DONE] Frontend dependencies found
)

REM Check launcher.py
echo [CHECK] Checking launcher script...
echo [CHECK] Checking launcher script...
if not exist "launcher.py" (
    echo [ERROR] launcher.py not found in current directory
    echo [SUGGESTION] Please ensure you have all project files
    pause
    exit /b 1
)
echo [DONE] Launcher script found

REM Check port 8000
echo [CHECK] Checking port 8000...
echo [DEBUG] Port check started

set PORT_IN_USE=0
set PORT_PID=

for /f "tokens=2,5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr /C:"LISTENING" /C:"监听"') do (
    set PORT_IN_USE=1
    set PORT_PID=%%b
)

if "%PORT_IN_USE%"=="1" (
    echo [WARNING] Port 8000 is in use
    echo.
    echo Process info:
    for /f "tokens=1" %%p in ('tasklist /fi "pid eq %PORT_PID%" /fo table /nh') do (
        echo   Process: %%p ^(PID: %PORT_PID%^)
    )
    echo.
    choice /C YN /N /M "Kill this process and continue? (Y=Yes, N=No) "

    if errorlevel 2 (
        echo.
        echo [INFO] You chose not to kill the process
        echo [SUGGESTION] You can:
        echo   1. Manually close the program using port 8000
        echo   2. Wait for the current process to end
        echo   3. Press Ctrl+C during startup to change port
        echo.
        pause
        exit /b 1
    ) else (
        echo [INFO] Killing process PID: %PORT_PID% ...
        taskkill /PID %PORT_PID% /F > nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Cannot kill process, admin rights may be needed
            echo [SUGGESTION] Run as administrator or manually close the program
            pause
            exit /b 1
        )
        echo [DONE] Process killed, port released
        timeout /t 2 /nobreak > nul
    )
) else (
    echo [DONE] Port 8000 is available
)

REM Build frontend
echo.
echo [BUILD] Building frontend...
if not exist "frontend" (
    echo [ERROR] frontend directory not found
    pause
    exit /b 1
)

cd frontend

REM Ensure node_modules exists
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies
        cd ..
        pause
        exit /b 1
    )
)

echo [INFO] Building production bundle...
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed
    cd ..
    pause
    exit /b 1
)
cd ..
echo [DONE] Frontend built successfully

echo.
echo ========================================
echo   Starting Backend + Frontend Services
echo ========================================
echo.
echo [INFO] Services will be available at:
echo        - Main App: http://localhost:8000
echo        - API Docs: http://localhost:8000/api/docs
echo.
echo [INFO] Features:
echo        - SQLite database ^(no MySQL needed^)
echo        - In-memory cache ^(no Redis needed^)
echo        - Sample job data included
echo        - AI features require API key configuration
echo.
echo [START] Starting integrated server...
echo.
echo Press Ctrl+C to stop the server
echo.

python launcher.py

if errorlevel 1 (
    echo.
    echo [ERROR] Startup failed
    echo [TROUBLESHOOTING] Please check:
    echo   1. Port 8000 is not in use by another program
    echo   2. All Python dependencies are installed
    echo   3. Error messages above
    echo.
    echo For more help, check the documentation or open an issue.
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Server stopped
pause
