"""
爬虫测试 - 验证基础爬虫功能

测试BaseCrawler及其子类的基本功能
包括数据清洗、验证、请求处理等
"""

import sys
import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.crawlers import (
    BaseCrawler, TestCrawler, MockCrawler,
    JobItem, clean_job_data, validate_job_data,
    create_test_crawler, create_mock_crawler
)


class TestJobItem(unittest.TestCase):
    """测试JobItem数据类"""

    def test_job_item_creation(self):
        """测试JobItem创建"""
        job = JobItem(
            id="test_001",
            title="测试岗位",
            company="测试公司",
            location="北京",
            job_type="实习",
            salary_min=8000,
            salary_max=12000,
            education="本科",
            experience="应届生",
            description="测试描述",
            requirements=["要求1", "要求2"],
            skills=["技能1", "技能2"],
            posted_date="2026-04-11",
            source="test",
            url="https://test.com/job/001"
        )

        self.assertEqual(job.id, "test_001")
        self.assertEqual(job.title, "测试岗位")
        self.assertEqual(job.company, "测试公司")
        self.assertEqual(job.location, "北京")
        self.assertEqual(job.job_type, "实习")
        self.assertEqual(job.salary_min, 8000)
        self.assertEqual(job.salary_max, 12000)
        self.assertEqual(job.education, "本科")
        self.assertEqual(job.experience, "应届生")
        self.assertEqual(job.description, "测试描述")
        self.assertEqual(job.requirements, ["要求1", "要求2"])
        self.assertEqual(job.skills, ["技能1", "技能2"])
        self.assertEqual(job.posted_date, "2026-04-11")
        self.assertEqual(job.source, "test")
        self.assertEqual(job.url, "https://test.com/job/001")

    def test_job_item_defaults(self):
        """测试JobItem默认值"""
        job = JobItem(
            id="test_002",
            title="测试岗位",
            company="测试公司",
            location="上海",
            job_type="实习",
            posted_date="2026-04-11",
            source="test",
            url="https://test.com/job/002"
        )

        # 测试默认值
        self.assertEqual(job.salary_min, None)
        self.assertEqual(job.salary_max, None)
        self.assertEqual(job.education, "不限")
        self.assertEqual(job.experience, "不限")
        self.assertEqual(job.description, "")
        self.assertEqual(job.requirements, [])
        self.assertEqual(job.skills, [])
        self.assertIsNotNone(job.raw_data)


class TestBaseCrawler(unittest.TestCase):
    """测试BaseCrawler基类"""

    def setUp(self):
        """测试前准备"""
        # 创建一个测试爬虫实例
        # BaseCrawler是抽象类，不能直接实例化，使用TestCrawler代替
        self.crawler = TestCrawler()

    def test_base_crawler_initialization(self):
        """测试BaseCrawler初始化"""
        # 使用TestCrawler实例，检查其属性
        self.assertEqual(self.crawler.platform, "test")
        self.assertEqual(self.crawler.base_url, "https://test.example.com")
        self.assertIsNone(self.crawler.headers)
        self.assertEqual(self.crawler.min_delay, 1.0)
        self.assertEqual(self.crawler.max_delay, 5.0)
        self.assertEqual(self.crawler.max_retries, 3)
        self.assertEqual(self.crawler._request_count, 0)
        self.assertEqual(self.crawler._failed_count, 0)

    def test_get_stats(self):
        """测试获取统计信息"""
        stats = self.crawler.get_stats()
        self.assertEqual(stats["requests"], 0)
        self.assertEqual(stats["failed"], 0)
        self.assertEqual(stats["success_rate"], 0)

        # 模拟一些请求
        self.crawler._request_count = 10
        self.crawler._failed_count = 2
        stats = self.crawler.get_stats()
        self.assertEqual(stats["requests"], 10)
        self.assertEqual(stats["failed"], 2)
        self.assertEqual(stats["success_rate"], 0.8)

    def test_reset_stats(self):
        """测试重置统计"""
        self.crawler._request_count = 10
        self.crawler._failed_count = 3
        self.crawler.reset_stats()
        self.assertEqual(self.crawler._request_count, 0)
        self.assertEqual(self.crawler._failed_count, 0)


class TestTestCrawler(unittest.TestCase):
    """测试TestCrawler"""

    def setUp(self):
        """测试前准备"""
        self.crawler = TestCrawler()

    def test_test_crawler_initialization(self):
        """测试TestCrawler初始化"""
        self.assertEqual(self.crawler.platform, "test")
        self.assertEqual(self.crawler.base_url, "https://test.example.com")
        self.assertIsNotNone(self.crawler.test_data)
        self.assertEqual(len(self.crawler.test_data), 3)

    def test_search_jobs(self):
        """测试搜索岗位"""
        # 测试无过滤搜索
        jobs = list(self.crawler.search_jobs(""))
        self.assertEqual(len(jobs), 3)

        # 测试关键词搜索
        jobs = list(self.crawler.search_jobs("Python"))
        self.assertEqual(len(jobs), 2)  # Python开发和数据分析

        # 测试城市过滤
        jobs = list(self.crawler.search_jobs("", "北京"))
        self.assertEqual(len(jobs), 1)

        # 测试关键词+城市过滤
        jobs = list(self.crawler.search_jobs("开发", "北京"))
        self.assertEqual(len(jobs), 1)

    def test_parse_job_detail(self):
        """测试获取岗位详情"""
        job = self.crawler.parse_job_detail("test_job_001")
        self.assertIsNotNone(job)
        self.assertEqual(job.id, "test_job_001")
        self.assertEqual(job.title, "Python开发实习生")
        self.assertEqual(job.company, "测试公司A")

        # 测试不存在的ID
        job = self.crawler.parse_job_detail("non_existent")
        self.assertIsNone(job)

    def test_parse_list_page(self):
        """测试解析列表页"""
        # 模拟HTML内容
        html = "<html>测试页面</html>"
        result = self.crawler.parse_list_page(html)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["title"], "Python开发实习生")

    def test_parse_detail_page(self):
        """测试解析详情页"""
        # 测试不同ID的HTML
        job1 = self.crawler.parse_detail_page("<html>test_job_001</html>")
        self.assertEqual(job1["id"], "test_job_001")

        job2 = self.crawler.parse_detail_page("<html>test_job_002</html>")
        self.assertEqual(job2["id"], "test_job_002")

        job3 = self.crawler.parse_detail_page("<html>other</html>")
        self.assertEqual(job3["id"], "test_job_003")

    def test_data_cleaning(self):
        """测试数据清洗"""
        test_data = {
            "salary": "8k-12k",
            "location": "北京市海淀区",
            "education": "大学本科",
            "experience": "经验1-3年",
            "company_size": "100-499人"
        }

        cleaned = self.crawler.clean_data(test_data)
        self.assertIn("salary_min", cleaned)
        self.assertIn("salary_max", cleaned)
        self.assertEqual(cleaned["location"], "北京")
        self.assertEqual(cleaned["education"], "本科")
        self.assertEqual(cleaned["experience"], "1-3年")
        self.assertEqual(cleaned["company_size"], "150-500人")

    def test_data_validation(self):
        """测试数据验证"""
        # 测试有效数据
        valid_data = {
            "id": "test_id_12345",
            "title": "测试岗位",
            "company": "测试公司",
            "location": "北京",
            "job_type": "实习",
            "posted_date": "2026-04-11",
            "source": "other",
            "url": "https://test.com/job/123"
        }
        self.assertTrue(self.crawler.validate_data(valid_data))

        # 测试无效数据（缺少必填字段）
        invalid_data = {
            "id": "test",
            "title": "测试"
        }
        self.assertFalse(self.crawler.validate_data(invalid_data))


class TestCleaningRules(unittest.TestCase):
    """测试数据清洗规则"""

    def test_clean_salary(self):
        """测试薪资清洗"""
        from backend.crawlers.cleaning_rules import clean_salary

        # 测试面议
        min_sal, max_sal, months = clean_salary("面议")
        self.assertIsNone(min_sal)
        self.assertIsNone(max_sal)
        self.assertIsNone(months)

        # 测试k单位
        min_sal, max_sal, months = clean_salary("8k-12k")
        self.assertEqual(min_sal, 8000)
        self.assertEqual(max_sal, 12000)

        # 测试万单位
        min_sal, max_sal, months = clean_salary("0.8-1.2万")
        self.assertEqual(min_sal, 8000)
        self.assertEqual(max_sal, 12000)

        # 测试带月数
        min_sal, max_sal, months = clean_salary("8k-12k·14薪")
        self.assertEqual(min_sal, 8000)
        self.assertEqual(max_sal, 12000)
        self.assertEqual(months, 14)

    def test_clean_location(self):
        """测试地点清洗"""
        from backend.crawlers.cleaning_rules import clean_location

        # 测试带后缀
        self.assertEqual(clean_location("北京市"), "北京")
        self.assertEqual(clean_location("上海市浦东新区"), "上海")
        self.assertEqual(clean_location("广州市天河区"), "广州")

        # 测试特殊格式
        self.assertEqual(clean_location("北京·海淀区"), "北京")
        self.assertEqual(clean_location("上海-浦东"), "上海")

        # 测试别名
        self.assertEqual(clean_location("魔都"), "上海")
        self.assertEqual(clean_location("帝都"), "北京")

    def test_clean_education(self):
        """测试学历清洗"""
        from backend.crawlers.cleaning_rules import clean_education

        self.assertEqual(clean_education("大学本科"), "本科")
        self.assertEqual(clean_education("硕士研究生"), "硕士")
        self.assertEqual(clean_education("大专"), "大专")
        self.assertEqual(clean_education("学历不限"), "不限")
        self.assertEqual(clean_education(""), "不限")

    def test_clean_job_data(self):
        """测试完整数据清洗"""
        raw_data = {
            "salary": "8k-12k",
            "salary_text": "8k-12k",
            "location": "北京市海淀区",
            "education": "大学本科",
            "experience": "经验1-3年",
            "company_size": "100-499人",
            "description": "  测试  描述  ",
            "skills": ["Python", "Python", "Java", ""]
        }

        cleaned = clean_job_data(raw_data)
        self.assertEqual(cleaned["salary_min"], 8000)
        self.assertEqual(cleaned["salary_max"], 12000)
        self.assertEqual(cleaned["location"], "北京")
        self.assertEqual(cleaned["education"], "本科")
        self.assertEqual(cleaned["experience"], "1-3年")
        self.assertEqual(cleaned["company_size"], "150-500人")
        self.assertEqual(cleaned["description"], "测试 描述")
        self.assertEqual(set(cleaned["skills"]), {"Python", "Java"})


class TestValidators(unittest.TestCase):
    """测试数据验证器"""

    def test_validate_job_data(self):
        """测试岗位数据验证"""
        # 测试有效数据
        valid_data = {
            "id": "test_id_12345",
            "title": "测试岗位标题",
            "company": "测试公司",
            "location": "北京",
            "job_type": "实习",
            "posted_date": "2026-04-11",
            "source": "other",
            "url": "https://test.com/job/123"
        }
        self.assertTrue(validate_job_data(valid_data))

        # 测试无效岗位类型
        invalid_data = valid_data.copy()
        invalid_data["job_type"] = "无效类型"
        self.assertFalse(validate_job_data(invalid_data))

        # 测试无效学历
        invalid_data = valid_data.copy()
        invalid_data["education"] = "无效学历"
        self.assertFalse(validate_job_data(invalid_data))

        # 测试无效URL
        invalid_data = valid_data.copy()
        invalid_data["url"] = "不是有效的URL"
        self.assertFalse(validate_job_data(invalid_data))

        # 测试薪资范围
        invalid_data = valid_data.copy()
        invalid_data["salary_min"] = 15000
        invalid_data["salary_max"] = 10000  # 最低大于最高
        self.assertFalse(validate_job_data(invalid_data))


class TestMockCrawler(unittest.TestCase):
    """测试MockCrawler"""

    def setUp(self):
        self.crawler = MockCrawler()

    def test_mock_functionality(self):
        """测试模拟功能"""
        # 设置模拟响应
        self.crawler.set_mock_response("https://test.com/api", {"data": "test"})

        # 测试模拟请求
        response = asyncio.run(self.crawler.mock_request("https://test.com/api"))
        self.assertEqual(response["data"], "test")

        # 测试默认响应
        response = asyncio.run(self.crawler.mock_request("https://unknown.com"))
        self.assertEqual(response["error"], "Not found")

        # 测试统计
        stats = self.crawler.get_mock_stats()
        self.assertEqual(stats["request_count"], 2)
        self.assertEqual(stats["unique_urls"], 2)


class TestIntegration(unittest.TestCase):
    """测试集成功能"""

    def test_create_test_crawler(self):
        """测试创建测试爬虫"""
        crawler = create_test_crawler()
        self.assertIsInstance(crawler, TestCrawler)
        self.assertEqual(crawler.platform, "test")

    def test_create_mock_crawler(self):
        """测试创建模拟爬虫"""
        crawler = create_mock_crawler()
        self.assertIsInstance(crawler, MockCrawler)

    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        crawler = TestCrawler()

        # 1. 搜索岗位
        jobs = list(crawler.search_jobs("开发"))
        self.assertGreater(len(jobs), 0)

        # 2. 获取第一个岗位的详情
        if jobs:
            job_id = jobs[0].id
            job_detail = crawler.parse_job_detail(job_id)
            self.assertIsNotNone(job_detail)
            self.assertEqual(job_detail.id, job_id)

            # 3. 验证数据
            self.assertTrue(validate_job_data(job_detail.__dict__))

            # 4. 检查统计
            stats = crawler.get_stats()
            self.assertGreaterEqual(stats["requests"], 0)


if __name__ == "__main__":
    # 运行测试
    print("运行爬虫测试...")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestJobItem))
    suite.addTests(loader.loadTestsFromTestCase(TestBaseCrawler))
    suite.addTests(loader.loadTestsFromTestCase(TestTestCrawler))
    suite.addTests(loader.loadTestsFromTestCase(TestCleaningRules))
    suite.addTests(loader.loadTestsFromTestCase(TestValidators))
    suite.addTests(loader.loadTestsFromTestCase(TestMockCrawler))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出结果
    print(f"\n测试结果:")
    print(f"  运行测试: {result.testsRun}")
    print(f"  通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")

    if result.wasSuccessful():
        print("✅ 所有测试通过!")
        sys.exit(0)
    else:
        print("❌ 测试失败!")
        sys.exit(1)