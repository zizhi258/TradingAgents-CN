"""
增强的多模型协作分析表单组件
改进用户体验、错误处理和进度反馈
"""

import datetime
import os
import time
from typing import Any

import streamlit as st

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("web")

# 导入错误处理器
from tradingagents.core.user_friendly_error_handler import (
    handle_user_friendly_error,  # noqa: E402
)

# 导入可复用模型选择面板（带开关的精简版）
from .model_selection_panel import (  # noqa: E402
    render_basic_advanced_settings,
    render_model_selection_panel,
    render_routing_section,
)


class AnalysisProgressTracker:
    """分析进度跟踪器"""

    def __init__(self):
        self.start_time = None
        self.current_stage = "准备中"
        self.progress_percentage = 0
        self.stage_details = ""
        self.estimated_time_remaining = None
        self.is_cancellable = True
        self.cancel_requested = False

        # 定义分析阶段
        self.stages = {
            "preparation": {
                "name": "🛠️ 准备分析环境",
                "progress_range": (0, 10),
                "estimated_seconds": 5,
            },
            "data_collection": {
                "name": "📊 收集股票数据",
                "progress_range": (10, 25),
                "estimated_seconds": 15,
            },
            "model_initialization": {
                "name": "🤖 初始化AI模型",
                "progress_range": (25, 35),
                "estimated_seconds": 10,
            },
            "agent_analysis": {
                "name": "💼 智能体协作分析",
                "progress_range": (35, 80),
                "estimated_seconds": 120,
            },
            "result_synthesis": {
                "name": "📋 结果整合与生成",
                "progress_range": (80, 95),
                "estimated_seconds": 15,
            },
            "completion": {
                "name": "✨ 分析完成",
                "progress_range": (95, 100),
                "estimated_seconds": 5,
            },
        }

    def start_analysis(self):
        """开始分析"""
        self.start_time = time.time()
        self.current_stage = "preparation"
        self.progress_percentage = 0
        self.cancel_requested = False

        # 计算总估计时间
        total_estimated = sum(
            stage["estimated_seconds"] for stage in self.stages.values()
        )
        self.estimated_total_time = total_estimated

    def update_stage(self, stage_key: str, details: str = ""):
        """更新当前阶段"""
        if stage_key in self.stages:
            self.current_stage = stage_key
            self.stage_details = details

            # 更新进度百分比到阶段起始点
            stage_info = self.stages[stage_key]
            self.progress_percentage = stage_info["progress_range"][0]

            # 更新预估剩余时间
            time.time() - self.start_time if self.start_time else 0
            remaining_stages = [
                k
                for k in self.stages.keys()
                if list(self.stages.keys()).index(k)
                > list(self.stages.keys()).index(stage_key)
            ]
            remaining_time = sum(
                self.stages[k]["estimated_seconds"] for k in remaining_stages
            )
            self.estimated_time_remaining = remaining_time

    def update_progress(self, percentage: float, details: str = ""):
        """更新进度百分比"""
        self.progress_percentage = min(100, max(0, percentage))
        if details:
            self.stage_details = details

    def request_cancel(self):
        """请求取消分析"""
        self.cancel_requested = True
        self.is_cancellable = False

    def is_cancelled(self) -> bool:
        """检查是否已请求取消"""
        return self.cancel_requested

    def get_display_info(self) -> dict[str, Any]:
        """获取用于界面显示的信息"""
        current_stage_info = self.stages.get(self.current_stage, {})

        return {
            "current_stage": current_stage_info.get("name", self.current_stage),
            "progress_percentage": self.progress_percentage,
            "details": self.stage_details,
            "estimated_time_remaining": self.estimated_time_remaining,
            "elapsed_time": time.time() - self.start_time if self.start_time else 0,
            "is_cancellable": self.is_cancellable,
            "status": "running" if not self.cancel_requested else "cancelling",
        }


def render_enhanced_multi_model_analysis_form():
    """渲染增强的多模型协作分析表单"""

    st.subheader("🤖 智能多模型协作分析")

    # 检查系统状态
    system_status = check_system_health()
    display_system_status(system_status)

    # 获取缓存的表单配置（确保不为None）
    cached_config = st.session_state.get("enhanced_multi_model_config") or {}

    # 创建表单
    with st.form("enhanced_multi_model_analysis_form", clear_on_submit=False):
        # 使用分栏/页签的精简配置面板，替代冗长竖排
        full_config = render_compact_multi_model_config_panel(cached_config)

        # 提交按钮
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            submitted = st.form_submit_button(
                "🚀 开始智能分析", use_container_width=True, type="primary"
            )

    # 处理表单提交
    if submitted:
        handle_analysis_submission(full_config)


def render_compact_multi_model_config_panel(
    cached_config: dict[str, Any],
) -> dict[str, Any]:
    """分区分页的多模型配置面板（去除重复的角色配置，集中到‘🧭 角色中心’）"""
    tabs = st.tabs(
        ["基础信息", "模型与提供商", "协作与智能体", "路由与预算", "高级设置", "结果"]
    )

    # 1) 基础信息
    with tabs[0]:
        st.markdown("### 📊 基础配置")
        base_cfg = render_basic_config_section(cached_config)

    # 2) 模型与提供商（隐藏路由/高级，专注模型）
    with tabs[1]:
        model_cfg = render_model_selection_panel(
            location="main", show_routing=False, show_advanced=False
        )

    # 3) 协作与智能体
    with tabs[2]:
        st.markdown("### 🤝 协作配置")
        ai_cfg = render_ai_collaboration_config(cached_config)

    # 4) 路由与预算（独立页签，避免与模型选择混在一起）
    with tabs[3]:
        st.markdown("### 🧭 路由与预算")
        routing_strategy, fallbacks, max_budget = render_routing_section(
            location="main"
        )

    # 5) 高级设置（基础项）
    with tabs[4]:
        adv_cfg = render_basic_advanced_settings(location="main")

    # 6) 结果（新增）：在同一面板内查看分析结果与绘图
    with tabs[5]:
        try:
            render_inline_multi_model_results_tab()
            # 标记已在面板内渲染结果，避免页面下方重复渲染
            try:
                st.session_state._multi_model_results_rendered_inline = True
            except Exception:
                pass
        except Exception as _e:
            st.info("结果区域待生成。提交分析后将在此显示。")
            st.caption(f"详情: {_e}")

    # 汇总配置（与原有键保持兼容）
    full_cfg = {
        **base_cfg,
        **model_cfg,
        **ai_cfg,
        **adv_cfg,
        "routing_strategy": routing_strategy,
        "fallbacks": fallbacks,
        "max_budget": max_budget,
        "analysis_mode": "multi_model",
    }
    return full_cfg


def check_system_health() -> dict[str, Any]:
    """检查系统健康状态"""
    try:
        # 检查环境变量
        required_env_vars = {
            "MULTI_MODEL_ENABLED": os.getenv("MULTI_MODEL_ENABLED", "false"),
            # 'DASHSCOPE_API_KEY' 已移除
            "FINNHUB_API_KEY": bool(os.getenv("FINNHUB_API_KEY")),
        }

        health_status = {
            "overall_health": "healthy",
            "multi_model_enabled": required_env_vars["MULTI_MODEL_ENABLED"].lower()
            in ["true", "1", "yes"],
            "api_keys_configured": required_env_vars["FINNHUB_API_KEY"],
            "system_load": "normal",
            "recommendations": [],
        }

        # 检查多模型功能是否启用
        if not health_status["multi_model_enabled"]:
            health_status["overall_health"] = "limited"
            health_status["recommendations"].append(
                "启用多模型功能：设置 MULTI_MODEL_ENABLED=true"
            )

        # 检查API密钥
        if not health_status["api_keys_configured"]:
            health_status["overall_health"] = "limited"
            health_status["recommendations"].append(
                "配置API密钥：请检查.env文件中的API密钥设置"
            )

        return health_status

    except Exception as e:
        logger.error(f"系统健康检查失败: {e}")
        return {
            "overall_health": "unknown",
            "error": str(e),
            "recommendations": ["请检查系统配置或联系技术支持"],
        }


def display_system_status(status: dict[str, Any]):
    """显示系统状态"""
    health = status["overall_health"]

    if health == "healthy":
        st.success("✅ 系统状态正常，所有功能可正常使用")
    elif health == "limited":
        st.warning("⚠️ 系统功能有限，部分功能可能不可用")

        if status.get("recommendations"):
            with st.expander("💡 优化建议", expanded=True):
                for recommendation in status["recommendations"]:
                    st.info(recommendation)

    elif health == "unknown":
        st.error("❌ 系统状态未知，请检查系统配置")
        if "error" in status:
            with st.expander("🔍 错误详情"):
                st.code(status["error"])


def render_basic_config_section(cached_config: dict[str, Any]) -> dict[str, Any]:
    """渲染基础配置部分"""
    col1, col2 = st.columns(2)

    with col1:
        # 市场选择
        market_options = ["美股", "A股", "港股"]
        cached_market = cached_config.get("market_type", "A股")
        try:
            market_index = market_options.index(cached_market)
        except (ValueError, TypeError):
            market_index = 1  # 默认A股

        market_type = st.selectbox(
            "选择市场 🌍",
            options=market_options,
            index=market_index,
            help="选择要分析的股票市场",
        )

        # 股票代码输入与验证
        stock_symbol = render_stock_input(market_type, cached_config)

    with col2:
        # 分析日期
        analysis_date = st.date_input(
            "分析日期 📅",
            value=datetime.date.today(),
            help="选择分析的基准日期",
            max_value=datetime.date.today(),
        )

    return {
        "market_type": market_type,
        "stock_symbol": stock_symbol,
        "analysis_date": analysis_date.isoformat(),
        "analysis_mode": "multi_model",  # 右侧不再选择，固定为多模型
    }


def render_stock_input(market_type: str, cached_config: dict[str, Any]) -> str:
    """渲染股票代码输入框并验证"""
    # 获取缓存的股票代码
    cached_stock = cached_config.get("stock_symbol", "")

    # 根据市场类型设置提示信息
    if market_type == "美股":
        placeholder = "输入美股代码，如 AAPL, TSLA, NVDA"
        help_text = "输入要分析的美股代码"
        validation_pattern = r"^[A-Z]{1,5}$"
        default_value = (
            cached_stock if cached_config.get("market_type") == "美股" else ""
        )
    elif market_type == "港股":
        placeholder = "输入港股代码，如 0700.HK, 9988.HK"
        help_text = "输入要分析的港股代码"
        validation_pattern = r"^\d{4,5}\.HK$"
        default_value = (
            cached_stock if cached_config.get("market_type") == "港股" else ""
        )
    else:  # A股
        placeholder = "输入A股代码，如 000001, 600519"
        help_text = "输入要分析的A股代码"
        validation_pattern = r"^\d{6}$"
        default_value = (
            cached_stock if cached_config.get("market_type") == "A股" else ""
        )

    # 股票代码输入
    stock_symbol = (
        st.text_input(
            "股票代码 📈",
            value=default_value,
            placeholder=placeholder,
            help=help_text,
            key=f"enhanced_{market_type}_stock_input",
        )
        .strip()
        .upper()
        if market_type != "A股"
        else st.text_input(
            "股票代码 📈",
            value=default_value,
            placeholder=placeholder,
            help=help_text,
            key=f"enhanced_{market_type}_stock_input",
        ).strip()
    )

    # 实时验证
    if stock_symbol:
        import re

        if not re.match(validation_pattern, stock_symbol):
            st.error("⚠️ 股票代码格式不正确，请检查后重新输入")
            st.info(
                f"💡 {market_type}正确格式示例: {placeholder.split('，')[1] if '，' in placeholder else placeholder}"
            )
        else:
            st.success("✅ 股票代码格式正确")

    return stock_symbol


def render_ai_collaboration_config(cached_config: dict[str, Any]) -> dict[str, Any]:
    """渲染AI协作配置部分"""
    col1, col2 = st.columns(2)

    with col1:
        # 协作模式选择
        collaboration_mode = st.selectbox(
            "协作模式 🔄",
            options=["sequential", "parallel", "debate"],
            format_func=lambda x: {
                "sequential": "📋 串行协作 - 智能体依次分析",
                "parallel": "⚡ 并行协作 - 智能体同时分析",
                "debate": "💬 辩论协作 - 智能体互相辩论",
            }[x],
            index=0,
            help="选择智能体协作模式：串行更稳定，并行更快速，辩论更全面",
        )

        # 分析深度
        research_depth = st.select_slider(
            "研究深度 🔍",
            options=[1, 2, 3, 4, 5],
            value=3,
            format_func=lambda x: {
                1: "1级 - 快速分析 (~2分钟)",
                2: "2级 - 基础分析 (~5分钟)",
                3: "3级 - 标准分析 (~8分钟)",
                4: "4级 - 深度分析 (~12分钟)",
                5: "5级 - 全面分析 (~20分钟)",
            }[x],
            help="选择分析的深度级别，级别越高结果越详细但耗时越长",
        )

    with col2:
        # 智能路由选择
        use_smart_routing = st.checkbox(
            "🧠 启用智能路由",
            value=True,
            help="让AI自动为每个任务选择最适合的模型组合，提高分析质量",
        )

        # 成本控制
        cost_optimization = st.selectbox(
            "成本控制 💰",
            options=["balanced", "cost_first", "quality_first"],
            format_func=lambda x: {
                "balanced": "⚖️ 平衡模式 - 成本与质量并重",
                "cost_first": "💸 成本优先 - 优先使用经济型模型",
                "quality_first": "⭐ 质量优先 - 优先使用高性能模型",
            }[x],
            index=0,
            help="选择成本优化策略：平衡模式推荐日常使用",
        )

    # 专业智能体选择（动态加载）
    st.markdown("#### 👥 专业智能体团队")
    st.markdown("*选择参与分析的专业智能体角色*")

    # 动态获取可用角色（API优先，本地回退，最终兜底）
    try:
        from web.utils.ui_utils import (
            get_available_agents_for_ui,
        )

        available_meta = get_available_agents_for_ui()
        available_roles = set(available_meta.get("available_agents", []) or [])
    except Exception:
        available_roles = set()

    # UI支持的角色清单（控制展示顺序与范围）
    supported_roles = [
        "news_hunter",
        "technical_analyst",
        "policy_researcher",
        "fundamental_expert",
        "sentiment_analyst",
        "tool_engineer",
        "risk_manager",
        "compliance_officer",
        "chief_decision_officer",
        # 新增：绘图师
        "charting_artist",
    ]

    # 仅展示当前后端可用的角色，保持顺序
    roles_to_show = [
        r for r in supported_roles if (not available_roles or r in available_roles)
    ]

    # 默认勾选的缓存值
    cached_agents = (
        cached_config.get(
            "selected_agents", ["news_hunter", "fundamental_expert", "risk_manager"]
        )
        if cached_config
        else ["news_hunter", "fundamental_expert", "risk_manager"]
    )

    # 角色提示文案
    help_map = {
        "news_hunter": "实时新闻收集与分析",
        "technical_analyst": "技术指标与图表分析，推荐使用DeepSeek-V3模型",
        "policy_researcher": "政策法规解读分析",
        "fundamental_expert": "财务数据与估值分析，推荐使用DeepSeek-R1模型",
        "sentiment_analyst": "市场情绪与社媒分析，推荐使用Step-3模型",
        "tool_engineer": "量化工具与回测分析，推荐使用Kimi-K2模型",
        "risk_manager": "投资风险评估与控制，推荐使用GLM-4.5模型",
        "compliance_officer": "法律合规性检查，推荐使用GLM-4.5或Gemini",
        "chief_decision_officer": "综合决策与最终建议，推荐使用最强模型",
        "charting_artist": "基于分析结果自动生成可交互金融图表（Plotly）",
    }

    selected_agents = []
    cols = st.columns(3)
    for idx, role in enumerate(roles_to_show):
        col = cols[idx % 3]
        with col:
            label = None
            try:
                from web.utils.ui_utils import get_role_display_name as _disp

                label = _disp(role)
            except Exception:
                label = role
            # 为视觉统一加上表情图标（简化：仅在已知映射中）
            emoji_map = {
                "news_hunter": "📰",
                "technical_analyst": "📈",
                "policy_researcher": "📋",
                "fundamental_expert": "💰",
                "sentiment_analyst": "💭",
                "tool_engineer": "🔧",
                "risk_manager": "⚠️",
                "compliance_officer": "🛡️",
                "chief_decision_officer": "🏆",
                "charting_artist": "🎨",
            }
            label = f"{emoji_map.get(role, '🤖')} {label}"
            if st.checkbox(
                label,
                value=(role in cached_agents),
                help=help_map.get(role, "参与协作分析"),
            ):
                selected_agents.append(role)

    # 检查是否选择了智能体
    if not selected_agents:
        st.warning("⚠️ 请至少选择一个专业智能体进行分析")
    else:
        st.success(f"✅ 已选择 {len(selected_agents)} 个专业智能体")

    return {
        "collaboration_mode": collaboration_mode,
        "research_depth": research_depth,
        "use_smart_routing": use_smart_routing,
        "cost_optimization": cost_optimization,
        "selected_agents": selected_agents,
    }


def render_advanced_settings(cached_config: dict[str, Any]) -> dict[str, Any]:
    """渲染高级设置部分"""
    col1, col2 = st.columns(2)

    with col1:
        # 超时设置
        analysis_timeout = st.number_input(
            "分析超时时间（分钟）",
            min_value=5,
            max_value=60,
            value=20,
            help="设置单次分析的最大时间限制，超时将自动停止",
        )

        # 重试设置
        max_retries = st.number_input(
            "最大重试次数",
            min_value=0,
            max_value=5,
            value=2,
            help="当分析失败时的最大自动重试次数",
        )

    with col2:
        # 缓存设置
        use_cache = st.checkbox(
            "启用结果缓存",
            value=True,
            help="启用后会缓存分析结果，相同配置的分析会直接使用缓存结果",
        )

        # 进度报告
        enable_progress_updates = st.checkbox(
            "实时进度更新", value=True, help="实时显示分析进度和各个阶段的状态"
        )

    return {
        "analysis_timeout": analysis_timeout,
        "max_retries": max_retries,
        "use_cache": use_cache,
        "enable_progress_updates": enable_progress_updates,
    }


def _get_mm_results_from_state() -> dict | None:
    """从 session_state 或最近的结果文件中获取多模型结果（容错）。"""
    try:
        import json, os
        from glob import glob
        results = st.session_state.get("multi_model_analysis_results")
        if results:
            return results
        # 兜底：尝试读取最近一次的结果文件
        files = sorted(glob("./data/multi_model_results_*.json"))
        if files:
            latest = files[-1]
            with open(latest, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("results") or data
    except Exception:
        return None


def render_inline_multi_model_results_tab() -> None:
    """在增强面板内渲染“结果”页签，包含各角色与绘图师的标签页。"""
    results = _get_mm_results_from_state()
    if not results:
        st.info("暂无结果。请在前面的页签完成配置并提交分析。")
        return

    # 兼容两种结构：直接是 results 映射 或 外层包含 results/final_article
    agent_results = results.get("results") if isinstance(results, dict) else None
    if not agent_results and isinstance(results, dict):
        agent_results = results
    final_article = None
    if isinstance(results, dict):
        final_article = results.get("final_article")

    # 标签页顺序（含绘图师）
    tab_labels = [
        "📝 主笔人长文",
        "📰 快讯猎手",
        "📈 技术分析师",
        "📋 政策研究员",
        "💰 基本面专家",
        "💭 情绪分析师",
        "🔧 工具工程师",
        "🛡️ 风控经理",
        "⚖️ 合规官",
        "🎯 首席决策官",
        "🎨 绘图师",
    ]
    tabs = st.tabs(tab_labels)

    # 1) 主笔人长文
    with tabs[0]:
        if isinstance(final_article, str) and final_article.strip():
            st.markdown(final_article)
        else:
            st.info("尚无主笔人长文。")

    # 角色键映射
    role_map = {
        1: "news_hunter",
        2: "technical_analyst",
        3: "policy_researcher",
        4: "fundamental_expert",
        5: "sentiment_analyst",
        6: "tool_engineer",
        7: "risk_manager",
        8: "compliance_officer",
        9: "chief_decision_officer",
    }

    # 2-10) 各智能体文本结果
    for idx, key in role_map.items():
        with tabs[idx]:
            if isinstance(agent_results, dict) and key in agent_results:
                item = agent_results[key]
                text = item.get("analysis") if isinstance(item, dict) else str(item)
                if text:
                    st.markdown(text)
                else:
                    st.info("暂无该角色输出。")
            else:
                st.info("未选择或无该角色输出。")

    # 11) 绘图师
    with tabs[10]:
        # 优先读取结果内的可视化清单
        viz = None
        if isinstance(agent_results, dict) and "charting_artist" in agent_results:
            entry = agent_results["charting_artist"]
            viz = entry.get("visualizations") if isinstance(entry, dict) else None
        charts = []
        if isinstance(viz, dict):
            charts = viz.get("charts_generated", []) or []
        if charts:
            for chart in charts:
                p = chart.get("path") or chart.get("file_path")
                if p and os.path.exists(p):
                    try:
                        if p.endswith(".html"):
                            with open(p, encoding="utf-8") as f:
                                html = f.read()
                            st.components.v1.html(html, height=600, scrolling=True)
                        elif p.endswith(".json"):
                            import json as _json
                            import plotly.graph_objects as go
                            with open(p, encoding="utf-8") as f:
                                fig_dict = _json.load(f)
                            st.plotly_chart(go.Figure(fig_dict), use_container_width=True)
                    except Exception as _e:
                        st.warning(f"图表显示失败: {_e}")
                st.markdown("---")
        else:
            # 兜底：展示历史图表
            st.caption("未检测到本次分析的图表结果，尝试加载历史图表…")
            try:
                from components.charting_artist_component import get_local_charts, display_local_charts
                symbol = None
                try:
                    symbol = (results.get("analysis_data") or {}).get("stock_symbol") if isinstance(results, dict) else None
                except Exception:
                    symbol = None
                local_charts = get_local_charts(symbol)
                if local_charts:
                    display_local_charts(local_charts)
                else:
                    st.info("暂无可展示的图表。")
            except Exception:
                st.info("图表组件不可用或未生成图表。")


def handle_analysis_submission(config: dict[str, Any]):
    """处理分析提交请求"""
    try:
        # 缓存配置
        st.session_state["enhanced_multi_model_config"] = config

        # 验证配置
        validation_error = validate_analysis_config(config)
        if validation_error:
            st.error(f"⚠️ 配置验证失败: {validation_error}")
            return

        # 显示配置总览
        display_analysis_overview(config)

        # 开始分析
        if config.get("enable_progress_updates", True):
            # 带进度反馈的分析
            run_analysis_with_progress(config)
        else:
            # 简单模式分析
            run_simple_analysis(config)

    except Exception as e:
        # 使用用户友好的错误处理
        user_error = handle_user_friendly_error(
            e, {"action": "analysis_submission", "config": config}
        )

        display_user_friendly_error(user_error)
        logger.error(f"分析提交处理失败: {e}", exc_info=True)


def validate_analysis_config(config: dict[str, Any]) -> str | None:
    """验证分析配置"""
    # 检查必需字段
    required_fields = ["market_type", "stock_symbol", "analysis_date", "analysis_mode"]
    for field in required_fields:
        if not config.get(field):
            return f"缺少必需配置项: {field}"

    # 检查股票代码格式
    stock_symbol = config["stock_symbol"]
    market_type = config["market_type"]

    import re

    validation_patterns = {
        "美股": r"^[A-Z]{1,5}$",
        "港股": r"^\d{4,5}\.HK$",
        "A股": r"^\d{6}$",
    }

    pattern = validation_patterns.get(market_type)
    if pattern and not re.match(pattern, stock_symbol):
        return f"股票代码格式不正确: {stock_symbol}"

    # 检查智能体选择
    if config.get("analysis_mode") == "multi_model":
        selected_agents = config.get("selected_agents", [])
        if not selected_agents:
            return "多模型模式下必须选择至少一个智能体"

    return None


def display_analysis_overview(config: dict[str, Any]):
    """显示分析配置总览"""
    with st.expander("📋 分析配置总览", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f"**目标股票**: {config['stock_symbol']} ({config['market_type']})"
            )
            st.markdown(f"**分析日期**: {config['analysis_date']}")
            st.markdown(f"**分析模式**: {config['analysis_mode']}")

        with col2:
            if config.get("analysis_mode") == "multi_model":
                agents_count = len(config.get("selected_agents", []))
                st.markdown(f"**智能体数量**: {agents_count} 个")
                st.markdown(
                    f"**协作模式**: {config.get('collaboration_mode', 'sequential')}"
                )
                st.markdown(f"**研究深度**: {config.get('research_depth', 3)} 级")

        # 显示智能体列表
        if config.get("selected_agents"):
            try:
                from web.utils.ui_utils import get_role_display_name

                agent_list = [
                    get_role_display_name(agent) for agent in config["selected_agents"]
                ]
            except Exception:
                agent_list = config["selected_agents"]
            st.markdown(f"**参与智能体**: {', '.join(agent_list)}")


def run_analysis_with_progress(config: dict[str, Any]):
    """运行带进度反馈的分析"""
    progress_tracker = AnalysisProgressTracker()
    progress_tracker.start_analysis()

    # 创建进度显示区域
    progress_container = st.empty()
    cancel_container = st.empty()

    try:
        # 显示初始进度
        display_progress_info(progress_tracker, progress_container, cancel_container)

        # 实际分析逻辑（这里需要集成到真实的分析系统）
        result = simulate_analysis_with_progress(
            config, progress_tracker, progress_container, cancel_container
        )

        if result:
            st.success("🎉 分析完成！")
            display_analysis_results(result)
        else:
            st.error("❌ 分析被取消或失败")

    except Exception as e:
        user_error = handle_user_friendly_error(
            e, {"action": "analysis_execution", "config": config}
        )
        display_user_friendly_error(user_error)


def simulate_analysis_with_progress(
    config: dict[str, Any],
    progress_tracker: AnalysisProgressTracker,
    progress_container,
    cancel_container,
) -> dict[str, Any] | None:
    """模拟带进度的分析过程（实际实现需要集成真实分析系统）"""
    stages = [
        "preparation",
        "data_collection",
        "model_initialization",
        "agent_analysis",
        "result_synthesis",
        "completion",
    ]

    for i, stage in enumerate(stages):
        if progress_tracker.is_cancelled():
            return None

        progress_tracker.update_stage(stage, f"正在执行阶段 {i+1}/6")
        display_progress_info(progress_tracker, progress_container, cancel_container)

        # 模拟处理时间
        stage_info = progress_tracker.stages[stage]
        simulation_time = min(stage_info["estimated_seconds"], 3)  # 最多3秒用于演示

        for j in range(int(simulation_time * 10)):
            if progress_tracker.is_cancelled():
                return None

            # 更新进度百分比
            stage_progress = (j / (simulation_time * 10)) * (
                stage_info["progress_range"][1] - stage_info["progress_range"][0]
            )
            progress_tracker.update_progress(
                stage_info["progress_range"][0] + stage_progress
            )
            display_progress_info(
                progress_tracker, progress_container, cancel_container
            )

            time.sleep(0.1)  # 模拟处理延迟

    # 返回模拟结果
    return {
        "status": "success",
        "config": config,
        "result": "分析完成，这是模拟结果。实际实现需要集成真实分析系统。",
    }


def display_progress_info(
    progress_tracker: AnalysisProgressTracker, progress_container, cancel_container
):
    """显示进度信息"""
    display_info = progress_tracker.get_display_info()

    with progress_container.container():
        # 进度条
        st.progress(display_info["progress_percentage"] / 100)

        # 当前阶段
        st.markdown(f"**当前阶段**: {display_info['current_stage']}")

        if display_info["details"]:
            st.markdown(f"**详情**: {display_info['details']}")

        # 时间信息
        col1, col2 = st.columns(2)
        with col1:
            elapsed_mins = int(display_info["elapsed_time"] // 60)
            elapsed_secs = int(display_info["elapsed_time"] % 60)
            st.markdown(f"**已用时间**: {elapsed_mins}分{elapsed_secs}秒")

        with col2:
            if display_info["estimated_time_remaining"]:
                remaining_mins = int(display_info["estimated_time_remaining"] // 60)
                remaining_secs = int(display_info["estimated_time_remaining"] % 60)
                st.markdown(f"**预计剩余**: {remaining_mins}分{remaining_secs}秒")

    # 取消按钮
    if display_info["is_cancellable"]:
        with cancel_container.container():
            if st.button("❌ 取消分析", type="secondary"):
                progress_tracker.request_cancel()
                st.warning("⚠️ 正在取消分析...")


def run_simple_analysis(config: dict[str, Any]):
    """运行简单模式分析"""
    with st.spinner("🤖 正在进行智能分析，请稍候..."):
        try:
            # 这里应该集成真实的分析系统
            time.sleep(3)  # 模拟处理时间

            result = {
                "status": "success",
                "config": config,
                "result": "简单模式分析完成，这是模拟结果。",
            }

            st.success("🎉 分析完成！")
            display_analysis_results(result)

        except Exception as e:
            user_error = handle_user_friendly_error(
                e, {"action": "simple_analysis", "config": config}
            )
            display_user_friendly_error(user_error)


def display_analysis_results(result: dict[str, Any]):
    """显示分析结果"""
    st.markdown("### 📊 分析结果")

    # 结果总览
    with st.expander("📋 结果总览", expanded=True):
        st.json(result)

    # 这里可以添加更详细的结果显示逻辑


def display_user_friendly_error(user_error: dict[str, Any]):
    """显示用户友好的错误信息"""
    st.error(f"{user_error['title']}")

    with st.expander("💡 解决建议", expanded=True):
        st.markdown(user_error["message"])
        st.markdown("**建议解决方案:**")
        st.markdown(user_error["suggestion"])

        if user_error.get("estimated_fix_time"):
            st.info(f"⏱️ 预计修复时间: {user_error['estimated_fix_time']}")

        if user_error.get("retry_possible", False):
            st.button("🔄 重试分析", type="secondary")


# 主渲染函数（兼容原有调用）
def render_multi_model_analysis_form():
    """兼容原有调用的主渲染函数"""
    render_enhanced_multi_model_analysis_form()
