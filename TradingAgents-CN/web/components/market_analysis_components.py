"""
Market Analysis Components
市场分析可复用UI组件 - 配置面板、进度显示、结果展示等
"""

import json
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("market_analysis_components")
from utils.market_config_store import get_config_store  # noqa: E402


class MarketConfigurationPanel:
    """市场分析配置面板组件"""

    def __init__(self):
        self.default_config = {
            "market_type": "A股",
            "preset_type": "大盘蓝筹",
            "scan_depth": 3,
            "budget_limit": 10.0,
            "stock_limit": 100,
            "time_range": "1月",
        }

    def render(self, key_prefix: str = "market_config") -> dict[str, Any]:
        """渲染配置面板并返回配置数据"""

        st.subheader("📊 分析配置")
        st.caption("配置市场分析参数，设定分析范围和深度")
        # 预设/保存/加载（标准版也支持）
        try:
            self._render_config_presets(key_prefix)
        except Exception as e:
            st.caption(f"⚠️ 预设功能加载失败: {e}")

        with st.form(f"{key_prefix}_form", clear_on_submit=False):
            return self._render_config_form(key_prefix)

    def _render_config_form(self, key_prefix: str) -> dict[str, Any]:
        """渲染配置表单内容"""

        col1, col2 = st.columns(2)

        with col1:
            # 基础配置
            market_type = st.selectbox(
                "📈 目标市场",
                options=["A股", "美股", "港股"],
                index=0,
                help="选择要分析的股票市场",
                key=f"{key_prefix}_market",
            )

            preset_type = self._get_preset_selector(market_type, key_prefix)

            scan_depth = st.select_slider(
                "🔍 分析深度",
                options=[1, 2, 3, 4, 5],
                value=3,
                format_func=lambda x: {
                    1: "1级 - 基础筛选",
                    2: "2级 - 技术分析",
                    3: "3级 - 综合分析",
                    4: "4级 - 深度研究",
                    5: "5级 - 全面调研",
                }[x],
                help="分析深度越高越详细，但成本和时间也会增加",
                key=f"{key_prefix}_depth",
            )

        with col2:
            # 限制设置
            budget_limit = st.number_input(
                "💰 预算上限 (¥)",
                min_value=1.0,
                max_value=500.0,
                value=10.0,
                step=1.0,
                help="本次分析的最大成本限制",
                key=f"{key_prefix}_budget",
            )

            stock_limit = st.number_input(
                "🎯 股票数量上限",
                min_value=10,
                max_value=1000,
                value=100,
                step=10,
                help="限制分析的股票数量以控制成本",
                key=f"{key_prefix}_limit",
            )

            time_range = st.selectbox(
                "⏰ 历史数据范围",
                options=["1周", "1月", "3月", "6月", "1年"],
                index=1,
                help="历史数据分析的时间窗口",
                key=f"{key_prefix}_timerange",
            )

        # 高级筛选条件
        if preset_type == "自定义筛选":
            custom_filters = self._render_custom_filters(key_prefix)
        else:
            custom_filters = {}

        # 分析重点选择
        st.markdown("### 🎯 分析重点")

        focus_col1, focus_col2 = st.columns(2)

        with focus_col1:
            technical_focus = st.checkbox(
                "📊 技术面分析", value=True, key=f"{key_prefix}_tech"
            )
            fundamental_focus = st.checkbox(
                "💰 基本面分析", value=True, key=f"{key_prefix}_fund"
            )
            valuation_focus = st.checkbox(
                "💎 估值分析", value=True, key=f"{key_prefix}_val"
            )

        with focus_col2:
            news_focus = st.checkbox(
                "📰 消息面分析", value=False, key=f"{key_prefix}_news"
            )
            sentiment_focus = st.checkbox(
                "💭 情绪分析", value=False, key=f"{key_prefix}_sentiment"
            )
            risk_focus = st.checkbox("⚠️ 风险评估", value=True, key=f"{key_prefix}_risk")

        # 高级选项
        with st.expander("⚙️ 高级选项"):
            enable_monitoring = st.checkbox(
                "📡 实时监控",
                value=True,
                help="分析过程中实时显示进度和中间结果",
                key=f"{key_prefix}_monitor",
            )

            enable_notification = st.checkbox(
                "📬 完成通知",
                value=False,
                help="分析完成后发送邮件通知（需配置邮件服务）",
                key=f"{key_prefix}_notify",
            )

            save_intermediate = st.checkbox(
                "💾 保存中间结果",
                value=False,
                help="保存分析过程中的中间分析结果",
                key=f"{key_prefix}_save_inter",
            )

        # 提交按钮组
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

        with col_btn1:
            start_scan = st.form_submit_button(
                "🚀 开始分析", type="primary", use_container_width=True
            )

        with col_btn2:
            estimate_cost = st.form_submit_button(
                "💰 预估成本", use_container_width=True
            )

        with col_btn3:
            save_config = st.form_submit_button("💾 保存配置", use_container_width=True)

        # 组装配置数据
        config_data = {
            "market_type": market_type,
            "preset_type": preset_type,
            "scan_depth": scan_depth,
            "budget_limit": budget_limit,
            "stock_limit": stock_limit,
            "time_range": time_range,
            "custom_filters": custom_filters,
            "analysis_focus": {
                "technical": technical_focus,
                "fundamental": fundamental_focus,
                "valuation": valuation_focus,
                "news": news_focus,
                "sentiment": sentiment_focus,
                "risk": risk_focus,
            },
            "advanced_options": {
                "enable_monitoring": enable_monitoring,
                "enable_notification": enable_notification,
                "save_intermediate": save_intermediate,
            },
            "submitted": start_scan,
            "estimate_requested": estimate_cost,
            "save_requested": save_config,
        }

        return config_data

    def _render_config_presets(self, key_prefix: str) -> None:
        """在标准配置面板顶部渲染“配置预设/保存/加载”。"""
        store = get_config_store()
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            preset_names = store.list_builtin_preset_names()
            preset_names.insert(0, "最近保存配置")
            preset_names.append("自定义配置")
            selected = st.selectbox(
                "📋 配置预设", preset_names, help="选择预设或加载最近保存"
            )

        with col2:
            if st.button(
                "💾 保存配置", use_container_width=True, key=f"save_cfg_{key_prefix}"
            ):
                try:
                    cfg = {
                        "market_type": st.session_state.get(f"{key_prefix}_market"),
                        "preset_type": st.session_state.get(f"{key_prefix}_preset"),
                        "scan_depth": st.session_state.get(f"{key_prefix}_depth"),
                        "budget_limit": st.session_state.get(f"{key_prefix}_budget"),
                        "stock_limit": st.session_state.get(f"{key_prefix}_limit"),
                        "time_range": st.session_state.get(f"{key_prefix}_timerange"),
                        "analysis_focus": {
                            "technical": st.session_state.get(f"{key_prefix}_tech"),
                            "fundamental": st.session_state.get(f"{key_prefix}_fund"),
                            "valuation": st.session_state.get(f"{key_prefix}_val"),
                            "news": st.session_state.get(f"{key_prefix}_news"),
                            "sentiment": st.session_state.get(
                                f"{key_prefix}_sentiment"
                            ),
                            "risk": st.session_state.get(f"{key_prefix}_risk"),
                        },
                        "advanced_options": {
                            "enable_monitoring": st.session_state.get(
                                f"{key_prefix}_monitor"
                            ),
                            "enable_notification": st.session_state.get(
                                f"{key_prefix}_notify"
                            ),
                            "save_intermediate": st.session_state.get(
                                f"{key_prefix}_save_inter"
                            ),
                        },
                    }
                    store.save_last_config(cfg)
                    st.success("✅ 已保存到最近保存配置")
                except Exception as e:
                    st.error(f"❌ 保存失败: {e}")

        with col3:
            if st.button(
                "📥 加载配置", use_container_width=True, key=f"load_cfg_{key_prefix}"
            ):
                try:
                    cfg = None
                    if selected == "最近保存配置":
                        cfg = store.load_last_config()
                        if not cfg:
                            st.warning("⚠️ 暂无最近保存配置")
                            return
                    else:
                        cfg = store.get_builtin_preset(selected)
                        if not cfg:
                            st.warning(f"⚠️ 未找到预设: {selected}")
                            return

                    # 将配置写回表单控件的 session_state
                    st.session_state[f"{key_prefix}_market"] = cfg.get("market_type")
                    st.session_state[f"{key_prefix}_preset"] = cfg.get("preset_type")
                    st.session_state[f"{key_prefix}_depth"] = cfg.get("scan_depth")
                    st.session_state[f"{key_prefix}_budget"] = cfg.get("budget_limit")
                    st.session_state[f"{key_prefix}_limit"] = cfg.get("stock_limit")
                    st.session_state[f"{key_prefix}_timerange"] = cfg.get("time_range")

                    af = cfg.get("analysis_focus", {})
                    st.session_state[f"{key_prefix}_tech"] = af.get("technical", True)
                    st.session_state[f"{key_prefix}_fund"] = af.get("fundamental", True)
                    st.session_state[f"{key_prefix}_val"] = af.get("valuation", True)
                    st.session_state[f"{key_prefix}_news"] = af.get("news", False)
                    st.session_state[f"{key_prefix}_sentiment"] = af.get(
                        "sentiment", False
                    )
                    st.session_state[f"{key_prefix}_risk"] = af.get("risk", True)

                    adv = cfg.get("advanced_options", {})
                    st.session_state[f"{key_prefix}_monitor"] = adv.get(
                        "enable_monitoring", True
                    )
                    st.session_state[f"{key_prefix}_notify"] = adv.get(
                        "enable_notification", False
                    )
                    st.session_state[f"{key_prefix}_save_inter"] = adv.get(
                        "save_intermediate", False
                    )

                    st.success(f"✅ 已加载预设: {selected}")
                    try:
                        st.rerun()
                    except Exception:
                        pass
                except Exception as e:
                    st.error(f"❌ 加载失败: {e}")

    def _get_preset_selector(self, market_type: str, key_prefix: str) -> str:
        """根据市场类型获取预设选择器 - 动态显示对应市场的预设选项"""

        preset_options = {
            "A股": [
                "大盘蓝筹",
                "中小板精选",
                "创业板",
                "科创板",
                "沪深300",
                "中证500",
                "自定义筛选",
            ],
            "美股": [
                "标普500",
                "纳斯达克100",
                "道琼斯",
                "成长股",
                "价值股",
                "科技股",
                "自定义筛选",
            ],
            "港股": [
                "恒生指数",
                "恒生科技",
                "国企指数",
                "红筹股",
                "蓝筹股",
                "自定义筛选",
            ],
        }

        # 获取当前市场对应的预设选项
        current_options = preset_options.get(market_type, preset_options["A股"])

        # 使用市场类型作为key的一部分，确保市场变化时组件重新渲染
        preset_key = f"{key_prefix}_preset_{market_type}"

        # 检查上一次的市场类型，如果发生变化则重置选择
        last_market_key = f"{key_prefix}_last_market_type"
        last_market = st.session_state.get(last_market_key)

        default_index = 0
        if last_market != market_type:
            # 市场类型发生变化，重置为第一个选项
            st.session_state[last_market_key] = market_type
            if preset_key in st.session_state:
                del st.session_state[preset_key]
        else:
            # 市场类型未变化，尝试保持当前选择
            current_preset = st.session_state.get(preset_key)
            if current_preset and current_preset in current_options:
                default_index = current_options.index(current_preset)

        return st.selectbox(
            "🎲 预设筛选",
            options=current_options,
            index=default_index,
            help=f"选择{market_type}市场的股票筛选预设，或选择自定义筛选",
            key=preset_key,
        )

    def _render_custom_filters(self, key_prefix: str) -> dict[str, Any]:
        """渲染自定义筛选条件"""

        st.markdown("#### 🔍 自定义筛选条件")

        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            # 财务指标筛选
            st.markdown("**📊 财务指标**")

            market_cap_min = st.number_input(
                "最小市值 (亿元)", min_value=0.0, value=0.0, key=f"{key_prefix}_cap_min"
            )

            pe_max = st.number_input(
                "最大PE倍数", min_value=0.0, value=100.0, key=f"{key_prefix}_pe_max"
            )

            pb_max = st.number_input(
                "最大PB倍数", min_value=0.0, value=10.0, key=f"{key_prefix}_pb_max"
            )

        with filter_col2:
            # 技术指标筛选
            st.markdown("**📈 技术指标**")

            price_change_min = st.number_input(
                "最小涨跌幅 (%)", value=-20.0, key=f"{key_prefix}_change_min"
            )

            price_change_max = st.number_input(
                "最大涨跌幅 (%)", value=20.0, key=f"{key_prefix}_change_max"
            )

            volume_filter = st.checkbox(
                "筛选活跃股票",
                value=True,
                help="只选择成交量较大的活跃股票",
                key=f"{key_prefix}_volume_filter",
            )

        return {
            "market_cap_min": market_cap_min,
            "pe_max": pe_max if pe_max > 0 else None,
            "pb_max": pb_max if pb_max > 0 else None,
            "price_change_min": price_change_min,
            "price_change_max": price_change_max,
            "volume_filter": volume_filter,
        }


class MarketProgressDisplay:
    """市场分析进度显示组件"""

    def __init__(self):
        self.progress_stages = [
            "数据准备",
            "股票筛选",
            "技术分析",
            "基本面分析",
            "风险评估",
            "生成报告",
        ]

    def render(self, scan_id: str, progress_data: dict | None = None) -> bool:
        """
        渲染进度显示

        Args:
            scan_id: 扫描ID
            progress_data: 进度数据

        Returns:
            bool: 是否已完成
        """

        if not scan_id:
            st.info("📝 尚未开始分析。请先在配置面板启动分析。")
            return False

        st.subheader(f"📊 分析进度 - {scan_id}")

        if not progress_data:
            st.warning("⚠️ 无法获取进度数据")
            return False

        # 总体进度条
        overall_progress = progress_data.get("overall_progress", 0)
        st.progress(overall_progress / 100.0)
        st.write(f"**整体进度:** {overall_progress}%")

        # 详细进度信息
        col1, col2 = st.columns(2)

        with col1:
            self._render_stage_progress(progress_data.get("stages", []))

        with col2:
            self._render_real_time_stats(progress_data.get("stats", {}))

        # 最新消息
        if "latest_message" in progress_data:
            st.info(f"🔔 {progress_data['latest_message']}")

        # 中间结果预览
        if progress_data.get("preview_results"):
            with st.expander("👀 中间结果预览"):
                self._render_preview_results(progress_data["preview_results"])

        # 控制按钮
        self._render_control_buttons(scan_id)

        return overall_progress >= 100

    def _render_stage_progress(self, stages_data: list[dict]):
        """渲染阶段进度"""

        st.markdown("**📋 分析阶段**")

        if not stages_data:
            # 使用默认阶段
            for stage in self.progress_stages:
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

    def _render_control_buttons(self, scan_id: str):
        """渲染控制按钮"""

        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button(
                "🔄 刷新进度", use_container_width=True, key=f"refresh_{scan_id}"
            ):
                st.rerun()

        with col2:
            if st.button(
                "⏸️ 暂停分析", use_container_width=True, key=f"pause_{scan_id}"
            ):
                self._pause_scan(scan_id)

        with col3:
            if st.button(
                "▶️ 继续分析", use_container_width=True, key=f"resume_{scan_id}"
            ):
                self._resume_scan(scan_id)

        with col4:
            if st.button(
                "🛑 停止分析", use_container_width=True, key=f"stop_{scan_id}"
            ):
                self._stop_scan(scan_id)

        # 自动刷新选项
        auto_refresh = st.checkbox(
            "⚡ 自动刷新 (5秒间隔)",
            value=True,
            key=f"auto_refresh_{scan_id}",
            help="自动刷新进度显示",
        )

        return auto_refresh

    def _pause_scan(self, scan_id: str):
        """暂停分析"""
        st.success(f"⏸️ 分析 {scan_id} 已暂停")
        logger.info(f"暂停市场扫描: {scan_id}")

    def _resume_scan(self, scan_id: str):
        """继续分析"""
        st.success(f"▶️ 分析 {scan_id} 已继续")
        logger.info(f"继续市场扫描: {scan_id}")

    def _stop_scan(self, scan_id: str):
        """停止分析"""
        st.error(f"🛑 分析 {scan_id} 已停止")
        logger.info(f"停止市场扫描: {scan_id}")


class MarketResultsDisplay:
    """市场分析结果显示组件"""

    def render(self, scan_id: str, results_data: dict) -> None:
        """渲染分析结果"""

        if not results_data:
            st.info("📊 暂无分析结果数据")
            return

        st.subheader(f"📋 分析结果 - {scan_id}")

        # 结果概览
        self._render_results_overview(results_data)

        # 结果详情标签页
        result_tabs = st.tabs(
            ["📊 股票排名", "🔥 板块热点", "📈 市场指标", "📑 执行摘要"]
        )

        with result_tabs[0]:
            self._render_stock_rankings(results_data.get("rankings", []))

        with result_tabs[1]:
            self._render_sector_analysis(results_data.get("sectors", {}))

        with result_tabs[2]:
            self._render_market_breadth(results_data.get("breadth", {}))

        with result_tabs[3]:
            self._render_executive_summary(results_data.get("summary", {}))

        # 导出功能
        st.markdown("---")
        self._render_export_options(scan_id, results_data)

    def _render_results_overview(self, results_data: dict):
        """渲染结果概览"""

        # 统计卡片
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "分析股票数",
                results_data.get("total_stocks", 0),
                help="本次分析的股票总数",
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
                help="本次分析实际花费成本",
            )

        with col4:
            scan_duration = results_data.get("scan_duration", "未知")
            st.metric("分析时长", scan_duration, help="分析总耗时")

    def _render_stock_rankings(self, rankings_data: list[dict]):
        """渲染股票排名"""

        if not rankings_data:
            st.info("📊 暂无股票排名数据")
            return

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
        filtered_data = self._filter_rankings(
            rankings_data, recommendation_filter, display_count
        )

        # 创建数据表
        df = pd.DataFrame(filtered_data)

        if not df.empty:
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
                df, use_container_width=True, height=400, column_config=column_config
            )

        # 选择股票查看详情
        if not df.empty:
            selected_stock = st.selectbox(
                "选择股票查看详细分析",
                options=[
                    f"{row['股票名称']} ({row['股票代码']})" for _, row in df.iterrows()
                ],
                key="selected_stock_detail",
            )

            if st.button("📊 查看详细分析", key="view_stock_detail"):
                self._show_stock_detail(selected_stock, rankings_data)

    def _render_sector_analysis(self, sectors_data: dict):
        """渲染板块分析"""

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
        self._render_sector_heatmap(sectors_data)

        # 板块详情
        if sectors_data:
            selected_sector = st.selectbox(
                "选择板块查看详情",
                options=list(sectors_data.keys()),
                key="selected_sector_detail",
            )

            if selected_sector:
                self._show_sector_detail(selected_sector, sectors_data[selected_sector])

    def _render_market_breadth(self, breadth_data: dict):
        """渲染市场广度指标"""

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

        # 市场强度评估
        market_strength = breadth_data.get("market_strength", 50)
        self._render_market_strength_gauge(market_strength)

    def _render_executive_summary(self, summary_data: dict):
        """渲染执行摘要"""

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

        # 投资建议
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

    def _render_export_options(self, scan_id: str, results_data: dict):
        """渲染导出选项"""

        st.subheader("📤 结果导出")
        st.caption("将分析结果导出为不同格式，便于后续使用和分享")

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            if st.button(
                "📊 Excel格式", use_container_width=True, key=f"export_excel_{scan_id}"
            ):
                self._export_to_excel(scan_id, results_data)

        with col2:
            if st.button(
                "📄 PDF报告", use_container_width=True, key=f"export_pdf_{scan_id}"
            ):
                self._export_to_pdf(scan_id, results_data)

        with col3:
            if st.button(
                "🌐 HTML页面", use_container_width=True, key=f"export_html_{scan_id}"
            ):
                self._export_to_html(scan_id, results_data)

        with col4:
            if st.button(
                "📋 JSON数据", use_container_width=True, key=f"export_json_{scan_id}"
            ):
                self._export_to_json(scan_id, results_data)

        with col5:
            if st.button(
                "💾 保存到库", use_container_width=True, key=f"save_results_{scan_id}"
            ):
                self._save_to_library(scan_id, results_data)

    # 辅助方法
    def _filter_rankings(
        self, rankings_data: list[dict], recommendation_filter: str, display_count: int
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

    def _render_sector_heatmap(self, sectors_data: dict):
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

    def _render_market_strength_gauge(self, strength_score: float):
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
            st.success(
                f"🟢 市场强度: {strength_score:.1f} - 市场表现强劲，建议积极参与"
            )
        elif strength_score >= 40:
            st.warning(
                f"🟡 市场强度: {strength_score:.1f} - 市场表现一般，建议谨慎操作"
            )
        else:
            st.error(f"🔴 市场强度: {strength_score:.1f} - 市场表现疲弱，建议控制仓位")

    def _show_stock_detail(self, selected_stock: str, rankings_data: list[dict]):
        """显示股票详情"""

        st.info(f"股票详情功能开发中: {selected_stock}")
        # 这里可以实现详细的个股分析展示

    def _show_sector_detail(self, sector_name: str, sector_data: dict):
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

    # 导出方法
    def _export_to_excel(self, scan_id: str, results_data: dict):
        """导出为Excel"""
        st.success("📊 Excel导出功能开发中...")
        logger.info(f"导出Excel: {scan_id}")

    def _export_to_pdf(self, scan_id: str, results_data: dict):
        """导出为PDF"""
        st.success("📄 PDF导出功能开发中...")
        logger.info(f"导出PDF: {scan_id}")

    def _export_to_html(self, scan_id: str, results_data: dict):
        """导出为HTML"""
        st.success("🌐 HTML导出功能开发中...")
        logger.info(f"导出HTML: {scan_id}")

    def _export_to_json(self, scan_id: str, results_data: dict):
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
            st.error(f"JSON导出失败: {e}")

    def _save_to_library(self, scan_id: str, results_data: dict):
        """保存到库"""
        st.success("💾 保存到库功能开发中...")
        logger.info(f"保存到库: {scan_id}")


# 工具函数
def format_currency(amount: float, currency: str = "¥") -> str:
    """格式化货币显示"""
    return f"{currency}{amount:.2f}"


def format_percentage(value: float, decimal_places: int = 2) -> str:
    """格式化百分比显示"""
    return f"{value:.{decimal_places}f}%"


def calculate_recommendation_color(recommendation: str) -> str:
    """根据投资建议返回颜色"""
    color_map = {
        "买入": "#28a745",
        "持有": "#ffc107",
        "关注": "#17a2b8",
        "卖出": "#dc3545",
    }
    return color_map.get(recommendation, "#6c757d")
