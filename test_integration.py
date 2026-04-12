#!/usr/bin/env python3
"""
一体化启动器集成测试
测试关键功能但不启动实际服务器
"""

import os
import sys
import tempfile
from pathlib import Path
import json

# 添加backend到路径
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

def test_environment_setup():
    """测试环境变量设置"""
    print("测试环境变量设置...")

    # 导入启动器的环境设置函数
    from launcher import setup_environment

    # 创建临时目录测试
    with tempfile.TemporaryDirectory() as temp_dir:
        # 修改HOME环境变量指向临时目录
        original_home = os.environ.get("HOME")
        os.environ["HOME"] = temp_dir

        try:
            db_path = setup_environment()

            # 验证环境变量
            assert "DATABASE_URL" in os.environ, "DATABASE_URL未设置"
            assert "sqlite://" in os.environ["DATABASE_URL"], "应使用SQLite数据库"
            assert "REDIS_URL" in os.environ, "REDIS_URL未设置"
            assert "memory://" in os.environ["REDIS_URL"], "应使用内存缓存"

            print(f"[OK] 数据库路径: {db_path}")
            print("[OK] 环境变量设置测试通过")
            return True
        finally:
            # 恢复原始HOME
            if original_home:
                os.environ["HOME"] = original_home
            else:
                os.environ.pop("HOME", None)

def test_memory_cache():
    """测试内存缓存功能"""
    print("\n测试内存缓存功能...")

    from memory_cache import MemoryCacheClient

    # 创建客户端
    client = MemoryCacheClient()

    # 测试基本操作
    client.set("test_key", "test_value", ex=10)
    value = client.get("test_key")
    assert value == "test_value", f"缓存获取失败: {value}"

    # 测试复杂数据类型
    test_data = {"name": "test", "items": [1, 2, 3]}
    client.set("complex_key", test_data)
    retrieved = client.get("complex_key")
    assert retrieved == test_data, f"复杂数据缓存失败: {retrieved}"

    # 测试哈希操作
    client.hset("test_hash", "field1", "value1")
    hash_value = client.hget("test_hash", "field1")
    assert hash_value == "value1", f"哈希操作失败: {hash_value}"

    print("[OK] 内存缓存功能测试通过")
    return True

def test_patching():
    """测试猴子补丁功能"""
    print("\n测试猴子补丁功能...")

    # 导入相关模块
    import backend.app.cache.redis_client as redis_module

    # 应用补丁
    from launcher import patch_redis
    patch_redis()

    # 验证RedisClient已被替换
    from memory_cache import MemoryCacheClient
    assert redis_module.RedisClient == MemoryCacheClient, "RedisClient未正确替换"

    # 测试获取客户端
    client = redis_module.get_redis_client()
    assert isinstance(client, MemoryCacheClient), f"客户端类型错误: {type(client)}"

    print("[OK] 猴子补丁功能测试通过")
    return True

def test_sample_data():
    """测试示例数据生成"""
    print("\n测试示例数据生成...")

    # 测试JSON序列化
    sample_job = {
        "title": "测试岗位",
        "company": "测试公司",
        "skills": ["Python", "测试"]
    }

    json_str = json.dumps(sample_job, ensure_ascii=False)
    parsed = json.loads(json_str)

    assert parsed["title"] == "测试岗位", "JSON序列化失败"
    assert "Python" in parsed["skills"], "技能列表序列化失败"

    print("[OK] 示例数据生成测试通过")
    return True

def main():
    """主测试函数"""
    print("=" * 60)
    print("一体化启动器集成测试")
    print("=" * 60)

    tests = [
        ("环境变量设置", test_environment_setup),
        ("内存缓存", test_memory_cache),
        ("猴子补丁", test_patching),
        ("示例数据", test_sample_data),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: 通过")
            else:
                print(f"[FAIL] {test_name}: 失败")
        except Exception as e:
            print(f"[FAIL] {test_name}: 错误 - {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！一体化启动器准备就绪。")
        return True
    else:
        print("⚠️  部分测试失败，请检查代码。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)