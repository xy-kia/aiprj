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
from sqlalchemy.orm import Session

from backend.config.settings import settings
from backend.app.db.database import get_db
from backend.app.db.models import User as UserModel

logger = logging.getLogger(__name__)

router = APIRouter()

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# 默认用户数据（如果数据库中不存在则创建）
DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Administrator",
        "password": "admin123",  # 明文，将在创建时哈希
        "role": "admin",
        "permissions": ["all"],
        "disabled": False
    },
    {
        "username": "operator",
        "email": "operator@example.com",
        "full_name": "Operator",
        "password": "operator123",  # 明文，将在创建时哈希
        "role": "operator",
        "permissions": ["dashboard", "crawler_monitor", "knowledge_management"],
        "disabled": False
    },
    {
        "username": "anonymous",
        "email": "anonymous@localhost",
        "full_name": "Anonymous User",
        "password": "anonymous123",  # 明文，将在创建时哈希
        "role": "anonymous",
        "permissions": [],  # 无特殊权限
        "disabled": False
    }
]


# 模型定义
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class User(BaseModel):
    id: Optional[int] = None  # 用户ID
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
        # 检查哈希格式
        if hashed_password.startswith("sha256$"):
            # 使用sha256验证（简化测试版本）
            import hashlib
            salt = "internship_assistant_salt_2024"
            password_str = str(plain_password)
            combined = salt + password_str
            test_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
            expected_hash = hashed_password[7:]  # 去掉"sha256$"前缀
            return test_hash == expected_hash
        else:
            # 可能是bcrypt格式，尝试使用pwd_context
            # 限制密码长度不超过72字节（bcrypt限制）
            plain_bytes = plain_password.encode('utf-8') if isinstance(plain_password, str) else plain_password
            if len(plain_bytes) > 72:
                plain_password = plain_bytes[:72].decode('utf-8', errors='ignore')
            return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.warning(f"Password verification failed: {e}")
        return False


def get_password_hash(password):
    """获取密码哈希（简化版本用于测试）"""
    # 生产环境应使用bcrypt，这里使用sha256作为测试
    import hashlib
    # 使用固定盐进行测试
    salt = "internship_assistant_salt_2024"
    password_str = str(password)
    # 组合盐和密码
    combined = salt + password_str
    # 生成哈希
    hashed = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    # 返回格式：sha256$hash
    return f"sha256${hashed}"


def get_user_by_username(db: Session, username: str):
    """从数据库获取用户"""
    return db.query(UserModel).filter(UserModel.username == username).first()


def get_user(db: Session, username: str):
    """兼容性函数，保持原有接口"""
    user = get_user_by_username(db, username)
    if not user:
        return None

    # 转换为UserInDB格式
    user_dict = {
        "id": user.id,  # 添加用户ID
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": "admin" if user.is_admin else "user",  # 根据is_admin字段确定角色
        "permissions": ["all"] if user.is_admin else [],  # 简单权限映射
        "disabled": not user.is_active,
        "hashed_password": user.hashed_password
    }
    return UserInDB(**user_dict)


def authenticate_user(db: Session, username: str, password: str):
    user = get_user(db, username)
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


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None or token.strip() == "":
        raise credentials_exception
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
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
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
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


# 初始化默认用户
def init_default_users():
    """初始化默认用户（如果不存在）"""
    from backend.app.db.database import get_db_session
    try:
        with get_db_session() as db:
            for user_data in DEFAULT_USERS:
                existing = db.query(UserModel).filter(UserModel.username == user_data["username"]).first()
                if not existing:
                    hashed_password = get_password_hash(user_data["password"])
                    new_user = UserModel(
                        username=user_data["username"],
                        email=user_data["email"],
                        full_name=user_data["full_name"],
                        hashed_password=hashed_password,
                        is_active=not user_data["disabled"],
                        is_admin=(user_data["role"] == "admin")
                    )
                    db.add(new_user)
                    db.commit()
                    logger.info(f"创建默认用户: {user_data['username']}")
    except Exception as e:
        logger.error(f"初始化默认用户失败: {e}")


# 应用启动时初始化默认用户（注释掉，可以在main.py中调用）
# init_default_users()


async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    获取当前用户（可选），如果未认证则返回None
    """
    if not token or token.strip() == "":
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            return None
        token_data = TokenData(username=username)
        user = get_user(db, username=token_data.username)
        return user
    except (JWTError, HTTPException):
        # JWT解码失败或用户不存在
        return None
    except Exception:
        # 其他异常
        return None