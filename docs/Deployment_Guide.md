# 部署指南

## 快速开始

### 1. 环境要求

- Python 3.9+
- MySQL 8.0+
- Redis 6.0+
- Node.js 18+ (前端可选)

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd aiprj

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 3. 配置环境变量

```bash
cd backend
cp .env.example .env
```

编辑`.env`文件，配置数据库、Redis和OpenAI API密钥。

### 4. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE internship_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 使用Alembic迁移（如果配置了）
alembic upgrade head
```

### 5. 启动服务

#### 开发模式

```bash
# 启动后端API
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 在另一个终端启动前端（如果前端存在）
cd frontend
npm run dev
```

#### 生产模式

```bash
# 使用gunicorn（需要安装）
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 6. 使用Docker Compose

```bash
# 一键部署所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## API端点

### 核心API

1. **意向解析**
   ```
   POST /api/v1/parse/intent
   ```

2. **岗位搜索**
   ```
   POST /api/v1/jobs/search
   ```

3. **问题生成**
   ```
   POST /api/v1/questions/generate
   ```

4. **回答评估**
   ```
   POST /api/v1/evaluation/answer
   ```

### 健康检查

```
GET /health
```

## 配置说明

### 爬虫配置

在`backend/config/settings.py`中调整爬虫参数：
- `CRAWLER_DELAY_MIN` / `CRAWLER_DELAY_MAX`: 请求延迟范围
- `CRAWLER_MAX_RETRIES`: 最大重试次数
- `USE_PROXY`: 是否使用代理

### OpenAI配置

- `OPENAI_API_KEY`: OpenAI API密钥
- `OPENAI_MODEL`: 使用的模型（默认：gpt-4o-mini）

### 数据库配置

- `DATABASE_URL`: MySQL连接字符串
- `REDIS_URL`: Redis连接字符串

## 监控与日志

### 日志配置

日志级别通过`LOG_LEVEL`环境变量控制：
- DEBUG: 开发环境
- INFO: 生产环境
- ERROR: 只记录错误

日志文件位置：`logs/app.log`

### 性能监控

关键性能指标：
- API响应时间（目标：<500ms）
- 爬虫成功率（目标：>85%）
- 缓存命中率

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查MySQL服务是否运行
   - 验证连接字符串中的用户名和密码

2. **OpenAI API调用失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 检查API使用额度

3. **爬虫无法获取数据**
   - 检查目标网站是否可访问
   - 调整反爬虫延迟设置
   - 考虑使用代理IP

4. **内存泄漏**
   - 检查爬虫是否及时关闭浏览器实例
   - 监控Redis内存使用情况

### 日志分析

```bash
# 查看实时日志
tail -f logs/app.log

# 搜索错误日志
grep "ERROR" logs/app.log

# 分析API响应时间
grep "response_time" logs/app.log | awk '{print $NF}'
```

## 备份与恢复

### 数据库备份

```bash
# 备份数据库
mysqldump -u root -p internship_db > backup_$(date +%Y%m%d).sql

# 恢复数据库
mysql -u root -p internship_db < backup_file.sql
```

### Redis备份

```bash
# 创建Redis快照
redis-cli SAVE

# 快照文件位置：/var/lib/redis/dump.rdb
```

## 安全建议

1. **API安全**
   - 在生产环境启用HTTPS
   - 实施API速率限制
   - 使用JWT认证

2. **数据安全**
   - 定期备份数据库
   - 加密敏感配置信息
   - 实施访问控制

3. **网络安全**
   - 配置防火墙规则
   - 使用VPN访问管理界面
   - 定期更新依赖包

## 扩展与定制

### 添加新的爬虫平台

1. 在`backend/crawlers/`目录下创建新的爬虫类
2. 继承`BaseCrawler`或`PlaywrightCrawler`
3. 实现`search_jobs`和`parse_job_detail`方法
4. 在`search_scheduler.py`中注册新爬虫

### 自定义匹配算法

1. 修改`match_calculator.py`中的权重配置
2. 调整各维度评分算法
3. 添加新的匹配维度

### 集成其他LLM服务

1. 在`question_generator.py`中支持其他LLM API
2. 实现统一的LLM服务接口
3. 配置模型参数和定价

---

**版本**: 1.0  
**更新日期**: 2026-04-11