"""
前程无忧爬虫实现
HTML解析或API调用

参考文档：Workflow.md 第2.4节、Functional_Spec.md 第2.2节
"""

import asyncio
import re
import json
from typing import Dict, List, Any, Optional, Generator
from urllib.parse import urlencode

from .base import PlaywrightCrawler, JobItem


class QianchengCrawler(PlaywrightCrawler):
    """前程无忧爬虫"""

    platform = "前程无忧"
    base_url = "https://search.51job.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = f"{self.base_url}/list"

        # 前程无忧配置
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 城市代码映射（前程无忧使用数字代码）
        self.city_code_map = {
            "北京": "010000",
            "上海": "020000",
            "广州": "030200",
            "深圳": "040000",
            "杭州": "080200",
            "成都": "090200",
            "武汉": "180200",
            "南京": "070200",
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
        # 前程无忧需要异步执行，这里调用异步版本
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

        self.logger.info(f"搜索前程无忧: {search_url}")

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
            # 返回空，不抛出异常，避免影响其他爬虫

    def _build_search_params(
        self,
        keyword: str,
        city: Optional[str],
        page: int,
        filters: Dict[str, Any]
    ) -> str:
        """构建搜索参数"""
        params = {
            "keyword": keyword,
            "searchType": 2,  # 搜索类型
            "postchannel": 0000,  # 岗位渠道
            "jobarea": self.city_code_map.get(city or "北京", "010000"),  # 默认北京
            "curr_page": page,  # 页码
        }

        # 添加过滤条件
        if "salary" in filters:
            salary_map = {
                "0-3k": "01", "3-5k": "02", "5-8k": "03",
                "8-10k": "04", "10-15k": "05", "15-20k": "06",
                "20-30k": "07", "30-50k": "08", "50k以上": "09"
            }
            if filters["salary"] in salary_map:
                params["salary"] = salary_map[filters["salary"]]

        if "experience" in filters:
            exp_map = {
                "不限": "99", "应届生": "01", "1年以内": "02",
                "1-3年": "03", "3-5年": "04", "5-10年": "05", "10年以上": "06"
            }
            if filters["experience"] in exp_map:
                params["workyear"] = exp_map[filters["experience"]]

        if "education" in filters:
            edu_map = {
                "不限": "99", "高中": "01", "大专": "02", "本科": "03",
                "硕士": "04", "博士": "05"
            }
            if filters["education"] in edu_map:
                params["degree"] = edu_map[filters["education"]]

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
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # 查找岗位列表（根据前程无忧实际DOM结构调整）
            # 常见的选择器：div.el, div.job_item, div.j_lists等
            job_elements = soup.find_all('div', class_=re.compile(r'el|job_item|j_lists'))

            # 如果没有找到，尝试其他选择器
            if not job_elements:
                job_elements = soup.find_all('div', class_=re.compile(r'joblist'))

            for element in job_elements[:30]:  # 限制数量
                job = self._parse_job_from_html(element)
                if job:
                    jobs.append(job)

        except Exception as e:
            self.logger.error(f"解析列表页失败: {e}")

        return jobs

    def _parse_job_from_html(self, element) -> Optional[Dict[str, Any]]:
        """从HTML元素解析岗位"""
        try:
            # 提取岗位信息（根据前程无忧页面结构调整）
            # 标题
            title_elem = element.find('span', class_=re.compile(r'jname|title'))
            if not title_elem:
                title_elem = element.find('a', class_=re.compile(r'el'))

            # 公司
            company_elem = element.find('a', class_=re.compile(r'cname|company'))
            if not company_elem:
                company_elem = element.find('span', class_=re.compile(r'cname'))

            # 薪资
            salary_elem = element.find('span', class_=re.compile(r'salary|money'))
            if not salary_elem:
                salary_elem = element.find('strong')

            # 地点
            location_elem = element.find('span', class_=re.compile(r'dq|location'))
            if not location_elem:
                location_elem = element.find('span', class_=re.compile(r'area'))

            # 经验要求
            exp_elem = element.find('span', class_=re.compile(r'exp|workyear'))
            if not exp_elem:
                exp_elem = element.find('span', class_=re.compile(r'experience'))

            # 学历要求
            edu_elem = element.find('span', class_=re.compile(r'edu|degree'))
            if not edu_elem:
                edu_elem = element.find('span', class_=re.compile(r'education'))

            # 链接
            link_elem = element.find('a', href=True)
            url = ""
            if link_elem:
                url = link_elem.get('href', '')
                if not url.startswith('http'):
                    url = f"https:{url}" if url.startswith('//') else f"https://www.51job.com{url}"

            # 岗位ID（从URL中提取）
            job_id = ""
            if url:
                # 从URL中提取数字ID
                match = re.search(r'/job/(\d+)', url)
                if match:
                    job_id = f"51job_{match.group(1)}"
                else:
                    # 备用方案：使用URL哈希
                    import hashlib
                    job_id = f"51job_{hashlib.md5(url.encode()).hexdigest()[:16]}"

            job_data = {
                "id": job_id,
                "title": title_elem.text.strip() if title_elem else "",
                "company": company_elem.text.strip() if company_elem else "",
                "salary_text": salary_elem.text.strip() if salary_elem else "",
                "location": location_elem.text.strip() if location_elem else "",
                "experience": exp_elem.text.strip() if exp_elem else "不限",
                "education": edu_elem.text.strip() if edu_elem else "不限",
                "url": url
            }

            return job_data

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

    async def parse_job_detail(self, job_id: str) -> Optional[JobItem]:
        """
        获取岗位详情

        Args:
            job_id: 岗位ID（格式: 51job_数字）

        Returns:
            JobItem或None
        """
        # 提取原始ID
        if job_id.startswith("51job_"):
            original_id = job_id.replace("51job_", "")
        else:
            original_id = job_id

        # 构建详情页URL
        detail_url = f"https://jobs.51job.com/all/co{original_id}.html"

        self.logger.info(f"获取前程无忧岗位详情: {job_id}")

        try:
            # 访问详情页
            html = await self.fetch_page(detail_url)
            detail_data = self.parse_detail_page(html)

            if detail_data:
                # 合并基础信息
                detail_data["id"] = job_id
                detail_data["url"] = detail_url
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
        job_data = {
            "title": "",
            "company": "",
            "description": "",
            "requirements": [],
            "skills": []
        }

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')

            # 提取标题
            title_elem = soup.find('h1', class_=re.compile(r'job-title|position-title'))
            if title_elem:
                job_data["title"] = title_elem.text.strip()

            # 提取公司
            company_elem = soup.find('a', class_=re.compile(r'company-name|com-name'))
            if not company_elem:
                company_elem = soup.find('div', class_=re.compile(r'company'))
            if company_elem:
                job_data["company"] = company_elem.text.strip()

            # 提取职位描述
            desc_elem = soup.find('div', class_=re.compile(r'job-description|bmsg'))
            if desc_elem:
                job_data["description"] = desc_elem.text.strip()

                # 从描述中提取技能关键词
                skills = self._extract_skills_from_text(job_data["description"])
                job_data["skills"] = skills

                # 提取要求（简单的分割）
                requirements = self._extract_requirements_from_text(job_data["description"])
                job_data["requirements"] = requirements

            # 提取薪资（详情页通常有更准确的信息）
            salary_elem = soup.find('span', class_=re.compile(r'salary|money'))
            if salary_elem:
                job_data["salary_text"] = salary_elem.text.strip()

            # 提取地点
            location_elem = soup.find('span', class_=re.compile(r'location|work-address'))
            if location_elem:
                job_data["location"] = location_elem.text.strip()

        except Exception as e:
            self.logger.error(f"解析详情页失败: {e}")

        return job_data

    def _extract_skills_from_text(self, text: str) -> List[str]:
        """从文本中提取技能关键词"""
        skills = []

        if not text:
            return skills

        # 常见技能关键词
        tech_keywords = [
            "Python", "Java", "JavaScript", "TypeScript", "Go", "C++", "C",
            "Vue.js", "React", "Angular", "Node.js", "Spring", "Django", "Flask",
            "MySQL", "Redis", "MongoDB", "Docker", "Kubernetes", "Git", "Linux",
            "AWS", "机器学习", "深度学习", "数据分析", "SQL", "算法", "数据结构",
            "前端开发", "后端开发", "移动开发", "测试", "运维", "项目管理"
        ]

        text_lower = text.lower()

        for keyword in tech_keywords:
            if keyword.lower() in text_lower or keyword in text:
                skills.append(keyword)

        # 去重
        return list(set(skills))

    def _extract_requirements_from_text(self, text: str) -> List[str]:
        """从文本中提取要求"""
        requirements = []

        if not text:
            return requirements

        # 简单的分割逻辑（根据常见分隔符）
        lines = re.split(r'[。；;\.\n]', text)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是要求相关的句子
            requirement_indicators = [
                "要求", "需要", "必备", "熟悉", "掌握", "了解", "优先",
                "具备", "能够", "善于", "熟练", "精通"
            ]

            if any(indicator in line for indicator in requirement_indicators):
                requirements.append(line)

        # 限制数量
        return requirements[:10]