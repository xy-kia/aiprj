@echo off
echo === Debug npm check ===
echo.

echo 1. Checking if npm exists in PATH...
where npm
echo Errorlevel after 'where npm': %errorlevel%

echo.
echo 2. Checking npm version...
npm -v
echo Errorlevel after 'npm -v': %errorlevel%

echo.
echo 3. Direct test without redirection...
where npm > test_where.txt 2>&1
echo where npm output saved to test_where.txt
type test_where.txt
del test_where.txt

echo.
echo 4. Test with error level check...
where npm > nul 2>&1
if errorlevel 1 (
    echo ERROR: where npm failed
) else (
    echo SUCCESS: where npm passed
)

npm -v > nul 2>&1
if errorlevel 1 (
    echo ERROR: npm -v failed
) else (
    echo SUCCESS: npm -v passed
)

echo.
pause