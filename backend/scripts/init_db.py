#!/usr/bin/env python3
"""
数据库初始化脚本
创建所有数据库表
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from backend.app.db.database import init_db

def main():
    """初始化数据库"""
    print("Initializing database...")
    try:
        init_db()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()