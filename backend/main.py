"""
FastAPI主应用 - 学生求职AI助手后端API
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from backend.config.settings import settings
from backend.app.api.v1 import router as api_v1_router
from backend.app.middlewares.logging_middleware import create_logging_middleware
from backend.app.middlewares.exception_handler import create_exception_handler_middleware
from backend.app.db.database import check_db_connection
from backend.app.cache.redis_client import check_redis_connection

# 配置日志
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="学生求职AI助手后端API，提供意向解析、岗位搜索、问题生成和回答评估功能",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定义中间件
# 异常处理中间件（应该在最外层，最先处理异常）
app.add_middleware(create_exception_handler_middleware())
# 请求日志中间件
app.add_middleware(create_logging_middleware())

# 注册路由
# 注意：前端代理配置期望 /api 前缀，所以这里使用 /api/v1
app.include_router(api_v1_router, prefix="/v1")

# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查端点"""
    # 检查数据库连接
    db_healthy = check_db_connection()
    # 检查Redis连接
    redis_healthy = check_redis_connection()

    # 确定整体状态
    if db_healthy and redis_healthy:
        status = "healthy"
    elif not db_healthy and not redis_healthy:
        status = "unhealthy"
    else:
        status = "degraded"

    return {
        "status": status,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected" if db_healthy else "disconnected",
        "redis": "connected" if redis_healthy else "disconnected"
    }

# 根端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Welcome to Internship Assistant API",
        "docs": "/docs" if settings.DEBUG else None,
        "version": settings.APP_VERSION
    }

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理器"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "message": f"HTTP error: {exc.status_code}"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )