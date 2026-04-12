"""
数据清洗规则模块 - 标准化和清洗爬虫获取的数据
"""

import re
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# 学历标准化映射
EDUCATION_MAPPING = {
    # 不限
    "不限": "不限",
    "学历不限": "不限",
    "": "不限",
    # 高中
    "高中": "高中",
    "中专": "高中",
    "中技": "高中",
    "职高": "高中",
    # 大专
    "大专": "大专",
    "专科": "大专",
    "大学专科": "大专",
    # 本科
    "本科": "本科",
    "大学本科": "本科",
    "统招本科": "本科",
    "全日制本科": "本科",
    # 硕士
    "硕士": "硕士",
    "硕士研究生": "硕士",
    "研究生": "硕士",
    # 博士
    "博士": "博士",
    "博士研究生": "博士",
}

# 经验标准化映射
EXPERIENCE_MAPPING = {
    "不限": "不限",
    "经验不限": "不限",
    "无经验": "不限",
    "应届生": "应届生",
    "应届毕业生": "应届生",
    "在校生": "应届生",
    "1年以内": "1年以内",
    "1年": "1年以内",
    "经验1年以下": "1年以内",
    "1-3年": "1-3年",
    "经验1-3年": "1-3年",
    "3-5年": "3-5年",
    "经验3-5年": "3-5年",
    "3年以上": "3-5年",
    "5-10年": "5-10年",
    "经验5-10年": "5-10年",
    "5年以上": "5-10年",
    "10年以上": "10年以上",
    "经验10年以上": "10年以上",
}


def clean_salary(salary_text: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    清洗薪资字段

    Args:
        salary_text: 原始薪资文本，如 "15k-25k·14薪"

    Returns:
        (最低薪资, 最高薪资, 薪资月数) 单位：元/月
    """
    if not salary_text or salary_text in ["面议", "", "薪资面议"]:
        return None, None, None

    try:
        text = salary_text.strip().lower()

        # 提取薪资月数
        months = None
        months_match = re.search(r'(\d+)[薪|个月]', text)
        if months_match:
            months = int(months_match.group(1))
            text = re.sub(r'\d+[薪|个月]', '', text)

        # 提取数值范围
        # 匹配模式: 15k-25k, 15-25k, 15k-25, 15000-25000 等
        numbers = re.findall(r'(\d+(?:\.\d+)?)', text)

        if not numbers:
            return None, None, months

        # 判断是否以千为单位
        is_k = 'k' in text or '千' in text
        is_wan = '万' in text

        if len(numbers) >= 2:
            min_val = float(numbers[0])
            max_val = float(numbers[1])
        else:
            min_val = max_val = float(numbers[0])

        # 统一转换为元/月
        if is_wan:
            min_val *= 10000
            max_val *= 10000
        elif is_k or (min_val < 100 and max_val < 100):
            # 数值小于100，推测为k
            min_val *= 1000
            max_val *= 1000

        return int(min_val), int(max_val), months

    except Exception as e:
        logger.warning(f"Failed to parse salary '{salary_text}': {e}")
        return None, None, None


def clean_location(location: str) -> str:
    """
    清洗城市字段

    Args:
        location: 原始地点文本，如 "北京市海淀区"

    Returns:
        清洗后的城市名
    """
    if not location:
        return ""

    # 去除空白字符
    location = location.strip()

    # 处理别名映射
    city_mapping = {
        "魔都": "上海",
        "帝都": "北京",
        "羊城": "广州",
        "鹏城": "深圳",
        "杭城": "杭州",
        "蓉城": "成都",
        "江城": "武汉",
    }
    if location in city_mapping:
        return city_mapping[location]

    # 处理"XX·XX区"格式（BOSS直聘）
    if '·' in location:
        parts = location.split('·')
        location = parts[0]

    # 处理"XX-XX区"格式
    if '-' in location:
        parts = location.split('-')
        location = parts[0]

    # 找到第一个"市"的位置，取之前的部分
    if '市' in location:
        idx = location.find('市')
        location = location[:idx]
    # 去除省后缀
    elif location.endswith('省'):
        location = location[:-1]
    # 去除自治区、特别行政区后缀
    elif location.endswith('自治区'):
        location = location[:-3]
    elif location.endswith('特别行政区'):
        location = location[:-5]

    # 去除区县后缀
    district_suffixes = [
        "区", "县", "镇", "街道", "新区", "开发区", "高新区",
        "海淀区", "朝阳区", "浦东", "滨海"
    ]
    for suffix in district_suffixes:
        if location.endswith(suffix):
            # 特殊保留
            if suffix in ["浦东", "滨海"]:
                continue
            location = location[:-len(suffix) if len(suffix) > 1 else 1]
            break

    return location.strip()


def clean_education(edu_text: str) -> str:
    """
    清洗学历字段

    Args:
        edu_text: 原始学历文本

    Returns:
        标准化学历
    """
    if not edu_text:
        return "不限"

    edu_text = edu_text.strip()

    # 直接匹配
    if edu_text in EDUCATION_MAPPING:
        return EDUCATION_MAPPING[edu_text]

    # 关键词匹配
    if "博士" in edu_text:
        return "博士"
    if "硕士" in edu_text or "研究生" in edu_text:
        return "硕士"
    if "本科" in edu_text:
        return "本科"
    if "大专" in edu_text or "专科" in edu_text:
        return "大专"
    if "高中" in edu_text or "中专" in edu_text:
        return "高中"

    return "不限"


def clean_experience(exp_text: str) -> str:
    """
    清洗经验字段

    Args:
        exp_text: 原始经验文本

    Returns:
        标准化经验
    """
    if not exp_text:
        return "不限"

    exp_text = exp_text.strip()

    # 直接匹配
    if exp_text in EXPERIENCE_MAPPING:
        return EXPERIENCE_MAPPING[exp_text]

    # 提取数字范围
    numbers = re.findall(r'(\d+)', exp_text)
    if numbers:
        min_exp = int(numbers[0])

        if min_exp == 0:
            return "应届生"
        elif min_exp == 1:
            if len(numbers) > 1 and int(numbers[1]) >= 3:
                return "1-3年"
            return "1年以内"
        elif 3 <= min_exp < 5:
            return "3-5年"
        elif 5 <= min_exp < 10:
            return "5-10年"
        elif min_exp >= 10:
            return "10年以上"

    # 关键词匹配
    if "应届" in exp_text or "在校" in exp_text:
        return "应届生"
    if "1年以内" in exp_text or "1年内" in exp_text:
        return "1年以内"

    return "不限"


def clean_company_size(size_text: str) -> str:
    """
    清洗公司规模字段

    Args:
        size_text: 原始规模文本，如 "100-499人"

    Returns:
        标准化规模
    """
    if not size_text:
        return ""

    size_text = size_text.strip()

    # 提取数字
    numbers = re.findall(r'(\d+)', size_text)

    if not numbers:
        # 匹配特殊情况
        if "少于" in size_text or "以下" in size_text:
            return "少于15人"
        if "以上" in size_text:
            return "2000人以上"
        return size_text

    # 取最大值作为分类依据
    max_size = max(int(num) for num in numbers)

    if max_size < 15:
        return "少于15人"
    elif max_size < 50:
        return "15-50人"
    elif max_size < 150:
        return "50-150人"
    elif max_size < 500:
        return "150-500人"
    elif max_size < 2000:
        return "500-2000人"
    else:
        return "2000人以上"


def clean_job_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    清洗完整的岗位数据

    Args:
        data: 原始岗位数据字典

    Returns:
        清洗后的数据字典
    """
    cleaned = dict(data)

    # 清洗薪资
    if "salary" in cleaned or "salary_text" in cleaned:
        salary_text = cleaned.get("salary") or cleaned.get("salary_text", "")
        min_sal, max_sal, months = clean_salary(salary_text)
        cleaned["salary_min"] = min_sal
        cleaned["salary_max"] = max_sal
        cleaned["salary_months"] = months

    # 清洗地点
    if "location" in cleaned:
        cleaned["location"] = clean_location(cleaned["location"])

    # 清洗学历
    if "education" in cleaned:
        cleaned["education"] = clean_education(cleaned["education"])

    # 清洗经验
    if "experience" in cleaned:
        cleaned["experience"] = clean_experience(cleaned["experience"])

    # 清洗公司规模
    if "company_size" in cleaned:
        cleaned["company_size"] = clean_company_size(cleaned["company_size"])

    # 清洗技能标签（去重、去空）
    if "skills" in cleaned and isinstance(cleaned["skills"], list):
        cleaned["skills"] = list(set(
            s.strip() for s in cleaned["skills"] if s and s.strip()
        ))

    # 清洗描述（去除多余空白）
    if "description" in cleaned and isinstance(cleaned["description"], str):
        cleaned["description"] = re.sub(r'\s+', ' ', cleaned["description"]).strip()

    return cleaned
