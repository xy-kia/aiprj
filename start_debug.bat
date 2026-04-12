@echo off
chcp 65001 > nul 2>&1
echo ========================================
echo      学生求职AI助手 - 调试启动器
echo ========================================
echo [INFO] 如果窗口关闭太快，请使用此调试版本
echo [INFO] 按 Ctrl+C 停止服务器
echo.

REM 运行原始启动脚本
call start.bat

REM 如果 start.bat 返回错误代码（非零），则暂停
if errorlevel 1 (
    echo.
    echo [DEBUG] start.bat 退出代码: %errorlevel%
    echo [DEBUG] 请查看上面的错误信息
    pause
)

REM 如果服务器正常停止（Ctrl+C），也暂停一下
echo.
echo [DEBUG] 服务器已停止，窗口即将关闭...
timeout /t 5