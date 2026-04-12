"""
内存缓存客户端 - 替代Redis用于一体化启动
提供与RedisClient兼容的接口，但使用内存存储
"""

import json
import pickle
import logging
from typing import Any, Optional, Union, Dict, List, Tuple
import time
from threading import Lock
from collections import OrderedDict

logger = logging.getLogger(__name__)


class MemoryCacheClient:
    """内存缓存客户端，兼容RedisClient接口"""

    def __init__(self, url: Optional[str] = None, **kwargs):
        """
        初始化内存缓存客户端

        Args:
            url: 连接URL（忽略）
            **kwargs: 额外的参数（忽略）
        """
        self.url = url or "memory://"
        self.pool_size = kwargs.pop('pool_size', 10)

        # 内存存储
        self._store = {}  # 主存储
        self._expiry = {}  # 过期时间
        self._hashes = {}  # 哈希存储
        self._lists = {}  # 列表存储
        self._sets = {}  # 集合存储

        self._lock = Lock()  # 线程安全锁

        logger.info("Memory cache client initialized")
        self._cleanup_expired()  # 启动时清理过期数据

    def check_connection(self) -> bool:
        """检查连接（总是返回True）"""
        return True

    def close(self):
        """关闭连接（清理内存）"""
        with self._lock:
            self._store.clear()
            self._expiry.clear()
            self._hashes.clear()
            self._lists.clear()
            self._sets.clear()
        logger.info("Memory cache closed")

    def _cleanup_expired(self):
        """清理过期的键"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, expiry in self._expiry.items()
                if expiry > 0 and expiry < current_time
            ]

            for key in expired_keys:
                self._delete_key(key)

            logger.debug(f"Cleaned up {len(expired_keys)} expired keys")

    def _delete_key(self, key: str):
        """删除一个键及其所有相关数据"""
        # 从主存储删除
        if key in self._store:
            del self._store[key]

        # 从过期时间删除
        if key in self._expiry:
            del self._expiry[key]

        # 从哈希存储删除
        if key in self._hashes:
            del self._hashes[key]

        # 从列表存储删除
        if key in self._lists:
            del self._lists[key]

        # 从集合存储删除
        if key in self._sets:
            del self._sets[key]

    def _check_expiry(self, key: str) -> bool:
        """检查键是否已过期，如果过期则删除并返回False"""
        if key in self._expiry:
            expiry = self._expiry[key]
            if expiry > 0 and expiry < time.time():
                self._delete_key(key)
                return False
        return True

    # 基本的键操作
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        with self._lock:
            self._cleanup_expired()
            return (
                key in self._store or
                key in self._hashes or
                key in self._lists or
                key in self._sets
            )

    def delete(self, key: str) -> bool:
        """删除键"""
        with self._lock:
            existed = self.exists(key)
            self._delete_key(key)
            return existed

    def expire(self, key: str, ttl: int) -> bool:
        """设置键的过期时间（秒）"""
        with self._lock:
            if self.exists(key):
                self._expiry[key] = time.time() + ttl if ttl > 0 else 0
                return True
            return False

    def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        with self._lock:
            if key not in self._expiry:
                return -1  # 没有设置过期时间
            if not self.exists(key):
                return -2  # 键不存在

            expiry = self._expiry[key]
            if expiry == 0:
                return -1  # 永不过期

            remaining = int(expiry - time.time())
            return max(0, remaining)

    # 字符串操作
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置字符串值

        Args:
            key: 键
            value: 值（自动序列化）
            ex: 过期时间（秒）
        """
        with self._lock:
            # 序列化值
            serialized = self._serialize(value)
            self._store[key] = serialized

            # 设置过期时间
            if ex:
                self._expiry[key] = time.time() + ex
            else:
                self._expiry[key] = 0  # 永不过期

            return True

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取字符串值

        Args:
            key: 键
            default: 默认值（当键不存在时返回）
        """
        with self._lock:
            self._check_expiry(key)

            if key not in self._store:
                return default

            value = self._store[key]
            return self._deserialize(value)

    # 哈希操作
    def hset(self, name: str, key: str, value: Any) -> bool:
        """设置哈希字段"""
        with self._lock:
            if name not in self._hashes:
                self._hashes[name] = {}

            serialized = self._serialize(value)
            self._hashes[name][key] = serialized
            return True

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """获取哈希字段"""
        with self._lock:
            if name not in self._hashes or key not in self._hashes[name]:
                return default

            value = self._hashes[name][key]
            return self._deserialize(value)

    def hgetall(self, name: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        with self._lock:
            if name not in self._hashes:
                return {}

            result = {}
            for key, value in self._hashes[name].items():
                result[key] = self._deserialize(value)
            return result

    # 列表操作
    def lpush(self, name: str, *values: Any) -> int:
        """从左侧推入列表"""
        with self._lock:
            if name not in self._lists:
                self._lists[name] = []

            serialized_values = [self._serialize(v) for v in values]
            self._lists[name] = serialized_values + self._lists[name]
            return len(self._lists[name])

    def rpush(self, name: str, *values: Any) -> int:
        """从右侧推入列表"""
        with self._lock:
            if name not in self._lists:
                self._lists[name] = []

            serialized_values = [self._serialize(v) for v in values]
            self._lists[name].extend(serialized_values)
            return len(self._lists[name])

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围"""
        with self._lock:
            if name not in self._lists:
                return []

            lst = self._lists[name]
            actual_end = end if end >= 0 else len(lst) + end + 1
            slice_values = lst[start:actual_end]

            return [self._deserialize(v) for v in slice_values]

    # 集合操作
    def sadd(self, name: str, *values: Any) -> int:
        """添加集合元素"""
        with self._lock:
            if name not in self._sets:
                self._sets[name] = set()

            serialized_values = {self._serialize(v) for v in values}
            before_len = len(self._sets[name])
            self._sets[name].update(serialized_values)
            return len(self._sets[name]) - before_len

    def smembers(self, name: str) -> List[Any]:
        """获取所有集合元素"""
        with self._lock:
            if name not in self._sets:
                return []

            return [self._deserialize(v) for v in self._sets[name]]

    # 实用方法
    def cache_get_or_set(self, key: str, func: callable, ex: int = 3600, *args, **kwargs) -> Any:
        """
        缓存获取或设置模式

        Args:
            key: 缓存键
            func: 当缓存不存在时调用的函数
            ex: 过期时间（秒）
            *args, **kwargs: 传递给函数的参数

        Returns:
            缓存值或函数返回值
        """
        # 尝试从缓存获取
        cached = self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for key: {key}")
            return cached

        # 缓存未命中，调用函数获取结果
        logger.debug(f"Cache miss for key: {key}")
        result = func(*args, **kwargs)

        # 将结果存入缓存
        if result is not None:
            self.set(key, result, ex=ex)

        return result

    # 序列化/反序列化（与RedisClient保持兼容）
    @staticmethod
    def _serialize(value: Any) -> str:
        """序列化值"""
        if isinstance(value, (str, int, float, bool)) or value is None:
            # 基本类型直接转为字符串
            return str(value)
        else:
            # 复杂类型使用JSON序列化
            try:
                return json.dumps(value, ensure_ascii=False)
            except:
                # 如果JSON失败，使用pickle（二进制）
                return pickle.dumps(value).hex()

    @staticmethod
    def _deserialize(value: Union[str, bytes]) -> Any:
        """反序列化值"""
        if isinstance(value, bytes):
            value = value.decode('utf-8')

        try:
            # 尝试解析为基本类型
            if value.isdigit():
                return int(value)
            elif value.replace('.', '', 1).isdigit() and value.count('.') == 1:
                return float(value)
            elif value.lower() in ('true', 'false'):
                return value.lower() == 'true'
            elif value.lower() == 'none' or value.lower() == 'null':
                return None
        except:
            pass

        # 尝试JSON反序列化
        try:
            return json.loads(value)
        except:
            # 尝试pickle反序列化
            try:
                return pickle.loads(bytes.fromhex(value))
            except:
                # 如果所有方法都失败，返回原始字符串
                return value


# 全局内存缓存客户端实例
_memory_cache_client: Optional[MemoryCacheClient] = None


def get_memory_cache_client() -> MemoryCacheClient:
    """获取内存缓存客户端实例（单例）"""
    global _memory_cache_client
    if _memory_cache_client is None:
        _memory_cache_client = MemoryCacheClient()
    return _memory_cache_client


def check_memory_cache_connection() -> bool:
    """检查内存缓存连接是否正常（总是返回True）"""
    try:
        client = get_memory_cache_client()
        return client.check_connection()
    except Exception as e:
        logger.error(f"Memory cache connection check failed: {e}")
        return True  # 内存缓存不会失败