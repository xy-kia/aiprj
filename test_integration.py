#!/usr/bin/env python3
"""
集成测试：启动服务器并测试关键API功能
"""

import sys
import os
import time
import subprocess
import signal
import atexit

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

BASE_URL = "http://localhost:8000"
V1_URL = f"{BASE_URL}/v1"

class ServerManager:
    """管理服务器进程"""
    def __init__(self):
        self.process = None

    def start(self):
        """启动服务器"""
        if self.process:
            return

        print("启动服务器...")
        cmd = [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
        # 在后台启动
        self.process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW  # Windows上隐藏窗口
        )

        # 等待服务器启动
        print("等待服务器启动...")
        time.sleep(5)

        # 检查是否启动成功
        for _ in range(10):
            try:
                response = requests.get(f"{BASE_URL}/health", timeout=2)
                if response.status_code == 200:
                    print("服务器启动成功!")
                    return True
            except:
                time.sleep(1)

        print("服务器启动失败!")
        self.stop()
        return False

    def stop(self):
        """停止服务器"""
        if self.process:
            print("停止服务器...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

def wait_for_server():
    """等待服务器可用"""
    for i in range(30):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(1)
    return False

def test_anonymous_search():
    """测试匿名搜索"""
    print("\n1. 测试匿名搜索...")
    url = f"{V1_URL}/jobs/search-jobs"
    data = {
        "keywords": {
            "skills": ["Python"],
            "job_types": [],
            "locations": ["北京"],
            "experiences": [],
            "educations": []
        },
        "page": 1,
        "page_size": 5
    }

    try:
        response = requests.post(url, json=data, timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"成功! 获取到 {len(result.get('jobs', []))} 个岗位")
            return True
        else:
            print(f"失败: {response.text}")
            return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False

def test_login_and_config():
    """测试登录和配置"""
    print("\n2. 测试登录和AI配置...")

    # 登录
    print("登录admin用户...")
    login_url = f"{V1_URL}/auth/login"
    login_data = {"username": "admin", "password": "admin123"}

    response = requests.post(login_url, data=login_data, timeout=5)
    if response.status_code != 200:
        print(f"登录失败: {response.text}")
        return None

    token_data = response.json()
    token = token_data.get("access_token")
    print(f"登录成功，获取到token")

    # 获取AI配置
    print("获取AI配置...")
    headers = {"Authorization": f"Bearer {token}"}
    config_url = f"{V1_URL}/config/ai-config"

    response = requests.get(config_url, headers=headers, timeout=5)
    if response.status_code == 200:
        config = response.json()
        print(f"当前AI配置: provider={config.get('provider')}, enabled={config.get('enabled')}")
    else:
        print(f"获取配置失败: {response.text}")

    # 使用token搜索
    print("\n3. 测试认证后搜索...")
    search_url = f"{V1_URL}/jobs/search-jobs"
    search_data = {
        "keywords": {
            "skills": ["Java"],
            "job_types": [],
            "locations": ["上海"],
            "experiences": [],
            "educations": []
        },
        "page": 1,
        "page_size": 5
    }

    response = requests.post(search_url, headers=headers, json=search_data, timeout=10)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"成功! 获取到 {len(result.get('jobs', []))} 个岗位")

    return token

def main():
    """主测试函数"""
    print("="*60)
    print("集成测试开始")
    print("="*60)

    # 检查是否已有服务器运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"检测到服务器已在运行 (状态: {response.status_code})")
        server_running = True
    except:
        server_running = False
        print("未检测到运行中的服务器，将启动测试服务器...")

    server = None
    if not server_running:
        server = ServerManager()
        if not server.start():
            print("服务器启动失败，退出测试")
            return

    try:
        # 等待服务器就绪
        if not wait_for_server():
            print("服务器未在预期时间内响应")
            return

        # 测试匿名搜索
        test_anonymous_search()

        # 测试登录和配置
        test_login_and_config()

        print("\n" + "="*60)
        print("集成测试完成!")
        print("="*60)

    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if server:
            server.stop()

if __name__ == "__main__":
    main()