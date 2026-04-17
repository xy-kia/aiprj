# 项目结构优化任务清单


---

## 阶段一：前端合并与简化（优先级：高）

### 1.1 合并 admin 与 frontend
- [ ] 将 `admin/src/views/` 下的所有管理页面迁移到 `frontend/src/views/admin/`
- [ ] 将 `admin/src/services/api.ts` 中的 API 方法合并到 `frontend/src/services/`，去重统一
- [ ] 在 `frontend/src/router/` 中为管理员视图添加独立路由，使用路由守卫（`beforeEnter: requireAdmin`）控制访问权限
- [ ] 将 `admin/` 目录中的 `package.json`、`vite.config.ts`、`tsconfig*.json` 等配置内容合并到 `frontend/package.json`，统一构建入口
- [ ] **删除**独立的 `admin/` 目录

### 1.2 清理错位文件
- [ ] 将 `frontend/admin/memory_cache.py` 移回 `backend/app/cache/` 或根目录合适位置
- [ ] 删除 `frontend/admin/` 空目录

---

## 阶段二：运行时数据与配置治理（优先级：高）

### 2.1 建立 `data/` 运行时目录
- [ ] 在根目录创建 `data/` 文件夹，并加入 `.gitignore`
- [ ] 创建子目录结构：
  - `data/db/` — SQLite 数据库文件
  - `data/uploads/` — 用户上传的简历文件
  - `data/knowledge/` — 运行时抓取的岗位缓存数据
  - `data/logs/` — 日志文件
- [ ] 修改 `launcher.py` / `start.bat` / `start.sh`，启动时自动创建 `data/` 子目录

### 2.2 迁移知识库与示例数据
- [ ] 将 `knowledge/jobs/` 中的静态示例数据迁移到 `default-data/sample_jobs.json`
- [ ] 修改启动逻辑：若 `data/` 为空，自动将 `default-data/` 复制到 `data/`
- [ ] 保留 `prompts/` 目录（这是好设计），但将其中的模板视为只读代码资产

### 2.3 统一配置入口
- [ ] 合并 `.env`、`.env.prod`、`.env.prod.template` 和 `config/*.yaml` 为单一配置源
- [ ] 推荐方案：根目录保留一个 `.env.example` 作为模板，运行时由启动器自动生成 `.env`（写入 `.gitignore`）
- [ ] 修改 `backend/config/settings.py`，使其优先读取运行时 `.env`，并提供合理的默认值

---

## 阶段三：清理调试残留与 Git 污染（优先级：高）

### 3.1 删除一次性测试/调试文件
- [ ] 删除根目录及 `backend/` 下的临时测试文件：
  - `backend/test_ai_parser.py`
  - `backend/test_ai_simple.py`
  - `backend/test_boss_real.py`
  - `backend/test_crawler_simple.py`
  - `backend/test_launch.py`
  - `backend/test_scheduler_simple.py`
- [ ] 有价值的断言提取到 `tests/` 目录的正式测试用例中，无价值的直接丢弃

### 3.2 清理已入库的缓存文件
- [ ] 执行 `git rm -r --cached` 清理以下已追踪的缓存目录：
  - `backend/__pycache__/`
  - `backend/app/__pycache__/`
  - `backend/app/api/__pycache__/`
  - `backend/config/__pycache__/`
  - `backend/crawlers/__pycache__/`
  - `tests/__pycache__/`
  - `.pytest_cache/`
- [ ] 确保 `.gitignore` 包含以下规则：
  ```gitignore
  __pycache__/
  *.py[cod]
  *$py.class
  .pytest_cache/
  data/
  *.db
  *.sqlite3
  backend/.env
  .env
  uploads/
  ```

---

## 阶段四：爬虫模块插件化重构（优先级：中）

### 4.1 提取爬虫公共核心
- [ ] 在 `backend/crawlers/core/` 下建立以下模块：
  - `cleaning.py` — 原 `cleaning_rules.py`
  - `proxy.py` — 原 `proxy_pool.py`
  - `cookies.py` — 原 `cookie_manager.py`
  - `parser.py` — 通用 AI 兜底解析逻辑（从 `ai_parser.py` 中提取平台无关部分）
- [ ] 保留 `backend/crawlers/base.py`（`BaseCrawler` + `JobItem`）

### 4.2 按平台拆分爬虫插件
- [ ] 创建 `backend/crawlers/plugins/` 目录
- [ ] 将各平台爬虫重构为独立插件包：
  ```
  backend/crawlers/plugins/
  ├── boss/
  │   ├── __init__.py      # 导出 BOSSCrawler
  │   ├── crawler.py       # 平台-specific 爬取逻辑
  │   └── selectors.py     # DOM/接口选择器配置
  ├── liepin/
  │   ├── __init__.py
  │   ├── crawler.py
  │   └── selectors.py
  ├── qiancheng/
  │   ├── __init__.py
  │   ├── crawler.py
  │   └── selectors.py
  └── zhaopin/
      ├── __init__.py
      ├── crawler.py
      └── selectors.py
  ```
- [ ] 修改 `backend/crawlers/__init__.py`，实现自动发现插件加载机制
- [ ] 将 `backend/crawlers/ai_parser.py` 中平台-specific 的解析逻辑下沉到对应插件

---

## 阶段五：DevOps 与部署配置瘦身（优先级：中）

### 5.1 合并 Docker 配置
- [ ] 保留**一个** `docker-compose.yml`（供有 Docker 需求的用户使用）
- [ ] 删除多余的 Docker 文件：
  - `docker-compose.prod.yml`
  - `docker-compose.staging.yml`
  - `Dockerfile.backend`
  - `Dockerfile.frontend`
  - `backend/Dockerfile.prod`
  - `frontend/Dockerfile`
  - `frontend/Dockerfile.prod`
- [ ] （可选）将唯一保留的 `backend/Dockerfile` 移入 `docker/Dockerfile.backend`，根目录只留一个 `docker-compose.yml`

### 5.2 移除当前未使用的监控基础设施
- [ ] 将 `monitoring/`（Grafana + Prometheus + Alertmanager）移出主仓库，或归档到独立分支
- [ ] 将 `nginx/conf.d/` 和 `nginx/ssl/` 中未实际使用的配置清理掉，仅保留最小化配置（如需要）

---

## 阶段六：后端入口与包导入统一（优先级：中）

### 6.1 简化启动入口
- [ ] 在 `backend/` 下创建 `run.py`：
  ```python
  import uvicorn
  from app.main import app

  if __name__ == "__main__":
      uvicorn.run(app, host="0.0.0.0", port=8000)
  ```
- [ ] 修改 `backend/app/main.py`（或 `backend/main.py`）中的相对导入，确保 `cd backend && python run.py` 可直接启动
- [ ] 修改 `launcher.py` / `start.bat` / `start.sh`，使用新的 `backend/run.py` 作为后端启动入口
- [ ] 删除 `backend/__init__.py`（若导致包导入问题）

### 6.2 统一 API 版本前缀
- [ ] 确认前端代理配置与后端路由前缀一致（当前为 `/v1`）
- [ ] 检查所有 `frontend/src/services/` 中的请求路径，避免硬编码不一致的前缀

---


## 附录： 结构参考要点

|  实践 | 应用到本项目 |
| :--- | :--- |
| `public/` + `src/` 前后端代码分离 | `frontend/` + `backend/app/` |
| `data/` 存放所有运行时可变数据 | 新建 `data/` 目录 |
| `default/` 存放默认配置和示例 | 新建 `default-data/` 目录 |
| `plugins/` 和 `extensions/` 插件化扩展 | `crawlers/plugins/` 平台爬虫插件化 |
| 单一 `config.yaml` 配置入口 | 合并为单一 `.env` 配置 |
| Docker 配置收敛到 `docker/` 子目录 | 合并/归档冗余 Dockerfile |
| 根目录保持极简 | 删除监控、nginx 等未使用配置 |

---

**下一步建议**：从「阶段一：合并 admin」或「阶段三：清理调试文件」开始，这两个改动最直观、风险最低。
