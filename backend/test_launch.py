#!/usr/bin/env python3
"""
直接启动服务器测试
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

def main():
    try:
        # 导入app
        print("导入app...")
        from backend.app.main import app

        print("启动服务器...")
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    return True

if __name__ == "__main__":
    main()