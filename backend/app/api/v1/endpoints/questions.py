"""
问题生成API端点
实现POST /api/v1/generate-questions接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List

from backend.app.core.question_generator import create_question_generator, InterviewQuestion

router = APIRouter()


# 请求/响应模型
class GenerateQuestionsRequest(BaseModel):
    job_data: Dict[str, Any]
    question_type: Optional[str] = "intern_general"  # intern_general 或 intern_advanced
    num_questions: Optional[int] = 8


class QuestionResponse(BaseModel):
    question: str
    question_type: str
    target_skill: Optional[str] = None
    jd_reference: Optional[str] = None
    suggested_time: int
    difficulty: str
    scoring_criteria: Optional[List[str]] = None


class GenerateQuestionsResponse(BaseModel):
    questions: List[QuestionResponse]
    total_count: int
    question_type: str


@router.post("/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_questions(request: GenerateQuestionsRequest):
    """
    基于岗位JD生成面试问题

    - **job_data**: 岗位数据（包含title、company、description、requirements、skills等）
    - **question_type**: 问题类型，可选 "intern_general"（一般实习）或 "intern_advanced"（高阶实习/校招）
    - **num_questions**: 生成的问题数量

    返回生成的面试问题列表
    """
    try:
        # 创建问题生成器
        generator = create_question_generator()

        # 生成问题
        interview_questions = generator.generate_questions(
            job_data=request.job_data,
            question_type=request.question_type or "intern_general",
            num_questions=request.num_questions or 8
        )

        # 转换为响应模型
        questions_response = []
        for q in interview_questions:
            question_resp = QuestionResponse(
                question=q.question,
                question_type=q.question_type,
                target_skill=q.target_skill,
                jd_reference=q.jd_reference,
                suggested_time=q.suggested_time,
                difficulty=q.difficulty,
                scoring_criteria=q.scoring_criteria
            )
            questions_response.append(question_resp)

        return GenerateQuestionsResponse(
            questions=questions_response,
            total_count=len(questions_response),
            question_type=request.question_type or "intern_general"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"问题生成失败: {str(e)}"
        )