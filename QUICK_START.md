# 快速启动指南

## Windows 用户

只需双击 `start.bat` 文件即可启动所有服务。

## macOS/Linux 用户

在终端中运行：
```bash
chmod +x start.sh
./start.sh
```

## 系统要求

- Python 3.8+
- Node.js 18+

## 首次启动

脚本会自动：
1. 检查 Python 和 Node.js 是否安装
2. 安装 Python 依赖（fastapi, uvicorn, sqlalchemy 等）
3. 安装前端依赖（npm install）
4. 构建前端（npm run build）
5. 启动一体化服务器

## 访问应用

启动后，访问 http://localhost:8000

## 特性

- ✅ **无需 MySQL** - 使用 SQLite 数据库
- ✅ **无需 Redis** - 使用内存缓存
- ✅ **无需 BERT** - 使用 TF-IDF 计算相似度
- ✅ **示例数据** - 包含示例岗位和技能数据
- ⚠️ **AI 功能** - 需要配置 API 密钥

## 故障排除

### 端口被占用
如果端口 8000 被占用，脚本会提示终止占用进程或更换端口。

### 依赖安装失败
手动安装依赖：
```bash
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv pymysql scikit-learn jieba openai anthropic requests numpy
cd frontend && npm install
```

### 前端构建失败
```bash
cd frontend
npm install
npm run build
```
