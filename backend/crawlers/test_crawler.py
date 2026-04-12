"""
测试爬虫 - 用于验证爬虫基类功能

这是一个示例爬虫，用于测试爬虫框架的基本功能
它不访问真实网站，而是返回模拟数据
"""

import asyncio
from typing import Dict, List, Any, Optional, Generator, Union
from datetime import datetime
import random

from .base import BaseCrawler, JobItem


class TestCrawler(BaseCrawler):
    """测试爬虫 - 用于验证爬虫框架功能"""

    platform = "test"
    base_url = "https://test.example.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.test_data = [
            {
                "id": "test_job_001",
                "title": "Python开发实习生",
                "company": "测试公司A",
                "location": "北京",
                "job_type": "实习",
                "salary_min": 8000,
                "salary_max": 12000,
                "education": "本科",
                "experience": "应届生",
                "description": "这是一个测试岗位描述",
                "requirements": ["熟悉Python", "了解Web开发"],
                "skills": ["Python", "Django", "MySQL"],
                "posted_date": "2026-04-10",
                "source": "other",
                "url": "https://test.example.com/job/001"
            },
            {
                "id": "test_job_002",
                "title": "前端开发实习生",
                "company": "测试公司B",
                "location": "上海",
                "job_type": "实习",
                "salary_min": 7000,
                "salary_max": 11000,
                "education": "本科",
                "experience": "应届生",
                "description": "前端开发测试岗位",
                "requirements": ["熟悉Vue/React", "了解HTML/CSS"],
                "skills": ["Vue.js", "React", "TypeScript"],
                "posted_date": "2026-04-11",
                "source": "other",
                "url": "https://test.example.com/job/002"
            },
            {
                "id": "test_job_003",
                "title": "数据分析实习生",
                "company": "测试公司C",
                "location": "深圳",
                "job_type": "实习",
                "salary_min": 7500,
                "salary_max": 13000,
                "education": "硕士",
                "experience": "1年以内",
                "description": "数据分析测试岗位",
                "requirements": ["熟悉Python数据分析", "掌握SQL"],
                "skills": ["Python", "Pandas", "SQL", "数据分析"],
                "posted_date": "2026-04-09",
                "source": "other",
                "url": "https://test.example.com/job/003"
            }
        ]

    def search_jobs(
        self,
        keyword: Union[str, List[str]],
        city: Optional[str] = None,
        page: int = 1,
        **filters
    ) -> Generator[JobItem, None, None]:
        """
        搜索岗位（模拟）

        Args:
            keyword: 搜索关键词（字符串或字符串列表）
            city: 城市
            page: 页码

        Yields:
            JobItem对象
        """
        self.logger.info(f"搜索岗位: keyword={keyword}, city={city}, page={page}")

        # 模拟网络延迟
        self.before_request()

        # 处理keyword参数：如果是列表则连接为字符串
        if isinstance(keyword, list):
            keyword_str = " ".join(keyword)
        else:
            keyword_str = str(keyword)

        keyword_lower = keyword_str.lower()

        # 根据关键词过滤数据
        filtered_data = []
        for job in self.test_data:
            if keyword_lower in job["title"].lower() or any(kw in " ".join(job["skills"]).lower() for kw in keyword_lower.split()):
                if not city or city in job["location"]:
                    filtered_data.append(job)

        # 分页逻辑（模拟）
        page_size = 10
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_data = filtered_data[start_idx:end_idx]

        for job_data in paged_data:
            yield JobItem(**job_data)

    def parse_job_detail(self, job_id: str) -> Optional[JobItem]:
        """
        获取岗位详情（模拟）

        Args:
            job_id: 岗位ID

        Returns:
            JobItem或None
        """
        self.logger.info(f"获取岗位详情: {job_id}")

        # 模拟网络延迟
        self.before_request()

        for job_data in self.test_data:
            if job_data["id"] == job_id:
                return JobItem(**job_data)

        return None

    def parse_list_page(self, html: str) -> List[Dict[str, Any]]:
        """
        解析列表页（模拟）

        Args:
            html: 页面HTML内容

        Returns:
            岗位数据列表
        """
        self.logger.info("解析列表页")
        return self.test_data.copy()

    def parse_detail_page(self, html: str) -> Dict[str, Any]:
        """
        解析详情页（模拟）

        Args:
            html: 页面HTML内容

        Returns:
            岗位详细数据
        """
        self.logger.info("解析详情页")
        # 模拟解析HTML
        if "001" in html:
            return self.test_data[0]
        elif "002" in html:
            return self.test_data[1]
        else:
            return self.test_data[2]


class MockCrawler(TestCrawler):
    """模拟爬虫 - 用于单元测试"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mock_requests = []
        self.mock_responses = {}

    def set_mock_response(self, url: str, response: Dict):
        """设置模拟响应"""
        self.mock_responses[url] = response

    async def mock_request(self, url: str) -> Dict:
        """模拟网络请求"""
        self.mock_requests.append(url)
        self.before_request()

        if url in self.mock_responses:
            return self.mock_responses[url]

        # 默认返回空数据
        return {"error": "Not found", "url": url}

    def get_mock_stats(self) -> Dict:
        """获取模拟统计"""
        return {
            "request_count": len(self.mock_requests),
            "unique_urls": len(set(self.mock_requests))
        }


# 便捷函数
def create_test_crawler(**kwargs) -> TestCrawler:
    """创建测试爬虫"""
    return TestCrawler(**kwargs)


def create_mock_crawler(**kwargs) -> MockCrawler:
    """创建模拟爬虫"""
    return MockCrawler(**kwargs)


if __name__ == "__main__":
    # 简单测试
    async def main():
        crawler = TestCrawler()

        print("测试搜索功能:")
        jobs = list(crawler.search_jobs("开发", "北京"))
        print(f"找到 {len(jobs)} 个岗位")
        for job in jobs[:2]:  # 只显示前2个
            print(f"  - {job.title} ({job.company}, {job.location})")

        print("\n测试获取详情:")
        job_detail = crawler.parse_job_detail("test_job_001")
        if job_detail:
            print(f"  岗位: {job_detail.title}")
            print(f"  公司: {job_detail.company}")
            print(f"  技能: {', '.join(job_detail.skills)}")

        print("\n测试数据清洗:")
        test_data = {
            "salary": "8k-12k",
            "location": "北京市海淀区",
            "education": "大学本科",
            "experience": "经验1-3年"
        }
        cleaned = crawler.clean_data(test_data)
        print(f"  清洗后数据: {cleaned}")

        print("\n测试统计信息:")
        stats = crawler.get_stats()
        print(f"  请求统计: {stats}")

    asyncio.run(main())