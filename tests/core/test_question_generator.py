"""
问题生成器测试
"""

import sys
import os
import json
import unittest
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.question_generator import QuestionGenerator, InterviewQuestion


class TestQuestionGenerator(unittest.TestCase):
    """测试问题生成器"""

    def setUp(self):
        """测试前准备"""
        # 模拟OpenAI客户端
        self.mock_openai_client = Mock()
        self.mock_openai_client.chat.completions.create = Mock()

        # 模拟Redis客户端
        self.mock_redis_client = Mock()
        self.mock_redis_client.get = Mock(return_value=None)
        self.mock_redis_client.setex = Mock()

        with patch('openai.OpenAI', return_value=self.mock_openai_client):
            self.generator = QuestionGenerator(
                openai_api_key="test-key",
                model="gpt-4o-mini",
                cache_enabled=True,
                redis_client=self.mock_redis_client
            )

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.generator.api_key, "test-key")
        self.assertEqual(self.generator.model, "gpt-4o-mini")
        self.assertTrue(self.generator.cache_enabled)
        self.assertIsNotNone(self.generator.client)

    def test_extract_job_info(self):
        """测试岗位信息提取"""
        job_data = {
            "title": "Python开发工程师",
            "company": "某科技公司",
            "description": "负责Python后端开发",
            "requirements": ["熟悉Python", "了解Django框架"],
            "skills": ["Python", "Django", "MySQL"]
        }

        job_info = self.generator._extract_job_info(job_data)

        self.assertEqual(job_info["title"], "Python开发工程师")
        self.assertEqual(job_info["company"], "某科技公司")
        self.assertIn("Python后端开发", job_info["description"])
        self.assertIn("熟悉Python", job_info["requirements"])

    def test_extract_job_info_with_string_requirements(self):
        """测试字符串格式的岗位要求提取"""
        job_data = {
            "title": "前端开发",
            "company": "某公司",
            "description": "前端开发工作",
            "requirements": "熟悉JavaScript、React",
            "skills": []
        }

        job_info = self.generator._extract_job_info(job_data)
        self.assertEqual(job_info["requirements"], "熟悉JavaScript、React")

    def test_generate_cache_key(self):
        """测试缓存键生成"""
        job_data1 = {
            "title": "Python开发",
            "company": "A公司",
            "description": "需要Python开发经验"
        }

        job_data2 = {
            "title": "Python开发",
            "company": "A公司",
            "description": "需要Python开发经验"
        }

        job_data3 = {
            "title": "Java开发",
            "company": "A公司",
            "description": "需要Java开发经验"
        }

        key1 = self.generator._generate_cache_key(job_data1, "intern_general", 8)
        key2 = self.generator._generate_cache_key(job_data2, "intern_general", 8)
        key3 = self.generator._generate_cache_key(job_data3, "intern_general", 8)

        # 相同数据应该生成相同key
        self.assertEqual(key1, key2)

        # 不同数据应该生成不同key
        self.assertNotEqual(key1, key3)

    def test_parse_llm_response_valid_json(self):
        """测试解析有效的LLM响应"""
        valid_json = json.dumps([
            {
                "question": "什么是Python的装饰器？",
                "question_type": "technical",
                "target_skill": "Python",
                "jd_reference": "需要掌握Python",
                "suggested_time": 120,
                "difficulty": "medium",
                "scoring_criteria": ["理解装饰器原理", "能举例说明"]
            }
        ])

        result = self.generator._parse_llm_response(valid_json)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["question"], "什么是Python的装饰器？")

    def test_parse_llm_response_with_json_object(self):
        """测试解析JSON对象格式的LLM响应"""
        json_object = json.dumps({
            "questions": [
                {
                    "question": "请介绍一下Django框架",
                    "question_type": "technical",
                    "target_skill": "Django"
                }
            ]
        })

        result = self.generator._parse_llm_response(json_object)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["question"], "请介绍一下Django框架")

    def test_create_question_objects(self):
        """测试创建问题对象"""
        questions_data = [
            {
                "question": "什么是Python的GIL？",
                "question_type": "technical",
                "target_skill": "Python",
                "jd_reference": "需要掌握Python多线程",
                "suggested_time": "180",
                "difficulty": "hard",
                "scoring_criteria": "理解GIL原理、能解释影响、知道解决方案"
            }
        ]

        questions = self.generator._create_question_objects(questions_data)
        self.assertEqual(len(questions), 1)
        self.assertIsInstance(questions[0], InterviewQuestion)
        self.assertEqual(questions[0].question, "什么是Python的GIL？")
        self.assertEqual(questions[0].difficulty, "hard")

    def test_filter_questions_duplicate_removal(self):
        """测试问题过滤（去重）"""
        questions = [
            InterviewQuestion(question="这是一个测试问题A，用于测试重复删除功能", question_type="technical"),
            InterviewQuestion(question="这是一个测试问题A，用于测试重复删除功能", question_type="technical"),  # 重复
            InterviewQuestion(question="这是一个测试问题B，用于测试行为问题", question_type="behavioral")
        ]

        filtered = self.generator._filter_questions(questions)
        self.assertEqual(len(filtered), 2)  # 去重后应为2个

    def test_filter_questions_quality_check(self):
        """测试问题质量检查"""
        # 问题过短
        short_question = InterviewQuestion(
            question="短",  # 长度小于10
            question_type="technical",
            suggested_time=30,
            difficulty="easy"
        )

        # 无效的问题类型
        invalid_type_question = InterviewQuestion(
            question="这是一个有效的问题",
            question_type="invalid_type",  # 无效类型
            suggested_time=120,
            difficulty="medium"
        )

        # 有效问题
        valid_question = InterviewQuestion(
            question="这是一个有效的问题，长度足够",
            question_type="technical",
            suggested_time=120,
            difficulty="medium"
        )

        questions = [short_question, invalid_type_question, valid_question]
        filtered = self.generator._filter_questions(questions)

        # 只应保留有效问题
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].question, valid_question.question)

    def test_serialize_deserialize_questions(self):
        """测试问题序列化和反序列化"""
        questions = [
            InterviewQuestion(
                question="问题1",
                question_type="technical",
                target_skill="Python",
                jd_reference="JD引用",
                suggested_time=120,
                difficulty="medium",
                scoring_criteria=["标准1", "标准2"]
            )
        ]

        # 序列化
        serialized = self.generator._serialize_questions(questions)
        self.assertIsInstance(serialized, list)
        self.assertEqual(serialized[0]["question"], "问题1")

        # 反序列化
        deserialized = self.generator._deserialize_questions(serialized)
        self.assertEqual(len(deserialized), 1)
        self.assertEqual(deserialized[0].question, "问题1")

    def test_generate_questions_with_cache_hit(self):
        """测试缓存命中时的生成"""
        # 模拟Redis缓存命中
        cached_data = {
            "questions": [
                {
                    "question": "缓存的问题",
                    "question_type": "technical",
                    "target_skill": "Python",
                    "jd_reference": "缓存引用",
                    "suggested_time": 120,
                    "difficulty": "medium",
                    "scoring_criteria": None
                }
            ],
            "timestamp": "2024-01-01T00:00:00"
        }

        self.mock_redis_client.get.return_value = json.dumps(cached_data)

        job_data = {
            "title": "测试岗位",
            "company": "测试公司",
            "description": "测试描述",
            "requirements": ["要求1", "要求2"]
        }

        questions = self.generator.generate_questions(job_data, "intern_general", 5, enable_llm_evaluation=False)

        # 应该返回缓存的问题
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question, "缓存的问题")
        # OpenAI API不应被调用
        self.mock_openai_client.chat.completions.create.assert_not_called()

    def test_generate_questions_with_cache_miss(self):
        """测试缓存未命中时的生成"""
        # 模拟Redis缓存未命中
        self.mock_redis_client.get.return_value = None

        # 模拟OpenAI响应
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=json.dumps([
            {
                "question": "这是一个新生成的测试问题，用于测试缓存未命中场景",
                "question_type": "technical",
                "target_skill": "Python",
                "jd_reference": "JD引用",
                "suggested_time": 120,
                "difficulty": "medium"
            }
        ])))]
        self.mock_openai_client.chat.completions.create.return_value = mock_response

        job_data = {
            "title": "测试岗位",
            "company": "测试公司",
            "description": "测试描述",
            "requirements": ["要求1", "要求2"]
        }

        questions = self.generator.generate_questions(job_data, "intern_general", 5, enable_llm_evaluation=False)

        # 应该返回新生成的问题
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0].question, "这是一个新生成的测试问题，用于测试缓存未命中场景")
        # OpenAI API应该被调用一次
        self.mock_openai_client.chat.completions.create.assert_called_once()
        # Redis应该被设置
        self.mock_redis_client.setex.assert_called_once()

    def test_generate_questions_fallback(self):
        """测试LLM调用失败时的备用问题生成"""
        # 模拟OpenAI调用异常
        self.mock_openai_client.chat.completions.create.side_effect = Exception("API错误")

        job_data = {
            "title": "测试岗位",
            "company": "测试公司",
            "description": "测试描述",
            "requirements": ["要求1", "要求2"]
        }

        questions = self.generator.generate_questions(job_data, "intern_general", 5, enable_llm_evaluation=False)

        # 应该返回备用问题
        self.assertGreater(len(questions), 0)
        # 所有问题都应该是InterviewQuestion对象
        for q in questions:
            self.assertIsInstance(q, InterviewQuestion)

    def test_ensure_diversity(self):
        """测试问题多样性"""
        questions = [
            InterviewQuestion(question="问题1", question_type="technical"),
            InterviewQuestion(question="问题2", question_type="technical"),
            InterviewQuestion(question="问题3", question_type="technical"),
            InterviewQuestion(question="问题4", question_type="behavioral"),
            InterviewQuestion(question="问题5", question_type="behavioral"),
            InterviewQuestion(question="问题6", question_type="situational"),
        ]

        diversified = self.generator._ensure_diversity(questions)

        # 应该保持多样性
        types = [q.question_type for q in diversified]
        # 检查是否包含多种类型
        self.assertIn("technical", types)
        self.assertIn("behavioral", types)
        self.assertIn("situational", types)

    def test_get_cached_redis_fallback_memory(self):
        """测试Redis缓存失败时回退到内存缓存"""
        # 模拟Redis异常
        self.mock_redis_client.get.side_effect = Exception("Redis错误")

        # 设置内存缓存
        cache_key = "test_key"
        cache_data = {"test": "data"}
        self.generator.memory_cache[cache_key] = cache_data

        result = self.generator._get_cached(cache_key)
        self.assertEqual(result, cache_data)

    def test_set_cached_redis_fallback_memory(self):
        """测试Redis设置失败时回退到内存缓存"""
        # 模拟Redis异常
        self.mock_redis_client.setex.side_effect = Exception("Redis错误")

        cache_key = "test_key"
        cache_data = {"test": "data"}

        self.generator._set_cached(cache_key, cache_data)

        # 数据应该存储在内存缓存中
        self.assertEqual(self.generator.memory_cache[cache_key], cache_data)

    def test_generate_questions_async(self):
        """测试异步生成问题"""
        # 这个测试主要是为了确保异步方法存在并能调用同步方法
        # 在实际项目中，可能需要更复杂的异步测试
        job_data = {
            "title": "测试岗位",
            "company": "测试公司",
            "description": "测试描述",
            "requirements": ["要求1", "要求2"]
        }

        # 测试异步方法调用（这里主要是语法检查）
        import asyncio
        async def test():
            return await self.generator.generate_questions_async(job_data)

        # 运行异步测试
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(test())
            self.assertIsInstance(result, list)
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()