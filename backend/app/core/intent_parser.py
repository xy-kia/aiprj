"""
意向解析器 - 将用户自然语言输入解析为结构化关键词
实现文本清洗、分词、实体识别、关键词扩展、缺失值填充五个步骤

参考文档：Workflow.md 第1.4节、Functional_Spec.md 第2.1节
"""

import re
import jieba
import jieba.posseg as pseg
from typing import Dict, List, Any, Optional, Tuple
import json
import os


class IntentParser:
    """意向解析器"""

    def __init__(self, knowledge_base_path: str = None):
        """
        初始化意向解析器

        Args:
            knowledge_base_path: 知识库路径，默认使用项目内的knowledge目录
        """
        # 设置知识库路径
        if knowledge_base_path is None:
            # 假设项目根目录为当前文件的父目录的父目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            knowledge_base_path = os.path.join(project_root, "knowledge")

        self.knowledge_base_path = knowledge_base_path

        # 加载知识库
        self.skills_data = self._load_skills_data()
        self.skill_relations = self._load_skill_relations()
        self.skill_synonyms = self._load_skill_synonyms()

        # 缓存
        self._skill_names = None

        # 初始化分词器
        self._init_jieba()

    def _load_skills_data(self) -> Dict:
        """加载技能数据"""
        skills_file = os.path.join(self.knowledge_base_path, "skills.json")
        try:
            with open(skills_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: Skills file not found at {skills_file}")
            return {"categories": {}}

    def _load_skill_relations(self) -> Dict:
        """加载技能关系数据"""
        relations_file = os.path.join(self.knowledge_base_path, "skill_relations.json")
        try:
            with open(relations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("relations", {})
        except FileNotFoundError:
            print(f"Warning: Skill relations file not found at {relations_file}")
            return {}

    def _load_skill_synonyms(self) -> Dict:
        """加载技能同义词数据"""
        synonyms_file = os.path.join(self.knowledge_base_path, "skill_synonyms.json")
        try:
            with open(synonyms_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("synonyms", {})
        except FileNotFoundError:
            print(f"Warning: Skill synonyms file not found at {synonyms_file}")
            return {}

    def _init_jieba(self):
        """初始化jieba分词器"""
        # 添加技能词到自定义词典
        skill_names = self._get_all_skill_names()
        for skill in skill_names:
            jieba.add_word(skill, freq=1000, tag='n')

        # 添加其他常见求职相关词汇
        job_terms = [
            '实习', '校招', '社招', '全职', '兼职', '远程', '应届生',
            '前端开发', '后端开发', '数据分析', '产品经理', 'UI设计',
            '机器学习', '深度学习', '人工智能', '测试开发', '运维开发',
            'Java开发', 'Python开发', 'Go开发', '移动开发'
        ]
        for term in job_terms:
            jieba.add_word(term, freq=800, tag='n')

    def _get_all_skill_names(self) -> List[str]:
        """获取所有技能名称"""
        if self._skill_names is not None:
            return self._skill_names

        skill_names = set()

        # 从skills.json中提取
        for category_key, category_data in self.skills_data.get("categories", {}).items():
            for skill_item in category_data.get("skills", []):
                skill_name = skill_item.get("name")
                if skill_name:
                    skill_names.add(skill_name)

        # 从同义词中提取
        for skill, synonyms in self.skill_synonyms.items():
            skill_names.add(skill)
            skill_names.update(synonyms)

        # 从关系数据中提取
        for skill in self.skill_relations.keys():
            skill_names.add(skill)

        self._skill_names = list(skill_names)
        return self._skill_names

    def parse(self, raw_input: str) -> Dict[str, Any]:
        """
        解析用户输入

        Args:
            raw_input: 用户原始输入文本

        Returns:
            解析结果，包含keywords和confidence
        """
        # 1. 文本清洗
        cleaned_text = self._clean_text(raw_input)

        # 2. 分词
        words, pos_tags = self._tokenize(cleaned_text)

        # 3. 实体识别
        entities = self._recognize_entities(words, pos_tags)

        # 4. 关键词扩展
        expanded_keywords = self._expand_keywords(entities)

        # 5. 缺失值填充
        filled_keywords = self._fill_missing_values(expanded_keywords, raw_input)

        # 计算置信度
        confidence = self._calculate_confidence(filled_keywords)

        return {
            "keywords": filled_keywords,
            "confidence": confidence
        }

    def _clean_text(self, text: str) -> str:
        """
        文本清洗

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        # 去除多余空白字符
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # 去除常见语气词和停用词
        modal_words = [
            '啊', '呀', '呢', '吧', '嘛', '啦', '哇', '哦', '哟',
            '的', '了', '在', '是', '我', '有', '和', '就', '都',
            '想', '要', '可以', '能够', '可能', '也许', '大概'
        ]

        # 创建正则表达式匹配这些词（作为独立单词）
        pattern = r'\b(' + '|'.join(modal_words) + r')\b'
        text = re.sub(pattern, '', text)

        # 去除标点符号（保留中英文括号用于可能的技能说明）
        text = re.sub(r'[，。！？；："「」『』【】《》]', ' ', text)

        # 再次去除多余空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def _tokenize(self, text: str) -> Tuple[List[str], List[str]]:
        """
        分词和词性标注

        Args:
            text: 清洗后的文本

        Returns:
            (words, pos_tags) 单词列表和词性列表
        """
        if not text:
            return [], []

        # 使用jieba进行分词和词性标注
        words = []
        pos_tags = []

        # 使用pseg进行词性标注
        for word, pos in pseg.cut(text):
            words.append(word)
            pos_tags.append(pos)

        return words, pos_tags

    def _recognize_entities(self, words: List[str], pos_tags: List[str]) -> Dict[str, List[str]]:
        """
        实体识别

        Args:
            words: 单词列表
            pos_tags: 词性列表

        Returns:
            识别的实体字典，键为实体类型，值为实体列表
        """
        entities = {
            "skills": [],      # 技能
            "job_types": [],   # 岗位类型
            "locations": [],   # 地点
            "experiences": [], # 经验要求
            "educations": [],  # 学历要求
        }

        # 技能识别
        all_skills = self._get_all_skill_names()
        skill_synonyms_reverse = self._build_synonym_reverse_map()

        for i, word in enumerate(words):
            # 检查是否为技能
            if word in all_skills:
                entities["skills"].append(word)
            elif word in skill_synonyms_reverse:
                # 如果是同义词，映射到标准技能名
                entities["skills"].append(skill_synonyms_reverse[word])

            # 岗位类型识别（基于关键词）
            job_type_keywords = {
                "实习": ["实习", "实习生", "实习岗位"],
                "校招": ["校招", "校园招聘", "应届生", "毕业生"],
                "社招": ["社招", "社会招聘", "全职"],
                "兼职": ["兼职", "part-time"],
                "远程": ["远程", "线上", "居家", "work from home"]
            }

            for job_type, keywords in job_type_keywords.items():
                if word in keywords and job_type not in entities["job_types"]:
                    entities["job_types"].append(job_type)

            # 地点识别（简单的城市名识别）
            # 这里可以扩展为从city_codes.py加载城市数据
            if pos_tags[i] in ['ns', 'LOC']:  # 地名词性
                entities["locations"].append(word)

            # 经验要求识别
            experience_patterns = [
                (r'\d+年', "years"),  # X年经验
                (r'经验', "experience"),  # 提到"经验"
                (r'新手|无经验|小白', "no experience"),
                (r'资深|高级|专家', "senior"),
                (r'初级|入门|junior', "junior"),
            ]

            for pattern, exp_type in experience_patterns:
                if re.search(pattern, word):
                    if exp_type not in entities["experiences"]:
                        entities["experiences"].append(exp_type)

            # 学历要求识别
            education_keywords = {
                "本科": ["本科", "学士", "bachelor"],
                "硕士": ["硕士", "研究生", "master"],
                "博士": ["博士", "phd", "博士生"],
                "大专": ["大专", "专科", "高职"],
                "不限": ["不限", "无要求", "学历不限"]
            }

            for edu_level, keywords in education_keywords.items():
                if word in keywords and edu_level not in entities["educations"]:
                    entities["educations"].append(edu_level)

        return entities

    def _build_synonym_reverse_map(self) -> Dict[str, str]:
        """构建同义词反向映射（同义词 -> 标准技能名）"""
        reverse_map = {}
        for skill, synonyms in self.skill_synonyms.items():
            for synonym in synonyms:
                reverse_map[synonym] = skill
        return reverse_map

    def _expand_keywords(self, entities: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        关键词扩展

        Args:
            entities: 识别的实体

        Returns:
            扩展后的关键词
        """
        expanded = {
            "skills": entities["skills"].copy(),
            "job_types": entities["job_types"].copy(),
            "locations": entities["locations"].copy(),
            "experiences": entities["experiences"].copy(),
            "educations": entities["educations"].copy(),
            "related_skills": []  # 相关技能
        }

        # 基于技能关系扩展相关技能
        for skill in entities["skills"]:
            if skill in self.skill_relations:
                # 添加强相关技能
                strong_related = self.skill_relations[skill].get("strong", [])
                for related in strong_related:
                    if related not in expanded["skills"] and related not in expanded["related_skills"]:
                        expanded["related_skills"].append(related)

        return expanded

    def _fill_missing_values(self, keywords: Dict[str, List[str]], original_text: str) -> Dict[str, List[str]]:
        """
        缺失值填充

        Args:
            keywords: 扩展后的关键词
            original_text: 原始文本（用于上下文分析）

        Returns:
            填充缺失值后的关键词
        """
        filled = keywords.copy()

        # 如果岗位类型为空，默认为"实习"
        if not filled["job_types"]:
            filled["job_types"] = ["实习"]

        # 如果地点为空，根据文本上下文判断
        if not filled["locations"]:
            # 简单判断：如果文本中包含特定城市名关键词
            city_keywords = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京"]
            for city in city_keywords:
                if city in original_text:
                    filled["locations"].append(city)
                    break

        # 如果经验要求为空，根据岗位类型设置默认值
        if not filled["experiences"]:
            # 实习岗位通常无经验要求
            if "实习" in filled["job_types"]:
                filled["experiences"] = ["no experience"]
            else:
                filled["experiences"] = ["experience"]  # 默认有经验要求

        # 如果学历要求为空，设置默认值
        if not filled["educations"]:
            # 实习岗位通常要求本科或以上
            if "实习" in filled["job_types"]:
                filled["educations"] = ["本科"]
            else:
                filled["educations"] = ["不限"]

        return filled

    def _calculate_confidence(self, keywords: Dict[str, List[str]]) -> float:
        """
        计算解析置信度

        Args:
            keywords: 最终的关键词

        Returns:
            置信度得分 (0-1)
        """
        # 基础置信度
        confidence = 0.5

        # 如果有识别到技能，增加置信度
        if keywords["skills"]:
            confidence += 0.2

        # 如果有识别到岗位类型，增加置信度
        if keywords["job_types"]:
            confidence += 0.15

        # 如果有识别到地点，增加置信度
        if keywords["locations"]:
            confidence += 0.1

        # 如果识别到了经验和学历，增加置信度
        if keywords["experiences"]:
            confidence += 0.05

        if keywords["educations"]:
            confidence += 0.05

        # 限制在0-1范围内
        confidence = max(0.0, min(1.0, confidence))

        return round(confidence, 2)


# 工具函数：创建解析器实例
def create_intent_parser() -> IntentParser:
    """创建意向解析器实例"""
    return IntentParser()


# 测试函数
if __name__ == "__main__":
    # 测试代码
    parser = IntentParser()

    test_cases = [
        "我想找一份Python开发的实习工作，最好在北京",
        "有没有数据分析的岗位？需要SQL和Python技能",
        "Java后端开发，有Spring Boot经验",
        "前端开发，会Vue.js和React",
        "机器学习实习，懂Python和TensorFlow"
    ]

    for test_input in test_cases:
        print(f"输入: {test_input}")
        result = parser.parse(test_input)
        print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print("-" * 50)