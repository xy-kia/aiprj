#!/usr/bin/env python3
"""
测试config.py修复
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.db.database import Base, get_db
from backend.app.api.v1.endpoints.config import get_or_create_anonymous_user

# 创建内存数据库进行测试
engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建会话
db = SessionLocal()

try:
    print("测试get_or_create_anonymous_user函数...")
    user = get_or_create_anonymous_user(db)
    print(f"成功获取/创建匿名用户: {user.username} (ID: {user.id})")

    # 测试再次调用
    user2 = get_or_create_anonymous_user(db)
    print(f"再次调用获取用户: {user2.username} (ID: {user2.id})")
    print(f"两个用户对象是否相同: {user.id == user2.id}")

    print("测试成功!")
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()