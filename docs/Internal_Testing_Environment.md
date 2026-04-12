# 内部测试环境部署与验证指南

## 概述

本文档描述 Internship AI Assistant 内部测试环境的部署流程和验证标准，确保在发布到生产环境前进行充分的测试验证。

## 测试环境架构

### 1. 环境拓扑

```
┌─────────────────────────────────────────────────────────┐
│                  内部测试环境                           │
├─────────────┬─────────────┬─────────────┬─────────────┤
│  前端服务   │  后端服务   │   数据库    │   缓存      │
│  (Frontend) │  (Backend)  │   (MySQL)   │   (Redis)   │
│ 端口: 8080  │ 端口: 8001  │ 端口: 3307  │ 端口: 6380  │
└─────────────┴─────────────┴─────────────┴─────────────┘
                            │
                    ┌───────┴───────┐
                    │  反向代理     │
                    │   (Nginx)     │
                    │  端口: 80/443 │
                    └───────┬───────┘
                            │
                    ┌───────┴───────┐
                    │  测试域名     │
                    │  test.ai-internship.com │
                    └─────────────────┘
```

### 2. 资源配置

| 组件 | 版本 | 资源配置 | 数量 | 存储 |
|------|------|----------|------|------|
| 前端 | Node.js 18 | 1 CPU, 1GB RAM | 1 | 无状态 |
| 后端 | Python 3.11 | 2 CPU, 2GB RAM | 2 | 日志 10GB |
| MySQL | 8.0 | 2 CPU, 4GB RAM | 1 | 数据 50GB |
| Redis | 7.0 | 1 CPU, 1GB RAM | 1 | 内存 1GB |
| Nginx | 1.24 | 1 CPU, 512MB RAM | 1 | 日志 5GB |

### 3. 网络配置

- **测试域名**: `test.ai-internship.com`
- **SSL证书**: Let's Encrypt 自动签发
- **访问控制**: 仅限公司内网 IP 访问
- **端口开放**: 80, 443, 22 (SSH)

## 部署流程

### 1. 环境准备

#### 服务器准备
```bash
# 申请测试服务器（可通过运维平台或手动）
# 要求：4核8G，Ubuntu 22.04 LTS

# 初始化服务器
ssh admin@test-server
sudo apt update && sudo apt upgrade -y
sudo apt install docker docker-compose git curl -y
sudo usermod -aG docker $USER
```

#### 目录结构
```bash
/opt/internship-ai-test/
├── docker-compose.test.yml    # 测试环境编排
├── .env.test                  # 测试环境变量
├── nginx/
│   ├── nginx.test.conf       # 测试 Nginx 配置
│   └── ssl/                  # SSL 证书
├── data/
│   ├── mysql/                # 数据库数据
│   └── redis/                # Redis 数据
└── logs/                     # 应用日志
```

### 2. 配置文件

#### docker-compose.test.yml
```yaml
version: '3.8'
services:
  mysql-test:
    image: mysql:8.0
    container_name: internship_mysql_test
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: internship_db_test
      MYSQL_USER: internship_test
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    ports:
      - "3307:3306"
    volumes:
      - ./data/mysql:/var/lib/mysql
      - ./scripts/init_test_db.sql:/docker-entrypoint-initdb.d/init.sql
    command: --default-authentication-plugin=mysql_native_password --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      timeout: 20s
      retries: 10

  redis-test:
    image: redis:7-alpine
    container_name: internship_redis_test
    ports:
      - "6380:6379"
    volumes:
      - ./data/redis:/data
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend-test:
    image: ghcr.io/username/internship-backend:test-latest
    container_name: internship_backend_test
    environment:
      - DATABASE_URL=mysql+pymysql://internship_test:${MYSQL_PASSWORD}@mysql-test:3306/internship_db_test
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis-test:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY_TEST}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY_TEST}
      - LOG_LEVEL=DEBUG
      - ENVIRONMENT=test
    ports:
      - "8001:8000"
    volumes:
      - ./logs/backend:/app/logs
    depends_on:
      mysql-test:
        condition: service_healthy
      redis-test:
        condition: service_healthy
    restart: unless-stopped

  frontend-test:
    image: ghcr.io/username/internship-frontend:test-latest
    container_name: internship_frontend_test
    environment:
      - VITE_API_BASE_URL=/api
      - VITE_APP_TITLE="Internship AI Assistant (Test)"
    ports:
      - "8080:80"
    volumes:
      - ./logs/frontend:/var/log/nginx
    depends_on:
      - backend-test
    restart: unless-stopped

  nginx-test:
    image: nginx:alpine
    container_name: internship_nginx_test
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.test.conf:/etc/nginx/nginx.conf
      - ./nginx/conf.d.test:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - backend-test
      - frontend-test
    restart: unless-stopped
```

#### .env.test 模板
```bash
# 测试环境配置
MYSQL_ROOT_PASSWORD=test_root_password_123
MYSQL_PASSWORD=test_password_123
REDIS_PASSWORD=test_redis_password_123

# API 密钥（使用测试环境密钥）
OPENAI_API_KEY_TEST=sk-test-xxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY_TEST=sk-ant-test-xxxxxxxxxxxxxxxxxxxx

# 应用配置
ENVIRONMENT=test
LOG_LEVEL=DEBUG
DEBUG=true

# 测试数据配置
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=test123456
```

### 3. 部署脚本

#### 一键部署脚本
```bash
#!/bin/bash
# scripts/deploy_test.sh

set -e

echo "开始部署测试环境..."

# 1. 创建目录结构
mkdir -p /opt/internship-ai-test/{data,logs,nginx}
mkdir -p /opt/internship-ai-test/data/{mysql,redis}
mkdir -p /opt/internship-ai-test/logs/{backend,frontend,nginx}
mkdir -p /opt/internship-ai-test/nginx/ssl

# 2. 复制配置文件
cp docker-compose.test.yml /opt/internship-ai-test/
cp .env.test /opt/internship-ai-test/
cp nginx/nginx.test.conf /opt/internship-ai-test/nginx/

# 3. 生成 SSL 证书（如果需要）
if [ ! -f "/opt/internship-ai-test/nginx/ssl/cert.pem" ]; then
    echo "生成自签名 SSL 证书..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /opt/internship-ai-test/nginx/ssl/key.pem \
        -out /opt/internship-ai-test/nginx/ssl/cert.pem \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=Test/CN=test.ai-internship.com"
fi

# 4. 启动服务
cd /opt/internship-ai-test
docker-compose -f docker-compose.test.yml pull
docker-compose -f docker-compose.test.yml up -d

# 5. 等待服务就绪
echo "等待服务启动..."
sleep 30

# 6. 健康检查
curl -f http://localhost:8001/health || exit 1
curl -f http://localhost:8080 || exit 1

echo "测试环境部署完成!"
echo "前端访问: http://test.ai-internship.com"
echo "后端 API: http://test.ai-internship.com/api"
echo "API 文档: http://test.ai-internship.com/docs"
```

## 验证标准

### 1. 基础设施验证

#### 容器状态检查
```bash
# 检查所有容器运行状态
docker-compose -f docker-compose.test.yml ps

# 预期输出：所有服务状态应为 "Up"
```

#### 网络连通性测试
```bash
# 测试服务间连通性
docker-compose -f docker-compose.test.yml exec backend-test \
    curl -f http://mysql-test:3306

docker-compose -f docker-compose.test.yml exec backend-test \
    redis-cli -h redis-test -a $REDIS_PASSWORD ping
```

#### 资源使用监控
```bash
# 检查资源使用情况
docker stats --no-stream

# 检查磁盘空间
df -h /opt/internship-ai-test
```

### 2. 应用功能验证

#### 核心 API 测试
```bash
#!/bin/bash
# scripts/verify_test_apis.sh

# 1. 健康检查
curl -f http://test.ai-internship.com/health
echo "健康检查: ✅"

# 2. 意向解析 API
curl -X POST http://test.ai-internship.com/api/v1/parse/intent \
    -H "Content-Type: application/json" \
    -d '{"raw_input": "我想找一份北京的后端开发实习"}' \
    --fail --silent --show-error
echo "意向解析 API: ✅"

# 3. 岗位搜索 API
curl -X POST http://test.ai-internship.com/api/v1/jobs/search \
    -H "Content-Type: application/json" \
    -d '{"intent": {"position": "后端开发", "location": "北京"}, "page": 1, "page_size": 10}' \
    --fail --silent --show-error
echo "岗位搜索 API: ✅"

# 4. 问题生成 API
curl -X POST http://test.ai-internship.com/api/v1/questions/generate \
    -H "Content-Type: application/json" \
    -d '{"job_title": "Java 后端开发实习生", "company": "字节跳动", "skills": ["Java", "Spring", "MySQL"]}' \
    --fail --silent --show-error
echo "问题生成 API: ✅"

# 5. 回答评估 API
curl -X POST http://test.ai-internship.com/api/v1/evaluation/answer \
    -H "Content-Type: application/json" \
    -d '{"question": "请解释一下 Spring Boot 自动配置的原理", "answer": "Spring Boot 自动配置通过 @EnableAutoConfiguration 注解实现..."}' \
    --fail --silent --show-error
echo "回答评估 API: ✅"

echo "所有核心 API 验证通过!"
```

#### 前端功能测试
```bash
# 页面可访问性测试
curl -f http://test.ai-internship.com
curl -f http://test.ai-internship.com/jobs
curl -f http://test.ai-internship.com/practice
curl -f http://test.ai-internship.com/profile
```

#### 数据库验证
```bash
# 数据库连接测试
docker-compose -f docker-compose.test.yml exec mysql-test \
    mysql -u internship_test -p$MYSQL_PASSWORD internship_db_test \
    -e "SELECT COUNT(*) FROM jobs;"

# 检查表结构
docker-compose -f docker-compose.test.yml exec mysql-test \
    mysql -u internship_test -p$MYSQL_PASSWORD internship_db_test \
    -e "SHOW TABLES;"
```

### 3. 性能基准测试

#### API 响应时间
```bash
# 测试 API 响应时间
for i in {1..10}; do
    curl -w "%{time_total}s\n" -o /dev/null -s \
        http://test.ai-internship.com/health
done | awk '{sum+=$1} END {print "平均响应时间:", sum/NR, "秒"}'

# 验收标准：P95 < 500ms
```

#### 并发测试
```bash
# 使用 ab 进行并发测试
ab -n 100 -c 10 http://test.ai-internship.com/health

# 验收标准：成功率 > 99%，错误率 < 1%
```

#### 负载测试
```bash
# 模拟用户负载
siege -c 20 -t 30s http://test.ai-internship.com/api/v1/parse/intent
```

### 4. 安全验证

#### SSL/TLS 配置
```bash
# 检查 SSL 证书
openssl s_client -connect test.ai-internship.com:443 -servername test.ai-internship.com

# 检查安全头
curl -I https://test.ai-internship.com | grep -E "(Strict-Transport-Security|X-Content-Type-Options|X-Frame-Options)"
```

#### 访问控制验证
```bash
# 验证内网访问限制
curl -f http://test.ai-internship.com:80  # 应重定向到 HTTPS
curl -f https://test.ai-internship.com   # 应正常访问（内网）
```

#### 敏感信息检查
```bash
# 检查日志中是否泄露敏感信息
grep -r "password\|api_key\|secret" /opt/internship-ai-test/logs/ || echo "未发现敏感信息泄露"
```

## 测试数据管理

### 1. 测试数据集

#### 预置测试数据
```sql
-- scripts/init_test_db.sql
INSERT INTO users (email, password_hash, name) VALUES
    ('test.user@example.com', 'hashed_password_123', '测试用户'),
    ('admin.test@example.com', 'hashed_admin_password', '测试管理员');

INSERT INTO jobs (title, company, location, description) VALUES
    ('后端开发实习生', '字节跳动', '北京', '负责后端服务开发...'),
    ('前端开发实习生', '腾讯', '深圳', '负责前端界面开发...'),
    ('数据分析师实习生', '阿里巴巴', '杭州', '负责业务数据分析...');
```

#### 测试数据生成脚本
```python
# scripts/generate_test_data.py
import random
from faker import Faker

fake = Faker('zh_CN')

def generate_test_jobs(count=50):
    jobs = []
    for _ in range(count):
        jobs.append({
            'title': f'{random.choice(["后端", "前端", "数据", "产品", "运营"])}开发实习生',
            'company': fake.company(),
            'location': fake.city(),
            'description': fake.text(max_nb_chars=200)
        })
    return jobs
```

### 2. 数据清理策略

| 数据类型 | 保留策略 | 清理频率 |
|----------|----------|----------|
| 用户数据 | 保留 30 天 | 每日清理 |
| 任务数据 | 保留 7 天 | 每周清理 |
| 日志数据 | 保留 90 天 | 每月清理 |
| 缓存数据 | 保留 24 小时 | 每日清理 |

## 监控与告警

### 1. 监控指标

| 指标 | 告警阈值 | 检查频率 |
|------|----------|----------|
| 服务可用性 | <99% | 每分钟 |
| API 错误率 | >5% | 每分钟 |
| 响应时间 P95 | >1000ms | 每分钟 |
| 数据库连接数 | >80% | 每分钟 |
| 内存使用率 | >85% | 每分钟 |
| 磁盘使用率 | >90% | 每小时 |

### 2. 监控配置

#### Prometheus 配置
```yaml
# prometheus.test.yml
scrape_configs:
  - job_name: 'internship-test'
    static_configs:
      - targets:
        - 'backend-test:8000'
        - 'mysql-test:3306'
        - 'redis-test:6379'
        - 'nginx-test:80'
```

#### Grafana 仪表板
- 测试环境概览仪表板
- API 性能仪表板
- 资源使用仪表板
- 错误监控仪表板

### 3. 告警规则

```yaml
# alert.rules.test.yml
groups:
  - name: test-environment
    rules:
      - alert: TestAPIDown
        expr: up{job="internship-test", instance="backend-test:8000"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "测试环境 API 服务下线"
          
      - alert: TestAPIHighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "测试环境 API 错误率过高"
```

## 问题排查

### 1. 常见问题

#### 服务启动失败
```bash
# 查看容器日志
docker-compose -f docker-compose.test.yml logs backend-test
docker-compose -f docker-compose.test.yml logs mysql-test

# 检查端口冲突
netstat -tulpn | grep -E "(8001|3307|6380|8080)"
```

#### 数据库连接问题
```bash
# 检查数据库状态
docker-compose -f docker-compose.test.yml exec mysql-test mysqladmin -u root -p$MYSQL_ROOT_PASSWORD ping

# 检查数据库用户权限
docker-compose -f docker-compose.test.yml exec mysql-test \
    mysql -u root -p$MYSQL_ROOT_PASSWORD \
    -e "SELECT user, host FROM mysql.user WHERE user LIKE '%internship%';"
```

#### API 响应异常
```bash
# 查看应用日志
tail -f /opt/internship-ai-test/logs/backend/app.log

# 调试模式运行后端
docker-compose -f docker-compose.test.yml exec backend-test \
    python -c "import app; print(app.__version__)"
```

### 2. 恢复步骤

#### 服务重启
```bash
# 重启单个服务
docker-compose -f docker-compose.test.yml restart backend-test

# 重启所有服务
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d
```

#### 数据恢复
```bash
# 从备份恢复数据库
docker-compose -f docker-compose.test.yml exec mysql-test \
    mysql -u internship_test -p$MYSQL_PASSWORD internship_db_test < backup.sql
```

## 验收报告

### 1. 验证检查清单

| 检查项 | 状态 | 验证人 | 备注 |
|--------|------|--------|------|
| 容器状态正常 | ☐ | | 所有容器运行中 |
| 网络连通性 | ☐ | | 服务间通信正常 |
| API 功能正常 | ☐ | | 核心 API 测试通过 |
| 前端页面可访问 | ☐ | | 所有页面加载正常 |
| 性能指标达标 | ☐ | | 响应时间 < 500ms |
| 安全配置正确 | ☐ | | SSL、安全头正确 |
| 监控系统正常 | ☐ | | 指标采集、告警正常 |
| 日志记录完整 | ☐ | | 应用日志、访问日志正常 |

### 2. 验收报告模板

```markdown
# 测试环境部署验收报告

## 基本信息
- **环境名称**: 内部测试环境
- **部署版本**: v1.2.3
- **部署时间**: 2026-04-11 14:30:00
- **验证时间**: 2026-04-11 15:00:00
- **验证人**: 测试团队

## 验证结果

### 基础设施
- [x] 服务器资源充足
- [x] 容器编排正常
- [x] 网络配置正确
- [x] 存储挂载正常

### 应用功能
- [x] 后端 API 服务正常
- [x] 前端页面访问正常
- [x] 数据库连接正常
- [x] 缓存服务正常

### 性能指标
- [x] API 平均响应时间: 120ms (<500ms)
- [x] 并发处理能力: 100 RPS (>50 RPS)
- [x] 错误率: 0.1% (<1%)

### 安全合规
- [x] SSL/TLS 证书有效
- [x] 安全头配置正确
- [x] 访问控制生效
- [x] 敏感信息无泄露

## 发现的问题
1. 无

## 建议和改进
1. 无

## 验收结论
✅ **通过** - 测试环境部署成功，所有验证项目通过，可以用于后续测试工作。

**签名**: ____________________
**日期**: 2026-04-11
```

## 附录

### 快速命令参考
```bash
# 部署测试环境
./scripts/deploy_test.sh

# 验证测试环境
./scripts/verify_test_apis.sh

# 查看测试环境状态
docker-compose -f docker-compose.test.yml ps

# 查看测试环境日志
docker-compose -f docker-compose.test.yml logs -f

# 清理测试环境
docker-compose -f docker-compose.test.yml down -v
```

### 联系信息
- **测试负责人**: 测试团队 (test-team@example.com)
- **运维支持**: 运维团队 (ops@example.com)
- **紧急联系人**: 值班工程师 (oncall@example.com)

---

**文档版本**: 1.0  
**更新日期**: 2026-04-11  
**负责人**: 测试团队