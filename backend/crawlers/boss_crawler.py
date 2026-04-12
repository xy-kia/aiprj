"""
BOSS直聘爬虫实现
使用Playwright渲染页面，处理反爬策略

参考文档：Workflow.md 第2.4节、Functional_Spec.md 第2.2节
"""

import re
import json
import asyncio
from typing import Dict, List, Any, Optional, Generator
from urllib.parse import urlencode

from .base import PlaywrightCrawler, JobItem


class BOSSCrawler(PlaywrightCrawler):
    """BOSS直聘爬虫"""

    platform = "BOSS直聘"
    base_url = "https://www.zhipin.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # BOSS直聘特定配置
        self.search_url = f"{self.base_url}/web/geek/job"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 搜索参数
        self.city_code_map = {
            "北京": "101010100",
            "上海": "101020100",
            "广州": "101280100",
            "深圳": "101280600",
            "杭州": "101210100",
            "成都": "101270100",
            "武汉": "101200100",
            "南京": "101190100",
        }

    def search_jobs(
        self,
        keyword: str,
        city: Optional[str] = None,
        page: int = 1,
        **filters
    ) -> Generator[JobItem, None, None]:
        """
        搜索岗位（同步版本）

        Args:
            keyword: 搜索关键词
            city: 城市名称
            page: 页码
            **filters: 额外过滤条件

        Yields:
            JobItem: 岗位数据
        """
        # BOSS直聘需要异步执行，这里调用异步版本
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 创建异步任务
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
        搜索岗位（异步版本）

        Args:
            keyword: 搜索关键词
            city: 城市名称
            page: 页码
            **filters: 额外过滤条件

        Yields:
            JobItem: 岗位数据
        """
        # 初始化浏览器（如果需要）
        if not self.page:
            await self.init_browser()

        # 构建搜索URL
        query_params = self._build_search_params(keyword, city, page, filters)
        search_url = f"{self.search_url}?{query_params}"

        self.logger.info(f"搜索BOSS直聘: {search_url}")

        try:
            # 访问搜索页面
            html = await self.fetch_page(search_url)

            # 解析列表页
            job_list = self.parse_list_page(html)

            # 提取岗位详情（简单版本，只取前几个）
            max_jobs = 10  # 每页最大岗位数
            for i, job_data in enumerate(job_list[:max_jobs]):
                try:
                    # 生成JobItem
                    job = self._create_job_item(job_data)

                    # 可选：获取详细页面信息
                    # if job.id:
                    #     detail_job = await self.parse_job_detail(job.id)
                    #     if detail_job:
                    #         job = detail_job

                    yield job

                except Exception as e:
                    self.logger.error(f"处理岗位数据失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"搜索失败: {e}")
            raise

    def _build_search_params(
        self,
        keyword: str,
        city: Optional[str],
        page: int,
        filters: Dict[str, Any]
    ) -> str:
        """构建搜索参数"""
        params = {
            "query": keyword,
            "page": page,
            "city": self.city_code_map.get(city or "北京", "101010100")
        }

        # 添加过滤条件
        if "salary" in filters:
            params["salary"] = filters["salary"]

        if "experience" in filters:
            params["experience"] = filters["experience"]

        if "education" in filters:
            params["degree"] = filters["education"]

        return urlencode(params)

    def parse_list_page(self, html: str) -> List[Dict[str, Any]]:
        """
        解析列表页

        Args:
            html: 页面HTML内容

        Returns:
            岗位数据列表
        """
        jobs = []

        try:
            # 尝试多种JSON模式匹配
            json_patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;',
                r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>',
                r'<script id="__NEXT_DATA__"[^>]*>({.*?})</script>',
                r'<script[^>]*>window\.__NUXT__\s*=\s*({.*?});</script>',
                r'<script[^>]*>window\.__REDUX_STATE__\s*=\s*({.*?});</script>',
            ]

            data = None
            json_str = None

            for pattern in json_patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    try:
                        data = json.loads(json_str)
                        self.logger.debug(f"使用JSON模式成功解析数据: {pattern[:30]}...")
                        break
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"JSON解析失败，尝试下一个模式: {e}")
                        continue

            if data:
                # 尝试多个可能的路径来获取岗位列表
                job_list = None
                possible_paths = [
                    data.get("jobList", {}).get("list", []),
                    data.get("jobs", []),
                    data.get("list", []),
                    data.get("data", {}).get("list", []),
                    data.get("result", {}).get("list", []),
                ]

                for path in possible_paths:
                    if isinstance(path, list) and len(path) > 0:
                        job_list = path
                        self.logger.debug(f"找到岗位列表路径，数量: {len(job_list)}")
                        break

                if job_list:
                    for job_data in job_list:
                        parsed = self._parse_job_from_json(job_data)
                        if parsed:
                            jobs.append(parsed)
                else:
                    self.logger.warning("未找到岗位列表路径，尝试直接搜索jobs字段")
                    # 递归搜索jobs字段
                    def find_jobs(obj, depth=0):
                        if depth > 5:  # 防止无限递归
                            return []
                        if isinstance(obj, list):
                            # 检查列表中的元素是否包含岗位数据
                            if len(obj) > 0 and isinstance(obj[0], dict):
                                # 检查是否有常见字段
                                sample = obj[0]
                                if any(key in sample for key in ['jobName', 'title', 'company', 'brandName']):
                                    return obj
                            return []
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if 'job' in key.lower() or 'list' in key.lower():
                                    result = find_jobs(value, depth+1)
                                    if result:
                                        return result
                            # 递归搜索所有值
                            for value in obj.values():
                                result = find_jobs(value, depth+1)
                                if result:
                                    return result
                        return []

                    found_jobs = find_jobs(data)
                    if found_jobs:
                        self.logger.info(f"通过递归搜索找到岗位数据: {len(found_jobs)} 条")
                        for job_data in found_jobs:
                            parsed = self._parse_job_from_json(job_data)
                            if parsed:
                                jobs.append(parsed)

            # 如果JSON解析失败或未找到岗位数据，尝试HTML解析
            if not jobs:
                self.logger.info("JSON解析未找到数据，尝试HTML解析")
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')

                # 查找岗位卡片（根据实际DOM结构调整）
                job_cards = soup.find_all('div', class_=re.compile(r'job-card|job-item|job-list-item'))

                if not job_cards:
                    # 尝试其他常见类名
                    job_cards = soup.find_all('li', class_=re.compile(r'job-item|job-card'))

                for card in job_cards[:30]:  # 限制数量
                    job = self._parse_job_from_html(card)
                    if job:
                        jobs.append(job)

            self.logger.info(f"解析列表页完成，共找到 {len(jobs)} 个岗位")

        except Exception as e:
            self.logger.error(f"解析列表页失败: {e}", exc_info=True)

        return jobs

    def _parse_job_from_json(self, job_data: Dict) -> Optional[Dict[str, Any]]:
        """从JSON数据解析岗位"""
        try:
            # 支持多种字段名映射
            field_mappings = {
                "id": ["encryptId", "id", "jobId", "positionId"],
                "title": ["jobName", "title", "positionName", "name"],
                "company": ["brandName", "company", "companyName", "employer"],
                "location": ["cityName", "location", "city", "workLocation"],
                "salary_text": ["salaryDesc", "salary", "salaryText", "salaryInfo"],
                "experience": ["jobExperience", "experience", "workExperience", "exp"],
                "education": ["jobDegree", "education", "degree", "academic"],
                "skills": ["skills", "tags", "skillTags", "requirements"],
                "description": ["jobDescription", "description", "jobDetail", "content"],
            }

            def get_field(data, keys):
                for key in keys:
                    if key in data:
                        value = data[key]
                        # 确保列表和字符串类型正确
                        if isinstance(value, list):
                            return value
                        if isinstance(value, str):
                            return value.strip()
                        return value
                return None

            # 提取字段
            job_id = get_field(job_data, field_mappings["id"]) or ""
            title = get_field(job_data, field_mappings["title"]) or ""
            company = get_field(job_data, field_mappings["company"]) or ""
            location = get_field(job_data, field_mappings["location"]) or ""
            salary_text = get_field(job_data, field_mappings["salary_text"]) or ""
            experience = get_field(job_data, field_mappings["experience"]) or ""
            education = get_field(job_data, field_mappings["education"]) or ""
            skills = get_field(job_data, field_mappings["skills"]) or []
            description = get_field(job_data, field_mappings["description"]) or ""

            # 确保skills是列表
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            elif not isinstance(skills, list):
                skills = []

            # 构建URL
            url = ""
            if job_id:
                url = f"{self.base_url}/job_detail/{job_id}.html"
            elif "url" in job_data:
                url = job_data["url"]

            job = {
                "id": str(job_id) if job_id else "",
                "title": title,
                "company": company,
                "location": location,
                "salary_text": salary_text,
                "experience": experience,
                "education": education,
                "skills": skills,
                "description": description,
                "url": url
            }

            # 记录解析成功的日志
            self.logger.debug(f"解析岗位: {title} - {company}")

            return job
        except Exception as e:
            self.logger.warning(f"解析JSON岗位数据失败: {e}", exc_info=True)
            return None

    def _parse_job_from_html(self, element) -> Optional[Dict[str, Any]]:
        """从HTML元素解析岗位"""
        try:
            # 简单的HTML解析（需要根据实际页面结构调整）
            title_elem = element.find('span', class_=re.compile(r'job-name'))
            company_elem = element.find('div', class_=re.compile(r'company-name'))
            salary_elem = element.find('span', class_=re.compile(r'salary'))

            if not title_elem:
                return None

            job = {
                "id": element.get('data-jobid') or "",
                "title": title_elem.text.strip() if title_elem else "",
                "company": company_elem.text.strip() if company_elem else "",
                "salary_text": salary_elem.text.strip() if salary_elem else "",
                "url": self.base_url + element.find('a').get('href', '') if element.find('a') else ""
            }
            return job
        except Exception as e:
            self.logger.warning(f"解析HTML岗位数据失败: {e}")
            return None

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

    async def parse_job_detail(self, job_id: str) -> Optional[JobItem]:
        """
        获取岗位详情

        Args:
            job_id: 岗位ID

        Returns:
            JobItem或None
        """
        detail_url = f"{self.base_url}/job_detail/{job_id}.html"

        try:
            html = await self.fetch_page(detail_url)
            detail_data = self.parse_detail_page(html)

            if detail_data:
                job = self._create_job_item(detail_data)
                return job

        except Exception as e:
            self.logger.error(f"获取岗位详情失败 {job_id}: {e}")

        return None

    def parse_detail_page(self, html: str) -> Dict[str, Any]:
        """
        解析详情页

        Args:
            html: 页面HTML内容

        Returns:
            岗位详细数据
        """
        try:
            # 尝试解析JSON数据
            json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;'
            match = re.search(json_pattern, html, re.DOTALL)

            if match:
                json_str = match.group(1)
                data = json.loads(json_str)

                # 提取岗位详情（根据实际数据结构调整）
                job_detail = data.get("jobDetail", {}).get("jobInfo", {})

                return {
                    "id": job_detail.get("encryptId", ""),
                    "title": job_detail.get("jobName", ""),
                    "company": job_detail.get("brandName", ""),
                    "location": job_detail.get("cityName", ""),
                    "salary_text": job_detail.get("salaryDesc", ""),
                    "experience": job_detail.get("jobExperience", ""),
                    "education": job_detail.get("jobDegree", ""),
                    "description": job_detail.get("jobDescription", ""),
                    "requirements": job_detail.get("jobRequirement", "").split("\n") if job_detail.get("jobRequirement") else [],
                    "skills": job_detail.get("skills", []),
                    "url": f"{self.base_url}/job_detail/{job_detail.get('encryptId', '')}.html"
                }

        except Exception as e:
            self.logger.error(f"解析详情页失败: {e}")

        # 备用方案：HTML解析
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        job_data = {
            "title": "",
            "company": "",
            "description": "",
            "requirements": []
        }

        # 提取标题
        title_elem = soup.find('div', class_=re.compile(r'job-title'))
        if title_elem:
            job_data["title"] = title_elem.text.strip()

        # 提取公司
        company_elem = soup.find('div', class_=re.compile(r'company-name'))
        if company_elem:
            job_data["company"] = company_elem.text.strip()

        # 提取描述
        desc_elem = soup.find('div', class_=re.compile(r'job-detail'))
        if desc_elem:
            job_data["description"] = desc_elem.text.strip()

        return job_data