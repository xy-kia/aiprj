"""
匹配计算器测试
"""

import sys
import os
import unittest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.app.core.match_calculator import MatchCalculator


class TestMatchCalculator(unittest.TestCase):
    """测试匹配计算器"""

    def setUp(self):
        """测试前准备"""
        self.calculator = MatchCalculator(use_bert=False)

    def test_calculate_match_basic(self):
        """测试基本匹配计算"""
        user_intent = {
            "skills": ["Python", "机器学习"],
            "related_skills": ["数据分析", "深度学习"],
            "job_types": ["实习"],
            "locations": ["北京"],
            "experiences": ["应届生"],
            "educations": ["本科"]
        }

        job_data = {
            "title": "机器学习实习工程师",
            "company": "某科技公司",
            "location": "北京市海淀区",
            "skills": ["Python", "机器学习", "深度学习", "TensorFlow"],
            "requirements": "需要掌握Python和机器学习基础知识，有相关项目经验者优先",
            "salary_min": 8000,
            "salary_max": 12000,
            "experience": "应届生",
            "education": "本科"
        }

        result = self.calculator.calculate_match(user_intent, job_data)

        # 检查基本结构
        self.assertIn("total_score", result)
        self.assertIn("match_level", result)
        self.assertIn("dimension_scores", result)
        self.assertIn("weights", result)

        # 检查分数范围
        self.assertGreaterEqual(result["total_score"], 0)
        self.assertLessEqual(result["total_score"], 100)

        # 检查匹配等级
        self.assertIn(result["match_level"], ["高度匹配", "匹配", "部分匹配", "不匹配"])

    def test_calculate_match_partial(self):
        """测试部分匹配情况"""
        user_intent = {
            "skills": ["Java", "Spring"],
            "related_skills": ["MySQL", "Redis"],
            "job_types": ["实习"],
            "locations": ["上海"],
            "experiences": ["1-3年"],
            "educations": ["本科"]
        }

        job_data = {
            "title": "Python开发工程师",
            "company": "某软件公司",
            "location": "北京",
            "skills": ["Python", "Django", "Flask"],
            "requirements": "需要Python开发经验，熟悉Web框架",
            "salary_min": 10000,
            "salary_max": 15000,
            "experience": "1-3年",
            "education": "本科"
        }

        result = self.calculator.calculate_match(user_intent, job_data)

        # 技能不匹配，分数应该较低
        self.assertLess(result["total_score"], 70)
        self.assertEqual(result["dimension_scores"]["skills"], 0.0)

    def test_calculate_match_perfect(self):
        """测试完全匹配情况"""
        user_intent = {
            "skills": ["Python", "Django", "MySQL"],
            "related_skills": ["Redis", "Linux"],
            "job_types": ["实习"],
            "locations": ["北京"],
            "experiences": ["应届生"],
            "educations": ["本科"]
        }

        job_data = {
            "title": "Python开发实习",
            "company": "某科技公司",
            "location": "北京",
            "skills": ["Python", "Django", "MySQL", "Redis"],
            "requirements": "需要Python和Django开发经验，熟悉MySQL数据库",
            "salary_min": 8000,
            "salary_max": 12000,
            "experience": "应届生",
            "education": "本科"
        }

        result = self.calculator.calculate_match(user_intent, job_data)

        # 完全匹配，分数应该较高
        self.assertGreaterEqual(result["total_score"], 70)
        self.assertEqual(result["match_level"], "匹配")

    def test_skills_match_calculation(self):
        """测试技能匹配计算"""
        user_skills = ["Python", "机器学习"]
        user_related_skills = ["数据分析", "深度学习"]
        job_skills = ["Python", "机器学习", "深度学习", "TensorFlow"]
        job_requirements = "需要掌握Python和机器学习基础知识"

        score = self.calculator._calculate_skills_match(
            user_skills, user_related_skills, job_skills, job_requirements
        )

        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    def test_location_match_calculation(self):
        """测试地点匹配计算"""
        # 精确匹配
        score1 = self.calculator._calculate_location_match(["北京"], "北京")
        self.assertEqual(score1, 1.0)

        # 部分匹配
        score2 = self.calculator._calculate_location_match(["北京"], "北京市海淀区")
        self.assertEqual(score2, 0.8)

        # 不匹配
        score3 = self.calculator._calculate_location_match(["上海"], "北京")
        self.assertEqual(score3, 0.0)

        # 用户未指定地点
        score4 = self.calculator._calculate_location_match([], "北京")
        self.assertEqual(score4, 0.5)

    def test_salary_match_calculation(self):
        """测试薪资匹配计算"""
        # 期望在范围内
        score1 = self.calculator._calculate_salary_match(10000, 8000, 12000)
        self.assertEqual(score1, 1.0)

        # 期望略高于
        score2 = self.calculator._calculate_salary_match(13000, 8000, 12000)
        self.assertEqual(score2, 0.8)

        # 期望远高于
        score3 = self.calculator._calculate_salary_match(20000, 8000, 12000)
        self.assertEqual(score3, 0.2)

        # 期望略低于
        score4 = self.calculator._calculate_salary_match(7000, 8000, 12000)
        self.assertEqual(score4, 0.7)

        # 用户未指定期望
        score5 = self.calculator._calculate_salary_match(None, 8000, 12000)
        self.assertEqual(score5, 0.5)

    def test_experience_match_calculation(self):
        """测试经验匹配计算"""
        # 完全匹配
        score1 = self.calculator._calculate_experience_match(["应届生"], "应届生")
        self.assertEqual(score1, 1.0)

        # 用户经验超过要求
        score2 = self.calculator._calculate_experience_match(["3-5年"], "1-3年")
        self.assertEqual(score2, 1.0)

        # 用户经验不足
        score3 = self.calculator._calculate_experience_match(["应届生"], "3-5年")
        self.assertLess(score3, 1.0)

        # 岗位无经验要求
        score4 = self.calculator._calculate_experience_match(["应届生"], "不限")
        self.assertEqual(score4, 1.0)

    def test_education_match_calculation(self):
        """测试学历匹配计算"""
        # 完全匹配
        score1 = self.calculator._calculate_education_match(["本科"], "本科")
        self.assertEqual(score1, 1.0)

        # 用户学历超过要求
        score2 = self.calculator._calculate_education_match(["硕士"], "本科")
        self.assertEqual(score2, 1.0)

        # 用户学历不足
        score3 = self.calculator._calculate_education_match(["大专"], "本科")
        self.assertLess(score3, 1.0)

        # 岗位无学历要求
        score4 = self.calculator._calculate_education_match(["本科"], "不限")
        self.assertEqual(score4, 1.0)

    def test_text_match_calculation(self):
        """测试文本匹配计算"""
        user_keywords = ["Python", "开发", "经验"]
        job_text = "需要Python开发经验，熟悉Django框架"

        score = self.calculator._calculate_text_match(user_keywords, job_text)

        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)

    def test_get_match_level(self):
        """测试匹配等级判定"""
        self.assertEqual(self.calculator._get_match_level(85), "高度匹配")
        self.assertEqual(self.calculator._get_match_level(70), "匹配")
        self.assertEqual(self.calculator._get_match_level(50), "部分匹配")
        self.assertEqual(self.calculator._get_match_level(30), "不匹配")

    def test_batch_calculate(self):
        """测试批量计算"""
        user_intent = {
            "skills": ["Python"],
            "related_skills": ["数据分析"],
            "job_types": ["实习"],
            "locations": ["北京"],
            "experiences": ["应届生"],
            "educations": ["本科"]
        }

        jobs_data = [
            {
                "title": "Python开发实习",
                "location": "北京",
                "skills": ["Python", "Django"],
                "requirements": "需要Python开发经验",
                "salary_min": 8000,
                "salary_max": 12000,
                "experience": "应届生",
                "education": "本科"
            },
            {
                "title": "Java开发实习",
                "location": "上海",
                "skills": ["Java", "Spring"],
                "requirements": "需要Java开发经验",
                "salary_min": 8000,
                "salary_max": 12000,
                "experience": "应届生",
                "education": "本科"
            },
            {
                "title": "前端开发实习",
                "location": "北京",
                "skills": ["JavaScript", "React"],
                "requirements": "需要前端开发经验",
                "salary_min": 8000,
                "salary_max": 12000,
                "experience": "应届生",
                "education": "本科"
            }
        ]

        results = self.calculator.batch_calculate(user_intent, jobs_data, top_k=2)

        # 检查返回数量
        self.assertEqual(len(results), 2)

        # 检查排序（Python开发应该排第一）
        self.assertEqual(results[0]["job_data"]["title"], "Python开发实习")

        # 检查结构
        for result in results:
            self.assertIn("job_data", result)
            self.assertIn("match_result", result)

    def test_custom_weights(self):
        """测试自定义权重"""
        user_intent = {
            "skills": ["Python"],
            "related_skills": ["数据分析"],
            "job_types": ["实习"],
            "locations": ["北京"],
            "experiences": ["应届生"],
            "educations": ["本科"]
        }

        job_data = {
            "title": "Python开发实习",
            "location": "北京",
            "skills": ["Python", "Django"],
            "requirements": "需要Python开发经验",
            "salary_min": 8000,
            "salary_max": 12000,
            "experience": "应届生",
            "education": "本科"
        }

        custom_weights = {
            "skills": 0.5,
            "title": 0.2,
            "location": 0.1,
            "salary": 0.1,
            "experience": 0.05,
            "education": 0.05
        }

        result = self.calculator.calculate_match(user_intent, job_data, weights=custom_weights)

        self.assertEqual(result["weights"], custom_weights)


if __name__ == "__main__":
    unittest.main()