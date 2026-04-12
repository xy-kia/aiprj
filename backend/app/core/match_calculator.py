"""
匹配度计算器 - 计算用户意向与岗位的匹配度
使用TF-IDF向量化或BERT模型计算余弦相似度，加权关键词匹配加分。

参考文档：Workflow.md 第2.4节、Functional_Spec.md 第2.2节
"""

import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Union
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import jieba


class MatchCalculator:
    """匹配度计算器"""

    def __init__(self, use_bert: bool = False):
        """
        初始化匹配度计算器

        Args:
            use_bert: 是否使用BERT模型（需要sentence-transformers库）
        """
        self.use_bert = use_bert
        self.tfidf_vectorizer = None
        self.bert_model = None
        self._init_models()

    def _init_models(self):
        """初始化模型"""
        # 初始化TF-IDF向量化器
        self.tfidf_vectorizer = TfidfVectorizer(
            tokenizer=self._tokenize_chinese,
            max_features=5000,
            min_df=1,
            max_df=0.9,
            ngram_range=(1, 2)
        )

        # 如果需要，加载BERT模型
        if self.use_bert:
            try:
                from sentence_transformers import SentenceTransformer
                self.bert_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            except ImportError:
                print("Warning: sentence-transformers not installed, falling back to TF-IDF")
                self.use_bert = False

    def _tokenize_chinese(self, text: str) -> List[str]:
        """中文分词函数"""
        if not text:
            return []
        # 使用jieba分词
        words = jieba.lcut(text)
        # 去除停用词和标点
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '都', '而', '及', '与', '或'}
        filtered = [word for word in words if word.strip() and word not in stop_words]
        return filtered

    def calculate_match(
        self,
        user_intent: Dict[str, Any],
        job_data: Dict[str, Any],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        计算用户意向与岗位的匹配度

        Args:
            user_intent: 用户意向（来自IntentParser的输出）
            job_data: 岗位数据
            weights: 各维度权重配置

        Returns:
            匹配度计算结果
        """
        # 默认权重配置
        default_weights = {
            "skills": 0.35,      # 技能匹配权重
            "title": 0.20,       # 职位标题匹配权重
            "location": 0.15,    # 地点匹配权重
            "salary": 0.10,      # 薪资匹配权重
            "experience": 0.10,  # 经验匹配权重
            "education": 0.10,   # 学历匹配权重
        }

        weights = weights or default_weights

        # 计算各维度分数
        dimension_scores = {}

        # 1. 技能匹配分数
        dimension_scores["skills"] = self._calculate_skills_match(
            user_intent.get("skills", []),
            user_intent.get("related_skills", []),
            job_data.get("skills", []),
            job_data.get("requirements", "")
        )

        # 2. 职位标题匹配分数
        dimension_scores["title"] = self._calculate_text_match(
            user_intent.get("skills", []) + user_intent.get("job_types", []),
            job_data.get("title", "")
        )

        # 3. 地点匹配分数
        dimension_scores["location"] = self._calculate_location_match(
            user_intent.get("locations", []),
            job_data.get("location", "")
        )

        # 4. 薪资匹配分数
        dimension_scores["salary"] = self._calculate_salary_match(
            user_intent.get("salary_expectation", None),  # 可选：用户薪资期望
            job_data.get("salary_min"),
            job_data.get("salary_max")
        )

        # 5. 经验匹配分数
        dimension_scores["experience"] = self._calculate_experience_match(
            user_intent.get("experiences", []),
            job_data.get("experience", "")
        )

        # 6. 学历匹配分数
        dimension_scores["education"] = self._calculate_education_match(
            user_intent.get("educations", []),
            job_data.get("education", "")
        )

        # 计算加权总分
        total_score = 0.0
        weight_sum = 0.0

        for dimension, score in dimension_scores.items():
            if dimension in weights:
                weight = weights[dimension]
                total_score += score * weight
                weight_sum += weight

        # 归一化分数（0-100）
        if weight_sum > 0:
            final_score = (total_score / weight_sum) * 100
        else:
            final_score = 0.0

        # 确定匹配等级
        match_level = self._get_match_level(final_score)

        return {
            "total_score": round(final_score, 2),
            "match_level": match_level,
            "dimension_scores": {k: round(v, 2) for k, v in dimension_scores.items()},
            "weights": weights
        }

    def _calculate_skills_match(
        self,
        user_skills: List[str],
        user_related_skills: List[str],
        job_skills: List[str],
        job_requirements: str
    ) -> float:
        """计算技能匹配分数"""
        if not user_skills and not user_related_skills:
            return 0.5  # 用户未指定技能，给中等分数

        # 从职位要求中提取技能关键词
        all_job_skills = set(job_skills)
        if job_requirements:
            # 简单地从要求文本中提取技能词（实际项目需要更复杂的NLP）
            requirement_skills = self._extract_skills_from_text(job_requirements)
            all_job_skills.update(requirement_skills)

        # 用户的技能集合（包括相关技能）
        all_user_skills = set(user_skills)
        all_user_skills.update(user_related_skills)

        if not all_job_skills:
            return 0.5  # 岗位未明确要求技能，给中等分数

        # 计算技能匹配率
        matched_skills = all_user_skills.intersection(all_job_skills)
        if not matched_skills:
            return 0.0

        # 基础匹配分数
        match_ratio = len(matched_skills) / len(all_job_skills)

        # 如果用户有核心技能匹配，加分
        core_skill_bonus = 0.0
        if len(matched_skills) > 0:
            core_skill_bonus = min(0.2, len(matched_skills) * 0.05)

        return min(1.0, match_ratio + core_skill_bonus)

    def _extract_skills_from_text(self, text: Union[str, List[str]]) -> List[str]:
        """从文本中提取技能词（简化版）"""
        if not text:
            return []

        # 如果是列表，则连接为字符串
        if isinstance(text, list):
            text_str = " ".join(text)
        else:
            text_str = str(text)

        # 常见技能关键词（实际项目应从知识库加载）
        common_skills = [
            "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "C",
            "Vue.js", "React", "Angular", "Node.js", "Spring", "Django",
            "MySQL", "Redis", "MongoDB", "Docker", "Kubernetes", "Git",
            "Linux", "AWS", "机器学习", "深度学习", "数据分析", "SQL"
        ]

        found_skills = []
        text_lower = text_str.lower()

        for skill in common_skills:
            skill_lower = skill.lower()
            if skill_lower in text_lower or skill in text_str:
                found_skills.append(skill)

        return found_skills

    def _calculate_text_match(self, user_keywords: List[str], job_text: str) -> float:
        """计算文本匹配分数"""
        if not user_keywords or not job_text:
            return 0.5

        # 构建用户关键词文本
        user_text = " ".join(user_keywords)

        # 使用TF-IDF或BERT计算相似度
        if self.use_bert and self.bert_model:
            # BERT编码
            embeddings = self.bert_model.encode([user_text, job_text])
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        else:
            # TF-IDF向量化
            if self.tfidf_vectorizer is None:
                self._init_models()

            texts = [user_text, job_text]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

        # 归一化到0-1范围
        return float(max(0.0, min(1.0, similarity)))

    def _calculate_location_match(self, user_locations: List[str], job_location: str) -> float:
        """计算地点匹配分数"""
        if not user_locations:
            return 0.5  # 用户未指定地点，给中等分数

        if not job_location:
            return 0.5  # 岗位未指定地点，给中等分数

        # 地点精确匹配
        job_location_clean = job_location.strip()
        for user_loc in user_locations:
            user_loc_clean = user_loc.strip()
            if user_loc_clean == job_location_clean:
                return 1.0

            # 部分匹配（如用户输入"北京"，岗位是"北京市海淀区"）
            if user_loc_clean in job_location_clean or job_location_clean in user_loc_clean:
                return 0.8

        # 完全不匹配
        return 0.0

    def _calculate_salary_match(
        self,
        user_salary_expectation: Optional[int],
        job_salary_min: Optional[int],
        job_salary_max: Optional[int]
    ) -> float:
        """计算薪资匹配分数"""
        if not user_salary_expectation:
            return 0.5  # 用户未指定薪资期望，给中等分数

        if job_salary_min is None or job_salary_max is None:
            return 0.5  # 岗位薪资未明确，给中等分数

        # 用户期望在薪资范围内
        if job_salary_min <= user_salary_expectation <= job_salary_max:
            return 1.0
        # 用户期望略高于薪资范围（不超过20%）
        elif user_salary_expectation > job_salary_max:
            excess_ratio = (user_salary_expectation - job_salary_max) / job_salary_max
            if excess_ratio <= 0.2:
                return 0.8
            else:
                return 0.2
        # 用户期望略低于薪资范围（不低于20%）
        else:
            deficit_ratio = (job_salary_min - user_salary_expectation) / job_salary_min
            if deficit_ratio <= 0.2:
                return 0.7
            else:
                return 0.4

    def _calculate_experience_match(self, user_experiences: List[str], job_experience: str) -> float:
        """计算经验匹配分数"""
        if not user_experiences:
            return 0.5  # 用户未指定经验要求，给中等分数

        if not job_experience or job_experience == "不限":
            return 1.0  # 岗位无经验要求，完全匹配

        # 经验等级映射
        experience_levels = {
            "no experience": 0,
            "应届生": 1,
            "1年以内": 2,
            "1-3年": 3,
            "3-5年": 4,
            "5-10年": 5,
            "10年以上": 6
        }

        # 获取用户最高经验要求
        user_max_level = 0
        for exp in user_experiences:
            level = experience_levels.get(exp, 0)
            user_max_level = max(user_max_level, level)

        # 获取岗位经验要求
        job_level = experience_levels.get(job_experience, 0)

        if user_max_level == 0:  # 用户无经验
            if job_level <= 1:  # 岗位要求应届生或无经验
                return 1.0
            else:
                return 0.0
        elif user_max_level >= job_level:
            return 1.0  # 用户经验满足或超过岗位要求
        else:
            # 计算差距比例
            gap = job_level - user_max_level
            max_gap = max(experience_levels.values())
            return max(0.0, 1.0 - (gap / max_gap))

    def _calculate_education_match(self, user_educations: List[str], job_education: str) -> float:
        """计算学历匹配分数"""
        if not user_educations:
            return 0.5  # 用户未指定学历要求，给中等分数

        if not job_education or job_education == "不限":
            return 1.0  # 岗位无学历要求，完全匹配

        # 学历等级映射
        education_levels = {
            "不限": 0,
            "高中": 1,
            "大专": 2,
            "本科": 3,
            "硕士": 4,
            "博士": 5
        }

        # 获取用户最高学历
        user_max_level = 0
        for edu in user_educations:
            level = education_levels.get(edu, 0)
            user_max_level = max(user_max_level, level)

        # 获取岗位学历要求
        job_level = education_levels.get(job_education, 0)

        if user_max_level >= job_level:
            return 1.0  # 用户学历满足或超过岗位要求
        else:
            # 计算差距比例
            gap = job_level - user_max_level
            max_gap = max(education_levels.values())
            return max(0.0, 1.0 - (gap / max_gap))

    def _get_match_level(self, score: float) -> str:
        """根据分数确定匹配等级"""
        if score >= 80:
            return "高度匹配"
        elif score >= 60:
            return "匹配"
        elif score >= 40:
            return "部分匹配"
        else:
            return "不匹配"

    def batch_calculate(
        self,
        user_intent: Dict[str, Any],
        jobs_data: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        批量计算岗位匹配度

        Args:
            user_intent: 用户意向
            jobs_data: 岗位数据列表
            top_k: 返回前K个最匹配的岗位

        Returns:
            排序后的匹配结果列表
        """
        results = []

        for job in jobs_data:
            match_result = self.calculate_match(user_intent, job)
            results.append({
                "job_data": job,
                "match_result": match_result
            })

        # 按总分降序排序
        results.sort(key=lambda x: x["match_result"]["total_score"], reverse=True)

        # 返回前K个
        return results[:top_k]


# 工具函数：创建匹配计算器实例
def create_match_calculator(use_bert: bool = False) -> MatchCalculator:
    """创建匹配度计算器实例"""
    return MatchCalculator(use_bert=use_bert)


# 测试函数
if __name__ == "__main__":
    # 测试代码
    calculator = MatchCalculator()

    # 模拟用户意向
    user_intent = {
        "skills": ["Python", "机器学习"],
        "related_skills": ["数据分析", "深度学习"],
        "job_types": ["实习"],
        "locations": ["北京"],
        "experiences": ["应届生"],
        "educations": ["本科"]
    }

    # 模拟岗位数据
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

    result = calculator.calculate_match(user_intent, job_data)
    print("匹配度计算结果:")
    print(f"总分: {result['total_score']}")
    print(f"匹配等级: {result['match_level']}")
    print(f"各维度分数: {result['dimension_scores']}")