### 手动启动
```bash
# 安装必要依赖（如果尚未安装）
pip install fastapi uvicorn sqlalchemy pydantic python-dotenv pymysql scikit-learn jieba

# 启动一体化服务器
python launcher.py
```

### 一体化版本特点
- ✅ **无需安装MySQL、Redis** - 使用SQLite数据库 + 内存缓存
- ✅ **禁用BERT模型依赖** - 使用TF-IDF替代，启动更快
- ✅ **包含示例数据** - 默认有岗位、技能等数据
- ✅ **自动打开浏览器** - 启动后自动访问应用
- ⚠️ **AI功能需要配置** - 首次使用需在界面中配置API密钥

访问地址：
- **应用界面**: http://localhost:8000
- **API文档**: http://localhost:8000/api/docs
- **健康检查**: http://localhost:8000/api/health

## 快速开始（使用Docker Compose）

如果你已经安装了Docker和Docker Compose，可以快速启动所有服务：

```bash
# 复制环境变量示例文件
cp backend/.env.example backend/.env

# 启动所有服务（MySQL, Redis, 后端API）
docker-compose up -d

# 启动前端开发服务器（新终端）
cd frontend
npm install
npm run dev

# 启动管理后台（新终端，可选）
cd admin
npm install
npm run dev
```

访问应用：
- 前端界面：http://localhost:5173 (Vite默认端口)
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs
- 管理后台：http://localhost:5174 (如果启动)

停止服务：
```bash
docker-compose down
```

注意：首次运行需要构建Docker镜像，可能需要几分钟。

## 环境配置要求

### 1. 基础开发环境

#### 1.1 必需软件
- **Python 3.9+** - 后端开发语言
- **Node.js 18+** - 前端开发环境
- **MySQL 8.0+** - 数据库
- **Redis 6.0+** - 缓存和消息队列
- **Docker** - 容器化部署（可选，用于开发环境）
- **Git** - 版本控制

#### 1.2 安装指南

##### Windows 系统

1. **Python 3.9+**
   - 访问 [Python官网](https://www.python.org/downloads/)
   - 下载 Python 3.9+ 安装包
   - 安装时勾选 "Add Python to PATH"
   - 验证安装：`python --version`

2. **Node.js 18+**
   - 访问 [Node.js官网](https://nodejs.org/)
   - 下载 LTS 版本（推荐 18+）
   - 验证安装：`node --version` 和 `npm --version`

3. **MySQL 8.0+**
   - 访问 [MySQL官网](https://dev.mysql.com/downloads/mysql/)
   - 下载 MySQL Community Server
   - 安装过程中设置 root 密码（请妥善保存）
   - 验证安装：`mysql --version`

4. **Redis 6.0+**
   - Windows 版本有限制，建议使用以下方式之一：
   - **选项1：使用 Docker**（推荐）
     ```bash
     docker run --name redis -p 6379:6379 -d redis:6-alpine
     ```
   - **选项2：Windows 子系統 Linux (WSL)**
     - 启用 WSL：`wsl --install`
     - 安装 Ubuntu，然后在 Ubuntu 中安装 Redis
   - 验证安装：`redis-cli ping` 返回 PONG

5. **Docker Desktop**
   - 访问 [Docker官网](https://www.docker.com/products/docker-desktop/)
   - 下载 Docker Desktop for Windows
   - 安装后重启计算机
   - 验证安装：`docker --version`

6. **Git**
   - 访问 [Git官网](https://git-scm.com/download/win)
   - 下载 Git for Windows
   - 验证安装：`git --version`
   - 配置用户名和邮箱：
     ```bash
     git config --global user.name "Your Name"
     git config --global user.email "your.email@example.com"
     ```

##### macOS 系统

1. **使用 Homebrew 安装（推荐）**
   ```bash
   # 安装 Homebrew（如果未安装）
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   
   # 安装各组件
   brew install python@3.9
   brew install node@18
   brew install mysql@8.0
   brew install redis
   brew install docker
   brew install git
   
   # 启动服务
   brew services start mysql
   brew services start redis
   ```

##### Linux (Ubuntu/Debian) 系统

```bash
# 更新包管理器
sudo apt update && sudo apt upgrade -y

# 安装 Python 3.9
sudo apt install python3.9 python3.9-venv python3.9-dev -y

# 安装 Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# 安装 MySQL 8.0
sudo apt install mysql-server -y
sudo systemctl start mysql
sudo systemctl enable mysql

# 安装 Redis
sudo apt install redis-server -y
sudo systemctl start redis
sudo systemctl enable redis

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Git
sudo apt install git -y
```

### 2. 项目依赖安装

#### 2.1 后端依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖包
pip install -r requirements.txt

# 安装 Playwright 浏览器（仅需一次）
playwright install chromium
```

**后端核心依赖包：**
- FastAPI - Web框架
- Uvicorn - ASGI服务器
- SQLAlchemy - ORM
- PyMySQL - MySQL驱动
- Redis - 缓存客户端
- Scrapy/Playwright - 爬虫框架
- Jieba - 中文分词
- scikit-learn - 机器学习
- sentence-transformers - 文本嵌入
- OpenAI/HTTPX - API调用

#### 2.2 前端依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 开发模式运行
npm run dev
```

**前端核心依赖包：**
- Vue 3 - 前端框架
- Axios - HTTP客户端
- Element Plus - UI组件库
- Vue Router - 路由管理
- Pinia - 状态管理
- ECharts - 图表库
- Markdown-it - Markdown解析

### 3. 数据库配置

#### 3.1 MySQL 配置

```sql
-- 创建数据库
CREATE DATABASE IF NOT EXISTS job_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 创建用户并授权
CREATE USER IF NOT EXISTS 'job_ai_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON job_ai.* TO 'job_ai_user'@'localhost';
FLUSH PRIVILEGES;
```

#### 3.2 Redis 配置

默认配置（无需修改）：
- 主机：localhost
- 端口：6379
- 密码：无（生产环境建议设置）

### 4. 环境变量配置

#### 4.1 后端环境变量

复制后端示例环境变量文件并配置：

```bash
cd backend
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_NAME=job_ai
DB_USER=job_ai_user
DB_PASSWORD=your_password

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# 应用配置
APP_ENV=development
APP_DEBUG=true
APP_SECRET_KEY=your_secret_key_here

# 爬虫配置
CRAWLER_PROXY_ENABLED=false
CRAWLER_MAX_CONCURRENT=3
CRAWLER_REQUEST_DELAY=1-5

# AI服务配置（可选）
# 注意：您也可以通过Admin管理后台界面配置AI服务，详见"大模型API配置"章节
OPENAI_API_KEY=your_openai_api_key
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 5. 项目初始化

#### 5.1 数据库迁移

```bash
cd backend
# 初始化数据库表（确保MySQL和Redis服务已启动）
python scripts/init_db.py

# 或使用 Alembic（如果配置）
alembic upgrade head
```

#### 5.2 知识库数据导入

```bash
cd backend
# 导入预设的岗位、技能等数据（需要数据库已初始化）
python scripts/import_knowledge_data.py
```

#### 5.3 启动服务

**开发环境：**

1. 启动后端服务：
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. 启动前端服务：
   ```bash
   cd frontend
   npm run dev
   ```

3. 访问应用：
   - 前端：http://localhost:3000
   - 后端API：http://localhost:8000
   - API文档：http://localhost:8000/docs

**使用 Docker Compose：**

```bash
# 一键启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 6. 验证安装

运行测试脚本验证环境配置：

```bash
cd scripts
python check_environment.py
```

预期输出（示例）：
```
==================================================
环境配置检查
==================================================
检查 Python 3.9+... ✅ Python 3.9.10
检查 Node.js 18+... ✅ v18.19.0
检查 MySQL 安装... ✅ mysql  Ver 8.0.36 for Linux on x86_64 (MySQL Community Server - GPL)
检查 Redis 安装... ✅ redis-cli 6.2.5
检查 Docker... ✅ Docker version 24.0.7, build afdd53b
检查 Git... ✅ git version 2.34.1
检查后端依赖... ✅ 已安装
检查前端依赖... ✅ node_modules存在
==================================================
✅ 所有检查通过 (8/8)
✅ 所有服务就绪！
```

### 7. 常见问题

#### 7.1 Python 包安装失败
- 使用国内镜像源：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`
- 升级 pip：`python -m pip install --upgrade pip`

#### 7.2 Node.js 依赖安装慢
- 使用淘宝镜像：`npm config set registry https://registry.npmmirror.com`
- 使用 yarn：`npm install -g yarn && yarn install`

#### 7.3 MySQL 连接失败
- 检查服务是否启动：`sudo systemctl status mysql`
- 检查防火墙设置
- 验证用户名和密码

#### 7.4 Redis 连接失败
- Windows 用户建议使用 Docker 运行 Redis
- 检查 Redis 服务状态：`sudo systemctl status redis`

#### 7.5 Playwright 安装失败
- 手动安装 Chromium：`playwright install chromium --with-deps`
- 或使用系统包管理器安装浏览器

### 8. 下一步

环境配置完成后，请参考以下文档：
- [开发流程](./docs/Development_Process.md) - 完整开发流程
- [功能规格](./docs/Functional_Spec.md) - 功能需求说明
- [API文档](./docs/API_Documentation.md) - API接口文档

## 技术支持

遇到问题请：
1. 查看项目文档
2. 检查环境配置步骤
3. 查看 `docs/` 目录下的详细文档
4. 提交 Issue 到项目仓库

---

**最后更新：2026-04-12**  
**新增功能：一体化启动器 - 启动时间从分钟级缩短到秒级**  
**环境检查状态：部分完成（参见 docs/Phase1_Task_Checklist.md）**