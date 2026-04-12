@echo off
echo Testing full start.bat...
echo.
echo Running start.bat in a new window...
echo If the window closes immediately, there's an error.
echo.
echo Press any key to test...
pause >nul

start "Test Start.bat" cmd /k "cd /d "%~dp0" && start.bat"

echo.
echo Test launched. Check the new window for errors.
echo Press any key to exit...
pause >nul