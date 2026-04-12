"""
全局异常处理中间件
捕获所有未处理的异常，返回统一的错误响应格式
"""

import logging
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

logger = logging.getLogger(__name__)


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except HTTPException as http_exc:
            # 处理HTTP异常（如400、404等）
            return JSONResponse(
                status_code=http_exc.status_code,
                content={
                    "error": "HTTP Error",
                    "message": str(http_exc.detail),
                    "status_code": http_exc.status_code,
                    "path": request.url.path
                }
            )
        except Exception as exc:
            # 处理其他所有异常
            logger.error(f"Unhandled exception: {exc}", exc_info=True)

            # 根据环境决定是否暴露错误详情
            from backend.config.settings import settings
            error_detail = str(exc) if settings.DEBUG else "Internal server error"

            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "message": error_detail,
                    "status_code": HTTP_500_INTERNAL_SERVER_ERROR,
                    "path": request.url.path
                }
            )


def create_exception_handler_middleware():
    """创建异常处理中间件实例"""
    return ExceptionHandlerMiddleware