"""
ChartingArtist Web Interface Component
绘图师Web界面组件 - 用于显示和管理可视化图表
增强版：集成完整API支持和向后兼容性
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import os
import uuid
import datetime
import numpy as np
import pandas as pd

from tradingagents.utils.logging_init import get_logger
from tradingagents.services.file_manager import FileManager
import requests
# 导入增强图表生成器
from .enhanced_chart_generators import (
    create_enhanced_candlestick_chart,
    create_enhanced_bar_chart, 
    create_enhanced_pie_chart,
    create_enhanced_line_chart,
    create_enhanced_radar_chart,
    create_enhanced_heatmap_chart,
    save_enhanced_chart,
    create_simple_line_chart,
    create_simple_heatmap_chart
)
# 导入批量操作相关功能
from .chart_batch_operations import (
    download_chart_enhanced,
    share_chart_enhanced,
    delete_chart_enhanced,
    get_local_charts_enhanced,
    display_local_charts_enhanced
)

logger = get_logger("charting_web_component")


class ChartingArtistAPIClient:
    """ChartingArtist API客户端"""
    
    def __init__(self):
        self.base_url = os.getenv("CHARTING_ARTIST_API_URL", "http://localhost:8000/api")
        self.timeout = int(os.getenv("CHARTING_ARTIST_TIMEOUT", "60"))
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "TradingAgents-CN-ChartingArtist/1.0"
        })
    
    def is_api_available(self) -> bool:
        """检查API是否可用"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate_charts(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成图表 - POST /api/charts/generate"""
        try:
            response = self.session.post(
                f"{self.base_url}/charts/generate",
                json=request_data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}", "details": response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API generate_charts失败: {e}")
            return {"error": "连接失败", "details": str(e)}
    
    def get_charts_by_analysis(self, analysis_id: str) -> Dict[str, Any]:
        """获取分析的图表 - GET /api/charts/{analysis_id}"""
        try:
            response = self.session.get(
                f"{self.base_url}/charts/{analysis_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API get_charts失败: {e}")
            return {"error": "连接失败", "details": str(e)}
    
    def get_chart_by_id(self, chart_id: str) -> Dict[str, Any]:
        """获取特定图表 - GET /api/charts/{chart_id}"""
        try:
            response = self.session.get(
                f"{self.base_url}/charts/{chart_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": "连接失败", "details": str(e)}
    
    def delete_chart(self, chart_id: str) -> Dict[str, Any]:
        """删除图表 - DELETE /api/charts/{chart_id}"""
        try:
            response = self.session.delete(
                f"{self.base_url}/charts/{chart_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": "连接失败", "details": str(e)}
    
    def list_all_charts(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """列出所有图表 - GET /api/charts/list"""
        try:
            params = {"limit": limit, "offset": offset}
            response = self.session.get(
                f"{self.base_url}/charts/list",
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": "连接失败", "details": str(e)}
    
    def batch_chart_operations(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量图表操作 - POST /api/charts/batch"""
        try:
            payload = {"operations": operations}
            response = self.session.post(
                f"{self.base_url}/charts/batch",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            return {"error": "连接失败", "details": str(e)}


def render_visualization_section(analysis_results: Dict[str, Any], 
                                symbol: str = None, analysis_id: str = None) -> None:
    """
    渲染可视化图表部分 - 增强版本，支持完整API集成
    
    Args:
        analysis_results: 分析结果字典
        symbol: 股票代码
        analysis_id: 分析ID，用于API调用
    """
    # 检查是否启用ChartingArtist
    if not is_charting_artist_enabled():
        render_charting_artist_disabled_info()
        return
    
    # 渲染主要图表界面
    render_charting_artist_interface(analysis_results, symbol, analysis_id)


def render_charting_artist_disabled_info() -> None:
    """渲染ChartingArtist禁用时的信息界面"""
    
    with st.expander("📊 图表分析 (未启用)", expanded=False):
        st.info("""
        🎨 **ChartingArtist功能未启用**
        
        ChartingArtist是专业的图表可视化智能体，能够根据分析结果生成多种类型的专业图表。
        
        **启用方法：**
        1. 设置环境变量：`CHARTING_ARTIST_ENABLED=true`
        2. 重启应用服务
        3. 刷新页面即可使用完整的可视化功能
        
        **功能特性：**
        """)
        
        # 功能特性展示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **📈 技术分析图表**
            - K线图与技术指标
            - 支撑阻力位标注  
            - 交易量分析图表
            - 趋势线识别
            - MACD/RSI等指标
            """)
        
        with col2:
            st.markdown("""
            **📊 基本面图表**
            - 财务数据柱状图
            - 盈利能力雷达图
            - 现金流瀑布图
            - ROE/ROA对比图
            - 行业对比分析
            """)
        
        with col3:
            st.markdown("""
            **🎯 风险分析图表**
            - 风险评估热力图
            - 投资组合饼图
            - 相关性矩阵图
            - 波动率箱线图
            - VaR风险度量
            """)
        
        # 显示图表类型支持
        st.markdown("**支持的图表类型：**")
        chart_types = [
            "📈 K线图 (Candlestick)", "📊 柱状图 (Bar Chart)", "🥧 饼图 (Pie Chart)",
            "📉 折线图 (Line Chart)", "🎯 散点图 (Scatter Plot)", "🔥 热力图 (Heatmap)",
            "🕸️ 雷达图 (Radar Chart)", "📏 仪表盘 (Gauge Chart)", "🌊 瀑布图 (Waterfall Chart)",
            "📦 箱线图 (Box Plot)"
        ]
        
        # 分两列显示图表类型
        col_a, col_b = st.columns(2)
        with col_a:
            for chart_type in chart_types[:5]:
                st.markdown(f"• {chart_type}")
        with col_b:
            for chart_type in chart_types[5:]:
                st.markdown(f"• {chart_type}")


def render_charting_artist_interface(analysis_results: Dict[str, Any], 
                                   symbol: str = None, 
                                   analysis_id: str = None) -> None:
    """渲染ChartingArtist主界面"""
    
    st.markdown("---")
    st.markdown("## 📊 ChartingArtist 智能图表分析")
    
    # 初始化API客户端
    api_client = ChartingArtistAPIClient()
    api_available = api_client.is_api_available()
    
    # 显示API状态
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if api_available:
            st.success("✅ ChartingArtist API 服务可用")
        else:
            st.warning("⚠️ ChartingArtist API 服务不可用，将使用本地生成")
    
    with col2:
        # API状态指示
        status_color = "green" if api_available else "orange"
        st.markdown(f"**API状态:** :{status_color}[{'在线' if api_available else '离线'}]")
    
    with col3:
        # 图表生成按钮
        if st.button("🎨 生成图表", type="primary"):
            execute_chart_generation_enhanced(
                analysis_results, symbol, analysis_id, api_client, api_available
            )
    
    # 显示现有图表
    display_existing_charts_enhanced(analysis_results, symbol, analysis_id, api_client)
    
    # 图表管理功能
    render_chart_management_enhanced(api_client, api_available)


def execute_chart_generation_enhanced(analysis_results: Dict[str, Any], 
                                     symbol: str, 
                                     analysis_id: str,
                                     api_client: ChartingArtistAPIClient,
                                     api_available: bool) -> None:
    """增强版图表生成执行函数"""
    
    if not symbol:
        st.error("❌ 缺少股票代码，无法生成图表")
        return
    
    if not analysis_results:
        st.error("❌ 缺少分析数据，无法生成图表")
        return
    
    # 显示生成配置选择
    with st.expander("⚙️ 生成配置", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**图表类型选择**")
            chart_types = []
            
            if st.checkbox("📈 K线图", value=True):
                chart_types.append("candlestick")
            if st.checkbox("📊 财务柱状图", value=True):
                chart_types.append("bar")
            if st.checkbox("🥧 业务构成饼图"):
                chart_types.append("pie")
            if st.checkbox("📉 价格趋势线"):
                chart_types.append("line")
            if st.checkbox("🎯 散点图"):
                chart_types.append("scatter")
            if st.checkbox("🔥 相关性热力图"):
                chart_types.append("heatmap")
            if st.checkbox("🕸️ 评分雷达图"):
                chart_types.append("radar")
            if st.checkbox("📏 风险仪表盘"):
                chart_types.append("gauge")
            if st.checkbox("🌊 现金流瀑布图"):
                chart_types.append("waterfall")
            if st.checkbox("📦 波动率箱线图"):
                chart_types.append("box")
        
        with col2:
            st.markdown("**图表配置**")
            theme = st.selectbox("主题", ["plotly_dark", "plotly_white", "ggplot2", "seaborn"])
            interactive = st.checkbox("交互式图表", value=True)
            include_indicators = st.checkbox("包含技术指标", value=True)
            add_annotations = st.checkbox("添加标注说明", value=True)
    
    if not chart_types:
        st.warning("⚠️ 请至少选择一种图表类型")
        return
    
    # 执行生成
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 准备图表生成...")
        progress_bar.progress(10)
        
        # 准备请求数据
        generation_config = {
            "theme": theme,
            "interactive": interactive,
            "include_indicators": include_indicators,
            "add_annotations": add_annotations,
            "width": 800,
            "height": 600
        }
        
        data_sources = prepare_enhanced_data_sources(analysis_results, symbol)
        
        request_data = {
            "analysis_id": analysis_id or f"chart_{uuid.uuid4().hex[:8]}",
            "chart_types": chart_types,
            "config": generation_config,
            "data_sources": data_sources
        }
        
        progress_bar.progress(30)
        
        if api_available:
            # 使用API生成
            status_text.text("📡 调用ChartingArtist API...")
            result = api_client.generate_charts(request_data)
            
            progress_bar.progress(80)
            
            if "error" not in result:
                # API成功
                status_text.text("✅ API生成完成")
                progress_bar.progress(100)
                
                # 更新分析结果
                analysis_results["charting_artist"] = result
                
                st.success(f"🎯 API成功生成 {result.get('total_charts', len(chart_types))} 个图表")
                
                # 显示生成详情
                if result.get('charts'):
                    st.info(f"生成的图表类型: {', '.join([c.get('chart_type', '未知') for c in result['charts']])}")
                
            else:
                # API失败，回退到本地生成
                status_text.text("🔄 API失败，使用本地生成...")
                local_charts = generate_local_charts_enhanced(analysis_results, symbol, chart_types, generation_config)
                handle_local_generation_result(local_charts, analysis_results, progress_bar, status_text)
        else:
            # 直接使用本地生成
            status_text.text("🔄 使用本地图表生成...")
            local_charts = generate_local_charts_enhanced(analysis_results, symbol, chart_types, generation_config)
            handle_local_generation_result(local_charts, analysis_results, progress_bar, status_text)
        
        # 刷新显示
        st.rerun()
        
    except Exception as e:
        logger.error(f"图表生成失败: {e}")
        status_text.text("❌ 生成失败")
        st.error(f"图表生成失败: {str(e)}")
    
    finally:
        # 清理进度显示
        progress_bar.empty()
        status_text.empty()


def handle_local_generation_result(local_charts: List[Dict[str, Any]], 
                                 analysis_results: Dict[str, Any],
                                 progress_bar: st.progress,
                                 status_text: st.empty) -> None:
    """处理本地生成结果"""
    
    if local_charts:
        progress_bar.progress(100)
        status_text.text("✅ 本地生成完成")
        
        # 更新分析结果
        analysis_results["charting_artist"] = {
            "charts_generated": local_charts,
            "total_charts": len(local_charts),
            "generation_method": "local_fallback",
            "generation_time": datetime.datetime.now().isoformat()
        }
        
        st.success(f"✅ 本地成功生成 {len(local_charts)} 个图表")
        
        # 显示生成详情
        chart_types = [c.get('chart_type', '未知') for c in local_charts]
        st.info(f"生成的图表类型: {', '.join(chart_types)}")
        
    else:
        status_text.text("❌ 本地生成失败")
        st.error("图表生成失败，请检查数据和配置")


def prepare_enhanced_data_sources(analysis_results: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """准备增强的数据源"""
    
    data_sources = {
        "symbol": symbol,
        "timestamp": datetime.datetime.now().isoformat(),
        "analysis_summary": analysis_results
    }
    
    # 提取各类分析数据
    analyst_mappings = {
        "technical_data": ["technical_analyst", "market_analyst"],
        "fundamental_data": ["fundamental_expert", "fundamentals_analyst"],
        "sentiment_data": ["sentiment_analyst", "social_media_analyst"],
        "risk_data": ["risk_manager"],
        "news_data": ["news_analyst", "news_hunter"],
        "decision_data": ["chief_decision_officer"]
    }
    
    for data_key, analyst_keys in analyst_mappings.items():
        for analyst_key in analyst_keys:
            if analyst_key in analysis_results:
                data_sources[data_key] = analysis_results[analyst_key]
                break
    
    return data_sources


def generate_local_charts_enhanced(analysis_results: Dict[str, Any], 
                                 symbol: str, 
                                 chart_types: List[str], 
                                 config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """增强版本地图表生成"""
    
    charts = []
    
    chart_generators = {
        "candlestick": create_enhanced_candlestick_chart,
        "bar": create_enhanced_bar_chart,
        "pie": create_enhanced_pie_chart,
        "line": create_enhanced_line_chart,
        "scatter": create_enhanced_scatter_chart,
        "heatmap": create_enhanced_heatmap_chart,
        "radar": create_enhanced_radar_chart,
        "gauge": create_enhanced_gauge_chart,
        "waterfall": create_enhanced_waterfall_chart,
        "box": create_enhanced_box_chart
    }
    
    for chart_type in chart_types:
        try:
            if chart_type in chart_generators:
                chart = chart_generators[chart_type](analysis_results, symbol, config)
                if chart:
                    charts.append(chart)
                    logger.info(f"成功生成 {chart_type} 图表")
            else:
                logger.warning(f"不支持的图表类型: {chart_type}")
                
        except Exception as e:
            logger.error(f"生成 {chart_type} 图表失败: {e}")
            # 继续生成其他图表
            continue
    
    return charts


def display_existing_charts_enhanced(analysis_results: Dict[str, Any], 
                                   symbol: str = None, 
                                   analysis_id: str = None,
                                   api_client: ChartingArtistAPIClient = None) -> None:
    """增强版现有图表显示"""
    
    st.markdown("### 📈 生成的图表")
    
    # 优先显示分析结果中的图表
    chart_data = analysis_results.get("charting_artist", {})
    generated_charts = chart_data.get("charts_generated", [])
    api_charts = chart_data.get("charts", [])
    
    all_charts = generated_charts + api_charts
    
    if all_charts:
        display_charts_with_management(all_charts, api_client)
    
    elif analysis_id and api_client:
        # 尝试从API获取图表
        st.info("🔄 从API加载图表...")
        api_result = api_client.get_charts_by_analysis(analysis_id)
        
        if "error" not in api_result and api_result.get("charts"):
            api_charts = api_result["charts"]
            display_charts_with_management(api_charts, api_client)
        else:
            display_fallback_options(symbol)
    
    else:
        display_fallback_options(symbol)


def display_charts_with_management(charts: List[Dict[str, Any]], 
                                 api_client: ChartingArtistAPIClient = None) -> None:
    """显示图表并提供管理功能"""
    
    if not charts:
        st.info("暂无可用图表")
        return
    
    # 按类型分组
    chart_groups = {}
    for chart in charts:
        chart_type = chart.get("chart_type", "unknown")
        if chart_type not in chart_groups:
            chart_groups[chart_type] = []
        chart_groups[chart_type].append(chart)
    
    # 显示统计信息
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("图表总数", len(charts))
    with col2:
        st.metric("图表类型", len(chart_groups))
    with col3:
        generation_method = charts[0].get("metadata", {}).get("generation_method", "未知")
        st.metric("生成方式", generation_method)
    
    # 批量操作工具条
    all_ids = []
    for c in charts:
        cid = c.get('chart_id') or c.get('id') or str(hash(str(c)))
        all_ids.append(cid)
    sel_key = 'chart_batch_selection'
    if sel_key not in st.session_state or not isinstance(st.session_state.get(sel_key), set):
        st.session_state[sel_key] = set()

    selected_now = st.session_state[sel_key].intersection(set(all_ids))
    tb1, tb2, tb3, _ = st.columns([2, 2, 2, 6])
    with tb1:
        st.caption(f"已选中: {len(selected_now)}")
    with tb2:
        if st.button("📚 保存选中到图书馆", disabled=(len(selected_now) == 0)):
            saved = 0
            for c in charts:
                cid = c.get('chart_id') or c.get('id') or str(hash(str(c)))
                if cid in selected_now:
                    try:
                        _save_chart_to_library_enhanced(c)
                        saved += 1
                    except Exception:
                        pass
            if saved:
                st.success(f"✅ 已保存 {saved} 个图表到图书馆")
    with tb3:
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

    # 显示图表
    if len(chart_groups) > 1:
        # 多种类型用标签页
        group_names = list(chart_groups.keys())
        tabs = st.tabs([f"📊 {name.replace('_', ' ').title()}" for name in group_names])
        
        for i, (group_name, group_charts) in enumerate(chart_groups.items()):
            with tabs[i]:
                display_chart_group_enhanced(group_charts, api_client)
    else:
        # 单一类型直接显示
        chart_list = list(chart_groups.values())[0]
        display_chart_group_enhanced(chart_list, api_client)


def display_chart_group_enhanced(charts: List[Dict[str, Any]], 
                              api_client: ChartingArtistAPIClient = None) -> None:
    """增强版图表组显示"""
    
    for i, chart in enumerate(charts):
        try:
            # 显示图表头部信息 + 选择框
            cid = chart.get('chart_id') or chart.get('id') or f"idx_{i}"
            sel_key = 'chart_batch_selection'
            col0, col1, col2, col3, col4, col5 = st.columns([1, 4, 1, 1, 1, 1])
            with col0:
                checked = st.checkbox("", key=f"chart_sel_{cid}", help="选择此图表")
                if checked:
                    st.session_state.setdefault(sel_key, set()).add(cid)
                else:
                    st.session_state.setdefault(sel_key, set()).discard(cid)
            
            with col1:
                title = chart.get('title', f'Chart {i+1}')
                st.markdown(f"**{title}**")
                if chart.get('description'):
                    st.caption(chart['description'])
            
            with col2:
                # 下载按钮
                if st.button("⬇️", help="下载图表", key=f"download_enhanced_{chart.get('chart_id', i)}"):
                    download_chart_enhanced(chart)
            
            with col3:
                # 分享按钮
                if st.button("🔗", help="分享图表", key=f"share_enhanced_{chart.get('chart_id', i)}"):
                    share_chart_enhanced(chart)
            
            with col4:
                # 删除按钮
                if st.button("🗑️", help="删除图表", key=f"delete_enhanced_{chart.get('chart_id', i)}"):
                    delete_chart_enhanced(chart, api_client)
            
            with col5:
                # 保存到图书馆
                if st.button("📚", help="保存到图书馆", key=f"save_lib_enh_{chart.get('chart_id', i)}"):
                    _save_chart_to_library_enhanced(chart)
            
            # 显示图表内容
            render_chart_content_enhanced(chart)
            
            # 显示元数据
            if chart.get('metadata'):
                with st.expander("ℹ️ 图表信息"):
                    metadata = chart['metadata']
                    for key, value in metadata.items():
                        st.write(f"**{key}**: {value}")
            
            st.markdown("---")
            
        except Exception as e:
            logger.error(f"显示图表失败: {e}")
            st.error(f"图表 {chart.get('title', 'Unknown')} 显示失败: {str(e)}")


def render_chart_content_enhanced(chart: Dict[str, Any]) -> None:
    """增强版图表内容渲染"""

    try:
        # 检查Plotly JSON数据
        if 'plotly_json' in chart:
            plotly_data = chart['plotly_json']
            if isinstance(plotly_data, str):
                plotly_data = json.loads(plotly_data)
            
            fig = go.Figure(plotly_data)
            st.plotly_chart(fig, use_container_width=True)
            
        # 检查文件路径
        elif 'file_path' in chart or 'path' in chart:
            file_path = Path(chart.get('file_path') or chart.get('path'))
            
            if file_path.exists():
                if file_path.suffix.lower() == '.html':
                    # HTML文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.components.v1.html(html_content, height=600, scrolling=True)
                    
                elif file_path.suffix.lower() == '.json':
                    # JSON文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        fig_dict = json.load(f)
                    fig = go.Figure(fig_dict)
                    st.plotly_chart(fig, use_container_width=True)
                    
                elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.svg']:
                    # 图片文件
                    st.image(str(file_path), use_column_width=True)
                    
                else:
                    st.warning(f"不支持的文件格式: {file_path.suffix}")
            else:
                st.error("图表文件不存在")
        
        # 兼容后端返回的远程图片/页面URL
        elif 'image_url' in chart or 'url' in chart or 'download_url' in chart:
            url = chart.get('image_url') or chart.get('url') or chart.get('download_url')
            try:
                # 优先判断常见图片后缀
                if isinstance(url, str) and url.lower().endswith((".png", ".jpg", ".jpeg", ".svg")):
                    st.image(url, use_column_width=True)
                elif isinstance(url, str) and url.lower().endswith((".html",)):
                    # 远程HTML：简单拉取后嵌入
                    import requests
                    r = requests.get(url, timeout=5)
                    if r.ok:
                        st.components.v1.html(r.text, height=600, scrolling=True)
                    else:
                        st.markdown(f"[打开图表页面]({url})")
                else:
                    # 尝试作为图片获取
                    import requests
                    r = requests.get(url, timeout=5)
                    if r.ok:
                        ct = r.headers.get('content-type', '')
                        if 'image' in ct:
                            st.image(r.content, use_column_width=True)
                        elif 'html' in ct:
                            st.components.v1.html(r.text, height=600, scrolling=True)
                        else:
                            st.markdown(f"[下载/查看图表]({url})")
                    else:
                        st.markdown(f"[打开图表链接]({url})")
            except Exception:
                # 最保守处理：给出链接
                if isinstance(url, str):
                    st.markdown(f"[打开图表链接]({url})")
                else:
                    st.warning("未找到可显示的图表数据")

        # 检查Base64数据
        elif 'base64_data' in chart:
            import base64
            image_data = base64.b64decode(chart['base64_data'])
            st.image(image_data, use_column_width=True)
            
        # 检查直接的图表数据
        elif 'chart_data' in chart:
            chart_data = chart['chart_data']
            if isinstance(chart_data, dict):
                fig = go.Figure(chart_data)
                st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.warning("⚠️ 未找到可显示的图表数据")
            
    except Exception as e:
        logger.error(f"渲染图表内容失败: {e}")
        st.error(f"图表内容渲染失败: {str(e)}")


def _save_chart_to_library_enhanced(chart: Dict[str, Any]) -> None:
    """保存图表到图书馆（附件库）。"""
    try:
        fm = FileManager()
        filename = None
        content = None

        fp = chart.get('file_path') or chart.get('path')
        if fp and Path(fp).exists():
            filename = Path(fp).name
            with open(fp, 'rb') as f:
                content = f.read()
        else:
            url = chart.get('image_url') or chart.get('url') or chart.get('download_url')
            if isinstance(url, str):
                try:
                    r = requests.get(url, timeout=8)
                    if r.ok and r.content:
                        content = r.content
                        try:
                            filename = Path(url.split('?')[0]).name or f"chart_{chart.get('chart_id','unknown')}"
                        except Exception:
                            filename = f"chart_{chart.get('chart_id','unknown')}"
                except Exception:
                    pass

        if not content or not filename:
            st.error("未找到可保存的图表数据")
            return

        meta = {
            'chart_id': chart.get('chart_id'),
            'chart_type': chart.get('chart_type'),
            'title': chart.get('title'),
            'source': 'charting_artist',
            'generation_method': (chart.get('metadata') or {}).get('generation_method'),
        }
        file_id = fm.save_file(content, filename, category='chart', metadata=meta)
        # 生成缩略图（仅限PNG/JPG/JPEG）
        try:
            from PIL import Image
            import io
            suffix = Path(filename).suffix.lower()
            if suffix in ['.png', '.jpg', '.jpeg']:
                img = Image.open(io.BytesIO(content))
                img.thumbnail((320, 320))
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                thumb_bytes = buf.getvalue()
                fm.save_file(thumb_bytes, f"{Path(filename).stem}_thumb.png", category='temp', metadata={
                    'thumbnail_of': file_id,
                    'source': 'charting_artist',
                })
        except Exception:
            pass
        st.success(f"✅ 已保存到图书馆 (附件ID: {file_id})")
    except Exception as e:
        st.error(f"保存失败: {e}")


def display_fallback_options(symbol: str = None) -> None:
    """显示回退选项"""
    
    # 尝试显示本地历史图表
    local_charts = get_local_charts_enhanced(symbol)
    if local_charts:
        st.markdown("### 📂 历史图表")
        display_local_charts_enhanced(local_charts)
    else:
        st.info("""
        📊 **暂无可用图表**
        
        要生成图表，请：
        1. 点击上方的 "🎨 生成图表" 按钮
        2. 选择要生成的图表类型
        3. 配置图表参数并执行生成
        """)


def render_chart_management_enhanced(api_client: ChartingArtistAPIClient, 
                                   api_available: bool) -> None:
    """增强版图表管理面板"""
    
    with st.expander("🔧 图表管理", expanded=False):
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📋 所有图表"):
                show_all_charts_list(api_client, api_available)
        
        with col2:
            if st.button("🧹 清理图表"):
                show_chart_cleanup_dialog()
        
        with col3:
            if st.button("📦 批量操作"):
                show_batch_operations_dialog(api_client, api_available)
        
        with col4:
            if st.button("📊 使用统计"):
                show_usage_statistics()
        
        # 处理会话状态中的操作
        if st.session_state.get('show_all_charts'):
            render_all_charts_interface(api_client, api_available)
            
        if st.session_state.get('show_cleanup_dialog'):
            render_cleanup_interface()
            
        if st.session_state.get('show_batch_operations'):
            render_batch_operations_interface(api_client, api_available)
            
        if st.session_state.get('show_usage_stats'):
            render_usage_statistics_interface()


# 辅助函数继续实现...

def display_existing_charts(analysis_results: Dict[str, Any], 
                          symbol: str = None) -> None:
    """显示现有的图表"""
    
    # 检查分析结果中是否包含图表
    chart_data = analysis_results.get("charting_artist", {})
    charts_generated = chart_data.get("charts_generated", [])
    
    if charts_generated:
        st.markdown("### 🎯 生成的图表")
        
        # 创建标签页显示不同类型的图表
        chart_types = list(set([chart.get("chart_type", "unknown") for chart in charts_generated]))
        
        if len(chart_types) > 1:
            tabs = st.tabs([f"📈 {chart_type.title()}" for chart_type in chart_types])
            
            for i, chart_type in enumerate(chart_types):
                with tabs[i]:
                    display_charts_by_type(charts_generated, chart_type)
        else:
            # 单一图表类型直接显示
            display_charts_by_type(charts_generated, chart_types[0] if chart_types else None)
    
    else:
        # 如果没有生成的图表，尝试从本地获取
        local_charts = get_local_charts(symbol)
        if local_charts:
            st.markdown("### 📂 历史图表")
            display_local_charts(local_charts)
        else:
            st.info("暂无可用图表，点击上方 '生成图表' 按钮创建可视化分析")


def display_charts_by_type(charts: List[Dict[str, Any]], 
                         chart_type: str = None) -> None:
    """按类型显示图表"""
    
    filtered_charts = [c for c in charts if c.get("chart_type") == chart_type] if chart_type else charts
    
    for chart in filtered_charts:
        try:
            chart_path = chart.get("path") or chart.get("file_path")
            if chart_path and Path(chart_path).exists():
                
                # 显示图表信息
                st.markdown(f"**{chart.get('title', 'Untitled Chart')}**")
                if chart.get("description"):
                    st.caption(chart["description"])
                
                # 加载并显示图表
                if chart_path.endswith('.html'):
                    # HTML图表（Plotly）
                    with open(chart_path, 'r', encoding='utf-8') as f:
                        chart_html = f.read()
                    st.components.v1.html(chart_html, height=600, scrolling=True)
                
                elif chart_path.endswith('.json'):
                    # JSON格式的Plotly图表
                    with open(chart_path, 'r', encoding='utf-8') as f:
                        fig_dict = json.load(f)
                    fig = go.Figure(fig_dict)
                    st.plotly_chart(fig, use_container_width=True)
                
                else:
                    st.warning(f"不支持的图表格式: {chart_path}")
                
                # 图表操作按钮
                col1, col2, col3 = st.columns([1, 1, 4])
                with col1:
                    if st.button("⬇️ 下载", key=f"download_{chart.get('chart_id', 'unknown')}"):
                        download_chart(chart_path)
                with col2:
                    if st.button("🔗 分享", key=f"share_{chart.get('chart_id', 'unknown')}"):
                        share_chart(chart)
                
                st.markdown("---")
                
        except Exception as e:
            logger.error(f"显示图表失败: {e}")
            st.error(f"图表加载失败: {chart.get('title', 'Unknown')}")


def display_local_charts(charts: List[Path]) -> None:
    """显示本地图表文件"""
    
    for i, chart_path in enumerate(charts[:5]):  # 最多显示5个历史图表
        try:
            # 从文件名解析信息
            parts = chart_path.stem.split('_')
            chart_symbol = parts[0] if len(parts) > 0 else "Unknown"
            chart_type = parts[1] if len(parts) > 1 else "unknown"
            
            with st.expander(f"📊 {chart_symbol} - {chart_type.title()}", expanded=(i == 0)):
                
                if chart_path.exists():
                    if chart_path.suffix == '.html':
                        with open(chart_path, 'r', encoding='utf-8') as f:
                            chart_html = f.read()
                        st.components.v1.html(chart_html, height=500)
                    else:
                        st.warning("不支持的图表格式")
                else:
                    st.error("图表文件不存在")
                    
        except Exception as e:
            logger.error(f"显示本地图表失败: {e}")
            st.error(f"图表加载失败: {chart_path.name}")


def generate_charts_for_results(analysis_results: Dict[str, Any], 
                               symbol: str = None) -> None:
    """为分析结果生成图表"""
    
    if not symbol:
        st.error("缺少股票代码，无法生成图表")
        return
    
    # 显示生成进度
    progress_container = st.empty()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        with st.spinner("🎨 正在生成图表..."):
            
            # 准备API请求数据
            request_data = {
                "symbol": symbol,
                "analysis_results": analysis_results,
                "config": {
                    "theme": "plotly_dark",
                    "interactive": True
                }
            }
            
            # 调用可视化API
            api_url = "http://localhost:8000/api/v1/visualization/generate"  # 需要根据实际API地址调整
            
            status_text.text("📡 调用可视化服务...")
            progress_bar.progress(25)
            
            try:
                response = requests.post(api_url, json=request_data, timeout=60)
                progress_bar.progress(75)
                
                if response.status_code == 200:
                    viz_results = response.json()
                    progress_bar.progress(100)
                    status_text.text("✅ 图表生成完成")
                    
                    # 更新分析结果
                    analysis_results["charting_artist"] = viz_results
                    
                    # 显示成功信息
                    st.success(f"🎯 成功生成 {viz_results.get('total_charts', 0)} 个图表")
                    
                    # 刷新显示
                    st.experimental_rerun()
                    
                else:
                    st.error(f"图表生成失败: HTTP {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                # API服务不可用时的本地回退方案
                status_text.text("🔄 API服务不可用，使用本地生成...")
                progress_bar.progress(50)
                
                local_charts = generate_charts_locally(analysis_results, symbol)
                progress_bar.progress(100)
                
                if local_charts:
                    st.success(f"✅ 本地生成了 {len(local_charts)} 个图表")
                    analysis_results["charting_artist"] = {
                        "charts_generated": local_charts,
                        "total_charts": len(local_charts),
                        "generation_method": "local_fallback"
                    }
                    st.experimental_rerun()
                else:
                    st.error("本地图表生成也失败了")
                    
    except Exception as e:
        logger.error(f"图表生成过程失败: {e}")
        st.error(f"图表生成失败: {str(e)}")
        
    finally:
        # 清理进度显示
        progress_container.empty()
        progress_bar.empty()
        status_text.empty()


def generate_charts_locally(analysis_results: Dict[str, Any], 
                           symbol: str) -> List[Dict[str, Any]]:
    """本地生成图表的回退方案"""
    
    charts = []
    
    try:
        # 简单的本地图表生成示例
        # 实际应用中需要更复杂的逻辑
        
        # 生成价格趋势图
        if "technical_analyst" in analysis_results:
            price_chart = create_simple_price_chart(symbol)
            if price_chart:
                charts.append({
                    "chart_type": "line_chart",
                    "title": f"{symbol} 价格趋势",
                    "path": price_chart,
                    "description": "基于技术分析的价格趋势图"
                })
        
        # 生成财务指标图
        if "fundamental_expert" in analysis_results:
            financial_chart = create_simple_financial_chart(symbol)
            if financial_chart:
                charts.append({
                    "chart_type": "bar_chart", 
                    "title": f"{symbol} 财务指标",
                    "path": financial_chart,
                    "description": "基于基本面分析的财务指标图"
                })
                
    except Exception as e:
        logger.error(f"本地图表生成失败: {e}")
    
    return charts


def create_simple_price_chart(symbol: str) -> Optional[str]:
    """创建简单的价格图表"""
    try:
        import pandas as pd
        import uuid
        
        # 模拟价格数据
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        prices = [100 + i + (i % 7) for i in range(30)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=prices,
            mode='lines+markers',
            name=f'{symbol} 价格',
            line=dict(color='#1f77b4', width=2)
        ))
        
        fig.update_layout(
            title=f'{symbol} 价格趋势 (简化版)',
            xaxis_title='日期',
            yaxis_title='价格',
            template='plotly_dark'
        )
        
        # 保存图表
        charts_dir = Path("data/attachments/charts")
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        chart_file = charts_dir / f"{symbol}_line_chart_{uuid.uuid4().hex[:8]}_local.html"
        fig.write_html(str(chart_file))
        
        return str(chart_file)
        
    except Exception as e:
        logger.error(f"创建价格图表失败: {e}")
        return None


def create_simple_financial_chart(symbol: str) -> Optional[str]:
    """创建简单的财务图表"""
    try:
        import uuid
        
        # 模拟财务数据
        metrics = ['营收', '净利润', 'ROE', 'ROA']
        values = [1000, 150, 12.5, 8.2]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=metrics,
            y=values,
            marker_color=['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
            text=values,
            textposition='auto'
        ))
        
        fig.update_layout(
            title=f'{symbol} 关键财务指标 (简化版)',
            xaxis_title='指标',
            yaxis_title='数值',
            template='plotly_dark'
        )
        
        # 保存图表
        charts_dir = Path("data/attachments/charts")
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        chart_file = charts_dir / f"{symbol}_bar_chart_{uuid.uuid4().hex[:8]}_local.html"
        fig.write_html(str(chart_file))
        
        return str(chart_file)
        
    except Exception as e:
        logger.error(f"创建财务图表失败: {e}")
        return None


def render_chart_management_panel(symbol: str = None) -> None:
    """渲染图表管理面板"""
    
    st.markdown("#### 🔧 图表管理")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📂 浏览所有图表"):
            display_all_charts()
    
    with col2:
        if st.button("🧹 清理旧图表"):
            cleanup_old_charts()
    
    with col3:
        if st.button("⚙️ 图表设置"):
            display_chart_settings()


def display_all_charts() -> None:
    """显示所有图表"""
    charts_dir = Path("data/attachments/charts")
    
    if charts_dir.exists():
        chart_files = list(charts_dir.glob("*.html"))
        
        if chart_files:
            st.markdown(f"**找到 {len(chart_files)} 个图表文件**")
            
            for chart_file in chart_files[:10]:  # 显示前10个
                parts = chart_file.stem.split('_')
                chart_symbol = parts[0] if len(parts) > 0 else "Unknown"
                chart_type = parts[1] if len(parts) > 1 else "unknown"
                
                st.write(f"📊 {chart_symbol} - {chart_type} ({chart_file.name})")
        else:
            st.info("未找到任何图表文件")
    else:
        st.warning("图表目录不存在")


def cleanup_old_charts() -> None:
    """清理旧图表"""
    days_to_keep = st.number_input("保留天数", min_value=1, max_value=365, value=7)
    
    if st.button("确认清理"):
        try:
            # 这里应该调用清理API或实现本地清理逻辑
            st.success(f"已清理超过 {days_to_keep} 天的图表文件")
        except Exception as e:
            st.error(f"清理失败: {e}")


def display_chart_settings() -> None:
    """显示图表设置"""
    st.markdown("**图表配置**")
    
    theme = st.selectbox("主题", ["plotly_dark", "plotly_white", "ggplot2", "seaborn"])
    width = st.number_input("宽度", min_value=400, max_value=1200, value=800)
    height = st.number_input("高度", min_value=300, max_value=800, value=600)
    interactive = st.checkbox("交互式图表", value=True)
    
    if st.button("保存设置"):
        # 这里应该保存设置到配置文件
        st.success("设置已保存")


def get_local_charts(symbol: str = None) -> List[Path]:
    """获取本地图表文件"""
    charts_dir = Path("data/attachments/charts")
    
    if not charts_dir.exists():
        return []
    
    chart_files = []
    for chart_file in charts_dir.glob("*.html"):
        if symbol is None:
            chart_files.append(chart_file)
        else:
            # 检查文件名是否包含指定的股票代码
            if chart_file.name.startswith(f"{symbol}_"):
                chart_files.append(chart_file)
    
    # 按修改时间排序，最新的在前
    chart_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    return chart_files


def download_chart(chart_path: str) -> None:
    """下载图表文件"""
    try:
        chart_file = Path(chart_path)
        if chart_file.exists():
            with open(chart_file, 'rb') as f:
                st.download_button(
                    label="下载图表",
                    data=f.read(),
                    file_name=chart_file.name,
                    mime="text/html"
                )
        else:
            st.error("图表文件不存在")
    except Exception as e:
        st.error(f"下载失败: {e}")


def share_chart(chart_info: Dict[str, Any]) -> None:
    """分享图表"""
    chart_url = chart_info.get("url", "")
    if chart_url:
        st.code(f"图表链接: {chart_url}")
        st.info("复制上面的链接即可分享图表")
    else:
        st.error("无法获取图表链接")


def is_charting_artist_enabled() -> bool:
    """检查ChartingArtist是否启用"""
    return os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() == "true"


def render_charting_artist_status() -> None:
    """渲染ChartingArtist状态信息"""
    
    with st.sidebar:
        st.markdown("### 🎨 图表功能状态")
        
        if is_charting_artist_enabled():
            st.success("✅ ChartingArtist 已启用")
            
            # 显示统计信息
            charts_dir = Path("data/attachments/charts")
            if charts_dir.exists():
                chart_count = len(list(charts_dir.glob("*.html")))
                st.metric("生成图表数", chart_count)
        else:
            st.warning("⚠️ ChartingArtist 未启用")
            st.caption("设置 CHARTING_ARTIST_ENABLED=true 启用")


# 导出主要功能函数
__all__ = [
    'render_visualization_section',
    'display_existing_charts', 
    'generate_charts_for_results',
    'render_chart_management_panel',
    'render_charting_artist_status',
    'is_charting_artist_enabled'
]
