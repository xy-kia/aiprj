"""
意向解析API端点
实现POST /api/v1/parse-intent接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from backend.app.core.intent_parser import create_intent_parser

router = APIRouter()

# 请求/响应模型
class ParseIntentRequest(BaseModel):
    raw_input: str

class ParseIntentResponse(BaseModel):
    keywords: Dict[str, Any]
    confidence: float

@router.post("/parse-intent", response_model=ParseIntentResponse)
async def parse_intent(request: ParseIntentRequest):
    """
    解析用户意向，提取关键词

    - **raw_input**: 用户原始输入文本，如"我想找一份Python开发的实习工作，最好在北京"

    返回解析后的关键词和置信度
    """
    try:
        # 创建解析器实例
        parser = create_intent_parser()

        # 解析用户输入
        result = parser.parse(request.raw_input)

        return ParseIntentResponse(
            keywords=result["keywords"],
            confidence=result["confidence"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"意向解析失败: {str(e)}"
        )