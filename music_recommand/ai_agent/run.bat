@echo off
echo ========================================
echo   AI音乐推荐智能体 - 启动脚本
echo ========================================
echo.

REM 检查.env文件是否存在
if not exist .env (
    echo [警告] .env 文件不存在！
    echo 请复制 env_example.txt 为 .env 并填入您的 DeepSeek API 密钥
    echo.
    pause
    exit /b 1
)

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Python 未安装或未添加到PATH
    echo 请先安装 Python 3.7 或更高版本
    pause
    exit /b 1
)

REM 检查依赖是否安装
echo [信息] 检查依赖...
pip show Flask >nul 2>&1
if errorlevel 1 (
    echo [信息] 安装依赖...
    pip install -r requirements.txt
)

echo.
echo [信息] 启动Flask应用...
echo [信息] 服务将在 http://127.0.0.1:5000 启动
echo [信息] 按 Ctrl+C 停止服务
echo.

python app.py

pause

