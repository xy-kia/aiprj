"""
回答评估器 - 评估用户对面试问题的回答
实现四维度评分：岗位技能覆盖度、案例具体性、逻辑表达、量化成果

参考文档：Workflow.md 第4.4节、Functional_Spec.md 第2.4节
"""

import re
import json
import jieba
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

import openai
from backend.config.settings import settings


@dataclass
class EvaluationResult:
    """评估结果"""
    total_score: float  # 综合评分 (0-10)
    dimension_scores: Dict[str, float]  # 各维度评分
    match_level: str  # 匹配等级：通过、待提升、不通过
    keyword_matches: List[str]  # 匹配的关键词
    semantic_similarity: float  # 语义相似度 (0-1)
    improvement_suggestions: List[str]  # 改进建议
    detailed_feedback: Dict[str, Any]  # 详细反馈


class AnswerEvaluator:
    """回答评估器"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        max_concurrent_requests: int = 5
    ):
        """
        初始化回答评估器

        Args:
            openai_api_key: OpenAI API密钥
            model: 模型名称
            base_url: API基础URL，如未提供则使用配置
            max_concurrent_requests: 最大并发请求数，用于限流
        """
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.max_concurrent_requests = max_concurrent_requests

        # 初始化OpenAI客户端
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 日志
        self.logger = logging.getLogger(__name__)

        # 技能库（从文件加载）
        self.skill_keywords = self._load_skill_keywords()

        # 异步请求信号量（用于限流）
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

        # 评分权重配置
        self.score_weights = {
            "skill_coverage": 0.30,  # 岗位技能覆盖度
            "case_specificity": 0.25,  # 案例具体性
            "logical_expression": 0.25,  # 逻辑表达
            "quantitative_results": 0.20,  # 量化成果
        }

    def _load_skill_keywords(self) -> List[str]:
        """加载技能关键词"""
        # 这里从知识库加载技能关键词
        # 简化版本：使用常见技能词
        common_skills = [
            "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "C",
            "Vue.js", "React", "Angular", "Node.js", "Spring", "Django", "Flask",
            "MySQL", "Redis", "MongoDB", "Docker", "Kubernetes", "Git", "Linux",
            "AWS", "机器学习", "深度学习", "数据分析", "SQL", "算法", "数据结构",
            "前端开发", "后端开发", "移动开发", "测试", "运维", "项目管理", "团队协作",
            "沟通能力", "问题解决", "创新思维", "学习能力", "执行力", "责任心"
        ]

        # 添加同义词
        skill_synonyms = {
            "Python": ["python", "py", "Python开发"],
            "Java": ["java", "Java开发"],
            "机器学习": ["machine learning", "ML", "人工智能"],
            "深度学习": ["deep learning", "DL", "神经网络"],
            "数据分析": ["data analysis", "数据挖掘"],
            "团队协作": ["团队合作", "协作能力", "沟通协作"],
            "问题解决": ["解决问题", "处理问题", "故障排除"]
        }

        all_keywords = set(common_skills)
        for skill, synonyms in skill_synonyms.items():
            all_keywords.add(skill)
            all_keywords.update(synonyms)

        return list(all_keywords)

    def evaluate(
        self,
        question: str,
        answer: str,
        job_data: Optional[Dict[str, Any]] = None,
        question_data: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """
        评估回答

        Args:
            question: 面试问题
            answer: 用户回答
            job_data: 岗位数据（可选）
            question_data: 问题数据（可选，包含target_skill等）

        Returns:
            评估结果
        """
        self.logger.info(f"开始评估回答，问题: {question[:50]}...")

        # 1. 关键词匹配
        keyword_matches = self._keyword_matching(answer, job_data, question_data)

        # 2. 语义分析
        semantic_similarity = self._semantic_analysis(question, answer, job_data)

        # 3. 多维度评分
        dimension_scores = self._multidimensional_scoring(
            question, answer, job_data, question_data,
            keyword_matches, semantic_similarity
        )

        # 4. 计算总分
        total_score = self._calculate_total_score(dimension_scores)

        # 5. 改进建议生成
        improvement_suggestions = self._generate_improvement_suggestions(
            dimension_scores, keyword_matches, total_score
        )

        # 6. 决策判定
        match_level = self._determine_match_level(total_score)

        # 7. 详细反馈
        detailed_feedback = self._generate_detailed_feedback(
            dimension_scores, keyword_matches, semantic_similarity
        )

        return EvaluationResult(
            total_score=total_score,
            dimension_scores=dimension_scores,
            match_level=match_level,
            keyword_matches=keyword_matches,
            semantic_similarity=semantic_similarity,
            improvement_suggestions=improvement_suggestions,
            detailed_feedback=detailed_feedback
        )

    def _keyword_matching(
        self,
        answer: str,
        job_data: Optional[Dict[str, Any]],
        question_data: Optional[Dict[str, Any]]
    ) -> List[str]:
        """关键词匹配"""
        matches = set()

        # 从回答中提取关键词
        answer_keywords = self._extract_keywords(answer)

        # 匹配技能关键词
        for keyword in answer_keywords:
            if keyword in self.skill_keywords:
                matches.add(keyword)

        # 如果提供了岗位数据，匹配岗位相关技能
        if job_data:
            job_skills = job_data.get("skills", [])
            if isinstance(job_skills, list):
                for skill in job_skills:
                    if skill in answer:
                        matches.add(skill)

            # 从岗位描述中提取关键词
            job_description = job_data.get("description", "")
            job_requirements = job_data.get("requirements", "")
            job_text = f"{job_description} {job_requirements}"

            job_text_keywords = self._extract_keywords(job_text)
            for keyword in job_text_keywords:
                if keyword in answer_keywords and keyword in self.skill_keywords:
                    matches.add(keyword)

        # 如果提供了问题数据，匹配目标技能
        if question_data and question_data.get("target_skill"):
            target_skill = question_data["target_skill"]
            if target_skill in answer:
                matches.add(target_skill)

        return list(matches)

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        if not text:
            return []

        # 使用jieba分词
        words = jieba.lcut(text)

        # 过滤停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '都', '而', '及', '与', '或'}
        filtered = [word for word in words if word.strip() and word not in stop_words]

        # 提取名词、动词等关键词
        # 简化版本：返回所有非停用词
        return filtered

    def _semantic_analysis(
        self,
        question: str,
        answer: str,
        job_data: Optional[Dict[str, Any]]
    ) -> float:
        """语义分析（计算问题与回答的语义相关性）"""
        try:
            # 使用OpenAI Embeddings计算语义相似度
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=[question, answer]
            )

            embeddings = [data.embedding for data in response.data]

            # 计算余弦相似度
            similarity = self._cosine_similarity(embeddings[0], embeddings[1])
            return float(similarity)

        except Exception as e:
            self.logger.error(f"语义分析失败: {e}")
            # 回退到基于关键词的简单相似度计算
            return self._simple_text_similarity(question, answer)

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _simple_text_similarity(self, text1: str, text2: str) -> float:
        """简单文本相似度计算（基于共同词汇）"""
        words1 = set(self._extract_keywords(text1))
        words2 = set(self._extract_keywords(text2))

        if not words1 or not words2:
            return 0.0

        common_words = words1.intersection(words2)
        similarity = len(common_words) / max(len(words1), len(words2))

        return similarity

    def _multidimensional_scoring(
        self,
        question: str,
        answer: str,
        job_data: Optional[Dict[str, Any]],
        question_data: Optional[Dict[str, Any]],
        keyword_matches: List[str],
        semantic_similarity: float
    ) -> Dict[str, float]:
        """多维度评分"""
        scores = {}

        # 1. 岗位技能覆盖度
        scores["skill_coverage"] = self._score_skill_coverage(
            answer, job_data, keyword_matches
        )

        # 2. 案例具体性
        scores["case_specificity"] = self._score_case_specificity(answer)

        # 3. 逻辑表达
        scores["logical_expression"] = self._score_logical_expression(answer)

        # 4. 量化成果
        scores["quantitative_results"] = self._score_quantitative_results(answer)

        # 基于语义相似度调整分数
        if semantic_similarity < 0.3:
            # 回答与问题相关性低，整体扣分
            for key in scores:
                scores[key] *= 0.7
        elif semantic_similarity > 0.8:
            # 回答与问题相关性高，整体加分
            for key in scores:
                scores[key] = min(1.0, scores[key] * 1.1)

        # 确保分数在0-1范围内
        for key in scores:
            scores[key] = max(0.0, min(1.0, scores[key]))

        return scores

    def _score_skill_coverage(
        self,
        answer: str,
        job_data: Optional[Dict[str, Any]],
        keyword_matches: List[str]
    ) -> float:
        """评分：岗位技能覆盖度"""
        # 如果没有岗位数据，基于关键词匹配评分
        if not job_data or not job_data.get("skills"):
            if keyword_matches:
                return min(1.0, len(keyword_matches) * 0.2)
            return 0.3

        job_skills = job_data.get("skills", [])
        if not job_skills:
            return 0.3

        # 计算匹配的技能比例
        matched_count = len(keyword_matches)
        total_skills = len(job_skills)

        coverage = matched_count / total_skills

        # 基础分数
        score = coverage * 0.8

        # 如果匹配到核心技能，加分
        if matched_count > 0:
            score += min(0.2, matched_count * 0.05)

        return min(1.0, score)

    def _score_case_specificity(self, answer: str) -> float:
        """评分：案例具体性"""
        # 检查回答中是否包含具体案例
        case_indicators = [
            "例如", "比如", "举个例子", "我曾经", "在某个项目中",
            "当时", "具体来说", "实际情况", "实际案例"
        ]

        # 检查是否有具体的时间、地点、人物、事件
        has_example = any(indicator in answer for indicator in case_indicators)

        # 检查是否有具体数据
        has_numbers = bool(re.search(r'\d+', answer))

        # 检查回答长度（更长的回答可能包含更多细节）
        answer_length = len(answer)
        length_score = min(1.0, answer_length / 500)

        if has_example and has_numbers:
            return min(1.0, 0.7 + length_score * 0.3)
        elif has_example:
            return min(1.0, 0.5 + length_score * 0.3)
        elif has_numbers:
            return min(1.0, 0.4 + length_score * 0.3)
        else:
            return min(1.0, 0.3 + length_score * 0.2)

    def _score_logical_expression(self, answer: str) -> float:
        """评分：逻辑表达"""
        # 逻辑连接词
        logical_connectors = [
            "首先", "其次", "然后", "最后", "因此", "所以", "因为", "由于",
            "然而", "但是", "不过", "同时", "另外", "此外", "总而言之",
            "总的来说", "一方面", "另一方面"
        ]

        # 统计逻辑连接词数量
        connector_count = sum(1 for connector in logical_connectors if connector in answer)

        # 检查段落结构
        paragraphs = answer.split('\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])

        # 计算分数
        connector_score = min(1.0, connector_count * 0.2)
        structure_score = min(1.0, paragraph_count * 0.15)

        # 回答连贯性（基于句子长度变化）
        sentences = re.split(r'[。！？；]', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)

        if sentence_count > 1:
            coherence_score = min(1.0, sentence_count * 0.1)
        else:
            coherence_score = 0.2

        total_score = (connector_score + structure_score + coherence_score) / 3

        return min(1.0, total_score)

    def _score_quantitative_results(self, answer: str) -> float:
        """评分：量化成果"""
        # 查找数字
        numbers = re.findall(r'\d+', answer)

        if not numbers:
            return 0.2

        # 查找百分比
        percentages = re.findall(r'\d+%', answer)

        # 查找增长/提升表述
        improvement_indicators = [
            "提升", "提高", "增加", "增长", "减少", "降低", "优化", "改善",
            "从...到...", "达到", "实现", "完成"
        ]

        has_improvement = any(indicator in answer for indicator in improvement_indicators)

        # 计算分数
        number_score = min(1.0, len(numbers) * 0.1)
        percentage_score = len(percentages) * 0.15
        improvement_score = 0.3 if has_improvement else 0.1

        total_score = number_score + percentage_score + improvement_score

        return min(1.0, total_score)

    def _calculate_total_score(self, dimension_scores: Dict[str, float]) -> float:
        """计算总分（0-10）"""
        total = 0.0

        for dimension, score in dimension_scores.items():
            weight = self.score_weights.get(dimension, 0.25)
            total += score * weight

        # 转换为0-10分制
        total_score = total * 10

        return round(total_score, 2)

    def _generate_improvement_suggestions(
        self,
        dimension_scores: Dict[str, float],
        keyword_matches: List[str],
        total_score: float
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 根据各维度分数生成建议
        if dimension_scores.get("skill_coverage", 0) < 0.5:
            suggestions.append("可以更多地提及岗位相关的专业技能和工具使用经验。")

        if dimension_scores.get("case_specificity", 0) < 0.5:
            suggestions.append("建议使用具体的案例来支撑你的观点，包括时间、地点、具体任务和行动。")

        if dimension_scores.get("logical_expression", 0) < 0.5:
            suggestions.append("回答可以更有逻辑性，尝试使用'首先、其次、最后'等连接词来组织思路。")

        if dimension_scores.get("quantitative_results", 0) < 0.5:
            suggestions.append("尽量用量化数据来展示你的成果，如'提升了30%的效率'或'完成了5个项目'。")

        # 如果关键词匹配较少
        if len(keyword_matches) < 2:
            suggestions.append("可以更明确地提到岗位要求的关键技能和知识点。")

        # 如果总分较低
        if total_score < 5:
            suggestions.append("整体回答需要更加具体、有深度，建议结合实际经历进行阐述。")

        # 确保至少有1个建议
        if not suggestions:
            suggestions.append("回答整体不错，可以进一步突出你的独特优势和差异化价值。")

        return suggestions[:3]  # 返回最多3个建议

    def _determine_match_level(self, total_score: float) -> str:
        """决策判定"""
        if total_score >= 7:
            return "通过"
        elif total_score >= 5:
            return "待提升"
        else:
            return "不通过"

    def _generate_detailed_feedback(
        self,
        dimension_scores: Dict[str, float],
        keyword_matches: List[str],
        semantic_similarity: float
    ) -> Dict[str, Any]:
        """生成详细反馈"""
        feedback = {
            "score_breakdown": {
                "skill_coverage": {
                    "score": dimension_scores.get("skill_coverage", 0),
                    "weight": self.score_weights.get("skill_coverage", 0.30),
                    "description": "评估回答是否覆盖了岗位要求的关键技能"
                },
                "case_specificity": {
                    "score": dimension_scores.get("case_specificity", 0),
                    "weight": self.score_weights.get("case_specificity", 0.25),
                    "description": "评估回答中是否包含具体案例和细节"
                },
                "logical_expression": {
                    "score": dimension_scores.get("logical_expression", 0),
                    "weight": self.score_weights.get("logical_expression", 0.25),
                    "description": "评估回答的逻辑性和条理性"
                },
                "quantitative_results": {
                    "score": dimension_scores.get("quantitative_results", 0),
                    "weight": self.score_weights.get("quantitative_results", 0.20),
                    "description": "评估回答中是否包含量化成果和数据支撑"
                }
            },
            "keyword_analysis": {
                "matched_keywords": keyword_matches,
                "match_count": len(keyword_matches),
                "semantic_similarity": round(semantic_similarity, 3)
            },
            "strengths": [],
            "weaknesses": []
        }

        # 分析优势
        strengths = []
        if dimension_scores.get("skill_coverage", 0) >= 0.7:
            strengths.append("较好地覆盖了岗位所需技能")
        if dimension_scores.get("case_specificity", 0) >= 0.7:
            strengths.append("案例具体，有实际细节支撑")
        if dimension_scores.get("logical_expression", 0) >= 0.7:
            strengths.append("逻辑清晰，表达有条理")
        if dimension_scores.get("quantitative_results", 0) >= 0.7:
            strengths.append("量化成果明确，有数据支撑")
        if semantic_similarity >= 0.7:
            strengths.append("回答与问题相关性高")

        # 分析弱点
        weaknesses = []
        if dimension_scores.get("skill_coverage", 0) < 0.5:
            weaknesses.append("岗位技能覆盖不足")
        if dimension_scores.get("case_specificity", 0) < 0.5:
            weaknesses.append("缺乏具体案例支撑")
        if dimension_scores.get("logical_expression", 0) < 0.5:
            weaknesses.append("逻辑表达可以更加清晰")
        if dimension_scores.get("quantitative_results", 0) < 0.5:
            weaknesses.append("量化成果不足")
        if semantic_similarity < 0.5:
            weaknesses.append("回答与问题的相关性有待提高")

        feedback["strengths"] = strengths[:3]
        feedback["weaknesses"] = weaknesses[:3]

        return feedback

    async def evaluate_async(
        self,
        question: str,
        answer: str,
        job_data: Optional[Dict[str, Any]] = None,
        question_data: Optional[Dict[str, Any]] = None
    ) -> EvaluationResult:
        """异步评估回答（带限流）"""
        async with self._semaphore:
            # 在线程池中执行同步方法
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.evaluate(question, answer, job_data, question_data)
            )


# 工具函数：创建回答评估器实例
def create_answer_evaluator(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    max_concurrent_requests: int = 5
) -> AnswerEvaluator:
    """创建回答评估器实例

    Args:
        api_key: API密钥，如未提供则使用配置
        model: 模型名称，如未提供则使用配置
        base_url: API基础URL，如未提供则使用配置
        max_concurrent_requests: 最大并发请求数，用于限流
    """
    return AnswerEvaluator(
        openai_api_key=api_key,
        model=model,
        base_url=base_url,
        max_concurrent_requests=max_concurrent_requests
    )