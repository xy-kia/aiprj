#!/usr/bin/env python3
"""
测试API连接
"""

import sys
import json
import requests
import time

def test_health():
    """测试健康端点"""
    url = "http://localhost:8000/api/health"
    try:
        response = requests.get(url, timeout=5)
        print(f"健康检查: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"健康检查失败: {e}")
        return False

def test_search_jobs():
    """测试搜索岗位"""
    url = "http://localhost:8000/api/v1/search-jobs"
    data = {
        "keywords": {
            "skills": ["Python"],
            "job_types": [],
            "locations": [],
            "experiences": [],
            "educations": []
        },
        "page": 1,
        "page_size": 10
    }

    try:
        response = requests.post(url, json=data, timeout=30)
        print(f"搜索岗位: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"找到岗位数: {result.get('total', 0)}")
            print(f"返回岗位数: {len(result.get('jobs', []))}")
            if result.get('jobs'):
                for i, job in enumerate(result['jobs'][:3]):
                    print(f"  岗位 {i+1}: {job.get('title')} - {job.get('company')}")
            return True
        else:
            print(f"错误: {response.text}")
            return False
    except Exception as e:
        print(f"搜索失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 50)
    print("测试API连接")
    print("=" * 50)

    # 等待服务器启动
    print("等待服务器启动...")
    time.sleep(3)

    # 测试健康端点
    print("\n1. 测试健康端点...")
    if not test_health():
        print("❌ 健康检查失败")
        return False

    # 测试搜索
    print("\n2. 测试搜索岗位...")
    success = test_search_jobs()

    print("\n" + "=" * 50)
    print(f"测试结果: {'✅ 成功' if success else '❌ 失败'}")
    print("=" * 50)

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)