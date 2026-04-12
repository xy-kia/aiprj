"""
应用配置
"""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # 应用信息
    APP_NAME: str = "Internship Assistant API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 数据库配置 (开发环境使用SQLite，生产环境使用MySQL)
    DATABASE_URL: str = "sqlite:///./internship_db.sqlite"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # 安全配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # 爬虫配置
    CRAWLER_DELAY_MIN: float = 1.0
    CRAWLER_DELAY_MAX: float = 5.0
    CRAWLER_MAX_RETRIES: int = 3
    CRAWLER_TIMEOUT: int = 30

    # 代理配置
    USE_PROXY: bool = False
    PROXY_LIST: List[str] = []

    # OpenAI配置
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        case_sensitive = True


# 全局配置实例
settings = Settings()
