"""
搜索调度器 - 调度多个爬虫并行执行，整合搜索结果
支持并行执行、失败重试、结果去重。

参考文档：Workflow.md 第2.4节、Functional_Spec.md 第2.2节
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import hashlib

from backend.crawlers.base import BaseCrawler, JobItem


class SearchScheduler:
    """搜索调度器"""

    def __init__(
        self,
        crawlers: List[BaseCrawler],
        max_workers: int = 4,
        timeout: int = 30,
        max_retries: int = 2
    ):
        """
        初始化搜索调度器

        Args:
            crawlers: 爬虫实例列表
            max_workers: 最大并发工作线程数
            timeout: 单个爬虫超时时间（秒）
            max_retries: 最大重试次数
        """
        self.crawlers = crawlers
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger(__name__)

        # 去重缓存
        self.seen_jobs: Set[str] = set()

    async def search(
        self,
        keyword: str,
        city: Optional[str] = None,
        page_limit: int = 3,
        min_success_rate: float = 0.7
    ) -> List[JobItem]:
        """
        执行搜索

        Args:
            keyword: 搜索关键词
            city: 城市名称
            page_limit: 每个爬虫最大页数
            min_success_rate: 最小成功爬虫比例

        Returns:
            岗位数据列表（已去重）
        """
        self.logger.info(f"开始搜索: keyword={keyword}, city={city}")

        # 清空去重缓存
        self.seen_jobs.clear()

        # 创建任务列表
        tasks = []
        for crawler in self.crawlers:
            task = self._run_crawler_with_retry(
                crawler, keyword, city, page_limit
            )
            tasks.append(task)

        # 并行执行所有爬虫任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 整合结果
        all_jobs = []
        successful_crawlers = 0

        for i, result in enumerate(results):
            crawler = self.crawlers[i]

            if isinstance(result, Exception):
                self.logger.error(f"爬虫 {crawler.platform} 执行失败: {result}")
                continue

            successful_crawlers += 1
            jobs = result

            # 去重并添加来源平台
            for job in jobs:
                job.source = crawler.platform
                job_id = self._generate_job_id(job)

                if job_id not in self.seen_jobs:
                    self.seen_jobs.add(job_id)
                    all_jobs.append(job)

            self.logger.info(f"爬虫 {crawler.platform} 获取到 {len(jobs)} 个岗位，去重后新增 {len(jobs)} 个")

        # 检查成功率
        success_rate = successful_crawlers / len(self.crawlers) if self.crawlers else 0
        self.logger.info(f"搜索完成: 成功爬虫 {successful_crawlers}/{len(self.crawlers)}, "
                        f"成功率 {success_rate:.2%}, 总岗位数 {len(all_jobs)}")

        if success_rate < min_success_rate:
            self.logger.warning(f"爬虫成功率低于阈值: {success_rate:.2%} < {min_success_rate:.2%}")

        return all_jobs

    async def _run_crawler_with_retry(
        self,
        crawler: BaseCrawler,
        keyword: str,
        city: Optional[str],
        page_limit: int
    ) -> List[JobItem]:
        """
        执行单个爬虫（带重试）

        Args:
            crawler: 爬虫实例
            keyword: 搜索关键词
            city: 城市名称
            page_limit: 最大页数

        Returns:
            岗位数据列表
        """
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(f"执行爬虫 {crawler.platform}, 尝试 {attempt + 1}/{self.max_retries + 1}")

                # 创建超时任务
                search_task = asyncio.create_task(
                    self._execute_crawler_search(crawler, keyword, city, page_limit)
                )

                # 等待任务完成，带超时
                jobs = await asyncio.wait_for(search_task, timeout=self.timeout)

                self.logger.info(f"爬虫 {crawler.platform} 成功获取 {len(jobs)} 个岗位")
                return jobs

            except asyncio.TimeoutError:
                self.logger.warning(f"爬虫 {crawler.platform} 超时 (尝试 {attempt + 1})")
                if attempt == self.max_retries:
                    raise

            except Exception as e:
                self.logger.error(f"爬虫 {crawler.platform} 出错: {e} (尝试 {attempt + 1})")
                if attempt == self.max_retries:
                    raise

                # 重试前等待
                await asyncio.sleep(2 ** attempt)  # 指数退避

        return []  # 理论上不会执行到这里

    async def _execute_crawler_search(
        self,
        crawler: BaseCrawler,
        keyword: str,
        city: Optional[str],
        page_limit: int
    ) -> List[JobItem]:
        """
        执行爬虫搜索

        Args:
            crawler: 爬虫实例
            keyword: 搜索关键词
            city: 城市名称
            page_limit: 最大页数

        Returns:
            岗位数据列表
        """
        jobs = []

        # 分页搜索
        for page in range(1, page_limit + 1):
            try:
                page_jobs = []

                # 调用爬虫的搜索方法
                # 注意：这里假设爬虫的search_jobs是生成器
                if hasattr(crawler, 'async_search_jobs'):
                    # 异步方法优先
                    async for job in crawler.async_search_jobs(keyword, city, page):
                        if job:
                            page_jobs.append(job)

                elif hasattr(crawler, 'search_jobs'):
                    # 同步方法：在线程池中执行
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(
                            self._sync_search_jobs,
                            crawler, keyword, city, page
                        )
                        page_results = future.result(timeout=self.timeout // 2)

                        for job in page_results:
                            if job:
                                page_jobs.append(job)

                # 如果没有获取到岗位，可能已经到达最后一页
                if not page_jobs:
                    self.logger.debug(f"爬虫 {crawler.platform} 第 {page} 页无结果，停止翻页")
                    break

                jobs.extend(page_jobs)
                self.logger.debug(f"爬虫 {crawler.platform} 第 {page} 页获取到 {len(page_jobs)} 个岗位")

                # 避免请求过快
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.warning(f"爬虫 {crawler.platform} 第 {page} 页失败: {e}")
                break

        return jobs

    def _sync_search_jobs(
        self,
        crawler: BaseCrawler,
        keyword: str,
        city: Optional[str],
        page: int
    ) -> List[JobItem]:
        """同步执行爬虫搜索（用于线程池）"""
        jobs = []
        try:
            # 调用同步的search_jobs方法
            for job in crawler.search_jobs(keyword, city, page):
                if job:
                    jobs.append(job)
        except Exception as e:
            self.logger.error(f"同步搜索失败: {e}")
        return jobs

    def _generate_job_id(self, job: JobItem) -> str:
        """生成岗位唯一ID（用于去重）"""
        # 基于标题、公司、地点生成哈希ID
        content = f"{job.title}_{job.company}_{job.location}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def deduplicate_jobs(self, jobs: List[JobItem]) -> List[JobItem]:
        """
        去重岗位数据

        Args:
            jobs: 岗位数据列表

        Returns:
            去重后的岗位列表
        """
        seen = set()
        deduplicated = []

        for job in jobs:
            job_id = self._generate_job_id(job)

            if job_id not in seen:
                seen.add(job_id)
                deduplicated.append(job)
            else:
                self.logger.debug(f"去重重复岗位: {job.title} - {job.company}")

        self.logger.info(f"去重结果: {len(jobs)} -> {len(deduplicated)}")
        return deduplicated

    def filter_jobs(
        self,
        jobs: List[JobItem],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[JobItem]:
        """
        过滤岗位数据

        Args:
            jobs: 岗位数据列表
            filters: 过滤条件

        Returns:
            过滤后的岗位列表
        """
        if not filters:
            return jobs

        filtered_jobs = []

        for job in jobs:
            include = True

            # 薪资过滤
            if "min_salary" in filters and job.salary_min:
                if job.salary_min < filters["min_salary"]:
                    include = False

            if "max_salary" in filters and job.salary_max:
                if job.salary_max > filters["max_salary"]:
                    include = False

            # 地点过滤
            if "locations" in filters and job.location:
                if not any(loc in job.location for loc in filters["locations"]):
                    include = False

            # 岗位类型过滤
            if "job_types" in filters and job.job_type:
                if job.job_type not in filters["job_types"]:
                    include = False

            # 学历过滤
            if "education" in filters and job.education:
                # 学历等级映射
                education_levels = {"不限": 0, "大专": 1, "本科": 2, "硕士": 3, "博士": 4}
                job_level = education_levels.get(job.education, 0)
                filter_level = education_levels.get(filters["education"], 0)

                if job_level < filter_level:
                    include = False

            if include:
                filtered_jobs.append(job)

        self.logger.info(f"过滤结果: {len(jobs)} -> {len(filtered_jobs)}")
        return filtered_jobs


# 工具函数：创建搜索调度器实例
def create_search_scheduler(crawlers: List[BaseCrawler]) -> SearchScheduler:
    """创建搜索调度器实例"""
    return SearchScheduler(crawlers=crawlers)