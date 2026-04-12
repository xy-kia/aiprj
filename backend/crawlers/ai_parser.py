"""
AI网页解析器 - 使用大模型解析网页内容，提取结构化岗位数据
当传统解析方法失败时，使用AI解析作为备用方案

支持从用户配置(UserConfig)初始化，使用用户个人的AI API配置

参考文档：Functional_Spec.md 第2.2节
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import openai
from openai import APITimeoutError, APIConnectionError, AuthenticationError, APIError
try:
    from ..config.settings import settings
except ImportError:
    # 当直接运行或路径不同时
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.settings import settings


class AIParser:
    """AI网页解析器"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.1,
        user_config: Optional[Any] = None  # UserConfig模型对象
    ):
        """
        初始化AI解析器

        Args:
            api_key: API密钥，如未提供则使用配置
            base_url: API基础URL，如未提供则使用配置
            model: 模型名称，如未提供则使用配置
            max_tokens: 最大token数
            temperature: 温度参数
            user_config: 用户配置对象，优先使用用户配置
        """
        # 优先使用用户配置
        if user_config:
            # 如果用户配置已启用，使用用户配置
            if getattr(user_config, 'enabled', False):
                # 尝试导入解密函数，如果失败则使用原始密钥
                try:
                    from ..app.api.v1.endpoints.config import decrypt_api_key
                    decrypted_key = decrypt_api_key(user_config.api_key)
                except ImportError:
                    self.logger.warning("无法导入decrypt_api_key，使用原始API密钥")
                    decrypted_key = user_config.api_key  # 使用原始值

                if decrypted_key:
                    self.api_key = decrypted_key
                    self.base_url = user_config.base_url
                    self.model = user_config.default_model
                    # 使用用户配置的温度和最大token数（如果有的话）
                    if hasattr(user_config, 'temperature'):
                        self.temperature = user_config.temperature
                    if hasattr(user_config, 'max_tokens'):
                        self.max_tokens = user_config.max_tokens
                    self.logger = logging.getLogger(__name__)
                    self.logger.info(f"使用用户AI配置，模型: {self.model}")
                else:
                    # 解密失败或密钥为空，使用参数或全局配置
                    self.api_key = api_key or settings.OPENAI_API_KEY
                    self.base_url = base_url or settings.OPENAI_BASE_URL
                    self.model = model or settings.OPENAI_MODEL
                    self.max_tokens = max_tokens
                    self.temperature = temperature
                    self.logger = logging.getLogger(__name__)
                    self.logger.warning("用户API密钥无效或解密失败，使用备用配置")
            else:
                # 用户配置未启用，使用参数或全局配置
                self.api_key = api_key or settings.OPENAI_API_KEY
                self.base_url = base_url or settings.OPENAI_BASE_URL
                self.model = model or settings.OPENAI_MODEL
                self.max_tokens = max_tokens
                self.temperature = temperature
                self.logger = logging.getLogger(__name__)
        else:
            # 没有用户配置，使用参数或全局配置
            self.api_key = api_key or settings.OPENAI_API_KEY
            self.base_url = base_url or settings.OPENAI_BASE_URL
            self.model = model or settings.OPENAI_MODEL
            self.max_tokens = max_tokens
            self.temperature = temperature
            self.logger = logging.getLogger(__name__)

        # 初始化OpenAI客户端
        # 设置连接超时30秒，读取超时1800秒（30分钟），防止慢速API或网络问题
        timeout_config = (30.0, 1800.0)  # (connect_timeout, read_timeout)
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url if self.base_url != "https://api.openai.com/v1" else None,
            timeout=timeout_config
        )
        self.logger.info(f"AI解析器初始化完成，使用模型: {self.model}，base_url: {self.base_url}，超时设置: {timeout_config} 秒")

        # 提示词模板
        self.prompt_templates = {
            "boss_list_page": """你是一名专业的招聘网站数据提取专家。请从以下BOSS直聘岗位列表页的HTML内容中提取所有岗位信息。

网页内容摘要:
{html_summary}

请仔细分析HTML内容，提取所有你能找到的岗位信息。每个岗位应包含以下字段：
1. title: 岗位标题（如"Python开发工程师"）
2. company: 公司名称（如"字节跳动"）
3. location: 工作地点（如"北京"）
4. salary_text: 薪资范围（如"8-10K"，"面议"）
5. experience: 经验要求（如"经验不限"，"1-3年"）
6. education: 学历要求（如"本科"，"大专"）
7. skills: 技能标签列表（如["Python", "Django"]）
8. description: 岗位描述（如果有的话）
9. id: 岗位ID或标识符（如果有的话）
10. url: 岗位详情页URL（如果有的话）

重要要求：
1. 仔细检查HTML内容，寻找任何看起来像岗位信息的片段
2. 即使信息不完整，也请提取你能找到的部分字段
3. 如果同一岗位信息重复出现，只提取一次
4. 薪资范围保持原样，不要修改格式
5. 经验要求和学历要求保持原样
6. 技能标签提取为列表，如果没有技能标签则留空列表
7. 输出必须是一个有效的JSON数组，每个元素是一个岗位对象
8. 如果找不到任何岗位，返回空数组 []

示例输出格式：
[
  {
    "title": "Python开发工程师",
    "company": "科技有限公司",
    "location": "上海",
    "salary_text": "15-25K",
    "experience": "1-3年",
    "education": "本科",
    "skills": ["Python", "Django", "MySQL"],
    "description": "负责Python后端开发",
    "id": "abc123",
    "url": "https://www.zhipin.com/job_detail/abc123.html"
  }
]

请直接输出JSON数组，不要有任何其他解释或文本。""",

            "boss_detail_page": """你是一名专业的招聘网站数据提取专家。请从以下BOSS直聘岗位详情页的HTML内容中提取岗位详细信息。

网页内容摘要:
{html_summary}

请提取以下字段:
1. title: 岗位标题
2. company: 公司名称
3. location: 工作地点
4. salary_text: 薪资范围
5. experience: 经验要求
6. education: 学历要求
7. description: 岗位描述（合并所有描述内容）
8. requirements: 岗位要求列表（从描述中提取具体要求，每项作为一个列表元素）
9. skills: 技能标签列表（从描述和要求中提取关键技术关键词）
10. company_size: 公司规模（如果有的话）
11. id: 岗位ID或标识符
12. url: 岗位详情页URL

重要要求：
1. 仔细分析HTML，寻找岗位详情信息
2. 岗位描述字段应包含所有描述文本，合并成一段
3. 岗位要求从描述中提取，每个要求作为列表的一个元素
4. 技能标签应该是技术关键词，如"Python", "Java", "React"等
5. 如果某个字段没有找到，使用空字符串或空列表
6. 输出必须是一个有效的JSON对象

示例输出格式：
{
  "title": "Python高级开发工程师",
  "company": "科技有限公司",
  "location": "北京",
  "salary_text": "25-40K·15薪",
  "experience": "3-5年",
  "education": "本科",
  "description": "负责公司核心业务系统开发...",
  "requirements": ["3年以上Python开发经验", "熟悉Django/Flask框架", "有高并发系统经验"],
  "skills": ["Python", "Django", "MySQL", "Redis", "Linux"],
  "company_size": "1000-9999人",
  "id": "xyz789",
  "url": "https://www.zhipin.com/job_detail/xyz789.html"
}

请直接输出JSON对象，不要有任何其他解释或文本。""",

            "generic_job_page": """你是一名专业的招聘网站数据提取专家。请从以下招聘网页的HTML内容中提取岗位信息。

网页内容摘要:
{html_summary}

请尽可能提取以下字段:
1. title: 岗位标题
2. company: 公司名称
3. location: 工作地点
4. salary_text: 薪资范围
5. experience: 经验要求
6. education: 学历要求
7. description: 岗位描述
8. skills: 技能标签列表
9. id: 岗位ID或标识符
10. url: 岗位详情页URL

重要要求：
1. 仔细分析HTML内容，识别任何包含岗位信息的区域
2. 即使信息不完整，也请提取你能找到的字段
3. 如果找不到某个字段，使用空字符串或空列表
4. 输出格式为JSON对象（单个岗位）或JSON数组（多个岗位）
5. 如果页面包含多个岗位，请输出JSON数组；如果只有一个岗位，输出JSON对象

示例输出（单个岗位）：
{
  "title": "Java开发工程师",
  "company": "互联网公司",
  "location": "深圳",
  "salary_text": "20-30K",
  "experience": "3-5年",
  "education": "本科",
  "description": "负责Java后端开发...",
  "skills": ["Java", "Spring", "MySQL"],
  "id": "job123",
  "url": "https://example.com/job/job123"
}

示例输出（多个岗位）：
[
  {
    "title": "前端开发工程师",
    "company": "科技公司",
    "location": "杭州",
    "salary_text": "15-25K",
    "experience": "1-3年",
    "education": "本科",
    "skills": ["JavaScript", "React", "Vue"],
    "id": "fe001",
    "url": "https://example.com/job/fe001"
  }
]

请直接输出JSON，不要有任何其他解释或文本。"""
        }

    def _prepare_html_summary(self, html: str, max_length: int = 8000) -> str:
        """
        准备HTML摘要，减少token使用

        Args:
            html: 原始HTML
            max_length: 最大字符长度

        Returns:
            摘要文本
        """
        if len(html) <= max_length:
            return html

        # 提取可能包含数据的部分
        # 1. 查找script标签中的JSON数据
        json_patterns = [
            r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*;',
            r'window\.__INITIAL_STATE__\s*=\s*({.*?})\s*</script>',
            r'<script id="__NEXT_DATA__"[^>]*>({.*?})</script>',
            r'<script[^>]*>window\.__NUXT__\s*=\s*({.*?});</script>',
            r'<script[^>]*>window\.__REDUX_STATE__\s*=\s*({.*?});</script>',
        ]

        for pattern in json_patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                json_str = match.group(1)
                try:
                    data = json.loads(json_str)
                    # 提取关键部分
                    summary = f"页面包含JSON数据，长度: {len(json_str)} 字符"

                    # 查找jobs相关字段
                    def find_jobs(obj, path="", depth=0):
                        if depth > 3:
                            return []
                        if isinstance(obj, dict):
                            results = []
                            for key, value in obj.items():
                                if 'job' in key.lower() or 'list' in key.lower():
                                    results.append(f"{path}.{key}: 找到字段")
                                    if isinstance(value, (list, dict)) and len(str(value)) < 500:
                                        results.append(f"  示例: {str(value)[:200]}")
                                results.extend(find_jobs(value, f"{path}.{key}", depth+1))
                            return results
                        elif isinstance(obj, list) and len(obj) > 0:
                            if len(obj) > 3:
                                return [f"{path}: 列表长度 {len(obj)}"]
                            else:
                                return [f"{path}: {obj}"]
                        return []

                    job_fields = find_jobs(data)
                    if job_fields:
                        summary += "\n" + "\n".join(job_fields[:10])
                    return summary[:max_length]
                except json.JSONDecodeError:
                    continue

        # 2. 提取包含岗位信息的HTML片段
        # 查找常见的岗位容器类（包括BOSS直聘和其他招聘网站）
        container_patterns = [
            # BOSS直聘常见类名
            r'<div[^>]*class="[^"]*job-card[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*job-item[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*job-list[^"]*"[^>]*>.*?</div>',
            r'<li[^>]*class="[^"]*job-item[^"]*"[^>]*>.*?</li>',
            r'<div[^>]*class="[^"]*job-primary[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*job-box[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*info-primary[^"]*"[^>]*>.*?</div>',
            # 通用招聘网站类名
            r'<div[^>]*class="[^"]*position[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*job[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*recruit[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*vacancy[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*career[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*opening[^"]*"[^>]*>.*?</div>',
            # 智联招聘、前程无忧等
            r'<div[^>]*class="[^"]*joblist[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*jobInfo[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*jobinfo[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*el-card[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*position-list[^"]*"[^>]*>.*?</div>',
        ]

        extracted_parts = []
        for pattern in container_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                extracted_parts.extend(matches[:5])  # 取前5个

        if extracted_parts:
            summary = "提取到的岗位容器片段:\n" + "\n---\n".join(extracted_parts[:3])
            return summary[:max_length]

        # 3. 尝试提取包含岗位相关关键词的文本片段
        # 定义岗位相关关键词
        job_keywords = ['薪资', '工资', '薪', '经验', '学历', '本科', '大专', '硕士', '公司', '岗位', '职位', '招聘', '要求', '职责', '技能', '技术']

        # 查找包含这些关键词的div或span元素
        keyword_patterns = []
        for keyword in job_keywords:
            # 查找包含关键词的标签，尽量获取周围上下文
            keyword_patterns.append(r'<[^>]*>[^<]*{}[^<]*</[^>]*>'.format(re.escape(keyword)))

        keyword_matches = []
        for pattern in keyword_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            keyword_matches.extend(matches[:5])  # 每个关键词取前5个

        if keyword_matches:
            unique_matches = list(dict.fromkeys(keyword_matches))  # 去重保持顺序
            summary = "包含岗位关键词的片段:\n" + "\n---\n".join(unique_matches[:10])
            return summary[:max_length]

        # 4. 简单截取中间部分
        half = len(html) // 2
        start = max(0, half - max_length // 2)
        end = min(len(html), half + max_length // 2)
        summary = html[start:end]

        return f"HTML中间部分截取 ({start}-{end}):\n{summary}"

    def parse_list_page(self, html: str, platform: str = "BOSS直聘") -> List[Dict[str, Any]]:
        """
        解析列表页

        Args:
            html: 页面HTML内容
            platform: 平台名称，用于选择提示词模板

        Returns:
            岗位数据列表
        """
        # 检查API密钥是否有效
        if not self.api_key or self.api_key.strip() == "":
            self.logger.warning("AI解析器API密钥为空，跳过AI解析")
            return []

        try:
            # 准备HTML摘要
            html_summary = self._prepare_html_summary(html)

            # 选择提示词模板
            if "boss" in platform.lower() or "直聘" in platform:
                template_key = "boss_list_page"
            else:
                template_key = "generic_job_page"

            prompt = self.prompt_templates[template_key].format(html_summary=html_summary)

            self.logger.info(f"使用AI解析 {platform} 列表页，HTML摘要长度: {len(html_summary)}")

            # 调用AI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一名专业的网页数据提取助手，擅长从HTML中提取结构化数据。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
                timeout=1800.0  # 增加到1800秒（30分钟）防止超时
            )

            # 解析响应
            content = response.choices[0].message.content
            data = json.loads(content)

            # 处理响应格式
            jobs = []
            if isinstance(data, list):
                jobs = data
            elif isinstance(data, dict):
                # 如果是字典，尝试查找包含岗位列表的字段
                for value in data.values():
                    if isinstance(value, list):
                        jobs = value
                        break
                if not jobs:
                    # 如果没有找到列表，将整个字典作为单个岗位
                    jobs = [data]

            self.logger.info(f"AI解析成功，提取到 {len(jobs)} 个岗位")
            return jobs

        except json.JSONDecodeError as e:
            self.logger.error(f"AI响应JSON解析失败: {e}")
            # 尝试从响应中提取JSON
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                    if isinstance(data, list):
                        self.logger.info(f"从响应中提取JSON成功，获取 {len(data)} 个岗位")
                        return data
                except:
                    pass

            self.logger.error(f"AI响应内容: {content[:500]}...")
            return []

        except APITimeoutError as e:
            self.logger.error(f"AI解析超时: {e}，请检查网络连接或API服务状态，超时设置为1800秒")
            return []
        except APIConnectionError as e:
            self.logger.error(f"AI解析连接错误: {e}，请检查网络连接或代理设置")
            return []
        except AuthenticationError as e:
            self.logger.error(f"AI API认证失败: {e}，请检查API密钥是否正确")
            return []
        except APIError as e:
            self.logger.error(f"AI API错误: {e}，可能是服务端问题")
            return []
        except Exception as e:
            self.logger.error(f"AI解析失败: {e}")
            return []

    def parse_detail_page(self, html: str, platform: str = "BOSS直聘") -> Dict[str, Any]:
        """
        解析详情页

        Args:
            html: 页面HTML内容
            platform: 平台名称

        Returns:
            岗位详细数据
        """
        # 检查API密钥是否有效
        if not self.api_key or self.api_key.strip() == "":
            self.logger.warning("AI解析器API密钥为空，跳过AI解析")
            return {}

        try:
            html_summary = self._prepare_html_summary(html)

            if "boss" in platform.lower() or "直聘" in platform:
                template_key = "boss_detail_page"
            else:
                template_key = "generic_job_page"

            prompt = self.prompt_templates[template_key].format(html_summary=html_summary)

            self.logger.info(f"使用AI解析 {platform} 详情页，HTML摘要长度: {len(html_summary)}")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一名专业的网页数据提取助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"},
                timeout=1800.0  # 增加到1800秒（30分钟）防止超时
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            if isinstance(data, dict):
                self.logger.info(f"AI解析详情页成功")
                return data
            else:
                self.logger.warning(f"AI响应不是字典类型: {type(data)}")
                return {}

        except APITimeoutError as e:
            self.logger.error(f"AI解析详情页超时: {e}，请检查网络连接或API服务状态，超时设置为1800秒")
            return {}
        except APIConnectionError as e:
            self.logger.error(f"AI解析详情页连接错误: {e}，请检查网络连接或代理设置")
            return {}
        except AuthenticationError as e:
            self.logger.error(f"AI API认证失败: {e}，请检查API密钥是否正确")
            return {}
        except APIError as e:
            self.logger.error(f"AI API错误: {e}，可能是服务端问题")
            return {}
        except Exception as e:
            self.logger.error(f"AI解析详情页失败: {e}")
            return {}

    def extract_jobs_from_html(self, html: str, platform: str = "unknown") -> List[Dict[str, Any]]:
        """
        通用方法：从HTML中提取岗位数据（自动判断页面类型）

        Args:
            html: 页面HTML内容
            platform: 平台名称

        Returns:
            岗位数据列表
        """
        # 简单判断页面类型
        if self._is_list_page(html):
            return self.parse_list_page(html, platform)
        else:
            # 可能是详情页或混合页面
            job = self.parse_detail_page(html, platform)
            return [job] if job else []

    def _is_list_page(self, html: str) -> bool:
        """判断是否为列表页"""
        list_indicators = [
            r'job-card',
            r'job-item',
            r'job-list',
            r'职位列表',
            r'岗位列表',
            r'招聘列表'
        ]

        for indicator in list_indicators:
            if re.search(indicator, html, re.IGNORECASE):
                return True

        # 检查是否有多个相似的结构
        div_count = len(re.findall(r'<div[^>]*class="[^"]*job[^"]*"[^>]*>', html, re.IGNORECASE))
        if div_count > 2:
            return True

        return False


# 工具函数：创建AI解析器实例
def create_ai_parser() -> AIParser:
    """创建AI解析器实例"""
    return AIParser()