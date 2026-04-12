@echo off
chcp 65001 > nul 2>&1
echo.
echo ========================================
echo     学生求职AI助手 - 简化启动器
echo ========================================
echo [INFO] 此脚本将直接启动后端服务
echo [INFO] 跳过依赖检查和前端构建
echo.

REM 切换到脚本所在目录
cd /d "%~dp0"
echo [INFO] 工作目录: %CD%

REM 检查Python
echo [CHECK] 检查Python...
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python未找到
    echo 请安装Python 3.8或更高版本
    echo 下载: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM 检查必要文件
if not exist "launcher.py" (
    echo [ERROR] launcher.py未找到
    pause
    exit /b 1
)

if not exist "memory_cache.py" (
    echo [ERROR] memory_cache.py未找到
    pause
    exit /b 1
)

REM 检查端口8000
echo [CHECK] 检查端口8000...
netstat -ano | findstr :8000 > nul
if errorlevel 0 (
    echo [WARNING] 端口8000已被占用
    echo 请关闭占用端口的程序后重试
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  启动服务
echo ========================================
echo [INFO] 服务地址: http://localhost:8000
echo [INFO] API文档: http://localhost:8000/api/docs
echo [INFO] 按 Ctrl+C 停止服务
echo.

REM 直接启动服务器
python launcher.py

if errorlevel 1 (
    echo.
    echo [ERROR] 启动失败
    echo 请检查上面的错误信息
    pause
    exit /b 1
)

echo.
echo [INFO] 服务已停止
pause