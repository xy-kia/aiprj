"""
爬虫工具模块 - 封装HTTP请求、重试机制、超时处理
"""

import asyncio
import logging
from typing import Dict, Optional, Callable, Any
from functools import wraps
import random
import time

import httpx


logger = logging.getLogger(__name__)


class RequestUtils:
    """请求工具类"""

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_RETRIES = 3
    DEFAULT_BACKOFF = 2.0

    def __init__(
        self,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF,
        proxy: Optional[str] = None,
        headers: Optional[Dict] = None
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.proxy = proxy
        self.headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self.headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def get(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """GET请求"""
        return await self._request_with_retry(
            "GET", url, params=params, headers=headers, **kwargs
        )

    async def post(
        self,
        url: str,
        data: Optional[Dict] = None,
        json: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """POST请求"""
        return await self._request_with_retry(
            "POST", url, data=data, json=json, headers=headers, **kwargs
        )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        带重试的请求

        Args:
            method: HTTP方法
            url: 请求URL
            **kwargs: 额外参数

        Returns:
            Response对象

        Raises:
            httpx.HTTPError: 重试耗尽后仍失败
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                client = self._client or httpx.AsyncClient(
                    timeout=self.timeout,
                    headers=self.headers,
                    proxies=self.proxy
                )

                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                # HTTP错误，某些状态码不需要重试
                if e.response.status_code in (401, 403, 404):
                    raise
                last_exception = e
                logger.warning(f"HTTP {e.response.status_code} on {url}")

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                logger.warning(f"Connection error on {url}: {e}")

            except Exception as e:
                last_exception = e
                logger.warning(f"Request error on {url}: {e}")

            # 计算退避时间
            if attempt < self.max_retries:
                sleep_time = self.backoff_factor * (2 ** attempt)
                sleep_time += random.uniform(0, 1)  # 添加抖动
                logger.info(f"Retrying in {sleep_time:.2f}s (attempt {attempt + 2}/{self.max_retries + 1})")
                await asyncio.sleep(sleep_time)

        # 重试耗尽
        raise last_exception


def retry(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器

    Args:
        max_retries: 最大重试次数
        backoff_factor: 退避系数
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} failed (attempt {attempt + 1}): {e}")

                    if attempt < max_retries:
                        sleep_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)

                        if on_retry:
                            on_retry(attempt, sleep_time, e)

                        await asyncio.sleep(sleep_time)

            raise last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} failed (attempt {attempt + 1}): {e}")

                    if attempt < max_retries:
                        sleep_time = backoff_factor * (2 ** attempt) + random.uniform(0, 1)

                        if on_retry:
                            on_retry(attempt, sleep_time, e)

                        time.sleep(sleep_time)

            raise last_exception

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def random_delay(min_seconds: float = 1.0, max_seconds: float = 5.0):
    """
    随机延时装饰器

    Args:
        min_seconds: 最小延时
        max_seconds: 最大延时
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            delay = random.uniform(min_seconds, max_seconds)
            logger.debug(f"Delaying for {delay:.2f}s")
            await asyncio.sleep(delay)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            delay = random.uniform(min_seconds, max_seconds)
            logger.debug(f"Delaying for {delay:.2f}s")
            time.sleep(delay)
            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class RateLimiter:
    """请求速率限制器"""

    def __init__(self, max_requests: int = 10, time_window: float = 60.0):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            time_window: 时间窗口(秒)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: list = []

    async def acquire(self):
        """获取请求许可"""
        now = time.time()

        # 清理过期请求记录
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < self.time_window
        ]

        if len(self.requests) >= self.max_requests:
            # 需要等待
            oldest = self.requests[0]
            wait_time = self.time_window - (now - oldest)
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

        self.requests.append(time.time())


def create_session(
    headers: Optional[Dict] = None,
    cookies: Optional[Dict] = None,
    proxy: Optional[str] = None
) -> httpx.AsyncClient:
    """
    创建HTTP会话

    Args:
        headers: 默认请求头
        cookies: 默认Cookie
        proxy: 代理地址

    Returns:
        AsyncClient实例
    """
    default_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }

    if headers:
        default_headers.update(headers)

    return httpx.AsyncClient(
        headers=default_headers,
        cookies=cookies,
        proxies=proxy,
        follow_redirects=True,
        timeout=30.0
    )


def parse_cookie_string(cookie_str: str) -> Dict[str, str]:
    """
    解析Cookie字符串

    Args:
        cookie_str: Cookie字符串，如 "a=1; b=2"

    Returns:
        Cookie字典
    """
    cookies = {}
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            cookies[key] = value
    return cookies


def build_cookie_string(cookies: Dict[str, str]) -> str:
    """
    构建Cookie字符串

    Args:
        cookies: Cookie字典

    Returns:
        Cookie字符串
    """
    return '; '.join(f"{k}={v}" for k, v in cookies.items())
