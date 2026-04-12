"""
猎聘爬虫实现
反爬策略较强，成功率目标70%

参考文档：Workflow.md 第2.4节、Functional_Spec.md 第2.2节
"""

import asyncio
import re
import json
import random
import time
from typing import Dict, List, Any, Optional, Generator
from urllib.parse import urlencode

from .base import PlaywrightCrawler, JobItem
from .ai_parser import AIParser


class LiepinCrawler(PlaywrightCrawler):
    """猎聘爬虫"""

    base_url = "https://www.liepin.com"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.platform = "猎聘"
        self.search_url = f"{self.base_url}/zhaopin"

        # 猎聘反爬策略较强，增加延迟
        self.min_delay = 3.0
        self.max_delay = 8.0

        # 猎聘配置
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.liepin.com/",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 城市映射（猎聘使用拼音或数字代码）
        self.city_map = {
            "北京": "010",
            "上海": "020",
            "广州": "050020",
            "深圳": "050090",
            "杭州": "070020",
            "成都": "280020",
            "武汉": "170020",
            "南京": "060020",
        }

        # AI解析器（作为备用解析方案）
        self.ai_parser_enabled = kwargs.get("ai_parser_enabled", True)
        self.user_config = kwargs.get("user_config")  # 用户AI配置
        self.ai_parser = None
        if self.ai_parser_enabled:
            try:
                # 如果有用户配置，传递给AI解析器
                if self.user_config:
                    enabled = getattr(self.user_config, 'enabled', False)
                    self.logger.info(f"用户配置存在，启用状态: {enabled}")
                    self.ai_parser = AIParser(user_config=self.user_config)
                    self.logger.info("AI解析器初始化成功（使用用户配置）")
                else:
                    self.logger.info("未提供用户配置，使用系统默认配置")
                    self.ai_parser = AIParser()
                    self.logger.info("AI解析器初始化成功（使用系统配置）")
            except Exception as e:
                self.logger.warning(f"AI解析器初始化失败，将仅使用传统解析: {e}")

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
        # 猎聘需要异步执行，这里调用异步版本
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

        self.logger.info(f"搜索猎聘: {search_url}")

        try:
            # 访问搜索页面
            html = await self.fetch_page(search_url)

            # 解析列表页
            job_list = self.parse_list_page(html)

            # 提取岗位详情（简单版本，只取前几个）
            max_jobs = 8  # 猎聘每页限制较少，目标成功率70%
            for i, job_data in enumerate(job_list[:max_jobs]):
                try:
                    # 生成JobItem
                    job = self._create_job_item(job_data)

                    # 猎聘详情页获取较困难，成功率目标70%
                    # 有50%的概率尝试获取详情
                    if random.random() < 0.5 and job.id:
                        try:
                            detail_job = await self.parse_job_detail(job.id)
                            if detail_job:
                                job = detail_job
                        except Exception as detail_error:
                            self.logger.warning(f"获取猎聘详情失败 {job.id}: {detail_error}")
                            # 继续使用基础信息

                    yield job

                except Exception as e:
                    self.logger.error(f"处理岗位数据失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"猎聘搜索失败: {e}")
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
            "key": keyword,
            "currentPage": page - 1,  # 猎聘从0开始
            "dq": self.city_map.get(city or "北京", "010"),  # 默认北京
        }

        # 添加过滤条件
        if "salary" in filters:
            salary_map = {
                "0-3k": "110$111", "3-5k": "111$112", "5-8k": "112$113",
                "8-10k": "113$114", "10-15k": "114$115", "15-20k": "115$116",
                "20-30k": "116$117", "30-50k": "117$118", "50k以上": "118"
            }
            if filters["salary"] in salary_map:
                params["salary"] = salary_map[filters["salary"]]

        if "experience" in filters:
            exp_map = {
                "不限": "", "应届生": "101", "1年以内": "102",
                "1-3年": "103", "3-5年": "104", "5-10年": "105", "10年以上": "106"
            }
            if filters["experience"] in exp_map:
                params["workYearCode"] = exp_map[filters["experience"]]

        if "education" in filters:
            edu_map = {
                "不限": "", "高中": "201", "大专": "202", "本科": "203",
                "硕士": "204", "博士": "205"
            }
            if filters["education"] in edu_map:
                params["degree"] = edu_map[filters["education"]]

        # 猎聘特定参数
        params["industries"] = ""  # 行业不限
        params["jobKind"] = 2  # 工作类型（2: 全职）
        params["compScale"] = ""  # 公司规模不限
        params["compKind"] = ""  # 公司性质不限
        params["clean_condition"] = ""  # 清理条件

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
            # 猎聘页面通常包含JSON数据
            json_pattern = r'window\.searchResult\s*=\s*({.*?})\s*;'
            match = re.search(json_pattern, html, re.DOTALL)

            if match:
                json_str = match.group(1)
                data = json.loads(json_str)

                # 提取岗位列表
                job_list = data.get("data", {}).get("jobCardList", [])

                for item in job_list:
                    job = self._parse_job_from_json(item)
                    if job:
                        jobs.append(job)

            else:
                # 备用方案：HTML解析
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')

                # 查找岗位卡片
                job_cards = soup.find_all('div', class_=re.compile(r'job-card|job-list'))

                for card in job_cards[:15]:  # 限制数量
                    job = self._parse_job_from_html(card)
                    if job:
                        jobs.append(job)

        except Exception as e:
            self.logger.error(f"解析列表页失败: {e}")

        # 如果传统解析方法都没有找到数据，尝试AI解析
        if not jobs and self.ai_parser and self.ai_parser_enabled:
            try:
                self.logger.info("传统解析方法失败，尝试使用AI解析")
                ai_jobs = self.ai_parser.parse_list_page(html, self.platform)

                if ai_jobs:
                    self.logger.info(f"AI解析成功，找到 {len(ai_jobs)} 个岗位")

                    # 将AI解析的数据转换为标准格式
                    for ai_job_data in ai_jobs:
                        try:
                            # 确保数据有必要的字段
                            if not isinstance(ai_job_data, dict):
                                continue

                            # 如果AI解析缺少必要字段，尝试补充
                            if "id" not in ai_job_data:
                                ai_job_data["id"] = ""
                            if "url" not in ai_job_data:
                                ai_job_data["url"] = ""
                            if "skills" not in ai_job_data:
                                ai_job_data["skills"] = []

                            jobs.append(ai_job_data)
                        except Exception as e:
                            self.logger.warning(f"处理AI解析数据失败: {e}")
                            continue
                else:
                    self.logger.info("AI解析也未找到岗位数据")
            except Exception as e:
                self.logger.error(f"AI解析失败: {e}")

        return jobs

    def _parse_job_from_json(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从JSON数据解析岗位"""
        # 检查item类型
        if not isinstance(item, dict):
            self.logger.warning(f"JSON岗位数据不是字典类型: {type(item)}，值: {item}")
            return None
        try:
            job_id = item.get("jobId") or item.get("encryptId", "")
            title = item.get("jobName") or item.get("title", "")
            company = item.get("brandName") or item.get("company", "")
            salary = item.get("salary") or item.get("salaryDesc", "")
            city = item.get("city") or item.get("cityName", "")
            experience = item.get("experience") or item.get("workYear", "")
            education = item.get("education") or item.get("degree", "")

            # 构建URL
            url = ""
            if job_id:
                url = f"{self.base_url}/job/{job_id}.html"

            job_data = {
                "id": f"liepin_{job_id}" if job_id else f"liepin_{str(abs(hash(str(item))))[:16]}",
                "title": title,
                "company": company,
                "location": city,
                "salary_text": salary,
                "experience": experience,
                "education": education,
                "url": url
            }

            return job_data

        except Exception as e:
            self.logger.warning(f"解析JSON岗位数据失败: {e}")
            return None

    def _parse_job_from_html(self, element) -> Optional[Dict[str, Any]]:
        """从HTML元素解析岗位"""
        try:
            self.logger.debug(f"解析HTML元素，类型: {type(element)}，内容摘要: {str(element)[:200]}")
            # 检查element是否为可用的Tag对象
            if not hasattr(element, 'find'):
                self.logger.warning(f"HTML元素不支持find方法，类型: {type(element)}")
                return None
            # 提取岗位信息
            title_elem = element.find('a', class_=re.compile(r'job-title|title'))
            company_elem = element.find('a', class_=re.compile(r'company-name|company'))
            salary_elem = element.find('span', class_=re.compile(r'salary|money'))
            location_elem = element.find('span', class_=re.compile(r'area|location'))
            exp_elem = element.find('span', class_=re.compile(r'exp|work-year'))
            edu_elem = element.find('span', class_=re.compile(r'edu|degree'))

            # 链接
            link_elem = element.find('a', href=True)
            url = ""
            if link_elem:
                url = link_elem.get('href', '')
                if not url.startswith('http'):
                    url = f"{self.base_url}{url}" if url.startswith('/') else f"https:{url}"

            # 岗位ID（从URL中提取）
            job_id = ""
            if url:
                match = re.search(r'/job/(\d+)', url)
                if match:
                    job_id = match.group(1)

            job_data = {
                "id": f"liepin_{job_id}" if job_id else f"liepin_{str(abs(hash(str(element))))[:16]}",
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
            import traceback
            self.logger.warning(f"解析HTML岗位数据失败: {e}")
            self.logger.warning(f"异常堆栈: {traceback.format_exc()}")
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
            job_id: 岗位ID（格式: liepin_数字）

        Returns:
            JobItem或None
        """
        # 提取原始ID
        if job_id.startswith("liepin_"):
            original_id = job_id.replace("liepin_", "")
        else:
            original_id = job_id

        # 构建详情页URL
        detail_url = f"{self.base_url}/job/{original_id}.html"

        self.logger.info(f"获取猎聘岗位详情: {job_id}")

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
            self.logger.error(f"获取猎聘岗位详情失败 {job_id}: {e}")

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
            # 尝试解析JSON数据
            json_pattern = r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;'
            match = re.search(json_pattern, html, re.DOTALL)

            if match:
                json_str = match.group(1)
                data = json.loads(json_str)

                # 提取岗位详情
                job_detail = data.get("jobDetail", {}).get("jobInfo", {})

                job_data["title"] = job_detail.get("jobName", "")
                job_data["company"] = job_detail.get("brandName", "")
                job_data["description"] = job_detail.get("jobDescription", "")

                # 提取技能
                skills = job_detail.get("skills", [])
                if isinstance(skills, list):
                    job_data["skills"] = skills

                # 提取要求
                requirements = job_detail.get("jobRequirement", "")
                if requirements:
                    req_list = re.split(r'[。；;\.\n]', requirements)
                    job_data["requirements"] = [req.strip() for req in req_list if req.strip()]

            else:
                # 备用方案：HTML解析
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'html.parser')

                # 提取标题
                title_elem = soup.find('h1', class_=re.compile(r'job-title|title'))
                if title_elem:
                    job_data["title"] = title_elem.text.strip()

                # 提取公司
                company_elem = soup.find('a', class_=re.compile(r'company-name'))
                if not company_elem:
                    company_elem = soup.find('div', class_=re.compile(r'company-info'))
                if company_elem:
                    job_data["company"] = company_elem.text.strip()

                # 提取职位描述
                desc_elem = soup.find('div', class_=re.compile(r'job-description|content'))
                if desc_elem:
                    job_data["description"] = desc_elem.text.strip()

                    # 从描述中提取技能
                    skills = self._extract_skills_from_text(job_data["description"])
                    job_data["skills"] = skills

                    # 提取要求
                    requirements = self._extract_requirements_from_text(job_data["description"])
                    job_data["requirements"] = requirements

        except Exception as e:
            self.logger.error(f"解析详情页失败: {e}")

        # 如果传统解析方法都没有找到有效数据，尝试AI解析
        if not job_data.get("title") and not job_data.get("company") and self.ai_parser and self.ai_parser_enabled:
            try:
                self.logger.info("详情页传统解析方法失败，尝试使用AI解析")
                ai_job_data = self.ai_parser.parse_detail_page(html, self.platform)

                if ai_job_data:
                    self.logger.info("AI解析详情页成功")
                    # 合并AI解析的数据（优先使用AI数据）
                    for key, value in ai_job_data.items():
                        if value:  # 只覆盖非空值
                            job_data[key] = value
            except Exception as e:
                self.logger.error(f"详情页AI解析失败: {e}")

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
            "前端开发", "后端开发", "移动开发", "测试", "运维", "项目管理", "架构设计"
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

        # 简单的分割逻辑
        lines = re.split(r'[。；;\.\n]', text)

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否是要求相关的句子
            requirement_indicators = [
                "要求", "需要", "必备", "熟悉", "掌握", "了解", "优先",
                "具备", "能够", "善于", "熟练", "精通", "负责", "参与"
            ]

            if any(indicator in line for indicator in requirement_indicators):
                requirements.append(line)

        # 限制数量
        return requirements[:10]

    def before_request(self):
        """请求前的准备工作（猎聘增加额外延时）"""
        super().before_request()

        # 猎聘反爬较强，增加随机额外延时
        extra_delay = random.uniform(1.0, 3.0)
        time.sleep(extra_delay)