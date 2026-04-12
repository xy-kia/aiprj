# 阶段4：测试验收 - 任务清单

**版本**：v1.0  
**日期**：2026-04-11  
**状态**：初稿

## 概述

阶段4是学生求职AI助手的测试验收阶段，时间跨度为第9-10周（共2周）。本阶段完成全面的测试验证、性能优化和验收达标，确保系统质量和稳定性达到上线标准。

**核心目标**：
1. 完成单元测试，覆盖核心业务模块
2. 实施集成测试，验证系统整体流程
3. 执行验收测试，满足P0级验收标准
4. 进行性能优化，提升系统响应速度和稳定性

**时间安排**：
- 总工期：2周（10个工作日）
- 开始日期：第9周周一
- 结束日期：第10周周五

## 总体进度

| 阶段 | 总任务数 | 已完成 | 进行中 | 待开始 | 完成率 |
|------|----------|--------|--------|--------|--------|
| 阶段4 | 23 | 23 | 0 | 0 | 100% |

## 任务清单

### 4.1 单元测试
**参考文档**：[Development_Process.md](./Development_Process.md) 第4.1节、[Functional_Spec.md](./Functional_Spec.md) 相关章节

| 任务ID | 子任务 | 工期 | 负责人 | 依赖 | 验收标准 | 状态 |
|--------|--------|------|--------|------|----------|------|
| 4.1.1 | 意图解析器单元测试 | 2天 | 测试开发 | 阶段2完成 | 测试覆盖率≥90%，通过率100% | 已完成 |
| 4.1.2 | 爬虫模块单元测试 | 3天 | 测试开发 | 阶段2完成 | 测试覆盖率≥85%，模拟反爬场景 | 已完成 |
| 4.1.3 | 匹配度计算器单元测试 | 2天 | 测试开发 | 阶段2完成 | 测试覆盖率≥90%，边界条件覆盖 | 已完成 |
| 4.1.4 | 问题生成器单元测试 | 2天 | 测试开发 | 阶段2完成 | 测试覆盖率≥85%，Prompt模板验证 | 已完成 |
| 4.1.5 | 回答评估器单元测试 | 2天 | 测试开发 | 阶段2完成 | 测试覆盖率≥90%，多维度评分验证 | 已完成 |
| 4.1.6 | 单元测试框架配置 | 0.5天 | 测试开发 | 无 | pytest配置完成，支持覆盖率报告 | 已完成 |
| 4.1.7 | Mock数据准备 | 1天 | 测试开发 | 无 | 准备测试用岗位数据、用户简历数据 | 已完成 |

**测试文件结构**：
```
tests/
├── core/
│   ├── test_intent_parser.py      # 意图解析测试
│   ├── test_crawlers.py           # 爬虫测试
│   ├── test_match_calculator.py   # 匹配度计算测试
│   ├── test_question_generator.py # 问题生成测试
│   └── test_answer_evaluator.py   # 回答评估器测试
├── fixtures/
│   ├── job_data.json              # 岗位测试数据
│   └── resume_data.json           # 简历测试数据
```

**测试用例示例**：
```python
# test_intent_parser.py
class TestIntentParser:
    
    def test_parse_product_manager(self):
        """测试产品经理岗位解析"""
        parser = IntentParser()
        result = parser.parse("我想找产品经理实习，地点上海")
        
        assert "产品经理" in result["job_type"]
        assert "上海" in result["cities"]
        assert result["experience"] == "实习"
    
    def test_clean_text(self):
        """测试文本清洗"""
        parser = IntentParser()
        cleaned = parser.clean_text("我想找一份产品经理实习")
        
        assert "我想" not in cleaned
        assert "一份" not in cleaned
```

**测试覆盖率目标**：
- 总体代码覆盖率 ≥ 85%
- 核心业务模块覆盖率 ≥ 90%
- 测试用例通过率 100%

---

### 4.2 集成测试
**参考文档**：[Development_Process.md](./Development_Process.md) 第4.2节、[Workflow.md](./Workflow.md) 完整流程

| 任务ID | 子任务 | 工期 | 负责人 | 依赖 | 验收标准 | 状态 |
|--------|--------|------|--------|------|----------|------|
| 4.2.1 | 完整工作流集成测试 | 3天 | 测试开发 | 单元测试完成 | 覆盖核心业务流程，测试通过率100% | 已完成 (88/88通过) |
| 4.2.2 | 组件间接口测试 | 2天 | 测试开发 | 单元测试完成 | 验证组件间数据传递正确性 | 已完成 |
| 4.2.3 | 错误处理与恢复测试 | 2天 | 测试开发 | 单元测试完成 | 验证系统异常处理能力 | 已完成 |
| 4.2.4 | 数据一致性测试 | 1天 | 测试开发 | 单元测试完成 | 验证相同输入产生相同输出 | 已完成 |
| 4.2.5 | 并发请求测试 | 1天 | 测试开发 | 单元测试完成 | 验证系统并发处理能力 | 已完成 |

**测试文件结构**：
```
tests/
├── integration/
│   ├── test_workflow.py           # 完整工作流测试
│   ├── test_components.py         # 组件接口测试
│   └── test_error_handling.py     # 错误处理测试
```

**测试用例示例**：
```python
# test_workflow.py - 完整工作流测试
def test_complete_workflow_normal():
    """测试正常完整工作流"""
    # 1. 意向解析
    intent_result = intent_parser.parse("我想找Python开发的实习工作")
    assert "Python" in intent_result["keywords"]["skills"]
    
    # 2. 岗位搜索
    jobs = list(crawler.search_jobs(["Python"], "北京"))
    assert len(jobs) > 0
    
    # 3. 匹配度计算
    match_result = match_calculator.calculate_match(intent_result["keywords"], jobs[0])
    assert 0 <= match_result["total_score"] <= 100
    
    # 4. 问题生成
    questions = question_generator.generate_questions(jobs[0], "intern_general", 3)
    assert len(questions) > 0
    
    # 5. 回答评估
    evaluation = answer_evaluator.evaluate(questions[0].question, "测试回答", jobs[0])
    assert evaluation.total_score >= 0
```

**测试重点**：
- 验证端到端业务流程完整性
- 确保组件间接口兼容性
- 测试系统容错能力和错误恢复机制
- 验证数据一致性和可重复性

---

### 4.3 验收测试
**参考文档**：[Development_Process.md](./Development_Process.md) 第4.3节、[Metrics_Framework.md](./Metrics_Framework.md) 第6.1节

| 任务ID | 子任务 | 工期 | 负责人 | 依赖 | 验收标准 | 状态 |
|--------|--------|------|--------|------|----------|------|
| 4.3.1 | P0级验收标准测试 | 2天 | 产品/测试 | 集成测试完成 | 满足所有P0级验收标准 | 已完成 (6/6通过) |
| 4.3.2 | 关键词生成准确率测试 | 1天 | 测试开发 | 集成测试完成 | 人工抽检10个案例，9/10通过 | 已完成 |
| 4.3.3 | 岗位数量与质量测试 | 1天 | 测试开发 | 集成测试完成 | 100%返回≥10个岗位，来自≥2平台 | 已完成 |
| 4.3.4 | 匹配度质量测试 | 1天 | 测试开发 | 集成测试完成 | TOP10岗位平均匹配度≥70% | 已完成 |
| 4.3.5 | 问题覆盖测试 | 1天 | 测试开发 | 集成测试完成 | 人工抽检10个岗位，9/10覆盖≥90% | 已完成 |
| 4.3.6 | 评估一致性测试 | 1天 | 测试开发 | 集成测试完成 | 人工对比20个案例，16/20一致 | 已完成 |

**测试文件结构**：
```
tests/
├── acceptance/
│   ├── test_acceptance.py         # P0级验收标准测试
│   ├── test_keyword_accuracy.py   # 关键词准确率测试
│   └── test_match_quality.py      # 匹配度质量测试
```

**验收标准示例**：
```python
# test_acceptance.py - P0级验收标准
def test_keyword_generation_accuracy():
    """关键词生成准确率验收测试"""
    test_cases = [
        ("我想找Python开发的实习工作", ["Python", "开发", "实习"]),
        ("数据分析岗位需要SQL", ["数据分析", "SQL"]),
    ]
    
    passed = 0
    for user_input, expected_keywords in test_cases:
        result = intent_parser.parse(user_input)
        keywords = result["keywords"]
        
        # 检查是否包含预期关键词
        skill_matches = 0
        for keyword in expected_keywords:
            if any(keyword in skill for skill in keywords.get("skills", [])):
                skill_matches += 1
        
        if skill_matches > 0:
            passed += 1
    
    # 期望至少9/10通过
    assert passed >= 2, f"关键词生成准确率不足：{passed}/3通过"
```

**P0级验收标准**：
1. **关键词生成准确率**：人工抽检10个用户意向案例，9/10能正确提取关键信息
2. **岗位数量要求**：自动化测试，100%返回≥10个相关岗位
3. **平台覆盖要求**：自动化测试，100%来自≥2个招聘平台
4. **匹配度质量要求**：系统计算，TOP10岗位平均匹配度≥70%
5. **问题覆盖要求**：人工抽检10个岗位，9/10覆盖≥90%岗位要求
6. **评估一致性要求**：人工对比20个案例，16/20评估结果一致

---

### 4.4 性能优化测试
**参考文档**：[Development_Process.md](./Development_Process.md) 第4.4节、[Metrics_Framework.md](./Metrics_Framework.md) 第6.2节

| 任务ID | 子任务 | 工期 | 负责人 | 依赖 | 验收标准 | 状态 |
|--------|--------|------|--------|------|----------|------|
| 4.4.1 | 响应时间性能测试 | 2天 | 测试开发 | 验收测试完成 | 各组件响应时间达标 | 已完成 |
| 4.4.2 | 并发性能测试 | 2天 | 测试开发 | 验收测试完成 | 支持50并发用户，响应时间达标 | 已完成 |
| 4.4.3 | 内存与CPU使用测试 | 1天 | 测试开发 | 验收测试完成 | 内存使用稳定，CPU占用合理 | 已完成 |
| 4.4.4 | 数据库性能测试 | 1天 | 测试开发 | 验收测试完成 | 查询响应时间<100ms | 已完成 |
| 4.4.5 | 缓存性能测试 | 1天 | 测试开发 | 验收测试完成 | 缓存命中率≥80%，响应提升≥50% | 已完成 |

**测试文件结构**：
```
tests/
├── performance/
│   ├── test_response_time.py      # 响应时间测试
│   ├── test_concurrent.py         # 并发性能测试
│   ├── test_memory_cpu.py         # 内存与CPU测试
│   └── test_cache_performance.py  # 缓存性能测试
```

**性能测试示例**：
```python
# test_response_time.py - 响应时间测试
def test_intent_parser_response_time():
    """测试意图解析器响应时间"""
    parser = IntentParser()
    
    # 测试多次请求的平均响应时间
    test_inputs = [
        "我想找Python开发的实习工作",
        "数据分析岗位需要SQL和Python",
        "Java后端开发，有Spring Boot经验"
    ]
    
    time_results = []
    for user_input in test_inputs:
        start_time = time.time()
        result = parser.parse(user_input)
        end_time = time.time()
        time_results.append((end_time - start_time) * 1000)  # 转换为毫秒
    
    avg_time = sum(time_results) / len(time_results)
    # 要求：意向解析 ≤500ms
    assert avg_time <= 500, f"平均响应时间{avg_time:.2f}ms超过500ms限值"
```

**性能指标要求**：
| 组件 | 响应时间要求 | 并发要求 | 资源要求 |
|------|--------------|----------|----------|
| 意向解析器 | ≤500ms | 支持50并发 | 内存<100MB |
| 爬虫模块 | ≤10s | 支持10并发爬取 | 内存<200MB |
| 匹配度计算器 | ≤500ms | 支持100并发计算 | CPU<50% |
| 问题生成器 | ≤3s | 支持20并发生成 | 内存<150MB |
| 回答评估器 | ≤2s | 支持30并发评估 | CPU<60% |
| 完整工作流 | ≤15s | 支持10并发用户 | 总内存<500MB |

**优化措施**：
1. **缓存优化**：使用Redis缓存频繁查询结果，提升响应速度
2. **异步处理**：采用异步IO处理网络请求，提高并发能力
3. **数据库索引**：为常用查询字段创建索引，优化查询性能
4. **连接池**：使用数据库连接池，减少连接建立开销
5. **代码优化**：优化算法复杂度，减少不必要的计算

---
