"""
数据模型定义
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    search_histories = relationship("SearchHistory", back_populates="user")
    evaluation_records = relationship("EvaluationRecord", back_populates="user")


class SearchHistory(Base):
    """搜索历史表"""
    __tablename__ = "search_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    raw_query = Column(Text, nullable=False)
    parsed_keywords = Column(JSON)  # 解析后的关键词
    search_results = Column(JSON)  # 搜索结果
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="search_histories")


class Job(Base):
    """岗位表（从爬虫获取）"""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)  # 来源平台：boss、zhaopin等
    job_id = Column(String(100), unique=True, nullable=False)  # 平台原始ID
    title = Column(String(200), nullable=False)
    company = Column(String(200), nullable=False)
    location = Column(String(100))
    salary = Column(String(100))
    experience = Column(String(100))
    education = Column(String(100))
    job_type = Column(String(50))  # 全职、实习、兼职等
    description = Column(Text)
    requirements = Column(Text)
    skills = Column(JSON)  # 技能列表
    tags = Column(JSON)  # 标签
    url = Column(String(500))
    published_at = Column(DateTime(timezone=True))
    crawled_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # 关系
    evaluations = relationship("EvaluationRecord", back_populates="job")


class EvaluationRecord(Base):
    """评估记录表"""
    __tablename__ = "evaluation_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    question_set = Column(JSON, nullable=False)  # 问题集
    user_answers = Column(JSON, nullable=False)  # 用户答案
    evaluation_results = Column(JSON, nullable=False)  # 评估结果
    overall_score = Column(Float, nullable=False)
    feedback = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    user = relationship("User", back_populates="evaluation_records")
    job = relationship("Job", back_populates="evaluations")


class Skill(Base):
    """技能库表"""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))
    description = Column(Text)
    synonyms = Column(JSON)  # 同义词列表
    related_skills = Column(JSON)  # 相关技能
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR等
    module = Column(String(100))
    message = Column(Text, nullable=False)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserConfig(Base):
    """用户配置表（存储AI API配置等）"""
    __tablename__ = "user_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # AI API配置
    ai_provider = Column(String(50), default="openai")  # openai, anthropic, azure, custom
    api_key = Column(String(500))  # 加密存储
    base_url = Column(String(500), default="https://api.openai.com/v1")
    default_model = Column(String(100), default="gpt-4o-mini")

    # 是否启用自定义配置（如禁用则使用系统默认）
    enabled = Column(Boolean, default=False)

    # 其他配置
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=2000)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # 关系
    user = relationship("User")