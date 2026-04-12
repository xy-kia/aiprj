#!/usr/bin/env python3
"""
测试调度器
"""

import sys
import os
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlers.test_crawler import TestCrawler
from app.core.search_scheduler import create_search_scheduler

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_scheduler():
    """测试调度器"""
    print("测试调度器...")

    # 创建爬虫实例
    crawlers = [TestCrawler()]

    # 创建调度器
    scheduler = create_search_scheduler(crawlers)

    # 执行搜索
    keyword = "Python"
    city = "北京"

    print(f"搜索: {keyword}, 城市: {city}")

    jobs = await scheduler.search(keyword=keyword, city=city, page_limit=1)

    print(f"获取到 {len(jobs)} 个岗位")

    for i, job in enumerate(jobs[:5]):
        print(f"{i+1}. {job.title} - {job.company} ({job.location})")

    return len(jobs) > 0

async def main():
    success = await test_scheduler()
    print(f"\n测试结果: {'成功' if success else '失败'}")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)