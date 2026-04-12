import subprocess
import time
import requests
import sys
import os

print("Starting server via launcher.py...")
# 启动服务器，使用相同的端口8000
proc = subprocess.Popen([sys.executable, "launcher.py"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True)

try:
    # 等待服务器启动
    print("Waiting for server to start...")
    time.sleep(5)

    # 测试端点
    url = "http://localhost:8000/api/v1/ai-config"
    print(f"Testing {url}")
    for i in range(3):
        try:
            resp = requests.get(url, timeout=5)
            print(f"Status: {resp.status_code}")
            print(f"Response: {resp.text}")
            if resp.status_code == 200:
                print("✅ 端点访问成功！")
                break
        except Exception as e:
            print(f"Attempt {i+1} failed: {e}")
            time.sleep(2)
    else:
        print("❌ 端点访问失败")

    # 保持服务器运行，等待用户中断
    print("Server is running. Press Ctrl+C to stop.")
    proc.wait()
except KeyboardInterrupt:
    print("Stopping server...")
    proc.terminate()
    proc.wait()
except Exception as e:
    print(f"Error: {e}")
    proc.terminate()
    proc.wait()