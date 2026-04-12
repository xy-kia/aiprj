import subprocess
import time
import requests
import sys
import os

# 启动服务器
print("Starting server...")
proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
try:
    # 等待服务器启动
    time.sleep(3)

    # 测试端点 - 直接访问 backend_app（无挂载）
    url = "http://localhost:8001/v1/ai-config"
    print(f"Testing {url}")
    resp = requests.get(url, timeout=5)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
    # 测试挂载后的路径（如果服务器通过 launcher.py 启动，应该使用 /api/v1/ai-config）
    # 但这里我们只测试 backend_app 本身
except Exception as e:
    print(f"Error: {e}")
finally:
    # 终止服务器
    proc.terminate()
    proc.wait()
    print("Server stopped")