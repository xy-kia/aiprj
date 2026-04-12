"""
岗位搜索API端点
实现POST /api/v1/search-jobs接口
支持使用用户配置的AI API进行搜索和解析
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import asyncio
import sys
from sqlalchemy.orm import Session

from backend.app.core.search_scheduler import create_search_scheduler
from backend.app.core.match_calculator import create_match_calculator
from backend.crawlers.boss_crawler import BOSSCrawler
from backend.crawlers.test_crawler import TestCrawler
from backend.crawlers.liepin_crawler import LiepinCrawler
from backend.app.api.v1.endpoints.auth import get_current_user_optional
from backend.app.db.database import get_db
from backend.app.db.models import UserConfig, User
# 注意：其他爬虫需要实际实现

router = APIRouter()


# 请求/响应模型
class KeywordsModel(BaseModel):
    skills: List[str] = []
    job_types: List[str] = []
    locations: List[str] = []
    experiences: List[str] = []
    educations: List[str] = []

class SearchJobsRequest(BaseModel):
    keywords: KeywordsModel
    page: Optional[int] = 1
    page_size: Optional[int] = 10
    filters: Optional[Dict[str, Any]] = None


class JobItemResponse(BaseModel):
    id: int
    source: str
    title: str
    company: str
    location: str
    salary: str
    experience: str
    education: str
    job_type: str
    description: str
    skills: List[str]
    url: str

class SearchJobsResponse(BaseModel):
    jobs: List[JobItemResponse]
    total: int
    page: int
    page_size: int
    match_results: Optional[List[Dict[str, Any]]] = None


def get_user_config_by_username(db: Session, username: str) -> Optional[UserConfig]:
    """通过用户名获取用户配置"""
    # 首先通过用户名查找用户ID
    from backend.app.db.models import User
    user = db.query(User).filter(User.username == username).first()
    if user:
        # 然后查找用户配置
        return db.query(UserConfig).filter(UserConfig.user_id == user.id).first()
    return None


@router.post("/search-jobs", response_model=SearchJobsResponse)
async def search_jobs(
    request: SearchJobsRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    搜索岗位并计算匹配度
    使用当前用户的AI配置进行搜索和解析（如果已配置）
    允许匿名访问，但如果用户已登录且配置了AI API，则使用用户配置

    - **keywords**: 结构化关键词（技能、岗位类型、地点等）
    - **page**: 页码
    - **page_size**: 每页数量
    - **filters**: 额外过滤条件

    返回搜索到的岗位列表和匹配度结果
    """
    try:
        # 获取用户AI配置
        user_config = None
        if current_user and hasattr(current_user, 'username'):
            user_config = get_user_config_by_username(db, current_user.username)
            if user_config:
                print(f"[DEBUG] 找到认证用户AI配置，用户名: {current_user.username}, 启用状态: {user_config.enabled}", file=sys.stderr)
            else:
                print(f"[DEBUG] 未找到认证用户AI配置，使用系统默认配置", file=sys.stderr)
        else:
            # 尝试获取匿名用户配置
            print(f"[DEBUG] 当前用户未认证，尝试获取匿名用户配置", file=sys.stderr)
            anonymous_user = db.query(User).filter(User.username == "anonymous").first()
            if anonymous_user:
                user_config = get_user_config_by_username(db, "anonymous")
                if user_config:
                    print(f"[DEBUG] 找到匿名用户AI配置，启用状态: {user_config.enabled}", file=sys.stderr)
                else:
                    print(f"[DEBUG] 未找到匿名用户AI配置", file=sys.stderr)
            else:
                print(f"[DEBUG] 匿名用户不存在", file=sys.stderr)

        # 创建爬虫实例（这里只使用BOSS直聘作为示例）
        # 实际项目中应初始化所有平台的爬虫
        crawlers = [
            BOSSCrawler(
                use_proxy=False,
                headless=True,
                user_config=user_config  # 传递用户配置给爬虫
            ),
            LiepinCrawler(
                use_proxy=False,
                headless=True,
                user_config=user_config  # 传递用户配置给爬虫
            ),
            TestCrawler(user_config=user_config)  # 测试爬虫也传递配置
            # 可添加其他爬虫：ZhaopinCrawler(), QianchengCrawler()
        ]
        print(f"[DEBUG] 创建了 {len(crawlers)} 个爬虫: {[c.platform for c in crawlers]}", file=sys.stderr)

        # 创建搜索调度器
        scheduler = create_search_scheduler(crawlers)

        # 构建搜索关键词：将技能组合成搜索词
        search_keyword = " ".join(request.keywords.skills) if request.keywords.skills else "实习"

        # 如果有岗位类型，添加到关键词中
        if request.keywords.job_types:
            search_keyword = f"{search_keyword} {request.keywords.job_types[0]}"

        # 确定城市：使用第一个地点
        city = request.keywords.locations[0] if request.keywords.locations else None

        # 构建过滤条件（合并keywords中的条件和额外的filters）
        all_filters = {}
        if request.filters:
            all_filters.update(request.filters)

        # 添加keywords中的过滤条件
        if request.keywords.job_types:
            all_filters["job_types"] = request.keywords.job_types
        if request.keywords.locations:
            all_filters["locations"] = request.keywords.locations
        if request.keywords.experiences:
            # 将经验要求转换为过滤器
            all_filters["experience"] = request.keywords.experiences[0]
        if request.keywords.educations:
            all_filters["education"] = request.keywords.educations[0]

        # 执行搜索
        print(f"[DEBUG] 搜索开始: keyword={search_keyword}, city={city}", file=sys.stderr)
        jobs = await scheduler.search(
            keyword=search_keyword,
            city=city,
            page_limit=3  # 每平台最大页数
        )
        print(f"[DEBUG] 搜索完成，获取到 {len(jobs)} 个岗位", file=sys.stderr)

        # 过滤岗位（如果提供了过滤条件）
        if all_filters:
            jobs = scheduler.filter_jobs(jobs, all_filters)

        # 如果没有任何岗位，使用TestCrawler作为后备
        if not jobs:
            print(f"[DEBUG] 没有获取到岗位，使用TestCrawler后备方案", file=sys.stderr)
            test_crawler = TestCrawler()
            # TestCrawler的search_jobs是同步生成器，需要转换为列表
            test_jobs = list(test_crawler.search_jobs(search_keyword, city, page=1))
            print(f"[DEBUG] TestCrawler获取到 {len(test_jobs)} 个岗位", file=sys.stderr)
            if test_jobs:
                jobs = test_jobs

        # 转换为字典列表，匹配前端接口
        jobs_data = []
        for i, job in enumerate(jobs):
            # 构建薪资字符串
            salary_str = ""
            if job.salary_min and job.salary_max:
                salary_str = f"{job.salary_min}-{job.salary_max}K"
            elif job.salary_min:
                salary_str = f"{job.salary_min}K以上"
            elif job.salary_max:
                salary_str = f"{job.salary_max}K以下"
            else:
                salary_str = "面议"

            job_dict = {
                "id": i + 1,  # 前端期望数字ID
                "source": job.source.lower() if job.source else "unknown",
                "title": job.title or "",
                "company": job.company or "",
                "location": job.location or "",
                "salary": salary_str,
                "experience": job.experience or "无经验",
                "education": job.education or "不限",
                "job_type": job.job_type or "实习",
                "description": job.description or "",
                "skills": job.skills or [],
                "url": job.url or ""
            }
            jobs_data.append(job_dict)

        # 使用关键词计算匹配度
        match_results = None
        if request.keywords and jobs_data:
            calculator = create_match_calculator()
            # 将keywords转换为user_intent格式供匹配计算器使用
            user_intent = {
                "skills": request.keywords.skills,
                "job_types": request.keywords.job_types,
                "locations": request.keywords.locations,
                "experiences": request.keywords.experiences,
                "educations": request.keywords.educations
            }
            match_results = calculator.batch_calculate(
                user_intent=user_intent,
                jobs_data=jobs_data,
                top_k=min(20, len(jobs_data))
            )

        # 分页处理
        page = request.page or 1
        page_size = request.page_size or 10
        total = len(jobs_data)

        # 计算分页范围
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_jobs = jobs_data[start_idx:end_idx]

        # 将字典转换为JobItemResponse对象
        job_responses = []
        for job_dict in paginated_jobs:
            # 确保数据类型正确
            job_response = JobItemResponse(
                id=job_dict["id"],
                source=job_dict["source"],
                title=job_dict["title"],
                company=job_dict["company"],
                location=job_dict["location"],
                salary=job_dict["salary"],
                experience=job_dict["experience"],
                education=job_dict["education"],
                job_type=job_dict["job_type"],
                description=job_dict["description"],
                skills=job_dict["skills"],
                url=job_dict["url"]
            )
            job_responses.append(job_response)

        return SearchJobsResponse(
            jobs=job_responses,
            total=total,
            page=page,
            page_size=page_size,
            match_results=match_results
        )

    except Exception as e:
        import traceback
        print(f"[ERROR] 岗位搜索异常: {str(e)}", file=sys.stderr)
        print(f"[ERROR] 异常堆栈:\n{traceback.format_exc()}", file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"岗位搜索失败: {str(e)}"
        )