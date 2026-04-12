"""
爬虫基类 - 定义所有爬虫的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Generator
from dataclasses import dataclass
from datetime import datetime
import logging
import time
import random


@dataclass
class JobItem:
    """岗位数据标准格式"""
    id: str
    title: str
    company: str
    location: str
    job_type: str = "实习"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    education: str = "不限"
    experience: str = "不限"
    description: str = ""
    requirements: List[str] = None
    skills: List[str] = None
    posted_date: Optional[str] = None
    source: str = ""
    url: str = ""
    raw_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.requirements is None:
            self.requirements = []
        if self.skills is None:
            self.skills = []
        if self.raw_data is None:
            self.raw_data = {}


class BaseCrawler(ABC):
    """
    爬虫基类
    所有具体爬虫应继承此类并实现抽象方法
    """

    # 平台标识
    platform: str = ""

    # 基础配置
    base_url: str = ""
    headers: Dict[str, str] = None

    # 反爬配置
    min_delay: float = 1.0
    max_delay: float = 5.0
    max_retries: int = 3

    def __init__(self, **kwargs):
        """
        初始化爬虫

        Args:
            proxy_pool: 代理IP池实例
            cookie_manager: Cookie管理器实例
            use_proxy: 是否使用代理
            use_random_ua: 是否使用随机User-Agent
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.proxy_pool = kwargs.get("proxy_pool")
        self.cookie_manager = kwargs.get("cookie_manager")
        self.use_proxy = kwargs.get("use_proxy", False)
        self.use_random_ua = kwargs.get("use_random_ua", True)

        self.session = None
        self._request_count = 0
        self._failed_count = 0

    @abstractmethod
    def search_jobs(
        self,
        keyword: str,
        city: Optional[str] = None,
        page: int = 1,
        **filters
    ) -> Generator[JobItem, None, None]:
        """
        搜索岗位

        Args:
            keyword: 搜索关键词
            city: 城市名称
            page: 页码
            **filters: 额外过滤条件

        Yields:
            JobItem: 岗位数据
        """
        pass

    @abstractmethod
    def parse_job_detail(self, job_id: str) -> Optional[JobItem]:
        """
        获取岗位详情

        Args:
            job_id: 岗位ID

        Returns:
            JobItem或None
        """
        pass

    @abstractmethod
    def parse_list_page(self, html: str) -> List[Dict[str, Any]]:
        """
        解析列表页

        Args:
            html: 页面HTML内容

        Returns:
            岗位数据列表
        """
        pass

    @abstractmethod
    def parse_detail_page(self, html: str) -> Dict[str, Any]:
        """
        解析详情页

        Args:
            html: 页面HTML内容

        Returns:
            岗位详细数据
        """
        pass

    def before_request(self):
        """请求前的准备工作"""
        # 随机延时
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

        # 更新headers
        if self.use_random_ua:
            self._update_user_agent()

    def after_request(self, response):
        """请求后的处理"""
        self._request_count += 1

        # 保存Cookie
        if self.cookie_manager and hasattr(response, 'cookies'):
            self.cookie_manager.update_cookies(response.cookies)

    def on_request_error(self, error: Exception):
        """请求错误处理"""
        self._failed_count += 1
        self.logger.error(f"Request failed: {error}")

        # 切换代理
        if self.use_proxy and self.proxy_pool:
            self.proxy_pool.mark_failed(self._current_proxy)
            self._current_proxy = self.proxy_pool.get_proxy()

    def _update_user_agent(self):
        """更新User-Agent"""
        try:
            from fake_useragent import UserAgent
            ua = UserAgent()
            if self.headers is None:
                self.headers = {}
            self.headers['User-Agent'] = ua.random
        except ImportError:
            self.headers['User-Agent'] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

    def clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        清洗数据

        Args:
            data: 原始数据

        Returns:
            清洗后的数据
        """
        from .cleaning_rules import clean_job_data
        return clean_job_data(data)

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证数据

        Args:
            data: 待验证数据

        Returns:
            是否有效
        """
        from .validators import validate_job_data
        return validate_job_data(data)

    def get_stats(self) -> Dict[str, int]:
        """获取爬虫统计信息"""
        return {
            "requests": self._request_count,
            "failed": self._failed_count,
            "success_rate": (
                (self._request_count - self._failed_count) / self._request_count
                if self._request_count > 0 else 0
            )
        }

    def reset_stats(self):
        """重置统计"""
        self._request_count = 0
        self._failed_count = 0


class PlaywrightCrawler(BaseCrawler):
    """
    基于Playwright的爬虫基类
    适用于需要JS渲染的页面
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.browser = None
        self.context = None
        self.page = None
        self.headless = kwargs.get("headless", True)

    async def init_browser(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self.browser = await self._playwright.chromium.launch(
            headless=self.headless
        )
        self.context = await self.browser.new_context(
            user_agent=self.headers.get('User-Agent') if self.headers else None
        )
        self.page = await self.context.new_page()

    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, '_playwright'):
            await self._playwright.stop()

    async def fetch_page(self, url: str) -> str:
        """
        获取页面内容

        Args:
            url: 页面URL

        Returns:
            HTML内容
        """
        if not self.page:
            await self.init_browser()

        self.before_request()

        try:
            response = await self.page.goto(url, wait_until="networkidle")
            html = await self.page.content()
            self.after_request(response)
            return html
        except Exception as e:
            self.on_request_error(e)
            raise


class APICrawler(BaseCrawler):
    """
    基于API的爬虫基类
    适用于直接调用接口的情况
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_base: str = ""
        self.api_key: Optional[str] = kwargs.get("api_key")

    def get_api_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.headers:
            headers.update(self.headers)
        return headers

    async def fetch_api(self, endpoint: str, params: Dict = None) -> Dict:
        """
        调用API

        Args:
            endpoint: API端点
            params: 请求参数

        Returns:
            JSON响应
        """
        import httpx

        self.before_request()

        url = f"{self.api_base}{endpoint}"
        proxy = self.proxy_pool.get_proxy() if self.use_proxy else None

        try:
            async with httpx.AsyncClient(proxies=proxy) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=self.get_api_headers(),
                    timeout=30.0
                )
                response.raise_for_status()
                self.after_request(response)
                return response.json()
        except Exception as e:
            self.on_request_error(e)
            raise
