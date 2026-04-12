"""
数据库连接池配置
基于SQLAlchemy的连接池管理
"""

from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import logging

from backend.config.settings import settings

logger = logging.getLogger(__name__)

# 创建基类
Base = declarative_base()

# 全局引擎实例
_engine: Optional[create_engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine():
    """获取数据库引擎实例（单例）"""
    global _engine
    if _engine is None:
        # 解析数据库URL
        db_url = settings.DATABASE_URL

        # 创建连接池
        pool_config = {
            "poolclass": QueuePool,
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_recycle": 3600,  # 连接池回收时间（秒）
            "pool_pre_ping": True,  # 连接前ping检查
            "echo": settings.DEBUG,  # 调试模式下输出SQL
            "echo_pool": settings.DEBUG,  # 调试模式下输出连接池事件
        }

        try:
            _engine = create_engine(db_url, **pool_config)
            logger.info(f"Database engine created with pool size: {settings.DATABASE_POOL_SIZE}")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise

    return _engine


def get_session_local():
    """获取会话本地工厂（单例）"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db():
    """获取数据库会话（用于依赖注入）"""
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """获取数据库会话的上下文管理器"""
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """初始化数据库（创建所有表）"""
    engine = get_engine()

    try:
        # 导入所有模型，确保它们被注册到Base.metadata
        # 这里需要导入所有模型文件
        from backend.app.db import models  # 假设模型在backend.app.db.models中

        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def check_db_connection() -> bool:
    """检查数据库连接是否正常"""
    try:
        with get_db_session() as db:
            # 执行简单查询测试连接
            result = db.execute(text("SELECT 1"))
            result.fetchone()
            logger.debug("Database connection check passed")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def close_db_connection():
    """关闭数据库连接池"""
    global _engine
    if _engine:
        _engine.dispose()
        _engine = None
        logger.info("Database connection pool closed")