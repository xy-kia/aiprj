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
from openai import APITimeoutError, APIConnectionError, AuthenticationError, APIError
from backend.config.settings import settings


@dataclass
class InterviewQuestion:
    """面试问题"""
    question: str
    question_type: str  # 类型：technical, behavioral, situational, general
    target_skill: Optional[str] = None  # 考察的技能点
    jd_reference: Optional[str] = None  # JD原文依据
    resume_reference: Optional[str] = None  # 简历原文依据（个性化问题）
    suggested_time: int = 120  # 建议回答时间（秒）
    difficulty: str = "medium"  # 难度：easy, medium, hard
    scoring_criteria: Optional[List[str]] = None  # 评分标准


class QuestionGenerator:
    """问题生成器"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
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
            base_url: API基础URL，如未提供则使用配置
            cache_enabled: 是否启用缓存
            redis_client: Redis客户端实例，如未提供则根据配置创建
            redis_prefix: Redis键前缀
            max_concurrent请求数，用于限流
        """
        self.api_key = openai_api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.cache_enabled = cache_enabled
        self.redis_prefix = redis_prefix
        self.max_concurrent_requests = max_concurrent_requests

        # 日志
        self.logger = logging.getLogger(__name__)

        # 初始化OpenAI客户端 - 增加超时时间到1800秒（30分钟），防止慢速API或网络问题
        timeout_config = (30.0, 1800.0)  # (connect_timeout, read_timeout)
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout_config
        )
        self.logger.info(f"问题生成器初始化完成，使用模型: {self.model}，base_url: {self.base_url}，超时设置: {timeout_config} 秒")

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

请直接输出JSON数组，不要有其他内容。""",

            "personalized_intern_general": """你是一名资深面试官，需要为实习岗位生成个性化的面试问题。

岗位信息：
- 职位：{job_title}
- 公司：{company}
- 岗位描述：{job_description}
- 岗位要求：{job_requirements}

求职者个人资料：
{resume_text}

请根据求职者的个人资料，生成{num_questions}个针对性的面试问题，重点考察：
1. 个人经历与岗位的匹配度
2. 技能掌握程度与实践经验
3. 项目经历中的具体贡献
4. 个人优势与岗位需求的结合点
5. 职业发展潜力与学习能力

要求：
- 问题应紧密结合求职者的简历内容，挖掘其独特经历
- 包含技术深度问题和个人经历挖掘问题
- 每个问题标注考察点、建议回答时间
- 输出格式为JSON数组，每个元素包含以下字段：
  - question: 问题内容
  - question_type: 问题类型（technical/behavioral/situational/general）
  - target_skill: 考察的技能点
  - jd_reference: 参考了JD中的哪部分要求
  - suggested_time: 建议回答时间（秒）
  - difficulty: 难度（easy/medium/hard）
  - resume_reference: 参考了简历中的哪部分内容（可选）

请直接输出JSON数组，不要有其他内容。""",

            "personalized_intern_advanced": """你是一名资深面试官，需要为高阶实习或校招岗位生成个性化的面试问题。

岗位信息：
- 职位：{job_title}
- 公司：{company}
- 岗位描述：{job_description}
- 岗位要求：{job_requirements}

求职者个人资料：
{resume_text}

请根据求职者的个人资料，生成{num_questions}个有深度的个性化面试问题，重点考察：
1. 项目深度和技术细节，结合个人经历
2. 复杂问题解决能力与具体案例
3. 业务理解和行业洞察，基于个人背景
4. 系统设计能力与个人项目经验结合
5. 团队协作和领导潜力，基于过往经历
6. 创新思维和学习能力，结合个人特点

要求：
- 问题要有深度和挑战性，能够基于求职者经历进行深度挖掘
- 包含开放性问题和技术深度问题，紧密结合个人经历
- 每个问题标注考察点、建议回答时间、评分标准
- 输出格式为JSON数组，每个元素包含以下字段：
  - question: 问题内容
  - question_type: 问题类型（technical/behavioral/situational/general）
  - target_skill: 考察的技能点
  - jd_reference: 参考了JD中的哪部分要求
  - suggested_time: 建议回答时间（秒）
  - difficulty: 难度（easy/medium/hard）
  - scoring_criteria: 评分标准列表（至少3条）
  - resume_reference: 参考了简历中的哪部分内容（可选）

请直接输出JSON数组，不要有其他内容。""",

            "question_evaluation": """你是一名面试问题评估专家，需要评估生成的面试问题的质量。

请评估以下面试问题，给出综合评分和改进建议。

岗位信息：
- 职位：{title}
- 公司：{company}
- 岗位描述：{description}
- 岗位要求：{requirements}

面试问题列表：
{questions_text}

评估标准：
1. 相关性：问题是否与岗位要求紧密相关
2. 清晰度：问题表述是否清晰明确，无歧义
3. 难度：问题难度是否适合目标岗位（实习/校招）
4. 可操作性：问题是否能够有效考察候选人的能力
5. 多样性：问题是否覆盖多个考察维度
6. 个性化：问题是否结合了求职者个人资料（如果提供了的话）

请对每个问题进行评分（1-10分），并给出整体评估和改进建议。
输出格式为JSON对象，包含以下字段：
  - overall_score: 整体评分（1-10）
  - question_scores: 每个问题的评分列表，与输入顺序对应
  - strengths: 整体优势分析（列表）
  - weaknesses: 整体不足分析（列表）
  - improvement_suggestions: 改进建议（列表）
  - recommended_questions: 推荐保留的问题索引列表（从0开始）

请直接输出JSON对象，不要有其他内容。"""
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
        num_questions: int = 8,
        enable_llm_evaluation: bool = True
    ) -> List[InterviewQuestion]:
        """
        生成面试问题

        Args:
            job_data: 岗位数据
            question_type: 问题类型，可选 "intern_general"（一般实习）或 "intern_advanced"（高阶实习/校招）
            num_questions: 问题数量
            enable_llm_evaluation: 是否启用LLM问题评估，默认True

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

        # 选择模板（如果提供了候选者资料，优先使用个性化模板）
        candidate_profile = job_info.get("candidate_profile", "")
        use_personalized = candidate_profile and len(candidate_profile.strip()) > 0

        template_key = question_type
        if use_personalized:
            personalized_key = f"personalized_{question_type}"
            if personalized_key in self.prompt_templates:
                template_key = personalized_key
            else:
                self.logger.info(f"个性化模板 {personalized_key} 不存在，使用普通模板")

        template = self.prompt_templates.get(template_key, self.prompt_templates["intern_general"])

        # 填充模板
        format_args = {
            "job_title": job_info["title"],
            "company": job_info["company"],
            "job_description": job_info["description"],
            "job_requirements": job_info["requirements"],
            "num_questions": num_questions
        }

        if use_personalized and template_key.startswith("personalized_"):
            format_args["resume_text"] = candidate_profile

        prompt = template.format(**format_args)

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
                max_tokens=4000,  # 增加token数量，适应生成多个问题
                response_format={"type": "json_object"},
                timeout=1800.0  # 增加到1800秒（30分钟）防止超时
            )

            # 解析响应
            content = response.choices[0].message.content
            questions_data = self._parse_llm_response(content)

            # 转换为InterviewQuestion对象
            questions = self._create_question_objects(questions_data)

            # 过滤和排序问题
            filtered_questions = self._filter_questions(questions)

            # 启用LLM评估（可选）
            if enable_llm_evaluation and len(filtered_questions) > 0:
                try:
                    self.logger.info(f"开始LLM问题评估，共{len(filtered_questions)}个问题")
                    evaluation_result = self.evaluate_questions_with_llm(
                        filtered_questions, job_info, question_type
                    )

                    # 根据评估结果进一步过滤问题
                    if evaluation_result and "recommended_questions" in evaluation_result:
                        evaluated_questions = self._filter_questions_by_evaluation(
                            filtered_questions, evaluation_result, num_questions
                        )
                        filtered_questions = evaluated_questions
                        self.logger.info(f"LLM评估完成，保留{len(filtered_questions)}个问题")
                    else:
                        self.logger.warning("LLM评估结果无效，使用原始过滤结果")
                except Exception as e:
                    self.logger.error(f"LLM评估过程中出错: {e}，继续使用过滤后的问题")

            # 确保问题数量不超过要求
            if len(filtered_questions) > num_questions:
                filtered_questions = filtered_questions[:num_questions]

            # 缓存结果
            if self.cache_enabled:
                cache_data = {
                    "questions": self._serialize_questions(filtered_questions),
                    "timestamp": datetime.now().isoformat(),
                    "llm_evaluation_enabled": enable_llm_evaluation
                }
                self._set_cached(cache_key, cache_data, ttl=3600)

            return filtered_questions

        except APITimeoutError as e:
            self.logger.error(f"生成问题超时: {e}，请检查网络连接或API服务状态，超时设置为1800秒")
            # 返回备用问题
            return self._generate_fallback_questions(job_info)
        except APIConnectionError as e:
            self.logger.error(f"生成问题连接错误: {e}，请检查网络连接或代理设置")
            return self._generate_fallback_questions(job_info)
        except AuthenticationError as e:
            self.logger.error(f"AI API认证失败: {e}，请检查API密钥是否正确")
            return self._generate_fallback_questions(job_info)
        except APIError as e:
            self.logger.error(f"AI API错误: {e}，可能是服务端问题")
            return self._generate_fallback_questions(job_info)
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

        # 提取求职者个人资料（如果提供）
        candidate_profile = job_data.get("candidate_profile", "")
        if not candidate_profile:
            candidate_profile = job_data.get("resume_text", "")

        # 如果candidate_profile是字典，转换为字符串
        if isinstance(candidate_profile, dict):
            import json
            candidate_profile = json.dumps(candidate_profile, ensure_ascii=False, indent=2)
        elif isinstance(candidate_profile, list):
            candidate_profile = "\n".join(candidate_profile)

        return {
            "title": title,
            "company": company,
            "description": description[:1000],  # 限制长度
            "requirements": requirements_text[:1000],
            "candidate_profile": candidate_profile[:2000] if candidate_profile else ""  # 限制长度
        }

    def _generate_cache_key(
        self,
        job_data: Dict[str, Any],
        question_type: str,
        num_questions: int
    ) -> str:
        """生成缓存键"""
        import hashlib

        # 提取candidate_profile（用于个性化问题）
        candidate_profile = job_data.get("candidate_profile", "")
        if not candidate_profile:
            candidate_profile = job_data.get("resume_text", "")

        key_data = {
            "title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "description_hash": hashlib.md5(
                job_data.get("description", "").encode()
            ).hexdigest()[:16],
            "candidate_profile_hash": hashlib.md5(
                candidate_profile.encode() if candidate_profile else "".encode()
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
                    resume_reference=item.get("resume_reference"),
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
                "resume_reference": q.resume_reference,
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
        num_questions: int = 8,
        enable_llm_evaluation: bool = True
    ) -> List[InterviewQuestion]:
        """异步生成面试问题（带限流）"""
        async with self._semaphore:
            # 在线程池中执行同步方法
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                lambda: self.generate_questions(job_data, question_type, num_questions, enable_llm_evaluation)
            )

    def evaluate_questions_with_llm(
        self,
        questions: List[InterviewQuestion],
        job_info: Dict[str, Any],
        question_type: str = "intern_general"
    ) -> Dict[str, Any]:
        """
        使用LLM评估生成的问题质量

        Args:
            questions: 面试问题列表
            job_info: 岗位信息字典
            question_type: 问题类型

        Returns:
            评估结果字典
        """
        if not questions:
            return {"overall_score": 0, "question_scores": [], "recommended_questions": []}

        self.logger.info(f"开始LLM问题评估，共{len(questions)}个问题")

        # 准备问题文本
        questions_text = ""
        for i, q in enumerate(questions):
            questions_text += f"{i+1}. {q.question} (类型: {q.question_type}, 难度: {q.difficulty})\n"

        # 获取评估模板
        template = self.prompt_templates.get("question_evaluation")
        if not template:
            self.logger.warning("问题评估模板未找到，跳过评估")
            return {"overall_score": 0, "question_scores": [], "recommended_questions": list(range(len(questions)))}

        # 填充模板
        prompt = template.format(
            title=job_info["title"],
            company=job_info["company"],
            description=job_info["description"],
            requirements=job_info["requirements"],
            questions_text=questions_text
        )

        try:
            # 调用LLM进行评估
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一名专业的面试问题评估专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=3000,  # 增加token数量用于评估多个问题
                response_format={"type": "json_object"},
                timeout=1800.0  # 增加到1800秒（30分钟）防止超时
            )

            # 解析响应
            content = response.choices[0].message.content
            evaluation_result = json.loads(content)

            self.logger.info(f"问题评估完成，整体评分: {evaluation_result.get('overall_score', 'N/A')}")
            return evaluation_result

        except APITimeoutError as e:
            self.logger.error(f"问题评估超时: {e}，请检查网络连接或API服务状态，超时设置为1800秒")
            # 返回默认评估结果，推荐所有问题
            return {
                "overall_score": 7.0,
                "question_scores": [7.0] * len(questions),
                "strengths": ["问题生成正常"],
                "weaknesses": ["评估服务暂时不可用"],
                "improvement_suggestions": ["请确保问题与岗位要求相关"],
                "recommended_questions": list(range(len(questions)))
            }
        except APIConnectionError as e:
            self.logger.error(f"问题评估连接错误: {e}，请检查网络连接或代理设置")
            return {
                "overall_score": 7.0,
                "question_scores": [7.0] * len(questions),
                "strengths": ["问题生成正常"],
                "weaknesses": ["评估服务暂时不可用"],
                "improvement_suggestions": ["请确保问题与岗位要求相关"],
                "recommended_questions": list(range(len(questions)))
            }
        except AuthenticationError as e:
            self.logger.error(f"AI API认证失败: {e}，请检查API密钥是否正确")
            return {
                "overall_score": 7.0,
                "question_scores": [7.0] * len(questions),
                "strengths": ["问题生成正常"],
                "weaknesses": ["评估服务暂时不可用"],
                "improvement_suggestions": ["请确保问题与岗位要求相关"],
                "recommended_questions": list(range(len(questions)))
            }
        except APIError as e:
            self.logger.error(f"AI API错误: {e}，可能是服务端问题")
            return {
                "overall_score": 7.0,
                "question_scores": [7.0] * len(questions),
                "strengths": ["问题生成正常"],
                "weaknesses": ["评估服务暂时不可用"],
                "improvement_suggestions": ["请确保问题与岗位要求相关"],
                "recommended_questions": list(range(len(questions)))
            }
        except Exception as e:
            self.logger.error(f"LLM问题评估失败: {e}")
            # 返回默认评估结果，推荐所有问题
            return {
                "overall_score": 7.0,
                "question_scores": [7.0] * len(questions),
                "strengths": ["问题生成正常"],
                "weaknesses": ["评估服务暂时不可用"],
                "improvement_suggestions": ["请确保问题与岗位要求相关"],
                "recommended_questions": list(range(len(questions)))
            }

    def _filter_questions_by_evaluation(
        self,
        questions: List[InterviewQuestion],
        evaluation_result: Dict[str, Any],
        num_questions: int
    ) -> List[InterviewQuestion]:
        """根据评估结果过滤问题"""
        if not questions or not evaluation_result:
            return questions

        recommended_indices = evaluation_result.get("recommended_questions", [])
        if not recommended_indices:
            # 如果没有推荐索引，使用评分排序
            question_scores = evaluation_result.get("question_scores", [])
            if question_scores and len(question_scores) == len(questions):
                # 根据评分排序，选择最高分的问题
                sorted_indices = sorted(range(len(questions)), key=lambda i: question_scores[i], reverse=True)
                selected_indices = sorted_indices[:num_questions]
                selected_questions = [questions[i] for i in selected_indices]
                self.logger.info(f"根据评分选择了 {len(selected_questions)} 个问题，最高分: {max(question_scores) if question_scores else 'N/A'}")
                return selected_questions
            else:
                # 无法评估，返回原始问题
                return questions[:num_questions]

        # 使用推荐的问题索引
        valid_indices = [i for i in recommended_indices if 0 <= i < len(questions)]
        if not valid_indices:
            return questions[:num_questions]

        # 如果推荐的问题数量超过需求，取前N个
        selected_indices = valid_indices[:num_questions]
        selected_questions = [questions[i] for i in selected_indices]

        self.logger.info(f"根据LLM推荐选择了 {len(selected_questions)} 个问题")

        return selected_questions


# 工具函数：创建问题生成器实例
def create_question_generator(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    cache_enabled: bool = True
) -> QuestionGenerator:
    """创建问题生成器实例

    Args:
        api_key: API密钥，如未提供则使用配置
        model: 模型名称，如未提供则使用配置
        base_url: API基础URL，如未提供则使用配置
        cache_enabled: 是否启用缓存
    """
    return QuestionGenerator(
        openai_api_key=api_key,
        model=model,
        base_url=base_url,
        cache_enabled=cache_enabled
    )