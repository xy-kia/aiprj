# 应用性能监控（APM）集成指南

## 概述

本文档描述学生求职AI助手项目的应用性能监控（APM）集成方案，用于监控应用性能、追踪请求链路、分析性能瓶颈。

## APM选型

### 选型对比
| APM方案 | 优点 | 缺点 | 适用场景 | 选型结果 |
|---------|------|------|----------|----------|
| SkyWalking | 开源、功能全面、社区活跃 | 部署较复杂、学习曲线陡 | 微服务架构、全链路追踪 | **首选** |
| Elastic APM | 集成ELK生态、易用性好 | 商业版功能更强大 | 已有ELK栈、快速集成 | 备选 |
| Jaeger | CNCF项目、云原生友好 | 功能相对简单 | 云原生环境、Kubernetes | 备选 |
| Prometheus + Grafana | 已有基础、成本低 | 无全链路追踪 | 基础指标监控 | 基础监控 |

### 最终方案
- **生产环境**：SkyWalking（全链路追踪 + 性能监控）
- **开发/测试环境**：Elastic APM（快速集成）
- **基础监控**：Prometheus + Grafana（已有）

## SkyWalking集成

### 架构设计
```
[前端应用] → [Nginx] → [后端API] → [数据库/缓存]
     ↓           ↓         ↓           ↓
[Browser Agent] [Nginx Agent] [Java/Python Agent] [Database Agent]
     ↓           ↓         ↓           ↓
          [SkyWalking OAP Server]
                   ↓
          [Elasticsearch/MySQL]
                   ↓
          [SkyWalking UI]
```

### 部署配置

#### Docker Compose配置
```yaml
# docker-compose.apm.yml
version: '3.8'
services:
  # Elasticsearch (SkyWalking存储)
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    container_name: skywalking-es
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    networks:
      - skywalking-network

  # SkyWalking OAP Server
  oap:
    image: apache/skywalking-oap-server:9.7.0
    container_name: skywalking-oap
    depends_on:
      - elasticsearch
    environment:
      - SW_STORAGE=elasticsearch
      - SW_STORAGE_ES_CLUSTER_NODES=elasticsearch:9200
      - SW_TELEMETRY=prometheus
      - JAVA_OPTS=-Xms2g -Xmx2g
    ports:
      - "11800:11800"  # gRPC端口
      - "12800:12800"  # HTTP端口
    volumes:
      - ./skywalking/config:/skywalking/config
    networks:
      - skywalking-network
      - internship_network

  # SkyWalking UI
  ui:
    image: apache/skywalking-ui:9.7.0
    container_name: skywalking-ui
    depends_on:
      - oap
    environment:
      - SW_OAP_ADDRESS=oap:12800
    ports:
      - "8080:8080"
    networks:
      - skywalking-network

volumes:
  es_data:

networks:
  skywalking-network:
    driver: bridge
```

### 应用集成

#### 后端Python集成
```python
# requirements.txt 添加
skywalking==1.0.0

# main.py 配置
from skywalking import agent, config

# SkyWalking配置
config.init(
    agent_name='internship-backend',
    collector_address='skywalking-oap:11800',
    log_level='INFO',
    log_reporter_active=True,
    # 采样率：生产环境10%，测试环境100%
    sampler='percentage',
    sampling_rate=0.1 if os.getenv('ENVIRONMENT') == 'production' else 1.0
)

# 启动Agent
agent.start()

# FastAPI集成
from skywalking.plugins.sw_fastapi import FastapiInstrumentation
from fastapi import FastAPI

app = FastAPI()
FastapiInstrumentation().instrument(app)

# 数据库监控
from skywalking.plugins.sw_mysql import MysqlInstrumentation
MysqlInstrumentation().instrument()

# Redis监控
from skywalking.plugins.sw_redis import RedisInstrumentation
RedisInstrumentation().instrument()
```

#### 前端JavaScript集成
```javascript
// package.json 添加
"skywalking-client-js": "^0.4.0"

// main.js 配置
import { Client } from 'skywalking-client-js';

const client = new Client({
  service: 'internship-frontend',
  serviceVersion: process.env.VUE_APP_VERSION,
  pagePath: window.location.pathname,
  collector: 'https://skywalking.example.com',
  // 采样率
  traceRatio: window.location.hostname.includes('production') ? 0.1 : 1,
  // 忽略静态资源
  ignoreResources: [/\.(css|js|png|jpg|jpeg|gif|ico)$/],
});

// 启动监控
client.start();

// Vue.js错误监控
Vue.config.errorHandler = function(err, vm, info) {
  client.error(err, { component: vm.$options.name, info });
  console.error(err);
};
```

#### Nginx集成
```nginx
# nginx.conf
load_module modules/ngx_http_skywalking_module.so;

http {
    skywalking on;
    skywalking_service_name internship-nginx;
    skywalking_instance_name nginx-prod-01;
    skywalking_backend_service oap:11800;
    skywalking_sample_rate 0.1;
    
    server {
        location / {
            skywalking_ignore;
            proxy_pass http://backend:8000;
        }
        
        location /api/ {
            skywalking_trace;
            proxy_pass http://backend:8000;
        }
    }
}
```

### 监控指标

#### 关键性能指标（KPI）
| 指标 | 采集方式 | 告警阈值 | 优化目标 |
|------|----------|----------|----------|
| 响应时间(P95) | SkyWalking Agent | >15s | <10s |
| 错误率 | SkyWalking Agent | >5% | <1% |
| 吞吐量 | SkyWalking Agent | - | 根据业务增长 |
| 服务依赖健康度 | SkyWalking拓扑 | 依赖服务不可用 | 全部健康 |

#### 业务性能指标
| 指标 | 采集方式 | 说明 |
|------|----------|------|
| 意向解析耗时 | 自定义Span | 用户输入到关键词生成时间 |
| 岗位搜索耗时 | 自定义Span | 关键词搜索到结果返回时间 |
| 问题生成耗时 | 自定义Span | JD输入到问题生成时间 |
| 评估计算耗时 | 自定义Span | 回答提交到评估结果时间 |

### 自定义追踪
```python
from skywalking.trace.context import get_context
from skywalking.trace.tags import Tag

class IntentParser:
    def parse(self, raw_input: str):
        # 创建自定义Span
        with get_context().new_entry_span(op='IntentParser.parse') as span:
            span.tag(Tag(key='input_length', val=len(raw_input)))
            span.tag(Tag(key='service', val='intent-parser'))
            
            try:
                # 业务逻辑
                result = self._parse_intent(raw_input)
                
                # 记录成功
                span.tag(Tag(key='result_count', val=len(result)))
                span.tag(Tag(key='status', val='success'))
                return result
            except Exception as e:
                # 记录错误
                span.error_occurred()
                span.log(f'Parse error: {str(e)}')
                raise

class SearchService:
    def search_jobs(self, keywords):
        # 跨服务追踪
        with get_context().new_exit_span(op='Crawler.search', peer='crawler-service:8000') as span:
            # 添加跨服务header
            carrier = span.inject()
            headers = {'sw8': carrier}
            
            # 调用爬虫服务
            response = requests.post(
                'http://crawler-service:8000/search',
                json=keywords,
                headers=headers
            )
            
            span.tag(Tag(key='job_count', val=len(response.json())))
            return response.json()
```

## Elastic APM集成（备选方案）

### 快速集成
```python
# requirements.txt
elastic-apm[flask]

# 配置
from elasticapm import Client

apm = Client(
    service_name='internship-backend',
    server_url='http://apm-server:8200',
    secret_token='${APM_SECRET_TOKEN}',
    environment='production',
    framework_name='FastAPI',
    framework_version='0.104.0'
)

# FastAPI集成
from elasticapm.contrib.starlette import make_apm_client, ElasticAPM

apm = make_apm_client({
    'SERVICE_NAME': 'internship-backend',
    'SERVER_URL': 'http://apm-server:8200',
    'SECRET_TOKEN': '${APM_SECRET_TOKEN}',
    'ENVIRONMENT': 'production'
})

app = FastAPI()
app.add_middleware(ElasticAPM, client=apm)
```

## 性能分析

### 性能基线
| 端点 | P50响应时间 | P95响应时间 | P99响应时间 | 吞吐量(req/s) |
|------|-------------|-------------|-------------|---------------|
| POST /api/v1/parse/intent | 320ms | 450ms | 800ms | 50 |
| POST /api/v1/jobs/search | 8.2s | 12.5s | 20s | 10 |
| POST /api/v1/questions/generate | 2.1s | 3.5s | 6s | 20 |
| POST /api/v1/evaluation/answer | 1.5s | 2.8s | 5s | 30 |

### 性能优化建议
1. **搜索性能优化**
   - 增加爬虫并发数
   - 实现结果缓存
   - 优化数据库查询

2. **问题生成优化**
   - 缓存LLM响应
   - 优化Prompt工程
   - 批量处理请求

3. **评估计算优化**
   - 预计算关键词匹配
   - 并行计算各维度分数
   - 优化向量计算

## 告警配置

### SkyWalking告警规则
```yaml
# skywalking/alarm-settings.yml
rules:
  # 服务响应时间告警
  service_resp_time_rule:
    metrics-name: service_resp_time
    op: ">"
    threshold: 10000  # 10秒
    period: 10
    count: 3
    silence-period: 5
    message: "Service {name} response time over 10s in 3 minutes"

  # 服务错误率告警
  service_error_rate_rule:
    metrics-name: service_error_rate
    op: ">"
    threshold: 0.05  # 5%
    period: 10
    count: 2
    silence-period: 5
    message: "Service {name} error rate over 5% in 2 minutes"

  # 端点响应时间告警
  endpoint_avg_rule:
    metrics-name: endpoint_avg
    op: ">"
    threshold: 5000  # 5秒
    period: 10
    count: 2
    silence-period: 5
    message: "Endpoint {name} average response time over 5s in 2 minutes"

webhooks:
  - http://alertmanager:9093/api/v1/alerts
```

## 仪表板配置

### SkyWalking UI仪表板
| 仪表板 | 用途 | 访问地址 |
|--------|------|----------|
| 服务拓扑图 | 服务依赖关系可视化 | http://skywalking:8080/topology |
| 服务性能 | 服务级性能指标 | http://skywalking:8080/service |
| 端点性能 | 端点级性能指标 | http://skywalking:8080/endpoint |
| 追踪查询 | 分布式追踪查询 | http://skywalking:8080/trace |
| 日志关联 | 日志与追踪关联 | http://skywalking:8080/log |

### Grafana仪表板
1. **服务性能概览**
   - 响应时间趋势
   - 吞吐量监控
   - 错误率统计

2. **业务性能分析**
   - 各功能模块性能对比
   - 用户行为分析
   - 业务漏斗分析

3. **基础设施监控**
   - 服务器资源使用
   - 数据库性能
   - 缓存命中率

## 故障排查

### 常见问题排查流程
1. **性能下降**
   - 查看服务拓扑，识别瓶颈服务
   - 分析端点性能，定位慢接口
   - 检查追踪链路，分析调用链

2. **错误增加**
   - 查看错误类型分布
   - 分析错误堆栈信息
   - 关联日志和追踪

3. **服务不可用**
   - 检查服务健康状态
   - 分析依赖服务状态
   - 查看网络连接情况

### 诊断命令
```bash
# 查看SkyWalking服务状态
curl http://skywalking-oap:12800/

# 查询追踪信息
curl "http://skywalking-oap:12800/trace?serviceId=xxx&traceId=xxx"

# 导出性能数据
curl "http://skywalking-oap:12800/metrics" > metrics.json
```

## 维护与优化

### 日常维护任务
| 任务 | 频率 | 负责人 |
|------|------|--------|
| 监控系统健康检查 | 每日 | 运维 |
| 性能数据备份 | 每周 | 运维 |
| 告警规则优化 | 每月 | 运维+开发 |
| 系统容量评估 | 每季度 | 架构师 |

### 性能优化周期
1. **每周**：分析性能趋势，识别潜在问题
2. **每月**：优化慢查询，调整资源配置
3. **每季度**：架构优化，技术栈评估

## 附录

### 资源需求
| 组件 | CPU | 内存 | 存储 | 数量 |
|------|-----|------|------|------|
| SkyWalking OAP | 4核 | 8GB | 100GB | 2 |
| Elasticsearch | 4核 | 16GB | 500GB | 3 |
| SkyWalking UI | 2核 | 4GB | 20GB | 1 |

### 监控指标导出
```python
# 自定义指标导出到Prometheus
from prometheus_client import Counter, Histogram

# 定义指标
SEARCH_REQUESTS = Counter('internship_search_requests_total', 'Total search requests')
SEARCH_DURATION = Histogram('internship_search_duration_seconds', 'Search request duration')

# 使用装饰器记录指标
@SEARCH_DURATION.time()
def search_jobs(keywords):
    SEARCH_REQUESTS.inc()
    # 搜索逻辑
```

### 参考文档
- [SkyWalking官方文档](https://skywalking.apache.org/docs/)
- [Elastic APM文档](https://www.elastic.co/guide/en/apm/get-started/current/index.html)
- [分布式追踪最佳实践](https://opentracing.io/docs/best-practices/)