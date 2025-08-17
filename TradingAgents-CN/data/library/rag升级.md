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

明白了——你要做的是\*\*“事后”问答\*\*：你（或团队）已经完成了分析，形成了报告/复盘/研报等文档，把它们沉淀成知识库；随后一个智能助手**只基于这些分析文档**用 RAG 回答问题。下面给你一份**专为“报告即知识库”的 RAG 方案**，强调可验证性、时间有效性、冲突处理与可运维性，并对齐你现有的接口与代码骨架（Chroma + FinancialRAGSystem + FastAPI/Streamlit）。

---

## 为什么“报告型 RAG”跟普通 RAG 不一样

* **必须“可归因”**：答案需要能被**报告里的具体段落/图表**核验（Attributable to Identified Sources, AIS），而不是泛泛地“来自某报告”。这类“可归因”有现成评测范式和工具链（AIS/FActScore/VeriScore）。([MIT Press Direct][1], [GitHub][2], [arXiv][3], [ACL Anthology][4])
* **时间敏感**：报告中的结论**有生效时间**（as‑of date）与版本；时间错配会直接误导。近期工作把**时间感知**作为 RAG 的一等公民来做（Time‑aware RAG/MRAG/TimeR⁴）。([arXiv][5], [ACL Anthology][6])
* **可能相互矛盾**：不同报告/不同版本对同一问题可能**结论相左**，需要“冲突检测→并列呈现→给出裁决/不确定性”。社区正在把**冲突感知**作为 RAG 的关键能力建设。([arXiv][7])

---

## 方案总览（面向“报告即知识库”）

**一库两层**（强烈建议，但第二层可后做）

* **层 A：分析报告层**（你现在已有）——所有已经完成的分析、复盘、研报、内部 memo。
* **层 B：证据/原始出处层**（可选增强）——报告中引用的法规、公告、研报原文、表格数据等，用**锚点**连接至层 A 的“主张句”。这让助手能在回答里**同时给出“我们自己的结论”和“它来自哪条证据”**，并在 UI 中回溯。把这种溯源关系按 W3C **PROV‑O** 记录，后续审计/对账非常顺手。([W3C][8])

> 你现有的 Chroma + FinancialRAGSystem/知识库接口可以直接承载层 A；在层 A 的 chunk 元数据里加入“证据锚点/时间元数据”，即可渐进升级。

---

## 数据与索引（把“主张—证据—时间—版本”刻进索引）

**A. 报告解析 → 主张单元（Claim Units）**

* 将报告切成三类节点并分别入库：

  1. `claim`（**主张句**，1–3 句，含“结论/判断/数字”）；
  2. `rationale`（**理由/方法**，可多段）；
  3. `citation`（**证据锚点**：外部来源的 URL/DocID/page/段落哈希或内部表格路径）。
* 每个 `claim` 写清：`as_of_date / valid_from..to / version / author / review_status / stance（预测/观察/建议）/ risk_note`；如能抽取到**反对证据**也记录 `refutes[]`。主张级索引的好处是**更易做可归因评测（AIS/FActScore）**。([MIT Press Direct][1], [arXiv][3])

**B. 长文治理**

* 章节→段落的基础切分外，给长文再建一棵 **RAPTOR** 树（层级摘要节点单独索引），用于“全局脉络”检索；对跨报告关系/实体‑实体‑事件问题，给出一条 **GraphRAG** 支路（实体关系图 + 社群摘要）。([arXiv][9], [Microsoft GitHub][10])
* 拼接上下文时把最高相关的证据放**首/尾**，规避“Lost‑in‑the‑Middle”。([arXiv][11])

**C. 嵌入与重排（中文/多语优先）**

* 嵌入：**BGE‑M3**（多语/长文本/多粒度统一），对中文与长段表现更稳。([arXiv][12], [ACL Anthology][13])
* 重排：粗召回（dense+sparse/多查询）→ **RRF 融合** → 顶层 **Cross‑Encoder Reranker**（如 Jina Reranker v2 多语版）做最终裁决。([Jina AI][14])

> 与你文件中“相似度×时间衰减×个性化×可信度”的线性重排兼容；只是在其前面增加 RRF，在后面加一层交叉编码重排即可。

---

## 检索→生成流程（专为“事后问答”设计）

**Step 0 | 查询分类**

* `fact_lookup（查结论） / explanation（问为什么） / where_in_report（问出处） / policy&process（问流程）`；不同类别选择不同**检索 profile**（报告层/证据层/图谱层/树摘要层）。
* 若希望更省检索，可上 **Self‑RAG** 的“是否需要检索/是否采纳”反思 token（推理期自决）。([ICLR Proceedings][15])

**Step 1 | 时间约束**

* 从用户问题或领域（标的/财报期/政策生效日）推断 `time_window`，只检索**相符版本**的主张/证据；这是处理“旧结论被新事实推翻”的关键。([arXiv][5])

**Step 2 | 多路召回与融合**

* 原问句 +（可选）**HyDE** 伪文档扩展多查询；dense（BGE‑M3）+ sparse（BM25/SPLADE 可选）并行召回，**RRF 融合**后进重排。([arXiv][9])

**Step 3 | 证据选择与冲突检测**

* 用交叉编码重排挑前 k 条；在生成前跑**冲突探测**（是否同一问题的主张互相矛盾/版本冲突），必要时进入“并列回答模式”（见下）。([arXiv][7])

**Step 4 | 模板化回答（带可归因引用）**

* 输出结构建议：

  * **结论（as‑of 日期/版本）**
  * **要点**（每点后**挂主张编号**与**报告段落锚点**）
  * **若冲突**：列出互相矛盾的主张 + 它们的版本/时间 + 我们的处置（偏好/弃权/待核实）
  * **来源**：报告及（可选）原始证据清单（PROV 路径）。
* 模板可以被 AIS/FActScore 线下验证，利于回归评测。([MIT Press Direct][1], [arXiv][3])

---

## 冲突与不确定性的“并列呈现”策略

* **场景**：同一问题 A 报告（2024Q4）与 B 报告（2025H1）结论不一致。
* **做法**：

  1. **并列列出**相冲突主张（含 `as_of` / `version`）；
  2. 标注**证据强度**（来源数量/新鲜度/引用一致性）；
  3. 给出**系统偏好/默认规则**（如“优先最新版本/优先正式发布而非草案/优先经复核文档”）；
  4. 置信度低时**选择性回答**（abstain）并**回退到“仅列证据”**，避免误导。
* 该路线与近年的“**冲突感知 RAG**/多代理裁决”方向一致，能有效减少在现实数据中的误判。([arXiv][7])

---

## 评测与度量（让“可归因”与“时间正确”可量化）

在 `/api/kb/query` 回传 `eval_meta` 并做离线回放：

* **可归因性**：AIS 分数（是否所有主张能在引用中找到证据），**FActScore/VeriScore** 的原子事实覆盖率。([MIT Press Direct][1], [arXiv][3], [ACL Anthology][4])
* **时间一致性**：命中文档与回答 `as_of` 的一致率、时间窗越界率。([arXiv][5])
* **冲突处理质量**：冲突检测召回/精确率，**并列回答**触发率与用户接受度。([arXiv][16])
* **长上下文鲁棒性**：证据相对位置与答题正确率关系，用“Lost‑in‑the‑Middle”协议评测拼接策略。([arXiv][11])

---

## 安全与合规（只回答“报告里说过的”）

* 在检索→生成链路两端接**Guardrails**：输入注入检测、输出事实核对（仅允许引用证据中的信息）、敏感信息屏蔽、免责声明（“不构成投资建议”）。可直接复用 **NVIDIA NeMo Guardrails** 的 RAG/Fact‑Checking rails；安全风险遵循 **OWASP LLM Top‑10**。([NVIDIA Docs][17], [OWASP Foundation][18])

---

## 与你现有实现如何对齐（最小改动版）

> 下面这几个字段与接口，直接**增量**落在你文件里描述的 API 与类上，保持向下兼容。

**1) 文库摄取（新增/增强）**
`ingest_library()` 解析报告→抽取 `claim / rationale / citation` 三类节点→写入 Chroma；每条 chunk 元数据新增：

```json
{
  "node_type": "claim|rationale|citation",
  "as_of_date": "2025-06-30",
  "version": "v3.2",
  "prov": {"wasDerivedFrom": ["doc://source/…#p12", "url://…"]},
  "review_status": "reviewed|draft",
  "risk_note": "...",
  "symbol": "XYZ",
  "tags": ["fundamental","earnings"]
}
```

（PROV 只需以 JSON 记录“来源/生成活动/责任主体”等核心关系即可，格式之后再演进到 RDF/PROV‑O。([W3C][8])）

**2) 查询接口（兼容扩展）**
`POST /api/kb/query` 新增可选字段：

```json
{
  "query_text": "XYZ 的 2025Q2 指引是什么？",
  "intent": "fact_lookup|explanation|where_in_report|policy",
  "time_window": {"start": "2025-01-01", "end": "2025-08-01"},
  "retriever_profile": "report|graph|raptor|auto",
  "reranker": {"provider":"jina", "top_k":50},
  "return_mode": "answer|evidence_only|both"
}
```

服务端顺序：多路召回 + RRF → 交叉编码重排 → 冲突检测 → 模板化回答 → 附 `eval_meta`/`as_of`/`version`。([Jina AI][14])&#x20;

**3) 前端展示**

* 在答案卡片上固定展示：**结论 + as‑of/版本 + 证据清单**；冲突时出现“**并列观点**”区域。
* 来源点击直达**报告页锚点**；可再加“原始证据（可选）”跳转。

---

## 工程要点 Checklist（按风险与收益排序）

1. **主张级索引**（claim/rationale/citation + as\_of/version）与**首/尾优先拼接**（避开中间遗忘）。([arXiv][11])
2. **时间感知检索**：查询→时间窗推断→过滤→时间一致性打分。([arXiv][5])
3. **多路召回 + RRF + 交叉编码重排**（BGE‑M3 + Jina Reranker v2，多语稳）。([arXiv][12], [Jina AI][14])
4. **冲突检测→并列回答**（必要时 `abstain` 并只列证据）。([arXiv][7])
5. **可归因评测管道**（离线 AIS/FActScore/VeriScore；在线回传 eval\_meta）。([MIT Press Direct][1], [arXiv][3], [ACL Anthology][4])
6. **Guardrails**（注入/PII/事实核对 + OWASP LLM Top‑10 对照清单）。([NVIDIA Docs][19], [OWASP Foundation][18])
7. **（可选进阶）RAPTOR/GraphRAG** 支路处理“综述类/跨文档/多跳”问题。([arXiv][9], [Microsoft GitHub][10])

---

## 典型问答模版（可直接用）

> **问**：*我们对 XYZ 的 2025Q2 毛利率展望？*
> **答（as‑of 2025‑06‑30，版本 v3.2）**
>
> 1. **结论**：预计 2025Q2 毛利率 **38%–40%（中枢 39%）**。〔**R‑2025‑H1‑复盘** §3.2 主张 C‑17〕
> 2. **理由**：原材料 ASP 下行、产能利用率回升，费用率持平。〔同上 §3.2 理由 R‑17〕
> 3. **冲突信息**：**R‑2025‑Q1‑前瞻**（v2.1，as‑of 2025‑03‑31）给出 36%–38%，**已被 v3.2 更新覆盖**。
>    **来源**：
>    – R‑2025‑H1‑复盘 v3.2（as‑of 2025‑06‑30） §3.2 C‑17；
>    – R‑2025‑Q1‑前瞻 v2.1（as‑of 2025‑03‑31） §2.4 C‑08。
>    **备注**：上述结论仅反映**报告期内**判断，不构成投资建议。

---

## 参考依据（选摘）

* **Self‑RAG**：推理期自决“是否检索/是否采纳”，提升事实性与引用准确率。([arXiv][20], [ICLR Proceedings][15])
* **RAPTOR/GraphRAG**：层级摘要与图谱检索，适合长报告与跨文档关系。([arXiv][9], [Microsoft GitHub][10])
* **长上下文位置偏置**：证据放首/尾更稳。([arXiv][11])
* **时间感知 RAG**：问题分解出时间约束后检索/重排显著更准。([arXiv][5])
* **冲突感知 RAG**：对矛盾证据并列呈现/裁决。([arXiv][7])
* **可归因评测**：AIS/FActScore/VeriScore。([MIT Press Direct][1], [arXiv][3], [ACL Anthology][4])
* **嵌入与重排（中文/多语）**：BGE‑M3 与 Jina Reranker v2。([arXiv][12], [Jina AI][14])
* **溯源标准**：W3C PROV‑O。([W3C][8])

---

### 与你现有文档的锚点

* 直接复用你在《RAG 升级方案（兼容版）》里定义的 **Chroma 持久化、API `/api/kb/query`、统计与 UI**，只是把**主张级元数据/时间窗/并列冲突展示**加进去；无须破坏现有回退与 Windows/离线兼容策略。

如果你愿意，我可以把**主张级索引 + 时间感知检索 + 并列回答模板**的最小补丁（接口 JSON + 伪代码）直接写到你现有的 `financial_rag.py` 与 `knowledge_endpoints.py` 的对应位置，保证与当前开关兼容。

[1]: https://direct.mit.edu/coli/article/49/4/777/116438/Measuring-Attribution-in-Natural-Language?utm_source=chatgpt.com "Measuring Attribution in Natural Language Generation Models"
[2]: https://github.com/google-research-datasets/AIS?utm_source=chatgpt.com "AIS: Attributable to Identified Sources - GitHub"
[3]: https://arxiv.org/abs/2305.14251?utm_source=chatgpt.com "FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation"
[4]: https://aclanthology.org/2024.findings-emnlp.552/?utm_source=chatgpt.com "VeriScore: Evaluating the factuality of verifiable claims in long-form ..."
[5]: https://arxiv.org/html/2401.13222v2?utm_source=chatgpt.com "It’s About Time: Incorporating Temporality in Retrieval Augmented ..."
[6]: https://aclanthology.org/2024.emnlp-main.394/?utm_source=chatgpt.com "TimeR4 : Time-aware Retrieval-Augmented Large Language Models for ..."
[7]: https://arxiv.org/abs/2504.13079?utm_source=chatgpt.com "Retrieval-Augmented Generation with Conflicting Evidence"
[8]: https://www.w3.org/TR/prov-o/?utm_source=chatgpt.com "PROV-O: The PROV Ontology - World Wide Web Consortium (W3C)"
[9]: https://arxiv.org/html/2401.18059v1?utm_source=chatgpt.com "RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval"
[10]: https://microsoft.github.io/graphrag/?utm_source=chatgpt.com "Welcome - GraphRAG"
[11]: https://arxiv.org/abs/2307.03172?utm_source=chatgpt.com "Lost in the Middle: How Language Models Use Long Contexts"
[12]: https://arxiv.org/abs/2402.03216?utm_source=chatgpt.com "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation"
[13]: https://aclanthology.org/2024.findings-acl.137/?utm_source=chatgpt.com "M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity ..."
[14]: https://jina.ai/reranker/?utm_source=chatgpt.com "Reranker API - Jina"
[15]: https://proceedings.iclr.cc/paper_files/paper/2024/file/25f7be9694d7b32d5cc670927b8091e1-Paper-Conference.pdf?utm_source=chatgpt.com "SELF RAG: LEARNING TO RETRIEVE, GENERATE AND CRITIQUE THROUGH SELF ..."
[16]: https://arxiv.org/html/2504.00180v1?utm_source=chatgpt.com "Contradiction Detection in RAG Systems: Evaluating LLMs as Context ..."
[17]: https://docs.nvidia.com/nemo/guardrails/latest/getting-started/7-rag/README.html?utm_source=chatgpt.com "Retrieval-Augmented Generation — NVIDIA NeMo Guardrails"
[18]: https://owasp.org/www-project-top-10-for-large-language-model-applications/?utm_source=chatgpt.com "OWASP Top 10 for Large Language Model Applications"
[19]: https://docs.nvidia.com/nemo-guardrails/index.html?utm_source=chatgpt.com "NVIDIA NeMo Guardrails - NVIDIA Docs"
[20]: https://arxiv.org/abs/2310.11511?utm_source=chatgpt.com "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection"
