# RAG 升级方案（兼容版）

面向 TradingAgents-CN，将“图书馆”文件沉淀为可检索的知识库（向量化存储），并通过 RAG 为大模型提供个性化金融问答能力。该方案强调与现有代码与运行环境的“向下兼容、替代可选、渐进落地”。

## 目标
- 将 `data/library/`（或上传的文件）清洗、切分、嵌入，持久化到本地向量库（ChromaDB）。
- 基于金融领域与个性化画像进行过滤与加权检索，向 LLM 生成带引用的答案。
- 完全复用/扩展现有模块：`FinancialRAGSystem`、`AIOrchestrator`、`FileManager`、Streamlit/FASTAPI；保证 Windows 兼容与“无外网/无额外依赖”可降级运行。

## 架构与衔接
- 向量库与嵌入
  - 首选 ChromaDB 持久化（已在 `pyproject.toml` 依赖且多处使用），存放于 `financial_kb/chromadb/`。
  - 嵌入优先级（自动降级）：SiliconFlow（如 Qwen3-Embedding）→ OpenAI（text-embedding-3）→ 本地 Ollama（nomic-embed-text）→ SentenceTransformers（如 all-MiniLM-L6-v2）→ 哈希回退（已在 `FinancialEmbedding` 内提供）。
  - Windows 兼容：初始化 Chroma 时优先走 `tradingagents/agents/utils/chromadb_win11_config.py` 的 `get_optimal_chromadb_client()` 策略；`MEMORY_ENABLED=false` 时允许禁用向量内存以绕过旧版 Win10 兼容问题。
- RAG 主体
  - 复用 `tradingagents/ai/financial_rag.py`：`FinancialKnowledgeBase` + `FinancialRAGSystem` 已具备向量检索、召回过滤、模板化生成、统计持久化能力。
  - 扩展：新增“文库摄取/索引”方法，支持多格式文件解析、chunk 切分、元数据入库、增量更新。
- 文件与上传
  - 复用 `tradingagents/services/file_manager.py`：统一上传/落盘/元数据记录；入库索引与该服务联动。
- API 与 UI
  - FastAPI：在 `tradingagents/api/` 新增 `knowledge_endpoints.py`，提供上传、重建索引、查询、统计接口。
  - Streamlit：在 `web/` 新增“知识库管理”“个性化问答”页面，支持上传、打标、检索预览与问答引用展示。

## 文库摄取与索引（Ingestion）
- 目录约定：`data/library/`（可在 .env 自定义），按层级组织：行业/公司/主题/年份。
- 支持格式：`pdf / docx / xlsx / csv / md / html / txt`。
  - 优先使用 Pandoc（仓库已包含 `pypandoc` 与 Windows MSI 安装包），统一转 markdown/纯文本。
  - 若系统未安装 Pandoc：兼容回退，仅处理 `txt/md/csv/html(纯文本抽取)`；其余格式跳过并记录告警，不阻断流程。
- 清洗与切分
  - 标题层级 → 章节 → 段落 chunk；每 chunk 约 800–1200 字符，重叠 10–20%。表格/列表保留结构化标记。
  - 中文语料无需特殊分词，交由嵌入模型适配；必要时可引入轻量中文分句（可选）。
- 元数据（metadata）
  - 通用：`source_path, file_md5, title, doc_type(paper/manual/policy/report), tags, lang, created_at, updated_at`。
  - 金融：`symbol, sector, market, period, data_date`（从目录/文件名或内容正则提取，可为空）。
  - 个性化：`user_id/tenant_id, visibility(private/shared), portfolio_tags`。
- 去重与增量
  - `doc_id = md5(file) + section_anchor`；记录 manifest（文件哈希、切分 anchor），支持“新增/修改/删除”的精确更新。
  - 摄取完成后调用 `save_knowledge_base()` 落盘索引统计。

### 代码变更清单（最小集）
- `tradingagents/ai/financial_rag.py`
  - 新增方法：
    - `ingest_library(root_dir, default_doc_type, default_tags, user_id)`：遍历目录→解析→切分→入库→增量索引。
    - `parse_file_to_text(path)`：Pandoc/回退解析；提取标题、正文、表格为 markdown 文本。
    - `chunk_text(text, strategy=...)`：按策略生成 chunk，返回 `[FinancialDocument]`。
  - 调整 `FinancialEmbedding`：增加可注入式 provider（复用 `agents/utils/memory.py` 的 provider 选择与 API 封装），保持当前回退逻辑不变。
  - `FinancialKnowledgeBase`：支持以 `user_id/tenant_id`、`symbol/sector` 维度入库与查询过滤。
- `tradingagents/api/knowledge_endpoints.py`（新）
  - `POST /api/kb/upload`：文件上传（走 `FileManager`），可选 `tags/symbol/user_id`，后台触发摄取。
  - `POST /api/kb/reindex`：对目录/文件增量重建索引（支持 dry-run）。
  - `GET /api/kb/stats`：库规模、类型分布、嵌入/向量库状态、最近更新。
  - `POST /api/kb/query`：RAG 问答（`query_text, query_type?, symbols?, user_id?, filters?, top_k?`）。
- `web/` 新增页面
  - “知识库管理”：上传、标注、重建索引、统计可视化、错误告警预览。
  - “个性化问答”：问题输入、证券/时间/标签过滤、答案与引用展示、片段高亮与原文跳转。

## 检索与个性化（Retrieval）
- 查询预处理：意图分类（`general/technical/fundamental/news/risk`），必要时用 `AIOrchestrator` 做 Query Rewriting（可选）。
- 召回与过滤：
  - 语义召回：`top_k * 2` 粗召回；
  - 过滤：按 `user_id/tenant_id`、`symbol/sector`、`doc_type/tags`、时间窗过滤；
  - 重排：相似度×时间衰减×个性化权重×来源可信度（简单线性/学习排序后续可选）。
- 生成：使用 `FinancialRAGSystem` 现有模板（`general/technical/fundamental/news/risk`），上下文拼接+引用；UI 展示出处与片段。

## 兼容性策略
- OS/环境
  - Windows 10/11：Chroma 初始化优先 `get_optimal_chromadb_client()`；如遇 duckdb/文件锁问题，可在 `.env` 设置 `MEMORY_ENABLED=false` 暂时关闭向量内存。
  - 无外网：嵌入回退至 `SentenceTransformers` 或哈希向量；RAG 仍能工作但精度降低，UI/日志明确提示降级。
  - 依赖最小化：不新增重型依赖；优先使用现有 `pypandoc`，若系统未安装 Pandoc，则“只处理 txt/md/csv/html 纯文本”，其余格式保留任务与告警。
- 配置开关（`.env`）
  - `MEMORY_ENABLED=true|false`：全局向量存储开关；
  - 模型提供商：`SILICONFLOW_ENABLED/DEEPSEEK_ENABLED/GEMINI_API_KEY/OPENAI_*`；
  - 多模型：`MULTI_MODEL_ENABLED=true`、`ROUTING_STRATEGY=intelligent`；
  - 数据/缓存目录：`TRADINGAGENTS_DATA_DIR/TRADINGAGENTS_CACHE_DIR`（用于库与索引落盘）；
  - 可选：`MONGODB_ENABLED/REDIS_ENABLED` 不作为 RAG 硬依赖。

## API 设计（示例）
- `POST /api/kb/upload`
  - form-data：`file`, `doc_type?`, `tags?`, `symbol?`, `user_id?`, `visibility?`
  - 返回：`{file_id, queued: true}`
- `POST /api/kb/reindex`
  - json：`{root_dir?, files?, dry_run?}`
  - 返回：`{added, updated, skipped, warnings}`
- `GET /api/kb/stats`
  - 返回：`{total_documents, documents_by_type, symbols_covered, date_range, vector_db_available}`
- `POST /api/kb/query`
  - json：`{query_text, query_type?, symbols?, user_id?, filters?, top_k?}`
  - 返回：`{answer, sources[], metadata{avg_relevance, context_length, ...}}`

## UI 设计（Streamlit）
- 知识库管理
  - 文件上传、标签与可见性编辑、重建索引、统计概览、错误/降级提示。
- 个性化问答
  - 问题输入、证券/时间/标签过滤、答案与引用展示、片段高亮、原文跳转。

## 落地里程碑（MVP → 强化）
- 阶段1（MVP，1–2 天）
  - 在 `financial_rag.py` 增加 `ingest_library/parse_file_to_text/chunk_text`；
  - 新增 `POST /api/kb/reindex`、`POST /api/kb/query`；
  - 嵌入提供者接入 `agents/utils/memory.py`，保持现有回退链。
- 阶段2（个性化/可用性，2–4 天）
  - `user_id/tenant_id` 分权、`symbol/sector` 过滤；
  - Streamlit 两个页面；增量索引、统计面板。
- 阶段3（优化/评测，3–5 天）
  - Query 重写、重排器（时间/权重/新鲜度）、结构化回答模板；
  - 评测集与指标（Recall@k/MRR/人工准确性）、权限与治理。

## 测试与验收
- 单测：对切分、元数据抽取、增量索引、过滤与重排做函数级测试（若项目已有 pytest，新增至 `TradingAgents-CN/tests/`）。
- 端到端：
  - 准备 `data/library/demo/` 小样；
  - 调用 `POST /api/kb/reindex` 建库；
  - `POST /api/kb/query` 检索问答，确认引用与过滤；
  - 评测：构建 20–50 个金融问答集，统计 Recall@k/MRR；人工 spot-check。

## 运维与安全
- 定时任务：`APScheduler` 定期增量索引（夜间窗口），失败重试与告警（日志/邮件可选）。
- 备份：`data/library/` 与 `financial_kb/chromadb/` 周期备份；记录校验与恢复指引。
- 隐私与合规：文库分权（`user_id/tenant_id`）、私有/共享标签、敏感信息清洗；UI 注明“不构成投资建议”。
- 成本控制：默认使用本地/免费嵌入；有网时再启用云端嵌入，设置速率与成本阈值。

## 实施清单（Checklist）
- [ ] `financial_rag.py`：新增文库摄取/切分方法；增强嵌入提供者注入；支持个性化过滤字段。
- [ ] `api/knowledge_endpoints.py`：上传/重建/查询/统计 4 类接口。
- [ ] `web/`：知识库管理与个性化问答两页。
- [ ] `.env`：增加 `LIBRARY_ROOT`（可选）、`MEMORY_ENABLED` 文档说明；确认嵌入提供商环境变量。
- [ ] 文档：README/本文件链接与使用指引；兼容性与降级说明。

## 运行指引（本地）
- 安装：
  - `cd TradingAgents-CN && pip install -U pip && pip install -e .`
  - 建议安装 Pandoc（Windows 下仓库附带 MSI，可双击安装）。
- 启动 API：
  - `uvicorn tradingagents.api.main:app --host 0.0.0.0 --port 8000`
- 启动 Web：
  - `python start_web.py`，打开 `http://localhost:8501`
- 建库：
  - `POST /api/kb/reindex` 指向 `data/library/`；观察日志与 `financial_kb/` 生成情况。
- 问答：
  - `POST /api/kb/query` 提交问题，查看答案与引用。

---

此方案在“不改动现有核心能力”的前提下，最小代价扩展“文件→知识库→RAG问答”闭环；在没有网络或依赖缺失时均可平稳降级，满足“确保兼容”的要求。

