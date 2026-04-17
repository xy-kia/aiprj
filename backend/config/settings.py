"""
应用配置
"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 尝试从项目根目录或 backend 目录加载 .env
_project_root = Path(__file__).parent.parent.parent
_backend_dir = Path(__file__).parent.parent
for _env_path in [_project_root / ".env", _backend_dir / ".env"]:
    if _env_path.exists():
        load_dotenv(dotenv_path=str(_env_path), override=False)
        break


class Settings(BaseSettings):
    """应用配置类 - 优先读取运行时 .env，并提供本地运行的合理默认值"""

    # 应用信息
    APP_NAME: str = "Internship Assistant API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # 数据库配置 (默认使用 data/db/ 下的 SQLite)
    DATABASE_URL: str = "sqlite:///./data/db/internship.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis配置 (默认本地，开发环境可被内存缓存替换)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # JWT配置
    JWT_SECRET_KEY: str = "your-jwt-secret-key-change-this"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS配置（逗号分隔字符串，在代码中按需 split）
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:8080"

    # 爬虫配置
    CRAWLER_DELAY_MIN: float = 1.0
    CRAWLER_DELAY_MAX: float = 5.0
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_TIMEOUT: int = 30

    # 代理配置（逗号分隔字符串，在代码中按需 split）
    USE_PROXY: bool = False
    PROXY_LIST: str = ""

    # OpenAI / LLM 配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 文件存储配置
    STORAGE_TYPE: str = "local"
    STORAGE_LOCAL_PATH: str = "./data/uploads"
    STORAGE_MAX_FILE_SIZE: int = 10485760  # 10MB

    # 限流配置
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    # 监控配置
    PROMETHEUS_METRICS_ENABLED: bool = False
    SENTRY_DSN: str = ""

    class Config:
        case_sensitive = True


# 全局配置实例
settings = Settings()
