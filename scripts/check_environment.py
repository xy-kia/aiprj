#!/usr/bin/env python3
"""
环境检查脚本
验证开发环境是否配置正确
"""

import sys
import subprocess
import os

def run_command(cmd):
    """运行命令并返回输出"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def check_python():
    """检查Python版本"""
    print("检查 Python 3.9+...", end=" ")
    success, out, err = run_command("python --version")
    if success:
        # 解析版本号
        version_str = out.split()[1]
        major, minor, _ = map(int, version_str.split('.'))
        if major == 3 and minor >= 9:
            print(f"✅ {out}")
            return True
        else:
            print(f"❌ 版本过低: {out}，需要 Python 3.9+")
            return False
    else:
        print(f"❌ 未安装Python")
        return False

def check_node():
    """检查Node.js版本"""
    print("检查 Node.js 18+...", end=" ")
    success, out, err = run_command("node --version")
    if success:
        version_str = out.strip('v')
        major = int(version_str.split('.')[0])
        if major >= 18:
            print(f"✅ {out}")
            return True
        else:
            print(f"❌ 版本过低: {out}，需要 Node.js 18+")
            return False
    else:
        print("❌ 未安装Node.js")
        return False

def check_mysql():
    """检查MySQL安装"""
    print("检查 MySQL 安装...", end=" ")
    success, out, err = run_command("mysql --version")
    if success:
        print(f"✅ {out}")
        return True
    else:
        print("❌ 未安装MySQL或未在PATH中")
        return False

def check_redis():
    """检查Redis安装"""
    print("检查 Redis 安装...", end=" ")
    success, out, err = run_command("redis-cli --version")
    if success:
        print(f"✅ {out}")
        return True
    else:
        print("❌ 未安装Redis或未在PATH中")
        return False

def check_docker():
    """检查Docker"""
    print("检查 Docker...", end=" ")
    success, out, err = run_command("docker --version")
    if success:
        print(f"✅ {out}")
        return True
    else:
        print("❌ 未安装Docker")
        return False

def check_git():
    """检查Git"""
    print("检查 Git...", end=" ")
    success, out, err = run_command("git --version")
    if success:
        print(f"✅ {out}")
        return True
    else:
        print("❌ 未安装Git")
        return False

def check_backend_deps():
    """检查后端依赖"""
    print("检查后端依赖...", end=" ")
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import redis
        print("✅ 已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        return False

def check_frontend_deps():
    """检查前端依赖（通过package.json）"""
    print("检查前端依赖...", end=" ")
    if os.path.exists("frontend/node_modules"):
        print("✅ node_modules存在")
        return True
    else:
        print("⚠️  node_modules未安装，请运行 npm install")
        return False

def main():
    print("=" * 50)
    print("环境配置检查")
    print("=" * 50)

    checks = [
        ("Python", check_python()),
        ("Node.js", check_node()),
        ("MySQL", check_mysql()),
        ("Redis", check_redis()),
        ("Docker", check_docker()),
        ("Git", check_git()),
        ("后端依赖", check_backend_deps()),
        ("前端依赖", check_frontend_deps()),
    ]

    print("=" * 50)
    passed = sum(1 for _, status in checks if status)
    total = len(checks)

    if passed == total:
        print(f"✅ 所有检查通过 ({passed}/{total})")
        print("✅ 所有服务就绪！")
    else:
        print(f"⚠️  部分检查未通过 ({passed}/{total})")
        print("请根据上述提示解决问题后重试")

    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()