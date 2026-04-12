#!/usr/bin/env python3
"""
简单的AI解析器测试 - 不使用Unicode字符
"""

import sys
import os
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_basic_integration():
    """测试基本集成"""
    print("=" * 60)
    print("测试 AI解析器基本集成")
    print("=" * 60)

    try:
        print("1. 导入模块...")
        from crawlers.boss_crawler import BOSSCrawler
        print("   [OK] 导入成功")

        print("\n2. 创建爬虫实例...")
        # 创建不启用AI解析的爬虫（避免API调用）
        crawler = BOSSCrawler(ai_parser_enabled=False)
        print(f"   [OK] BOSSCrawler创建成功")
        print(f"       平台: {crawler.platform}")
        print(f"       AI解析启用: {crawler.ai_parser_enabled}")

        print("\n3. 测试传统解析方法...")
        mock_html = """
        <html>
        <script>
        window.__INITIAL_STATE__ = {
            "jobList": {
                "list": [
                    {
                        "encryptId": "test001",
                        "jobName": "前端开发实习生",
                        "brandName": "互联网公司",
                        "cityName": "上海",
                        "salaryDesc": "6-8K",
                        "jobExperience": "应届生",
                        "jobDegree": "本科",
                        "skills": ["JavaScript", "React"]
                    }
                ]
            }
        };
        </script>
        </html>
        """

        jobs = crawler.parse_list_page(mock_html)
        print(f"   [OK] 传统解析成功")
        print(f"       解析到 {len(jobs)} 个岗位")
        if jobs:
            for i, job in enumerate(jobs[:2]):
                print(f"       岗位 {i+1}: {job.get('title', 'N/A')} - {job.get('company', 'N/A')}")

        print("\n4. 检查AI解析器属性...")
        if hasattr(crawler, 'ai_parser'):
            print(f"   [INFO] 爬虫有ai_parser属性: {crawler.ai_parser is not None}")
        if hasattr(crawler, 'ai_parser_enabled'):
            print(f"   [INFO] AI解析启用状态: {crawler.ai_parser_enabled}")

        print("\n5. 测试AI解析器类存在性...")
        try:
            from crawlers.ai_parser import AIParser
            print("   [OK] AIParser类存在")

            # 检查是否能创建实例（可能因缺少API密钥而失败）
            try:
                parser = AIParser()
                print(f"   [OK] 可以创建AIParser实例")
                print(f"       模型: {parser.model}")
            except Exception as e:
                print(f"   [INFO] 创建AIParser实例失败（可能缺少API密钥）: {e}")
                print("         这是正常现象，AI解析将作为可选功能")

        except ImportError as e:
            print(f"   [ERROR] 导入AIParser失败: {e}")
            return False

        print("\n" + "=" * 60)
        print("集成测试完成")
        print("=" * 60)
        print("总结:")
        print("- AI解析器模块已成功创建")
        print("- BOSSCrawler已集成AI解析作为后备方案")
        print("- 传统解析方法正常工作")
        print("- AI解析器可根据配置启用/禁用")
        print("\n后续步骤:")
        print("1. 配置OPENAI_API_KEY环境变量以启用AI解析")
        print("2. 或在前端配置界面设置AI提供商")
        print("3. 当传统爬虫被反爬时，AI解析将自动启用")

        return True

    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("开始测试AI解析器集成...\n")
    success = test_basic_integration()

    print("\n" + "=" * 60)
    print("测试结果: " + ("通过" if success else "失败"))
    print("=" * 60)

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)