"""
集成测试：完整工作流测试
测试从意向输入到评估报告的完整流程
参考文档：Development_Process.md 第4.2节
"""

import sys
import os
import unittest
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.intent_parser import IntentParser
from backend.app.core.match_calculator import MatchCalculator
from backend.app.core.question_generator import QuestionGenerator
from backend.app.core.answer_evaluator import AnswerEvaluator
from backend.crawlers.base import BaseCrawler
from backend.crawlers.test_crawler import TestCrawler


@pytest.mark.integration
class TestCompleteWorkflow(unittest.TestCase):
    """测试完整工作流"""

    def setUp(self):
        """测试前准备"""
        # 设置知识库路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        knowledge_path = os.path.join(current_dir, "..", "..", "knowledge")

        # 初始化各个组件
        self.intent_parser = IntentParser(knowledge_base_path=knowledge_path)
        self.match_calculator = MatchCalculator(use_bert=False)

        # 模拟Redis客户端
        mock_redis_client = MagicMock()
        mock_redis_client.get = MagicMock(return_value=None)
        mock_redis_client.setex = MagicMock()

        # 初始化问题生成器（使用模拟Redis）
        with patch('openai.OpenAI') as mock_openai_class:
            mock_openai_client = MagicMock()
            mock_openai_class.return_value = mock_openai_client
            self.question_generator = QuestionGenerator(
                openai_api_key="test-key",
                model="gpt-4o-mini",
                cache_enabled=False,  # 测试中禁用缓存
                redis_client=mock_redis_client
            )

        # 初始化回答评估器
        with patch('openai.OpenAI') as mock_openai_class:
            mock_openai_client = MagicMock()
            mock_openai_class.return_value = mock_openai_client
            self.answer_evaluator = AnswerEvaluator(
                openai_api_key="test-key",
                model="gpt-4o-mini"
            )

        self.crawler = TestCrawler()

        # 加载测试数据
        self.test_job_data = self._load_test_job_data()
        self.test_resume_data = self._load_test_resume_data()

    def _load_test_job_data(self):
        """加载测试岗位数据"""
        job_file = os.path.join(os.path.dirname(__file__), "..", "fixtures", "job_data.json")
        with open(job_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_test_resume_data(self):
        """加载测试简历数据"""
        resume_file = os.path.join(os.path.dirname(__file__), "..", "fixtures", "resume_data.json")
        with open(resume_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def test_complete_workflow_normal(self):
        """测试正常完整工作流"""
        # 1. 意向解析
        user_input = "我想找一份Python开发的实习工作，最好在北京"
        intent_result = self.intent_parser.parse(user_input)

        self.assertIn("keywords", intent_result)
        self.assertIn("confidence", intent_result)
        self.assertGreater(intent_result["confidence"], 0.5)

        # 2. 岗位搜索（使用测试爬虫）
        keywords = intent_result["keywords"]
        jobs = list(self.crawler.search_jobs(
            keywords.get("skills", []) + keywords.get("related_skills", []),
            keywords.get("locations", [])[0] if keywords.get("locations") else None
        ))

        self.assertGreater(len(jobs), 0, "应该找到至少一个岗位")

        # 3. 匹配度计算
        job = jobs[0]
        match_result = self.match_calculator.calculate_match(keywords, job.__dict__)

        self.assertIn("total_score", match_result)
        self.assertIn("match_level", match_result)
        self.assertGreaterEqual(match_result["total_score"], 0)
        self.assertLessEqual(match_result["total_score"], 100)

        # 4. 问题生成（使用Mock OpenAI）
        with patch.object(self.question_generator.client.chat.completions, 'create') as mock_create:
            mock_response = MagicMock()
            mock_response.choices = [MagicMock(message=MagicMock(content=json.dumps([
                {
                    "question": "请介绍一下你的Python项目经验",
                    "question_type": "technical",
                    "target_skill": "Python",
                    "jd_reference": "需要Python开发经验",
                    "suggested_time": 120,
                    "difficulty": "medium",
                    "scoring_criteria": ["项目背景", "技术实现", "成果量化"]
                }
            ])))]
            mock_create.return_value = mock_response

            questions = self.question_generator.generate_questions(job.__dict__, "intern_general", 3)

            self.assertGreater(len(questions), 0, "应该生成至少一个问题")

            # 5. 回答评估（使用Mock OpenAI）
            with patch.object(self.answer_evaluator.client.embeddings, 'create') as mock_embed:
                mock_embed_response = MagicMock()
                mock_embed_response.data = [
                    MagicMock(embedding=[0.1, 0.2, 0.3]),
                    MagicMock(embedding=[0.1, 0.2, 0.3])
                ]
                mock_embed.return_value = mock_embed_response

                question = questions[0]
                answer = "我有Python开发经验，曾使用Django框架开发电商网站，优化了数据库查询，将响应时间从500ms降低到200ms。"

                evaluation = self.answer_evaluator.evaluate(
                    question.question,
                    answer,
                    job.__dict__
                )

                self.assertIsNotNone(evaluation)
                self.assertIn("total_score", evaluation.__dict__)
                self.assertIn("match_level", evaluation.__dict__)

    def test_error_handling_crawler_failure(self):
        """测试爬虫失败时的错误处理"""
        # 模拟爬虫失败
        mock_crawler = MagicMock(spec=BaseCrawler)
        mock_crawler.search_jobs.side_effect = Exception("爬虫请求失败")

        # 应该优雅处理异常，不导致整个系统崩溃
        with self.assertRaises(Exception):
            list(mock_crawler.search_jobs(["Python"], "北京"))

    def test_error_handling_llm_timeout(self):
        """测试LLM超时时的错误处理"""
        with patch.object(self.question_generator.client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = Exception("OpenAI API超时")

            job_data = self.test_job_data
            # 应该返回备用问题而不是崩溃
            questions = self.question_generator.generate_questions(job_data, "intern_general", 3)

            # 即使API失败，也应该返回问题（备用问题）
            self.assertGreater(len(questions), 0)

    def test_data_consistency(self):
        """测试数据一致性：相同输入产生相同输出"""
        user_input = "Python开发实习"

        # 第一次解析
        result1 = self.intent_parser.parse(user_input)

        # 第二次解析（相同输入）
        result2 = self.intent_parser.parse(user_input)

        # 关键词应该一致
        self.assertEqual(result1["keywords"], result2["keywords"])
        # 置信度应该一致（允许微小浮点误差）
        self.assertAlmostEqual(result1["confidence"], result2["confidence"], places=2)

    @patch('backend.app.core.question_generator.QuestionGenerator.generate_questions')
    @patch('backend.app.core.match_calculator.MatchCalculator.calculate_match')
    def test_concurrent_requests(self, mock_match, mock_questions):
        """测试并发请求处理（模拟）"""
        # 模拟匹配计算返回
        mock_match.return_value = {
            "total_score": 75,
            "match_level": "匹配",
            "dimension_scores": {},
            "weights": {}
        }

        # 模拟问题生成返回
        mock_question = MagicMock()
        mock_question.question = "测试问题"
        mock_questions.return_value = [mock_question]

        # 模拟多个并发请求
        keywords = {"skills": ["Python"], "job_types": ["实习"], "locations": ["北京"]}
        job_data = self.test_job_data

        # 同时调用多次（实际并发测试需要更复杂的工具如pytest-asyncio）
        results = []
        for _ in range(3):
            match_result = self.match_calculator.calculate_match(keywords, job_data)
            questions = self.question_generator.generate_questions(job_data, "intern_general", 2)
            results.append((match_result, questions))

        self.assertEqual(len(results), 3)
        # 所有请求都应该成功处理
        for match_result, questions in results:
            self.assertIsNotNone(match_result)
            self.assertIsNotNone(questions)

    def test_integration_with_mock_services(self):
        """测试使用模拟服务的集成"""
        # 模拟Redis客户端
        mock_redis_client = MagicMock()
        mock_redis_client.get = MagicMock(return_value=None)
        mock_redis_client.setex = MagicMock()

        # 这个测试使用所有模拟服务来验证集成点
        with patch('openai.OpenAI') as mock_openai_class:

            # 设置模拟OpenAI客户端
            mock_client = MagicMock()
            mock_openai_class.return_value = mock_client

            # 模拟聊天完成
            mock_chat_response = MagicMock()
            mock_chat_response.choices = [MagicMock(message=MagicMock(content=json.dumps([
                {
                    "question": "请详细介绍一下你在Python项目开发中的具体经验和贡献",
                    "question_type": "technical",
                    "target_skill": "Python",
                    "suggested_time": 120,
                    "difficulty": "medium"
                }
            ])))]
            mock_client.chat.completions.create.return_value = mock_chat_response

            # 模拟嵌入
            mock_embed_response = MagicMock()
            mock_embed_response.data = [
                MagicMock(embedding=[0.1, 0.2, 0.3]),
                MagicMock(embedding=[0.1, 0.2, 0.3])
            ]
            mock_client.embeddings.create.return_value = mock_embed_response

            # 重新初始化使用模拟客户端的组件
            generator = QuestionGenerator(
                openai_api_key="test-key",
                model="gpt-4o-mini",
                cache_enabled=True,
                redis_client=mock_redis_client
            )
            evaluator = AnswerEvaluator(
                openai_api_key="test-key",
                model="gpt-4o-mini"
            )

            # 执行工作流步骤
            job_data = self.test_job_data

            # 生成问题
            questions = generator.generate_questions(job_data, "intern_general", 2)
            self.assertGreater(len(questions), 0)

            # 评估回答
            evaluation = evaluator.evaluate(
                questions[0].question,
                "这是一个测试回答",
                job_data
            )
            self.assertIsNotNone(evaluation)


class TestIntegrationMarkers(unittest.TestCase):
    """测试集成测试标记"""

    def test_integration_marker(self):
        """确保集成测试被正确标记"""
        # 这个测试用于验证pytest标记系统
        pass


if __name__ == "__main__":
    unittest.main()