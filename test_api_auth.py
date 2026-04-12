#!/usr/bin/env python3
"""
测试API认证和配置流程
"""

import sys
import os
import json
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    import requests
except ImportError:
    print("安装requests库...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# API基础URL
BASE_URL = "http://localhost:8000/v1"

def print_response(response, description=""):
    """打印响应信息"""
    print(f"\n{'='*60}")
    if description:
        print(f"{description}")
    print(f"URL: {response.url}")
    print(f"状态码: {response.status_code}")
    if response.status_code != 200:
        print(f"错误: {response.text}")
    else:
        try:
            data = response.json()
            print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应文本: {response.text}")
    print(f"{'='*60}")

def test_health():
    """测试健康检查"""
    print("测试健康检查...")
    response = requests.get("http://localhost:8000/health")
    print_response(response, "健康检查")

def test_login(username, password):
    """测试登录"""
    print(f"\n测试登录: {username}")
    url = f"{BASE_URL}/auth/login"
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(url, data=data)
    print_response(response, f"登录 {username}")

    if response.status_code == 200:
        token_data = response.json()
        return token_data.get("access_token")
    return None

def test_get_me(token):
    """测试获取当前用户信息"""
    print("\n测试获取当前用户信息...")
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "获取当前用户")
    return response

def test_get_ai_config(token):
    """测试获取AI配置"""
    print("\n测试获取AI配置...")
    url = f"{BASE_URL}/config/ai-config"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print_response(response, "获取AI配置")
    return response

def test_update_ai_config(token, config):
    """测试更新AI配置"""
    print("\n测试更新AI配置...")
    url = f"{BASE_URL}/config/ai-config"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=config)
    print_response(response, "更新AI配置")
    return response

def test_search_jobs(token=None, anonymous=False):
    """测试搜索岗位"""
    print(f"\n测试搜索岗位 (anonymous={anonymous})...")
    url = f"{BASE_URL}/jobs/search-jobs"
    headers = {}
    if token and not anonymous:
        headers["Authorization"] = f"Bearer {token}"

    data = {
        "keywords": {
            "skills": ["Python", "Java"],
            "job_types": [],
            "locations": ["北京"],
            "experiences": [],
            "educations": []
        },
        "page": 1,
        "page_size": 10
    }

    response = requests.post(url, headers=headers, json=data)
    print_response(response, f"搜索岗位 (anonymous={anonymous})")
    return response

def main():
    """主测试函数"""
    print("开始API测试...")

    # 先检查服务是否运行
    try:
        test_health()
    except requests.exceptions.ConnectionError:
        print("错误：API服务未运行！请先启动服务。")
        print("启动命令: cd backend && python -m uvicorn main:app --reload")
        return

    # 测试匿名搜索（应该可以工作）
    print("\n=== 测试匿名搜索 ===")
    test_search_jobs(anonymous=True)

    # 测试登录和配置
    print("\n=== 测试认证流程 ===")

    # 测试admin登录
    admin_token = test_login("admin", "admin123")
    if not admin_token:
        print("管理员登录失败，停止测试")
        return

    # 测试获取用户信息
    test_get_me(admin_token)

    # 测试获取AI配置
    ai_config_resp = test_get_ai_config(admin_token)

    # 测试更新AI配置（模拟配置）
    if ai_config_resp.status_code == 200:
        config_data = ai_config_resp.json()
        print(f"当前配置ID: {config_data.get('id')}")

        # 测试更新配置（使用模拟API密钥）
        new_config = {
            "provider": "openai",
            "api_key": "sk-test-key-123456789",  # 测试密钥
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "enabled": True,
            "temperature": 0.7,
            "max_tokens": 2000
        }

        update_resp = test_update_ai_config(admin_token, new_config)
        if update_resp.status_code == 200:
            print("AI配置更新成功！")

    # 测试认证后的搜索
    print("\n=== 测试认证后搜索 ===")
    test_search_jobs(token=admin_token, anonymous=False)

    # 测试operator登录
    print("\n=== 测试operator用户 ===")
    operator_token = test_login("operator", "operator123")
    if operator_token:
        test_get_me(operator_token)
        test_search_jobs(token=operator_token, anonymous=False)

    print("\n测试完成！")

if __name__ == "__main__":
    main()