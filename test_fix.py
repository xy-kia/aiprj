#!/usr/bin/env python3
"""
测试AI解析器修复逻辑
"""

import sys
import os
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from crawlers.ai_parser import AIParser

def test_parse_detail_page_fix():
    """测试详情页解析修复逻辑"""
    print("测试详情页解析修复逻辑")

    # 创建一个模拟AI解析器，不实际调用API
    class MockAIParser(AIParser):
        def __init__(self):
            # 跳过父类初始化，避免需要API密钥
            self.logger = logging.getLogger(__name__)
            self.api_key = "fake_key"
            self.base_url = "https://api.openai.com/v1"
            self.model = "gpt-3.5-turbo"
            self.max_tokens = 4000
            self.temperature = 0.1
            self.prompt_templates = {}

    parser = MockAIParser()

    # 模拟AI返回 '\n  "title"' 的情况
    test_cases = [
        ('\n  "title"', '带换行符和空格的字段名'),
        ('"title"', '仅字段名'),
        ('title', '无引号字段名'),
        ('"Python开发工程师"', '正常字符串值'),
        ('\n  "company"', '公司字段'),
        ('', '空响应'),
    ]

    for content, description in test_cases:
        print(f"\n测试用例: {description}")
        print(f"原始内容: {repr(content)}")

        # 模拟AI响应
        class MockChoice:
            class Message:
                content = content
            message = Message()

        class MockResponse:
            choices = [MockChoice()]

        # 调用修复逻辑（通过一个辅助方法）
        # 实际上，我们需要模拟parse_detail_page的内部逻辑
        # 这里我们直接测试修复逻辑的核心部分
        content_stripped = content.strip()
        print(f"去除空白后: {repr(content_stripped)}")

        # 情况1: 引号包围的内容
        if (content_stripped.startswith('"') and content_stripped.endswith('"')) or \
           (content_stripped.startswith("'") and content_stripped.endswith("'")):
            unquoted = content_stripped[1:-1]
            print(f"去除引号后: {repr(unquoted)}")
            if not unquoted:
                data = {}
                print(f"结果: 空对象")
            else:
                known_fields = ["title", "company", "location", "salary_text", "experience", "education",
                              "description", "requirements", "skills", "company_size", "id", "url"]
                if unquoted in known_fields:
                    data = {unquoted: ""}
                    print(f"结果: 字段名对象 {data}")
                else:
                    data = {"title": unquoted}
                    print(f"结果: 标题对象 {data}")
        # 情况3: 非JSON字符串
        elif content_stripped and not content_stripped.startswith('[') and not content_stripped.startswith('{') and not content_stripped.startswith('"') and not content_stripped.startswith("'"):
            known_fields = ["title", "company", "location", "salary_text", "experience", "education",
                          "description", "requirements", "skills", "company_size", "id", "url"]
            if content_stripped in known_fields:
                data = {content_stripped: ""}
                print(f"结果: 字段名对象 {data}")
            else:
                data = {"title": content_stripped}
                print(f"结果: 标题对象 {data}")
        else:
            print(f"结果: 未匹配任何情况")

    print("\n所有测试用例完成")

if __name__ == "__main__":
    test_parse_detail_page_fix()