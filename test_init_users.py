#!/usr/bin/env python3
"""
测试初始化默认用户
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from backend.app.db.database import get_db_session
    from backend.app.db.models import User
    from backend.app.api.v1.endpoints.auth import init_default_users
    from passlib.context import CryptContext

    print("导入成功，开始初始化默认用户...")

    # 先检查现有用户
    with get_db_session() as db:
        users = db.query(User).all()
        print(f"当前数据库中有 {len(users)} 个用户:")
        for user in users:
            print(f"  - {user.username} ({user.email}), active: {user.is_active}, admin: {user.is_admin}")

    # 调用初始化函数
    init_default_users()

    # 再次检查
    with get_db_session() as db:
        users = db.query(User).all()
        print(f"\n初始化后有 {len(users)} 个用户:")
        for user in users:
            print(f"  - {user.username} ({user.email}), active: {user.is_active}, admin: {user.is_admin}")

    print("\n测试完成!")

except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)