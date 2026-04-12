"""
API v1 路由
"""

from fastapi import APIRouter
from .endpoints import intent, jobs, questions, evaluation, auth, config

router = APIRouter()

# 注册各模块路由
router.include_router(intent.router, tags=["意向解析"])
router.include_router(jobs.router, tags=["岗位搜索"])
router.include_router(questions.router, tags=["问题生成"])
router.include_router(evaluation.router, tags=["回答评估"])
router.include_router(auth.router, prefix="/auth", tags=["认证授权"])
router.include_router(config.router, tags=["AI配置"])