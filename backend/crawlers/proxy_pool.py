"""
代理IP池 - 管理和轮换代理IP
"""

import random
import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ProxyStatus(Enum):
    """代理状态"""
    ACTIVE = "active"       # 可用
    INACTIVE = "inactive"   # 不可用
    CHECKING = "checking"   # 检测中
    FAILED = "failed"       # 失败过多


@dataclass
class Proxy:
    """代理IP数据类"""
    host: str
    port: int
    protocol: str = "http"  # http/https/socks5
    username: Optional[str] = None
    password: Optional[str] = None

    # 状态信息
    status: ProxyStatus = ProxyStatus.ACTIVE
    fail_count: int = 0
    success_count: int = 0
    response_time: float = 0.0
    last_used: Optional[datetime] = None
    last_checked: Optional[datetime] = None

    # 元数据
    source: str = ""  # 来源
    location: str = ""  # 地理位置
    tags: List[str] = field(default_factory=list)

    @property
    def url(self) -> str:
        """获取代理URL"""
        if self.username and self.password:
            return (
                f"{self.protocol}://{self.username}:{self.password}"
                f"@{self.host}:{self.port}"
            )
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def is_available(self) -> bool:
        """检查是否可用"""
        if self.status == ProxyStatus.FAILED:
            return False
        if self.fail_count >= 5:
            return False
        return True

    def record_success(self, response_time: float):
        """记录成功"""
        self.success_count += 1
        self.response_time = response_time
        self.last_used = datetime.now()
        if self.fail_count > 0:
            self.fail_count = 0  # 重置失败计数

    def record_fail(self):
        """记录失败"""
        self.fail_count += 1
        self.last_used = datetime.now()

        if self.fail_count >= 5:
            self.status = ProxyStatus.FAILED
            logger.warning(f"Proxy {self.host}:{self.port} marked as failed")


class ProxyPool:
    """
    代理IP池

    功能：
    1. 管理代理IP列表
    2. 自动轮换代理
    3. 检测代理可用性
    4. 失败自动切换
    """

    def __init__(
        self,
        max_fail_count: int = 5,
        check_interval: int = 300,  # 5分钟检测一次
        test_url: str = "http://httpbin.org/ip"
    ):
        """
        初始化代理池

        Args:
            max_fail_count: 最大失败次数
            check_interval: 检测间隔(秒)
            test_url: 代理测试URL
        """
        self.proxies: List[Proxy] = []
        self.max_fail_count = max_fail_count
        self.check_interval = check_interval
        self.test_url = test_url

        self._current_index = 0
        self._lock = asyncio.Lock()

    def add_proxy(self, proxy: Proxy):
        """添加代理"""
        self.proxies.append(proxy)
        logger.debug(f"Added proxy: {proxy.host}:{proxy.port}")

    def add_proxies(self, proxies: List[Proxy]):
        """批量添加代理"""
        for proxy in proxies:
            self.add_proxy(proxy)

    def add_from_dict(self, proxy_dict: Dict[str, Any]):
        """
        从字典添加代理

        Args:
            proxy_dict: 代理配置字典
        """
        proxy = Proxy(
            host=proxy_dict["host"],
            port=proxy_dict["port"],
            protocol=proxy_dict.get("protocol", "http"),
            username=proxy_dict.get("username"),
            password=proxy_dict.get("password"),
            source=proxy_dict.get("source", ""),
            location=proxy_dict.get("location", "")
        )
        self.add_proxy(proxy)

    def add_from_url(self, proxy_url: str):
        """
        从URL添加代理

        Args:
            proxy_url: 代理URL，如 http://user:pass@host:port
        """
        from urllib.parse import urlparse

        parsed = urlparse(proxy_url)

        proxy = Proxy(
            host=parsed.hostname,
            port=parsed.port,
            protocol=parsed.scheme,
            username=parsed.username,
            password=parsed.password
        )
        self.add_proxy(proxy)

    def get_proxy(self, strategy: str = "round_robin") -> Optional[Proxy]:
        """
        获取代理

        Args:
            strategy: 选择策略 (round_robin/random/best)

        Returns:
            Proxy对象或None
        """
        available = [p for p in self.proxies if p.is_available]

        if not available:
            logger.warning("No available proxies in pool")
            return None

        if strategy == "random":
            return random.choice(available)

        elif strategy == "best":
            # 选择响应时间最短且失败最少的
            return min(available, key=lambda p: (
                p.fail_count,
                p.response_time if p.response_time > 0 else float('inf')
            ))

        else:  # round_robin
            proxy = available[self._current_index % len(available)]
            self._current_index += 1
            return proxy

    def mark_failed(self, proxy: Proxy):
        """
        标记代理失败

        Args:
            proxy: 失败的代理
        """
        proxy.record_fail()

    def mark_success(self, proxy: Proxy, response_time: float):
        """
        标记代理成功

        Args:
            proxy: 成功的代理
            response_time: 响应时间
        """
        proxy.record_success(response_time)

    async def check_proxy(self, proxy: Proxy) -> bool:
        """
        检测代理可用性

        Args:
            proxy: 待检测代理

        Returns:
            是否可用
        """
        import httpx

        proxy.status = ProxyStatus.CHECKING
        proxy.last_checked = datetime.now()

        try:
            start = asyncio.get_event_loop().time()

            async with httpx.AsyncClient(
                proxies=proxy.url,
                timeout=10.0
            ) as client:
                response = await client.get(self.test_url)
                response_time = asyncio.get_event_loop().time() - start

                if response.status_code == 200:
                    proxy.status = ProxyStatus.ACTIVE
                    proxy.record_success(response_time)
                    logger.debug(f"Proxy {proxy.host} is active")
                    return True

        except Exception as e:
            logger.debug(f"Proxy {proxy.host} check failed: {e}")

        proxy.status = ProxyStatus.INACTIVE
        return False

    async def check_all(self):
        """检测所有代理"""
        tasks = [self.check_proxy(p) for p in self.proxies]
        await asyncio.gather(*tasks, return_exceptions=True)

        active_count = sum(1 for p in self.proxies if p.status == ProxyStatus.ACTIVE)
        logger.info(f"Proxy check complete: {active_count}/{len(self.proxies)} active")

    def get_stats(self) -> Dict[str, Any]:
        """获取代理池统计"""
        total = len(self.proxies)
        active = sum(1 for p in self.proxies if p.status == ProxyStatus.ACTIVE)
        failed = sum(1 for p in self.proxies if p.status == ProxyStatus.FAILED)
        inactive = total - active - failed

        return {
            "total": total,
            "active": active,
            "inactive": inactive,
            "failed": failed,
            "availability": active / total if total > 0 else 0
        }

    def remove_failed(self):
        """移除失败代理"""
        before = len(self.proxies)
        self.proxies = [p for p in self.proxies if p.status != ProxyStatus.FAILED]
        after = len(self.proxies)
        logger.info(f"Removed {before - after} failed proxies")

    def clear(self):
        """清空代理池"""
        self.proxies.clear()
        self._current_index = 0


class FreeProxyPool(ProxyPool):
    """
    免费代理池

    自动获取免费代理IP
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sources = [
            "http://www.89ip.cn/",
            "https://www.zdaye.com/",
        ]

    async def fetch_free_proxies(self) -> List[Proxy]:
        """
        获取免费代理

        Returns:
            代理列表
        """
        # 这里实现具体的免费代理抓取逻辑
        # 示例：返回一些公共代理
        free_proxies = []

        # 注意：这些只是示例，实际使用时需要替换为可用的免费代理
        # 或者实现从免费代理网站抓取的逻辑

        logger.warning("Free proxy fetching not fully implemented")
        return free_proxies


class ProxyRotator:
    """
    代理轮换器

    简化的代理管理，支持上下文管理器
    """

    def __init__(self, proxy_pool: ProxyPool, strategy: str = "round_robin"):
        self.pool = proxy_pool
        self.strategy = strategy
        self._current: Optional[Proxy] = None

    async def __aenter__(self) -> str:
        self._current = self.pool.get_proxy(self.strategy)
        if not self._current:
            raise RuntimeError("No proxy available")
        return self._current.url

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type and self._current:
            self.pool.mark_failed(self._current)
        elif self._current:
            # 假设成功，记录响应时间0（实际应该从请求中获取）
            self.pool.mark_success(self._current, 0)


# 便捷函数
def create_proxy_pool(
    proxy_list: Optional[List[str]] = None,
    max_fail_count: int = 5
) -> ProxyPool:
    """
    创建代理池

    Args:
        proxy_list: 代理URL列表
        max_fail_count: 最大失败次数

    Returns:
        ProxyPool实例
    """
    pool = ProxyPool(max_fail_count=max_fail_count)

    if proxy_list:
        for proxy_url in proxy_list:
            try:
                pool.add_from_url(proxy_url)
            except Exception as e:
                logger.error(f"Failed to add proxy {proxy_url}: {e}")

    return pool
