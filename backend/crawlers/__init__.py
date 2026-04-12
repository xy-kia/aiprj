"""
爬虫模块

提供各类招聘网站的爬虫实现
"""

from .base import BaseCrawler, PlaywrightCrawler, APICrawler, JobItem
from .utils import RequestUtils, retry, random_delay, RateLimiter
from .cleaning_rules import clean_job_data, clean_salary, clean_location, clean_education
from .validators import validate_job_data, JobValidator
from .cookie_manager import CookieManager, RotatingCookieManager
from .proxy_pool import ProxyPool, Proxy, create_proxy_pool
from .test_crawler import TestCrawler, MockCrawler, create_test_crawler, create_mock_crawler

__all__ = [
    # 基类
    "BaseCrawler",
    "PlaywrightCrawler",
    "APICrawler",
    "JobItem",

    # 测试爬虫
    "TestCrawler",
    "MockCrawler",
    "create_test_crawler",
    "create_mock_crawler",

    # 工具
    "RequestUtils",
    "retry",
    "random_delay",
    "RateLimiter",

    # 清洗规则
    "clean_job_data",
    "clean_salary",
    "clean_location",
    "clean_education",

    # 验证器
    "validate_job_data",
    "JobValidator",

    # Cookie管理
    "CookieManager",
    "RotatingCookieManager",

    # 代理池
    "ProxyPool",
    "Proxy",
    "create_proxy_pool",
]
