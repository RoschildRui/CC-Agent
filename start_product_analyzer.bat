@echo off
chcp 65001 >nul
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo    PolyScore - AI 驱动的产品市场分析系统
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
cd /d %~dp0

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env 配置文件不存在
    if exist "env_example.txt" (
        echo [INFO] 从模板创建 .env 文件...
        copy env_example.txt .env >nul
        echo [SUCCESS] 已创建 .env 文件
        echo [重要] 请编辑 .env 文件填入实际的 API 密钥后重新运行
        echo.
        notepad .env
        pause
        exit /b 1
    )
) else (
    echo [INFO] 已找到 .env 配置文件
)

echo.
echo [INFO] 正在启动应用...
echo [INFO] 应用地址: http://localhost:5001
echo.
python app.py
pause