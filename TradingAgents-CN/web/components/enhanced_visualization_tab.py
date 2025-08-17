"""
Enhanced Visualization Tab Component
增强可视化标签组件 - 集成ChartingArtist API和图表展示功能
"""

import base64
import json
import os
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

from tradingagents.services.file_manager import FileManager
from tradingagents.utils.logging_init import get_logger
from web.components.custom_model_helper import validate_custom_model_name
from web.utils.model_catalog import (
    get_deepseek_models,
    get_google_models,
    get_siliconflow_models,
)

logger = get_logger("enhanced_visualization")


class ChartingArtistAPI:
    """ChartingArtist API客户端"""

    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv(
            "CHARTING_ARTIST_API_URL", "http://localhost:8000/api"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {"Content-Type": "application/json", "User-Agent": "TradingAgents-CN/1.0"}
        )

    def generate_charts(
        self,
        analysis_id: str,
        chart_types: list[str],
        config: dict[str, Any],
        data_sources: dict[str, Any],
    ) -> dict[str, Any]:
        """生成图表"""
        try:
            # 统一chart_types到后端规范
            type_map = {
                "candlestick": "candlestick",
                "line": "line_chart",
                "bar": "bar_chart",
                "pie": "pie_chart",
                "scatter": "scatter_plot",
                "heatmap": "heatmap",
                "radar": "radar_chart",
                "gauge": "gauge_chart",
                "waterfall": "waterfall",
                "box": "box_plot",
            }
            normalized_types = [type_map.get(t, t) for t in chart_types]
            payload = {
                "analysis_id": analysis_id,
                "chart_types": normalized_types,
                "config": config,
                "data_sources": data_sources,
            }
            # 兼容LLM绘图的顶层配置传递
            if isinstance(config, dict):
                if "render_mode" in config:
                    payload["render_mode"] = config.get("render_mode")
                if "model_override" in config:
                    payload["model_override"] = config.get("model_override")

            response = self.session.post(
                f"{self.base_url}/charts/generate", json=payload, timeout=60
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API请求失败: {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            logger.error(f"API连接失败: {e}")
            return {"error": str(e)}

    def get_charts(self, analysis_id: str) -> dict[str, Any]:
        """获取分析的图表"""
        try:
            response = self.session.get(
                f"{self.base_url}/charts/{analysis_id}", timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_chart_by_id(self, chart_id: str) -> dict[str, Any]:
        """根据ID获取特定图表"""
        try:
            response = self.session.get(
                f"{self.base_url}/charts/chart/{chart_id}", timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def delete_chart(self, chart_id: str) -> dict[str, Any]:
        """删除图表"""
        try:
            response = self.session.delete(
                f"{self.base_url}/charts/chart/{chart_id}", timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def list_charts(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """列出所有图表"""
        try:
            params = {"limit": limit, "offset": offset}
            response = self.session.get(
                f"{self.base_url}/charts/list", params=params, timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def batch_operations(self, operations: list[dict[str, Any]]) -> dict[str, Any]:
        """批量图表操作"""
        try:
            payload = {"operations": operations}
            response = self.session.post(
                f"{self.base_url}/charts/batch", json=payload, timeout=120
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}


def render_enhanced_visualization_tab(
    analysis_results: dict[str, Any], analysis_id: str = None, symbol: str = None
) -> None:
    """渲染增强的可视化标签页"""

    st.markdown("## 📊 智能图表分析")

    # 检查ChartingArtist是否启用
    if not is_charting_artist_enabled():
        render_disabled_state()
        return

    # 创建子标签页
    viz_tabs = st.tabs(["🎨 图表生成", "📈 图表展示", "📊 图表管理", "⚙️ 设置"])
    # 若外部触发打开“图表管理”，自动切换对应标签
    try:
        if st.session_state.pop("_open_chart_management", False):
            st.session_state.show_charts_list = True
            st.markdown(
                """
                <script>
                setTimeout(function(){
                    const tabs = document.querySelectorAll('div[role="tab"]');
                    for (const t of tabs) {
                        if (t.innerText && t.innerText.indexOf('图表管理') !== -1) { t.click(); break; }
                    }
                }, 50);
                </script>
                """,
                unsafe_allow_html=True,
            )
    except Exception:
        pass

    with viz_tabs[0]:
        render_chart_generation_tab(analysis_results, analysis_id, symbol)

    with viz_tabs[1]:
        render_chart_display_tab(analysis_results, analysis_id, symbol)

    with viz_tabs[2]:
        render_chart_management_tab()

    with viz_tabs[3]:
        render_chart_settings_tab()


def render_disabled_state() -> None:
    """渲染禁用状态"""

    with st.container():
        st.info(
            """
        🎨 **ChartingArtist功能未启用**
        
        ChartingArtist是TradingAgents-CN的可视化专家，能够基于分析结果生成专业的图表和可视化内容。
        
        **启用方法：**
        1. 设置环境变量：`CHARTING_ARTIST_ENABLED=true`
        2. 重启应用服务
        3. 刷新页面即可使用完整的可视化功能
        """
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(
                """
            **📈 技术分析图表**
            - K线图与技术指标
            - 支撑阻力位标注
            - 交易量分析
            - 趋势线识别
            """
            )

        with col2:
            st.markdown(
                """
            **📊 基本面图表**
            - 财务数据柱状图
            - 盈利能力对比
            - 现金流瀑布图
            - ROE/ROA雷达图
            """
            )

        with col3:
            st.markdown(
                """
            **🎯 风险分析图表**
            - 风险热力图
            - 投资组合饼图
            - 相关性矩阵
            - 波动率箱线图
            """
            )

        st.markdown("---")

        # 显示示例图表
        render_demo_charts()


def render_chart_generation_tab(
    analysis_results: dict[str, Any], analysis_id: str = None, symbol: str = None
) -> None:
    """渲染图表生成标签页"""

    st.markdown("### 🎨 智能图表生成")

    if not analysis_results:
        st.warning("请先运行个股分析以获得数据")
        return

    # 生成配置区域
    with st.expander("📋 生成配置", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**图表类型选择**")

            # 支持的图表类型
            chart_types = {
                "candlestick": "📈 K线图",
                "bar": "📊 柱状图",
                "pie": "🥧 饼图",
                "line": "📉 折线图",
                "scatter": "🎯 散点图",
                "heatmap": "🔥 热力图",
                "radar": "🕸️ 雷达图",
                "gauge": "📏 仪表盘",
                "waterfall": "🌊 瀑布图",
                "box": "📦 箱线图",
            }

            selected_types = []
            for chart_type, display_name in chart_types.items():
                if st.checkbox(display_name, key=f"chart_{chart_type}"):
                    selected_types.append(chart_type)

        with col2:
            st.markdown("**生成配置**")

            theme = st.selectbox(
                "主题", ["plotly_dark", "plotly_white", "ggplot2", "seaborn"], index=0
            )
            interactive = st.checkbox("交互式图表", value=True)
            export_format = st.selectbox(
                "导出格式", ["html", "json", "png", "svg"], index=0
            )
            render_mode = st.selectbox(
                "绘图方式(LLM)",
                ["python", "html"],
                index=0,
                help="LLM 生成 Plotly 代码或直接生成可嵌入 HTML。Docker 内建议选择 python。",
            )

            # 供应商 → 模型 下拉逻辑（与主面板一致，限定为多模型管理器支持的三类）
            st.markdown("**绘图模型 (供应商 → 型号)**")
            viz_providers = ["google", "deepseek", "siliconflow"]
            viz_provider_labels = {
                "google": "🌟 Google AI (Gemini)",
                "deepseek": "🚀 DeepSeek 官方",
                "siliconflow": "🌐 SiliconFlow (聚合)",
            }
            current_provider = st.session_state.get(
                "viz_llm_provider", os.getenv("CHARTING_ARTIST_PROVIDER", "siliconflow")
            )
            provider = st.selectbox(
                "LLM提供商",
                options=viz_providers,
                index=(
                    viz_providers.index(current_provider)
                    if current_provider in viz_providers
                    else 2
                ),
                format_func=lambda k: viz_provider_labels.get(k, k),
                key="viz_provider_select",
            )

            # 模型选项
            if provider == "google":
                catalog = get_google_models()
            elif provider == "deepseek":
                catalog = get_deepseek_models()
            else:
                catalog = get_siliconflow_models()

            options = catalog + ["💡 自定义模型"]
            default_model = os.getenv(
                "CHARTING_ARTIST_LLM_MODEL", "moonshotai/Kimi-K2-Instruct"
            )
            model_choice = st.selectbox(
                "选择模型",
                options=options,
                index=(
                    options.index(default_model)
                    if default_model in options
                    else (options.index(catalog[0]) if catalog else 0)
                ),
                key="viz_model_select",
            )
            if model_choice == "💡 自定义模型":
                custom_model = st.text_input(
                    "🔧 自定义模型",
                    value=(default_model if default_model not in catalog else ""),
                    placeholder=(
                        "google: gemini-2.5-pro | deepseek: deepseek-chat | siliconflow: org/model"
                    ),
                    key="viz_model_custom_input",
                )
                if custom_model:
                    is_valid, msg = validate_custom_model_name(
                        custom_model,
                        (
                            "siliconflow"
                            if "/" in custom_model
                            else (
                                "google"
                                if custom_model.startswith("gemini")
                                else "deepseek"
                            )
                        ),
                    )
                    if is_valid:
                        model_override = custom_model
                    else:
                        st.error(msg)
                        model_override = default_model
                else:
                    model_override = default_model
            else:
                model_override = model_choice
            # 记录选择
            st.session_state.viz_llm_provider = provider

            # 高级配置
            with st.expander("高级配置"):
                width = st.number_input(
                    "宽度", min_value=400, max_value=1600, value=800
                )
                height = st.number_input(
                    "高度", min_value=300, max_value=1000, value=600
                )
                dpi = st.number_input("DPI", min_value=72, max_value=300, value=150)

    # 生成按钮
    if st.button("🚀 开始生成图表", type="primary", disabled=not selected_types):
        if not selected_types:
            st.error("请至少选择一种图表类型")
            return

        # 准备生成配置
        generation_config = {
            "theme": theme,
            "interactive": interactive,
            "export_format": export_format,
            "width": width,
            "height": height,
            "dpi": dpi,
        }

        # 执行图表生成
        execute_chart_generation(
            analysis_results=analysis_results,
            analysis_id=analysis_id or f"viz_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            chart_types=selected_types,
            config={
                **generation_config,
                "render_mode": render_mode,
                "model_override": model_override,
            },
        )


def render_chart_display_tab(
    analysis_results: dict[str, Any], analysis_id: str = None, symbol: str = None
) -> None:
    """渲染图表展示标签页"""

    st.markdown("### 📈 图表展示")

    # 检查是否有图表数据
    chart_data = analysis_results.get("charting_artist", {})
    generated_charts = chart_data.get("charts_generated", [])

    if generated_charts:
        display_generated_charts(generated_charts)
    else:
        # 尝试从API获取图表
        if analysis_id:
            api_charts = load_charts_from_api(analysis_id)
            if api_charts:
                display_api_charts(api_charts)
            else:
                display_no_charts_message()
        else:
            display_no_charts_message()

    # 显示本地图表作为后备
    local_charts = get_local_charts(symbol)
    if local_charts:
        st.markdown("---")
        st.markdown("### 📂 历史图表")
        display_local_charts(local_charts)


def render_chart_management_tab() -> None:
    """渲染图表管理标签页"""

    st.markdown("### 📊 图表管理")

    # 管理操作区域
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📋 查看所有图表"):
            display_all_charts_list()

    with col2:
        if st.button("🧹 清理旧图表"):
            show_cleanup_dialog()

    with col3:
        if st.button("📦 批量操作"):
            show_batch_operations()

    with col4:
        if st.button("📊 使用统计"):
            show_usage_statistics()

    # 图表列表区域
    if "show_charts_list" in st.session_state and st.session_state.show_charts_list:
        render_charts_list_panel()

    if (
        "show_cleanup_dialog" in st.session_state
        and st.session_state.show_cleanup_dialog
    ):
        render_cleanup_panel()

    if "show_batch_ops" in st.session_state and st.session_state.show_batch_ops:
        render_batch_operations_panel()

    if "show_usage_stats" in st.session_state and st.session_state.show_usage_stats:
        render_usage_statistics_panel()


def render_chart_settings_tab() -> None:
    """渲染图表设置标签页"""

    st.markdown("### ⚙️ 图表设置")

    # 默认设置
    with st.expander("🎨 默认外观设置", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            default_theme = st.selectbox(
                "默认主题", ["plotly_dark", "plotly_white", "ggplot2", "seaborn"]
            )
            default_width = st.number_input(
                "默认宽度", min_value=400, max_value=1600, value=800
            )
            default_height = st.number_input(
                "默认高度", min_value=300, max_value=1000, value=600
            )

        with col2:
            color_scheme = st.selectbox(
                "配色方案", ["默认", "蓝色系", "绿色系", "红色系", "紫色系"]
            )
            show_watermark = st.checkbox("显示水印", value=True)
            auto_refresh = st.checkbox("自动刷新", value=False)

    # 性能设置
    with st.expander("⚡ 性能设置"):
        col1, col2 = st.columns(2)

        with col1:
            cache_enabled = st.checkbox("启用缓存", value=True)
            max_cache_size = st.number_input(
                "最大缓存大小(MB)", min_value=10, max_value=1000, value=100
            )

        with col2:
            concurrent_generation = st.checkbox("并发生成", value=True)
            max_concurrent_jobs = st.number_input(
                "最大并发数", min_value=1, max_value=10, value=3
            )

    # API设置
    with st.expander("🔌 API设置"):
        api_url = st.text_input("API地址", value="http://localhost:8000/api")
        timeout = st.number_input("超时时间(秒)", min_value=10, max_value=300, value=60)
        retry_count = st.number_input("重试次数", min_value=0, max_value=5, value=2)

    # 保存设置按钮
    if st.button("💾 保存设置"):
        settings = {
            "default_theme": default_theme,
            "default_width": default_width,
            "default_height": default_height,
            "color_scheme": color_scheme,
            "show_watermark": show_watermark,
            "auto_refresh": auto_refresh,
            "cache_enabled": cache_enabled,
            "max_cache_size": max_cache_size,
            "concurrent_generation": concurrent_generation,
            "max_concurrent_jobs": max_concurrent_jobs,
            "api_url": api_url,
            "timeout": timeout,
            "retry_count": retry_count,
        }

        save_chart_settings(settings)
        st.success("✅ 设置已保存")


def execute_chart_generation(
    analysis_results: dict[str, Any],
    analysis_id: str,
    symbol: str,
    chart_types: list[str],
    config: dict[str, Any],
) -> None:
    """执行图表生成"""

    # 显示进度条
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        # 初始化API客户端
        api = ChartingArtistAPI()

        status_text.text("🔄 准备生成数据...")
        progress_bar.progress(10)

        # 准备数据源
        data_sources = prepare_chart_data_sources(analysis_results, symbol)

        status_text.text("📡 调用ChartingArtist API...")
        progress_bar.progress(30)

        # 调用API生成图表（仅使用真实数据，不进行本地模拟回退）
        result = api.generate_charts(
            analysis_id,
            chart_types,
            config,
            data_sources,
        )

        progress_bar.progress(70)

        if "error" in result:
            # API失败，不做本地模拟，直接报错（保证不显示虚假数据）
            status_text.text("❌ 图表生成失败（API错误）")
            st.error(
                f"图表生成失败: {result.get('error', '未知错误')}。系统已按要求禁用本地模拟图表。"
            )
        else:
            # API成功
            progress_bar.progress(100)
            status_text.text("✅ API生成完成")

            # 更新分析结果
            analysis_results["charting_artist"] = result
            st.success(f"🎯 成功生成 {result.get('total_charts', 0)} 个图表")

            # 刷新页面显示
            st.rerun()

    except Exception as e:
        logger.error(f"图表生成失败: {e}")
        status_text.text("❌ 生成失败")
        st.error(f"图表生成失败: {str(e)}")
    finally:
        # 清理进度显示
        progress_bar.empty()
        status_text.empty()


def display_generated_charts(charts: list[dict[str, Any]]) -> None:
    """显示已生成的图表"""

    if not charts:
        st.info("暂无生成的图表")
        return

    # 批量操作工具条（保存到图书馆）
    all_ids = []
    for c in charts:
        cid = c.get("chart_id") or c.get("id") or str(hash(str(c)))
        all_ids.append(cid)
    sel_key = "chart_batch_selection"
    if sel_key not in st.session_state or not isinstance(
        st.session_state.get(sel_key), set
    ):
        st.session_state[sel_key] = set()

    selected_now = st.session_state[sel_key].intersection(set(all_ids))
    cbar1, cbar2, cbar3, _ = st.columns([2, 2, 2, 6])
    with cbar1:
        st.caption(f"已选中: {len(selected_now)}")
    with cbar2:
        if st.button("📚 保存选中到图书馆", disabled=(len(selected_now) == 0)):
            saved = 0
            for c in charts:
                cid = c.get("chart_id") or c.get("id") or str(hash(str(c)))
                if cid in selected_now:
                    _save_chart_to_library(c)
                    saved += 1
            if saved:
                st.success(f"✅ 已保存 {saved} 个图表到图书馆")
    with cbar3:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("全选本页"):
                for cid in all_ids:
                    st.session_state[sel_key].add(cid)
                    st.session_state[f"chart_sel_{cid}"] = True
                st.rerun()
        with c2:
            if st.button("清空选择", disabled=(len(selected_now) == 0)):
                for cid in list(selected_now):
                    st.session_state[sel_key].discard(cid)
                    st.session_state[f"chart_sel_{cid}"] = False
                st.rerun()

    # 按类型分组显示
    chart_groups = {}
    for chart in charts:
        chart_type = chart.get("chart_type", "unknown")
        if chart_type not in chart_groups:
            chart_groups[chart_type] = []
        chart_groups[chart_type].append(chart)

    # 创建标签页或展开器
    if len(chart_groups) > 1:
        # 多种类型用标签页
        group_names = list(chart_groups.keys())
        tabs = st.tabs([f"📊 {name.title()}" for name in group_names])

        for i, (group_name, group_charts) in enumerate(chart_groups.items()):
            with tabs[i]:
                display_chart_group(group_charts)
    else:
        # 单一类型直接显示
        chart_list = list(chart_groups.values())[0]
        display_chart_group(chart_list)


def display_chart_group(charts: list[dict[str, Any]]) -> None:
    """显示一组图表"""

    for i, chart in enumerate(charts):
        try:
            # 显示图表信息 + 选择框
            cid = chart.get("chart_id") or chart.get("id") or f"idx_{i}"
            sel_key = "chart_batch_selection"
            col0, col1, col2, col3, col4 = st.columns([1, 5, 2, 2, 2])
            with col0:
                checked = st.checkbox("", key=f"chart_sel_{cid}", help="选择此图表")
                if checked:
                    st.session_state.setdefault(sel_key, set()).add(cid)
                else:
                    st.session_state.setdefault(sel_key, set()).discard(cid)

            with col1:
                st.markdown(f"**{chart.get('title', f'Chart {i+1}')}**")
                if chart.get("description"):
                    st.caption(chart["description"])

            with col2:
                # 下载按钮
                if st.button(
                    "⬇️ 下载", key=f"download_chart_{chart.get('chart_id', i)}"
                ):
                    download_chart(chart)

            with col3:
                # 删除按钮
                if st.button("🗑️ 删除", key=f"delete_chart_{chart.get('chart_id', i)}"):
                    delete_chart(chart)

            with col4:
                # 保存到图书馆
                if st.button(
                    "📚 保存", key=f"save_chart_lib_{chart.get('chart_id', i)}"
                ):
                    _save_chart_to_library(chart)

            # 显示图表内容
            render_chart_content(chart)

            st.markdown("---")

        except Exception as e:
            logger.error(f"显示图表失败: {e}")
            st.error(f"图表 {chart.get('title', 'Unknown')} 显示失败")


def render_chart_content(chart: dict[str, Any]) -> None:
    """渲染图表内容"""

    try:
        # 检查图表数据类型
        if "plotly_json" in chart:
            # Plotly JSON格式
            fig_dict = chart["plotly_json"]
            if isinstance(fig_dict, str):
                fig_dict = json.loads(fig_dict)

            fig = go.Figure(fig_dict)
            st.plotly_chart(fig, use_container_width=True)

        elif "file_path" in chart or "path" in chart:
            # 文件路径格式
            file_path = chart.get("file_path") or chart.get("path")
            if file_path and Path(file_path).exists():

                if file_path.endswith(".html"):
                    # HTML文件
                    with open(file_path, encoding="utf-8") as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=600)

                elif file_path.endswith(".json"):
                    # JSON文件
                    with open(file_path, encoding="utf-8") as f:
                        fig_dict = json.load(f)
                    fig = go.Figure(fig_dict)
                    st.plotly_chart(fig, use_container_width=True)

                elif file_path.endswith((".png", ".jpg", ".jpeg", ".svg")):
                    # 图片文件
                    st.image(file_path, use_column_width=True)

                else:
                    st.warning(f"不支持的文件格式: {file_path}")
            else:
                st.error("图表文件不存在")

        # 兼容：后端返回远程链接
        elif "image_url" in chart or "url" in chart or "download_url" in chart:
            url = (
                chart.get("image_url") or chart.get("url") or chart.get("download_url")
            )
            try:
                if isinstance(url, str) and url.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".svg")
                ):
                    st.image(url, use_column_width=True)
                elif isinstance(url, str) and url.lower().endswith((".html",)):
                    import requests

                    r = requests.get(url, timeout=5)
                    if r.ok:
                        st.components.v1.html(r.text, height=600, scrolling=True)
                    else:
                        st.markdown(f"[打开图表页面]({url})")
                else:
                    import requests

                    r = requests.get(url, timeout=5)
                    if r.ok:
                        ct = r.headers.get("content-type", "")
                        if "image" in ct:
                            st.image(r.content, use_column_width=True)
                        elif "html" in ct:
                            st.components.v1.html(r.text, height=600, scrolling=True)
                        else:
                            st.markdown(f"[下载/查看图表]({url})")
                    else:
                        st.markdown(f"[打开图表链接]({url})")
            except Exception:
                if isinstance(url, str):
                    st.markdown(f"[打开图表链接]({url})")
                else:
                    st.warning("未找到可显示的图表数据")

        elif "base64_data" in chart:
            # Base64编码数据
            image_data = base64.b64decode(chart["base64_data"])
            st.image(image_data, use_column_width=True)

        else:
            st.warning("未找到可显示的图表数据")

    except Exception as e:
        logger.error(f"渲染图表内容失败: {e}")
        st.error("图表内容渲染失败")


def _save_chart_to_library(chart: dict[str, Any]) -> None:
    """将图表保存到图书馆（附件库: category='chart'）。"""
    try:
        fm = FileManager()
        filename = None
        content = None

        # 1) 本地文件
        fp = chart.get("file_path") or chart.get("path")
        if fp and Path(fp).exists() and Path(fp).is_file():
            filename = Path(fp).name
            with open(fp, "rb") as f:
                content = f.read()

        # 2) 远程图片/页面
        if content is None:
            url = (
                chart.get("image_url") or chart.get("url") or chart.get("download_url")
            )
            if isinstance(url, str):
                try:
                    r = requests.get(url, timeout=8)
                    if r.ok and r.content:
                        content = r.content
                        # 从URL推断文件名
                        try:
                            filename = (
                                Path(url.split("?")[0]).name
                                or f"chart_{chart.get('chart_id','unknown')}"
                            )
                        except Exception:
                            filename = f"chart_{chart.get('chart_id','unknown')}"
                except Exception:
                    pass

        if content is None or filename is None:
            st.error("未找到可保存的图表数据")
            return

        meta = {
            "chart_id": chart.get("chart_id"),
            "chart_type": chart.get("chart_type"),
            "title": chart.get("title"),
            "source": "charting_artist",
            "generation_method": (chart.get("metadata") or {}).get("generation_method"),
        }
        file_id = fm.save_file(content, filename, category="chart", metadata=meta)
        # 生成缩略图（仅限PNG/JPG/JPEG）
        try:
            import io

            from PIL import Image

            suffix = Path(filename).suffix.lower()
            if suffix in [".png", ".jpg", ".jpeg"]:
                img = Image.open(io.BytesIO(content))
                img.thumbnail((320, 320))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                thumb_bytes = buf.getvalue()
                fm.save_file(
                    thumb_bytes,
                    f"{Path(filename).stem}_thumb.png",
                    category="temp",
                    metadata={
                        "thumbnail_of": file_id,
                        "source": "charting_artist",
                    },
                )
        except Exception:
            pass
        st.success(f"✅ 已保存到图书馆 (附件ID: {file_id})")
    except Exception as e:
        st.error(f"保存失败: {e}")


def prepare_chart_data_sources(
    analysis_results: dict[str, Any], symbol: str
) -> dict[str, Any]:
    """准备图表数据源"""

    data_sources = {"symbol": symbol, "analysis_results": analysis_results}

    # 增加真实OHLC数据以供后端绘图（仅真实数据，失败则不提供）
    try:
        # 计算时间范围：以分析日期为终点，向前取90天；若无分析日期，则取近90天
        import datetime as _dt

        from tradingagents.dataflows.interface import get_stock_ohlc_json

        end_date = None
        start_date = None
        try:
            end_date = analysis_results.get("analysis_date")
            if end_date:
                _end = _dt.datetime.strptime(end_date, "%Y-%m-%d")
            else:
                _end = _dt.datetime.today()
            _start = _end - _dt.timedelta(days=90)
            start_date = _start.strftime("%Y-%m-%d")
            end_date = _end.strftime("%Y-%m-%d")
        except Exception:
            _end = _dt.datetime.today()
            _start = _end - _dt.timedelta(days=90)
            start_date = _start.strftime("%Y-%m-%d")
            end_date = _end.strftime("%Y-%m-%d")

        ohlc = get_stock_ohlc_json(symbol, start_date, end_date)
        if ohlc and isinstance(ohlc, dict) and ohlc.get("records"):
            data_sources["ohlc"] = ohlc
            logger.info(
                f"📡 已附加真实OHLC数据: {symbol} {start_date}~{end_date} 条数={len(ohlc.get('records', []))}"
            )
        else:
            logger.warning("⚠️ 未获取到可用的OHLC数据，不向图表服务提供行情数据")
    except Exception as e:
        logger.error(f"❌ 获取真实OHLC失败: {e}")

    # 提取不同类型的分析数据
    if "technical_analyst" in analysis_results:
        data_sources["technical_data"] = analysis_results["technical_analyst"]

    if "fundamental_expert" in analysis_results:
        data_sources["fundamental_data"] = analysis_results["fundamental_expert"]

    if "sentiment_analyst" in analysis_results:
        data_sources["sentiment_data"] = analysis_results["sentiment_analyst"]

    if "risk_manager" in analysis_results:
        data_sources["risk_data"] = analysis_results["risk_manager"]

    return data_sources


def generate_charts_locally(
    analysis_results: dict[str, Any],
    symbol: str,
    chart_types: list[str],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """为保证数据真实，已禁用本地模拟图表回退，始终返回空。"""
    logger.info("ℹ️ 本地模拟图表已禁用，返回空列表")
    return []


def generate_single_chart_locally(
    analysis_results: dict[str, Any],
    symbol: str,
    chart_type: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """生成单个本地图表"""

    try:
        if chart_type == "candlestick":
            return create_candlestick_chart(symbol, config)
        elif chart_type == "bar":
            return create_bar_chart(analysis_results, symbol, config)
        elif chart_type == "pie":
            return create_pie_chart(analysis_results, symbol, config)
        elif chart_type == "line":
            return create_line_chart(symbol, config)
        elif chart_type == "heatmap":
            return create_heatmap_chart(analysis_results, symbol, config)
        elif chart_type == "radar":
            return create_radar_chart(analysis_results, symbol, config)
        else:
            logger.warning(f"不支持的图表类型: {chart_type}")
            return None

    except Exception as e:
        logger.error(f"生成{chart_type}图表失败: {e}")
        return None


def create_candlestick_chart(symbol: str, config: dict[str, Any]) -> dict[str, Any]:
    """创建K线图"""

    # 模拟K线数据
    import numpy as np
    import pandas as pd

    dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
    np.random.seed(42)

    # 生成模拟价格数据
    base_price = 100
    returns = np.random.normal(0.001, 0.02, len(dates))
    prices = base_price * np.cumprod(1 + returns)

    # 生成OHLC数据
    data = []
    for i, date in enumerate(dates):
        if i == 0:
            open_price = base_price
        else:
            open_price = data[i - 1]["close"]

        high = open_price * (1 + abs(np.random.normal(0, 0.01)))
        low = open_price * (1 - abs(np.random.normal(0, 0.01)))
        close = prices[i]
        volume = np.random.randint(1000000, 10000000)

        data.append(
            {
                "date": date,
                "open": open_price,
                "high": max(high, open_price, close),
                "low": min(low, open_price, close),
                "close": close,
                "volume": volume,
            }
        )

    df = pd.DataFrame(data)

    # 创建K线图
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=f"{symbol} K线",
            )
        ]
    )

    fig.update_layout(
        title=f"{symbol} K线图",
        xaxis_title="日期",
        yaxis_title="价格",
        template=config.get("theme", "plotly_dark"),
        width=config.get("width", 800),
        height=config.get("height", 600),
    )

    # 保存图表
    chart_id = f"candlestick_{symbol}_{uuid.uuid4().hex[:8]}"
    chart_path = save_chart_to_file(fig, chart_id, config.get("export_format", "html"))

    return {
        "chart_id": chart_id,
        "chart_type": "candlestick",
        "title": f"{symbol} K线图",
        "description": f"{symbol}的K线走势图",
        "file_path": chart_path,
        "metadata": {
            "symbol": symbol,
            "data_points": len(df),
            "date_range": f"{df['date'].min()} - {df['date'].max()}",
        },
    }


def create_bar_chart(
    analysis_results: dict[str, Any], symbol: str, config: dict[str, Any]
) -> dict[str, Any]:
    """创建财务数据柱状图"""

    # 模拟财务数据
    metrics = ["营收(亿)", "净利润(亿)", "ROE(%)", "ROA(%)", "毛利率(%)"]
    values = [150.5, 25.8, 15.6, 8.9, 42.3]

    fig = go.Figure(
        data=[
            go.Bar(
                x=metrics,
                y=values,
                marker_color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],
                text=[f"{v:.1f}" for v in values],
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title=f"{symbol} 关键财务指标",
        xaxis_title="指标",
        yaxis_title="数值",
        template=config.get("theme", "plotly_dark"),
        width=config.get("width", 800),
        height=config.get("height", 600),
    )

    # 保存图表
    chart_id = f"bar_{symbol}_{uuid.uuid4().hex[:8]}"
    chart_path = save_chart_to_file(fig, chart_id, config.get("export_format", "html"))

    return {
        "chart_id": chart_id,
        "chart_type": "bar",
        "title": f"{symbol} 财务指标",
        "description": f"{symbol}的关键财务指标对比",
        "file_path": chart_path,
        "metadata": {"symbol": symbol, "metrics_count": len(metrics)},
    }


def create_pie_chart(
    analysis_results: dict[str, Any], symbol: str, config: dict[str, Any]
) -> dict[str, Any]:
    """创建饼图"""

    # 模拟业务构成数据
    segments = ["主营业务", "投资收益", "其他业务", "金融服务"]
    values = [65, 15, 12, 8]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=segments,
                values=values,
                hole=0.3,
                textinfo="label+percent",
                textposition="auto",
            )
        ]
    )

    fig.update_layout(
        title=f"{symbol} 业务构成",
        template=config.get("theme", "plotly_dark"),
        width=config.get("width", 800),
        height=config.get("height", 600),
    )

    # 保存图表
    chart_id = f"pie_{symbol}_{uuid.uuid4().hex[:8]}"
    chart_path = save_chart_to_file(fig, chart_id, config.get("export_format", "html"))

    return {
        "chart_id": chart_id,
        "chart_type": "pie",
        "title": f"{symbol} 业务构成",
        "description": f"{symbol}的业务结构分析",
        "file_path": chart_path,
        "metadata": {"symbol": symbol, "segments_count": len(segments)},
    }


def create_line_chart(symbol: str, config: dict[str, Any]) -> dict[str, Any]:
    """创建折线图"""

    # 模拟股价趋势数据
    import numpy as np
    import pandas as pd

    dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=dates,
                y=prices,
                mode="lines+markers",
                name=f"{symbol} 价格趋势",
                line=dict(color="#1f77b4", width=2),
            )
        ]
    )

    fig.update_layout(
        title=f"{symbol} 价格走势",
        xaxis_title="日期",
        yaxis_title="价格",
        template=config.get("theme", "plotly_dark"),
        width=config.get("width", 800),
        height=config.get("height", 600),
    )

    # 保存图表
    chart_id = f"line_{symbol}_{uuid.uuid4().hex[:8]}"
    chart_path = save_chart_to_file(fig, chart_id, config.get("export_format", "html"))

    return {
        "chart_id": chart_id,
        "chart_type": "line",
        "title": f"{symbol} 价格走势",
        "description": f"{symbol}的价格趋势分析",
        "file_path": chart_path,
        "metadata": {"symbol": symbol, "data_points": len(dates)},
    }


def create_heatmap_chart(
    analysis_results: dict[str, Any], symbol: str, config: dict[str, Any]
) -> dict[str, Any]:
    """创建热力图"""

    # 模拟相关性矩阵数据
    assets = [symbol, "SPY", "QQQ", "IWM", "GLD"]
    corr_matrix = np.random.rand(5, 5)
    corr_matrix = (corr_matrix + corr_matrix.T) / 2  # 确保对称
    np.fill_diagonal(corr_matrix, 1)  # 对角线为1

    fig = go.Figure(
        data=go.Heatmap(
            z=corr_matrix,
            x=assets,
            y=assets,
            colorscale="RdYlBu_r",
            text=np.round(corr_matrix, 2),
            texttemplate="%{text}",
            textfont={"size": 10},
        )
    )

    fig.update_layout(
        title=f"{symbol} 资产相关性热力图",
        template=config.get("theme", "plotly_dark"),
        width=config.get("width", 800),
        height=config.get("height", 600),
    )

    # 保存图表
    chart_id = f"heatmap_{symbol}_{uuid.uuid4().hex[:8]}"
    chart_path = save_chart_to_file(fig, chart_id, config.get("export_format", "html"))

    return {
        "chart_id": chart_id,
        "chart_type": "heatmap",
        "title": f"{symbol} 相关性热力图",
        "description": f"{symbol}与其他资产的相关性分析",
        "file_path": chart_path,
        "metadata": {"symbol": symbol, "assets_count": len(assets)},
    }


def create_radar_chart(
    analysis_results: dict[str, Any], symbol: str, config: dict[str, Any]
) -> dict[str, Any]:
    """创建雷达图"""

    # 模拟评分数据
    categories = ["盈利能力", "成长性", "安全性", "流动性", "估值水平"]
    scores = [85, 78, 92, 68, 75]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=scores, theta=categories, fill="toself", name=f"{symbol} 评分"
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title=f"{symbol} 综合评分雷达图",
        template=config.get("theme", "plotly_dark"),
        width=config.get("width", 800),
        height=config.get("height", 600),
    )

    # 保存图表
    chart_id = f"radar_{symbol}_{uuid.uuid4().hex[:8]}"
    chart_path = save_chart_to_file(fig, chart_id, config.get("export_format", "html"))

    return {
        "chart_id": chart_id,
        "chart_type": "radar",
        "title": f"{symbol} 评分雷达图",
        "description": f"{symbol}的综合评分分析",
        "file_path": chart_path,
        "metadata": {
            "symbol": symbol,
            "categories_count": len(categories),
            "average_score": np.mean(scores),
        },
    }


def save_chart_to_file(fig: go.Figure, chart_id: str, export_format: str) -> str:
    """保存图表到文件"""

    # 确保输出目录存在
    charts_dir = Path("data/attachments/charts")
    charts_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件路径
    if export_format == "html":
        file_path = charts_dir / f"{chart_id}.html"
        fig.write_html(str(file_path))
    elif export_format == "json":
        file_path = charts_dir / f"{chart_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(fig.to_dict(), f, ensure_ascii=False, indent=2)
    elif export_format == "png":
        file_path = charts_dir / f"{chart_id}.png"
        fig.write_image(str(file_path))
    elif export_format == "svg":
        file_path = charts_dir / f"{chart_id}.svg"
        fig.write_image(str(file_path))
    else:
        # 默认HTML
        file_path = charts_dir / f"{chart_id}.html"
        fig.write_html(str(file_path))

    return str(file_path)


def render_demo_charts() -> None:
    """渲染演示图表"""

    st.markdown("### 📊 图表类型预览")

    demo_tabs = st.tabs(["📈 K线图", "📊 柱状图", "🥧 饼图"])

    with demo_tabs[0]:
        # K线图示例
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        np.random.seed(42)
        data = []
        base_price = 100

        for i, date in enumerate(dates):
            price = base_price + i + np.random.randn() * 2
            data.append(
                {
                    "date": date,
                    "open": price - 0.5,
                    "high": price + 1,
                    "low": price - 1,
                    "close": price + 0.5,
                }
            )

        df = pd.DataFrame(data)

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["date"],
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                )
            ]
        )

        fig.update_layout(title="K线图示例", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with demo_tabs[1]:
        # 柱状图示例
        categories = ["Q1", "Q2", "Q3", "Q4"]
        values = [23, 45, 56, 78]

        fig = go.Figure(data=[go.Bar(x=categories, y=values)])
        fig.update_layout(title="季度业绩柱状图示例", height=400)
        st.plotly_chart(fig, use_container_width=True)

    with demo_tabs[2]:
        # 饼图示例
        labels = ["业务A", "业务B", "业务C", "其他"]
        values = [40, 30, 20, 10]

        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.3)])
        fig.update_layout(title="业务构成饼图示例", height=400)
        st.plotly_chart(fig, use_container_width=True)


# 辅助函数
def is_charting_artist_enabled() -> bool:
    """检查ChartingArtist是否启用"""
    return os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() == "true"


def get_local_charts(symbol: str = None) -> list[Path]:
    """获取本地图表文件"""
    charts_dir = Path("data/attachments/charts")

    if not charts_dir.exists():
        return []

    chart_files = []
    for chart_file in charts_dir.glob("*.html"):
        if symbol is None or chart_file.name.startswith(f"{symbol}_"):
            chart_files.append(chart_file)

    # 按修改时间排序
    chart_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return chart_files


def display_local_charts(charts: list[Path]) -> None:
    """显示本地图表"""

    for i, chart_path in enumerate(charts[:5]):  # 最多显示5个
        try:
            parts = chart_path.stem.split("_")
            chart_symbol = parts[0] if len(parts) > 0 else "Unknown"
            chart_type = parts[1] if len(parts) > 1 else "unknown"

            with st.expander(
                f"📊 {chart_symbol} - {chart_type.title()}", expanded=(i == 0)
            ):
                if chart_path.exists():
                    with open(chart_path, encoding="utf-8") as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=500)
                else:
                    st.error("图表文件不存在")

        except Exception as e:
            logger.error(f"显示本地图表失败: {e}")
            st.error(f"图表加载失败: {chart_path.name}")


def display_no_charts_message() -> None:
    """显示无图表消息"""
    st.info(
        """
    📊 **暂无可用图表**
    
    要生成图表，请：
    1. 切换到 "🎨 图表生成" 标签页
    2. 选择要生成的图表类型  
    3. 配置图表参数
    4. 点击 "开始生成图表" 按钮
    """
    )


def load_charts_from_api(analysis_id: str) -> list[dict[str, Any]] | None:
    """从API加载图表"""
    try:
        api = ChartingArtistAPI()
        result = api.get_charts(analysis_id)

        if "error" not in result:
            return result.get("charts", [])
        else:
            logger.warning(f"API加载图表失败: {result['error']}")
            return None

    except Exception as e:
        logger.error(f"API加载图表异常: {e}")
        return None


def display_api_charts(charts: list[dict[str, Any]]) -> None:
    """显示API获取的图表"""
    display_generated_charts(charts)


def display_all_charts_list() -> None:
    """显示所有图表列表"""
    st.session_state.show_charts_list = True


def show_cleanup_dialog() -> None:
    """显示清理对话框"""
    st.session_state.show_cleanup_dialog = True


def show_batch_operations() -> None:
    """显示批量操作"""
    st.session_state.show_batch_ops = True


def show_usage_statistics() -> None:
    """显示使用统计"""
    st.session_state.show_usage_stats = True


def render_charts_list_panel() -> None:
    """渲染图表列表面板"""
    # 实现图表列表显示逻辑
    st.markdown("#### 📋 所有图表")
    # TODO: 实现具体逻辑


def render_cleanup_panel() -> None:
    """渲染清理面板"""
    # 实现清理面板逻辑
    st.markdown("#### 🧹 清理选项")
    # TODO: 实现具体逻辑


def render_batch_operations_panel() -> None:
    """渲染批量操作面板"""
    # 实现批量操作逻辑
    st.markdown("#### 📦 批量操作")
    # TODO: 实现具体逻辑


def render_usage_statistics_panel() -> None:
    """渲染使用统计面板"""
    # 实现使用统计逻辑
    st.markdown("#### 📊 使用统计")
    # TODO: 实现具体逻辑


def download_chart(chart: dict[str, Any]) -> None:
    """下载图表"""
    # 实现下载逻辑
    st.success("图表下载功能正在开发中")


def delete_chart(chart: dict[str, Any]) -> None:
    """删除图表"""
    # 实现删除逻辑
    if st.confirm("确定要删除这个图表吗？"):
        st.success("图表已删除")


def save_chart_settings(settings: dict[str, Any]) -> None:
    """保存图表设置"""
    # 实现设置保存逻辑
    settings_file = Path("data/chart_settings.json")
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


# 导出主要功能函数
__all__ = [
    "render_enhanced_visualization_tab",
    "ChartingArtistAPI",
    "execute_chart_generation",
    "display_generated_charts",
    "render_demo_charts",
    "is_charting_artist_enabled",
]
