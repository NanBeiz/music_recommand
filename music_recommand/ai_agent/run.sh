#!/bin/bash

echo "========================================"
echo "  AI音乐推荐智能体 - 启动脚本"
echo "========================================"
echo ""

# 检查.env文件是否存在
if [ ! -f .env ]; then
    echo "[警告] .env 文件不存在！"
    echo "请复制 env_example.txt 为 .env 并填入您的 DeepSeek API 密钥"
    echo ""
    exit 1
fi

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] Python 未安装"
    echo "请先安装 Python 3.7 或更高版本"
    exit 1
fi

# 检查依赖是否安装
echo "[信息] 检查依赖..."
if ! python3 -c "import flask" &> /dev/null; then
    echo "[信息] 安装依赖..."
    pip3 install -r requirements.txt
fi

echo ""
echo "[信息] 启动Flask应用..."
echo "[信息] 服务将在 http://127.0.0.1:5000 启动"
echo "[信息] 按 Ctrl+C 停止服务"
echo ""

python3 app.py

