"""
回答评估API端点
实现POST /api/v1/evaluate-answer接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from backend.app.core.answer_evaluator import create_answer_evaluator, EvaluationResult
from sqlalchemy.orm import Session
from fastapi import Depends
from backend.app.db.database import get_db
from backend.app.api.v1.endpoints.config import get_or_create_anonymous_user, get_user_config, decrypt_api_key

router = APIRouter()


# 请求/响应模型
class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str
    job_data: Optional[Dict[str, Any]] = None
    question_data: Optional[Dict[str, Any]] = None


class DimensionScore(BaseModel):
    score: float
    weight: float
    description: str


class DetailedFeedback(BaseModel):
    score_breakdown: Dict[str, DimensionScore]
    keyword_analysis: Dict[str, Any]
    strengths: List[str]
    weaknesses: List[str]


class EvaluateAnswerResponse(BaseModel):
    total_score: float
    match_level: str
    dimension_scores: Dict[str, float]
    keyword_matches: List[str]
    semantic_similarity: float
    improvement_suggestions: List[str]
    detailed_feedback: DetailedFeedback


@router.post("/evaluate-answer", response_model=EvaluateAnswerResponse)
async def evaluate_answer(request: EvaluateAnswerRequest, db: Session = Depends(get_db)):
    """
    评估用户对面试问题的回答

    - **question**: 面试问题
    - **answer**: 用户回答
    - **job_data**: 岗位数据（可选，用于技能匹配）
    - **question_data**: 问题数据（可选，包含target_skill等）

    返回评估结果，包括总分、匹配等级、各维度分数和改进建议
    """
    try:
        # 获取匿名用户配置
        anonymous_user = get_or_create_anonymous_user(db)
        config = get_user_config(db, anonymous_user.id)

        api_key = None
        base_url = None
        model = None

        if config and config.enabled:
            # 解密API密钥
            api_key = decrypt_api_key(config.api_key) if config.api_key else None
            base_url = config.base_url
            model = config.default_model

        # 创建回答评估器
        evaluator = create_answer_evaluator(
            api_key=api_key,
            model=model,
            base_url=base_url
        )

        # 评估回答
        result = evaluator.evaluate(
            question=request.question,
            answer=request.answer,
            job_data=request.job_data,
            question_data=request.question_data
        )

        # 构建详细反馈
        dimension_scores = {}
        for dim_name, dim_data in result.detailed_feedback["score_breakdown"].items():
            dimension_scores[dim_name] = DimensionScore(
                score=dim_data["score"],
                weight=dim_data["weight"],
                description=dim_data["description"]
            )

        detailed_feedback = DetailedFeedback(
            score_breakdown=dimension_scores,
            keyword_analysis=result.detailed_feedback["keyword_analysis"],
            strengths=result.detailed_feedback["strengths"],
            weaknesses=result.detailed_feedback["weaknesses"]
        )

        return EvaluateAnswerResponse(
            total_score=result.total_score,
            match_level=result.match_level,
            dimension_scores=result.dimension_scores,
            keyword_matches=result.keyword_matches,
            semantic_similarity=result.semantic_similarity,
            improvement_suggestions=result.improvement_suggestions,
            detailed_feedback=detailed_feedback
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"回答评估失败: {str(e)}"
        )