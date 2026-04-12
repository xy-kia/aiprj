"""
请求日志中间件
记录所有API请求的详细信息：路径、方法、状态码、耗时等
"""

import time
import logging
from typing import Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        # 记录请求开始时间
        start_time = time.time()

        # 记录请求信息
        request_info = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        # 对于非GET请求，可以记录请求体（注意：可能会包含敏感信息）
        if request.method not in ["GET", "HEAD"]:
            try:
                body = await request.body()
                if body:
                    # 只记录前500个字符，避免日志过大
                    request_info["body_preview"] = body[:500].decode('utf-8', errors='ignore')
            except Exception:
                # 如果无法读取请求体，跳过
                pass

        # 调用下一个中间件或路由处理器
        response = await call_next(request)

        # 计算请求耗时
        process_time = time.time() - start_time

        # 记录响应信息
        response_info = {
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "content_length": response.headers.get("content-length", 0),
            "content_type": response.headers.get("content-type"),
        }

        # 组合日志信息
        log_data = {
            "type": "request",
            **request_info,
            **response_info,
        }

        # 根据状态码决定日志级别
        if response.status_code >= 500:
            logger.error(log_data)
        elif response.status_code >= 400:
            logger.warning(log_data)
        else:
            logger.info(log_data)

        # 添加响应头：请求耗时
        response.headers["X-Process-Time"] = str(process_time)

        return response


def create_logging_middleware():
    """创建日志中间件实例"""
    return LoggingMiddleware