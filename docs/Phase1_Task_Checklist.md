# 阶段1任务清单 - 基础准备（第1-2周）

**文档说明**：本清单基于 [Development_Process.md](./Development_Process.md) 阶段1部分制定，用于跟踪开发进度。

---

## 总体进度

| 阶段 | 总任务数 | 已完成 | 进行中 | 待开始 | 完成率 |
|------|----------|--------|--------|--------|--------|
| 阶段1 | 31 | 31 | 0 | 0 | 100% |

---

## 1.1 环境搭建

### 1.1.1 开发环境配置

- [x] **DEV-001** 安装 Python 3.9+ 环境
  - 负责人：后端
  - 验收标准：`python --version` 显示 3.9 或更高版本
  - 备注：建议使用 pyenv 或 conda 管理

- [x] **DEV-002** 安装 Node.js 18+ 环境
  - 负责人：前端
  - 验收标准：`node --version` 显示 v18 或更高版本
  - 备注：使用 nvm 管理版本

- [x] **DEV-003** 安装并配置 MySQL 8.0+
  - 负责人：后端
  - 验收标准：服务正常运行，可连接
  - 备注：记录 root 密码和端口配置

- [x] **DEV-004** 安装并配置 Redis 6.0+
  - 负责人：后端
  - 验收标准：`redis-cli ping` 返回 PONG
  - 备注：默认端口 6379

- [x] **DEV-005** 安装 Docker 最新版
  - 负责人：运维/后端
  - 验收标准：`docker --version` 正常输出
  - 备注：Windows 需安装 Docker Desktop

- [x] **DEV-006** 配置 Git 版本控制
  - 负责人：全员
  - 验收标准：`git --version` 正常输出，配置好用户名和邮箱
  - 备注：建议配置 SSH 密钥连接 GitHub/GitLab

### 1.1.2 项目结构初始化

- [x] **DEV-007** 创建后端项目目录结构
  - 负责人：后端
  - 验收标准：按文档规范创建所有目录
  - 交付物：
    ```
    backend/
    ├── app/
    │   ├── api/
    │   ├── core/
    │   ├── models/
    │   └── utils/
    ├── crawlers/
    ├── config/
    └── requirements.txt
    ```

- [x] **DEV-008** 创建前端项目目录结构
  - 负责人：前端
  - 验收标准：按文档规范创建所有目录
  - 交付物：
    ```
    frontend/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   └── services/
    └── package.json
    ```

- [x] **DEV-009** 创建其他项目目录
  - 负责人：后端
  - 验收标准：创建 admin/、knowledge/、scripts/、tests/ 目录
  - 备注：准备 docker-compose.yml 文件位置

### 1.1.3 依赖安装清单

- [x] **DEV-010** 安装后端核心依赖包
  - 负责人：后端
  - 验收标准：`pip list` 显示所有包已安装
  - 命令清单：
    ```bash
    pip install fastapi uvicorn sqlalchemy pymysql redis
    pip install scrapy playwright beautifulsoup4 lxml
    pip install jieba scikit-learn sentence-transformers
    pip install openai httpx python-dotenv
    ```

- [x] **DEV-011** 安装前端核心依赖包
  - 负责人：前端
  - 验收标准：`package.json` 包含所有依赖
  - 命令清单：
    ```bash
    npm install vue@3 axios element-plus vue-router pinia
    npm install echarts markdown-it
    ```

- [x] **DEV-012** 初始化 Playwright 浏览器
  - 负责人：后端
  - 验收标准：`playwright install chromium` 完成
  - 备注：仅安装 chromium 即可，减少体积

---

## 1.2 知识库构建

### 1.2.1 岗位模板库搭建

- [x] **KB-001** 定义岗位数据结构（JSON Schema）
  - 负责人：后端
  - 工期：2天
  - 验收标准：包含10个必填字段，通过校验测试
  - 交付物：job_schema.json

- [x] **KB-002** 收集20个MVP岗位数据
  - 负责人：运营
  - 工期：3天
  - 验收标准：覆盖主流实习类型（产品、开发、运营、设计等）
  - 交付物：jobs/ 目录下的20个 JSON 文件

- [x] **KB-003** 录入岗位别名映射表
  - 负责人：运营
  - 工期：2天
  - 验收标准：每个岗位 ≥2 个别名
  - 交付物：job_aliases.json

- [x] **KB-004** 定义岗位核心技能关联
  - 负责人：运营
  - 工期：2天
  - 验收标准：每个岗位 5-10 个核心技能
  - 交付物：job_skills_mapping.json

### 1.2.2 技能映射库搭建

- [x] **KB-005** 技能词条收集
  - 负责人：运营
  - 工期：3天
  - 数量目标：500+ 技能词条
  - 验收标准：覆盖主流技术栈（前端、后端、AI、产品等）
  - 交付物：skills.json

- [x] **KB-006** 技能分类整理
  - 负责人：运营
  - 工期：2天
  - 目标：10+ 类别，分类清晰无重叠
  - 交付物：skill_categories.json

- [x] **KB-007** 技能同义词映射
  - 负责人：运营
  - 工期：2天
  - 验收标准：每个技能 2-5 个同义词，提高召回率
  - 交付物：skill_synonyms.json

- [x] **KB-008** 关联技能标注
  - 负责人：运营
  - 工期：2天
  - 验收标准：每个技能标注 3-5 个关联技能
  - 交付物：skill_relations.json

### 1.2.3 城市代码库搭建

- [x] **KB-009** 收集招聘平台城市代码
  - 负责人：后端
  - 工期：2天
  - 覆盖平台：BOSS直聘、智联招聘、前程无忧、猎聘
  - 优先城市：北上广深杭成等10个核心城市
  - 交付物：city_codes.py

---

## 1.3 爬虫基础实现

### 1.3.1 爬虫架构设计

- [x] **CR-001** 实现爬虫基类 BaseCrawler
  - 负责人：后端
  - 工期：2天
  - 验收标准：抽象方法定义完整，可正常继承
  - 交付物：backend/crawlers/base.py

- [x] **CR-002** 实现通用请求工具模块
  - 负责人：后端
  - 工期：1天
  - 功能：封装 HTTP 请求、重试机制、超时处理
  - 交付物：backend/crawlers/utils.py

### 1.3.2 反爬策略配置

- [x] **CR-003** 实现 User-Agent 轮换
  - 负责人：后端
  - 工期：1天
  - 实现方式：集成 fake-useragent 库
  - 验收标准：每次请求随机切换 UA

- [x] **CR-004** 配置代理 IP 池
  - 负责人：后端
  - 工期：2天
  - 验收标准：请求失败自动切换代理
  - 备注：可先用免费代理池测试

- [x] **CR-005** 实现请求间隔随机延时
  - 负责人：后端
  - 工期：1天
  - 配置参数：1-5 秒随机
  - 交付物：delay 装饰器/中间件

- [x] **CR-006** 实现 Cookie 管理和更新
  - 负责人：后端
  - 工期：1天
  - 验收标准：会话保持，定期自动更新
  - 交付物：cookie_manager.py

### 1.3.3 数据清洗规则

- [x] **CR-007** 实现薪资字段清洗规则
  - 负责人：后端
  - 工期：1天
  - 规则：
    - "面议" → None
    - 提取数值范围，统一单位
  - 交付物：cleaning_rules.py 中 salary 规则

- [x] **CR-008** 实现城市字段清洗规则
  - 负责人：后端
  - 工期：1天
  - 规则：提取城市名，去除区县后缀
  - 交付物：cleaning_rules.py 中 location 规则

- [x] **CR-009** 实现学历字段清洗规则
  - 负责人：后端
  - 工期：1天
  - 规则：标准化为"本科"、"硕士"等
  - 交付物：cleaning_rules.py 中 education 规则

- [x] **CR-010** 实现数据验证器
  - 负责人：后端
  - 工期：1天
  - 功能：验证必填字段、数据类型、格式
  - 交付物：validators.py

---

## 里程碑检查点

### M1 检查点（第1周末）

- [x] 开发环境全部就绪（DEV-001 至 DEV-012）
- [x] 项目目录结构创建完成
- [x] 岗位数据结构定义完成（KB-001）

### M2 检查点（第2周末 - 阶段1完成）

- [x] 20个岗位数据收集完成（KB-002）
- [x] 技能库搭建完成（KB-005 至 KB-008）
- [x] 城市代码库完成（KB-009）
- [x] 爬虫基类实现完成（CR-001 至 CR-010）
- [x] 基础爬虫可运行测试通过

---

## 任务统计

| 类别 | 任务数量 | 优先级分布 |
|------|----------|------------|
| 环境搭建 (DEV) | 12 | P0: 12 |
| 知识库构建 (KB) | 9 | P0: 6, P1: 3 |
| 爬虫实现 (CR) | 10 | P0: 8, P1: 2 |
| **总计** | **31** | **P0: 26, P1: 5** |

---

## 使用说明

1. **任务状态更新**：
   - 待开始：`[ ]`
   - 进行中：`[~]`
   - 已完成：`[x]`
   - 阻塞：`[!]`

2. **优先级定义**：
   - P0：阻塞后续开发，必须按期完成
   - P1：重要但不阻塞，可适当延期
   - P2：优化项，可选完成

3. **更新记录**：

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
| 2026-04-11 | 初始版本，基于阶段1规划创建 | Claude |

---

**关联文档**：
- [Development_Process.md](./Development_Process.md) - 完整开发流程
- [Knowledge_and_Data.md](./Knowledge_and_Data.md) - 知识库详细设计
- [Functional_Spec.md](./Functional_Spec.md) - 功能需求规格
