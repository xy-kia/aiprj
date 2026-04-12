@echo off
echo Testing npm check only...
echo.
echo [CHECK] Checking npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm check failed
    pause
    exit /b 1
)
echo [DONE] npm check passed
echo.
pause