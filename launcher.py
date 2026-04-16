#!/usr/bin/env python3
"""
一体化启动器 - 学生求职AI助手
将前端和后端集成到一个可执行文件中，一键启动。
"""

import os
import sys
import threading
import webbrowser
import time
import json
import socket
from pathlib import Path
import uvicorn
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse

# 添加项目根目录到Python路径（以便正确导入backend包）
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局应用实例
app = None

# === 猴子补丁：替换Redis为内存缓存 ===
def patch_redis():
    """用内存缓存替换Redis客户端"""
    logger.info("应用Redis猴子补丁...")

    # 导入原始的redis_client模块
    import backend.app.cache.redis_client as redis_module

    # 导入我们的内存缓存实现
    from backend.app.cache.memory_cache import MemoryCacheClient, get_memory_cache_client, check_memory_cache_connection

    # 替换RedisClient类
    redis_module.RedisClient = MemoryCacheClient

    # 替换全局客户端实例获取函数
    original_get_redis_client = redis_module.get_redis_client
    def patched_get_redis_client():
        return get_memory_cache_client()
    redis_module.get_redis_client = patched_get_redis_client

    # 替换连接检查函数
    redis_module.check_redis_connection = check_memory_cache_connection

    logger.info("Redis猴子补丁应用完成")

# === 猴子补丁：简化匹配计算器，禁用BERT ===
def patch_match_calculator():
    """修改匹配计算器，确保禁用BERT，使用TF-IDF"""
    logger.info("应用匹配计算器猴子补丁...")

    try:
        import backend.app.core.match_calculator as match_calculator_module

        # 保存原始方法
        original_init = match_calculator_module.MatchCalculator.__init__

        def patched_init(self, use_bert=False, *args, **kwargs):
            """强制禁用BERT，使用TF-IDF"""
            logger.info("匹配计算器初始化 - 禁用BERT，使用TF-IDF")
            # 调用原始初始化，但强制use_bert=False
            original_init(self, use_bert=False, *args, **kwargs)

        # 应用补丁
        match_calculator_module.MatchCalculator.__init__ = patched_init

        logger.info("匹配计算器猴子补丁应用完成 (BERT已禁用)")
    except Exception as e:
        logger.warning(f"应用匹配计算器猴子补丁失败: {e}")

# === 环境设置 ===
def setup_environment():
    """设置环境变量，配置SQLite和内存缓存"""
    # 获取用户数据目录
    data_dir = Path.home() / ".internship_assistant"
    data_dir.mkdir(exist_ok=True)

    # 设置SQLite数据库路径
    db_path = data_dir / "internship.db"

    # 环境变量配置
    env_vars = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "REDIS_URL": "memory://",  # 使用内存缓存
        "DEBUG": "False",
        "LOG_LEVEL": "INFO",
        "CORS_ORIGINS": '["http://localhost:8000"]',
        "OPENAI_API_KEY": "",  # 留空，用户可以在界面中配置
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "OPENAI_MODEL": "gpt-4o-mini",
        "APP_ENV": "production",
        "APP_DEBUG": "False"
    }

    # 设置环境变量
    for key, value in env_vars.items():
        os.environ[key] = value

    logger.info(f"数据库路径: {db_path}")
    logger.info("环境变量设置完成")
    return str(db_path)

# === 数据库初始化 ===
def init_database(db_path: str):
    """初始化SQLite数据库"""
    if not Path(db_path).exists():
        logger.info("初始化数据库...")

        try:
            # 导入数据库模块
            from backend.app.db.database import get_engine, Base

            # 导入所有模型以确保它们被注册
            from backend.app.db import models

            # 创建引擎和表
            engine = get_engine()
            Base.metadata.create_all(bind=engine)

            logger.info("数据库表创建成功")

            # 插入一些示例数据
            insert_sample_data(engine)

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            logger.warning("将继续启动，但数据库可能不完整")
    else:
        logger.info("数据库已存在，跳过初始化")

def insert_sample_data(engine):
    """插入示例数据"""
    from sqlalchemy.orm import Session
    from backend.app.db.models import Job, Skill

    with Session(engine) as session:
        # 检查是否已有数据
        job_count = session.query(Job).count()
        skill_count = session.query(Skill).count()

        if job_count == 0:
            logger.info("插入示例岗位数据...")
            # 示例岗位数据
            sample_jobs = [
                Job(
                    source="demo",
                    job_id="demo_001",
                    title="Python后端开发实习生",
                    company="科技公司A",
                    location="北京",
                    salary="200-300元/天",
                    experience="无经验要求",
                    education="本科及以上",
                    job_type="实习",
                    description="负责Python后端开发，参与系统设计和实现",
                    requirements="熟悉Python，了解Flask/FastAPI，有良好编码习惯",
                    skills=json.dumps(["Python", "Flask", "MySQL", "Git"]),
                    tags=json.dumps(["后端", "实习", "Python"]),
                    url="http://example.com/job/001",
                    published_at="2024-01-01",
                    is_active=True
                ),
                Job(
                    source="demo",
                    job_id="demo_002",
                    title="前端开发实习生",
                    company="互联网公司B",
                    location="上海",
                    salary="180-250元/天",
                    experience="无经验要求",
                    education="本科及以上",
                    job_type="实习",
                    description="负责Web前端开发，参与产品界面实现",
                    requirements="熟悉Vue/React，了解HTML/CSS/JavaScript",
                    skills=json.dumps(["Vue", "JavaScript", "HTML", "CSS"]),
                    tags=json.dumps(["前端", "实习", "Vue"]),
                    url="http://example.com/job/002",
                    published_at="2024-01-02",
                    is_active=True
                ),
                Job(
                    source="demo",
                    job_id="demo_003",
                    title="数据分析师实习生",
                    company="金融公司C",
                    location="深圳",
                    salary="220-300元/天",
                    experience="无经验要求",
                    education="本科及以上",
                    job_type="实习",
                    description="负责数据分析，制作报表，支持业务决策",
                    requirements="熟悉Python数据分析，了解SQL，有统计学基础",
                    skills=json.dumps(["Python", "SQL", "数据分析", "Excel"]),
                    tags=json.dumps(["数据", "实习", "分析"]),
                    url="http://example.com/job/003",
                    published_at="2024-01-03",
                    is_active=True
                )
            ]

            session.add_all(sample_jobs)
            session.commit()
            logger.info(f"插入了 {len(sample_jobs)} 个示例岗位")

        if skill_count == 0:
            logger.info("插入示例技能数据...")
            # 示例技能数据
            sample_skills = [
                Skill(name="Python", category="编程语言", description="Python编程语言"),
                Skill(name="Java", category="编程语言", description="Java编程语言"),
                Skill(name="JavaScript", category="编程语言", description="JavaScript编程语言"),
                Skill(name="Vue", category="前端框架", description="Vue.js前端框架"),
                Skill(name="React", category="前端框架", description="React前端框架"),
                Skill(name="Flask", category="后端框架", description="Flask Python框架"),
                Skill(name="FastAPI", category="后端框架", description="FastAPI Python框架"),
                Skill(name="MySQL", category="数据库", description="MySQL数据库"),
                Skill(name="SQL", category="数据库", description="SQL查询语言"),
                Skill(name="Git", category="工具", description="版本控制工具"),
                Skill(name="数据分析", category="数据分析", description="数据分析技能"),
                Skill(name="机器学习", category="AI", description="机器学习基础"),
            ]

            session.add_all(sample_skills)
            session.commit()
            logger.info(f"插入了 {len(sample_skills)} 个示例技能")

# === 创建应用 ===
def create_app():
    """创建FastAPI应用并集成前端"""
    logger.info("创建FastAPI应用...")

    # 应用猴子补丁
    patch_redis()
    patch_match_calculator()

    # 导入后端应用
    from backend.main import app as backend_app

    # 创建主应用
    app = FastAPI(
        title="学生求职AI助手 (一体化版本)",
        version="1.0.0",
        description="学生求职AI助手的一体化启动版本，包含前后端"
    )

    # 挂载后端API
    app.mount("/api", backend_app)

    # 尝试挂载前端静态文件
    frontend_dist = Path(__file__).parent / "frontend" / "dist"

    if frontend_dist.exists():
        # 挂载静态文件
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

        # 添加回退路由
        @app.get("/{full_path:path}")
        async def serve_frontend(request: Request, full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"error": "API path not found"}, status_code=404)

            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return JSONResponse({"error": "Frontend file not found"}, status_code=404)

        logger.info("前端静态文件已挂载")
    else:
        logger.warning("前端构建目录不存在，提供简化界面")
        # 提供简化界面
        @app.get("/")
        async def serve_simple_ui():
            html_content = """
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>学生求职AI助手 - 一体化版本</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 20px;
                        line-height: 1.6;
                    }
                    .header {
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 40px;
                        border-radius: 10px;
                        text-align: center;
                        margin-bottom: 30px;
                    }
                    .card {
                        background: white;
                        border: 1px solid #ddd;
                        border-radius: 8px;
                        padding: 20px;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .button {
                        display: inline-block;
                        background: #667eea;
                        color: white;
                        padding: 10px 20px;
                        text-decoration: none;
                        border-radius: 5px;
                        margin: 5px;
                        transition: background 0.3s;
                    }
                    .button:hover {
                        background: #5a67d8;
                    }
                    .endpoint {
                        background: #f7fafc;
                        border-left: 4px solid #667eea;
                        padding: 10px;
                        margin: 10px 0;
                        font-family: monospace;
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>学生求职AI助手</h1>
                    <p>一体化启动版本</p>
                </div>

                <div class="card">
                    <h2>🎯 系统状态</h2>
                    <p>✅ 后端API服务运行正常</p>
                    <p>⚠️ 前端界面未构建（使用此简化界面）</p>
                    <p>如需完整功能，请构建前端：<code>cd frontend && npm run build</code></p>
                </div>

                <div class="card">
                    <h2>🚀 快速开始</h2>
                    <p>系统已启动并运行以下服务：</p>

                    <div class="endpoint">
                        <strong>API文档:</strong> <a href="/api/docs" target="_blank">/api/docs</a>
                    </div>

                    <div class="endpoint">
                        <strong>健康检查:</strong> <a href="/api/health" target="_blank">/api/health</a>
                    </div>

                    <div class="endpoint">
                        <strong>API根端点:</strong> <a href="/api" target="_blank">/api</a>
                    </div>
                </div>

                <div class="card">
                    <h2>📚 可用API</h2>
                    <p>以下API端点可用：</p>
                    <ul>
                        <li><code>POST /api/v1/parse-intent</code> - 解析求职意向</li>
                        <li><code>POST /api/v1/search-jobs</code> - 搜索岗位</li>
                        <li><code>POST /api/v1/generate-questions</code> - 生成面试问题</li>
                        <li><code>POST /api/v1/evaluate-answer</code> - 评估回答</li>
                    </ul>

                    <p>
                        <a href="/api/docs" class="button">查看完整API文档</a>
                        <a href="https://github.com/your-repo" class="button" target="_blank">项目GitHub</a>
                    </p>
                </div>

                <div class="card">
                    <h2>⚙️ 技术说明</h2>
                    <p>这是一个一体化版本，特点：</p>
                    <ul>
                        <li>✅ 使用SQLite数据库（无需安装MySQL）</li>
                        <li>✅ 使用内存缓存（无需安装Redis）</li>
                        <li>✅ 禁用BERT模型依赖（使用TF-IDF）</li>
                        <li>✅ 包含示例数据</li>
                        <li>⚠️ AI功能需要配置API密钥（可在界面中配置）</li>
                    </ul>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)

    logger.info("FastAPI应用创建完成")
    return app

# === 端口检查 ===
def check_port_available(port: int) -> bool:
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return True
        except OSError:
            return False

def find_available_port(start_port: int = 8000, max_port: int = 9000) -> int:
    """查找可用端口"""
    for port in range(start_port, max_port + 1):
        if check_port_available(port):
            return port
    return -1

# === 服务器启动 ===
def start_server(port: int = 8000):
    """启动FastAPI服务器"""
    global app

    app = create_app()

    logger.info(f"🚀 启动服务器在 http://localhost:{port}")
    logger.info(f"📚 API文档: http://localhost:{port}/api/docs")
    logger.info(f"🏥 健康检查: http://localhost:{port}/api/health")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

# === 浏览器打开 ===
def open_browser(port: int = 8000, delay: int = 2):
    """延迟后打开浏览器"""
    time.sleep(delay)
    url = f"http://localhost:{port}"
    try:
        webbrowser.open(url)
        logger.info(f"🌐 已打开浏览器访问 {url}")
    except Exception as e:
        logger.warning(f"无法自动打开浏览器: {e}")
        logger.info(f"请手动访问: {url}")

# === 主函数 ===
def main():
    """主函数"""
    # 设置标准输出编码为UTF-8，避免Windows下emoji打印错误
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.6及以下版本不支持reconfigure
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("\n" + "="*60)
    print("       学生求职AI助手 - 一体化启动器")
    print("="*60)
    print("🚀 正在启动一体化版本...")
    print("💡 特点: SQLite数据库 + 内存缓存 + 示例数据")
    print("⏳ 请稍候...\n")

    # 获取端口配置
    port = int(os.environ.get("APP_PORT", "8000"))

    # 检查端口是否可用
    if not check_port_available(port):
        print(f"⚠️  端口 {port} 已被占用")
        new_port = find_available_port(port + 1)
        if new_port != -1:
            print(f"✅ 找到可用端口: {new_port}")
            try:
                response = input(f"是否使用端口 {new_port} 启动? (y/n): ").strip().lower()
                if response == 'y':
                    port = new_port
                    os.environ["APP_PORT"] = str(port)
                else:
                    print("❌ 用户取消启动")
                    sys.exit(0)
            except (KeyboardInterrupt, EOFError):
                print("\n❌ 启动已取消")
                sys.exit(0)
        else:
            print(f"❌ 无法找到 {port}-9000 范围内的可用端口")
            print("请手动关闭占用端口的程序")
            sys.exit(1)

    # 设置环境
    db_path = setup_environment()

    # 初始化数据库
    init_database(db_path)

    # 在后台线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser, args=(port, 3))
    browser_thread.daemon = True
    browser_thread.start()

    # 启动服务器（阻塞）
    try:
        start_server(port)
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()