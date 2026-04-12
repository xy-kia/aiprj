# 前言-（唯一非AI编写）

本项目是我在AI共造社活动尝试性使用claude code全程ai coding编写的学生求职AI员工，目前只实现了能调用用户配置的大模型API解析用户输入和简历开始搜索岗位，并设计面试问题供用户参考，同时对用户的回答进行评价

但搜索岗位并未完成，无法爬取BOSS直聘等平台的岗位信息，尝试过通过调用大模型API解析获得，但依旧无法成功

想法是能通过start.bat直接启动，初次可能耗时稍久，目前也没验证复现性

过程中一开始尝试不干扰ai编码，后面随着老师要求改变过方向，一开始要在终端分别运行前后端，下载依赖颇为复杂，配置api也在后端中特定配置，与本人预期不符，老版本的README文件写入了oldRM。

如今改为可以在前端中直接配置的样子，两天的时间内调成了现在可以运行的半成品，claude前期给的数据库设计现在看有些冗余，过程中也生成了很多用来找bug，修复bug的文件，设计需求，流程文件。

后面有时间的话尝试完成搜索功能，削减不必要的部分和文件

# 学生求职AI员工 - 智能岗位匹配系统

一个基于AI的学生求职辅助系统，通过爬虫收集招聘岗位，利用知识库进行智能匹配，帮助学生找到合适的实习和工作机会。

## 项目结构

```
.
├── backend/          # 后端服务（FastAPI + 爬虫）
├── frontend/         # 前端界面（Vue 3）
├── knowledge/        # 知识库数据（岗位、技能、城市代码等）
├── admin/            # 管理后台
├── scripts/          # 工具脚本
├── tests/            # 测试代码
├── docs/             # 项目文档
├── docker-compose.yml # Docker编排配置
├── launcher.py       # 🆕 一体化启动器（推荐使用）
├── start.bat         # 🆕 Windows启动脚本
├── start.sh          # 🆕 macOS/Linux启动脚本
└── memory_cache.py   # 🆕 内存缓存实现（替代Redis）
```

## 🚀 快速开始（一体化版本）

**推荐新用户使用此方式** - 无需安装MySQL、Redis，一键启动所有功能！

### Windows用户
1. 双击运行 `start.bat`
2. 等待自动安装依赖并启动
3. 浏览器自动打开 http://localhost:8000

### macOS/Linux用户
```bash
# 给启动脚本执行权限
chmod +x start.sh

# 运行启动脚本
./start.sh
```



## 大模型API配置

系统支持多AI提供商配置，可通过设置界面直接配置



#### 2. AI提供商配置
在"LLM API配置"板块中，您可以：

1. **选择AI提供商**：
   - **OpenAI**：官方OpenAI API（默认）
   - **Anthropic**：Claude系列模型
   - **Azure**：Azure OpenAI服务
   - **自定义/反代**：国内代理或自建OpenAI兼容服务

2. **配置API密钥**：
   - 输入对应提供商的API密钥
   - 密钥将加密存储到数据库

3. **设置基础URL**：
   - 系统会根据选择的提供商显示默认URL
   - 支持自定义URL用于国内代理（如OneAPI、OpenAI-Proxy等）
   - 示例：
     - OpenAI默认：`https://api.openai.com/v1`
     - 国内代理：`https://your-proxy.com/v1`
     - Azure OpenAI：`https://{resource}.openai.azure.com`

4. **测试连接**：
   - 点击"测试连接"按钮验证API密钥和URL
   - 成功连接后系统会自动获取可用模型列表
   - 错误提示会帮助诊断连接问题

5. **选择模型**：
   - 从获取的模型列表中选择默认模型
   - OpenAI：gpt-4o-mini, gpt-4o, gpt-3.5-turbo等
   - Anthropic：claude-3-sonnet, claude-3-haiku等

6. **调整参数**：
   - **温度**：控制回答的随机性（0.0-2.0）
   - **最大令牌数**：限制回答长度（100-16384）
   - **启用配置**：启用/禁用此AI配置

7. **保存配置**：
   - 点击"保存配置"将设置存储到数据库
   - 系统将使用此配置进行AI相关操作


## 📄 简历上传与AI分析功能

系统现已支持简历上传功能，可将您的PDF简历与求职意向结合，通过AI进行深度分析。

### 功能特性
- **PDF简历上传**：支持上传PDF格式的简历文件（最大10MB）
- **智能分析**：AI同时分析简历内容和求职意向，提供匹配度评估
- **技能识别**：自动识别简历中的技能点与求职意向的匹配程度
- **优化建议**：提供简历优化和技能提升建议

### 使用方法
1. 访问首页（http://localhost:8000）
2. 在输入框中填写求职意向（可选）
3. 点击"上传简历"按钮选择PDF文件
4. 点击"智能解析"按钮
5. 系统将使用您配置的LLM API进行分析，返回结构化结果

### 技术实现
- 后端API：`POST /api/v1/parse-intent-with-resume`
- 文件处理：使用pdfplumber提取PDF文本
- AI集成：调用用户配置的LLM API（OpenAI、Claude等）
- 响应格式：包含分析结果、简历摘要和关键词提取

### 注意事项
- 需要先配置LLM API（见上方"大模型API配置"章节）
- 仅支持PDF格式，文件大小限制10MB
- 分析结果的质量取决于LLM模型的性能

## 🎯 一体化启动器技术说明

### 设计目标
针对用户反馈的"启动时间太长"问题，一体化启动器实现了以下优化：

1. **零外部依赖** - 无需安装MySQL、Redis，使用SQLite + 内存缓存
2. **轻量级AI模型** - 用TF-IDF替代BERT，减少模型加载时间
3. **一键启动** - 双击脚本即可运行，自动安装依赖
4. **数据预置** - 包含示例岗位和技能数据

### 技术实现

#### 1. 数据库层优化
```python
# 使用SQLite替代MySQL
os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

# 自动创建示例数据
sample_jobs = [...]
sample_skills = [...]
```

#### 2. 缓存层优化
```python
# 使用内存缓存替代Redis
class MemoryCacheClient:
    # 实现与RedisClient兼容的接口
    def set(self, key, value, ex=None): ...
    def get(self, key, default=None): ...
```


### 限制与说明
1. **SQLite限制** - 适用于中小规模数据，大规模生产建议使用MySQL
2. **TF-IDF精度** - 文本相似度计算精度略低于BERT，但速度更快
3. **内存缓存** - 重启后数据丢失，适用于演示和开发
4. **AI功能** - 仍需配置API密钥才能使用完整AI功能

### 前端构建指南
一体化版本默认提供简化界面。如需使用完整前端：

```bash
# 1. 安装Node.js（如果尚未安装）
# 2. 进入前端目录
cd frontend

# 3. 安装依赖（首次运行）
npm install

# 4. 构建生产版本
npm run build

# 5. 重新启动一体化启动器
cd ..
python launcher.py
```

构建完成后，访问 http://localhost:8000 将显示完整的Vue前端。



