"""
管理员认证API端点
实现JWT token认证，权限控制
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# 模拟用户数据库（存储明文密码，在获取时哈希）
# 注意：这是演示用的内存数据库，生产环境应使用真实数据库并存储预哈希密码
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "password": "admin123",  # 明文存储，验证时哈希
        "role": "admin",
        "permissions": ["all"],
        "disabled": False
    },
    "operator": {
        "username": "operator",
        "full_name": "Operator",
        "email": "operator@example.com",
        "password": "operator123",  # 明文存储，验证时哈希
        "role": "operator",
        "permissions": ["dashboard", "crawler_monitor", "knowledge_management"],
        "disabled": False
    }
}

# 缓存哈希后的密码
_hashed_password_cache = {}


# 模型定义
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    permissions: list[str] = []
    disabled: Optional[bool] = None


class UserInDB(User):
    hashed_password: str = ""
    password: str = ""  # 用于明文存储时的字段


# 工具函数
def verify_password(plain_password, hashed_password):
    """验证密码，处理空值情况"""
    if not hashed_password:
        return False
    try:
        # 限制密码长度不超过72字节（bcrypt限制）
        plain_bytes = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
        if len(plain_bytes) > 72:
            plain_password = plain_bytes[:72].decode('utf-8', errors='ignore')
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


def get_password_hash(password):
    """获取密码哈希，限制长度不超过72字节"""
    # 限制密码长度不超过72字节（bcrypt限制）
    password_bytes = password.encode('utf-8') if isinstance(password, str) else password
    if len(password_bytes) > 72:
        password = password_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def get_user_hashed_password(username: str) -> str:
    """获取用户的哈希密码（使用缓存避免重复哈希计算）"""
    global _hashed_password_cache

    if username in _hashed_password_cache:
        return _hashed_password_cache[username]

    if username not in fake_users_db:
        return ""

    user_dict = fake_users_db[username]
    plain_password = user_dict.get("password", "")

    if not plain_password:
        return ""

    # 计算哈希并缓存
    try:
        hashed = get_password_hash(plain_password)
        _hashed_password_cache[username] = hashed
        return hashed
    except Exception as e:
        logger.error(f"Failed to hash password for user {username}: {e}")
        return ""


def get_user(db, username: str):
    if username in db:
        user_dict = db[username].copy()
        # 将明文密码替换为哈希密码
        user_dict["hashed_password"] = get_user_hashed_password(username)
        # 移除明文密码字段
        user_dict.pop("password", None)
        return UserInDB(**user_dict)
    return None


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def check_permission(user: User, permission: str):
    if "all" in user.permissions:
        return True
    if permission in user.permissions:
        return True
    return False


# API端点
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.post("/refresh")
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "role": current_user.role},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
async def logout():
    # 在实际应用中，您可能需要将token加入黑名单
    return {"message": "Successfully logged out"}


# 权限检查端点
@router.get("/check-permission/{permission}")
async def check_user_permission(
    permission: str,
    current_user: User = Depends(get_current_active_user)
):
    has_permission = await check_permission(current_user, permission)
    return {
        "has_permission": has_permission,
        "user": current_user.username,
        "permission": permission
    }