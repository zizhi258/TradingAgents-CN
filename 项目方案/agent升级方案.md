# Agent 视角升级方案（兼容版，贴合当前仓库）

本文面向 TradingAgents-CN 的现状，针对“多智能体协作/辩论（Debate）与裁决（CDO）”流程提出兼容升级方案。目标是在不侵入底层路由/成本/熔断逻辑（`MultiModelManager / SmartRoutingEngine`）的前提下，增强推理可靠性、证据支撑、投票聚合、公平裁决与可观测性。

对齐现状：
- 已存在“看涨/看跌研究员”与“风险辩论”状态：`investment_debate_state`（字段：`history`、`bear_history`、`bull_history`、`current_response`、`count`、可能的 `judge_decision`）与 `risk_debate_state`（`history`、`risky_history`、`safe_history`、`neutral_history`、`current_*_response`、`count`）。
- 首席决策官 CDO：`tradingagents/agents/specialized/chief_decision_officer.py` 负责综合仲裁，输出 `final_decision / decision_confidence / metrics`。
- 多模型编排：`AIOrchestrator` 与 `MultiModelManager` 已具备路由/缓存/成本约束。本文仅在“协作/辩论层”增强，保持 API 契约与调用路径不变。

为兼容：新增字段一律“可选输出/可选入”，新增 .env Feature Flag 默认关闭；旧客户端/旧流程可无感运行。

---

## TL;DR（优先级 Top 7）

1) 把“辩论”升级为“带证据的行动-推理回路（ReAct）”
- 为什么：纯口头几轮易流于“拼措辞”。ReAct 将 Thought→Action→Observation 串联，要求事实性主张必须触发检索/工具调用并附引用。
- 怎么落地：
  - 在各轮提示注入（如研究员节点与风险辩手节点的系统提示）追加“若提出事实性主张，必须执行 TOOL（search/retrieve/code-run）并在发言中带 cite”。
  - 在 `investment_debate_state`/`risk_debate_state` 的轮次记录中追加可选字段 `tool_calls: [{tool, args, observation, citations}]`（仅当启用时写入）。
  - 生成“亮点”时仅采样带引用的片段，减少噪点。
- 监控：每轮“有证据主张占比”“无引用主张比率”“跨源引用占比”。

2) 引入“自一致性加权投票（Self‑Consistency Weighted）”
- 为什么：对开放生成/复杂推理更稳健。
- 怎么落地：
  - 每位 agent 在内部对同一问题采样 k 条思路，计算 `consistency_score`（主张一致率/互证比例）。
  - 在终局 `final_votes` 外增记 `vote_weights[agent]=consistency_score`，裁决或聚合时按权重计票。
- 监控：一致性与准确度相关性、误判下降幅度。

3) 裁决器去偏（LLM‑as‑Judge 位置偏置缓解）
- 为什么：研究表明评审存在显著位置偏置与不稳定性。
- 怎么落地：
  - 新增 `judge_protocol`：{"swap_order": true, "anonymize": true, "judges": ["..."]}。
  - 裁决时对候选顺序做两次随机交换分别打分取中位；隐藏身份；可引入多裁决聚合（meta‑judge）。
- 监控：顺序交换后的“裁决翻转率 position_flip_rate”。

4) 票制从“二元表态”升级为“排序/成对胜出”（Borda/Condorcet‑Kemeny）
- 为什么：当候选/维度较多时，排序聚合更稳定，避免 51/49 掩盖强证据少数。
- 怎么落地：
  - 增加 `round_ranking[round][agent]=[...rank]` 可选埋点。
  - 终局 `vote_results.method = borda|kemeny`；优先 Borda（快），需要高精度时近似 Kemeny。
- 监控：Borda/Kemeny 下的最终一致性与准确度提升。

5) 允许“提前收敛 + 弃权/上诉”
- 为什么：非所有议题都需打满回合，且“不确定时少答更安全”。
- 怎么落地：
  - 计算投票熵/置信度变化率，达阈值早停；
  - 允许 `final_votes[agent] = "abstain"`；弃权率过高时触发上诉：`synthesis_metadata.escalation = more_compute|CDO`（如多采样或交 CDO 二次裁决）。
- 监控：提前收敛比例、弃权率与最终质量的关系。

6) 研究上下文升级为 GraphRAG / RAPTOR 管线
- 为什么：Vector‑RAG 面对长文/跨文献易丢全局；GraphRAG（图谱/社群摘要）或 RAPTOR（树状层级摘要）在复杂问答更稳。
- 怎么落地：
  - 在“研究上下文构建阶段”（现由 `market_report/news_report/fundamentals_report` 汇总）替换为 GraphRAG/RAPTOR 产物；
  - 在辩论注入的“前序摘要”里加入 `evidence_map`（关键实体/关系/来源）。
- 监控：复杂问题上的召回多样性、答案引用覆盖率、人工评估得分。

7) 持续化“反思-记忆-复用”闭环（Reflexion + MemGPT + STaR/V‑STaR）
- 为什么：不改参数，仅靠“语言反思+分层记忆+小型验证器”即可持续提升。
- 怎么落地：
  - 每轮后将“犯错→改进要点”写入 `experience_store`（可借 `tradingagents/agents/utils/memory.py` + Chroma/Mongo），下次作为隐式提示注入；
  - 在会话外维护 `core/recall/archive` 三层记忆（MemGPT 思想），`_inject_*_context` 时按需取回；
  - 离线从 `debate_state.history` 抽取“正例链路”，训练一个轻量 verifier，上线时作为附加打分器参与加权。
- 监控：复用记忆命中率、复用后质量提升、验证器与 CDO 一致度。

---

## 与现有方案的对齐点（不改动锚点与契约）
- 继续使用并扩展：`investment_debate_state / risk_debate_state`；新增字段全部“可选”。
- 继续维持：CDO 兜底仲裁；在 `synthesis_metadata.reason` 中保留 `tie_breaker` 等原因标记。
- 继续沿用：多模型路由与成本控制；新增计算（如自一致性采样）通过 Feature Flag 控制，默认关闭。

---

## A. 赛制与流程

### A1. 发言即行动（ReAct 写入辩论协议）
- 为什么：用工具与检索约束空口辩论，提升可验证性。
- 怎么落地：
  - 在研究员与风险辩手节点的提示模板中加入“若提出事实性主张 → 触发 TOOL 并附 cite”。
  - `state` 中按轮附 `tool_calls`（当启用）并在“亮点抽取”仅使用带引用内容。
- 监控：`evidence_backed_speeches_ratio`、`claim_without_citation_ratio`、`cross_source_citation_ratio`。

### A2. 交叉质询 + 预承诺
- 为什么：通过拆穿错误更接近真相。
- 怎么落地：在每轮注入 `cross_question` 槽位；下一位必须优先回应上轮质询并给证据。
- 监控：`qa_coverage_ratio`、`retracted_claims_count`。

### A3. 动态轮次与提前收敛
- 为什么：节省成本、加快收敛。
- 怎么落地：计算 `vote_entropy`/`confidence_slope` 达阈值即早停；平票或高不确定性走 CDO 回退（已有）。
- 监控：`early_stop_ratio`、`avg_rounds_to_converge`。

### A4. 裁决器去偏：顺序随机化 + 匿名化 + 多裁决聚合
- 为什么：缓解位置偏置与不稳定。
- 怎么落地：
  - `judge_protocol = {swap_order, anonymize, judges}`；
  - 随机交换顺序两次评分，取中位；可多裁决融合（meta‑judge）。
- 监控：`position_flip_rate`、`inter_judge_agreement`（kappa）。

---

## B. 票制与置信度

### B1. 自一致性加权投票（SC‑Weighted）
- 为什么：提升自由生成任务鲁棒性。
- 怎么落地：agent 内部采样 k 条思路→计算 `consistency_score`→`vote_weights[agent] = score`→终局加权计票。
- 监控：一致性‑准确度相关性、误判下降幅度。

### B2. 从表态到排序（Borda/Kemeny）
- 为什么：多候选/多维评分更稳健。
- 怎么落地：`round_ranking[...]` 可选埋点；`vote_results.method=borda|kemeny` 并输出聚合结果。
- 监控：聚合稳定度、与人工评估的一致性。

### B3. Abstain/Defer（选择性回答）+ 上诉 CDO/加算力
- 为什么：少答但更准，整体更安全。
- 怎么落地：允许 `final_votes[agent]="abstain"`；高弃权→`synthesis_metadata.escalation=more_compute|CDO`。
- 监控：弃权率与最终质量/时延/成本的关系。

---

## C. 研究与检索

### C1. GraphRAG / RAPTOR 替换“综合研究上下文”
- 为什么：复杂/长文场景显著提升稳定性与覆盖度。
- 怎么落地：以 `tradingagents/ai/financial_rag.py` 为底座，替换“综合研究上下文”构建；保留原接口签名，新增 `pipeline` 入参或从 `.env` 读取 `RAG_PIPELINE`。
- 监控：复杂问题的准确率、引用覆盖率、用户满意度。

### C2. Self‑RAG / HyDE 强化召回
- 为什么：证据不足时能二次检索，减少“臆断”。
- 怎么落地：当检测到“证据不足”主张 → 触发 HyDE（生成假设文档→召回→对齐）；在 `tool_calls` 记录此二次检索。
- 监控：二次检索触发率、纠错成功率。

---

## D. 记忆与自我改进

### D1. Reflexion（语言反思）→ 经验记忆
- 为什么：无需改权重即可提升后续表现。
- 怎么落地：把“犯错→改进要点”写入 `experience_store`（可用 Chroma/Mongo），下次作为隐式指令注入。
- 监控：记忆命中率、随时间的质量提升曲线。

### D2. MemGPT（分层记忆）
- 为什么：跨会话/长上下文保持一致性。
- 怎么落地：维护 `core/recall/archive` 三层；注入阶段按需分页加载。
- 监控：记忆读写延迟、溢出率、相关性评分。

### D3. STaR/V‑STaR 训练验证器
- 为什么：将正确推理链蒸馏为 verifier，稳定裁决质量。
- 怎么落地：离线从 `*_debate_state.history` 抽正例链训练轻量判别器，上线时参与加权。
- 监控：verifier‑CDO 一致性、误判率变化。

---

## E. 团队编排与路由

### E1. 动态挑选上场 Agent（AutoGen 思想）
- 为什么：并非所有问题都需全员出场，更省钱更准。
- 怎么落地：回合 0 做“开场路由”，基于问题类型/证据可得性只挑 2–3 名最相关角色入场，其余转“离线顾问”。
- 监控：有效参与人数、单位成本准确度。

---

## F. 观测与评测
- 公平性：顺序交换后裁决翻转率（`position_flip_rate`）应下降。
- 证据质量：有证据主张占比、跨源引用占比。
- 收敛性：投票熵下降曲线、提前收敛占比。
- 可解释性：`battle_highlights` 的证据覆盖率（亮点必须有关联 `tool_calls.citations`）。
- 兼容集成：指标可作为 `debate.metrics.*` 或独立 `/api/v2/performance/metrics` 输出，不破坏现有契约。

---

## 可直接落地的字段/配置补丁（保持兼容）

新增返回字段（仅当启用相关特性时出现，默认不输出）：
```json
"debate": {
  "method": "v2",
  "judge_protocol": {"swap_order": true, "anonymize": true, "judges": ["..."]},
  "vote_method": "borda",                 
  "vote_weights": {"fundamental_expert": 0.78, "technical_analyst": 0.62},
  "abstentions": ["risk_manager"],
  "tool_calls": [{"speaker":"...", "tool":"search", "citations":["..."]}]
}
```
- 与现有 `investment_debate_state/risk_debate_state` 并列或嵌入到“每轮记录”中；旧客户端可忽略未知字段。

建议新增 .env（默认 false，确保兼容）：
```ini
DEBATE_V2_REACT_ENABLED=false
DEBATE_JUDGE_SWAP_ORDER=false
DEBATE_JUDGE_ANONYMIZE=false
DEBATE_VOTE_METHOD=binary        # binary|borda|kemeny|weighted_sc
DEBATE_ALLOW_ABSTAIN=false
DEBATE_EARLY_STOP_BY_ENTROPY=false
DEBATE_SELF_CONSISTENCY_K=0
RAG_PIPELINE=vanilla             # vanilla|graphrag|raptor
REFLEXION_MEMORY_ENABLED=false
```

---

## 与当前代码的映射（实现提示）
- 提示注入位：
  - 看涨/看跌研究员：`tradingagents/agents/researchers/bull_researcher.py`、`bear_researcher.py`（在 `prompt` 追加 ReAct/交叉质询/证据要求）。
  - 风险辩手：`tradingagents/agents/risk_mgmt/*_debator.py`。
  - CDO：`chief_decision_officer.py` 的 `analysis_prompt` 可读取 `vote_results / judge_protocol` 等元数据以生成更可解释的裁决说明。
- 状态扩展位：
  - `investment_debate_state`、`risk_debate_state` 的轮次字典中追加可选 `tool_calls / cross_question / round_ranking`；序列化保持兼容。
- RAG 升级：
  - 以 `tradingagents/ai/financial_rag.py` 为底座，替换“综合研究上下文”构建；保留原接口签名，新增 `pipeline` 入参或从 `.env` 读取 `RAG_PIPELINE`。
- 监控指标：
  - 复用 `tradingagents/monitoring` 与日志系统，在每轮记录扩展埋点；或新增 `/api/v2/performance/metrics` 只读端点聚合。

---

## 两周落地路径（不入侵底层路由/成本/熔断）

Week 1（零侵入/轻改动）
- 打开 `DEBATE_JUDGE_SWAP_ORDER/ANONYMIZE`（先在 CDO 的裁决逻辑试点），记录 `position_flip_rate` 对照实验。
- 在发言模板加入“证据必填 + cross_question”，统计“有证据主张占比”。

Week 2（轻量扩展）
- 启用 `DEBATE_VOTE_METHOD=borda`，同时输出 `vote_weights`（先置 1）。
- 开启 `DEBATE_EARLY_STOP_BY_ENTROPY`；允许 `abstain` 并定义上诉路径到 CDO。
- 在一个主题上试点 GraphRAG/RAPTOR 生成“研究上下文”，对比准确率与引用覆盖度。

以上改动均由 Feature Flag 控制，默认关闭；旧流程按原样运行，满足“务必兼容”。

---

## 参考（选摘）
- ReAct：将推理与动作结合，提升证据驱动的问答与规划。
- Self‑Consistency：多路径采样提升推理鲁棒性，可转化为投票权。
- LLM‑as‑Judge 偏置：顺序交换与匿名化可显著降低位置偏置。
- Borda/Kemeny：排序聚合在多候选整合更稳健；Kemeny 需近似求解。
- GraphRAG / RAPTOR：图谱化与层级摘要检索，改善长文/跨文档问答。
- Reflexion / MemGPT / STaR / V‑STaR：语言反思、分层记忆、自训练验证器，构成“越用越强”的闭环。

（为便于落地，已在文中给出具体的“为什么/怎么做/监控什么”，并明确了与当前代码路径的映射与埋点位置。）

