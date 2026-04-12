"""
智联招聘爬虫实现
调用JSON接口，效率更高

参考文档：Workflow.md 第2.4节、Functional_Spec.md 第2.2节
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional, Generator
from urllib.parse import urlencode

from .base import APICrawler, JobItem


class ZhaopinCrawler(APICrawler):
    """智联招聘爬虫"""

    platform = "智联招聘"
    base_url = "https://fe-api.zhaopin.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api_base = f"{self.base_url}/c/i/sou"

        # 智联招聘API配置
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.zhaopin.com/",
            "Origin": "https://www.zhaopin.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 城市代码映射（智联招聘使用数字代码）
        self.city_code_map = {
            "北京": "530",
            "上海": "538",
            "广州": "763",
            "深圳": "765",
            "杭州": "653",
            "成都": "801",
            "武汉": "736",
            "南京": "635",
        }

    def search_jobs(
        self,
        keyword: str,
        city: Optional[str] = None,
        page: int = 1,
        **filters
    ) -> Generator[JobItem, None, None]:
        """
        搜索岗位

        Args:
            keyword: 搜索关键词
            city: 城市名称
            page: 页码
            **filters: 额外过滤条件

        Yields:
            JobItem: 岗位数据
        """
        # 智联招聘需要异步执行，这里调用异步版本
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            async def _async_search():
                jobs = []
                async for job in self.async_search_jobs(keyword, city, page, **filters):
                    jobs.append(job)
                return jobs

            jobs = loop.run_until_complete(_async_search())

            for job in jobs:
                yield job

        finally:
            loop.close()

    async def async_search_jobs(
        self,
        keyword: str,
        city: Optional[str] = None,
        page: int = 1,
        **filters
    ) -> Generator[JobItem, None, None]:
        """
        异步搜索岗位

        Args:
            keyword: 搜索关键词
            city: 城市名称
            page: 页码
            **filters: 额外过滤条件

        Yields:
            JobItem: 岗位数据
        """
        try:
            # 构建API请求参数
            params = self._build_search_params(keyword, city, page, filters)

            self.logger.info(f"搜索智联招聘: keyword={keyword}, city={city}, page={page}")

            # 调用API
            response_data = await self.fetch_api("", params=params)

            if not response_data:
                self.logger.warning("智联招聘API返回空数据")
                return

            # 解析响应数据
            job_list = self.parse_api_response(response_data)

            # 生成JobItem
            for job_data in job_list:
                try:
                    job = self._create_job_item(job_data)
                    yield job
                except Exception as e:
                    self.logger.error(f"处理岗位数据失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"智联招聘搜索失败: {e}")
            # 返回空，不抛出异常，避免影响其他爬虫

    def _build_search_params(
        self,
        keyword: str,
        city: Optional[str],
        page: int,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建搜索参数"""
        params = {
            "pageSize": 90,  # 每页数量
            "cityId": self.city_code_map.get(city or "北京", "530"),  # 默认北京
            "workExperience": -1,  # 工作经验不限
            "education": -1,  # 学历不限
            "companyType": -1,  # 公司类型不限
            "employmentType": -1,  # 雇佣类型不限
            "jobWelfareTag": -1,  # 福利标签不限
            "kw": keyword,  # 关键词
            "kt": 3,  # 搜索类型
            "at": "2e37457b5bf54844ab1e9b0967c4d0a7",  # 固定参数
            "rt": "2764f6b3f17d4593a26acf6b7d7e2c6c",  # 固定参数
            "_v": "0.1.0",  # 版本
            "x-zp-page-request-id": "a1b2c3d4e5f67890",  # 请求ID
            "x-zp-client-id": "12345678-90ab-cdef-1234-567890abcdef",  # 客户端ID
        }

        # 添加页码
        params["start"] = (page - 1) * params["pageSize"]

        # 添加过滤条件
        if "salary" in filters:
            salary_map = {
                "0-3k": "1001", "3-5k": "1002", "5-8k": "1003",
                "8-10k": "1004", "10-15k": "1005", "15-20k": "1006",
                "20-30k": "1007", "30-50k": "1008", "50k以上": "1009"
            }
            if filters["salary"] in salary_map:
                params["salary"] = salary_map[filters["salary"]]

        if "experience" in filters:
            exp_map = {
                "不限": "-1", "应届生": "102", "1年以内": "103",
                "1-3年": "305", "3-5年": "306", "5-10年": "307", "10年以上": "308"
            }
            if filters["experience"] in exp_map:
                params["workExperience"] = exp_map[filters["experience"]]

        if "education" in filters:
            edu_map = {
                "不限": "-1", "高中": "7", "大专": "5", "本科": "4",
                "硕士": "3", "博士": "1"
            }
            if filters["education"] in edu_map:
                params["education"] = edu_map[filters["education"]]

        return params

    def parse_api_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解析API响应

        Args:
            response_data: API返回的JSON数据

        Returns:
            岗位数据列表
        """
        jobs = []

        try:
            # 智联招聘API数据结构
            data = response_data.get("data", {})
            results = data.get("results", [])

            for item in results:
                job = self._parse_job_item(item)
                if job:
                    jobs.append(job)

        except Exception as e:
            self.logger.error(f"解析API响应失败: {e}")

        return jobs

    def _parse_job_item(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析单个岗位数据"""
        try:
            # 提取基本信息
            job_id = item.get("number", "")
            title = item.get("jobName", "")
            company = item.get("company", {}).get("name", "")

            # 薪资信息
            salary = item.get("salary", "")
            salary_min, salary_max, _ = self._parse_salary(salary)

            # 地点
            city = item.get("city", {}).get("display", "")

            # 经验要求
            working_exp = item.get("workingExp", {}).get("name", "不限")

            # 学历要求
            edu_level = item.get("eduLevel", {}).get("name", "不限")

            # 职位描述
            job_detail = self._extract_job_detail(item)

            # 技能标签
            skills = self._extract_skills(item)

            # 构建岗位数据
            job_data = {
                "id": f"zhaopin_{job_id}",
                "title": title,
                "company": company,
                "location": city,
                "salary_text": salary,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "experience": working_exp,
                "education": edu_level,
                "description": job_detail.get("description", ""),
                "requirements": job_detail.get("requirements", []),
                "skills": skills,
                "url": f"https://www.zhaopin.com/job/{job_id}.html" if job_id else ""
            }

            return job_data

        except Exception as e:
            self.logger.warning(f"解析岗位项失败: {e}")
            return None

    def _parse_salary(self, salary_text: str) -> tuple:
        """解析薪资文本"""
        from .cleaning_rules import clean_salary
        return clean_salary(salary_text)

    def _extract_job_detail(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """提取职位详情"""
        detail = {
            "description": "",
            "requirements": []
        }

        try:
            # 职位描述
            job_detail = item.get("jobDetail", "")
            detail["description"] = job_detail

            # 职位要求
            requirement = item.get("jobRequirement", "")
            if requirement:
                # 将要求文本分割为列表
                requirements = re.split(r'[;；。.]', requirement)
                detail["requirements"] = [req.strip() for req in requirements if req.strip()]

        except Exception as e:
            self.logger.warning(f"提取职位详情失败: {e}")

        return detail

    def _extract_skills(self, item: Dict[str, Any]) -> List[str]:
        """提取技能标签"""
        skills = []

        try:
            # 从职位标签中提取
            job_tags = item.get("jobTag", {}).get("searchTag", [])
            if isinstance(job_tags, list):
                skills.extend(job_tags)

            # 从职位描述中提取关键词
            job_detail = item.get("jobDetail", "")
            if job_detail:
                # 简单的关键词提取（实际项目应使用NLP）
                tech_keywords = [
                    "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "C",
                    "Vue.js", "React", "Angular", "Node.js", "Spring", "Django", "Flask",
                    "MySQL", "Redis", "MongoDB", "Docker", "Kubernetes", "Git", "Linux",
                    "AWS", "机器学习", "深度学习", "数据分析", "SQL", "算法", "数据结构"
                ]

                for keyword in tech_keywords:
                    if keyword in job_detail:
                        skills.append(keyword)

        except Exception as e:
            self.logger.warning(f"提取技能失败: {e}")

        # 去重
        return list(set(skills))

    def _create_job_item(self, job_data: Dict[str, Any]) -> JobItem:
        """创建JobItem对象"""
        # 数据清洗
        cleaned_data = self.clean_data(job_data)

        # 创建JobItem
        job = JobItem(
            id=cleaned_data.get("id", ""),
            title=cleaned_data.get("title", ""),
            company=cleaned_data.get("company", ""),
            location=cleaned_data.get("location", ""),
            job_type=cleaned_data.get("job_type", "实习"),
            salary_min=cleaned_data.get("salary_min"),
            salary_max=cleaned_data.get("salary_max"),
            education=cleaned_data.get("education", "不限"),
            experience=cleaned_data.get("experience", "不限"),
            description=cleaned_data.get("description", ""),
            requirements=cleaned_data.get("requirements", []),
            skills=cleaned_data.get("skills", []),
            source=self.platform,
            url=cleaned_data.get("url", ""),
            raw_data=job_data
        )

        return job

    def parse_job_detail(self, job_id: str) -> Optional[JobItem]:
        """
        获取岗位详情

        Args:
            job_id: 岗位ID（格式: zhaopin_数字）

        Returns:
            JobItem或None
        """
        # 提取原始ID
        original_id = job_id.replace("zhaopin_", "")

        # 构建详情页URL（智联招聘可能需要调用详情API）
        detail_url = f"https://www.zhaopin.com/job/{original_id}.html"

        self.logger.info(f"获取智联招聘岗位详情: {job_id}")

        # 这里可以调用详情API或解析详情页
        # 目前返回基础信息，实际项目应实现详情获取
        return JobItem(
            id=job_id,
            title=f"智联招聘岗位详情",
            company="智联招聘公司",
            location="北京",
            job_type="实习",
            salary_min=8000,
            salary_max=12000,
            education="本科",
            experience="不限",
            description="智联招聘岗位详情待完善",
            requirements=["详情待完善"],
            skills=["详情待完善"],
            source=self.platform,
            url=detail_url
        )

    def parse_list_page(self, html: str) -> List[Dict[str, Any]]:
        """
        解析列表页（HTML解析备用方案）

        Args:
            html: 页面HTML内容

        Returns:
            岗位数据列表
        """
        # 智联招聘主要使用API，这里提供HTML解析的备用方案
        jobs = []

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # 查找岗位列表（根据实际页面结构调整）
            job_elements = soup.find_all('div', class_=re.compile(r'job-list-box|job-item'))

            for element in job_elements[:20]:  # 限制数量
                job = self._parse_job_from_html(element)
                if job:
                    jobs.append(job)

        except Exception as e:
            self.logger.error(f"解析列表页失败: {e}")

        return jobs

    def _parse_job_from_html(self, element) -> Optional[Dict[str, Any]]:
        """从HTML元素解析岗位"""
        try:
            # 简单的HTML解析（需要根据实际页面结构调整）
            title_elem = element.find('a', class_=re.compile(r'job-title'))
            company_elem = element.find('a', class_=re.compile(r'company-name'))
            salary_elem = element.find('span', class_=re.compile(r'salary'))

            if not title_elem:
                return None

            job = {
                "id": element.get('data-jobid') or "",
                "title": title_elem.text.strip() if title_elem else "",
                "company": company_elem.text.strip() if company_elem else "",
                "salary_text": salary_elem.text.strip() if salary_elem else "",
                "url": "https://www.zhaopin.com" + title_elem.get('href', '') if title_elem else ""
            }
            return job
        except Exception as e:
            self.logger.warning(f"解析HTML岗位数据失败: {e}")
            return None

    def parse_detail_page(self, html: str) -> Dict[str, Any]:
        """
        解析详情页

        Args:
            html: 页面HTML内容

        Returns:
            岗位详细数据
        """
        # 智联招聘详情页解析（备用方案）
        job_data = {
            "title": "",
            "company": "",
            "description": "",
            "requirements": []
        }

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # 提取标题
            title_elem = soup.find('h1', class_=re.compile(r'job-title'))
            if title_elem:
                job_data["title"] = title_elem.text.strip()

            # 提取公司
            company_elem = soup.find('a', class_=re.compile(r'company-name'))
            if company_elem:
                job_data["company"] = company_elem.text.strip()

            # 提取描述
            desc_elem = soup.find('div', class_=re.compile(r'job-detail'))
            if desc_elem:
                job_data["description"] = desc_elem.text.strip()

        except Exception as e:
            self.logger.error(f"解析详情页失败: {e}")

        return job_data