# 性能与成本优化计划（OPS-004）

## 概述

本文档定义学生求职AI助手项目的性能优化和成本控制策略，通过持续监控、分析和优化，实现资源利用率≥70%和成本可控的目标。

## 优化目标与指标

### 性能优化目标
| 指标 | 当前值 | 目标值 | 优化优先级 | 负责人 |
|------|--------|--------|------------|--------|
| API响应时间P95 | 15s | ≤5s | P0 | 技术团队 |
| 系统可用性 | 99% | 99.9% | P0 | 运维团队 |
| 资源利用率 | 45% | ≥70% | P1 | 运维团队 |
| 缓存命中率 | 60% | ≥85% | P1 | 技术团队 |
| 数据库查询性能 | 慢查询10% | 慢查询≤2% | P1 | DBA |

### 成本控制目标
| 成本项 | 月度预算 | 当前花费 | 目标节省 | 优化策略 |
|--------|----------|----------|----------|----------|
| 云服务器 | ¥5,000 | ¥4,800 | 20% | 实例优化、预留实例 |
| 数据库服务 | ¥2,000 | ¥1,900 | 15% | 存储优化、查询优化 |
| 缓存服务 | ¥1,000 | ¥950 | 20% | 内存优化、数据结构优化 |
| CDN与带宽 | ¥3,000 | ¥2,800 | 25% | 压缩、缓存策略 |
| 第三方API | ¥10,000 | ¥9,500 | 30% | 调用优化、缓存 |
| **总计** | **¥21,000** | **¥19,950** | **22%** | - |

## 性能优化方案

### 应用层优化

#### 1. 代码性能优化
```python
# 优化前 - 低效的岗位搜索
def search_jobs_inefficient(keywords: List[str], filters: dict):
    results = []
    for keyword in keywords:
        # 每次循环都执行数据库查询
        jobs = Job.objects.filter(
            title__icontains=keyword,
            **filters
        ).all()
        results.extend(jobs)
    return list(set(results))

# 优化后 - 批量查询+缓存
from django.core.cache import cache
from django.db.models import Q

def search_jobs_optimized(keywords: List[str], filters: dict):
    # 生成缓存键
    cache_key = f"search:{hash(str(sorted(keywords)) + str(filters))}"
    
    # 检查缓存
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # 构建单个查询
    query = Q()
    for keyword in keywords:
        query |= Q(title__icontains=keyword)
    
    # 执行查询
    results = Job.objects.filter(query, **filters).distinct()
    
    # 缓存结果（5分钟）
    cache.set(cache_key, results, 300)
    return results

# 进一步优化 - 异步处理
from celery import shared_task

@shared_task
def async_search_jobs(keywords: List[str], filters: dict, user_id: str):
    """异步搜索任务"""
    results = search_jobs_optimized(keywords, filters)
    
    # 发送通知或存储结果
    send_search_result_notification(user_id, results)
    return results
```

#### 2. 数据库优化
```sql
-- 优化前 - 低效查询
SELECT * FROM jobs 
WHERE city LIKE '%上海%' 
AND salary_min > 10000 
ORDER BY created_at DESC 
LIMIT 100 OFFSET 0;

-- 优化后 - 使用索引
-- 创建复合索引
CREATE INDEX idx_jobs_search ON jobs(city, salary_min, created_at DESC);

-- 优化查询
SELECT id, title, company, salary_min, salary_max 
FROM jobs 
WHERE city = '上海'  -- 使用等值查询而非LIKE
AND salary_min > 10000 
ORDER BY created_at DESC 
LIMIT 100 OFFSET 0;

-- 分页优化
SELECT * FROM jobs 
WHERE id > ?  -- 使用游标分页而非OFFSET
AND city = '上海'
AND salary_min > 10000
ORDER BY id ASC 
LIMIT 100;
```

#### 3. 缓存策略优化
```python
# 多级缓存策略
class MultiLevelCache:
    def __init__(self):
        self.local_cache = {}  # 本地内存缓存
        self.redis_cache = redis.StrictRedis(host='redis', port=6379, db=0)
        self.cache_ttl = {
            'job_list': 300,      # 5分钟
            'user_profile': 1800, # 30分钟
            'search_result': 600, # 10分钟
            'static_content': 3600  # 1小时
        }
    
    def get(self, key: str):
        # 1. 检查本地缓存
        if key in self.local_cache:
            value, expiry = self.local_cache[key]
            if time.time() < expiry:
                return value
        
        # 2. 检查Redis缓存
        value = self.redis_cache.get(key)
        if value:
            # 回填本地缓存
            ttl = self.cache_ttl.get(key.split(':')[0], 300)
            self.local_cache[key] = (value, time.time() + ttl)
            return value
        
        # 3. 缓存未命中
        return None
    
    def set(self, key: str, value, ttl: int = None):
        cache_type = key.split(':')[0]
        ttl = ttl or self.cache_ttl.get(cache_type, 300)
        
        # 设置Redis缓存
        self.redis_cache.setex(key, ttl, value)
        
        # 设置本地缓存（较短的TTL）
        local_ttl = min(ttl, 60)  # 本地缓存最多1分钟
        self.local_cache[key] = (value, time.time() + local_ttl)
```

### 基础设施优化

#### 1. 服务器资源配置
```yaml
# docker-compose.optimized.yml
services:
  backend:
    image: internship-backend:optimized
    deploy:
      resources:
        limits:
          cpus: '2'      # 限制CPU使用
          memory: 2G     # 限制内存使用
        reservations:
          cpus: '0.5'    # 保证最少资源
          memory: 512M
    # 健康检查配置
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    # 重启策略
    restart: unless-stopped
  
  nginx:
    image: nginx:alpine
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
    # 启用HTTP/2和Gzip
    command: >
      nginx -g '
        daemon off;
        worker_processes auto;
        events {
          worker_connections 1024;
          use epoll;
          multi_accept on;
        }
        http {
          gzip on;
          gzip_comp_level 6;
          gzip_types text/plain text/css application/json application/javascript;
          http2 on;
        }
      '
```

#### 2. 自动伸缩策略
```python
# 自动伸缩脚本
import psutil
import requests
from datetime import datetime

class AutoScaler:
    def __init__(self):
        self.cpu_threshold_high = 70  # 扩容阈值
        self.cpu_threshold_low = 30   # 缩容阈值
        self.memory_threshold = 80    # 内存阈值
        self.min_instances = 2
        self.max_instances = 10
        self.current_instances = 2
    
    def check_metrics(self):
        """检查监控指标"""
        metrics = {
            'cpu': psutil.cpu_percent(interval=1),
            'memory': psutil.virtual_memory().percent,
            'load': psutil.getloadavg()[0],
            'connections': self.get_active_connections()
        }
        return metrics
    
    def scale_decision(self, metrics):
        """伸缩决策逻辑"""
        # CPU-based scaling
        if metrics['cpu'] > self.cpu_threshold_high:
            if self.current_instances < self.max_instances:
                return 'scale_out'
        elif metrics['cpu'] < self.cpu_threshold_low:
            if self.current_instances > self.min_instances:
                return 'scale_in'
        
        # Memory-based scaling
        if metrics['memory'] > self.memory_threshold:
            if self.current_instances < self.max_instances:
                return 'scale_out'
        
        return 'maintain'
    
    def execute_scaling(self, action):
        """执行伸缩操作"""
        if action == 'scale_out':
            self.current_instances += 1
            self.add_instance()
        elif action == 'scale_in':
            self.current_instances -= 1
            self.remove_instance()
        
        print(f"{datetime.now()}: {action}, instances: {self.current_instances}")
```

## 成本优化方案

### 云资源成本优化

#### 1. 实例类型优化
```bash
#!/bin/bash
# instance_optimization.sh
# 分析并优化实例类型

# 当前实例配置
CURRENT_INSTANCE="ec2.m5.xlarge"  # 4核16G
CURRENT_COST=0.192  # 每小时价格

# 分析资源使用率
CPU_USAGE=$(aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --statistics Average \
  --period 3600 \
  --start-time $(date -d "7 days ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date +%Y-%m-%dT%H:%M:%S) \
  --dimensions Name=InstanceId,Value=i-1234567890 \
  --query 'Datapoints[0].Average' \
  --output text)

MEMORY_USAGE=45  # 从监控系统获取

echo "当前资源使用率:"
echo "CPU: ${CPU_USAGE}%"
echo "内存: ${MEMORY_USAGE}%"

# 推荐优化方案
if [ $(echo "$CPU_USAGE < 40" | bc -l) -eq 1 ] && [ $MEMORY_USAGE -lt 50 ]; then
    RECOMMENDED_INSTANCE="ec2.m5.large"  # 2核8G
    ESTIMATED_COST=0.096
    SAVINGS=$(echo "scale=2; ($CURRENT_COST - $ESTIMATED_COST) * 24 * 30" | bc)
    
    echo "推荐优化: ${CURRENT_INSTANCE} -> ${RECOMMENDED_INSTANCE}"
    echo "预计月节省: ¥${SAVINGS}"
fi
```

#### 2. 预留实例与Spot实例
```yaml
# 混合实例策略
instance_strategy:
  reserved_instances:
    proportion: 60%    # 基础负载使用预留实例
    term: 1_year       # 1年期限
    payment_option: all_upfront  # 全预付以获得最大折扣
    
  spot_instances:
    proportion: 30%    # 可变负载使用Spot实例
    max_price: "on-demand_price * 0.7"  # 最高按需价格70%
    interruption_handling: "checkpoint_and_restart"
    
  on_demand_instances:
    proportion: 10%    # 峰值负载使用按需实例
    auto_scaling: true
    
# 预计节省计算
estimated_savings:
  reserved_instances: 40%  # 相比按需节省
  spot_instances: 70%      # 相比按需节省
  overall_savings: "≈50%"  # 总体节省
```

#### 3. 存储成本优化
```sql
-- 数据库存储优化
-- 1. 数据归档策略
CREATE TABLE job_archive (
    LIKE jobs INCLUDING ALL
) PARTITION BY RANGE (created_at);

-- 创建分区
CREATE TABLE jobs_2024_q1 PARTITION OF job_archive
FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE jobs_2024_q2 PARTITION OF job_archive
FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

-- 2. 数据压缩
ALTER TABLE job_archive 
ALTER COLUMN description 
SET STORAGE EXTERNAL;  -- 启用TOAST压缩

-- 3. 旧数据迁移到便宜存储
-- 将6个月前的数据迁移到S3 Glacier
INSERT INTO s3_archive 
SELECT * FROM jobs 
WHERE created_at < NOW() - INTERVAL '6 months';

DELETE FROM jobs 
WHERE created_at < NOW() - INTERVAL '6 months';
```

### 第三方服务成本优化

#### 1. OpenAI API调用优化
```python
class OpenAICostOptimizer:
    def __init__(self):
        self.cache = RedisCache()
        self.rate_limiter = RateLimiter()
        self.model_selector = ModelSelector()
    
    def generate_questions(self, job_description: str):
        # 1. 检查缓存
        cache_key = f"questions:{hash(job_description)}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # 2. 提取关键信息，减少Token使用
        extracted_info = self.extract_key_info(job_description)
        
        # 3. 根据复杂度选择模型
        complexity = self.assess_complexity(extracted_info)
        model = self.model_selector.select_model(complexity)
        
        # 4. 优化Prompt
        prompt = self.optimize_prompt(extracted_info, model)
        
        # 5. 调用API（带重试和退避）
        response = self.rate_limiter.call_with_retry(
            lambda: openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,  # 限制输出长度
                temperature=0.7
            )
        )
        
        # 6. 缓存结果
        questions = self.parse_response(response)
        self.cache.set(cache_key, questions, ttl=86400)  # 缓存24小时
        
        return questions
    
    def extract_key_info(self, job_description: str):
        """提取关键信息，减少Token使用"""
        # 使用本地NLP模型提取，避免调用API
        return {
            "position": self.extract_position(job_description),
            "requirements": self.extract_requirements(job_description),
            "skills": self.extract_skills(job_description),
            "experience": self.extract_experience(job_description)
        }
    
    def optimize_prompt(self, info: dict, model: str):
        """根据模型优化Prompt"""
        base_prompt = """
        基于以下职位信息，生成5个面试问题：
        职位：{position}
        要求：{requirements}
        技能：{skills}
        经验：{experience}
        """
        
        # GPT-3.5-turbo使用详细Prompt
        if model == "gpt-3.5-turbo":
            return base_prompt.format(**info) + "\n请生成专业、有深度的面试问题。"
        
        # GPT-4使用简洁Prompt
        elif model == "gpt-4":
            return f"为{info['position']}职位生成5个面试问题，要求：{info['requirements']}"
        
        return base_prompt.format(**info)
```

#### 2. 爬虫服务成本优化
```python
class CrawlerCostOptimizer:
    def __init__(self):
        self.proxy_manager = ProxyManager()
        self.scheduler = Scheduler()
        self.cache = Cache()
    
    def optimize_crawling(self):
        """优化爬虫成本策略"""
        strategies = {
            # 高频数据：使用便宜代理，频繁更新
            "zhipin": {
                "frequency": "hourly",
                "proxy_type": "datacenter",  # 便宜
                "cache_ttl": 3600,
                "retry_times": 2
            },
            
            # 中频数据：使用中等代理
            "zhilian": {
                "frequency": "4_hours",
                "proxy_type": "residential",  # 中等
                "cache_ttl": 14400,
                "retry_times": 3
            },
            
            # 低频数据：使用高质量代理
            "liepin": {
                "frequency": "daily",
                "proxy_type": "mobile",  # 高质量
                "cache_ttl": 86400,
                "retry_times": 5
            }
        }
        
        return strategies
    
    def schedule_crawls(self):
        """智能调度爬虫任务"""
        # 避开高峰时段
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 18:  # 工作时间
            concurrent_tasks = 2      # 减少并发
            delay_between = 5         # 增加延迟
        else:                         # 非工作时间
            concurrent_tasks = 5      # 增加并发
            delay_between = 2         # 减少延迟
        
        return {
            "concurrent_tasks": concurrent_tasks,
            "delay_between": delay_between,
            "timeout": 30
        }
```

## 监控与评估

### 性能监控仪表板
```yaml
# Grafana仪表板配置
dashboard:
  title: "性能与成本监控"
  panels:
    - title: "资源利用率"
      metrics:
        - cpu_usage{service="backend"} > 70
        - memory_usage{service="backend"} > 80
        - disk_usage{device="/"} > 85
      alerts:
        - name: "高资源使用率"
          condition: "ANY > 70% for 5m"
    
    - title: "API性能"
      metrics:
        - api_response_time_p95 < 5000
        - api_error_rate < 0.01
        - api_throughput > 100
      alerts:
        - name: "API性能下降"
          condition: "p95 > 5s for 2m"
    
    - title: "成本监控"
      metrics:
        - cloud_cost_daily < 700
        - api_call_cost_daily < 300
        - storage_cost_daily < 100
      alerts:
        - name: "成本超支"
          condition: "daily_cost > budget * 1.2"
```

### 成本分析报告
```markdown
# 月度成本分析报告

## 成本概览
- 总成本：¥19,950
- 预算：¥21,000
- 差异：-¥1,050 (节约5%)
- 趋势：环比下降8%

## 成本构成分析
### 按服务分解
| 服务 | 成本 | 占比 | 趋势 | 优化建议 |
|------|------|------|------|----------|
| 云服务器 | ¥4,800 | 24.1% | ↓5% | 可考虑预留实例 |
| 数据库 | ¥1,900 | 9.5% | ↓3% | 存储归档优化 |
| 缓存 | ¥950 | 4.8% | ↓8% | 内存数据结构优化 |
| CDN | ¥2,800 | 14.0% | ↓12% | 缓存策略有效 |
| OpenAI API | ¥9,500 | 47.6% | ↓10% | 继续优化调用 |

### 按环境分解
| 环境 | 成本 | 占比 | 资源使用率 | 优化空间 |
|------|------|------|------------|----------|
| 生产 | ¥15,960 | 80% | 65% | 中等 |
| 预发 | ¥2,394 | 12% | 45% | 较大 |
| 开发 | ¥1,596 | 8% | 30% | 很大 |

## 优化效果评估
### 已实施优化
1. **实例类型调整** (2026-03-15)
   - 节省：¥800/月
   - 影响：性能无下降

2. **缓存策略优化** (2026-03-20)
   - 节省：¥400/月
   - 影响：响应时间提升15%

3. **API调用优化** (2026-03-25)
   - 节省：¥1,200/月
   - 影响：用户体验无影响

### 待实施优化
| 优化项 | 预计节省 | 实施复杂度 | 优先级 | 预计完成 |
|--------|----------|------------|--------|----------|
| 预留实例采购 | ¥1,500/月 | 低 | P0 | 2026-04-15 |
| 数据归档策略 | ¥600/月 | 中 | P1 | 2026-04-30 |
| 爬虫代理优化 | ¥800/月 | 中 | P1 | 2026-05-15 |

## 下月优化计划
### 短期目标（1个月内）
1. 完成预留实例采购
2. 实施数据库自动归档
3. 优化CDN缓存策略

### 长期目标（3个月内）
1. 实施多云策略降低成本
2. 开发成本预测模型
3. 建立自动化优化系统
```

## 自动化优化系统

### 成本优化机器人
```python
class CostOptimizationBot:
    def __init__(self):
        self.monitor = CostMonitor()
        self.analyzer = CostAnalyzer()
        self.executor = ActionExecutor()
        
    def run_optimization_cycle(self):
        """运行优化周期"""
        # 1. 收集数据
        cost_data = self.monitor.collect_daily_costs()
        usage_data = self.monitor.collect_resource_usage()
        
        # 2. 分析优化机会
        opportunities = self.analyzer.find_optimization_opportunities(
            cost_data, usage_data
        )
        
        # 3. 优先级排序
        prioritized = self.prioritize_opportunities(opportunities)
        
        # 4. 执行优化
        for opp in prioritized[:3]:  # 每次执行前三项
            if self.should_execute(opp):
                self.executor.execute(opp)
                self.log_optimization(opp)
        
        # 5. 报告结果
        self.generate_optimization_report()
    
    def prioritize_opportunities(self, opportunities):
        """优先级排序算法"""
        def score_opportunity(opp):
            score = 0
            
            # 节省金额权重（40%）
            savings_score = min(opp['estimated_savings'] / 1000, 10) * 4
            
            # 实施难度权重（30%）
            difficulty_score = (10 - opp['implementation_difficulty']) * 3
            
            # 风险权重（20%）
            risk_score = (10 - opp['risk_level']) * 2
            
            # ROI权重（10%）
            roi_score = min(opp['roi_estimate'], 10)
            
            return savings_score + difficulty_score + risk_score + roi_score
        
        return sorted(opportunities, key=score_opportunity, reverse=True)
```

### 自动化伸缩策略
```terraform
# Terraform自动化伸缩配置
resource "aws_autoscaling_policy" "cpu_based" {
  name                   = "cpu-based-scaling"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.backend.name
}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "high-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "70"
  alarm_description   = "当CPU使用率超过70%时触发扩容"
  alarm_actions       = [aws_autoscaling_policy.cpu_based.arn]
}

resource "aws_cloudwatch_metric_alarm" "low_cpu" {
  alarm_name          = "low-cpu-utilization"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "30"
  alarm_description   = "当CPU使用率低于30%时触发缩容"
  alarm_actions       = [aws_autoscaling_policy.cpu_based.arn]
}
```

## 持续改进机制

### 优化回顾会议
| 会议 | 频率 | 参与人员 | 议程 |
|------|------|----------|------|
| 成本周会 | 每周 | 技术负责人、财务 | 周成本分析，快速优化决策 |
| 性能月会 | 每月 | 全体技术团队 | 性能趋势分析，优化方案评审 |
| 季度规划会 | 每季度 | 管理层、技术团队 | 长期优化规划，预算调整 |

### 优化效果追踪
```markdown
## 优化效果追踪表

### 2026年Q2优化追踪
| 优化项 | 目标 | 实际效果 | 状态 | 负责人 |
|--------|------|----------|------|--------|
| 实例类型优化 | 节省20% | 节省18% | ✅ 完成 | [姓名] |
| 缓存策略升级 | 命中率85% | 命中率88% | ✅ 完成 | [姓名] |
| API调用优化 | 减少30%调用 | 减少28%调用 | 🔄 进行中 | [姓名] |
| 数据库归档 | 存储成本降15% | 降12% | ⏳ 规划中 | [姓名] |

### 关键指标趋势
| 指标 | Q1平均值 | Q2当前值 | 变化 | 趋势 |
|------|----------|----------|------|------|
| 单位请求成本 | ¥0.15 | ¥0.11 | ↓26.7% | 📉 良好 |
| 资源利用率 | 45% | 62% | ↑17% | 📈 良好 |
| API响应时间P95 | 15s | 8.2s | ↓45.3% | 📉 优秀 |
| 月度总成本 | ¥21,500 | ¥19,950 | ↓7.2% | 📉 良好 |
```

## 附录

### 优化工具清单
| 工具 | 用途 | 使用方式 |
|------|------|----------|
| AWS Cost Explorer | 成本分析 | 每日查看，设置预算告警 |
| Grafana | 性能监控 | 实时仪表板，自定义告警 |
| Prometheus | 指标收集 | 应用性能指标收集 |
| Terraform | 基础设施即代码 | 自动化资源配置 |
| Python脚本 | 自定义优化 | 定期运行的成本分析脚本 |

### 联系人列表
| 角色 | 姓名 | 职责 | 联系方式 |
|------|------|------|----------|
| 成本优化负责人 | [姓名] | 总体协调，预算管理 | 电话/IM |
| 性能优化工程师 | [姓名] | 应用性能优化 | 电话/IM |
| 云架构师 | [姓名] | 基础设施优化 | 电话/IM |
| 财务分析师 | [姓名] | 成本数据分析 | 电话/IM |

### 变更记录
| 日期 | 版本 | 变更内容 | 变更人 | 审核人 |
|------|------|----------|--------|--------|
| 2026-04-11 | 1.0 | 初始版本创建 | Claude | - |
| [日期] | [版本] | [变更描述] | [姓名] | [姓名] |

---

**关联文档**：
- [Phase5_Task_Checklist.md](./Phase5_Task_Checklist.md) - 阶段5任务清单
- [Database_Backup_Recovery.md](./Database_Backup_Recovery.md) - 备份恢复策略
- [Emergency_Response_Plan.md](./Emergency_Response_Plan.md) - 应急预案
- [User_Feedback_Mechanism.md](./User_Feedback_Mechanism.md) - 用户反馈机制