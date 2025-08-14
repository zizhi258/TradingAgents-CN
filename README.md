# 项目介绍（股票智能投研与交易决策）

本项目是面向中文用户的“多智能体+可视化+可部署”的股票智能投研与交易决策解决方案。核心应用由 TradingAgents-CN 提供：它基于大语言模型与多智能体协作，对A股/港股/美股进行基本面、技术面、新闻与情绪等多维分析，并输出结构化结论与可视化报告；同时配套接口文档与外部服务说明，便于快速集成与二次开发。


## 项目用途

- 智能投研分析：针对单只或多只股票，结合基本面/技术面/新闻面/情绪面给出“买入/持有/卖出”建议与置信度，并附风险提示。
- 多市场支持：覆盖 A股、港股与美股，整合 Tushare、AkShare、FinnHub、Yahoo Finance 等数据源。
- 多模型协作：集成 DeepSeek、Google Gemini、OpenRouter（聚合 OpenAI/Anthropic/Meta/Google 等）等多家模型提供商，可在 Web 上一键切换与持久化配置。
- 可视化与报告：内置 ChartingArtist 图表服务与前端组件，支持 K 线、折线、柱状、热力等图表；分析结果可一键导出为 Markdown/Word/PDF。
- 部署与集成：提供 Docker Compose + 本地两种部署方式；后端 FastAPI 暴露图表与分析相关接口，便于系统对接。
- 文档与扩展：随附“接口文档”（如 Tushare 数据说明）与“升级蓝图”，支持按需扩展 RAG 问答、专业统计分析等高级能力。


## 整体架构概览

- 多智能体分析层：市场分析、基本面、新闻、情绪、看多/看空研究员、交易决策、风险管理等角色以图谱协作完成分析。
- 模型接入层：DeepSeek / Google AI (Gemini) / OpenRouter 等 LLM 提供商通过适配器统一调用，支持模型快速切换与参数持久化。
- 数据接入层：Tushare、AkShare、FinnHub、Yahoo Finance 等数据源，并提供缓存与降级策略；可选 MongoDB/Redis 持久化与加速。
- 应用层：Streamlit Web 前端 + FastAPI 后端（图表与服务接口），支持异步进度跟踪、结果恢复与会话管理。
- 部署与运维：Docker 一键编排（Web/API/DB/缓存/管理界面），脚本化运维与日志/监控辅助工具。


## 目录结构

根目录（/股票）包含核心应用、接口资料与服务说明：

- `TradingAgents-CN/`：核心应用（中文增强版 TradingAgents）
  - `tradingagents/`：Python 包（核心逻辑）
    - `agents/`：各分析师与角色智能体实现
    - `graph/`：多智能体协作与流程编排
    - `tools/`：行情、技术指标、新闻检索与实用工具
    - `api/`：后端接口（含 ChartingArtist 图表 API）
    - `llm/`、`llm_adapters/`：多模型提供商与适配层
    - `database/`、`services/`、`utils/`、`monitoring/` 等：存储、服务、工具与监控
  - `web/`：Streamlit 前端
    - `app.py`：Web 入口
    - `components/`、`modules/`、`pages/`、`static/`、`utils/`：组件、业务模块、页面与静态资源
  - `config/`：配置中心
    - `agent_roles.yaml`、`model_roles.yaml`、`multi_model_config.yaml` 等角色/模型/多模型配置
    - `charting_config.yaml`、`settings.json`、`pricing.json` 等功能与价格参数
  - `scripts/`：部署与诊断脚本（`smart_start.*`、`fix_chromadb_*`、`deploy.*`、数据库工具等）
  - 根级运行与编排：`main.py`、`start_web.py`、`docker-compose*.yml`、`Dockerfile*`、`requirements.txt`、`pyproject.toml`
  - 文档与示例：`README.md`、`examples/`（批量分析/自定义分析等 Demo）
- `接口文档/`：接口与数据说明（包含 Tushare 采集文档 `index*.md` 与图片资源 `images/`）
- `Gemini-API-服务介绍.md`：Gemini API 服务接入说明（OpenAI 兼容、无需翻墙、模型与示例）
- `升级.md`：能力升级蓝图（RAG 问答、Analyst-Pro 专业分析师、治理与反馈学习等规划）
- `项目介绍.md`：本文件


## 快速开始

方式一：Docker（推荐）

1) 切换目录：`cd TradingAgents-CN`  2) 配置环境：`cp .env.example .env` 并填入各类 API Key  
3) 启动服务：`docker-compose up -d --build`  
4) 访问 Web：`http://localhost:8501`

方式二：本地运行

1) 升级 pip：`python -m pip install --upgrade pip`  2) 安装依赖：`pip install -e .`  
3) 启动应用：`python start_web.py`  → 访问 `http://localhost:8501`

图表 API（ChartingArtist）默认随后端服务提供，详见 `TradingAgents-CN/README.md` 的“ChartingArtist API 配置”。


## 关键能力与特性（来自 TradingAgents-CN）

- 智能新闻分析：多层次过滤（基础/增强/集成）、质量评估与相关性分析，统一新闻检索工具。
- 多模型接入：DeepSeek / Google AI / OpenRouter（聚合 60+ 模型）一站式切换，Web 端配置持久化与 URL 分享。
- 实时进度与恢复：异步进度跟踪、状态持久化、页面刷新结果不丢失。
- 数据与市场：A股/港股/美股三大市场，整合多源数据并支持降级与缓存策略（Redis/MongoDB 可选）。
- 报告导出：Markdown/Word/PDF 专业报告，一键导出投资结论、详细分析与风险披露。
- 容器化与运维：Docker Compose 一键部署，包含 Web/API、MongoDB、Redis 及常用管理工具。


## 技术栈与依赖

- 语言与框架：Python 3.10+、Streamlit（前端）、FastAPI（后端 API）、LangChain（LLM 编排）
- 模型与提供商：DeepSeek、Google Gemini、OpenRouter（含 OpenAI/Anthropic/Meta/Google 等）
- 数据与存储：Tushare、AkShare、FinnHub、Yahoo Finance；MongoDB（持久化）、Redis（缓存）
- 部署与运维：Docker、Docker Compose；脚本化运维与日志/监控工具


## 面向角色

- 业务/投研：通过 Web 一键完成多维度分析并导出报告。
- 开发/架构：基于 API 与配置文件快速集成、拓展自有数据与工具链。
- 运维/部署：使用 Docker Compose 快速上线并配套数据库与缓存服务。


## 进阶与规划

- RAG 问答助手：知识库检索增强问答、证据引用与时间旅行（详见 `升级.md`）。
- Analyst-Pro：专业级统计/计量/事件研究工具链与结构化报告（详见 `升级.md`）。
- 协同治理：模型仲裁、合规守门、成本与质量仪表、反馈学习闭环（详见 `升级.md`）。


## 说明

- 本项目仅供技术研究与教学演示，不构成任何投资建议。请结合自身风险承受能力与市场环境谨慎使用。
# TradingAgents-CN 项目介绍（详细版）

TradingAgents-CN 是面向中文用户的多智能体股票投研与交易决策系统，提供 A股/港股/美股 多市场支持、可视化图表与专业报告导出、可配置的多模型协作（DeepSeek / Google Gemini / OpenRouter / SiliconFlow 等），并支持本地与 Docker 一键部署。本文从“用途、架构、目录结构、部署配置、工作流、扩展指南、排错与最佳实践”等维度做系统性介绍。


## 一、项目用途与价值

- 智能投研：围绕单只或多只股票，结合基本面、技术面、新闻与情绪分析，产出“买入/持有/卖出”建议与置信度，附风险提示与证据引用。
- 多市场覆盖：A股（Tushare/AkShare/通达信）、港股（AkShare/Yahoo Finance）、美股（FinnHub/Yahoo Finance）。
- 多模型协作：DeepSeek、Gemini、OpenRouter（聚合 OpenAI/Anthropic/Meta/Google 等）、SiliconFlow（国产聚合），内置路由、Fallback 与成本预算控制。
- 可视化与导出：ChartingArtist 图表服务，支持 K 线、折线、柱状、热力等；一键导出 Markdown / Word / PDF 专业报告。
- 可部署与集成：Streamlit Web 前端 + FastAPI 后端 + Docker Compose 编排；API 可对外提供图表和数据接口，便于二次开发与集成。


## 二、系统架构与数据流

数据与控制流程（简述）：

1) Web 前端（Streamlit，`web/app.py`）采集用户配置与股票输入，展示进度与结果；
2) 后端 API（FastAPI，`tradingagents/api/main.py`）提供图表、市场数据、可视化接口；
3) 多智能体协作（`tradingagents/graph/trading_graph.py`）驱动分析流程，组织分析师、研究员、交易与风险角色；
4) 模型适配层（`tradingagents/llm_adapters/`、`tradingagents/api/*_client.py`）统一接入 DeepSeek/Gemini/OpenRouter/SiliconFlow；
5) 数据接入与缓存（`tradingagents/dataflows/`）整合 Tushare/AkShare/FinnHub 等数据源，含 Redis/MongoDB 缓存与降级策略；
6) 可视化层（ChartingArtist：`tradingagents/api/charting_endpoints.py` + 前端组件）生成并管理图表；
7) 存储与状态（`MongoDB/Redis`）保存进度、图表与配置，支持恢复与异步跟踪。


## 三、目录结构详解（重点关注）

顶层重要内容：

- `web/`：Streamlit 前端（UI、表单、进度、可视化、角色与配置管理）。
- `tradingagents/`：核心 Python 包（智能体、数据流、LLM 适配、API、工具、核心编排、监控等）。
- `config/`：角色/模型/图表/定价等配置与模板。
- `scripts/`：部署、诊断、数据库、日志等运维脚本。
- `docker-compose.yml`、`Dockerfile*`：容器化编排与镜像构建。
- `.env.example`：环境变量示例（复制为 `.env` 后使用）。

### 3.1 web（前端）

- `web/app.py`：Web 入口。负责页面结构、主题、URL 参数、会话与多模型协作页签路由。
- `web/components/`：可复用的 UI 组件与交互逻辑。
  - `model_selection_panel.py`：模型提供商与模型选择、快速切换与持久化。
  - `enhanced_visualization_tab.py`、`charting_artist_component.py`：可视化入口与批量图表管理。
  - `analysis_form.py`、`multi_model_analysis_form.py`、`enhanced_multi_model_analysis_form.py`：单模型/多模型分析表单。
  - `results_display.py`、`market_results_display.py`、`enhanced_market_results_display.py`：结果与市场级结果展示。
  - `async_progress_display.py`、`history_manager.py`：统一进度展示与历史。
  - `header.py`、`sidebar.py`、`profile_panel.py`：导航、侧栏与个人信息。
- `web/modules/`：后端交互与业务逻辑模块。
  - `config_management.py`、`role_library_manager.py`、`role_model_binding.py`：配置中心与角色绑定。
  - `enhanced_market_wide_analysis.py`、`market_wide_analysis.py`：全市场分析模块。
  - `scheduler_admin.py`：调度管理页面（可选）。

### 3.2 tradingagents（核心包）

- `agents/`：智能体集合。
  - `analysts/`、`researchers/`：技术/基本面/新闻/情绪分析师、看多/看空研究员等。
  - `trader/`：交易决策输出；`risk_mgmt/`：风险控制与合规提示；`managers/`：研究主管与协作管理。
  - `specialized/`：专项能力（例如新闻增强过滤等）。
- `graph/`：多智能体协作流。
  - `trading_graph.py`：核心协作图谱（分析阶段、辩论、汇总、建议）。
  - `multi_model_extension.py`：多模型协作扩展；`reflection.py`、`signal_processing.py`：反思与信号处理。
- `api/`：后端 API 与第三方客户端。
  - `main.py`：FastAPI 入口；健康检查与路由汇总。
  - `charting_endpoints.py`、`visualization_api.py`：ChartingArtist 图表管理与生成。
  - `market_data_endpoints.py`、`stock_api.py`：市场数据与股票接口。
  - `google_ai_client.py`、`deepseek_client.py`、`siliconflow_client.py`：各提供商 OpenAI 兼容客户端。
- `tools/`：工具层。
  - `charting_tools.py`：统一图表生成工具；`unified_news_tool.py`：统一新闻抓取与处理工具。
- `llm/` 与 `llm_adapters/`：模型适配层与插件体系。
  - `openai_compatible_base.py`：OpenAI 兼容协议基类；`deepseek_adapter.py`、`deepseek_direct_adapter.py`：DeepSeek 接入。
  - `custom/`、`plugin_loader.py`：扩展与插件加载。
- `dataflows/`：数据接入、缓存与性能。
  - `data_source_manager.py`、`interface.py`：多源路由与统一接口；`akshare_utils.py`、`tushare_utils.py`、`finnhub_utils.py` 等源适配。
  - `enhanced_mongodb_integration.py`、`enhanced_redis_integration.py`、`integrated_cache.py`：MongoDB/Redis 集成与缓存策略。
  - `optimized_china_data.py`、`optimized_us_data.py`、`hk_stock_utils.py`：市场特定优化。
  - `streaming_pipeline.py`、`data_quality_monitor.py`、`performance_optimizer.py`：流式处理、质量与性能监控。
- `core/`：协作中枢。
  - `multi_model_manager.py`、`base_multi_model_adapter.py`：多模型协作管理与抽象层。
  - `smart_routing_engine.py`：智能路由与成本/性能平衡；`post_processing_orchestrator.py`：后处理编排。
  - `market_scan_orchestrator.py`：市场范围扫描任务；`user_friendly_error_handler.py`：可读错误封装。
- `utils/`：通用工具。
  - `news_filter.py`、`enhanced_news_filter.py`、`news_filter_integration.py`：新闻过滤与集成。
  - `logging_manager.py`、`tool_logging.py`、`charting_performance.py`：日志与性能。
  - `stock_validator.py`、`stock_utils.py`：股票代码校验与工具。
  - `api_key_utils.py`、`dependency_checker.py`：密钥与依赖诊断。
- `monitoring/gemini_monitoring.py`：Gemini 模型监控与采样诊断。
- `database/`：数据库文档与架构（MongoDB/SQL Schema、迁移策略、运维手册）。

### 3.3 config（配置中心）

- `agent_roles.yaml`、`model_roles.yaml`、`role_library.json`：角色能力定义（谁负责做什么）与模型映射。
- `multi_model_config.yaml`：多模型协作策略、优先级、Fallback 链路与成本/性能权衡。
- `charting_config.yaml`：图表模板与主题；`templates/`：报告/邮件等模板。
- `models.json`：模型清单；`pricing.json`：成本/价格配置；`settings.json`：UI 及系统设置。
- `logging.toml`、`logging_docker.toml`：日志配置。

### 3.4 scripts（脚本与运维）

- 启动与编排：`smart_start.sh/.ps1`、`start_docker.sh/.ps1`、`deploy.sh`、`deploy_multi_model.py`。
- 诊断与修复：`fix_chromadb*.ps1/.sh`（Win10 ChromaDB 修复）、`check_api_config.py`、`validation/*`、`maintenance/*`。
- 数据库：`mongo-init.js`、`db_migration.py`、`db_validation.py`、`setup/*`、`migrations/`。
- 日志与工具：`get_container_logs.py`、`view_logs.py`、`log_analyzer.py`。


## 四、部署与运行

### 4.1 Docker（推荐）

1) 复制配置：`cp .env.example .env`，填入至少一个 LLM 密钥（推荐：DeepSeek 或 Gemini），以及 `FINNHUB_API_KEY`、`TUSHARE_TOKEN`（可选但推荐）。
2) 启动：`docker-compose up -d --build`。
3) 访问：Web `http://localhost:8501`；API 健康检查 `http://localhost:8000/health`。

`docker-compose.yml` 主要服务：

- `web`：Streamlit 前端（端口 8501），挂载代码与配置，依赖 `mongodb`、`redis`、`api`。
- `api`：FastAPI 后端（端口 8000），提供 `/api/charts/*` 与市场数据接口。
- `mongodb`：MongoDB 存储（端口 27017，用户名 `admin`，密码 `tradingagents123`）。
- `redis`：Redis 缓存（容器内 6379，设置密码）。
- `mongo-express`（8082）：MongoDB 管理界面（可选，通过 `profiles: [management]` 启用）。
- `redis-commander`：Redis 管理界面（默认未暴露端口，如需可自行打开）。
- `scheduler`：邮件/任务调度（通过 `profiles: [scheduler]` 启用）。

内置环境变量要点（节选）：

- 多模型：`MULTI_MODEL_ENABLED=true`，`ROUTING_STRATEGY=intelligent`，`DEFAULT_COLLABORATION_MODE=sequential`。
- LLM 密钥：`DEEPSEEK_API_KEY`、`GEMINI_API_KEY`（别名兼容 `GOOGLE_AI_API_KEY`/`GOOGLE_API_KEY`）、`OPENROUTER_API_KEY`、`SILICONFLOW_API_KEY`。
- 数据源：`TUSHARE_TOKEN`、`FINNHUB_API_KEY`，`DEFAULT_CHINA_DATA_SOURCE`（akshare/tushare/baostock）。
- 图表：`CHARTING_ARTIST_ENABLED=true`，`CHARTING_ARTIST_API_URL=http://api:8000/api`。
- 存储：`TRADINGAGENTS_MONGODB_URL`、`TRADINGAGENTS_REDIS_URL`；同时在 Web 容器里还设置了 `REDIS_ENABLED=true` 等。

### 4.2 本地运行

1) 升级 pip：`python -m pip install --upgrade pip`
2) 安装依赖：`pip install -e .`
3) 启动应用：`python start_web.py` → 访问 `http://localhost:8501`

如需本地启用 API，可直接运行：

```bash
uvicorn tradingagents.api.main:app --host 0.0.0.0 --port 8000
```


## 五、核心功能与工作流

### 5.1 分析工作流（单模型）

1) 在 Web 侧边栏选择 LLM 提供商与模型；
2) 输入股票（示例：A股 `000001`、美股 `AAPL`、港股 `0700.HK`）；
3) 点击“开始分析”，观察实时进度与阶段说明；
4) 查看结论与可视化，必要时导出报告（Markdown/Word/PDF）。

### 5.2 多模型协作

- 配置：在 Web 顶部/侧栏启用“多模型协作”，选择路由策略与协作模式（顺序/并行/辩论）。
- 机制：`core/multi_model_manager.py` + `core/smart_routing_engine.py` 根据成本/质量/历史表现对模型进行智能分配与降级。
- 错误处理：`core/user_friendly_error_handler.py` 将底层错误转化为友好提示并记录。

### 5.3 图表与可视化（ChartingArtist）

- API 路径：`/api/charts/*`（`tradingagents/api/charting_endpoints.py`）。
- 前端组件：`web/components/enhanced_visualization_tab.py`，支持生成、查询、删除与批量操作。
- 图表类型：K线、折线、柱状、饼图、散点、热力、雷达、仪表盘、箱线、瀑布等。

### 5.4 新闻与情绪

- 统一工具：`tools/unified_news_tool.py`，跨多个源聚合新闻。
- 过滤增强：`utils/enhanced_news_filter.py` 与三层过滤机制（基础/增强/集成）。


## 六、配置指南（关键选项）

复制 `.env.example` 为 `.env` 后，建议至少配置：

- LLM：`DEEPSEEK_API_KEY` 或 `GEMINI_API_KEY`（也兼容 `GOOGLE_AI_API_KEY`/`GOOGLE_API_KEY`）。
- 数据：`FINNHUB_API_KEY`（美股）、`TUSHARE_TOKEN`（A股），并设置 `DEFAULT_CHINA_DATA_SOURCE`。
- 多模型：`MULTI_MODEL_ENABLED=true`、`ROUTING_STRATEGY=intelligent`、`MAX_COST_PER_SESSION=1.0`。
- 存储：生产建议启用 `MONGODB_ENABLED=true`、`REDIS_ENABLED=true` 并正确设置连接。
- 图表（可选）：`CHARTING_ARTIST_ENABLED=true`，若本地 API 则 `CHARTING_ARTIST_API_URL=http://localhost:8000/api`。

更细的角色/模型绑定与价格控制，请查看 `config/agent_roles.yaml`、`model_roles.yaml`、`multi_model_config.yaml`、`pricing.json`。


## 七、API 概览（后端）

- 健康检查：`GET /health`
- 图表：
  - `POST /api/charts/generate` 生成图表（同步/异步）
  - `GET /api/charts/{analysis_id}` 查询分析的图表列表
  - `GET /api/charts/chart/{chart_id}` 获取或 `DELETE` 删除图表
  - `GET /api/charts/list` 列表页；`POST /api/charts/batch` 批量操作
- 市场数据：详见 `tradingagents/api/market_data_endpoints.py` 与前端 `web/modules/*` 的调用。


## 八、扩展与二开

- 新增模型提供商：在 `tradingagents/llm_adapters/` 增加适配器（继承 `openai_compatible_base.py`），或新增 `api/*_client.py` 客户端；在 `config/models.json` 与 `config/multi_model_config.yaml` 配置即可接入协作。
- 新增分析角色：在 `tradingagents/agents/` 增加角色实现，并在 `graph/trading_graph.py` 接入；通过 `config/agent_roles.yaml` 定义角色职责与能力边界。
- 新增图表模板：扩展 `config/charting_config.yaml` 与 `tools/charting_tools.py`，前端组件可自动识别模板类型。
- 工作流定制：在 `graph/multi_model_extension.py` 与 `core/*` 中调整策略、路由与后处理；或在 `web/components/*` 添加新页签与表单。


## 九、常见问题与排错

- Windows 10 ChromaDB 冲突：如遇 “An instance of Chroma already exists...” 等，参考 `scripts/fix_chromadb_win10.ps1` 或在 `.env` 中设置 `MEMORY_ENABLED=false`。
- Charting API 404：确认前端请求路径为 `/api/charts/chart/{chart_id}`（单图），并检查 `CHARTING_ARTIST_API_URL` 指向 `/api` 前缀。
- 数据库未启动：`docker-compose ps` 检查 `mongodb/redis/api/web` 状态；端口占用请调整或释放。
- 密钥变量名：Gemini 优先读取 `GEMINI_API_KEY`（Docker Compose 已兼容 `GOOGLE_AI_API_KEY/GOOGLE_API_KEY` 别名）。
- 网络 DNS：Compose 已设置 `8.8.8.8 / 1.1.1.1 / 114.114.114.114`，若外网不通可替换为企业 DNS。


## 十、安全与合规

- `.env` 包含敏感密钥，请勿提交至版本库；已通过 `.gitignore` 排除。
- 仅用于技术研究与教学演示，不构成投资建议。请遵循目标市场与数据源的许可与合规要求。


## 十一、参考与后续路线

- 参考 `README.md` 获取更详细的使用教程与端到端案例。
- 进阶能力（RAG 问答、Analyst-Pro 专业统计分析、协同治理）详见根目录 `升级.md`，包含知识库检索、事件研究、仲裁与反馈学习等扩展蓝图。

—— 完 ———

