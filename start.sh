#!/bin/bash

# 设置脚本在遇到错误时停止
set -e

# 获取脚本所在目录
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "     学生求职AI助手 - 启动器"
echo "========================================"
echo "[INFO] 此脚本将启动后端API服务和前端界面"
echo "[INFO] 支持的AI模型: OpenAI, Claude, DeepSeek, Kimi, 通义千问"
echo ""

# 检查Python
echo "[CHECK] 检查Python..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3未找到"
    echo "请安装Python 3.8或更高版本"
    echo ""
    echo "安装提示:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  macOS: brew install python"
    echo "  或访问: https://www.python.org/downloads/"
    echo ""
    exit 1
fi
echo "[DONE] Python已找到"
python3 --version

# 检查Node.js
echo "[CHECK] 检查Node.js..."
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js未找到"
    echo "请安装Node.js 18或更高版本"
    echo ""
    echo "安装提示:"
    echo "  访问: https://nodejs.org/"
    echo "  下载LTS版本(18+)"
    echo ""
    exit 1
fi
echo "[DONE] Node.js已找到"
node --version

# 检查npm
echo "[CHECK] 检查npm..."
if ! command -v npm &> /dev/null; then
    echo "[ERROR] npm未找到"
    echo "请重新安装Node.js"
    exit 1
fi
echo "[DONE] npm已找到"

# 检查Python依赖
echo "[CHECK] 检查Python依赖..."
python3 -c "import fastapi, uvicorn, sqlalchemy, pydantic, sklearn, jieba" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[INFO] 安装核心Python依赖..."
    pip3 install fastapi uvicorn sqlalchemy pydantic python-dotenv pymysql scikit-learn jieba openai anthropic requests numpy
    if [ $? -ne 0 ]; then
        echo "[ERROR] 依赖安装失败"
        echo "[SUGGESTION] 尝试运行: pip3 install --upgrade pip"
        exit 1
    fi
    echo "[DONE] 核心依赖已安装"
else
    echo "[DONE] Python依赖已找到"
fi

# 检查并安装后端依赖
if [ -f "backend/requirements.txt" ]; then
    echo "[CHECK] 检查后端的依赖..."
    pip3 install -r backend/requirements.txt >/dev/null 2>&1 || true
    echo "[DONE] 后端依赖已检查"
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "[INFO] 安装前端依赖(这可能需要几分钟)..."
    cd frontend
    npm install
    if [ $? -ne 0 ]; then
        echo "[ERROR] 前端依赖安装失败"
        cd ..
        exit 1
    fi
    cd ..
    echo "[DONE] 前端依赖已安装"
else
    echo "[DONE] 前端依赖已找到"
fi

# 确保运行时目录存在
echo "[CHECK] 检查运行时数据目录..."
mkdir -p data/db data/uploads data/knowledge data/logs
echo "[DONE] 运行时数据目录已就绪"

# 若 .env 不存在，从模板生成
echo "[CHECK] 检查环境变量配置..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[INFO] 正在从 .env.example 生成 .env..."
        cp ".env.example" ".env"
        echo "[DONE] .env 已创建"
    else
        echo "[WARNING] .env.example 未找到，跳过 .env 生成"
    fi
else
    echo "[DONE] .env 已存在"
fi

# 检查launcher.py
if [ ! -f "launcher.py" ]; then
    echo "[ERROR] launcher.py未找到"
    exit 1
fi
echo "[DONE] 启动器脚本已找到"

# 检查端口占用
echo "[CHECK] 检查端口8000..."
if command -v lsof &> /dev/null; then
    PORT_PID=$(lsof -ti:8000 2>/dev/null || true)
elif command -v netstat &> /dev/null; then
    PORT_PID=$(netstat -tlnp 2>/dev/null | grep :8000 | awk '{print $7}' | cut -d'/' -f1 || true)
else
    PORT_PID=""
fi

if [ -n "$PORT_PID" ]; then
    echo "[WARNING] 端口8000已被占用"
    echo "进程PID: $PORT_PID"
    read -p "是否终止该进程并继续? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "[INFO] 正在终止进程 $PORT_PID..."
        kill -9 $PORT_PID 2>/dev/null || {
            echo "[ERROR] 无法终止进程，可能需要管理员权限"
            exit 1
        }
        echo "[DONE] 进程已终止，端口已释放"
        sleep 2
    else
        echo "[INFO] 用户选择不终止进程"
        echo "[SUGGESTION] 你可以:"
        echo "  1. 手动关闭占用端口8000的程序"
        echo "  2. 等待当前进程结束"
        echo "  3. 在启动时按Ctrl+C更改端口"
        exit 1
    fi
else
    echo "[DONE] 端口8000可用"
fi

# 构建前端
echo ""
echo "[BUILD] 构建前端..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "[INFO] 安装前端依赖..."
    npm install
    if [ $? -ne 0 ]; then
        echo "[ERROR] 前端依赖安装失败"
        cd ..
        exit 1
    fi
fi

echo "[INFO] 构建生产环境包..."
npm run build
if [ $? -ne 0 ]; then
    echo "[ERROR] 前端构建失败"
    cd ..
    exit 1
fi
cd ..
echo "[DONE] 前端构建成功"

echo ""
echo "========================================"
echo "   启动后端 + 前端服务"
echo "========================================"
echo ""
echo "[INFO] 服务将在以下地址可用:"
echo "       - 主应用: http://localhost:8000"
echo "       - API文档: http://localhost:8000/api/docs"
echo ""
echo "[INFO] 功能特性:"
echo "       - SQLite数据库 (无需MySQL)"
echo "       - 内存缓存 (无需Redis)"
echo "       - 包含示例岗位数据"
echo "       - AI功能需要配置API密钥"
echo ""
echo "[START] 正在启动一体化服务器..."
echo ""
echo "按Ctrl+C停止服务器"
echo ""

# 给launcher.py添加执行权限
chmod +x launcher.py 2>/dev/null || true

# 运行启动器
python3 launcher.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] 启动失败"
    echo "[TROUBLESHOOTING] 请检查:"
    echo "  1. 端口8000是否被其他程序占用"
    echo "  2. Python依赖是否完整安装"
    echo "  3. 上面的错误信息"
    echo ""
    echo "如需更多帮助，请查看文档或提交issue"
    exit 1
fi

echo ""
echo "[INFO] 服务器已停止"
