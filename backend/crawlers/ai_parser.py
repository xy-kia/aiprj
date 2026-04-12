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
            "boss_list_page": """你是一名网页数据提取专家。请从以下BOSS直聘岗位列表页的HTML内容中提取所有岗位信息。

网页内容摘要:
{html_summary}

请提取以下字段的岗位数据:
1. 岗位标题 (title)
2. 公司名称 (company)
3. 工作地点 (location)
4. 薪资范围 (salary_text)
5. 经验要求 (experience)
6. 学历要求 (education)
7. 技能标签 (skills)
8. 岗位描述 (description) - 如果有的话
9. 岗位ID或URL (id, url)

要求:
- 只提取实际存在的岗位数据，忽略模板、导航等无关内容
- 薪资范围保持原样，如"8-10K"
- 经验要求和学历要求保持原样，如"经验不限"、"本科"
- 技能标签提取为列表
- 如果没有某个字段，留空字符串或空列表
- 输出格式为JSON数组，每个元素是一个岗位对象

请直接输出JSON数组，不要有其他内容。""",

            "boss_detail_page": """你是一名网页数据提取专家。请从以下BOSS直聘岗位详情页的HTML内容中提取岗位详细信息。

网页内容摘要:
{html_summary}

请提取以下字段:
1. 岗位标题 (title)
2. 公司名称 (company)
3. 工作地点 (location)
4. 薪资范围 (salary_text)
5. 经验要求 (experience)
6. 学历要求 (education)
7. 岗位描述 (description)
8. 岗位要求 (requirements) - 列表形式
9. 技能标签 (skills) - 列表形式
10. 公司规模 (company_size) - 如果有的话
11. 岗位ID或URL (id, url)

要求:
- 只提取实际存在的岗位数据
- 岗位描述和岗位要求分开提取
- 技能标签从岗位要求或描述中提取关键词
- 输出格式为JSON对象

请直接输出JSON对象，不要有其他内容。""",

            "generic_job_page": """你是一名网页数据提取专家。请从以下招聘网页的HTML内容中提取岗位信息。

网页内容摘要:
{html_summary}

请尽可能提取以下字段:
1. 岗位标题 (title)
2. 公司名称 (company)
3. 工作地点 (location)
4. 薪资范围 (salary_text)
5. 经验要求 (experience)
6. 学历要求 (education)
7. 岗位描述 (description)
8. 技能标签 (skills)
9. 岗位ID或URL (id, url)

要求:
- 识别网页中的岗位信息区域
- 提取实际存在的字段
- 保持原始文本格式
- 输出格式为JSON对象

请直接输出JSON对象，不要有其他内容。"""
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
        # 查找常见的岗位容器类
        container_patterns = [
            r'<div[^>]*class="[^"]*job-card[^"]*"[^>]*>.*?</div>',
            r'<div[^>]*class="[^"]*job-item[^"]*"[^>]*>.*?</div>',
            r'<li[^>]*class="[^"]*job-item[^"]*"[^>]*>.*?</li>',
        ]

        extracted_parts = []
        for pattern in container_patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            if matches:
                extracted_parts.extend(matches[:5])  # 取前5个

        if extracted_parts:
            summary = "提取到的岗位容器片段:\n" + "\n---\n".join(extracted_parts[:3])
            return summary[:max_length]

        # 3. 简单截取中间部分
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