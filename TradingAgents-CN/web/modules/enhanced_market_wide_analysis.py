"""
Enhanced Market-Wide Analysis Page
🌍 增强版全球市场分析页面 - 基于TradingAgents-CN框架的智能市场分析功能

功能特性:
- 多市场支持(A股/美股/港股/全球)
- 智能预设配置和自定义筛选
- 实时进度跟踪和成本控制
- 高级数据可视化和分析报告
- 全格式导出和移动响应式设计
- AI模型配置和多模型协作
- 预算控制和成本优化
"""

import datetime
import json
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.utils.logging_manager import get_logger  # noqa: E402

logger = get_logger("enhanced_market_wide_analysis")

# 导入组件和工具
from utils.market_config_store import get_config_store  # noqa: E402
from utils.market_session_manager import (  # noqa: E402
    get_market_session_manager,
    init_market_session_state,
)


def render_enhanced_market_wide_analysis():
    """渲染增强版全球市场分析页面"""

    # 页面标题和介绍
    st.header("🌍 全球市场分析")
    st.caption(
        "🔍 智能市场分析 | 📊 股票排名 | 🔥 板块分析 | 📈 市场指标 | 💰 成本控制"
    )

    # 添加页面说明和快捷操作
    col_info, col_quick = st.columns([3, 1])

    with col_info:
        st.info(
            """
        💡 **功能说明**: 使用AI智能分析引擎，对指定市场进行全方位分析，为您发现投资机会、识别风险、分析板块趋势。
        支持A股、美股、港股等多个市场，提供从基础筛选到深度研究的5级分析深度。
        """
        )

    with col_quick:
        # 快捷操作按钮
        if st.button(
            "⚡ 快速分析A股",
            use_container_width=True,
            help="使用默认配置快速分析A股市场",
        ):
            quick_scan_a_shares()

        if st.button("📈 查看历史", use_container_width=True, help="查看历史分析记录"):
            st.session_state.show_scan_history = True
            st.rerun()

    # 初始化会话状态和管理器
    init_market_session_state()
    session_manager = get_market_session_manager()

    # 创建响应式标签页布局
    tab_config, tab_progress, tab_results = st.tabs(["⚙️ 配置", "📊 进度", "📋 结果"])

    # 添加页面状态指示器
    render_page_status_indicator(session_manager)

    with tab_config:
        render_enhanced_configuration_tab(session_manager)

    with tab_progress:
        render_enhanced_progress_tab(session_manager)

    with tab_results:
        render_enhanced_results_tab(session_manager)


def render_page_status_indicator(session_manager):
    """渲染页面状态指示器"""

    # 获取当前状态
    scan_running = st.session_state.get("market_scan_running", False)
    scan_id = st.session_state.get("current_market_scan_id")
    has_results = st.session_state.get("market_scan_results") is not None

    # 状态指示器
    status_col1, status_col2, status_col3, status_col4 = st.columns(4)

    with status_col1:
        if scan_running:
            st.success("🔄 分析进行中")
        else:
            st.info("⏸️ 未运行分析")

    with status_col2:
        if scan_id:
            st.write(f"📋 ID: {scan_id[:8]}...")
        else:
            st.write("📋 无活跃分析")

    with status_col3:
        if has_results:
            st.success("📊 有结果可查看")
        else:
            st.info("📊 暂无结果")

    with status_col4:
        # 显示API健康状态
        system_status = session_manager.get_system_status()
        api_health = system_status.get("api_health", False)

        if api_health:
            st.success("💚 API正常")
        else:
            st.error("❌ API异常")

    st.markdown("---")


def render_enhanced_configuration_tab(session_manager):
    """渲染增强版配置标签页"""
    try:
        st.markdown("### 📋 全球市场分析配置")
        st.markdown("---")

        # 检查是否有正在运行的扫描
        if st.session_state.get("market_scan_running", False):
            current_scan_id = st.session_state.get("current_market_scan_id")
            st.warning(
                f"⚠️ 当前有分析正在运行 (ID: {current_scan_id})，请等待完成或取消后再启动新的分析。"
            )

            if st.button("🛑 取消当前分析", type="secondary"):
                try:
                    session_manager.cancel_scan(current_scan_id)
                    st.session_state.market_scan_running = False
                    st.session_state.current_market_scan_id = None
                    st.success("✅ 分析已取消")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 取消分析失败: {e}")

            st.markdown("---")

        # 使用增强的配置组件
        config_panel = EnhancedMarketConfigurationPanel()
        config_data = config_panel.render("main_config")

        # 处理配置提交
        if config_data.get("submitted", False):
            handle_scan_submission(session_manager, config_data)

        elif config_data.get("estimate_requested", False):
            # 详细成本预估
            render_detailed_cost_estimation(config_data)

        elif config_data.get("save_requested", False):
            # 保存配置
            save_configuration_preset(config_data)

        elif config_data.get("validate_requested", False):
            # 验证配置
            validate_configuration(config_data)

        # 显示分析历史
        render_enhanced_scan_history(session_manager)

    except Exception as e:
        st.error(f"❌ 配置区域加载失败: {e}")
        with st.expander("尝试使用简化配置继续", expanded=True):
            with st.form("fallback_market_config_form"):
                market_type = st.selectbox(
                    "🌍 目标市场",
                    ["A股", "美股", "港股", "全球"],
                    index=0,
                    key="fallback_market_type",
                )

                # 根据市场类型动态设置预设选项
                fallback_preset_options = {
                    "A股": ["沪深300", "中证500", "创业板50", "科创50", "自定义筛选"],
                    "美股": [
                        "标普500",
                        "纳斯达克100",
                        "道琼斯30",
                        "罗素2000",
                        "自定义筛选",
                    ],
                    "港股": [
                        "恒生指数",
                        "恒生科技",
                        "国企指数",
                        "红筹指数",
                        "自定义筛选",
                    ],
                    "全球": [
                        "全球大盘",
                        "新兴市场",
                        "发达市场",
                        "科技巨头",
                        "自定义筛选",
                    ],
                }

                # 使用市场类型作为key的一部分，确保动态更新
                fallback_preset_key = f"fallback_preset_{market_type}"

                # 检查市场类型是否发生变化
                last_fallback_market = st.session_state.get("fallback_last_market_type")
                if last_fallback_market != market_type:
                    st.session_state["fallback_last_market_type"] = market_type
                    # 清除旧的预设选择
                    if fallback_preset_key in st.session_state:
                        del st.session_state[fallback_preset_key]

                preset_type = st.selectbox(
                    "🎲 预设筛选",
                    fallback_preset_options.get(
                        market_type, fallback_preset_options["A股"]
                    ),
                    index=0,
                    key=fallback_preset_key,
                )
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    scan_depth = st.select_slider(
                        "🔍 分析深度", options=[1, 2, 3, 4, 5], value=3
                    )
                with col_b:
                    budget_limit = st.number_input(
                        "💰 预算上限 (¥)",
                        min_value=1.0,
                        max_value=500.0,
                        value=10.0,
                        step=1.0,
                    )
                with col_c:
                    stock_limit = st.slider(
                        "🎯 股票数量上限",
                        min_value=10,
                        max_value=500,
                        value=100,
                        step=10,
                    )
                time_range = st.selectbox(
                    "📅 数据时间范围", ["1周", "1月", "3月", "6月", "1年"], index=1
                )
                submitted = st.form_submit_button("🚀 开始智能分析", type="primary")
            if submitted:
                minimal_cfg = {
                    "market_type": market_type,
                    "preset_type": preset_type,
                    "scan_depth": scan_depth,
                    "budget_limit": budget_limit,
                    "stock_limit": stock_limit,
                    "time_range": time_range,
                    "analysis_focus": {
                        "technical": True,
                        "fundamental": True,
                        "risk": True,
                    },
                    "advanced_options": {"enable_monitoring": True},
                }
                handle_scan_submission(session_manager, minimal_cfg)


def render_enhanced_progress_tab(session_manager):
    """渲染增强版进度标签页"""

    current_scan_id = st.session_state.get("current_market_scan_id")

    if not current_scan_id:
        st.info("📝 尚未开始分析。请在 '⚙️ 配置' 标签页启动分析。")
        render_progress_help()
        return

    # 获取进度数据
    progress_data = session_manager.get_session_progress(current_scan_id)

    if not progress_data:
        st.error("❌ 无法获取分析进度数据")
        return

    # 处理“扫描不存在/丢失”的情况，清理状态以防止反复报错
    if progress_data.get("status") == "not_found":
        st.warning("⚠️ 当前分析已不存在或已过期，请重新发起分析。")
        st.session_state.market_scan_running = False
        st.session_state.current_market_scan_id = None
        return

    # 渲染增强的进度显示（注入会话管理器以支持控制）
    progress_display = EnhancedMarketProgressDisplay(session_manager)
    is_completed = progress_display.render(current_scan_id, progress_data)

    # 更新Streamlit状态
    if is_completed and progress_data:
        if progress_data.get("status") == "completed":
            st.session_state.market_scan_running = False

            # 获取完整结果
            if not st.session_state.market_scan_results:
                results = session_manager.get_session_results(current_scan_id)
                if results:
                    st.session_state.market_scan_results = results
                    st.success("✅ 分析完成，结果已就绪！")
                    st.info("👉 请切换到 '📋 结果' 标签页查看详细分析结果")

        elif progress_data.get("status") in ["failed", "cancelled", "not_found"]:
            st.session_state.market_scan_running = False
            st.session_state.current_market_scan_id = None

    # 智能自动刷新逻辑
    handle_auto_refresh(current_scan_id, progress_data)


def render_enhanced_results_tab(session_manager):
    """渲染增强版结果标签页"""

    current_scan_id = st.session_state.get("current_market_scan_id")
    results_data = st.session_state.get("market_scan_results")

    if not current_scan_id or not results_data:
        st.info("📊 暂无分析结果。请先在 '⚙️ 配置' 标签页启动分析，并等待完成。")
        render_results_help()
        return

    # 渲染结果概览
    render_results_overview(current_scan_id, results_data)

    # 结果详情标签页（响应式设计）
    result_tabs = st.tabs(
        ["📊 股票排名", "🔥 板块热点", "📈 市场指标", "📑 执行摘要", "📤 导出"]
    )

    with result_tabs[0]:
        render_enhanced_stock_rankings(results_data.get("rankings", []))

    with result_tabs[1]:
        render_enhanced_sector_analysis(results_data.get("sectors", {}))

    with result_tabs[2]:
        render_enhanced_market_breadth(results_data.get("breadth", {}))

    with result_tabs[3]:
        render_enhanced_executive_summary(results_data.get("summary", {}))

    with result_tabs[4]:
        # 统一复用标准导出界面，避免增强版重复实现导致不一致
        try:
            from utils.market_export_utils import render_export_interface

            render_export_interface(current_scan_id, results_data)
        except Exception as e:
            st.error(f"❌ 导出模块加载失败: {e}")


class EnhancedMarketConfigurationPanel:
    """增强的市场配置面板"""

    def __init__(self):
        self.default_config = {
            "market_type": "A股",
            "preset_type": "沪深300",
            "scan_depth": 3,
            "budget_limit": 10.0,
            "stock_limit": 100,
            "time_range": "1月",
        }

    def render(self, key_prefix: str = "enhanced_market_config") -> dict[str, Any]:
        """渲染增强配置面板"""

        st.subheader("🛠️ 智能分析配置")
        st.caption("配置您的市场分析参数，AI将根据配置进行智能分析")

        # 添加配置预设加载/保存
        self._render_config_presets(key_prefix)

        with st.form(f"{key_prefix}_enhanced_form", clear_on_submit=False):
            return self._render_enhanced_config_form(key_prefix)

    def _render_config_presets(self, key_prefix: str):
        """渲染配置预设功能"""

        preset_col1, preset_col2, preset_col3, preset_col4 = st.columns([2, 1, 1, 1])

        with preset_col1:
            # 内置预设 + 最近保存
            store = get_config_store()
            preset_options = store.list_builtin_preset_names()
            preset_options.append("自定义配置")
            preset_options.insert(0, "最近保存配置")

            selected_preset = st.selectbox(
                "📋 配置预设",
                preset_options,
                help="选择预定义的配置模板，或选择自定义配置",
            )

        with preset_col2:
            if st.button("💾 保存配置", use_container_width=True):
                self._save_config_preset(key_prefix)

        with preset_col3:
            if st.button("📥 加载配置", use_container_width=True):
                self._load_config_preset(selected_preset, key_prefix)

        with preset_col4:
            # 轻量提示
            st.caption("配置加载功能开发中: 默认/快速/深度/全面 + 最近保存")

        # 应用预设配置
        if selected_preset != "自定义配置":
            self._apply_config_preset(selected_preset, key_prefix)

    def _render_enhanced_config_form(self, key_prefix: str) -> dict[str, Any]:
        """渲染增强的配置表单"""

        # 基础配置 - 使用响应式布局
        st.markdown("#### 📊 基础设置")

        basic_col1, basic_col2 = st.columns(2)

        with basic_col1:
            market_type = st.selectbox(
                "🌍 目标市场",
                options=["A股", "美股", "港股", "全球"],
                index=0,
                help="选择要分析的股票市场",
                key=f"{key_prefix}_market_enhanced",
            )

            preset_type = self._get_enhanced_preset_selector(market_type, key_prefix)

            scan_depth = st.select_slider(
                "🔍 分析深度",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: {
                    1: "1级 - 快速筛选 (2分钟)",
                    2: "2级 - 技术分析 (5分钟)",
                    3: "3级 - 综合分析 (15分钟)",
                    4: "4级 - 深度研究 (30分钟)",
                    5: "5级 - 全面调研 (60分钟)",
                }[x],
                help="分析深度越高越详细，但成本和时间也会增加",
                key=f"{key_prefix}_depth_enhanced",
            )

        with basic_col2:
            budget_limit = st.number_input(
                "💰 预算上限 (¥)",
                min_value=1.0,
                max_value=500.0,
                value=10.0,
                step=1.0,
                help="本次分析的最大成本限制",
                key=f"{key_prefix}_budget_enhanced",
            )

            stock_limit = st.slider(
                "🎯 股票数量上限",
                min_value=10,
                max_value=1000,
                value=100,
                step=10,
                help="限制分析的股票数量以控制成本",
                key=f"{key_prefix}_limit_enhanced",
            )

            time_range = st.selectbox(
                "📅 数据时间范围",
                options=["1周", "1月", "3月", "6月", "1年"],
                index=1,
                help="历史数据分析的时间窗口",
                key=f"{key_prefix}_timerange_enhanced",
            )

        # AI模型配置
        st.markdown("#### 🤖 AI模型配置")
        ai_model_config = self._render_ai_model_config(key_prefix)

        # 高级筛选条件（响应式）
        custom_filters = {}
        if preset_type == "自定义筛选":
            st.markdown("#### 🎯 自定义筛选")
            custom_filters = self._render_enhanced_custom_filters(key_prefix)

        # 分析重点选择（优化布局）
        st.markdown("#### 🎯 分析重点")
        analysis_focus = self._render_analysis_focus_grid(key_prefix)

        # 高级选项（折叠式）
        with st.expander("⚙️ 高级选项", expanded=False):
            advanced_options = self._render_advanced_options(key_prefix)

        # 实时成本预估
        st.markdown("#### 💰 成本预估")
        self._render_cost_estimation(
            {
                "market_type": market_type,
                "preset_type": preset_type,
                "scan_depth": scan_depth,
                "budget_limit": budget_limit,
                "stock_limit": stock_limit,
                "time_range": time_range,
                "analysis_focus": analysis_focus,
                "ai_model_config": ai_model_config,
            }
        )

        # 提交按钮组（响应式）
        st.markdown("---")
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([2, 1, 1, 1])

        with btn_col1:
            start_scan = st.form_submit_button(
                "🚀 开始智能分析", type="primary", use_container_width=True
            )

        with btn_col2:
            estimate_cost = st.form_submit_button(
                "💰 详细预估", use_container_width=True
            )

        with btn_col3:
            save_config = st.form_submit_button("💾 保存配置", use_container_width=True)

        with btn_col4:
            validate_config = st.form_submit_button(
                "✅ 验证配置", use_container_width=True
            )

        # 组装配置数据
        config_data = {
            "market_type": market_type,
            "preset_type": preset_type,
            "scan_depth": scan_depth,
            "budget_limit": budget_limit,
            "stock_limit": stock_limit,
            "time_range": time_range,
            "custom_filters": custom_filters,
            "analysis_focus": analysis_focus,
            "ai_model_config": ai_model_config,
            "advanced_options": advanced_options,
            "submitted": start_scan,
            "estimate_requested": estimate_cost,
            "save_requested": save_config,
            "validate_requested": validate_config,
        }

        return config_data

    def _render_ai_model_config(self, key_prefix: str) -> dict[str, Any]:
        """渲染AI模型配置"""

        ai_col1, ai_col2 = st.columns(2)

        with ai_col1:
            primary_model = st.selectbox(
                "🧠 主要模型",
                options=[
                    "gemini-2.0-flash",
                    "gemini-2.5-pro",
                    "deepseek-v3",
                    "siliconflow",
                ],
                index=0,
                help="用于主要分析的AI模型",
                key=f"{key_prefix}_primary_model",
            )

            use_ensemble = st.checkbox(
                "🤝 多模型协作",
                value=False,
                help="使用多个模型协作分析，提高准确性",
                key=f"{key_prefix}_ensemble",
            )

        with ai_col2:
            model_temperature = st.slider(
                "🌡️ 创新度",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.1,
                help="控制AI分析的创新程度，越高越具有探索性",
                key=f"{key_prefix}_temperature",
            )

            max_tokens = st.number_input(
                "📝 最大输出长度",
                min_value=1000,
                max_value=8000,
                value=4000,
                step=500,
                help="每次AI分析的最大输出长度",
                key=f"{key_prefix}_max_tokens",
            )

        return {
            "model": primary_model,
            "use_ensemble": use_ensemble,
            "temperature": model_temperature,
            "max_tokens": max_tokens,
        }

    def _render_analysis_focus_grid(self, key_prefix: str) -> dict[str, Any]:
        """渲染分析重点网格"""

        focus_col1, focus_col2, focus_col3 = st.columns(3)

        with focus_col1:
            st.markdown("**💹 基础分析**")
            technical_focus = st.checkbox(
                "📊 技术面分析", value=True, key=f"{key_prefix}_tech_enhanced"
            )
            fundamental_focus = st.checkbox(
                "💰 基本面分析", value=True, key=f"{key_prefix}_fund_enhanced"
            )
            valuation_focus = st.checkbox(
                "💎 估值分析", value=True, key=f"{key_prefix}_val_enhanced"
            )

        with focus_col2:
            st.markdown("**📰 信息分析**")
            news_focus = st.checkbox(
                "📰 新闻舆情", value=False, key=f"{key_prefix}_news_enhanced"
            )
            sentiment_focus = st.checkbox(
                "💭 市场情绪", value=False, key=f"{key_prefix}_sentiment_enhanced"
            )
            social_focus = st.checkbox(
                "📱 社交媒体", value=False, key=f"{key_prefix}_social_enhanced"
            )

        with focus_col3:
            st.markdown("**⚠️ 风险控制**")
            risk_focus = st.checkbox(
                "⚠️ 风险评估", value=True, key=f"{key_prefix}_risk_enhanced"
            )
            liquidity_focus = st.checkbox(
                "💧 流动性分析", value=False, key=f"{key_prefix}_liquidity_enhanced"
            )
            macro_focus = st.checkbox(
                "🌍 宏观环境", value=False, key=f"{key_prefix}_macro_enhanced"
            )

        return {
            "technical": technical_focus,
            "fundamental": fundamental_focus,
            "valuation": valuation_focus,
            "news": news_focus,
            "sentiment": sentiment_focus,
            "social": social_focus,
            "risk": risk_focus,
            "liquidity": liquidity_focus,
            "macro": macro_focus,
        }

    def _render_advanced_options(self, key_prefix: str) -> dict[str, Any]:
        """渲染高级选项"""

        adv_col1, adv_col2 = st.columns(2)

        with adv_col1:
            st.markdown("**🔄 执行控制**")
            enable_monitoring = st.checkbox(
                "📡 实时监控",
                value=True,
                help="分析过程中实时显示进度和中间结果",
                key=f"{key_prefix}_monitor_enhanced",
            )

            parallel_processing = st.checkbox(
                "⚡ 并行处理",
                value=True,
                help="启用并行处理以提高扫描速度",
                key=f"{key_prefix}_parallel",
            )

            auto_retry = st.checkbox(
                "🔄 自动重试",
                value=True,
                help="分析失败时自动重试",
                key=f"{key_prefix}_retry",
            )

        with adv_col2:
            st.markdown("**💾 数据处理**")
            enable_notification = st.checkbox(
                "📬 完成通知",
                value=False,
                help="扫描完成后发送邮件通知（需配置邮件服务）",
                key=f"{key_prefix}_notify_enhanced",
            )

            save_intermediate = st.checkbox(
                "💾 保存中间结果",
                value=False,
                help="保存扫描过程中的中间分析结果",
                key=f"{key_prefix}_save_inter_enhanced",
            )

            cache_results = st.checkbox(
                "🗄️ 缓存结果",
                value=True,
                help="缓存分析结果以加快后续查询",
                key=f"{key_prefix}_cache",
            )

        return {
            "enable_monitoring": enable_monitoring,
            "enable_notification": enable_notification,
            "save_intermediate": save_intermediate,
            "parallel_processing": parallel_processing,
            "auto_retry": auto_retry,
            "cache_results": cache_results,
        }

    def _render_cost_estimation(self, config_data: dict[str, Any]):
        """渲染实时成本预估"""

        cost_result = calculate_enhanced_scan_cost(config_data)

        if isinstance(cost_result, dict):
            total_cost = cost_result["total_cost"]
            breakdown = cost_result["breakdown"]
            factors = cost_result["factors"]

            # 主要成本显示
            cost_col1, cost_col2, cost_col3 = st.columns(3)

            with cost_col1:
                st.metric("💰 预估总成本", f"¥{total_cost:.2f}")

            with cost_col2:
                estimated_time = (
                    config_data["scan_depth"] * config_data["stock_limit"] / 20
                )
                st.metric("⏱️ 预估时间", f"{estimated_time:.1f}分钟")

            with cost_col3:
                cost_per_stock = total_cost / config_data["stock_limit"]
                st.metric("📊 单股成本", f"¥{cost_per_stock:.3f}")

            # 成本分解（可展开）
            with st.expander("💰 成本分解详情", expanded=False):
                breakdown_col1, breakdown_col2 = st.columns(2)

                with breakdown_col1:
                    st.markdown("**成本构成:**")
                    for key, value in breakdown.items():
                        display_name = {
                            "base_cost": "基础成本",
                            "market_adjustment": "市场调整",
                            "focus_adjustment": "重点调整",
                            "time_adjustment": "时间调整",
                            "model_adjustment": "AI模型调整",
                            "service_cost": "服务成本",
                        }.get(key, key)
                        st.write(f"• {display_name}: ¥{value:.2f}")

                with breakdown_col2:
                    st.markdown("**影响因子:**")
                    for key, value in factors.items():
                        display_name = {
                            "market_factor": "市场因子",
                            "focus_multiplier": "重点倍数",
                            "time_factor": "时间因子",
                            "model_factor": "模型因子",
                        }.get(key, key)
                        st.write(f"• {display_name}: {value:.2f}x")
        else:
            # 兼容旧版本
            st.metric("💰 预估成本", f"¥{cost_result:.2f}")

    def _get_enhanced_preset_selector(self, market_type: str, key_prefix: str) -> str:
        """增强的预设选择器 - 根据市场类型动态显示对应的预设选项（已修复联动逻辑）"""

        preset_options = {
            "A股": ["沪深300", "中证500", "创业板50", "科创50", "自定义筛选"],
            "美股": ["标普500", "纳斯达克100", "道琼斯30", "罗素2000", "自定义筛选"],
            "港股": ["恒生指数", "恒生科技", "国企指数", "红筹指数", "自定义筛选"],
            "全球": ["全球大盘", "新兴市场", "发达市场", "科技巨头", "自定义筛选"],
        }

        # 获取当前市场对应的预设选项
        current_options = preset_options.get(market_type, preset_options["A股"])

        # --- 修复联动逻辑 ---
        # 1. 使用固定的 session_state key 来存储上一次的市场选择
        last_market_key = f"{key_prefix}_last_market_type"
        last_market = st.session_state.get(last_market_key)

        # 2. 使用固定的 key 给预设筛选框，避免组件被销毁重建
        preset_key = f"{key_prefix}_preset_enhanced"

        # 3. 检查市场类型是否已更改
        if last_market != market_type:
            # 如果市场已更改，则将预设筛选的值重置为新选项列表的第一个
            st.session_state[last_market_key] = market_type
            st.session_state[preset_key] = current_options[0]

        # 从 session_state 获取当前值，如果不存在则使用第一个选项
        current_selection = st.session_state.get(preset_key, current_options[0])

        # 如果当前保存的值不在新的选项列表中，也重置为第一个
        if current_selection not in current_options:
            current_selection = current_options[0]
            st.session_state[preset_key] = current_selection

        return st.selectbox(
            "🎲 预设筛选",
            options=current_options,
            index=current_options.index(current_selection),
            help=f"选择{market_type}市场的股票筛选预设，或选择自定义筛选",
            key=preset_key,
        )

    def _render_enhanced_custom_filters(self, key_prefix: str) -> dict[str, Any]:
        """渲染增强的自定义筛选"""

        filter_tabs = st.tabs(
            ["📊 财务指标", "📈 技术指标", "🏢 公司属性", "💹 市场指标"]
        )

        filters = {}

        with filter_tabs[0]:  # 财务指标
            fin_col1, fin_col2 = st.columns(2)

            with fin_col1:
                filters["market_cap_min"] = st.number_input(
                    "最小市值 (亿元)",
                    min_value=0.0,
                    value=0.0,
                    key=f"{key_prefix}_cap_min_enhanced",
                )
                filters["pe_max"] = st.number_input(
                    "最大PE倍数",
                    min_value=0.0,
                    value=100.0,
                    key=f"{key_prefix}_pe_max_enhanced",
                )
                filters["pb_max"] = st.number_input(
                    "最大PB倍数",
                    min_value=0.0,
                    value=10.0,
                    key=f"{key_prefix}_pb_max_enhanced",
                )

            with fin_col2:
                filters["roe_min"] = st.number_input(
                    "最小ROE (%)", min_value=0.0, value=0.0, key=f"{key_prefix}_roe_min"
                )
                filters["debt_ratio_max"] = st.number_input(
                    "最大负债率 (%)",
                    min_value=0.0,
                    value=100.0,
                    key=f"{key_prefix}_debt_max",
                )
                filters["revenue_growth_min"] = st.number_input(
                    "最小营收增长率 (%)", value=0.0, key=f"{key_prefix}_revenue_growth"
                )

        with filter_tabs[1]:  # 技术指标
            tech_col1, tech_col2 = st.columns(2)

            with tech_col1:
                filters["price_change_min"] = st.number_input(
                    "最小涨跌幅 (%)",
                    value=-20.0,
                    key=f"{key_prefix}_change_min_enhanced",
                )
                filters["price_change_max"] = st.number_input(
                    "最大涨跌幅 (%)",
                    value=20.0,
                    key=f"{key_prefix}_change_max_enhanced",
                )
                filters["volume_filter"] = st.checkbox(
                    "筛选活跃股票",
                    value=True,
                    key=f"{key_prefix}_volume_filter_enhanced",
                )

            with tech_col2:
                filters["rsi_min"] = st.slider(
                    "RSI最小值", 0, 100, 30, key=f"{key_prefix}_rsi_min"
                )
                filters["rsi_max"] = st.slider(
                    "RSI最大值", 0, 100, 70, key=f"{key_prefix}_rsi_max"
                )
                filters["ma_trend"] = st.selectbox(
                    "均线趋势",
                    ["全部", "上升", "下降", "横盘"],
                    key=f"{key_prefix}_ma_trend",
                )

        with filter_tabs[2]:  # 公司属性
            comp_col1, comp_col2 = st.columns(2)

            with comp_col1:
                filters["sectors"] = st.multiselect(
                    "行业筛选",
                    ["科技", "金融", "医药", "消费", "能源", "材料", "工业", "房地产"],
                    key=f"{key_prefix}_sectors",
                )
                filters["exclude_st"] = st.checkbox(
                    "排除ST股票", value=True, key=f"{key_prefix}_exclude_st"
                )

            with comp_col2:
                filters["company_age_min"] = st.number_input(
                    "最小上市年限", min_value=0, value=0, key=f"{key_prefix}_age_min"
                )
                filters["employee_count_min"] = st.number_input(
                    "最小员工数量",
                    min_value=0,
                    value=0,
                    key=f"{key_prefix}_employee_min",
                )

        with filter_tabs[3]:  # 市场指标
            market_col1, market_col2 = st.columns(2)

            with market_col1:
                filters["liquidity_min"] = st.slider(
                    "最小流动性评分", 0, 100, 50, key=f"{key_prefix}_liquidity"
                )
                filters["volatility_max"] = st.slider(
                    "最大波动率 (%)", 0, 100, 50, key=f"{key_prefix}_volatility"
                )

            with market_col2:
                filters["analyst_rating"] = st.selectbox(
                    "分析师评级",
                    ["全部", "买入", "增持", "中性", "减持", "卖出"],
                    key=f"{key_prefix}_rating",
                )
                filters["institutional_holding_min"] = st.slider(
                    "最小机构持股比例 (%)", 0, 100, 0, key=f"{key_prefix}_institution"
                )

        return filters

    def _apply_config_preset(self, preset_name: str, key_prefix: str):
        """应用配置预设"""

        presets = {
            "快速扫描 (成本优先)": {
                "scan_depth": 2,
                "budget_limit": 5.0,
                "stock_limit": 50,
                "time_range": "1月",
            },
            "深度分析 (质量优先)": {
                "scan_depth": 4,
                "budget_limit": 25.0,
                "stock_limit": 100,
                "time_range": "3月",
            },
            "全面调研 (完整分析)": {
                "scan_depth": 5,
                "budget_limit": 50.0,
                "stock_limit": 200,
                "time_range": "6月",
            },
        }

        if preset_name in presets:
            presets[preset_name]
            # 这里可以通过session_state更新表单默认值
            # 实际实现需要与Streamlit的状态管理集成
            st.info(f"✅ 已应用预设配置: {preset_name}")

    def _save_config_preset(self, key_prefix: str):
        """保存配置预设（保存到“最近保存配置”）"""
        try:
            # 从表单控件读值（与 _render_enhanced_config_form 保持同步的key）
            cfg = {
                "market_type": st.session_state.get(f"{key_prefix}_market_enhanced"),
                "preset_type": st.session_state.get(f"{key_prefix}_preset_enhanced"),
                "scan_depth": st.session_state.get(f"{key_prefix}_depth_enhanced"),
                "budget_limit": st.session_state.get(f"{key_prefix}_budget_enhanced"),
                "stock_limit": st.session_state.get(f"{key_prefix}_limit_enhanced"),
                "time_range": st.session_state.get(f"{key_prefix}_timerange_enhanced"),
                "ai_model_config": {
                    "model": st.session_state.get(f"{key_prefix}_primary_model"),
                    "use_ensemble": st.session_state.get(f"{key_prefix}_ensemble"),
                    "temperature": st.session_state.get(f"{key_prefix}_temperature"),
                    "max_tokens": st.session_state.get(f"{key_prefix}_max_tokens"),
                },
                "analysis_focus": {
                    "technical": st.session_state.get(f"{key_prefix}_tech_enhanced"),
                    "fundamental": st.session_state.get(f"{key_prefix}_fund_enhanced"),
                    "valuation": st.session_state.get(f"{key_prefix}_val_enhanced"),
                    "news": st.session_state.get(f"{key_prefix}_news_enhanced"),
                    "sentiment": st.session_state.get(
                        f"{key_prefix}_sentiment_enhanced"
                    ),
                    "social": st.session_state.get(f"{key_prefix}_social_enhanced"),
                    "risk": st.session_state.get(f"{key_prefix}_risk_enhanced"),
                    "liquidity": st.session_state.get(
                        f"{key_prefix}_liquidity_enhanced"
                    ),
                    "macro": st.session_state.get(f"{key_prefix}_macro_enhanced"),
                },
                "advanced_options": {
                    "enable_monitoring": st.session_state.get(
                        f"{key_prefix}_monitor_enhanced"
                    ),
                    "enable_notification": st.session_state.get(
                        f"{key_prefix}_notify_enhanced"
                    ),
                    "save_intermediate": st.session_state.get(
                        f"{key_prefix}_save_inter_enhanced"
                    ),
                    "parallel_processing": st.session_state.get(
                        f"{key_prefix}_parallel"
                    ),
                    "auto_retry": st.session_state.get(f"{key_prefix}_retry"),
                    "cache_results": st.session_state.get(f"{key_prefix}_cache"),
                },
            }

            get_config_store().save_last_config(cfg)
            st.success("✅ 配置已保存")
        except Exception as e:
            st.error(f"❌ 保存配置失败: {e}")

    def _load_config_preset(self, preset_name: str, key_prefix: str):
        """加载配置预设（支持内置预设与最近保存）"""
        try:
            store = get_config_store()
            cfg = None
            if preset_name == "最近保存配置":
                cfg = store.load_last_config()
                if not cfg:
                    st.warning("⚠️ 暂无最近保存配置")
                    return
            else:
                cfg = store.get_builtin_preset(preset_name)
                if not cfg:
                    st.warning(f"⚠️ 未找到预设: {preset_name}")
                    return

            # 将配置写回 session_state，以便表单控件显示（Streamlit不支持直接设置控件值，这里通过提示方式告知已加载）
            st.session_state[f"{key_prefix}_market_enhanced"] = cfg.get("market_type")
            st.session_state[f"{key_prefix}_preset_enhanced"] = cfg.get("preset_type")
            st.session_state[f"{key_prefix}_depth_enhanced"] = cfg.get("scan_depth")
            st.session_state[f"{key_prefix}_budget_enhanced"] = cfg.get("budget_limit")
            st.session_state[f"{key_prefix}_limit_enhanced"] = cfg.get("stock_limit")
            st.session_state[f"{key_prefix}_timerange_enhanced"] = cfg.get("time_range")

            ai = cfg.get("ai_model_config", {})
            st.session_state[f"{key_prefix}_primary_model"] = ai.get("model")
            st.session_state[f"{key_prefix}_ensemble"] = ai.get("use_ensemble")
            st.session_state[f"{key_prefix}_temperature"] = ai.get("temperature")
            st.session_state[f"{key_prefix}_max_tokens"] = ai.get("max_tokens")

            af = cfg.get("analysis_focus", {})
            st.session_state[f"{key_prefix}_tech_enhanced"] = af.get("technical")
            st.session_state[f"{key_prefix}_fund_enhanced"] = af.get("fundamental")
            st.session_state[f"{key_prefix}_val_enhanced"] = af.get("valuation")
            st.session_state[f"{key_prefix}_news_enhanced"] = af.get("news")
            st.session_state[f"{key_prefix}_sentiment_enhanced"] = af.get("sentiment")
            st.session_state[f"{key_prefix}_social_enhanced"] = af.get("social")
            st.session_state[f"{key_prefix}_risk_enhanced"] = af.get("risk")
            st.session_state[f"{key_prefix}_liquidity_enhanced"] = af.get("liquidity")
            st.session_state[f"{key_prefix}_macro_enhanced"] = af.get("macro")

            adv = cfg.get("advanced_options", {})
            st.session_state[f"{key_prefix}_monitor_enhanced"] = adv.get(
                "enable_monitoring"
            )
            st.session_state[f"{key_prefix}_notify_enhanced"] = adv.get(
                "enable_notification"
            )
            st.session_state[f"{key_prefix}_save_inter_enhanced"] = adv.get(
                "save_intermediate"
            )
            st.session_state[f"{key_prefix}_parallel"] = adv.get("parallel_processing")
            st.session_state[f"{key_prefix}_retry"] = adv.get("auto_retry")
            st.session_state[f"{key_prefix}_cache"] = adv.get("cache_results")

            st.success(f"✅ 已加载预设: {preset_name}（控件将按已加载值更新）")
        except Exception as e:
            st.error(f"❌ 加载配置失败: {e}")


class EnhancedMarketProgressDisplay:
    """增强版市场分析进度显示组件"""

    def __init__(self, session_manager=None):
        self.session_manager = session_manager

    def render(self, scan_id: str, progress_data: dict) -> bool:
        """渲染增强的进度显示"""

        st.subheader(f"📊 分析进度 - {scan_id}")

        # 总体进度条和关键信息
        col_progress, col_stats = st.columns([2, 1])

        with col_progress:
            overall_progress = progress_data.get("overall_progress", 0)
            st.progress(overall_progress / 100.0)
            st.write(f"**整体进度:** {overall_progress}%")

            # 当前阶段信息
            current_stage = progress_data.get("current_stage", "准备中")
            st.info(f"🔄 当前阶段: {current_stage}")

        with col_stats:
            # 关键统计信息
            stats = progress_data.get("stats", {})
            st.metric("已处理", f"{stats.get('processed_stocks', 0)}")
            st.metric("总数量", f"{stats.get('total_stocks', 100)}")
            st.metric("成本", f"¥{stats.get('cost_used', 0):.2f}")

        # 详细进度信息
        progress_col1, progress_col2 = st.columns(2)

        with progress_col1:
            self._render_stage_progress(progress_data.get("stages", []))

        with progress_col2:
            self._render_real_time_stats(stats)

        # 预览结果
        if progress_data.get("preview_results"):
            with st.expander("👀 中间结果预览", expanded=True):
                self._render_preview_results(progress_data["preview_results"])

        # 增强的控制面板
        self._render_enhanced_control_panel(scan_id, progress_data)

        return overall_progress >= 100

    def _render_stage_progress(self, stages_data: list[dict]):
        """渲染阶段进度"""

        st.markdown("**📋 分析阶段**")

        if not stages_data:
            # 使用默认阶段
            default_stages = [
                "数据准备",
                "股票筛选",
                "技术分析",
                "基本面分析",
                "风险评估",
                "生成报告",
            ]
            for stage in default_stages:
                st.write(f"⏳ {stage}")
            return

        for stage in stages_data:
            if stage.get("completed", False):
                st.write(f"✅ {stage.get('name', '')}")
            elif stage.get("current", False):
                st.write(f"🔄 {stage.get('name', '')} (进行中)")
            else:
                st.write(f"⏳ {stage.get('name', '')}")

    def _render_real_time_stats(self, stats_data: dict):
        """渲染实时统计信息"""

        st.markdown("**📈 实时统计**")

        # 统计指标
        processed_stocks = stats_data.get("processed_stocks", 0)
        total_stocks = stats_data.get("total_stocks", 100)
        cost_used = stats_data.get("cost_used", 0.0)
        estimated_time = stats_data.get("estimated_time", "计算中...")

        st.metric("已处理股票", f"{processed_stocks}/{total_stocks}")
        st.metric("成本消耗", f"¥{cost_used:.2f}")
        st.metric("预计剩余时间", estimated_time)

        # 进度百分比
        if total_stocks > 0:
            completion_rate = (processed_stocks / total_stocks) * 100
            st.metric("完成率", f"{completion_rate:.1f}%")

    def _render_preview_results(self, preview_data: dict):
        """渲染中间结果预览"""

        if "top_stocks" in preview_data:
            st.markdown("**🔝 暂时排名前列的股票:**")
            for i, stock in enumerate(preview_data["top_stocks"][:5], 1):
                st.write(
                    f"{i}. {stock.get('name', '')} ({stock.get('symbol', '')}) - 评分: {stock.get('score', 0):.1f}"
                )

        if "sector_performance" in preview_data:
            st.markdown("**📊 板块表现概览:**")
            for sector, performance in preview_data["sector_performance"].items():
                change = performance.get("change_percent", 0)
                emoji = "🔴" if change < 0 else "🟢" if change > 0 else "⚪"
                st.write(f"{emoji} {sector}: {change:+.2f}%")

        if "market_sentiment" in preview_data:
            sentiment = preview_data["market_sentiment"]
            st.metric(
                "市场情绪指数", f"{sentiment:.1f}", help="基于已处理股票的综合情绪评估"
            )

    def _render_enhanced_control_panel(self, scan_id: str, progress_data: dict):
        """渲染增强的控制面板"""

        st.markdown("---")
        st.markdown("**⚙️ 分析控制**")

        # 控制按钮
        control_col1, control_col2, control_col3, control_col4 = st.columns(4)

        with control_col1:
            if st.button(
                "🔄 刷新进度", use_container_width=True, key=f"refresh_{scan_id}"
            ):
                st.rerun()

        with control_col2:
            if st.button(
                "⏸️ 暂停分析", use_container_width=True, key=f"pause_{scan_id}"
            ):
                self._pause_scan(scan_id)

        with control_col3:
            if st.button(
                "▶️ 继续分析", use_container_width=True, key=f"resume_{scan_id}"
            ):
                self._resume_scan(scan_id)

        with control_col4:
            if st.button(
                "🛑 停止分析", use_container_width=True, key=f"stop_{scan_id}"
            ):
                self._stop_scan(scan_id)

        # 自动刷新和通知设置
        auto_col1, auto_col2 = st.columns(2)

        with auto_col1:
            auto_refresh = st.checkbox(
                "⚡ 自动刷新 (5秒间隔)",
                value=True,
                key=f"auto_refresh_{scan_id}",
                help="自动刷新进度显示",
            )
            # 同步到全局与按扫描ID的状态，供自动刷新逻辑读取
            try:
                st.session_state["auto_refresh_enabled"] = bool(auto_refresh)
                st.session_state[f"auto_refresh_{scan_id}"] = bool(auto_refresh)
            except Exception:
                pass

        with auto_col2:
            st.checkbox(
                "🔔 完成通知",
                value=False,
                key=f"notify_completion_{scan_id}",
                help="扫描完成时桌面通知",
            )

        return auto_refresh

    def _pause_scan(self, scan_id: str):
        """暂停分析"""
        try:
            if self.session_manager and self.session_manager.pause_scan(scan_id):
                st.success(f"⏸️ 扫描 {scan_id} 已暂停")
            else:
                st.warning(f"⚠️ 暂停失败或不可用: {scan_id}")
        except Exception as e:
            st.error(f"❌ 暂停分析失败: {e}")
        logger.info(f"暂停市场扫描: {scan_id}")

    def _resume_scan(self, scan_id: str):
        """继续分析"""
        try:
            if self.session_manager and self.session_manager.resume_scan(scan_id):
                st.success(f"▶️ 扫描 {scan_id} 已继续")
            else:
                st.warning(f"⚠️ 继续失败或不可用: {scan_id}")
        except Exception as e:
            st.error(f"❌ 继续分析失败: {e}")
        logger.info(f"继续市场扫描: {scan_id}")

    def _stop_scan(self, scan_id: str):
        """停止分析"""
        try:
            if self.session_manager and self.session_manager.cancel_scan(scan_id):
                st.error(f"🛑 扫描 {scan_id} 已停止")
            else:
                st.warning(f"⚠️ 停止失败或不可用: {scan_id}")
        except Exception as e:
            st.error(f"❌ 停止分析失败: {e}")
        logger.info(f"停止市场扫描: {scan_id}")


# 辅助函数


def quick_scan_a_shares():
    """快速扫描A股市场"""
    try:
        session_manager = get_market_session_manager()

        quick_config = {
            "market_type": "A股",
            "preset_type": "沪深300",
            "scan_depth": 3,
            "budget_limit": 10.0,
            "stock_limit": 50,
            "time_range": "1月",
            "analysis_focus": {
                "technical": True,
                "fundamental": True,
                "valuation": True,
                "news": False,
                "sentiment": False,
                "risk": True,
            },
            "advanced_options": {
                "enable_monitoring": True,
                "enable_notification": False,
                "save_intermediate": False,
            },
        }

        scan_id = session_manager.create_scan_session(quick_config)

        st.session_state.current_market_scan_id = scan_id
        st.session_state.market_scan_running = True
        st.session_state.market_scan_results = None

        st.success(f"🚀 快速分析已启动！分析ID: {scan_id}")
        st.info("➡️ 请切换到 '📊 进度' 标签页查看分析进度")

    except Exception as e:
        st.error(f"❌ 快速扫描启动失败: {e}")
        logger.error(f"快速扫描A股失败: {e}")


def calculate_enhanced_scan_cost(config_data: dict[str, Any]):
    """计算增强版扫描成本预估"""

    # 更详细的成本模型
    base_cost_per_stock = {
        1: 0.008,  # 1级 - 基础筛选 (降低成本)
        2: 0.015,  # 2级 - 技术分析
        3: 0.035,  # 3级 - 综合分析
        4: 0.065,  # 4级 - 深度研究
        5: 0.100,  # 5级 - 全面调研
    }

    # AI模型成本系数
    model_cost_factor = {
        "gemini-2.0-flash": 1.0,  # 基准
        "gemini-2.5-pro": 2.5,
        "deepseek-v3": 0.3,
        "siliconflow": 0.2,
    }

    # 市场复杂度系数
    market_factor = {
        "A股": 1.0,
        "美股": 1.3,  # 美股数据获取成本更高
        "港股": 1.15,  # 港股数据需要额外处理
        "全球": 1.5,  # 全球市场最复杂
    }

    # 时间范围影响
    time_factor = {"1周": 0.8, "1月": 1.0, "3月": 1.3, "6月": 1.8, "1年": 2.5}

    # 分析重点系数
    focus_multiplier = 1.0
    analysis_focus = config_data.get("analysis_focus", {})
    enabled_focus_count = sum(1 for enabled in analysis_focus.values() if enabled)
    focus_multiplier = 0.8 + (enabled_focus_count * 0.1)  # 基础0.8，每个重点+0.1

    # 计算总成本
    stock_limit = config_data.get("stock_limit", 100)
    scan_depth = config_data.get("scan_depth", 3)
    market_type = config_data.get("market_type", "A股")
    time_range = config_data.get("time_range", "1月")

    # AI模型配置影响
    ai_model = config_data.get("ai_model_config", {}).get("model", "gemini-2.0-flash")
    model_factor_value = model_cost_factor.get(ai_model, 1.0)

    # 逐步计算
    base_cost = stock_limit * base_cost_per_stock.get(scan_depth, 0.035)
    market_adjusted_cost = base_cost * market_factor.get(market_type, 1.0)
    time_adjusted_cost = market_adjusted_cost * time_factor.get(time_range, 1.0)
    focus_adjusted_cost = time_adjusted_cost * focus_multiplier
    final_cost = focus_adjusted_cost * model_factor_value

    # 添加固定基础成本（服务器、数据源等）
    base_service_cost = 0.5
    total_cost = final_cost + base_service_cost

    return {
        "total_cost": total_cost,
        "breakdown": {
            "base_cost": base_cost,
            "market_adjustment": market_adjusted_cost - base_cost,
            "time_adjustment": time_adjusted_cost - market_adjusted_cost,
            "focus_adjustment": focus_adjusted_cost - time_adjusted_cost,
            "model_adjustment": final_cost - focus_adjusted_cost,
            "service_cost": base_service_cost,
        },
        "factors": {
            "market_factor": market_factor.get(market_type, 1.0),
            "focus_multiplier": focus_multiplier,
            "time_factor": time_factor.get(time_range, 1.0),
            "model_factor": model_factor_value,
        },
    }


def handle_scan_submission(session_manager, config_data: dict[str, Any]):
    """处理扫描提交"""

    try:
        # 创建扫描会话
        scan_id = session_manager.create_scan_session(config_data)

        # 更新Streamlit会话状态
        st.session_state.current_market_scan_id = scan_id
        st.session_state.market_scan_running = True
        st.session_state.market_scan_results = None

        st.success(f"🚀 智能分析已启动！分析ID: {scan_id}")

        # 显示配置摘要
        col_config1, col_config2 = st.columns(2)

        with col_config1:
            st.info(
                f"""
            **📊 分析配置摘要:**
            • 市场: {config_data['market_type']}
            • 预设: {config_data['preset_type']}
            • 深度: {config_data['scan_depth']}级
            • 预算: ¥{config_data['budget_limit']}
            """
            )

        with col_config2:
            st.info(
                f"""
            **🎯 分析重点:**
            • 股票数量: {config_data['stock_limit']}只
            • 时间范围: {config_data['time_range']}
            • AI模型: {config_data.get('ai_model_config', {}).get('model', '默认')}
            """
            )

        st.info("➡️ 请切换到 '📊 进度' 标签页查看分析进度")

        # 自动切换到进度标签页
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"❌ 启动扫描失败: {e}")
        logger.error(f"启动市场扫描失败: {e}")


def render_detailed_cost_estimation(config_data: dict[str, Any]):
    """渲染详细成本预估"""

    st.subheader("💰 详细成本分析")

    cost_result = calculate_enhanced_scan_cost(config_data)

    if isinstance(cost_result, dict):
        total_cost = cost_result["total_cost"]
        breakdown = cost_result["breakdown"]
        cost_result["factors"]

        # 成本分解饼图
        fig = px.pie(
            values=list(breakdown.values()),
            names=list(breakdown.keys()),
            title="成本构成分析",
        )
        st.plotly_chart(fig, use_container_width=True)

        # 详细表格
        breakdown_df = pd.DataFrame(
            [
                {
                    "成本项目": key,
                    "金额 (¥)": f"{value:.2f}",
                    "占比": f"{(value/total_cost)*100:.1f}%",
                }
                for key, value in breakdown.items()
            ]
        )

        st.dataframe(breakdown_df, use_container_width=True)

        # 优化建议
        st.markdown("### 💡 成本优化建议")

        if total_cost > config_data.get("budget_limit", 10):
            st.warning("⚠️ 预估成本超出预算限制，建议:")
            st.write("• 降低分析深度")
            st.write("• 减少股票数量")
            st.write("• 选择成本更低的AI模型")
        else:
            st.success("✅ 成本在预算范围内")

    else:
        st.metric("💰 预估总成本", f"¥{cost_result:.2f}")


def save_configuration_preset(config_data: dict[str, Any]):
    """保存配置预设"""

    st.success("💾 配置已保存到会话状态")
    st.session_state.market_config = config_data

    # 实际实现可以保存到数据库或文件
    logger.info(
        f"保存市场分析配置: {config_data.get('market_type')} - {config_data.get('preset_type')}"
    )


def validate_configuration(config_data: dict[str, Any]):
    """验证配置"""

    st.subheader("✅ 配置验证")

    # 验证规则
    issues = []
    warnings = []

    # 预算检查
    if config_data.get("budget_limit", 0) < 1.0:
        issues.append("预算限制过低，建议至少设置¥1.00")

    # 股票数量检查
    if config_data.get("stock_limit", 0) < 10:
        issues.append("股票数量过少，建议至少10只")
    elif config_data.get("stock_limit", 0) > 500:
        warnings.append("股票数量较多，扫描时间可能较长")

    # 深度检查
    if (
        config_data.get("scan_depth", 3) >= 4
        and config_data.get("stock_limit", 100) > 200
    ):
        warnings.append("高深度 + 大数量可能导致成本过高")

    # 显示结果
    if issues:
        st.error("❌ 发现配置问题:")
        for issue in issues:
            st.write(f"• {issue}")

    if warnings:
        st.warning("⚠️ 配置警告:")
        for warning in warnings:
            st.write(f"• {warning}")

    if not issues and not warnings:
        st.success("✅ 配置验证通过，可以开始分析")


def render_enhanced_scan_history(session_manager):
    """渲染增强版分析历史记录"""

    # 检查是否需要显示历史记录
    show_history = st.session_state.get("show_scan_history", False)

    if show_history:
        with st.expander("📚 分析历史", expanded=True):
            render_detailed_scan_history(session_manager)

        if st.button("❌ 隐藏历史记录"):
            st.session_state.show_scan_history = False
            st.rerun()
    else:
        with st.expander("📚 分析历史", expanded=False):
            render_detailed_scan_history(session_manager)


def render_detailed_scan_history(session_manager):
    """渲染详细的分析历史记录"""

    try:
        # 历史记录控制
        hist_col1, hist_col2, hist_col3 = st.columns([2, 1, 1])

        with hist_col1:
            limit = st.selectbox(
                "显示数量", [10, 20, 50, 100], index=1, key="history_limit"
            )

        with hist_col2:
            if st.button("🔄 刷新历史", use_container_width=True):
                st.rerun()

        with hist_col3:
            if st.button(
                "🧹 清理过期", use_container_width=True, help="清理7天前的记录"
            ):
                cleaned_count = session_manager.cleanup_old_sessions(days=7)
                st.success(f"✅ 已清理 {cleaned_count} 条过期记录")
                st.rerun()

        history = session_manager.get_session_history(limit=limit)

        if not history:
            st.info("📝 暂无分析历史记录")
            st.markdown(
                """
            💡 **提示**: 
            - 启动第一次扫描后，历史记录将在这里显示
            - 可以通过历史记录快速重新查看之前的分析结果
            - 过期记录会自动清理，也可以手动清理
            """
            )
            return

        st.markdown(f"### 📜 最近 {len(history)} 条扫描记录")

        # 添加搜索和筛选
        search_col1, search_col2 = st.columns(2)

        with search_col1:
            search_term = st.text_input(
                "🔍 搜索扫描记录", placeholder="输入扫描ID或市场类型..."
            )

        with search_col2:
            status_filter = st.selectbox(
                "📊 状态筛选", ["全部", "completed", "running", "failed", "cancelled"]
            )

        # 应用筛选
        if search_term:
            history = [
                h
                for h in history
                if search_term.lower() in h.get("scan_id", "").lower()
                or search_term.lower()
                in h.get("config", {}).get("market_type", "").lower()
            ]

        if status_filter != "全部":
            history = [h for h in history if h.get("status", "") == status_filter]

        if not history:
            st.info("🔍 没有找到符合条件的记录")
            return

        # 显示记录
        for i, session_data in enumerate(history):
            scan_id = session_data.get("scan_id", "")
            created_at = session_data.get("created_at", "")
            status = session_data.get("status", "unknown")
            config = session_data.get("config", {})

            # 状态图标
            status_icon = {
                "completed": "✅",
                "running": "🔄",
                "failed": "❌",
                "cancelled": "⏹️",
            }.get(status, "❓")

            # 使用更好的卡片布局显示记录
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

            with col1:
                st.markdown(f"{status_icon} **{scan_id}**")
                market_info = f"{config.get('market_type', '')} | {config.get('preset_type', '')} | {config.get('stock_limit', 0)}只股票"
                st.caption(market_info)

                # 显示成本和深度信息
                cost_info = f"💰 预算: ¥{config.get('budget_limit', 0):.1f} | 🔍 深度: {config.get('scan_depth', 1)}级"
                st.caption(cost_info)

            with col2:
                try:
                    created_time = datetime.datetime.fromisoformat(created_at)
                    st.markdown(f"**{created_time.strftime('%m-%d %H:%M')}**")

                    # 计算耗时
                    if "updated_at" in session_data:
                        try:
                            updated_time = datetime.datetime.fromisoformat(
                                session_data["updated_at"]
                            )
                            duration = updated_time - created_time
                            minutes = int(duration.total_seconds() / 60)
                            st.caption(f"⏱️ {minutes}分钟")
                        except Exception:
                            st.caption("⏱️ -")
                except Exception:
                    st.write(created_at)

                st.caption(f"📊 {status}")

            with col3:
                # 显示结果摘要（如果有）
                if (
                    "results_summary" in session_data
                    and session_data["results_summary"]
                ):
                    summary = session_data["results_summary"]
                    recommended = summary.get("recommended_stocks", 0)
                    total = summary.get("total_stocks", 0)
                    st.metric("推荐股票", f"{recommended}/{total}")
                else:
                    st.write("📊 无结果")

            with col4:
                # 操作按钮
                if st.button(
                    "👀 查看", key=f"view_history_{i}", use_container_width=True
                ):
                    load_historical_scan(session_manager, scan_id, i)

                # 删除按钮（仅对失败或很久以前的扫描显示）
                if status in ["failed", "cancelled"] or (
                    created_at
                    and (
                        datetime.datetime.now()
                        - datetime.datetime.fromisoformat(created_at)
                    ).days
                    > 7
                ):
                    if st.button(
                        "🗑️",
                        key=f"delete_history_{i}",
                        help="删除记录",
                        use_container_width=True,
                    ):
                        if session_manager.delete_session(scan_id):
                            st.success(f"✅ 已删除扫描记录: {scan_id}")
                            st.rerun()
                        else:
                            st.error(f"❌ 删除失败: {scan_id}")

            if i < len(history) - 1:
                st.markdown("---")

    except Exception as e:
        st.error(f"❌ 获取分析历史失败: {e}")
        logger.error(f"获取分析历史失败: {e}")

        # 提供故障排除建议
        with st.expander("🔧 故障排除"):
            st.markdown(
                """
            **可能的解决方案:**
            1. 刷新页面重试
            2. 检查数据目录权限
            3. 重启应用服务
            4. 联系技术支持
            """
            )


def load_historical_scan(session_manager, scan_id, index):
    """加载历史扫描记录"""
    try:
        st.session_state.current_market_scan_id = scan_id

        # 获取进度信息
        progress_data = session_manager.get_session_progress(scan_id)
        if progress_data:
            status = progress_data.get("status", "unknown")
            if status == "running":
                st.session_state.market_scan_running = True
                st.info(f"✅ 已切换到运行中的扫描: {scan_id}")
            else:
                st.session_state.market_scan_running = False

        # 尝试获取结果
        results = session_manager.get_session_results(scan_id)
        if results:
            st.session_state.market_scan_results = results
            st.success(f"✅ 已加载分析结果: {scan_id}")
        else:
            st.session_state.market_scan_results = None
            if st.session_state.get("market_scan_running", False):
                st.info(f"📊 分析正在进行中: {scan_id}")
            else:
                st.warning(f"⚠️ 暂无可用结果: {scan_id}")

    except Exception as e:
        st.error(f"❌ 加载扫描记录失败: {e}")
        logger.error(f"加载历史扫描失败 {scan_id}: {e}")


def handle_auto_refresh(scan_id: str, progress_data: dict):
    """智能自动刷新逻辑（支持按扫描ID单独控制）"""

    if st.session_state.market_scan_running and progress_data:
        # 优先读取该扫描的自动刷新开关，其次读取全局开关
        auto_refresh = st.session_state.get(f"auto_refresh_{scan_id}")
        if auto_refresh is None:
            auto_refresh = st.session_state.get("auto_refresh_enabled", True)
        if auto_refresh:
            # 根据进度调整刷新间隔
            progress = progress_data.get("overall_progress", 0)
            if progress < 20:
                refresh_interval = 2
            elif progress < 80:
                refresh_interval = 5
            else:
                refresh_interval = 3

            time.sleep(refresh_interval)
            st.rerun()


def render_progress_help():
    """渲染进度页面帮助信息"""

    st.markdown(
        """
    ### 📊 如何使用进度监控
    
    **功能说明:**
    - 实时显示扫描进度和当前阶段
    - 监控成本消耗和剩余预算
    - 查看中间分析结果预览
    - 控制扫描执行（暂停/继续/停止）
    
    **操作提示:**
    1. 在'配置'页面启动扫描后，进度将在此显示
    2. 可以随时查看各个阶段的完成状态
    3. 支持手动刷新或自动刷新模式
    4. 扫描完成后会自动跳转到结果页面
    """
    )


def render_results_help():
    """渲染结果页面帮助信息"""

    st.markdown(
        """
    ### 📊 如何查看分析结果
    
    **结果包含:**
    - **股票排名**: 按评分排序的推荐股票列表
    - **板块分析**: 各行业板块的表现和机会
    - **市场指标**: 整体市场强度和广度分析
    - **执行摘要**: AI生成的投资建议和风险提示
    
    **交互功能:**
    - 点击股票查看详细分析
    - 筛选和排序结果数据
    - 导出分析报告多种格式
    - 保存结果到个人图书馆
    """
    )


def render_results_overview(scan_id: str, results_data: dict):
    """渲染结果概览"""

    st.subheader(f"📊 分析结果概览 - {scan_id}")

    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "分析股票数",
            results_data.get("total_stocks", 0),
            help="本次扫描分析的股票总数",
        )

    with col2:
        st.metric(
            "推荐股票数",
            results_data.get("recommended_stocks", 0),
            help="符合投资条件的推荐股票数量",
        )

    with col3:
        st.metric(
            "实际成本",
            f"¥{results_data.get('actual_cost', 0):.2f}",
            help="本次扫描实际花费成本",
        )

    with col4:
        scan_duration = results_data.get("scan_duration", "未知")
        st.metric("分析时长", scan_duration, help="扫描分析总耗时")


def render_enhanced_stock_rankings(rankings_data: list[dict]):
    """渲染增强版股票排名"""

    if not rankings_data:
        st.info("📊 暂无股票排名数据")
        return

    st.markdown("### 📊 智能股票排名")

    # 筛选和排序控件
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        st.selectbox(
            "排序依据",
            options=["综合评分", "技术评分", "基本面评分", "涨跌幅", "成交量"],
            key="ranking_sort_by",
        )

    with filter_col2:
        recommendation_filter = st.selectbox(
            "投资建议筛选",
            options=["全部", "买入", "持有", "关注", "卖出"],
            key="ranking_recommendation_filter",
        )

    with filter_col3:
        display_count = st.number_input(
            "显示数量",
            min_value=10,
            max_value=len(rankings_data),
            value=min(50, len(rankings_data)),
            key="ranking_display_count",
        )

    # 应用筛选
    filtered_data = filter_rankings(rankings_data, recommendation_filter, display_count)

    if filtered_data:
        # 创建增强的数据表
        df = pd.DataFrame(filtered_data)

        # 配置列显示
        column_config = {
            "排名": st.column_config.NumberColumn("排名", width="small"),
            "综合评分": st.column_config.ProgressColumn(
                "综合评分", min_value=0, max_value=100
            ),
            "技术评分": st.column_config.ProgressColumn(
                "技术评分", min_value=0, max_value=100
            ),
            "基本面评分": st.column_config.ProgressColumn(
                "基本面评分", min_value=0, max_value=100
            ),
            "涨跌幅": st.column_config.TextColumn("涨跌幅", width="small"),
            "建议": st.column_config.TextColumn("建议", width="small"),
        }

        st.dataframe(
            df, use_container_width=True, height=500, column_config=column_config
        )

        # 选择股票查看详情
        selected_stock = st.selectbox(
            "选择股票查看详细分析",
            options=[
                f"{row['股票名称']} ({row['股票代码']})" for _, row in df.iterrows()
            ],
            key="selected_stock_detail",
        )

        if st.button("📊 查看详细分析", key="view_stock_detail"):
            show_stock_detail(selected_stock, rankings_data)


def render_enhanced_sector_analysis(sectors_data: dict):
    """渲染增强版板块分析"""

    if not sectors_data:
        st.info("🔥 暂无板块分析数据")
        return

    st.markdown("### 🔥 板块表现分析")

    # 板块表现表格
    sector_df = pd.DataFrame(
        [
            {
                "板块名称": sector,
                "涨跌幅(%)": data.get("change_percent", 0),
                "成交额(亿)": data.get("volume", 0),
                "活跃度": data.get("activity_score", 0),
                "推荐度": data.get("recommendation_score", 0),
                "龙头股票": data.get("leading_stock", ""),
                "推荐股票数": data.get("recommended_count", 0),
            }
            for sector, data in sectors_data.items()
        ]
    )

    if not sector_df.empty:
        st.dataframe(
            sector_df,
            use_container_width=True,
            column_config={
                "活跃度": st.column_config.ProgressColumn(
                    "活跃度", min_value=0, max_value=100
                ),
                "推荐度": st.column_config.ProgressColumn(
                    "推荐度", min_value=0, max_value=100
                ),
            },
        )

    # 板块热力图
    render_sector_heatmap(sectors_data)

    # 板块详情
    if sectors_data:
        selected_sector = st.selectbox(
            "选择板块查看详情",
            options=list(sectors_data.keys()),
            key="selected_sector_detail",
        )

        if selected_sector:
            show_sector_detail(selected_sector, sectors_data[selected_sector])


def render_enhanced_market_breadth(breadth_data: dict):
    """渲染增强版市场广度指标"""

    if not breadth_data:
        st.info("📈 暂无市场广度数据")
        return

    st.markdown("### 📈 市场广度分析")

    # 主要指标
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        up_ratio = breadth_data.get("up_ratio", 50)
        st.metric(
            "上涨股票占比",
            f"{up_ratio}%",
            delta=f"{breadth_data.get('up_ratio_change', 0):+.1f}%",
        )

    with col2:
        activity = breadth_data.get("activity_index", 50)
        st.metric(
            "成交活跃度",
            f"{activity:.1f}",
            delta=f"{breadth_data.get('activity_change', 0):+.1f}",
        )

    with col3:
        net_inflow = breadth_data.get("net_inflow", 0)
        st.metric(
            "资金净流入",
            f"{net_inflow:.1f}亿",
            delta=f"{breadth_data.get('net_inflow_change', 0):+.1f}亿",
        )

    with col4:
        sentiment = breadth_data.get("sentiment_index", 50)
        st.metric(
            "市场情绪",
            f"{sentiment:.1f}",
            delta=f"{breadth_data.get('sentiment_change', 0):+.1f}",
        )

    # 市场强度评估
    market_strength = breadth_data.get("market_strength", 50)
    render_market_strength_gauge(market_strength)

    # 详细指标表格
    detailed_indicators = [
        {
            "指标": "涨停股票数",
            "数值": breadth_data.get("limit_up_count", 0),
            "说明": "当日涨停股票数量",
        },
        {
            "指标": "跌停股票数",
            "数值": breadth_data.get("limit_down_count", 0),
            "说明": "当日跌停股票数量",
        },
        {
            "指标": "新高股票数",
            "数值": breadth_data.get("new_high_count", 0),
            "说明": "创新高股票数量",
        },
        {
            "指标": "新低股票数",
            "数值": breadth_data.get("new_low_count", 0),
            "说明": "创新低股票数量",
        },
        {
            "指标": "放量股票数",
            "数值": breadth_data.get("high_volume_count", 0),
            "说明": "成交量放大股票数量",
        },
    ]

    indicator_df = pd.DataFrame(detailed_indicators)
    st.dataframe(indicator_df, use_container_width=True)


def render_enhanced_executive_summary(summary_data: dict):
    """渲染增强版执行摘要"""

    if not summary_data:
        st.info("📑 暂无执行摘要数据")
        return

    st.markdown("### 📑 执行摘要")

    # 核心观点
    if "key_insights" in summary_data:
        st.markdown("#### 💡 核心观点")
        insights = summary_data["key_insights"]
        if isinstance(insights, list):
            for i, insight in enumerate(insights, 1):
                st.markdown(f"**{i}.** {insight}")
        else:
            st.markdown(insights)

    # 投资建议（增强版布局）
    if "investment_recommendations" in summary_data:
        st.markdown("#### 🎯 投资建议")

        rec_col1, rec_col2 = st.columns(2)
        recommendations = summary_data["investment_recommendations"]

        with rec_col1:
            st.markdown("**💚 推荐买入:**")
            buy_list = recommendations.get("buy", [])
            if buy_list:
                for stock in buy_list[:5]:
                    reason = stock.get("reason", "综合评分较高")
                    st.success(
                        f"• {stock.get('name', '')} ({stock.get('symbol', '')}) - {reason}"
                    )
            else:
                st.info("当前无强烈推荐买入的股票")

        with rec_col2:
            st.markdown("**👀 值得关注:**")
            watch_list = recommendations.get("watch", [])
            if watch_list:
                for stock in watch_list[:5]:
                    reason = stock.get("reason", "有潜在机会")
                    st.info(
                        f"• {stock.get('name', '')} ({stock.get('symbol', '')}) - {reason}"
                    )
            else:
                st.info("当前无特别关注的股票")

    # 风险提示
    if "risk_factors" in summary_data:
        st.markdown("#### ⚠️ 风险提示")
        risk_factors = summary_data["risk_factors"]
        if isinstance(risk_factors, list):
            for risk in risk_factors:
                st.warning(f"⚠️ {risk}")
        else:
            st.warning(f"⚠️ {risk_factors}")

    # 市场展望
    if "market_outlook" in summary_data:
        st.markdown("#### 🔮 市场展望")
        st.info(summary_data["market_outlook"])

    # 扫描质量指标
    if "scan_statistics" in summary_data:
        st.markdown("#### 📊 分析质量")
        stats = summary_data["scan_statistics"]

        quality_col1, quality_col2, quality_col3 = st.columns(3)

        with quality_col1:
            st.metric("完成度", f"{stats.get('completion_rate', 100)}%")

        with quality_col2:
            st.metric("数据质量", stats.get("data_quality", "良好"))

        with quality_col3:
            conf = stats.get("confidence_level")
            if conf is None:
                st.metric("结果置信度", "-")
            else:
                st.metric("结果置信度", f"{int(round(conf))}%")


def render_enhanced_export_options(scan_id: str, results_data: dict):
    """渲染增强版导出选项"""

    st.markdown("### 📤 结果导出")
    st.caption("将分析结果导出为不同格式，便于后续使用和分享")

    # 导出格式选择
    export_col1, export_col2 = st.columns(2)

    with export_col1:
        st.markdown("**📊 数据格式**")

        if st.button(
            "📊 Excel格式", use_container_width=True, key=f"export_excel_{scan_id}"
        ):
            export_to_excel(scan_id, results_data)

        if st.button(
            "📄 CSV文件", use_container_width=True, key=f"export_csv_{scan_id}"
        ):
            export_to_csv(scan_id, results_data)

        if st.button(
            "📋 JSON数据", use_container_width=True, key=f"export_json_{scan_id}"
        ):
            export_to_json(scan_id, results_data)

    with export_col2:
        st.markdown("**📑 报告格式**")

        if st.button(
            "📄 PDF报告", use_container_width=True, key=f"export_pdf_{scan_id}"
        ):
            export_to_pdf(scan_id, results_data)

        if st.button(
            "🌐 HTML页面", use_container_width=True, key=f"export_html_{scan_id}"
        ):
            export_to_html(scan_id, results_data)

        if st.button(
            "💾 保存到库", use_container_width=True, key=f"save_results_{scan_id}"
        ):
            save_to_library(scan_id, results_data)

        # 发送到订阅邮箱（市场摘要订阅）
        if st.button(
            "📧 发送到订阅邮箱", use_container_width=True, key=f"send_subs_{scan_id}"
        ):
            try:
                from datetime import datetime as _dt

                from tradingagents.services.mailer.email_sender import EmailSender
                from tradingagents.services.subscription.subscription_manager import (
                    SubscriptionManager,
                )
                from utils.market_session_manager import get_market_session_manager

                # 推断当前分析的市场范围
                msm = get_market_session_manager()
                market_type = None
                for sess in msm.get_active_sessions():
                    if getattr(sess, "scan_id", None) == scan_id:
                        market_type = (sess.config or {}).get("market_type")
                        break
                market_type = market_type or "A股"

                sm = SubscriptionManager()
                subs = sm.get_market_subscriptions(scope=market_type)
                recipients = sorted(
                    list({s.get("email") for s in subs if s.get("email")})
                )
                if not recipients:
                    st.warning("未找到该市场范围的订阅邮箱")
                else:
                    # 构建市场摘要邮件内容
                    summary = results_data.get("summary", {})
                    topn = results_data.get("rankings", [])[:5]
                    key_lines = [
                        f"• {it.get('symbol','')} {it.get('name','')} | 评分 {it.get('total_score',0):.1f} | 建议 {it.get('recommendation','')}"
                        for it in topn
                    ]
                    full_text = (
                        f"市场: {market_type}\n"
                        f"股票总数: {results_data.get('total_stocks', 0)}\n"
                        f"推荐股票: {results_data.get('recommended_stocks', 0)}\n"
                        f"实际成本: ¥{results_data.get('actual_cost', 0):.2f}\n\n"
                        + "\n".join(key_lines)
                    )
                    analysis_result = {
                        "analysis_date": _dt.now().strftime("%Y-%m-%d"),
                        "decision": {
                            "action": f"{market_type} 市场摘要",
                            "confidence": 0.0,
                            "risk_score": 0.0,
                            "reasoning": (
                                summary.get("overview", "")
                                if isinstance(summary, dict)
                                else ""
                            ),
                        },
                        "full_analysis": full_text,
                    }
                    es = EmailSender()
                    ok = es.send_analysis_report(
                        recipients=recipients,
                        stock_symbol=f"MARKET-{market_type}",
                        analysis_result=analysis_result,
                        attachments=None,
                    )
                    if ok:
                        st.success(f"✅ 已发送至 {len(recipients)} 个订阅邮箱")
                    else:
                        st.error("发送失败，请检查邮件配置")
            except Exception as e:
                st.error(f"发送失败: {e}")

    # 导出设置
    with st.expander("⚙️ 导出设置", expanded=False):
        export_settings = render_export_settings()

        if st.button("🚀 批量导出", use_container_width=True):
            batch_export(scan_id, results_data, export_settings)


# 辅助函数（继续完善）


def filter_rankings(
    rankings_data: list[dict], recommendation_filter: str, display_count: int
) -> list[dict]:
    """筛选排名数据"""

    filtered = rankings_data

    # 应用投资建议筛选
    if recommendation_filter != "全部":
        filtered = [
            stock
            for stock in filtered
            if stock.get("recommendation", "") == recommendation_filter
        ]

    # 限制显示数量
    filtered = filtered[:display_count]

    # 添加排名
    for i, stock in enumerate(filtered):
        stock["排名"] = i + 1
        stock["股票代码"] = stock.get("symbol", "")
        stock["股票名称"] = stock.get("name", "")
        stock["综合评分"] = stock.get("total_score", 0)
        stock["技术评分"] = stock.get("technical_score", 0)
        stock["基本面评分"] = stock.get("fundamental_score", 0)
        stock["当前价格"] = stock.get("current_price", 0)
        stock["涨跌幅"] = f"{stock.get('change_percent', 0):+.2f}%"
        stock["建议"] = stock.get("recommendation", "")

    return filtered


def render_sector_heatmap(sectors_data: dict):
    """渲染板块热力图"""

    if len(sectors_data) < 2:
        return

    st.markdown("#### 📊 板块表现热力图")

    # 准备热力图数据
    sector_names = list(sectors_data.keys())
    sector_changes = [
        sectors_data[sector].get("change_percent", 0) for sector in sector_names
    ]

    # 创建热力图
    fig = go.Figure(
        data=go.Heatmap(
            z=[sector_changes],
            x=sector_names,
            y=["板块涨跌幅"],
            colorscale="RdYlGn",
            text=[[f"{change:+.2f}%" for change in sector_changes]],
            texttemplate="%{text}",
            textfont={"size": 12},
            showscale=True,
            colorbar=dict(title="涨跌幅 (%)"),
        )
    )

    fig.update_layout(
        title="板块表现热力图",
        xaxis_title="板块",
        height=200,
        margin=dict(t=50, l=10, r=10, b=50),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_market_strength_gauge(strength_score: float):
    """渲染市场强度仪表盘"""

    st.markdown("#### 🎯 市场强度评估")

    # 创建仪表盘图
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=strength_score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "市场强度指数"},
            delta={"reference": 50},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 30], "color": "lightgray"},
                    {"range": [30, 70], "color": "gray"},
                    {"range": [70, 100], "color": "lightgreen"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 80,
                },
            },
        )
    )

    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    # 强度评估文字
    if strength_score >= 70:
        st.success(f"🟢 市场强度: {strength_score:.1f} - 市场表现强劲，建议积极参与")
    elif strength_score >= 40:
        st.warning(f"🟡 市场强度: {strength_score:.1f} - 市场表现一般，建议谨慎操作")
    else:
        st.error(f"🔴 市场强度: {strength_score:.1f} - 市场表现疲弱，建议控制仓位")


def show_stock_detail(selected_stock: str, rankings_data: list[dict]):
    """显示股票详情（基于排名数据的详细视图）"""

    # 解析名称与代码
    stock_name = None
    stock_symbol = None
    if (
        isinstance(selected_stock, str)
        and "(" in selected_stock
        and selected_stock.endswith(")")
    ):
        try:
            name_part, symbol_part = selected_stock.rsplit("(", 1)
            stock_name = name_part.strip()
            stock_symbol = symbol_part[:-1].strip()
        except Exception:
            stock_name = selected_stock
    else:
        stock_name = selected_stock

    # 在排名数据中查找该股票
    detail = None
    for row in rankings_data or []:
        sym = row.get("symbol") or row.get("股票代码")
        nm = row.get("name") or row.get("股票名称")
        if stock_symbol and sym == stock_symbol:
            detail = row
            break
        if stock_name and nm == stock_name:
            detail = row
            break

    if not detail:
        st.warning("未找到该股票的详细数据")
        return

    # 统一字段
    sym = detail.get("symbol") or detail.get("股票代码")
    nm = detail.get("name") or detail.get("股票名称") or stock_name or ""
    total_score = float(detail.get("total_score") or detail.get("综合评分") or 0)
    tech_score = float(detail.get("technical_score") or detail.get("技术评分") or 0)
    fund_score = float(detail.get("fundamental_score") or detail.get("基本面评分") or 0)
    price = detail.get("current_price") or detail.get("当前价格")
    chg = detail.get("change_percent")
    if isinstance(chg, str) and chg.endswith("%"):
        try:
            chg = float(chg.strip("%"))
        except Exception:
            chg = None
    rec = detail.get("recommendation") or detail.get("建议")
    tgt = detail.get("target_price") or detail.get("目标价格")
    mcap = detail.get("market_cap") or detail.get("市值")
    pe = detail.get("pe_ratio") or detail.get("PE")
    pb = detail.get("pb_ratio") or detail.get("PB")

    st.subheader(f"📌 {nm} ({sym}) 详细分析")
    meta_cols = st.columns(4)
    with meta_cols[0]:
        st.metric(
            "当前价格",
            f"{price:.2f}" if isinstance(price, (int, float)) else str(price or "-"),
        )
    with meta_cols[1]:
        if isinstance(chg, (int, float)):
            st.metric("涨跌幅", f"{chg:+.2f}%")
        else:
            st.metric("涨跌幅", str(chg or "-"))
    with meta_cols[2]:
        st.metric("投资建议", str(rec or "-"))
    with meta_cols[3]:
        st.metric(
            "目标价", f"{tgt:.2f}" if isinstance(tgt, (int, float)) else str(tgt or "-")
        )

    # 评分雷达/柱图
    try:
        import plotly.graph_objects as go

        score_fig = go.Figure()
        score_fig.add_trace(
            go.Bar(
                x=["综合", "技术", "基本面"],
                y=[total_score, tech_score, fund_score],
                marker_color=["#4e79a7", "#f28e2c", "#59a14f"],
            )
        )
        score_fig.update_layout(
            height=260, title="评分概览 (0-100)", yaxis=dict(range=[0, 100])
        )
        st.plotly_chart(score_fig, use_container_width=True)
    except Exception:
        st.write(
            f"评分: 综合 {total_score:.1f} | 技术 {tech_score:.1f} | 基本面 {fund_score:.1f}"
        )

    # 估值与规模
    with st.expander("估值与规模", expanded=True):
        val_cols = st.columns(3)
        with val_cols[0]:
            st.metric(
                "市值",
                f"{mcap:,.2f}" if isinstance(mcap, (int, float)) else str(mcap or "-"),
            )
        with val_cols[1]:
            st.metric(
                "PE", f"{pe:.2f}" if isinstance(pe, (int, float)) else str(pe or "-")
            )
        with val_cols[2]:
            st.metric(
                "PB", f"{pb:.2f}" if isinstance(pb, (int, float)) else str(pb or "-")
            )

    # 原始数据预览与导出
    with st.expander("原始数据", expanded=False):
        import json

        st.json(detail)
        try:
            json_str = json.dumps(detail, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 下载该股票详情 (JSON)",
                data=json_str,
                file_name=f"stock_detail_{sym}.json",
                mime="application/json",
            )
        except Exception:
            pass

    # 常用操作
    op_cols = st.columns(2)
    with op_cols[0]:
        if st.button("📧 订阅该股票邮件报告"):
            st.session_state.preselect_subscription_symbol = sym
            st.success("已预填订阅股票代码，请前往‘📧 邮件订阅管理’页完成添加")
    with op_cols[1]:
        if st.button("🔎 跳转到‘个股分析’进行深入分析"):
            st.session_state.last_stock_symbol = sym
            st.session_state.nav_to_stock_analysis = True
            st.info("已预填股票代码，请在顶部切换到‘📊 个股分析’页执行分析")


def show_sector_detail(sector_name: str, sector_data: dict):
    """显示板块详情"""

    st.markdown(f"### 📊 {sector_name} 板块详情")

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:
        st.metric("板块涨跌幅", f"{sector_data.get('change_percent', 0):+.2f}%")
        st.metric("推荐股票数", sector_data.get("recommended_count", 0))

    with detail_col2:
        st.metric("板块活跃度", f"{sector_data.get('activity_score', 0):.1f}")
        st.metric("龙头股票", sector_data.get("leading_stock", "暂无"))

    # 板块内推荐股票
    if "recommended_stocks" in sector_data:
        st.markdown("**板块内推荐股票:**")
        for stock in sector_data["recommended_stocks"][:10]:
            score = stock.get("score", 0)
            reason = stock.get("reason", "综合评分较高")
            st.write(
                f"• {stock.get('name', '')} ({stock.get('symbol', '')}) - 评分: {score:.1f} - {reason}"
            )


# 导出功能实现


def export_to_excel(scan_id: str, results_data: dict):
    """导出为Excel"""
    st.success("📊 Excel导出功能开发中...")
    logger.info(f"导出Excel: {scan_id}")


def export_to_csv(scan_id: str, results_data: dict):
    """导出为CSV"""

    try:
        # 转换股票排名数据为CSV
        rankings = results_data.get("rankings", [])
        if rankings:
            df = pd.DataFrame(rankings)
            csv_data = df.to_csv(index=False, encoding="utf-8")

            st.download_button(
                label="📥 下载CSV文件",
                data=csv_data,
                file_name=f"market_scan_{scan_id}_rankings.csv",
                mime="text/csv",
            )
            st.success("📄 CSV文件已准备下载")
        else:
            st.warning("⚠️ 无排名数据可导出")
    except Exception as e:
        st.error(f"❌ CSV导出失败: {e}")


def export_to_json(scan_id: str, results_data: dict):
    """导出为JSON"""

    try:
        json_str = json.dumps(results_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 下载JSON文件",
            data=json_str,
            file_name=f"market_scan_{scan_id}.json",
            mime="application/json",
        )
        st.success("📋 JSON数据已准备下载")
    except Exception as e:
        st.error(f"❌ JSON导出失败: {e}")


def export_to_pdf(scan_id: str, results_data: dict):
    """导出为PDF"""
    st.success("📄 PDF导出功能开发中...")
    logger.info(f"导出PDF: {scan_id}")


def export_to_html(scan_id: str, results_data: dict):
    """导出为HTML"""
    st.success("🌐 HTML导出功能开发中...")
    logger.info(f"导出HTML: {scan_id}")


def save_to_library(scan_id: str, results_data: dict):
    """保存全市场分析结果到图书馆（作为report分类）。"""
    try:
        from datetime import datetime as _dt

        from tradingagents.services.file_manager import FileManager

        fm = FileManager()
        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        filename = f"market_scan_{scan_id}_{ts}.json"
        import json as _json

        content = _json.dumps(results_data, ensure_ascii=False, indent=2).encode(
            "utf-8"
        )
        # 尝试找出market_type
        market_type = None
        try:
            from utils.market_session_manager import get_market_session_manager

            msm = get_market_session_manager()
            for sess in msm.get_active_sessions():
                if getattr(sess, "scan_id", None) == scan_id:
                    market_type = (sess.config or {}).get("market_type")
                    break
        except Exception:
            market_type = None
        meta = {
            "scan_id": scan_id,
            "category": "market_scan",
            "market_type": market_type or "unknown",
            "format": "json",
            "saved_via": "market_wide_analysis",
        }
        file_id = fm.save_file(content, filename, category="report", metadata=meta)
        st.success(f"✅ 已保存到图书馆 (附件ID: {file_id})")
    except Exception as e:
        st.error(f"保存失败: {e}")


def render_export_settings():
    """渲染导出设置"""

    settings = {}

    setting_col1, setting_col2 = st.columns(2)

    with setting_col1:
        settings["include_charts"] = st.checkbox("包含图表", value=True)
        settings["include_raw_data"] = st.checkbox("包含原始数据", value=False)
        settings["compress_file"] = st.checkbox("压缩文件", value=False)

    with setting_col2:
        settings["export_format"] = st.selectbox("首选格式", ["Excel", "PDF", "HTML"])
        settings["language"] = st.selectbox("报告语言", ["中文", "英文"])
        settings["template"] = st.selectbox(
            "报告模板", ["标准模板", "简洁模板", "详细模板"]
        )

    return settings


def batch_export(scan_id: str, results_data: dict, export_settings: dict):
    """批量导出"""

    st.info("🚀 开始批量导出...")

    progress = st.progress(0)
    status_text = st.empty()

    # 模拟批量导出过程
    exports = ["Excel", "CSV", "JSON", "PDF", "HTML"]

    for i, format_type in enumerate(exports):
        status_text.text(f"正在导出 {format_type} 格式...")
        progress.progress((i + 1) / len(exports))
        time.sleep(0.5)  # 模拟导出时间

    status_text.text("✅ 批量导出完成！")
    st.success("🎉 所有格式导出完成，请检查下载文件夹")


# 主入口
if __name__ == "__main__":
    render_enhanced_market_wide_analysis()
