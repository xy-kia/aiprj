"""
数据验证器 - 验证爬虫数据的完整性和格式
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """验证错误"""
    pass


class JobValidator:
    """岗位数据验证器"""

    # 必填字段
    REQUIRED_FIELDS = [
        "id", "title", "company", "location", "job_type",
        "posted_date", "source", "url"
    ]

    # 有效的岗位类型
    VALID_JOB_TYPES = ["全职", "兼职", "实习", "校招"]

    # 有效的学历
    VALID_EDUCATION = ["不限", "高中", "大专", "本科", "硕士", "博士"]

    # 有效的经验
    VALID_EXPERIENCE = [
        "不限", "应届生", "1年以内", "1-3年",
        "3-5年", "5-10年", "10年以上"
    ]

    # 有效的数据来源
    VALID_SOURCES = ["boss", "zhaopin", "51job", "liepin", "other"]

    def __init__(self):
        self.errors: List[str] = []

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        执行完整验证

        Args:
            data: 待验证数据

        Returns:
            是否通过验证
        """
        self.errors = []

        self._validate_required(data)
        self._validate_types(data)
        self._validate_values(data)
        self._validate_format(data)

        return len(self.errors) == 0

    def _validate_required(self, data: Dict[str, Any]):
        """验证必填字段"""
        for field in self.REQUIRED_FIELDS:
            if field not in data or data[field] is None or data[field] == "":
                self.errors.append(f"缺少必填字段: {field}")

    def _validate_types(self, data: Dict[str, Any]):
        """验证字段类型"""
        type_checks = {
            "id": str,
            "title": str,
            "company": str,
            "location": str,
            "job_type": str,
            "salary_min": (int, float, type(None)),
            "salary_max": (int, float, type(None)),
            "education": str,
            "experience": str,
            "description": str,
            "requirements": list,
            "skills": list,
            "posted_date": str,
            "source": str,
            "url": str,
        }

        for field, expected_type in type_checks.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], expected_type):
                    self.errors.append(
                        f"字段 {field} 类型错误，期望 {expected_type}，"
                        f"实际 {type(data[field])}"
                    )

    def _validate_values(self, data: Dict[str, Any]):
        """验证字段值"""
        # 验证岗位类型
        if "job_type" in data and data["job_type"] not in self.VALID_JOB_TYPES:
            self.errors.append(
                f"无效的岗位类型: {data['job_type']}，"
                f"应为 {self.VALID_JOB_TYPES}"
            )

        # 验证学历
        if "education" in data and data["education"] not in self.VALID_EDUCATION:
            self.errors.append(
                f"无效的学历: {data['education']}，"
                f"应为 {self.VALID_EDUCATION}"
            )

        # 验证经验
        if "experience" in data and data["experience"] not in self.VALID_EXPERIENCE:
            self.errors.append(
                f"无效的经验: {data['experience']}，"
                f"应为 {self.VALID_EXPERIENCE}"
            )

        # 验证数据来源
        if "source" in data and data["source"] not in self.VALID_SOURCES:
            self.errors.append(
                f"无效的数据来源: {data['source']}，"
                f"应为 {self.VALID_SOURCES}"
            )

        # 验证薪资范围
        if "salary_min" in data and "salary_max" in data:
            min_sal = data.get("salary_min")
            max_sal = data.get("salary_max")

            if min_sal is not None and max_sal is not None:
                if min_sal < 0 or max_sal < 0:
                    self.errors.append("薪资不能为负数")
                if min_sal > max_sal:
                    self.errors.append("最低薪资不能大于最高薪资")

        # 验证薪资合理性
        if "salary_max" in data and data["salary_max"]:
            if data["salary_max"] > 1000000:  # 100万/月
                self.errors.append("最高薪资超过合理范围")

    def _validate_format(self, data: Dict[str, Any]):
        """验证格式"""
        # 验证URL格式
        if "url" in data and data["url"]:
            url_pattern = re.compile(
                r'^https?://'
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
                r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                r'localhost|'
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
                r'(?::\d+)?'
                r'(?:/?|[/?]\S+)$', re.IGNORECASE
            )
            if not url_pattern.match(data["url"]):
                self.errors.append(f"URL格式错误: {data['url']}")

        # 验证日期格式
        if "posted_date" in data and data["posted_date"]:
            try:
                datetime.strptime(data["posted_date"], "%Y-%m-%d")
            except ValueError:
                try:
                    datetime.strptime(data["posted_date"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    self.errors.append(
                        f"日期格式错误: {data['posted_date']}，"
                        f"期望格式: YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS"
                    )

        # 验证ID格式
        if "id" in data and data["id"]:
            if len(str(data["id"])) < 5:
                self.errors.append(f"ID长度不足: {data['id']}")

    def get_errors(self) -> List[str]:
        """获取所有错误信息"""
        return self.errors.copy()


def validate_job_data(data: Dict[str, Any]) -> bool:
    """
    便捷函数：验证岗位数据

    Args:
        data: 岗位数据

    Returns:
        是否通过验证
    """
    validator = JobValidator()
    return validator.validate(data)


def validate_batch(data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    批量验证

    Args:
        data_list: 数据列表

    Returns:
        验证结果统计
    """
    validator = JobValidator()
    results = {
        "total": len(data_list),
        "valid": 0,
        "invalid": 0,
        "errors": []
    }

    for i, data in enumerate(data_list):
        if validator.validate(data):
            results["valid"] += 1
        else:
            results["invalid"] += 1
            results["errors"].append({
                "index": i,
                "data": data.get("id", "unknown"),
                "errors": validator.get_errors()
            })

    return results


class SchemaValidator:
    """
    JSON Schema验证器
    基于job_schema.json进行验证
    """

    def __init__(self, schema_path: Optional[str] = None):
        self.schema = None
        if schema_path:
            self.load_schema(schema_path)

    def load_schema(self, path: str):
        """加载Schema文件"""
        import json
        with open(path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        使用JSON Schema验证

        Args:
            data: 待验证数据

        Returns:
            是否通过验证
        """
        if not self.schema:
            raise ValidationError("Schema未加载")

        try:
            from jsonschema import validate, ValidationError as JSONSchemaError
            validate(instance=data, schema=self.schema)
            return True
        except JSONSchemaError as e:
            logger.error(f"Schema验证失败: {e}")
            return False
        except ImportError:
            logger.warning("jsonschema库未安装，使用基础验证")
            return validate_job_data(data)
