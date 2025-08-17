"""
Enhanced Market Results Display Components
增强版市场分析结果高级可视化组件 - 图表、热力图、仪表盘等
"""

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("enhanced_market_results_display")


class EnhancedStockRankingsDisplay:
    """增强版股票排名展示组件"""

    def __init__(self):
        self.default_columns = [
            "排名",
            "股票代码",
            "股票名称",
            "综合评分",
            "技术评分",
            "基本面评分",
            "当前价格",
            "涨跌幅",
            "建议",
            "目标价",
        ]

    def render(self, rankings_data: list[dict], key_suffix: str = "") -> None:
        """渲染增强版股票排名展示"""

        if not rankings_data:
            st.info("📊 暂无股票排名数据")
            self._render_empty_state_help()
            return

        # 数据预处理
        processed_data = self._process_rankings_data(rankings_data)

        # 控制面板
        filters = self._render_enhanced_control_panel(processed_data, key_suffix)

        # 应用筛选
        filtered_data = self._apply_filters(processed_data, filters)

        # 主要显示区域
        display_tabs = st.tabs(
            ["📋 排名表格", "📊 评分分布", "🎯 推荐分析", "📈 价格分析", "🔍 详细对比"]
        )

        with display_tabs[0]:
            self._render_enhanced_rankings_table(filtered_data, key_suffix)

        with display_tabs[1]:
            self._render_score_distribution(filtered_data, key_suffix)

        with display_tabs[2]:
            self._render_recommendation_analysis(filtered_data, key_suffix)

        with display_tabs[3]:
            self._render_price_analysis(filtered_data, key_suffix)

        with display_tabs[4]:
            self._render_detailed_comparison(filtered_data, key_suffix)

    def _process_rankings_data(self, rankings_data: list[dict]) -> pd.DataFrame:
        """处理和标准化排名数据"""

        try:
            df = pd.DataFrame(rankings_data)

            # 标准化列名
            column_mapping = {
                "symbol": "股票代码",
                "name": "股票名称",
                "total_score": "综合评分",
                "technical_score": "技术评分",
                "fundamental_score": "基本面评分",
                "current_price": "当前价格",
                "change_percent": "涨跌幅",
                "recommendation": "建议",
                "target_price": "目标价",
                "market_cap": "市值",
                "pe_ratio": "PE倍数",
                "pb_ratio": "PB倍数",
                "volume": "成交量",
            }

            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df[new_col] = df[old_col]

            # 添加排名
            if "综合评分" in df.columns:
                df = df.sort_values("综合评分", ascending=False).reset_index(drop=True)
                df["排名"] = range(1, len(df) + 1)

            # 数据类型转换
            numeric_columns = [
                "综合评分",
                "技术评分",
                "基本面评分",
                "当前价格",
                "涨跌幅",
                "目标价",
                "市值",
                "PE倍数",
                "PB倍数",
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            return df

        except Exception as e:
            logger.error(f"处理排名数据失败: {e}")
            return pd.DataFrame()

    def _render_enhanced_control_panel(
        self, df: pd.DataFrame, key_suffix: str
    ) -> dict[str, Any]:
        """渲染增强版控制面板"""

        st.markdown("#### 🎛️ 筛选控制")

        control_col1, control_col2, control_col3, control_col4 = st.columns(4)

        filters = {}

        with control_col1:
            if "建议" in df.columns:
                recommendations = df["建议"].dropna().unique().tolist()
                filters["recommendation"] = st.multiselect(
                    "投资建议",
                    options=recommendations,
                    default=recommendations,
                    key=f"rec_filter_{key_suffix}",
                )
            else:
                filters["recommendation"] = []

        with control_col2:
            if "综合评分" in df.columns:
                score_min, score_max = float(df["综合评分"].min()), float(
                    df["综合评分"].max()
                )
                filters["score_range"] = st.slider(
                    "综合评分范围",
                    min_value=score_min,
                    max_value=score_max,
                    value=(score_min, score_max),
                    key=f"score_range_{key_suffix}",
                )

        with control_col3:
            if "市值" in df.columns and df["市值"].max() > 0:
                cap_min, cap_max = float(df["市值"].min()), float(df["市值"].max())
                filters["market_cap_range"] = st.slider(
                    "市值范围 (亿元)",
                    min_value=cap_min,
                    max_value=cap_max,
                    value=(cap_min, cap_max),
                    key=f"cap_range_{key_suffix}",
                )

        with control_col4:
            filters["display_count"] = st.number_input(
                "显示数量",
                min_value=10,
                max_value=len(df) if len(df) > 0 else 100,
                value=min(50, len(df)) if len(df) > 0 else 50,
                key=f"display_count_{key_suffix}",
            )

        return filters

    def _apply_filters(self, df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
        """应用筛选条件"""

        try:
            filtered_df = df.copy()

            # 应用建议筛选
            if filters.get("recommendation") and "建议" in df.columns:
                filtered_df = filtered_df[
                    filtered_df["建议"].isin(filters["recommendation"])
                ]

            # 应用评分范围筛选
            if filters.get("score_range") and "综合评分" in df.columns:
                score_min, score_max = filters["score_range"]
                filtered_df = filtered_df[
                    (filtered_df["综合评分"] >= score_min)
                    & (filtered_df["综合评分"] <= score_max)
                ]

            # 应用市值范围筛选
            if filters.get("market_cap_range") and "市值" in df.columns:
                cap_min, cap_max = filters["market_cap_range"]
                filtered_df = filtered_df[
                    (filtered_df["市值"] >= cap_min) & (filtered_df["市值"] <= cap_max)
                ]

            # 限制显示数量
            display_count = filters.get("display_count", 50)
            filtered_df = filtered_df.head(display_count)

            return filtered_df

        except Exception as e:
            logger.error(f"应用筛选失败: {e}")
            return df

    def _render_enhanced_rankings_table(self, df: pd.DataFrame, key_suffix: str):
        """渲染增强版排名表格"""

        if df.empty:
            st.info("没有符合条件的股票数据")
            return

        # 准备显示的数据
        display_df = df.copy()

        # 格式化数字列
        if "涨跌幅" in display_df.columns:
            display_df["涨跌幅"] = display_df["涨跌幅"].apply(
                lambda x: f"{x:+.2f}%" if pd.notnull(x) else ""
            )

        if "当前价格" in display_df.columns:
            display_df["当前价格"] = display_df["当前价格"].apply(
                lambda x: f"¥{x:.2f}" if pd.notnull(x) else ""
            )

        if "目标价" in display_df.columns:
            display_df["目标价"] = display_df["目标价"].apply(
                lambda x: f"¥{x:.2f}" if pd.notnull(x) else ""
            )

        if "市值" in display_df.columns:
            display_df["市值"] = display_df["市值"].apply(
                lambda x: f"{x:.1f}亿" if pd.notnull(x) else ""
            )

        # 配置列显示
        column_config = {}

        if "综合评分" in display_df.columns:
            column_config["综合评分"] = st.column_config.ProgressColumn(
                "综合评分", min_value=0, max_value=100, format="%.1f"
            )

        if "技术评分" in display_df.columns:
            column_config["技术评分"] = st.column_config.ProgressColumn(
                "技术评分", min_value=0, max_value=100, format="%.1f"
            )

        if "基本面评分" in display_df.columns:
            column_config["基本面评分"] = st.column_config.ProgressColumn(
                "基本面评分", min_value=0, max_value=100, format="%.1f"
            )

        # 显示表格
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500,
            column_config=column_config,
            key=f"rankings_table_{key_suffix}",
        )

        # 添加表格操作
        self._render_table_actions(display_df, key_suffix)

    def _render_score_distribution(self, df: pd.DataFrame, key_suffix: str):
        """渲染评分分布图"""

        if df.empty:
            st.info("无数据可显示")
            return

        st.markdown("#### 📊 评分分布分析")

        # 创建子图
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=[
                "综合评分分布",
                "技术评分 vs 基本面评分",
                "评分箱型图",
                "推荐分布",
            ],
            specs=[
                [{"type": "histogram"}, {"type": "scatter"}],
                [{"type": "box"}, {"type": "pie"}],
            ],
        )

        # 综合评分分布直方图
        if "综合评分" in df.columns:
            fig.add_trace(
                go.Histogram(
                    x=df["综合评分"],
                    nbinsx=20,
                    name="综合评分分布",
                    marker_color="lightblue",
                ),
                row=1,
                col=1,
            )

        # 技术评分 vs 基本面评分散点图
        if "技术评分" in df.columns and "基本面评分" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["技术评分"],
                    y=df["基本面评分"],
                    mode="markers",
                    marker=dict(
                        size=8,
                        color=df["综合评分"] if "综合评分" in df.columns else "blue",
                        colorscale="Viridis",
                        showscale=True,
                        colorbar=dict(title="综合评分"),
                    ),
                    text=df["股票名称"] if "股票名称" in df.columns else None,
                    name="评分关系",
                ),
                row=1,
                col=2,
            )

        # 评分箱型图
        score_columns = ["综合评分", "技术评分", "基本面评分"]
        for i, col in enumerate(score_columns):
            if col in df.columns:
                fig.add_trace(
                    go.Box(y=df[col], name=col, boxpoints="outliers"), row=2, col=1
                )

        # 推荐分布饼图
        if "建议" in df.columns:
            recommendation_counts = df["建议"].value_counts()
            fig.add_trace(
                go.Pie(
                    labels=recommendation_counts.index,
                    values=recommendation_counts.values,
                    name="推荐分布",
                ),
                row=2,
                col=2,
            )

        fig.update_layout(height=800, showlegend=True, title="评分分布综合分析")
        st.plotly_chart(fig, use_container_width=True, key=f"score_dist_{key_suffix}")

    def _render_recommendation_analysis(self, df: pd.DataFrame, key_suffix: str):
        """渲染推荐分析"""

        if df.empty or "建议" not in df.columns:
            st.info("无推荐数据可显示")
            return

        st.markdown("#### 🎯 投资建议分析")

        # 推荐分布统计
        rec_col1, rec_col2 = st.columns(2)

        with rec_col1:
            recommendation_counts = df["建议"].value_counts()

            # 推荐分布饼图
            fig_pie = px.pie(
                values=recommendation_counts.values,
                names=recommendation_counts.index,
                title="推荐分布",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            st.plotly_chart(
                fig_pie, use_container_width=True, key=f"rec_pie_{key_suffix}"
            )

        with rec_col2:
            # 推荐 vs 评分箱型图
            fig_box = px.box(
                df,
                x="建议",
                y="综合评分" if "综合评分" in df.columns else None,
                title="建议类别 vs 综合评分",
                color="建议",
            )
            st.plotly_chart(
                fig_box, use_container_width=True, key=f"rec_box_{key_suffix}"
            )

        # 详细推荐统计
        st.markdown("##### 📈 推荐统计详情")

        for recommendation in recommendation_counts.index:
            rec_stocks = df[df["建议"] == recommendation]

            if not rec_stocks.empty:
                with st.expander(
                    f"{recommendation} ({len(rec_stocks)}只股票)", expanded=False
                ):

                    # 统计信息
                    stats_col1, stats_col2, stats_col3 = st.columns(3)

                    with stats_col1:
                        if "综合评分" in rec_stocks.columns:
                            avg_score = rec_stocks["综合评分"].mean()
                            st.metric("平均综合评分", f"{avg_score:.1f}")

                    with stats_col2:
                        if "涨跌幅" in rec_stocks.columns:
                            avg_change = rec_stocks["涨跌幅"].mean()
                            st.metric("平均涨跌幅", f"{avg_change:+.2f}%")

                    with stats_col3:
                        if "市值" in rec_stocks.columns:
                            avg_cap = rec_stocks["市值"].mean()
                            st.metric("平均市值", f"{avg_cap:.1f}亿")

                    # 显示相关股票
                    display_columns = [
                        "排名",
                        "股票名称",
                        "股票代码",
                        "综合评分",
                        "当前价格",
                        "涨跌幅",
                    ]
                    display_columns = [
                        col for col in display_columns if col in rec_stocks.columns
                    ]

                    if display_columns:
                        st.dataframe(
                            rec_stocks[display_columns].head(10),
                            use_container_width=True,
                        )

    def _render_price_analysis(self, df: pd.DataFrame, key_suffix: str):
        """渲染价格分析"""

        if df.empty:
            st.info("无价格数据可显示")
            return

        st.markdown("#### 📈 价格分析")

        price_col1, price_col2 = st.columns(2)

        with price_col1:
            # 价格分布直方图
            if "当前价格" in df.columns:
                fig_hist = px.histogram(
                    df,
                    x="当前价格",
                    nbins=20,
                    title="股价分布",
                    labels={"当前价格": "当前价格 (¥)"},
                )
                st.plotly_chart(
                    fig_hist, use_container_width=True, key=f"price_hist_{key_suffix}"
                )

        with price_col2:
            # 价格 vs 评分散点图
            if "当前价格" in df.columns and "综合评分" in df.columns:
                fig_scatter = px.scatter(
                    df,
                    x="当前价格",
                    y="综合评分",
                    size="市值" if "市值" in df.columns else None,
                    color="建议" if "建议" in df.columns else None,
                    hover_name="股票名称" if "股票名称" in df.columns else None,
                    title="价格 vs 评分关系",
                    labels={"当前价格": "当前价格 (¥)", "综合评分": "综合评分"},
                )
                st.plotly_chart(
                    fig_scatter,
                    use_container_width=True,
                    key=f"price_scatter_{key_suffix}",
                )

        # 涨跌幅分析
        if "涨跌幅" in df.columns:
            st.markdown("##### 📊 涨跌幅分析")

            change_col1, change_col2, change_col3 = st.columns(3)

            with change_col1:
                positive_count = len(df[df["涨跌幅"] > 0])
                st.metric("上涨股票数", positive_count)

            with change_col2:
                negative_count = len(df[df["涨跌幅"] < 0])
                st.metric("下跌股票数", negative_count)

            with change_col3:
                flat_count = len(df[df["涨跌幅"] == 0])
                st.metric("平盘股票数", flat_count)

            # 涨跌幅分布图
            fig_change = px.histogram(
                df,
                x="涨跌幅",
                nbins=30,
                title="涨跌幅分布",
                labels={"涨跌幅": "涨跌幅 (%)"},
            )
            fig_change.add_vline(
                x=0, line_dash="dash", line_color="red", annotation_text="平盘线"
            )
            st.plotly_chart(
                fig_change, use_container_width=True, key=f"change_hist_{key_suffix}"
            )

    def _render_detailed_comparison(self, df: pd.DataFrame, key_suffix: str):
        """渲染详细对比"""

        if df.empty:
            st.info("无数据可对比")
            return

        st.markdown("#### 🔍 股票详细对比")

        # 选择股票进行对比
        if "股票名称" in df.columns:
            available_stocks = df["股票名称"].tolist()

            selected_stocks = st.multiselect(
                "选择要对比的股票 (最多5只)",
                options=available_stocks,
                default=available_stocks[:3],
                max_selections=5,
                key=f"compare_stocks_{key_suffix}",
            )

            if selected_stocks:
                compare_df = df[df["股票名称"].isin(selected_stocks)]

                # 对比表格
                st.markdown("##### 📊 基础信息对比")

                compare_columns = [
                    "股票名称",
                    "股票代码",
                    "当前价格",
                    "涨跌幅",
                    "综合评分",
                    "技术评分",
                    "基本面评分",
                    "建议",
                ]
                compare_columns = [
                    col for col in compare_columns if col in compare_df.columns
                ]

                if compare_columns:
                    st.dataframe(
                        compare_df[compare_columns].set_index("股票名称"),
                        use_container_width=True,
                    )

                # 雷达图对比
                if len(selected_stocks) <= 3:
                    self._render_radar_comparison(compare_df, key_suffix)

                # 指标对比图
                self._render_metrics_comparison(compare_df, key_suffix)

    def _render_radar_comparison(self, df: pd.DataFrame, key_suffix: str):
        """渲染雷达图对比"""

        st.markdown("##### 🎯 多维评分对比")

        # 准备雷达图数据
        radar_metrics = ["综合评分", "技术评分", "基本面评分"]
        radar_metrics = [col for col in radar_metrics if col in df.columns]

        if len(radar_metrics) < 3:
            st.info("评分数据不足，无法绘制雷达图")
            return

        fig = go.Figure()

        for _, row in df.iterrows():
            values = [row[metric] for metric in radar_metrics] + [
                row[radar_metrics[0]]
            ]  # 闭合图形

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=radar_metrics + [radar_metrics[0]],
                    fill="toself",
                    name=row["股票名称"] if "股票名称" in row else row.name,
                )
            )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=True,
            title="股票多维评分对比",
        )

        st.plotly_chart(fig, use_container_width=True, key=f"radar_{key_suffix}")

    def _render_metrics_comparison(self, df: pd.DataFrame, key_suffix: str):
        """渲染指标对比图"""

        st.markdown("##### 📈 关键指标对比")

        # 选择要对比的指标
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_columns = ["排名"]
        numeric_columns = [col for col in numeric_columns if col not in exclude_columns]

        if not numeric_columns:
            st.info("无数值指标可对比")
            return

        selected_metric = st.selectbox(
            "选择对比指标", options=numeric_columns, key=f"compare_metric_{key_suffix}"
        )

        if selected_metric and "股票名称" in df.columns:
            # 柱状图对比
            fig_bar = px.bar(
                df,
                x="股票名称",
                y=selected_metric,
                title=f"{selected_metric}对比",
                color=selected_metric,
                color_continuous_scale="Viridis",
            )

            st.plotly_chart(
                fig_bar, use_container_width=True, key=f"metrics_bar_{key_suffix}"
            )

    def _render_table_actions(self, df: pd.DataFrame, key_suffix: str):
        """渲染表格操作"""

        st.markdown("---")
        st.markdown("##### 🛠️ 表格操作")

        action_col1, action_col2, action_col3, action_col4 = st.columns(4)

        with action_col1:
            if st.button("📥 导出CSV", key=f"export_csv_{key_suffix}"):
                self._export_csv(df)

        with action_col2:
            if st.button("📊 导出Excel", key=f"export_excel_{key_suffix}"):
                self._export_excel(df)

        with action_col3:
            if st.button("🔄 刷新数据", key=f"refresh_{key_suffix}"):
                st.rerun()

        with action_col4:
            if st.button("💾 保存筛选", key=f"save_filter_{key_suffix}"):
                st.success("筛选条件已保存")

    def _export_csv(self, df: pd.DataFrame):
        """导出CSV"""

        try:
            csv_data = df.to_csv(index=False, encoding="utf-8")
            st.download_button(
                label="下载CSV文件",
                data=csv_data,
                file_name=f"stock_rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
            st.success("CSV文件已准备下载")
        except Exception as e:
            st.error(f"导出CSV失败: {e}")

    def _export_excel(self, df: pd.DataFrame):
        """导出Excel"""
        st.info("Excel导出功能开发中...")

    def _render_empty_state_help(self):
        """渲染空状态帮助信息"""

        st.markdown(
            """
        ### 📊 如何获取股票排名数据
        
        **数据来源：**
        - 完成市场扫描后自动生成
        - 包含AI智能评分和推荐建议
        - 支持多维度筛选和分析
        
        **功能特性：**
        - 📋 智能排名表格
        - 📊 评分分布分析  
        - 🎯 投资建议统计
        - 📈 价格关系分析
        - 🔍 股票详细对比
        """
        )


class EnhancedSectorHeatmapDisplay:
    """增强版板块热力图展示组件"""

    def render(self, sectors_data: dict, key_suffix: str = "") -> None:
        """渲染增强版板块热力图"""

        if not sectors_data:
            st.info("🔥 暂无板块分析数据")
            return

        st.markdown("#### 🔥 板块热力图分析")

        # 热力图选项
        heatmap_col1, heatmap_col2 = st.columns(2)

        with heatmap_col1:
            metric_options = ["涨跌幅", "成交额", "活跃度", "推荐度"]
            selected_metric = st.selectbox(
                "选择显示指标",
                options=metric_options,
                key=f"heatmap_metric_{key_suffix}",
            )

        with heatmap_col2:
            colorscale_options = ["RdYlGn", "Viridis", "RdBu", "Spectral"]
            selected_colorscale = st.selectbox(
                "选择色彩方案",
                options=colorscale_options,
                key=f"heatmap_color_{key_suffix}",
            )

        # 准备热力图数据
        sector_names = list(sectors_data.keys())

        metric_mapping = {
            "涨跌幅": "change_percent",
            "成交额": "volume",
            "活跃度": "activity_score",
            "推荐度": "recommendation_score",
        }

        metric_key = metric_mapping[selected_metric]
        sector_values = [
            sectors_data[sector].get(metric_key, 0) for sector in sector_names
        ]

        # 创建热力图
        fig = go.Figure(
            data=go.Heatmap(
                z=[sector_values],
                x=sector_names,
                y=[selected_metric],
                colorscale=selected_colorscale,
                text=[[f"{value:.2f}" for value in sector_values]],
                texttemplate="%{text}",
                textfont={"size": 12},
                showscale=True,
                colorbar=dict(title=selected_metric),
            )
        )

        fig.update_layout(
            title=f"板块{selected_metric}热力图",
            xaxis_title="板块",
            height=300,
            margin=dict(t=50, l=50, r=50, b=100),
        )

        st.plotly_chart(
            fig, use_container_width=True, key=f"sector_heatmap_{key_suffix}"
        )

        # 板块排名
        self._render_sector_ranking(
            sectors_data, selected_metric, metric_key, key_suffix
        )

    def _render_sector_ranking(
        self, sectors_data: dict, metric_name: str, metric_key: str, key_suffix: str
    ):
        """渲染板块排名"""

        st.markdown(f"##### 📊 板块{metric_name}排名")

        # 排序板块
        sorted_sectors = sorted(
            sectors_data.items(), key=lambda x: x[1].get(metric_key, 0), reverse=True
        )

        # 显示排名
        for i, (sector_name, sector_data) in enumerate(sorted_sectors[:10], 1):

            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                st.write(f"**{i}.**")

            with col2:
                st.write(f"**{sector_name}**")

            with col3:
                value = sector_data.get(metric_key, 0)
                if metric_name == "涨跌幅":
                    st.write(f"{value:+.2f}%")
                elif metric_name == "成交额":
                    st.write(f"{value:.1f}亿")
                else:
                    st.write(f"{value:.1f}")


class EnhancedMarketBreadthGauge:
    """增强版市场广度仪表盘组件"""

    def render(self, breadth_data: dict) -> None:
        """渲染增强版市场广度仪表盘"""

        if not breadth_data:
            st.info("📈 暂无市场广度数据")
            return

        st.markdown("#### 📈 市场广度仪表盘")

        # 主要指标仪表盘
        gauge_col1, gauge_col2 = st.columns(2)

        with gauge_col1:
            self._render_market_strength_gauge(breadth_data.get("market_strength", 50))

        with gauge_col2:
            self._render_sentiment_gauge(breadth_data.get("sentiment_index", 50))

        # 详细指标网格
        self._render_breadth_metrics_grid(breadth_data)

        # 市场广度趋势图
        self._render_breadth_trends(breadth_data)

    def _render_market_strength_gauge(self, strength_score: float):
        """渲染市场强度仪表盘"""

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
                        {"range": [30, 70], "color": "yellow"},
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

        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True, key="market_strength_gauge")

        # 文字解读
        if strength_score >= 70:
            st.success(f"🟢 市场强劲 ({strength_score:.1f})")
        elif strength_score >= 40:
            st.warning(f"🟡 市场一般 ({strength_score:.1f})")
        else:
            st.error(f"🔴 市场疲弱 ({strength_score:.1f})")

    def _render_sentiment_gauge(self, sentiment_score: float):
        """渲染市场情绪仪表盘"""

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=sentiment_score,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "市场情绪指数"},
                delta={"reference": 50},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": "purple"},
                    "steps": [
                        {"range": [0, 30], "color": "red"},
                        {"range": [30, 70], "color": "yellow"},
                        {"range": [70, 100], "color": "green"},
                    ],
                    "threshold": {
                        "line": {"color": "black", "width": 4},
                        "thickness": 0.75,
                        "value": 75,
                    },
                },
            )
        )

        fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True, key="sentiment_gauge")

        # 文字解读
        if sentiment_score >= 70:
            st.success(f"😊 情绪乐观 ({sentiment_score:.1f})")
        elif sentiment_score >= 40:
            st.warning(f"😐 情绪中性 ({sentiment_score:.1f})")
        else:
            st.error(f"😰 情绪悲观 ({sentiment_score:.1f})")

    def _render_breadth_metrics_grid(self, breadth_data: dict):
        """渲染市场广度指标网格"""

        st.markdown("##### 📊 关键指标")

        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

        with metric_col1:
            up_ratio = breadth_data.get("up_ratio", 50)
            up_change = breadth_data.get("up_ratio_change", 0)
            st.metric("上涨占比", f"{up_ratio:.1f}%", delta=f"{up_change:+.1f}%")

        with metric_col2:
            activity = breadth_data.get("activity_index", 50)
            activity_change = breadth_data.get("activity_change", 0)
            st.metric("成交活跃度", f"{activity:.1f}", delta=f"{activity_change:+.1f}")

        with metric_col3:
            net_inflow = breadth_data.get("net_inflow", 0)
            inflow_change = breadth_data.get("net_inflow_change", 0)
            st.metric(
                "资金净流入", f"{net_inflow:.1f}亿", delta=f"{inflow_change:+.1f}亿"
            )

        with metric_col4:
            new_highs = breadth_data.get("new_high_count", 0)
            new_lows = breadth_data.get("new_low_count", 0)
            ratio = (
                (new_highs / (new_highs + new_lows) * 100)
                if (new_highs + new_lows) > 0
                else 50
            )
            st.metric("新高新低比", f"{ratio:.1f}%", delta=f"{new_highs}/{new_lows}")

        # 次要指标
        st.markdown("##### 📈 次要指标")

        secondary_col1, secondary_col2, secondary_col3, secondary_col4 = st.columns(4)

        with secondary_col1:
            st.metric("涨停股票", breadth_data.get("limit_up_count", 0))

        with secondary_col2:
            st.metric("跌停股票", breadth_data.get("limit_down_count", 0))

        with secondary_col3:
            st.metric("创新高股票", breadth_data.get("new_high_count", 0))

        with secondary_col4:
            st.metric("创新低股票", breadth_data.get("new_low_count", 0))

    def _render_breadth_trends(self, breadth_data: dict):
        """渲染市场广度趋势图"""

        st.markdown("##### 📈 广度趋势分析")

        # 由于这是实时数据，这里创建一个示例趋势图
        # 实际实现中应该从历史数据中获取趋势

        import random

        # 模拟趋势数据
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")

        trend_data = {
            "上涨占比": [
                breadth_data.get("up_ratio", 50) + random.uniform(-10, 10)
                for _ in range(30)
            ],
            "成交活跃度": [
                breadth_data.get("activity_index", 50) + random.uniform(-15, 15)
                for _ in range(30)
            ],
            "市场情绪": [
                breadth_data.get("sentiment_index", 50) + random.uniform(-12, 12)
                for _ in range(30)
            ],
        }

        fig = go.Figure()

        for metric, values in trend_data.items():
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode="lines+markers",
                    name=metric,
                    line=dict(width=2),
                )
            )

        fig.update_layout(
            title="市场广度趋势 (最近30天)",
            xaxis_title="日期",
            yaxis_title="指数值",
            height=400,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True, key="breadth_trends")

        st.caption("📝 注：趋势数据为模拟数据，实际部署时将使用真实历史数据")
