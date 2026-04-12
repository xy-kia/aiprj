"""
简历解析API端点
实现POST /api/v1/parse-intent-with-resume接口
接收PDF简历文件和求职文本，使用用户配置的LLM API进行分析
"""

import logging
import tempfile
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import UserConfig, User as UserModel
from .config import get_or_create_anonymous_user, get_user_config, decrypt_api_key

import openai
import anthropic

router = APIRouter()
logger = logging.getLogger(__name__)


# 请求/响应模型
class ParseIntentWithResumeRequest(BaseModel):
    """解析请求（用于JSON部分）"""
    raw_input: Optional[str] = None

class ParseIntentWithResumeResponse(BaseModel):
    """解析响应"""
    analysis: Dict[str, Any]  # LLM返回的完整分析结果
    extracted_resume_text: Optional[str] = None  # 提取的简历文本（可摘要）
    keywords: Optional[Dict[str, Any]] = None  # 兼容现有格式的关键词
    confidence: Optional[float] = None


# PDF解析函数
def extract_text_from_pdf(pdf_file: UploadFile) -> str:
    """
    从PDF文件中提取文本
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed. Please install with: pip install pdfplumber")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF processing library not installed"
        )

    text = ""
    try:
        # 将上传的文件保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = pdf_file.file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # 使用pdfplumber提取文本
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        # 删除临时文件
        os.unlink(tmp_path)

        logger.info(f"Extracted {len(text)} characters from PDF")
        return text.strip()

    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to extract text from PDF: {str(e)}"
        )


# LLM调用函数
async def call_llm_with_config(
    prompt: str,
    db: Session,
    user_id: int,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> str:
    """
    使用用户配置的LLM API调用
    """
    config = get_user_config(db, user_id)

    # 如果没有配置或未启用，使用系统默认配置
    if not config or not config.enabled:
        from backend.config.settings import settings
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        provider = "openai"
        model = settings.OPENAI_MODEL
    else:
        api_key = decrypt_api_key(config.api_key)
        base_url = config.base_url
        provider = config.ai_provider
        model = config.default_model
        temperature = config.temperature
        max_tokens = config.max_tokens

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置API密钥"
        )

    # 根据提供商调用不同的API
    if provider == "openai":
        return await call_openai_api(
            api_key, base_url, model, prompt, temperature, max_tokens
        )
    elif provider == "anthropic":
        return await call_anthropic_api(
            api_key, model, prompt, temperature, max_tokens
        )
    elif provider in ["deepseek", "kimi", "qwen", "azure", "custom"]:
        # 这些国内模型通常使用OpenAI兼容的API格式
        return await call_openai_api(
            api_key, base_url, model, prompt, temperature, max_tokens
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的提供商: {provider}"
        )


async def call_openai_api(
    api_key: str,
    base_url: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int
) -> str:
    """调用OpenAI兼容API"""
    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url if base_url != "https://api.openai.com/v1" else None,
            timeout=(30.0, 120.0)
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个求职顾问，帮助分析简历与求职要求的匹配度。"},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content.strip()

    except openai.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API密钥无效或已过期"
        )
    except openai.APIConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="网络连接失败，请检查网络或代理设置"
        )
    except openai.APIError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"未知错误: {str(e)}"
        )


async def call_anthropic_api(
    api_key: str,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int
) -> str:
    """调用Anthropic API"""
    try:
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            system="你是一个求职顾问，帮助分析简历与求职要求的匹配度。",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.content[0].text.strip()

    except anthropic.AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API密钥无效或已过期"
        )
    except anthropic.APIConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNANAVAILABLE,
            detail="网络连接失败，请检查网络或代理设置"
        )
    except anthropic.APIError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"未知错误: {str(e)}"
        )


# 构建LLM提示词
def build_analysis_prompt(resume_text: str, job_intent: Optional[str] = None) -> str:
    """
    构建分析提示词
    """
    prompt = f"""
请分析以下简历内容，并根据求职意向提供匹配度分析和建议。

{'求职意向：' + job_intent if job_intent else '求职意向未提供，请仅分析简历内容。'}

简历内容：
{resume_text[:5000]}  # 限制长度，避免token超出

请提供以下分析：
1. 简历摘要（教育背景、工作经验、技能等）
2. 与求职意向的匹配度（如果提供了求职意向）
3. 技能缺口与建议学习的技能
4. 优化建议（简历改进、求职策略等）
5. 推荐岗位类型（实习/全职、行业、职位等）

请以结构化JSON格式返回分析结果，包含以下字段：
- summary (简历摘要)
- match_score (匹配度得分，0-100)
- matched_skills (匹配的技能列表)
- missing_skills (缺失的技能列表)
- recommendations (优化建议列表)
- suggested_job_types (推荐岗位类型列表)

如果无法提供某项信息，请使用空值。
"""
    return prompt


# 解析LLM返回的JSON（尝试）
def parse_llm_response(llm_response: str) -> Dict[str, Any]:
    """
    尝试解析LLM返回的JSON，如果失败则返回原始文本
    """
    import json
    try:
        # 尝试提取JSON部分（有些LLM会在文本中包含JSON）
        import re
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            return json.loads(json_str)
        else:
            # 如果没有找到JSON，尝试直接解析整个响应
            return json.loads(llm_response)
    except json.JSONDecodeError:
        # 如果无法解析为JSON，返回原始文本
        logger.warning("LLM response is not valid JSON, returning raw text")
        return {"raw_response": llm_response}


# API端点
@router.post("/parse-intent-with-resume", response_model=ParseIntentWithResumeResponse)
async def parse_intent_with_resume(
    resume_file: Optional[UploadFile] = File(None, description="PDF简历文件"),
    raw_input: Optional[str] = Form(None, description="求职意向文本"),
    db: Session = Depends(get_db)
):
    """
    解析简历和求职意向，使用LLM进行分析

    - **resume_file**: PDF格式的简历文件（可选）
    - **raw_input**: 求职意向文本（可选）

    至少需要提供一项（简历文件或求职意向文本）
    """
    if not resume_file and not raw_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要提供简历文件或求职意向文本"
        )

    # 获取或创建匿名用户（与现有配置一致）
    anonymous_user = get_or_create_anonymous_user(db)
    if not anonymous_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="匿名用户ID无效"
        )

    resume_text = ""
    if resume_file:
        # 检查文件类型
        if resume_file.content_type not in ["application/pdf", "application/octet-stream"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持PDF格式的简历文件"
            )

        # 提取文本
        resume_text = extract_text_from_pdf(resume_file)
        logger.info(f"简历文本长度: {len(resume_text)}")

    # 构建提示词
    prompt = build_analysis_prompt(resume_text, raw_input)
    logger.info(f"Prompt length: {len(prompt)}")

    # 调用LLM
    try:
        llm_response = await call_llm_with_config(
            prompt=prompt,
            db=db,
            user_id=anonymous_user.id
        )
        logger.info(f"LLM response received, length: {len(llm_response)}")

        # 尝试解析为结构化数据
        analysis_result = parse_llm_response(llm_response)

        # 为了兼容现有前端，尝试提取关键词
        # 这里可以调用现有的意向解析器来解析求职文本
        keywords = None
        confidence = None
        if raw_input:
            from backend.app.core.intent_parser import create_intent_parser
            try:
                parser = create_intent_parser()
                intent_result = parser.parse(raw_input)
                keywords = intent_result["keywords"]
                confidence = intent_result["confidence"]
            except Exception as e:
                logger.warning(f"Failed to parse intent with local parser: {e}")

        return ParseIntentWithResumeResponse(
            analysis=analysis_result,
            extracted_resume_text=resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text,
            keywords=keywords,
            confidence=confidence
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in parse_intent_with_resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理失败: {str(e)}"
        )