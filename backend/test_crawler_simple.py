#!/usr/bin/env python3
"""
简单爬虫测试脚本
测试爬虫基本功能
"""

import sys
import os
import asyncio
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlers.test_crawler import TestCrawler
from crawlers.boss_crawler import BOSSCrawler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_test_crawler():
    """测试TestCrawler"""
    print("=" * 50)
    print("测试 TestCrawler")
    print("=" * 50)

    crawler = TestCrawler()

    # 测试搜索
    print("搜索关键词: 'Python'")
    jobs = list(crawler.search_jobs("Python"))
    print(f"找到 {len(jobs)} 个岗位")
    for job in jobs[:3]:  # 显示前3个
        print(f"  - {job.title} ({job.company}, {job.location})")

    # 测试详情
    if jobs:
        job_detail = crawler.parse_job_detail(jobs[0].id)
        if job_detail:
            print(f"\n获取详情成功: {job_detail.title}")
            print(f"  技能: {', '.join(job_detail.skills)}")

    return len(jobs) > 0

async def test_boss_crawler_mock():
    """测试BOSS直聘爬虫（模拟模式）"""
    print("\n" + "=" * 50)
    print("测试 BOSSCrawler（模拟）")
    print("=" * 50)

    # 创建爬虫实例，使用headless=True
    crawler = BOSSCrawler(headless=True)

    # 测试解析逻辑（不实际访问网络）
    print("测试解析函数...")

    # 创建一个模拟HTML，包含window.__INITIAL_STATE__
    mock_html = """
    <html>
    <script>
    window.__INITIAL_STATE__ = {
        "jobList": {
            "list": [
                {
                    "encryptId": "test123",
                    "jobName": "Python开发实习生",
                    "brandName": "测试公司",
                    "cityName": "北京",
                    "salaryDesc": "8-10K",
                    "jobExperience": "经验不限",
                    "jobDegree": "本科",
                    "skills": ["Python", "Django"],
                    "jobDescription": "岗位描述"
                }
            ]
        }
    };
    </script>
    </html>
    """

    try:
        jobs = crawler.parse_list_page(mock_html)
        print(f"解析到 {len(jobs)} 个岗位")
        for job in jobs:
            print(f"  - {job.get('title', 'N/A')} ({job.get('company', 'N/A')})")

        # 测试数据清洗
        if jobs:
            cleaned = crawler.clean_data(jobs[0])
            print(f"\n清洗后数据:")
            print(f"  标题: {cleaned.get('title')}")
            print(f"  薪资范围: {cleaned.get('salary_min')}-{cleaned.get('salary_max')}")

        return True
    except Exception as e:
        print(f"解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_boss_crawler_real():
    """测试BOSS直聘爬虫（真实网络请求，谨慎使用）"""
    print("\n" + "=" * 50)
    print("测试 BOSSCrawler（真实请求）")
    print("=" * 50)

    print("警告: 这将访问真实网站，可能触发反爬措施")
    response = input("是否继续? (y/N): ")
    if response.lower() != 'y':
        print("跳过真实请求测试")
        return None

    crawler = BOSSCrawler(headless=True)

    try:
        # 初始化浏览器
        print("初始化浏览器...")
        await crawler.init_browser()

        # 搜索一个简单的关键词
        keyword = "实习"
        city = "北京"
        page = 1

        print(f"搜索: {keyword}, 城市: {city}, 页码: {page}")

        # 构建搜索URL
        query_params = crawler._build_search_params(keyword, city, page, {})
        search_url = f"{crawler.search_url}?{query_params}"
        print(f"搜索URL: {search_url}")

        # 获取页面
        print("获取页面...")
        html = await crawler.fetch_page(search_url)

        print(f"获取到HTML长度: {len(html)}")

        # 解析
        jobs = crawler.parse_list_page(html)
        print(f"解析到 {len(jobs)} 个岗位")

        if jobs:
            for i, job_data in enumerate(jobs[:5]):
                print(f"{i+1}. {job_data.get('title')} - {job_data.get('company')}")

        # 关闭浏览器
        await crawler.close_browser()

        return len(jobs) > 0

    except Exception as e:
        print(f"真实请求失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("爬虫测试开始")

    # 1. 测试TestCrawler
    test1 = await test_test_crawler()

    # 2. 测试BOSS直聘解析逻辑
    test2 = await test_boss_crawler_mock()

    # 3. 测试真实请求（可选）
    test3 = await test_boss_crawler_real()

    print("\n" + "=" * 50)
    print("测试结果总结")
    print("=" * 50)
    print(f"TestCrawler: {'✅ 通过' if test1 else '❌ 失败'}")
    print(f"BOSSCrawler解析: {'✅ 通过' if test2 else '❌ 失败'}")
    if test3 is not None:
        print(f"BOSSCrawler真实请求: {'✅ 通过' if test3 else '❌ 失败'}")
    else:
        print(f"BOSSCrawler真实请求: 跳过")

    # 总体结果
    all_passed = test1 and test2 and (test3 is None or test3)
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)