"""
多模型协作分析表单组件
"""

import datetime

import streamlit as st

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

"""
注意：本表单已精简为仅包含“任务信息、协作模式、研究深度、智能体选择、提交”。
多模型的模型/路由/预算等配置请前往“⚙️ 配置管理”或“🧭 角色中心”。
"""
logger = get_logger("web")


def render_multi_model_analysis_form():
    """渲染多模型协作分析表单"""

    # 页面标题与架构标识
    st.subheader("🤖 多模型协作分析 · 表单")
    st.caption(
        "仅保留必要项：任务信息 → 协作设置 → 选择智能体 → 提交。详细配置见‘⚙️ 配置管理’与‘🧭 角色中心’。"
    )

    # 架构说明（折叠显示，避免界面噪声）
    with st.expander("🧱 参考架构与建议（可选）", expanded=False):
        st.info(
            "🚀 两池旗舰模型：Gemini-2.5-Pro（深度推理） + DeepSeek-V3（长序列/技术/代码）"
        )

    # 获取缓存的表单配置（确保不为None）
    cached_config = st.session_state.get("multi_model_form_config") or {}

    # 创建表单
    with st.form("multi_model_analysis_form", clear_on_submit=False):

        # 一、任务信息
        st.markdown("### ① 任务信息")
        col1, col2 = st.columns(2)

        with col1:
            # 市场选择
            market_options = ["美股", "A股", "港股"]
            cached_market = (
                cached_config.get("market_type", "A股") if cached_config else "A股"
            )
            try:
                market_index = market_options.index(cached_market)
            except (ValueError, TypeError):
                market_index = 1  # 默认A股

            market_type = st.selectbox(
                "选择市场",
                options=market_options,
                index=market_index,
                help="选择要分析的股票市场",
            )

            # 股票代码输入
            cached_stock = (
                cached_config.get("stock_symbol", "") if cached_config else ""
            )

            if market_type == "美股":
                stock_symbol = (
                    st.text_input(
                        "股票代码",
                        value=(
                            cached_stock
                            if (
                                cached_config
                                and cached_config.get("market_type") == "美股"
                            )
                            else ""
                        ),
                        placeholder="输入美股代码，如 AAPL, TSLA, NVDA",
                        help="输入要分析的美股代码",
                        key="multi_us_stock_input",
                    )
                    .upper()
                    .strip()
                )
            elif market_type == "港股":
                stock_symbol = (
                    st.text_input(
                        "股票代码",
                        value=(
                            cached_stock
                            if (
                                cached_config
                                and cached_config.get("market_type") == "港股"
                            )
                            else ""
                        ),
                        placeholder="输入港股代码，如 0700.HK, 9988.HK",
                        help="输入要分析的港股代码",
                        key="multi_hk_stock_input",
                    )
                    .upper()
                    .strip()
                )
            else:  # A股
                stock_symbol = st.text_input(
                    "股票代码",
                    value=(
                        cached_stock
                        if (cached_config and cached_config.get("market_type") == "A股")
                        else ""
                    ),
                    placeholder="输入A股代码，如 000001, 600519",
                    help="输入要分析的A股代码",
                    key="multi_cn_stock_input",
                ).strip()

        with col2:
            # 分析日期
            analysis_date = st.date_input(
                "分析日期", value=datetime.date.today(), help="选择分析的基准日期"
            )

        # 二、分析套餐与协作
        st.markdown("---")
        st.markdown("### ② 协作设置")

        col1, col2 = st.columns(2)

        with col1:
            # 协作模式选择
            collaboration_mode = st.selectbox(
                "协作模式",
                options=["sequential", "parallel", "debate"],
                format_func=lambda x: {
                    "sequential": "📝 串行协作 - 智能体依次分析",
                    "parallel": "⚡ 并行协作 - 智能体同时分析",
                    "debate": "💬 辩论协作 - 智能体互相辩论（实验性）",
                }[x],
                index=0,
                help="选择智能体协作模式；‘辩论’当前为简化模拟流程，仍在迭代中",
            )
            if collaboration_mode == "debate":
                st.info(
                    "💡 提示：辩论模式为实验性实现，当前结果由简化流程生成，用于演示交互与共识展示。"
                )

            # 分析深度
            research_depth = st.select_slider(
                "研究深度",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: {
                    1: "1级 - 快速分析",
                    2: "2级 - 基础分析",
                    3: "3级 - 标准分析",
                    4: "4级 - 深度分析",
                    5: "5级 - 全面分析",
                }[x],
                help="选择分析的深度级别",
            )

        with col2:
            # 多模型路由/套餐已移至配置页
            st.info("模型/路由/套餐配置请到‘⚙️ 配置管理’与‘🧭 角色中心’办理")

        # 专业智能体选择 - 两池旗舰模型架构
        st.markdown("### 👥 专业智能体团队 (两池旗舰模型架构)")
        st.markdown("*智能路由将自动分配每个智能体到最适合的旗舰模型池*")

        # 添加两池架构说明
        with st.expander("🔍 查看两池旗舰模型架构"):
            st.markdown(
                """
            **🧠 通用深度推理池** - Gemini-2.5-Pro (1M tokens)
            - 首席决策官、基本面专家、风控经理、政策研究员、合规官
            
            **🔄 技术面&长序列&代码池** - DeepSeek-V3 (128K tokens) 
            - 技术分析师、快讯猎手、情绪分析师、工具工程师
            - 支持代码生成、量化回测分析
            """
            )

        # 三、选择智能体（可自定义；套餐会自动调整）
        # 获取缓存的智能体选择
        cached_agents = (
            cached_config.get(
                "selected_agents", ["news_hunter", "fundamental_expert", "risk_manager"]
            )
            if cached_config
            else ["news_hunter", "fundamental_expert", "risk_manager"]
        )

        # 动态加载角色（支持自定义）
        try:
            from tradingagents.config.provider_models import model_provider_manager

            _defs = model_provider_manager.role_definitions
            roles_config = []
            for rk, rc in _defs.items():
                if getattr(rc, "enabled", True):
                    roles_config.append(
                        (rk, rc.name or rk, rc.description or rc.name or rk)
                    )
            roles_config.sort(key=lambda x: x[1])
        except Exception:
            roles_config = [
                ("news_hunter", "📰 快讯猎手", "实时新闻收集与分析"),
                ("fundamental_expert", "💰 基本面专家", "财务数据与估值分析"),
                ("technical_analyst", "📈 技术分析师", "技术指标与图表分析"),
                ("sentiment_analyst", "💭 情绪分析师", "市场情绪与社媒分析"),
                ("risk_manager", "⚠️ 风控经理", "风险评估与管理"),
                ("compliance_officer", "📋 合规官", "合规性检查"),
                ("policy_researcher", "📋 政策研究员", "政策法规解读分析"),
                ("tool_engineer", "🔧 工具工程师", "量化工具与代码生成"),
                ("chief_decision_officer", "👔 首席决策官", "最终决策仲裁"),
            ]

        # 提示：模型目录与路由策略已在“⚙️ 配置管理/🧭 角色中心”统一管理

        # 导入配置工具
        # 角色集中配置入口已合并至“🧭 角色中心”

        # 为表单态按钮生成不可见后缀，避免重复label引起的重复key
        def _invisible_suffix(seed: str) -> str:
            try:
                count = abs(hash(seed)) % 7 + 1
            except Exception:
                count = 1
            return "\u200b" * count

        # 创建3列布局显示9个智能体
        col1, col2, col3 = st.columns(3)
        selected_agents = []

        # 分配角色到三列
        roles_per_col = len(roles_config) // 3 + (1 if len(roles_config) % 3 else 0)

        for col_idx, col in enumerate([col1, col2, col3]):
            start_idx = col_idx * roles_per_col
            end_idx = min(start_idx + roles_per_col, len(roles_config))

            with col:
                for role_key, role_label, role_desc in roles_config[start_idx:end_idx]:
                    # 创建内嵌列: checkbox + 配置按钮
                    check_col, config_col = st.columns([4, 1])

                    with check_col:
                        is_selected = st.checkbox(
                            role_label,
                            value=role_key in cached_agents,
                            key=f"agent_{role_key}",
                            help=role_desc,
                        )
                        if is_selected:
                            selected_agents.append(role_key)

                    with config_col:
                        pass

        # 显示选择摘要
        if selected_agents:
            try:
                from tradingagents.config.provider_models import model_provider_manager

                selected_names = [
                    (
                        model_provider_manager.role_definitions.get(agent).name
                        if model_provider_manager.role_definitions.get(agent)
                        else agent
                    )
                    for agent in selected_agents
                ]
            except Exception:
                selected_names = selected_agents
            st.success(
                f"✅ 已选择 {len(selected_agents)} 个智能体: {', '.join(selected_names)}"
            )
        else:
            st.warning("⚠️ 请至少选择一个智能体")

        # 已移除集中配置入口（避免与独立“🧭 角色中心”页面重复）

        # 架构指标移至上方折叠说明，避免主屏噪声

        # 显示输入状态
        if not stock_symbol:
            st.info("💡 请在上方输入股票代码")
        else:
            st.success(
                f"✅ 已配置多模型协作分析: {stock_symbol} ({len(selected_agents)}个智能体)"
            )

        # 保存当前配置
        current_config = {
            "stock_symbol": stock_symbol,
            "market_type": market_type,
            "analysis_date": str(analysis_date),
            "analysis_mode": "multi_model",  # 固定为多模型
            "collaboration_mode": collaboration_mode,
            "research_depth": research_depth,
            "selected_agents": selected_agents,
        }

        # 自动保存配置
        if current_config != cached_config:
            st.session_state.multi_model_form_config = current_config

        # 六、提交
        submitted = st.form_submit_button(
            "🚀 开始多模型协作分析", type="primary", use_container_width=True
        )

    # 返回表单数据
    if submitted and stock_symbol and selected_agents:
        form_data = {
            "submitted": True,
            "stock_symbol": stock_symbol,
            "market_type": market_type,
            "analysis_date": str(analysis_date),
            "analysis_mode": "multi_model",  # 固定为多模型
            "collaboration_mode": collaboration_mode,
            "research_depth": research_depth,
            "selected_agents": selected_agents,
        }

        logger.info(f"🤖 [多模型表单] 提交数据: {form_data}")
        return form_data

    elif submitted:
        # 验证失败
        if not stock_symbol:
            st.error("❌ 请输入股票代码")
        if not selected_agents:
            st.error("❌ 请至少选择一个智能体/分析师")
        return {"submitted": False}

    else:
        return {"submitted": False}


def render_multi_model_progress_display(analysis_id: str):
    """渲染多模型协作分析进度显示"""

    st.markdown("### 📊 多模型协作分析进度")

    # 检查是否有多模型扩展
    try:
        from tradingagents.graph.multi_model_extension import get_multi_model_progress

        # 获取进度数据
        progress_data = get_multi_model_progress(analysis_id)

        if progress_data:
            # 显示总体进度
            total_progress = progress_data.get("total_progress", 0)
            st.progress(total_progress / 100)
            st.write(f"总体进度: {total_progress}%")

            # 显示各智能体状态
            agents_status = progress_data.get("agents_status", {})

            if agents_status:
                st.markdown("#### 🤖 智能体状态")

                cols = st.columns(3)
                agent_names = {
                    "news_hunter": "📰 快讯猎手",
                    "fundamental_expert": "💰 基本面专家",
                    "technical_analyst": "📈 技术分析师",
                    "sentiment_analyst": "💭 情绪分析师",
                    "policy_researcher": "📋 政策研究员",
                    "tool_engineer": "🔧 工具工程师",
                    "risk_manager": "⚠️ 风控经理",
                    "compliance_officer": "📋 合规官",
                    "chief_decision_officer": "👔 首席决策官",
                }

                for i, (agent_id, status) in enumerate(agents_status.items()):
                    col = cols[i % 3]
                    with col:
                        agent_name = agent_names.get(agent_id, agent_id)

                        if status == "completed":
                            st.success(f"{agent_name}: ✅ 完成")
                        elif status == "running":
                            st.info(f"{agent_name}: 🔄 分析中")
                        elif status == "failed":
                            st.error(f"{agent_name}: ❌ 失败")
                        else:
                            st.warning(f"{agent_name}: ⏳ 等待中")

            # 显示成本信息
            cost_info = progress_data.get("cost_info", {})
            if cost_info:
                st.markdown("#### 💰 成本统计")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("总成本", f"${cost_info.get('total_cost', 0):.4f}")
                with col2:
                    st.metric("Token消耗", f"{cost_info.get('total_tokens', 0):,}")
                with col3:
                    st.metric("API调用次数", cost_info.get("api_calls", 0))

            # 显示协作模式信息
            collaboration_info = progress_data.get("collaboration_info", {})
            if collaboration_info:
                st.markdown("#### 🔄 协作信息")
                st.info(f"协作模式: {collaboration_info.get('mode', 'Unknown')}")

                if "routing_decisions" in collaboration_info:
                    with st.expander("🧠 智能路由决策"):
                        for decision in collaboration_info["routing_decisions"]:
                            st.write(f"• {decision}")

        else:
            st.warning("⚠️ 无法获取多模型分析进度")

    except ImportError:
        st.error("❌ 多模型协作功能未正确安装")
    except Exception as e:
        st.error(f"❌ 进度显示错误: {e}")


# ---------------------------------------------------------------------------
# 统一增强：覆写 render_multi_model_analysis_form，复用增强版配置面板
# ---------------------------------------------------------------------------
def render_multi_model_analysis_form():
    """渲染多模型协作分析表单（统一到增强版面板）。

    返回值与现有 app 集成保持一致：
    { submitted, stock_symbol, market_type, analysis_date, collaboration_mode,
      research_depth, selected_agents }
    """
    import streamlit as st  # local import to keep compatibility

    try:
        from .enhanced_multi_model_analysis_form import (
            render_compact_multi_model_config_panel,
        )
    except Exception:
        # 回退到旧实现（上方原函数定义）
        return {"submitted": False}

    st.subheader("🤖 多模型协作分析 · 配置（增强版）")
    st.caption("统一面板：基础信息｜模型与提供商｜协作与智能体｜路由与预算｜高级设置")

    cached_config = st.session_state.get("multi_model_form_config") or {}

    with st.form("multi_model_analysis_form", clear_on_submit=False):
        full_cfg = render_compact_multi_model_config_panel(cached_config)
        st.markdown("---")
        submitted = st.form_submit_button(
            "🚀 开始多模型协作分析",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return {"submitted": False}

    stock_symbol = (full_cfg.get("stock_symbol") or "").strip()
    selected_agents = list(full_cfg.get("selected_agents") or [])

    if not stock_symbol:
        st.error("❌ 请输入股票代码")
        return {"submitted": False}
    if not selected_agents:
        st.error("❌ 请至少选择一个智能体/分析师")
        return {"submitted": False}

    # 缓存最近一次配置
    try:
        st.session_state.multi_model_form_config = full_cfg
    except Exception:
        pass

    result = {
        "submitted": True,
        "stock_symbol": stock_symbol,
        "market_type": full_cfg.get("market_type"),
        "analysis_date": full_cfg.get("analysis_date"),
        "analysis_mode": "multi_model",
        "collaboration_mode": full_cfg.get("collaboration_mode", "sequential"),
        "research_depth": full_cfg.get("research_depth", 3),
        "selected_agents": selected_agents,
    }
    try:
        logger.info(f"🤖 [多模型表单/统一] 提交: {result}")
    except Exception:
        pass
    return result


def render_multi_model_results(results: dict):
    """渲染多模型协作分析结果"""

    if not results:
        st.warning("⚠️ 暂无分析结果")
        return

    # 调试信息
    logger.info(f"🔍 [渲染结果] 收到数据结构: {type(results)}")
    logger.info(
        f"🔍 [渲染结果] 数据键: {list(results.keys()) if isinstance(results, dict) else 'Not a dict'}"
    )

    # 统一样式优先：尝试将多模型结果映射为单模型展示结构并复用 render_results
    try:
        if isinstance(results, dict) and results.get("status") != "error":

            def _extract_action(text: str) -> str:
                t = (text or "").lower()
                if any(k in t for k in ["买入", "buy"]):
                    return "买入"
                if any(k in t for k in ["卖出", "sell"]):
                    return "卖出"
                if any(k in t for k in ["持有", "hold"]):
                    return "持有"
                return "持有"

            analysis_data = results.get("analysis_data") or {}
            agents_used = list(results.get("agents_used") or [])
            agent_results = results.get("results") or {}

            # 状态块映射（扩展）：将未原生支持的角色合并到最相近的板块
            state_map = {
                "technical_analyst": "market_report",
                "tool_engineer": "market_report",  # 工具/回测 → 技术面
                "fundamental_expert": "fundamentals_report",
                "sentiment_analyst": "sentiment_report",
                "news_hunter": "news_report",
                "policy_researcher": "news_report",  # 政策动向 → 资讯板块
                "risk_manager": "risk_assessment",
                "compliance_officer": "risk_assessment",  # 合规风险 → 风险板块
                "chief_decision_officer": "investment_plan",  # 最终建议 → 投资建议板块
            }
            # 累积填充，避免覆盖同一板块的多位专家观点
            state: dict = {}
            for agent_key, section_key in state_map.items():
                if agent_key in agent_results:
                    text = agent_results[agent_key].get("analysis") or ""
                    if not text:
                        continue
                    if section_key not in state or not state.get(section_key):
                        state[section_key] = f"【{agent_key}】\n{text}"
                    else:
                        state[section_key] = (
                            str(state[section_key])
                            + "\n\n---\n\n"
                            + f"【{agent_key}】\n{text}"
                        )

            # 投资建议：优先首席决策官
            decision = {
                "action": "持有",
                "confidence": 0.7,
                "risk_score": 0.3,
                "target_price": None,
                "reasoning": "",
            }
            cdo = agent_results.get("chief_decision_officer") or {}
            if cdo:
                atext = cdo.get("analysis") or ""
                decision["action"] = _extract_action(atext)
                decision["confidence"] = cdo.get("confidence", 0.7)
                decision["reasoning"] = atext[:4000]
            else:
                # 回退到任一智能体
                if isinstance(agent_results, dict) and agent_results:
                    any_agent = next(iter(agent_results.values()))
                    atext = (
                        (any_agent.get("analysis") or "")
                        if isinstance(any_agent, dict)
                        else ""
                    )
                    decision["action"] = _extract_action(atext)
                    decision["reasoning"] = atext[:4000]

            {
                "stock_symbol": analysis_data.get("stock_symbol") or "N/A",
                "analysis_date": analysis_data.get("analysis_date"),
                "research_depth": analysis_data.get("research_depth", 3),
                "analysts": agents_used,
                "llm_provider": "multi",
                "llm_model": "multi",
                "state": state,
                "decision": decision,
                "final_article": results.get("final_article"),
                "final_article_metrics": results.get("final_article_metrics") or {},
                "success": True,
            }

            # 汇总视图已改为按智能体标签页展示，不在此处渲染整体汇总
    except Exception as _e:
        # 失败则回退到原有渲染逻辑
        logger.warning(f"多模型结果统一渲染失败，回退到原样式: {_e}")

    st.markdown("### 🎯 多模型协作分析报告")

    # 提取元数据信息
    collaboration_mode = results.get("collaboration_mode", "unknown")
    agents_used = results.get("agents_used", [])
    analysis_data = results.get("analysis_data", {})

    # 显示分析概览
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📊 分析股票: {analysis_data.get('stock_symbol', 'N/A')}")
    with col2:
        st.info(f"🔄 协作模式: {collaboration_mode}")
    with col3:
        st.info(f"🤖 智能体数量: {len(agents_used)}")

    # 处理不同的数据结构格式
    actual_results = None

    if isinstance(results, dict):
        # 检查错误状态
        if "status" in results and results["status"] == "error":
            st.error(f"❌ 分析失败: {results.get('error', '未知错误')}")
            return

        # 提取实际结果数据 - 支持多层嵌套
        if "results" in results:
            nested_results = results["results"]

            # 处理不同协作模式的数据结构
            if collaboration_mode == "debate":
                # 辩论模式: results.results.independent_analyses
                if "independent_analyses" in nested_results:
                    actual_results = nested_results["independent_analyses"]
                    # 同时显示共识结果
                    if "consensus" in nested_results:
                        st.markdown("#### 💬 辩论共识结果")
                        consensus = nested_results["consensus"]
                        with st.expander("🎯 最终共识", expanded=False):
                            st.markdown("**共识结论:**")
                            st.write(
                                consensus.get("final_recommendation", "无共识结论")
                            )

                            col1, col2 = st.columns(2)
                            with col1:
                                agreement = consensus.get("agreement_level", 0)
                                st.metric(
                                    "共识度",
                                    f"{agreement:.1%}" if agreement > 0 else "N/A",
                                )
                            with col2:
                                method = consensus.get("consensus_method", "unknown")
                                st.info(f"🔄 共识方法: {method}")

                            # 显示不同意见
                            dissenting = consensus.get("dissenting_opinions", [])
                            if dissenting:
                                st.markdown("**不同意见:**")
                                for opinion in dissenting:
                                    st.warning(f"⚠️ {opinion}")

            elif collaboration_mode in ["sequential", "parallel"]:
                # 串行/并行模式: results.results 直接包含智能体结果
                # 或者 results.results.summary 包含整合结果
                if isinstance(nested_results, dict):
                    # 查找智能体结果
                    agent_results = {}
                    for key, value in nested_results.items():
                        if (
                            isinstance(value, dict)
                            and "agent_type" in value
                            and "analysis" in value
                        ):
                            agent_results[key] = value

                    if agent_results:
                        actual_results = agent_results
                    else:
                        # 如果没有找到标准格式，尝试直接使用nested_results
                        actual_results = nested_results

                # 显示整合结果（如果有）
                if "summary" in nested_results:
                    st.markdown("#### 📋 整合分析结果")
                    summary = nested_results["summary"]
                    with st.expander("🎯 综合结论", expanded=False):
                        if isinstance(summary, dict):
                            st.write(
                                summary.get("overall_recommendation", "无综合建议")
                            )

                            col1, col2, col3 = st.columns(3)
                            with col1:
                                confidence = summary.get("confidence_score", 0)
                                st.metric(
                                    "置信度",
                                    f"{confidence:.1%}" if confidence > 0 else "N/A",
                                )
                            with col2:
                                risk = summary.get("risk_level", "unknown")
                                st.info(f"📊 风险等级: {risk}")
                            with col3:
                                method = summary.get("integration_method", "unknown")
                                st.info(f"🔄 整合方法: {method}")
                        else:
                            st.write(summary)

        # 如果上面的逻辑都没找到结果，尝试直接使用results
        if not actual_results:
            actual_results = results

    # 将多模型结果映射为标准结果结构，并直接复用统一的结果渲染
    try:
        if isinstance(results, dict) and results.get("status") != "error":

            def _extract_action(text: str) -> str:
                t = (text or "").lower()
                if any(k in t for k in ["买入", "buy"]):
                    return "买入"
                if any(k in t for k in ["卖出", "sell"]):
                    return "卖出"
                if any(k in t for k in ["持有", "hold"]):
                    return "持有"
                return "持有"

            analysis_data = results.get("analysis_data") or {}
            agents_used = list(results.get("agents_used") or [])
            agent_results = results.get("results") or {}

            # 聚合到 state（保留兼容性）
            state_map = {
                "technical_analyst": "market_report",
                "tool_engineer": "market_report",
                "fundamental_expert": "fundamentals_report",
                "sentiment_analyst": "sentiment_report",
                "news_hunter": "news_report",
                "policy_researcher": "news_report",
                "risk_manager": "risk_assessment",
                "compliance_officer": "risk_assessment",
                "chief_decision_officer": "investment_plan",
            }
            state: dict = {}
            for agent_key, section_key in state_map.items():
                if agent_key in agent_results:
                    text = agent_results[agent_key].get("analysis") or ""
                    if not text:
                        continue
                    if section_key not in state or not state.get(section_key):
                        state[section_key] = f"【{agent_key}】\n{text}"
                    else:
                        state[section_key] = (
                            str(state[section_key])
                            + "\n\n---\n\n"
                            + f"【{agent_key}】\n{text}"
                        )

            decision = {
                "action": "持有",
                "confidence": 0.7,
                "risk_score": 0.3,
                "target_price": None,
                "reasoning": "",
            }
            cdo = agent_results.get("chief_decision_officer") or {}
            if cdo:
                atext = cdo.get("analysis") or ""
                decision["action"] = _extract_action(atext)
                decision["confidence"] = cdo.get("confidence", 0.7)
                decision["reasoning"] = atext[:4000]

            standard_results = {
                "stock_symbol": analysis_data.get("stock_symbol") or "N/A",
                "analysis_date": analysis_data.get("analysis_date"),
                "research_depth": analysis_data.get("research_depth", 3),
                "analysts": agents_used,
                "llm_provider": "multi",
                "llm_model": "multi",
                "state": state,
                "decision": decision,
                "final_article": results.get("final_article"),
                "final_article_metrics": results.get("final_article_metrics") or {},
                # 关键：把原始多智能体结果也传入，供详细面板标签直接按智能体渲染
                "results": agent_results,
                "agents_used": agents_used,
                "success": True,
            }

            from components.results_display import render_results as _render

            _render(standard_results)
            return
    except Exception as _e:
        st.warning(f"⚠️ 结果映射失败，显示原始结构: {_e}")
        st.json(results)
