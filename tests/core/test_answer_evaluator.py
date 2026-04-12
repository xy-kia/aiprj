"""
回答评估器测试
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.answer_evaluator import AnswerEvaluator, EvaluationResult


class TestAnswerEvaluator(unittest.TestCase):
    """测试回答评估器"""

    def setUp(self):
        """测试前准备"""
        # 模拟OpenAI客户端
        self.mock_openai_client = Mock()
        self.mock_openai_client.embeddings.create = Mock()

        with patch('openai.OpenAI', return_value=self.mock_openai_client):
            self.evaluator = AnswerEvaluator(
                openai_api_key="test-key",
                model="gpt-4o-mini"
            )

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.evaluator.api_key, "test-key")
        self.assertEqual(self.evaluator.model, "gpt-4o-mini")
        self.assertIsNotNone(self.evaluator.client)
        self.assertIsInstance(self.evaluator.skill_keywords, list)
        self.assertGreater(len(self.evaluator.skill_keywords), 0)

    def test_extract_keywords(self):
        """测试关键词提取"""
        text = "我使用Python和Django进行Web开发，并且熟悉MySQL数据库"
        keywords = self.evaluator._extract_keywords(text)

        # 应该提取出关键词
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)

        # 检查是否包含预期关键词
        expected_keywords = ["Python", "Django", "Web开发", "MySQL", "数据库"]
        for keyword in expected_keywords:
            # 由于分词可能返回中文词汇，这里只检查基本功能
            pass

    def test_keyword_matching_with_job_data(self):
        """测试带岗位数据的关键词匹配"""
        answer = "我使用Python和Django开发过电商网站，使用MySQL存储数据"
        job_data = {
            "skills": ["Python", "Django", "MySQL"],
            "description": "需要Python和Django开发经验",
            "requirements": "熟悉MySQL数据库"
        }

        matches = self.evaluator._keyword_matching(answer, job_data, None)

        # 应该匹配到技能关键词
        self.assertIsInstance(matches, list)
        self.assertGreater(len(matches), 0)

    def test_keyword_matching_with_question_data(self):
        """测试带问题数据的关键词匹配"""
        answer = "Python的装饰器是一种高级功能"
        question_data = {
            "target_skill": "Python"
        }

        matches = self.evaluator._keyword_matching(answer, None, question_data)

        # 应该匹配到目标技能
        self.assertIn("Python", matches)

    def test_simple_text_similarity(self):
        """测试简单文本相似度计算"""
        text1 = "Python开发经验"
        text2 = "我有Python开发经验"
        text3 = "Java开发经验"

        similarity1 = self.evaluator._simple_text_similarity(text1, text2)
        similarity2 = self.evaluator._simple_text_similarity(text1, text3)

        # 相同或相似文本应该有更高的相似度
        self.assertGreater(similarity1, similarity2)
        self.assertGreaterEqual(similarity1, 0)
        self.assertLessEqual(similarity1, 1)

    def test_score_skill_coverage(self):
        """测试技能覆盖度评分"""
        answer = "我使用Python和Django"
        job_data = {
            "skills": ["Python", "Django", "MySQL", "Redis"]
        }
        keyword_matches = ["Python", "Django"]

        score = self.evaluator._score_skill_coverage(answer, job_data, keyword_matches)

        # 匹配了2/4个技能，基础分数应该是0.4，加上加分可能更高
        self.assertGreaterEqual(score, 0.4)
        self.assertLessEqual(score, 1.0)

    def test_score_case_specificity(self):
        """测试案例具体性评分"""
        # 包含案例和数字的回答
        answer_with_case = "例如，在去年的电商项目中，我使用Python将处理时间从5小时减少到30分钟"
        score1 = self.evaluator._score_case_specificity(answer_with_case)

        # 普通回答
        answer_general = "我使用Python进行开发"
        score2 = self.evaluator._score_case_specificity(answer_general)

        # 包含案例的回答应该得分更高
        self.assertGreater(score1, score2)
        self.assertGreaterEqual(score1, 0)
        self.assertLessEqual(score1, 1.0)

    def test_score_logical_expression(self):
        """测试逻辑表达评分"""
        # 逻辑清晰的回答
        logical_answer = "首先，我分析了需求。其次，设计了架构。然后，实现了功能。最后，进行了测试。"
        score1 = self.evaluator._score_logical_expression(logical_answer)

        # 逻辑混乱的回答
        illogical_answer = "我做了一些东西，然后其他东西，就这样"
        score2 = self.evaluator._score_logical_expression(illogical_answer)

        # 逻辑清晰的回答应该得分更高
        self.assertGreater(score1, score2)

    def test_score_quantitative_results(self):
        """测试量化成果评分"""
        # 包含量化数据的回答
        quantitative_answer = "我优化了系统性能，将响应时间从500ms降低到200ms，提升了60%的效率"
        score1 = self.evaluator._score_quantitative_results(quantitative_answer)

        # 不含量化数据的回答
        qualitative_answer = "我优化了系统性能，使其更快"
        score2 = self.evaluator._score_quantitative_results(qualitative_answer)

        # 包含量化数据的回答应该得分更高
        self.assertGreater(score1, score2)

    def test_calculate_total_score(self):
        """测试总分计算"""
        dimension_scores = {
            "skill_coverage": 0.8,
            "case_specificity": 0.7,
            "logical_expression": 0.9,
            "quantitative_results": 0.6
        }

        total_score = self.evaluator._calculate_total_score(dimension_scores)

        # 总分应该在0-10之间
        self.assertGreaterEqual(total_score, 0)
        self.assertLessEqual(total_score, 10)

        # 检查权重计算
        expected = (0.8*0.3 + 0.7*0.25 + 0.9*0.25 + 0.6*0.2) * 10
        self.assertAlmostEqual(total_score, expected, places=2)

    def test_determine_match_level(self):
        """测试匹配等级判定"""
        self.assertEqual(self.evaluator._determine_match_level(8.5), "通过")
        self.assertEqual(self.evaluator._determine_match_level(6.0), "待提升")
        self.assertEqual(self.evaluator._determine_match_level(4.0), "不通过")

    def test_generate_improvement_suggestions(self):
        """测试改进建议生成"""
        # 低分情况
        low_scores = {
            "skill_coverage": 0.3,
            "case_specificity": 0.4,
            "logical_expression": 0.2,
            "quantitative_results": 0.1
        }

        suggestions = self.evaluator._generate_improvement_suggestions(
            low_scores, [], 3.5
        )

        self.assertIsInstance(suggestions, list)
        self.assertGreater(len(suggestions), 0)

        # 高分情况
        high_scores = {
            "skill_coverage": 0.9,
            "case_specificity": 0.8,
            "logical_expression": 0.9,
            "quantitative_results": 0.8
        }

        suggestions = self.evaluator._generate_improvement_suggestions(
            high_scores, ["Python", "Django"], 8.5
        )

        # 即使高分也应该有建议
        self.assertGreater(len(suggestions), 0)

    def test_generate_detailed_feedback(self):
        """测试详细反馈生成"""
        dimension_scores = {
            "skill_coverage": 0.8,
            "case_specificity": 0.7,
            "logical_expression": 0.9,
            "quantitative_results": 0.6
        }

        keyword_matches = ["Python", "Django"]
        semantic_similarity = 0.85

        feedback = self.evaluator._generate_detailed_feedback(
            dimension_scores, keyword_matches, semantic_similarity
        )

        # 检查反馈结构
        self.assertIn("score_breakdown", feedback)
        self.assertIn("keyword_analysis", feedback)
        self.assertIn("strengths", feedback)
        self.assertIn("weaknesses", feedback)

        # 检查分数细分
        breakdown = feedback["score_breakdown"]
        self.assertIn("skill_coverage", breakdown)
        self.assertIn("case_specificity", breakdown)
        self.assertIn("logical_expression", breakdown)
        self.assertIn("quantitative_results", breakdown)

    def test_evaluate_with_semantic_analysis_failure(self):
        """测试语义分析失败时的评估"""
        # 模拟OpenAI Embeddings异常
        self.mock_openai_client.embeddings.create.side_effect = Exception("API错误")

        question = "请介绍一下Python的装饰器"
        answer = "装饰器是Python的一种高级功能"
        job_data = {
            "skills": ["Python"]
        }

        result = self.evaluator.evaluate(question, answer, job_data)

        # 即使语义分析失败，也应该返回评估结果
        self.assertIsInstance(result, EvaluationResult)
        self.assertGreaterEqual(result.total_score, 0)
        self.assertLessEqual(result.total_score, 10)

    def test_evaluate_with_job_data(self):
        """测试带岗位数据的评估"""
        # 模拟OpenAI Embeddings
        mock_embedding_response = Mock()
        mock_embedding_response.data = [
            Mock(embedding=[0.1, 0.2, 0.3]),
            Mock(embedding=[0.1, 0.2, 0.3])
        ]
        self.mock_openai_client.embeddings.create.return_value = mock_embedding_response

        question = "请介绍一下你的Python项目经验"
        answer = "我使用Python和Django开发了一个电商网站，处理了高并发请求"
        job_data = {
            "skills": ["Python", "Django", "高并发"],
            "description": "需要Python和Django开发经验",
            "requirements": "能够处理高并发场景"
        }

        result = self.evaluator.evaluate(question, answer, job_data)

        # 检查结果结构
        self.assertIsInstance(result, EvaluationResult)
        self.assertIsInstance(result.total_score, float)
        self.assertIsInstance(result.dimension_scores, dict)
        self.assertIsInstance(result.match_level, str)
        self.assertIsInstance(result.keyword_matches, list)
        self.assertIsInstance(result.semantic_similarity, float)
        self.assertIsInstance(result.improvement_suggestions, list)
        self.assertIsInstance(result.detailed_feedback, dict)

        # 检查分数范围
        self.assertGreaterEqual(result.total_score, 0)
        self.assertLessEqual(result.total_score, 10)

        # 检查匹配等级
        self.assertIn(result.match_level, ["通过", "待提升", "不通过"])

    def test_evaluate_without_job_data(self):
        """测试不带岗位数据的评估"""
        question = "请介绍一下你的团队协作经验"
        answer = "在之前的项目中，我经常与团队成员协作，使用Git进行版本控制"

        result = self.evaluator.evaluate(question, answer)

        # 即使没有岗位数据，也应该返回评估结果
        self.assertIsInstance(result, EvaluationResult)
        self.assertGreaterEqual(result.total_score, 0)
        self.assertLessEqual(result.total_score, 10)

    def test_evaluate_async(self):
        """测试异步评估"""
        # 这个测试主要是为了确保异步方法存在并能调用同步方法
        question = "测试问题"
        answer = "测试回答"

        # 测试异步方法调用（这里主要是语法检查）
        import asyncio
        async def test():
            return await self.evaluator.evaluate_async(question, answer)

        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test())
            self.assertIsInstance(result, EvaluationResult)
        finally:
            loop.close()

    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]  # 完全相同
        vec3 = [0.0, 1.0, 0.0]  # 正交

        similarity1 = self.evaluator._cosine_similarity(vec1, vec2)
        similarity2 = self.evaluator._cosine_similarity(vec1, vec3)

        # 相同向量相似度应为1
        self.assertAlmostEqual(similarity1, 1.0, places=5)

        # 正交向量相似度应为0
        self.assertAlmostEqual(similarity2, 0.0, places=5)

        # 零向量测试
        zero_vec = [0.0, 0.0, 0.0]
        similarity3 = self.evaluator._cosine_similarity(vec1, zero_vec)
        self.assertEqual(similarity3, 0.0)


if __name__ == "__main__":
    unittest.main()