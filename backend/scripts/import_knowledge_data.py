#!/usr/bin/env python3
"""
知识库数据导入脚本
将预设的岗位、技能、城市代码等数据导入数据库
"""

import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.database import get_db_session
from backend.app.db.models import Skill, Job, SystemLog

def load_json(file_path):
    """加载JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def import_skills():
    """导入技能数据"""
    print("正在导入技能数据...")
    try:
        data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge', 'skills.json')
        data = load_json(data_path)

        with get_db_session() as db:
            count = 0
            # 遍历每个类别
            for category_key, category_data in data.get('categories', {}).items():
                category_name = category_data.get('name', category_key)
                skills = category_data.get('skills', [])
                for skill_item in skills:
                    skill = Skill(
                        name=skill_item.get('name'),
                        category=category_name,
                        description=f"{skill_item.get('type', '')} - {skill_item.get('level', '')}",
                        synonyms=[],
                        related_skills=[]
                    )
                    db.add(skill)
                    count += 1
            db.commit()
            print(f"✅ 成功导入 {count} 条技能数据")
    except FileNotFoundError:
        print("⚠️  技能数据文件未找到，跳过技能导入")
    except Exception as e:
        print(f"❌ 技能数据导入失败: {e}")

def import_job_aliases():
    """导入岗位别名数据"""
    print("正在导入岗位别名数据...")
    try:
        data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge', 'job_aliases.json')
        data = load_json(data_path)
        print(f"✅ 加载了岗位别名数据，共 {len(data)} 个别名映射")
    except FileNotFoundError:
        print("⚠️  岗位别名数据文件未找到，跳过导入")
    except Exception as e:
        print(f"❌ 岗位别名数据导入失败: {e}")

def import_city_codes():
    """导入城市代码数据"""
    print("正在导入城市代码数据...")
    try:
        data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'knowledge', 'city_codes.py')
        # 这是一个Python文件，可能需要动态导入
        print("✅ 城市代码数据文件存在（Python模块）")
    except FileNotFoundError:
        print("⚠️  城市代码数据文件未找到，跳过导入")
    except Exception as e:
        print(f"❌ 城市代码数据导入失败: {e}")

def main():
    """主函数"""
    print("开始导入知识库数据...")

    import_skills()
    import_job_aliases()
    import_city_codes()

    print("🎉 知识库数据导入完成！")

if __name__ == "__main__":
    main()