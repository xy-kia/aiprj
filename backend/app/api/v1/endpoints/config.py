"""
AI配置API端点
用于管理用户的大模型API配置（OpenAI、Claude等）
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import UserConfig, User as UserModel
from backend.config.settings import settings
from .auth import get_current_active_user, get_user
import openai
import anthropic
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


# 请求/响应模型
class AIProviderConfig(BaseModel):
    """AI提供商配置"""
    provider: str = Field(default="openai", description="AI提供商：openai, anthropic, azure, deepseek, kimi, qwen, custom")
    api_key: str = Field(description="API密钥（前端传输时需加密，后端存储时加密）")
    base_url: str = Field(default="https://api.openai.com/v1", description="API基础URL，可用于国内代理或自建服务")
    default_model: str = Field(default="gpt-4o-mini", description="默认模型")
    enabled: bool = Field(default=True, description="是否启用此配置")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(default=2000, ge=1, le=16384, description="最大token数")


class AIConfigResponse(BaseModel):
    """AI配置响应"""
    id: int
    user_id: int
    provider: str
    base_url: str
    default_model: str
    enabled: bool
    temperature: float
    max_tokens: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ModelInfo(BaseModel):
    """模型信息"""
    id: str
    object: str
    created: Optional[int] = None
    owned_by: Optional[str] = None


class ModelListResponse(BaseModel):
    """模型列表响应"""
    models: List[ModelInfo]
    provider: str


class TestConnectionRequest(BaseModel):
    """测试连接请求"""
    provider: str
    api_key: str
    base_url: str


class TestConnectionResponse(BaseModel):
    """测试连接响应"""
    success: bool
    message: str
    models: Optional[List[str]] = None
    provider: Optional[str] = None


# 工具函数
def get_or_create_anonymous_user(db: Session) -> UserModel:
    """获取或创建匿名用户（用于未认证访问）"""
    anonymous_user = db.query(UserModel).filter(UserModel.username == "anonymous").first()
    if not anonymous_user:
        # 导入密码哈希函数
        from .auth import get_password_hash
        anonymous_user = UserModel(
            username="anonymous",
            email="anonymous@localhost",
            full_name="Anonymous User",
            hashed_password=get_password_hash("anonymous123"),
            is_active=True,
            is_admin=False
        )
        db.add(anonymous_user)
        db.commit()
        db.refresh(anonymous_user)
        logger.info(f"创建匿名用户: {anonymous_user.username}")
    return anonymous_user


def get_user_config(db: Session, user_id: int) -> Optional[UserConfig]:
    """获取用户配置"""
    return db.query(UserConfig).filter(UserConfig.user_id == user_id).first()


def create_or_update_user_config(db: Session, user_id: int, config_data: dict) -> UserConfig:
    """创建或更新用户配置"""
    existing = get_user_config(db, user_id)

    if existing:
        for key, value in config_data.items():
            setattr(existing, key, value)
    else:
        existing = UserConfig(user_id=user_id, **config_data)
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


def encrypt_api_key(api_key: str) -> str:
    """加密API密钥（简单实现，实际生产环境应使用强加密）"""
    # TODO: 使用环境变量中的密钥进行加密
    # 目前暂时返回原值，实际生产环境需要加密存储
    return api_key


def decrypt_api_key(encrypted_key: str) -> str:
    """解密API密钥"""
    # TODO: 解密逻辑
    return encrypted_key


async def test_openai_connection(api_key: str, base_url: str) -> tuple[bool, str, Optional[List[str]]]:
    """测试OpenAI连接并获取模型列表"""
    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=base_url if base_url != "https://api.openai.com/v1" else None
        )

        # 测试连接：获取模型列表
        models_response = client.models.list()
        models = [model.id for model in models_response.data]

        # 过滤出可用的聊天模型
        chat_models = [model for model in models if 'gpt' in model.lower() or 'chat' in model.lower()]

        return True, "连接成功", chat_models[:20]  # 返回前20个模型

    except openai.AuthenticationError:
        return False, "API密钥无效或已过期", None
    except openai.APIConnectionError:
        return False, "网络连接失败，请检查网络或代理设置", None
    except openai.APIError as e:
        return False, f"API错误: {str(e)}", None
    except Exception as e:
        return False, f"未知错误: {str(e)}", None


async def test_anthropic_connection(api_key: str) -> tuple[bool, str, Optional[List[str]]]:
    """测试Anthropic连接并获取模型列表"""
    try:
        client = anthropic.Anthropic(api_key=api_key)

        # 测试连接：发送一个简单的消息或获取模型列表
        # Anthropic API 没有直接的模型列表端点，我们可以发送一个简单的消息来测试连接
        # 但我们可以返回一些已知的模型
        known_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]

        # 尝试发送一个简单的消息来验证连接
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hello"}]
            )
            return True, "连接成功", known_models
        except anthropic.AuthenticationError:
            return False, "API密钥无效或已过期", None
        except anthropic.APIConnectionError:
            return False, "网络连接失败，请检查网络或代理设置", None
        except anthropic.APIError as e:
            return False, f"API错误: {str(e)}", None

    except Exception as e:
        return False, f"未知错误: {str(e)}", None


# API端点
@router.get("/ai-config", response_model=AIConfigResponse)
async def get_ai_config(
    db: Session = Depends(get_db)
):
    """
    获取AI配置（匿名用户）
    """
    # 获取或创建匿名用户
    anonymous_user = get_or_create_anonymous_user(db)

    if not anonymous_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="匿名用户ID无效"
        )

    config = get_user_config(db, anonymous_user.id)

    if not config:
        # 返回默认配置
        return AIConfigResponse(
            id=0,
            user_id=anonymous_user.id,
            provider="openai",
            base_url=settings.OPENAI_BASE_URL,
            default_model=settings.OPENAI_MODEL,
            enabled=False,
            temperature=0.7,
            max_tokens=2000
        )

    return AIConfigResponse(
        id=config.id,
        user_id=config.user_id,
        provider=config.ai_provider,
        base_url=config.base_url,
        default_model=config.default_model,
        enabled=config.enabled,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None
    )


@router.post("/ai-config", response_model=AIConfigResponse)
async def update_ai_config(
    config: AIProviderConfig,
    db: Session = Depends(get_db)
):
    """
    更新AI配置（匿名用户）
    """
    # 获取或创建匿名用户
    anonymous_user = get_or_create_anonymous_user(db)

    if not anonymous_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="匿名用户ID无效"
        )

    # 加密API密钥
    encrypted_key = encrypt_api_key(config.api_key)

    config_data = {
        "ai_provider": config.provider,
        "api_key": encrypted_key,
        "base_url": config.base_url,
        "default_model": config.default_model,
        "enabled": config.enabled,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens
    }

    user_config = create_or_update_user_config(db, anonymous_user.id, config_data)

    return AIConfigResponse(
        id=user_config.id,
        user_id=user_config.user_id,
        provider=user_config.ai_provider,
        base_url=user_config.base_url,
        default_model=user_config.default_model,
        enabled=user_config.enabled,
        temperature=user_config.temperature,
        max_tokens=user_config.max_tokens,
        created_at=user_config.created_at.isoformat() if user_config.created_at else None,
        updated_at=user_config.updated_at.isoformat() if user_config.updated_at else None
    )


@router.post("/ai-config/test-connection", response_model=TestConnectionResponse)
async def test_ai_connection(
    request: TestConnectionRequest
):
    """
    测试AI API连接并获取可用模型列表
    """
    provider = request.provider.lower()

    if provider == "openai":
        success, message, models = await test_openai_connection(
            request.api_key,
            request.base_url
        )
    elif provider == "anthropic":
        # Anthropic 可以使用自定义基础URL（例如国内代理）
        # 如果base_url是默认的OpenAI URL，则使用Anthropic官方URL
        if request.base_url == "https://api.openai.com/v1":
            # 使用默认的Anthropic URL，但Anthropic客户端目前不支持自定义base_url
            # 我们将忽略base_url，使用官方客户端
            success, message, models = await test_anthropic_connection(request.api_key)
        else:
            # 如果有自定义base_url，可能是Anthropic的反代
            # 目前Anthropic Python SDK不支持自定义base_url，我们暂时使用官方客户端测试
            # 但可以尝试使用自定义URL，这里简化处理
            success, message, models = await test_anthropic_connection(request.api_key)
    elif provider in ["deepseek", "kimi", "qwen", "azure", "custom"]:
        # Azure OpenAI和自定义OpenAI兼容API使用OpenAI客户端
        success, message, models = await test_openai_connection(
            request.api_key,
            request.base_url
        )
    else:
        return TestConnectionResponse(
            success=False,
            message=f"暂不支持 {request.provider} 提供商"
        )

    if success:
        return TestConnectionResponse(
            success=True,
            message=message,
            models=models,
            provider=request.provider
        )
    else:
        return TestConnectionResponse(
            success=False,
            message=message
        )


@router.get("/ai-config/models", response_model=ModelListResponse)
async def get_available_models(
    db: Session = Depends(get_db)
):
    """
    获取可用模型列表（匿名用户）
    """
    # 获取或创建匿名用户
    anonymous_user = get_or_create_anonymous_user(db)

    if not anonymous_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="匿名用户ID无效"
        )

    config = get_user_config(db, anonymous_user.id)

    # 如果没有配置或未启用，使用系统默认配置
    if not config or not config.enabled:
        api_key = settings.OPENAI_API_KEY
        base_url = settings.OPENAI_BASE_URL
        provider = "openai"
    else:
        api_key = decrypt_api_key(config.api_key)
        base_url = config.base_url
        provider = config.ai_provider

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未配置API密钥"
        )

    # 根据提供商调用不同的测试函数
    if provider == "openai":
        success, message, models = await test_openai_connection(api_key, base_url)
    elif provider == "anthropic":
        success, message, models = await test_anthropic_connection(api_key)
    elif provider in ["deepseek", "kimi", "qwen", "azure", "custom"]:
        # DeepSeek、Kimi、通义千问、Azure OpenAI和自定义OpenAI兼容API
        # 这些国内模型通常使用OpenAI兼容的API格式
        success, message, models = await test_openai_connection(api_key, base_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的提供商: {provider}"
        )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # 转换模型信息
    model_infos = [ModelInfo(id=model_id, object="model", owned_by=provider) for model_id in models]

    return ModelListResponse(
        models=model_infos,
        provider=provider
    )