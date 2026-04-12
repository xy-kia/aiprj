# 学生求职AI员工 - 智能岗位匹配系统

一个基于AI的学生求职辅助系统，通过爬虫收集招聘岗位，利用知识库进行智能匹配，帮助学生找到合适的实习和工作机会。

## 项目结构

```
.
├── backend/          # 后端服务（FastAPI + 爬虫）
├── frontend/         # 前端界面（Vue 3）
├── knowledge/        # 知识库数据（岗位、技能、城市代码等）
├── admin/            # 管理后台
├── scripts/          # 工具脚本
├── tests/            # 测试代码
├── docs/             # 项目文档
├── docker-compose.yml # Docker编排配置
├── launcher.py       # 🆕 一体化启动器（推荐使用）
├── start.bat         # 🆕 Windows启动脚本
├── start.sh          # 🆕 macOS/Linux启动脚本
└── memory_cache.py   # 🆕 内存缓存实现（替代Redis）
```

## 🚀 快速开始（一体化版本）

**推荐新用户使用此方式** - 无需安装MySQL、Redis，一键启动所有功能！

### Windows用户
1. 双击运行 `start.bat`
2. 等待自动安装依赖并启动
3. 浏览器自动打开 http://localhost:8000

### macOS/Linux用户
```bash
# 给启动脚本执行权限
chmod +x start.sh

# 运行启动脚本
./start.sh
```

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

## 大模型API配置

系统支持多AI提供商配置，可通过Admin管理后台轻松设置OpenAI、Anthropic、Azure和自定义大模型API。

### 配置流程

**配置优先级说明**：
- **管理界面配置优先**：如果在Admin后台配置了AI服务，系统将优先使用界面配置
- **环境变量备选**：如果未在界面配置或配置未启用，系统将使用环境变量中的配置
- **建议**：生产环境建议使用管理界面配置，便于管理和切换

#### 1. 访问管理后台
1. 启动管理后台服务：
   ```bash
   cd admin
   npm install
   npm run dev
   ```
2. 访问管理后台：http://localhost:5174
3. 登录后进入"系统配置"页面

#### 2. AI提供商配置
在"LLM API配置"板块中，您可以：

1. **选择AI提供商**：
   - **OpenAI**：官方OpenAI API（默认）
   - **Anthropic**：Claude系列模型
   - **Azure**：Azure OpenAI服务
   - **自定义/反代**：国内代理或自建OpenAI兼容服务

2. **配置API密钥**：
   - 输入对应提供商的API密钥
   - 密钥将加密存储到数据库

3. **设置基础URL**：
   - 系统会根据选择的提供商显示默认URL
   - 支持自定义URL用于国内代理（如OneAPI、OpenAI-Proxy等）
   - 示例：
     - OpenAI默认：`https://api.openai.com/v1`
     - 国内代理：`https://your-proxy.com/v1`
     - Azure OpenAI：`https://{resource}.openai.azure.com`

4. **测试连接**：
   - 点击"测试连接"按钮验证API密钥和URL
   - 成功连接后系统会自动获取可用模型列表
   - 错误提示会帮助诊断连接问题

5. **选择模型**：
   - 从获取的模型列表中选择默认模型
   - OpenAI：gpt-4o-mini, gpt-4o, gpt-3.5-turbo等
   - Anthropic：claude-3-sonnet, claude-3-haiku等

6. **调整参数**：
   - **温度**：控制回答的随机性（0.0-2.0）
   - **最大令牌数**：限制回答长度（100-16384）
   - **启用配置**：启用/禁用此AI配置

7. **保存配置**：
   - 点击"保存配置"将设置存储到数据库
   - 系统将使用此配置进行AI相关操作

### 支持的AI提供商

#### OpenAI（推荐）
- **官方API**：`https://api.openai.com/v1`
- **支持模型**：GPT-4系列、GPT-3.5系列
- **国内使用**：需配置代理或使用国内中转服务
- **自定义URL**：支持反代服务（如OneAPI、LobeChat等）

#### Anthropic（Claude）
- **官方API**：`https://api.anthropic.com`
- **支持模型**：Claude-3系列（Sonnet、Haiku、Opus）
- **特色**：长上下文、强推理能力

#### Azure OpenAI
- **URL格式**：`https://{resource}.openai.azure.com`
- **兼容性**：完全兼容OpenAI API
- **优势**：企业级服务、合规性支持

#### 自定义/反代服务
- **适用场景**：国内网络环境、自建部署
- **常见方案**：
  - **OneAPI**：统一API网关，支持多模型
  - **LobeChat**：带界面的ChatGPT客户端
  - **自建服务器**：使用openai-api、ChatGPT-Next-Web等
- **配置方式**：将服务地址填入基础URL字段

### 常见问题

#### Q: 如何获取API密钥？
- **OpenAI**：访问 https://platform.openai.com/api-keys
- **Anthropic**：访问 https://console.anthropic.com/account/keys
- **Azure**：在Azure门户创建OpenAI资源

#### Q: 国内无法访问OpenAI怎么办？
1. 使用代理服务（如OneAPI、API2D等）
2. 配置自定义基础URL
3. 选择国内可访问的提供商（如Anthropic）

#### Q: 测试连接失败怎么办？
1. 检查API密钥是否正确
2. 验证网络连接是否正常
3. 确认基础URL格式正确
4. 查看后端日志获取详细错误信息

#### Q: 如何切换不同的AI提供商？
1. 在Admin后台选择新的提供商
2. 输入对应的API密钥和URL
3. 测试连接并选择模型
4. 保存配置即可切换

#### Q: 配置保存后如何生效？
- 配置会立即生效，系统下次调用AI时会使用新配置
- 建议重启后端服务以确保配置完全加载

### 配置示例

#### 示例1：OpenAI + 国内代理
```yaml
提供商: OpenAI
API密钥: sk-****************
基础URL: https://api.example.com/v1  # 国内代理地址
模型: gpt-4o-mini
温度: 0.7
最大令牌数: 2000
```

#### 示例2：Anthropic官方
```yaml
提供商: Anthropic
API密钥: sk-ant-****************
基础URL: https://api.anthropic.com  # 自动填充
模型: claude-3-sonnet
温度: 0.8
最大令牌数: 4000
```

#### 示例3：Azure OpenAI
```yaml
提供商: Azure
API密钥: **********  # Azure API密钥
基础URL: https://my-ai-resource.openai.azure.com
模型: gpt-4
温度: 0.9
最大令牌数: 1000
```

### 最佳实践
1. **生产环境**：建议使用Azure OpenAI或自建服务
2. **开发环境**：可使用OpenAI官方API（注意用量限制）
3. **密钥安全**：API密钥应加密存储，定期轮换
4. **监控告警**：配置API使用量监控和异常告警
5. **备份配置**：定期导出配置文件备份

### 故障排除

#### 后端日志查看
```bash
# Docker环境
docker-compose logs -f backend

# 本地环境
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 数据库配置检查
```sql
-- 查看用户配置
SELECT user_id, ai_provider, enabled, base_url, default_model 
FROM user_configs;
```

#### API测试
```bash
# 测试配置API
curl -X GET "http://localhost:8000/api/v1/ai-config"

# 测试连接
curl -X POST "http://localhost:8000/api/v1/ai-config/test-connection" \
  -H "Content-Type: application/json" \
  -d '{"provider": "openai", "api_key": "your_key", "base_url": "https://api.openai.com/v1"}'
```

更多技术细节请参考：[config.py](backend/app/api/v1/endpoints/config.py)

## 🎯 一体化启动器技术说明

### 设计目标
针对用户反馈的"启动时间太长"问题，一体化启动器实现了以下优化：

1. **零外部依赖** - 无需安装MySQL、Redis，使用SQLite + 内存缓存
2. **轻量级AI模型** - 用TF-IDF替代BERT，减少模型加载时间
3. **一键启动** - 双击脚本即可运行，自动安装依赖
4. **数据预置** - 包含示例岗位和技能数据

### 技术实现

#### 1. 数据库层优化
```python
# 使用SQLite替代MySQL
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

# 自动创建示例数据
sample_jobs = [...]
sample_skills = [...]
```

#### 2. 缓存层优化
```python
# 使用内存缓存替代Redis
class MemoryCacheClient:
    # 实现与RedisClient兼容的接口
    def set(self, key, value, ex=None): ...
    def get(self, key, default=None): ...
```

#### 3. AI模型优化
```python
# 禁用BERT，使用TF-IDF
def patched_calculate_similarity(self, user_text, job_text, use_bert=False):
    # 强制使用TF-IDF，忽略use_bert参数
    vectors = self.vectorizer.transform([user_text, job_text])
    similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
    return float(similarity)
```

#### 4. 前后端集成
```python
# 挂载前端静态文件
app.mount("/", StaticFiles(directory=str(frontend_dist), html=True))

# 后端API路由
app.mount("/api", backend_app)
```

### 性能对比
| 方面 | 传统方式 | 一体化版本 | 改进 |
|------|----------|------------|------|
| 启动时间 | 2-5分钟 | 10-30秒 | ⏱️ 10倍更快 |
| 外部依赖 | MySQL + Redis | 无 | 📦 零依赖 |
| 安装步骤 | 5+步 | 1步 | 🚀 一键启动 |
| 内存占用 | 较高 | 较低 | 💾 更轻量 |

### 限制与说明
1. **SQLite限制** - 适用于中小规模数据，大规模生产建议使用MySQL
2. **TF-IDF精度** - 文本相似度计算精度略低于BERT，但速度更快
3. **内存缓存** - 重启后数据丢失，适用于演示和开发
4. **AI功能** - 仍需配置API密钥才能使用完整AI功能

### 前端构建指南
一体化版本默认提供简化界面。如需使用完整前端：

```bash
# 1. 安装Node.js（如果尚未安装）
# 2. 进入前端目录
cd frontend

# 3. 安装依赖（首次运行）
npm install

# 4. 构建生产版本
npm run build

# 5. 重新启动一体化启动器
cd ..
python launcher.py
```

构建完成后，访问 http://localhost:8000 将显示完整的Vue前端。

### 高级使用
如需切换回完整版本，只需：
```bash
# 1. 安装MySQL和Redis
# 2. 修改backend/.env配置
# 3. 使用Docker Compose或传统方式启动
```

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