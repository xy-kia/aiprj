"""
Redis缓存客户端封装
支持连接池、重试机制、序列化
"""

import json
import pickle
import logging
from typing import Any, Optional, Union, Dict, List, Tuple
from functools import wraps
import redis
from redis.connection import ConnectionPool
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
import time

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis客户端封装"""

    def __init__(self, url: Optional[str] = None, **kwargs):
        """
        初始化Redis客户端

        Args:
            url: Redis连接URL，默认为配置中的REDIS_URL
            **kwargs: 额外的连接参数
        """
        self.url = url or settings.REDIS_URL
        self.pool_size = kwargs.pop('pool_size', settings.REDIS_POOL_SIZE)

        # 连接池配置
        pool_kwargs = {
            'max_connections': self.pool_size,
            'retry': Retry(ExponentialBackoff(), 3),  # 重试3次
            'health_check_interval': 30,  # 健康检查间隔
            'socket_keepalive': True,
            **kwargs
        }

        # 创建连接池
        self.pool = ConnectionPool.from_url(self.url, **pool_kwargs)

        # 创建Redis客户端
        self.client = redis.Redis(connection_pool=self.pool, decode_responses=True)

        logger.info(f"Redis client initialized with pool size: {self.pool_size}")

    def check_connection(self) -> bool:
        """检查Redis连接是否正常"""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis connection check failed: {e}")
            return False

    def close(self):
        """关闭连接池"""
        self.pool.disconnect()
        logger.info("Redis connection pool closed")

    # 基本的键操作
    def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除键"""
        try:
            return bool(self.client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False

    def expire(self, key: str, time: int) -> bool:
        """设置键的过期时间（秒）"""
        try:
            return self.client.expire(key, time)
        except Exception as e:
            logger.error(f"Redis expire failed for key {key}: {e}")
            return False

    def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Redis ttl failed for key {key}: {e}")
            return -2

    # 字符串操作
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        设置字符串值

        Args:
            key: 键
            value: 值（自动序列化）
            ex: 过期时间（秒）
        """
        try:
            serialized = self._serialize(value)
            if ex:
                return self.client.setex(key, ex, serialized)
            else:
                return self.client.set(key, serialized)
        except Exception as e:
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取字符串值

        Args:
            key: 键
            default: 默认值（当键不存在时返回）
        """
        try:
            value = self.client.get(key)
            if value is None:
                return default
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Redis get failed for key {key}: {e}")
            return default

    # 哈希操作
    def hset(self, name: str, key: str, value: Any) -> bool:
        """设置哈希字段"""
        try:
            serialized = self._serialize(value)
            return bool(self.client.hset(name, key, serialized))
        except Exception as e:
            logger.error(f"Redis hset failed for hash {name}, field {key}: {e}")
            return False

    def hget(self, name: str, key: str, default: Any = None) -> Any:
        """获取哈希字段"""
        try:
            value = self.client.hget(name, key)
            if value is None:
                return default
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Redis hget failed for hash {name}, field {key}: {e}")
            return default

    def hgetall(self, name: str) -> Dict[str, Any]:
        """获取所有哈希字段"""
        try:
            result = self.client.hgetall(name)
            return {k: self._deserialize(v) for k, v in result.items()}
        except Exception as e:
            logger.error(f"Redis hgetall failed for hash {name}: {e}")
            return {}

    # 列表操作
    def lpush(self, name: str, *values: Any) -> int:
        """从左侧推入列表"""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self.client.lpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis lpush failed for list {name}: {e}")
            return 0

    def rpush(self, name: str, *values: Any) -> int:
        """从右侧推入列表"""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self.client.rpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis rpush failed for list {name}: {e}")
            return 0

    def lrange(self, name: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围"""
        try:
            values = self.client.lrange(name, start, end)
            return [self._deserialize(v) for v in values]
        except Exception as e:
            logger.error(f"Redis lrange failed for list {name}: {e}")
            return []

    # 集合操作
    def sadd(self, name: str, *values: Any) -> int:
        """添加集合元素"""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self.client.sadd(name, *serialized_values)
        except Exception as e:
            logger.error(f"Redis sadd failed for set {name}: {e}")
            return 0

    def smembers(self, name: str) -> List[Any]:
        """获取所有集合元素"""
        try:
            values = self.client.smembers(name)
            return [self._deserialize(v) for v in values]
        except Exception as e:
            logger.error(f"Redis smembers failed for set {name}: {e}")
            return []

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

    # 序列化/反序列化
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


# 全局Redis客户端实例
_redis_client: Optional[RedisClient] = None


def get_redis_client() -> RedisClient:
    """获取Redis客户端实例（单例）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
    return _redis_client


def check_redis_connection() -> bool:
    """检查Redis连接是否正常"""
    try:
        client = get_redis_client()
        return client.check_connection()
    except Exception as e:
        logger.error(f"Redis connection check failed: {e}")
        return False