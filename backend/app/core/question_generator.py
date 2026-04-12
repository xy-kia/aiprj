"""
个性化问题生成器 - 基于岗位JD生成面试问题
设计两套问题：一般实习版和高阶实习/校招版

参考文档：Workflow.md 第3.4节、Functional_Spec.md 第2.3节
"""

import json
import re
import asyncio
import logging
import redis
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import openai
from backend.config.settings import settings


@dataclass
class InterviewQuestion:
    """面试问题"""
    question: str
    question_type: str  # 类型：technical, behavioral, situational, general
    target_skill: Optional[str] = None  # 考察的技能点
    jd_reference: Optional[str] = None  # JD原文依据
    suggested_time: int = 120  # 建议回答时间（秒）
    difficulty: str = "medium"  # 难度：easy, medium, hard
    scoring_criteria: Optional[List[str]] = None  # 评分标准


class QuestionGenerator:
    """问题生成器"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        cache_enabled: bool = True,
        redis_client: Optional[redis.Redis] = None,
        redis_prefix: str = "question_gen:",
        max_concurrent_requests: int = 5
    ):
        """
        初始化问题生成器

        Args:
            openai_api_key: OpenAI API密钥，如未提供则使用配置
            model: 模型名称
            cache_enabled: 是否启用缓存
            redis_client: Redis客户端实例，如未提供则根据配置创建
            redis_prefix: Redis键前缀
            max_concurrent_requests: 最大并发请求数，用于限流
        """
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.cache_enabled = cache_enabled
        self.redis_prefix = redis_prefix
        self.max_concurrent_requests = max_concurrent_requests

        # 日志
        self.logger = logging.getLogger(__name__)

        # 初始化OpenAI客户端
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=settings.OPENAI_BASE_URL
        )

        # 初始化Redis客户端
        self.redis_client = redis_client or self._init_redis_client()

        # 内存缓存作为后备
        self.memory_cache = {}

        # 异步请求信号量（用于限流）
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

        # Prompt模板
        self.prompt_templates = self._init_prompt_templates()

    def _init_redis_client(self) -> Optional[redis.Redis]:
        """
        初始化Redis客户端

        Returns:
            Redis客户端实例，如果配置不可用则返回None
        """
        try:
            # 解析Redis URL
            redis_url = settings.REDIS_URL
            if redis_url.startswith("redis://"):
                # 从URL中提取信息
                import urllib.parse
                parsed = urllib.parse.urlparse(redis_url)

                host = parsed.hostname or "localhost"
                port = parsed.port or 6379
                db = parsed.path.lstrip('/') or '0'
                password = parsed.password

                client = redis.Redis(
                    host=host,
                    port=port,
                    db=int(db) if db.isdigit() else 0,
                    password=password,
                    decode_responses=True,  # 自动解码字符串
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    max_connections=10
                )

                # 测试连接
                client.ping()
                self.logger.info(f"Redis连接成功: {host}:{port}/{db}")
                return client
            else:
                self.logger.warning(f"Redis URL格式不支持: {redis_url}")
                return None

        except Exception as e:
            self.logger.warning(f"Redis连接失败，将使用内存缓存: {e}")
            return None

    def _init_prompt_templates(self) -> Dict[str, str]:
        """初始化Prompt模板"""
        return {
            "intern_general": """你是一名资深面试官，需要为实习岗位生成面试问题。

岗位信息：
- 职位：{job_title}
- 公司：{company}
- 岗位描述：{job_description}
- 岗位要求：{job_requirements}

请生成{num_questions}个面试问题，针对实习岗位的特点，重点考察：
1. 基础技能掌握程度
2. 学习能力和执行力
3. 基本的问题解决能力
4. 团队协作意识
5. 职业发展意愿

要求：
- 问题应具体、可操作，避免过于宽泛
- 包含技术问题和非技术问题
- 每个问题标注考察点、建议回答时间
- 输出格式为JSON数组，每个元素包含以下字段：
  - question: 问题内容
  - question_type: 问题类型（technical/behavioral/situational/general）
  - target_skill: 考察的技能点（如Python、团队协作、问题解决等）
  - jd_reference: 参考了JD中的哪部分要求
  - suggested_time: 建议回答时间（秒）
  - difficulty: 难度（easy/medium/hard）

请直接输出JSON数组，不要有其他内容。""",

            "intern_advanced": """你是一名资深面试官，需要为高阶实习或校招岗位生成面试问题。

岗位信息：
- 职位：{job_title}
- 公司：{company}
- 岗位描述：{job_description}
- 岗位要求：{job_requirements}

请生成{num_questions}个有深度的面试问题，针对高阶实习/校招岗位的特点，重点考察：
1. 项目深度和技术细节
2. 复杂问题解决能力
3. 业务理解和行业洞察
4. 系统设计能力
5. 团队协作和领导潜力
6. 创新思维和学习能力

要求：
- 问题要有深度和挑战性，能够区分候选人的水平
- 包含开放性问题和技术深度问题
- 每个问题标注考察点、建议回答时间、评分标准
- 输出格式为JSON数组，每个元素包含以下字段：
  - question: 问题内容
  - question_type: 问题类型（technical/behavioral/situational/general）
  - target_skill: 考察的技能点
  - jd_reference: 参考了JD中的哪部分要求
  - suggested_time: 建议回答时间（秒）
  - difficulty: 难度（easy/medium/hard）
  - scoring_criteria: 评分标准列表（至少3条）

请直接输出JSON数组，不要有其他内容。"""
        }

    def _get_cached(self, cache_key: str) -> Optional[Any]:
        """获取缓存数据"""
        if not self.cache_enabled:
            return None

        # 先尝试Redis缓存
        if self.redis_client is not None:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    self.logger.info(f"命中Redis缓存: {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                self.logger.warning(f"Redis缓存获取失败，回退到内存缓存: {e}")

        # 回退到内存缓存
        if cache_key in self.memory_cache:
            self.logger.info(f"命中内存缓存: {cache_key}")
            return self.memory_cache[cache_key]

        return None

    def _set_cached(self, cache_key: str, data: Any, ttl: int = 3600):
        """设置缓存数据"""
        if not self.cache_enabled:
            return

        # 序列化数据
        try:
            serialized = json.dumps(data, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"缓存数据序列化失败: {e}")
            return

        # 先尝试Redis缓存
        if self.redis_client is not None:
            try:
                self.redis_client.setex(cache_key, ttl, serialized)
                self.logger.debug(f"数据已缓存到Redis: {cache_key}")
                return
            except Exception as e:
                self.logger.warning(f"Redis缓存设置失败，回退到内存缓存: {e}")

        # 回退到内存缓存（内存缓存无TTL）
        self.memory_cache[cache_key] = data
        self.logger.debug(f"数据已缓存到内存: {cache_key}")

    def generate_questions(
        self,
        job_data: Dict[str, Any],
        question_type: str = "intern_general",
        num_questions: int = 8
    ) -> List[InterviewQuestion]:
        """
        生成面试问题

        Args:
            job_data: 岗位数据
            question_type: 问题类型，可选 "intern_general"（一般实习）或 "intern_advanced"（高阶实习/校招）
            num_questions: 问题数量

        Returns:
            面试问题列表
        """
        # 检查缓存
        cache_key = self._generate_cache_key(job_data, question_type, num_questions)
        cached = self._get_cached(cache_key)
        if cached is not None:
            self.logger.info(f"命中缓存: {cache_key}")
            return self._deserialize_questions(cached["questions"])

        # 提取岗位信息
        job_info = self._extract_job_info(job_data)

        # 选择模板
        template = self.prompt_templates.get(question_type, self.prompt_templates["intern_general"])

        # 填充模板
        prompt = template.format(
            job_title=job_info["title"],
            company=job_info["company"],
            job_description=job_info["description"],
            job_requirements=job_info["requirements"],
            num_questions=num_questions
        )

        self.logger.info(f"生成问题: {job_info['title']}, 类型: {question_type}")

        try:
            # 调用LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一名专业的面试问题设计师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )

            # 解析响应
            content = response.choices[0].message.content
            questions_data = self._parse_llm_response(content)

            # 转换为InterviewQuestion对象
            questions = self._create_question_objects(questions_data)

            # 过滤和排序问题
            filtered_questions = self._filter_questions(questions)

            # 缓存结果
            if self.cache_enabled:
                cache_data = {
                    "questions": self._serialize_questions(filtered_questions),
                    "timestamp": datetime.now().isoformat()
                }
                self._set_cached(cache_key, cache_data, ttl=3600)

            return filtered_questions

        except Exception as e:
            self.logger.error(f"生成问题失败: {e}")
            # 返回备用问题
            return self._generate_fallback_questions(job_info)

    def _extract_job_info(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """从岗位数据中提取信息"""
        title = job_data.get("title", "")
        company = job_data.get("company", "")

        # 描述和要求
        description = job_data.get("description", "")
        requirements = job_data.get("requirements", [])

        # 如果requirements是列表，转换为字符串
        if isinstance(requirements, list):
            requirements_text = "\n".join([f"- {req}" for req in requirements if req])
        else:
            requirements_text = str(requirements)

        # 提取技能关键词
        skills = job_data.get("skills", [])
        if skills and isinstance(skills, list):
            skills_text = "、".join(skills[:5])
            if skills_text:
                description = f"{description}\n\n所需技能: {skills_text}"

        return {
            "title": title,
            "company": company,
            "description": description[:1000],  # 限制长度
            "requirements": requirements_text[:1000]
        }

    def _generate_cache_key(
        self,
        job_data: Dict[str, Any],
        question_type: str,
        num_questions: int
    ) -> str:
        """生成缓存键"""
        import hashlib

        key_data = {
            "title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "description_hash": hashlib.md5(
                job_data.get("description", "").encode()
            ).hexdigest()[:16],
            "question_type": question_type,
            "num_questions": num_questions
        }

        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _parse_llm_response(self, content: str) -> List[Dict[str, Any]]:
        """解析LLM响应"""
        try:
            # 提取JSON部分
            json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # 尝试直接解析
                json_str = content

            data = json.loads(json_str)

            # 如果是字典且包含questions字段
            if isinstance(data, dict):
                if "questions" in data:
                    questions = data["questions"]
                else:
                    # 尝试查找数组类型的值
                    questions = []
                    for value in data.values():
                        if isinstance(value, list):
                            questions = value
                            break
            else:
                questions = data

            if not isinstance(questions, list):
                questions = [questions]

            return questions

        except Exception as e:
            self.logger.error(f"解析LLM响应失败: {e}, 内容: {content[:200]}...")
            return []

    def _create_question_objects(self, questions_data: List[Dict]) -> List[InterviewQuestion]:
        """创建InterviewQuestion对象"""
        questions = []

        for item in questions_data:
            try:
                # 确保必要字段存在
                question_text = item.get("question", "")
                if not question_text:
                    continue

                # 处理评分标准
                scoring_criteria = item.get("scoring_criteria")
                if isinstance(scoring_criteria, str):
                    scoring_criteria = [criteria.strip() for criteria in scoring_criteria.split(",")]
                elif not isinstance(scoring_criteria, list):
                    scoring_criteria = None

                question = InterviewQuestion(
                    question=question_text,
                    question_type=item.get("question_type", "general"),
                    target_skill=item.get("target_skill"),
                    jd_reference=item.get("jd_reference"),
                    suggested_time=int(item.get("suggested_time", 120)),
                    difficulty=item.get("difficulty", "medium"),
                    scoring_criteria=scoring_criteria
                )

                questions.append(question)

            except Exception as e:
                self.logger.warning(f"创建问题对象失败: {e}, 数据: {item}")

        return questions

    def _filter_questions(self, questions: List[InterviewQuestion]) -> List[InterviewQuestion]:
        """过滤问题（去重、质量检查）"""
        if not questions:
            return []

        filtered = []
        seen_questions = set()

        for question in questions:
            # 检查重复
            question_key = question.question
            if question_key in seen_questions:
                continue

            seen_questions.add(question_key)

            # 质量检查
            if self._is_quality_question(question):
                filtered.append(question)

        # 确保问题多样性
        filtered = self._ensure_diversity(filtered)

        return filtered

    def _is_quality_question(self, question: InterviewQuestion) -> bool:
        """检查问题质量"""
        # 问题长度检查
        if len(question.question) < 10 or len(question.question) > 500:
            return False

        # 问题类型检查
        valid_types = {"technical", "behavioral", "situational", "general"}
        if question.question_type not in valid_types:
            return False

        # 难度检查
        valid_difficulties = {"easy", "medium", "hard"}
        if question.difficulty not in valid_difficulties:
            return False

        # 建议时间检查
        if question.suggested_time < 30 or question.suggested_time > 600:
            return False

        return True

    def _ensure_diversity(self, questions: List[InterviewQuestion]) -> List[InterviewQuestion]:
        """确保问题多样性"""
        if len(questions) <= 1:
            return questions

        # 按类型分组
        type_groups = {}
        for q in questions:
            q_type = q.question_type
            if q_type not in type_groups:
                type_groups[q_type] = []
            type_groups[q_type].append(q)

        # 确保每种类型的问题数量相对均衡
        max_per_type = max(len(v) for v in type_groups.values())
        target_per_type = min(max_per_type, max(2, len(questions) // len(type_groups)))

        selected = []
        for q_type, q_list in type_groups.items():
            # 从每种类型中选择前N个
            selected.extend(q_list[:target_per_type])

        return selected[:len(questions)]  # 保持原数量

    def _serialize_questions(self, questions: List[InterviewQuestion]) -> List[Dict]:
        """序列化问题列表"""
        return [
            {
                "question": q.question,
                "question_type": q.question_type,
                "target_skill": q.target_skill,
                "jd_reference": q.jd_reference,
                "suggested_time": q.suggested_time,
                "difficulty": q.difficulty,
                "scoring_criteria": q.scoring_criteria
            }
            for q in questions
        ]

    def _deserialize_questions(self, questions_data: List[Dict]) -> List[InterviewQuestion]:
        """反序列化问题列表"""
        return self._create_question_objects(questions_data)

    def _generate_fallback_questions(self, job_info: Dict[str, Any]) -> List[InterviewQuestion]:
        """生成备用问题（当LLM调用失败时）"""
        title = job_info["title"]
        skills = ["相关技能", "问题解决", "团队协作"]

        fallback_questions = [
            InterviewQuestion(
                question=f"请介绍一下你对{title}这个岗位的理解。",
                question_type="general",
                target_skill="岗位理解",
                suggested_time=120,
                difficulty="medium"
            ),
            InterviewQuestion(
                question=f"如果你在{title}岗位上遇到了一个技术难题，你会如何解决？",
                question_type="situational",
                target_skill="问题解决",
                suggested_time=180,
                difficulty="medium"
            ),
            InterviewQuestion(
                question="请分享一个你过去在团队中合作的经历。",
                question_type="behavioral",
                target_skill="团队协作",
                suggested_time=150,
                difficulty="easy"
            ),
            InterviewQuestion(
                question=f"你认为在{title}岗位上最重要的技能是什么？为什么？",
                question_type="technical",
                target_skill="技术理解",
                suggested_time=120,
                difficulty="medium"
            )
        ]

        return fallback_questions[:4]

    async def generate_questions_async(
        self,
        job_data: Dict[str, Any],
        question_type: str = "intern_general",
        num_questions: int = 8
    ) -> List[InterviewQuestion]:
        """异步生成面试问题（带限流）"""
        async with self._semaphore:
            # 在线程池中执行同步方法
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.generate_questions(job_data, question_type, num_questions)
            )


# 工具函数：创建问题生成器实例
def create_question_generator() -> QuestionGenerator:
    """创建问题生成器实例"""
    return QuestionGenerator()