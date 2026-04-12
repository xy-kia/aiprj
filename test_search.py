#!/usr/bin/env python3
"""
测试搜索功能，直接调用jobs.py中的函数
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.database import Base, get_db
from backend.app.api.v1.endpoints.jobs import search_jobs, SearchJobsRequest, KeywordsModel
import asyncio

# 创建内存数据库
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 模拟数据库依赖
def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

async def test():
    # 创建模拟请求
    request = SearchJobsRequest(
        keywords=KeywordsModel(
            skills=[],
            job_types=['实习'],
            locations=['上海'],
            experiences=['no experience'],
            educations=['本科']
        ),
        page=1,
        page_size=10
    )

    # 调用搜索函数（需要模拟current_user和db）
    try:
        db = next(override_get_db())
        result = await search_jobs(request, current_user=None, db=db)
        print(f'成功: {result}')
    except HTTPException as e:
        print(f'HTTP异常: {e.detail}')
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f'其他异常: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())