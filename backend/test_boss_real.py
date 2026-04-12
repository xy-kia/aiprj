#!/usr/bin/env python3
"""
诊断BOSS直聘爬虫
"""

import sys
import os
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crawlers.boss_crawler import BOSSCrawler

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_boss_crawler():
    """测试BOSS直聘爬虫"""
    print("=" * 60)
    print("诊断 BOSSCrawler")
    print("=" * 60)

    crawler = BOSSCrawler(headless=True, use_proxy=False)

    try:
        # 初始化浏览器
        print("1. 初始化浏览器...")
        await crawler.init_browser()
        print("   ✅ 浏览器初始化成功")

        # 构建搜索URL
        keyword = "实习"
        city = "北京"
        page = 1

        print(f"2. 构建搜索参数: keyword={keyword}, city={city}, page={page}")
        query_params = crawler._build_search_params(keyword, city, page, {})
        search_url = f"{crawler.search_url}?{query_params}"
        print(f"   搜索URL: {search_url}")

        # 获取页面
        print("3. 获取页面...")
        html = await crawler.fetch_page(search_url)
        print(f"   ✅ 获取到HTML，长度: {len(html)}")

        # 保存HTML用于调试
        debug_html_path = "debug_boss_page.html"
        with open(debug_html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"   HTML已保存到: {debug_html_path}")

        # 解析页面
        print("4. 解析页面...")
        jobs = crawler.parse_list_page(html)
        print(f"   ✅ 解析到 {len(jobs)} 个岗位")

        if jobs:
            print("   前5个岗位:")
            for i, job in enumerate(jobs[:5]):
                print(f"     {i+1}. {job.get('title', 'N/A')} - {job.get('company', 'N/A')}")

            # 测试创建JobItem
            print("5. 创建JobItem...")
            job_item = crawler._create_job_item(jobs[0])
            print(f"   ✅ 创建成功: {job_item.title}")
            print(f"       公司: {job_item.company}")
            print(f"       地点: {job_item.location}")
            print(f"       薪资: {job_item.salary_min}-{job_item.salary_max}")
            print(f"       技能: {job_item.skills}")
        else:
            print("   ⚠️  未解析到任何岗位")
            # 检查HTML内容
            print("   检查HTML中是否包含岗位数据...")
            if 'window.__INITIAL_STATE__' in html:
                print("   ✅ HTML中包含 window.__INITIAL_STATE__")
                # 提取并显示部分JSON
                import re
                match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;', html, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    print(f"   JSON长度: {len(json_str)}")
                    # 尝试解析
                    import json
                    try:
                        data = json.loads(json_str)
                        print(f"   JSON解析成功，键: {list(data.keys())}")
                        # 搜索jobs相关键
                        def find_keys(obj, prefix=""):
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    if 'job' in key.lower() or 'list' in key.lower():
                                        print(f"     发现关键键: {prefix}{key}")
                                    find_keys(value, f"{prefix}{key}.")
                            elif isinstance(obj, list):
                                if len(obj) > 0:
                                    find_keys(obj[0], f"{prefix}[0].")
                        find_keys(data)
                    except json.JSONDecodeError as e:
                        print(f"   JSON解析失败: {e}")
            else:
                print("   ❌ HTML中未找到 window.__INITIAL_STATE__")

        # 关闭浏览器
        print("6. 关闭浏览器...")
        await crawler.close_browser()
        print("   ✅ 浏览器关闭成功")

        return len(jobs) > 0

    except Exception as e:
        print(f"❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("开始诊断BOSS直聘爬虫...")
    success = await test_boss_crawler()

    print("\n" + "=" * 60)
    print("诊断结果: " + ("✅ 成功" if success else "❌ 失败"))
    print("=" * 60)

    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n用户中断")
        sys.exit(1)