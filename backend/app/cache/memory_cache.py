#!/usr/bin/env python3
"""
内存缓存模块 - 用于替代Redis的简单内存缓存实现
"""

import time
import threading
from typing import Any, Optional, Dict, List, Set, Union
import logging

logger = logging.getLogger(__name__)


class MemoryCacheClient:
    """内存缓存客户端，模拟Redis客户端接口"""

    def __init__(self, host: str = "memory", port: int = 6379, **kwargs):
        self.host = host
        self.port = port
        self._cache: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._connected = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get(self, key: str) -> Optional[str]:
        """获取键值"""
        with self._lock:
            self._clean_expired()
            if key in self._cache:
                value = self._cache[key]
                # 转换为字符串，模拟Redis的行为
                if isinstance(value, (int, float)):
                    return str(value)
                return value
            return None

    def set(self, key: str, value: Any, ex: Optional[int] = None, px: Optional[int] = None) -> bool:
        """设置键值"""
        with self._lock:
            self._cache[key] = value
            if ex or px:
                expiry = ex or (px / 1000 if px else None)
                if expiry:
                    self._expiry[key] = time.time() + expiry
            return True

    def delete(self, *keys: str) -> int:
        """删除键"""
        with self._lock:
            deleted = 0
            for key in keys:
                if key in self._cache:
                    del self._cache[key]
                    if key in self._expiry:
                        del self._expiry[key]
                    deleted += 1
            return deleted

    def exists(self, *keys: str) -> int:
        """检查键是否存在"""
        with self._lock:
            self._clean_expired()
            return sum(1 for key in keys if key in self._cache)

    def expire(self, key: str, time_in_seconds: int) -> bool:
        """设置过期时间"""
        with self._lock:
            if key in self._cache:
                self._expiry[key] = time.time() + time_in_seconds
                return True
            return False

    def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        with self._lock:
            if key not in self._cache:
                return -2
            if key not in self._expiry:
                return -1
            ttl_value = self._expiry[key] - time.time()
            return max(0, int(ttl_value))

    def incr(self, key: str, amount: int = 1) -> int:
        """递增键值"""
        with self._lock:
            current = self.get(key)
            if current is None:
                new_value = amount
            else:
                try:
                    new_value = int(current) + amount
                except ValueError:
                    new_value = amount
            self.set(key, new_value)
            return new_value

    def decr(self, key: str, amount: int = 1) -> int:
        """递减键值"""
        return self.incr(key, -amount)

    def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的键"""
        with self._lock:
            self._clean_expired()
            import fnmatch
            return [key for key in self._cache.keys() if fnmatch.fnmatch(key, pattern)]

    def flushdb(self) -> bool:
        """清空数据库"""
        with self._lock:
            self._cache.clear()
            self._expiry.clear()
            return True

    def ping(self) -> bool:
        """检查连接"""
        return self._connected

    def close(self):
        """关闭连接"""
        self._connected = False

    def _clean_expired(self):
        """清理过期的键"""
        current_time = time.time()
        expired_keys = [key for key, expiry in self._expiry.items() if expiry < current_time]
        for key in expired_keys:
            if key in self._cache:
                del self._cache[key]
            del self._expiry[key]

    # Redis哈希表操作
    def hset(self, name: str, key: str, value: Any) -> int:
        """设置哈希字段"""
        with self._lock:
            if name not in self._cache:
                self._cache[name] = {}
            self._cache[name][key] = value
            return 1

    def hget(self, name: str, key: str) -> Optional[str]:
        """获取哈希字段"""
        with self._lock:
            if name in self._cache and key in self._cache[name]:
                value = self._cache[name][key]
                if isinstance(value, (int, float)):
                    return str(value)
                return value
            return None

    def hgetall(self, name: str) -> Dict[str, str]:
        """获取所有哈希字段"""
        with self._lock:
            if name in self._cache:
                result = {}
                for k, v in self._cache[name].items():
                    if isinstance(v, (int, float)):
                        result[k] = str(v)
                    else:
                        result[k] = v
                return result
            return {}

    # Redis列表操作
    def lpush(self, name: str, *values: Any) -> int:
        """从左侧推入列表"""
        with self._lock:
            if name not in self._cache:
                self._cache[name] = []
            self._cache[name] = list(values) + self._cache[name]
            return len(self._cache[name])

    def rpush(self, name: str, *values: Any) -> int:
        """从右侧推入列表"""
        with self._lock:
            if name not in self._cache:
                self._cache[name] = []
            self._cache[name].extend(values)
            return len(self._cache[name])

    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """获取列表范围"""
        with self._lock:
            if name not in self._cache:
                return []
            lst = self._cache[name]
            # Redis的end包含，Python切片不包含
            if end == -1:
                end = len(lst)
            else:
                end = min(end + 1, len(lst))
            start = max(0, start)
            return [str(item) for item in lst[start:end]]


# 全局内存缓存客户端实例
_global_client: Optional[MemoryCacheClient] = None
_client_lock = threading.RLock()


def get_memory_cache_client() -> MemoryCacheClient:
    """获取全局内存缓存客户端实例"""
    global _global_client
    with _client_lock:
        if _global_client is None:
            _global_client = MemoryCacheClient()
            logger.info("创建内存缓存客户端")
        return _global_client


def check_memory_cache_connection() -> bool:
    """检查内存缓存连接"""
    try:
        client = get_memory_cache_client()
        return client.ping()
    except Exception as e:
        logger.error(f"内存缓存连接检查失败: {e}")
        return False


# 测试函数
if __name__ == "__main__":
    # 简单测试
    client = get_memory_cache_client()

    # 测试基本操作
    client.set("test_key", "test_value", ex=10)
    print(f"Get test_key: {client.get('test_key')}")
    print(f"Exists test_key: {client.exists('test_key')}")
    print(f"TTL test_key: {client.ttl('test_key')}")

    # 测试哈希
    client.hset("test_hash", "field1", "value1")
    print(f"HGet test_hash field1: {client.hget('test_hash', 'field1')}")

    # 测试列表
    client.lpush("test_list", "item1", "item2")
    print(f"LRange test_list 0 -1: {client.lrange('test_list', 0, -1)}")

    print("内存缓存测试完成")
