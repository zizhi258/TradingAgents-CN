"""
Market Results Display Components
市场分析结果高级可视化组件 - 图表、热力图、仪表盘等
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from typing import Dict, List, Any, Optional, Tuple
from io import BytesIO
from datetime import datetime
import json

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('market_results_display')


class AdvancedStockRankingsDisplay:
    """高级股票排名展示组件"""
    
    def __init__(self):
        self.default_columns = [
            '排名', '股票代码', '股票名称', '综合评分', '技术评分', 
            '基本面评分', '当前价格', '涨跌幅', '建议', '目标价'
        ]
    
    def render(self, rankings_data: List[Dict], key_suffix: str = "") -> None:
        """
        渲染高级股票排名展示
        
        Args:
            rankings_data: 股票排名数据
            key_suffix: 组件key后缀
        """
        
        if not rankings_data:
            st.info("📊 暂无股票排名数据")
            return
        
        # 控制面板
        self._render_control_panel(key_suffix)
        
        # 主要显示区域
        display_tabs = st.tabs(["📋 排名表格", "📊 评分分布", "🎯 推荐分析", "📈 价格分析"])
        
        with display_tabs[0]:
            self._render_rankings_table(rankings_data, key_suffix)
        
        with display_tabs[1]:
            self._render_score_distribution(rankings_data, key_suffix)
        
        with display_tabs[2]:
            self._render_recommendation_analysis(rankings_data, key_suffix)
        
        with display_tabs[3]:
            self._render_price_analysis(rankings_data, key_suffix)
    
    def _render_control_panel(self, key_suffix: str):
        """渲染控制面板"""
        
        st.markdown("### 🎛️ 显示控制")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            sort_by = st.selectbox(
                "排序字段",
                options=["综合评分", "技术评分", "基本面评分", "涨跌幅", "市值"],
                key=f"ranking_sort_{key_suffix}"
            )
        
        with col2:
            order = st.selectbox(
                "排序方向",
                options=["降序", "升序"],
                key=f"ranking_order_{key_suffix}"
            )
        
        with col3:
            recommendation_filter = st.multiselect(
                "投资建议筛选",
                options=["买入", "持有", "关注", "卖出"],
                default=["买入", "持有", "关注"],
                key=f"rec_filter_{key_suffix}"
            )
        
        with col4:
            display_count = st.number_input(
                "显示数量",
                min_value=10,
                max_value=200,
                value=50,
                key=f"display_count_{key_suffix}"
            )
        
        # 保存控制参数到session state
        st.session_state[f'ranking_controls_{key_suffix}'] = {
            'sort_by': sort_by,
            'order': order,
            'recommendation_filter': recommendation_filter,
            'display_count': display_count
        }
    
    def _render_rankings_table(self, rankings_data: List[Dict], key_suffix: str):
        """渲染排名表格"""

        st.markdown("### 📋 股票排名表")

        # 获取控制参数
        controls = st.session_state.get(f'ranking_controls_{key_suffix}', {})

        # 数据预处理和筛选
        df = self._prepare_rankings_dataframe(rankings_data, controls)

        if df.empty:
            st.warning("没有符合筛选条件的数据")
            return

        # 分页设置
        col_p1, col_p2, _ = st.columns([1, 1, 4])
        with col_p1:
            page_size = st.slider("每页数量", 10, 200, 50, 10, key=f"rank_page_size_{key_suffix}")
        total_rows = len(df)
        total_pages = max(1, (total_rows + page_size - 1) // page_size)
        with col_p2:
            page = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1, key=f"rank_page_{key_suffix}")
        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end].reset_index(drop=True)

        # 配置表格列显示
        column_config = {
            "排名": st.column_config.NumberColumn("排名", width="small"),
            "股票代码": st.column_config.TextColumn("代码", width="small"),
            "综合评分": st.column_config.ProgressColumn("综合评分", min_value=0, max_value=100),
            "技术评分": st.column_config.ProgressColumn("技术评分", min_value=0, max_value=100),
            "基本面评分": st.column_config.ProgressColumn("基本面评分", min_value=0, max_value=100),
            "涨跌幅": st.column_config.NumberColumn("涨跌幅(%)", format="%.2f"),
            "当前价格": st.column_config.NumberColumn("价格(¥)", format="%.2f"),
            "目标价": st.column_config.NumberColumn("目标价(¥)", format="%.2f"),
            "建议": self._get_recommendation_column_config()
        }
        
        # 显示表格
        selected_rows = st.dataframe(
            page_df,
            use_container_width=True,
            height=500,
            column_config=column_config,
            on_select="rerun",
            selection_mode="multi-row"
        )

        # 导出与操作区
        st.markdown("#### 📤 导出与操作")
        sel_idx = list(getattr(getattr(selected_rows, 'selection', None), 'rows', []) or [])
        selected_subset = page_df.iloc[sel_idx] if sel_idx else page_df.iloc[0:0]

        # 构造导出数据
        def df_to_csv_bytes(d: pd.DataFrame) -> bytes:
            return d.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')

        def df_to_excel_bytes(d: pd.DataFrame) -> Optional[bytes]:
            try:
                import pandas as _pd
                import io as _io
                bio = _io.BytesIO()
                with _pd.ExcelWriter(bio, engine='openpyxl') as writer:
                    d.to_excel(writer, index=False, sheet_name='rankings')
                bio.seek(0)
                return bio.read()
            except Exception:
                return None

        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
        with col_e1:
            st.download_button("下载选中CSV", data=df_to_csv_bytes(selected_subset) if not selected_subset.empty else b"", file_name="selected_rankings.csv", mime="text/csv", disabled=selected_subset.empty)
        with col_e2:
            xbytes = df_to_excel_bytes(selected_subset) if not selected_subset.empty else None
            st.download_button("下载选中Excel", data=xbytes or b"", file_name="selected_rankings.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", disabled=(xbytes is None))
        with col_e3:
            st.download_button("下载本页CSV", data=df_to_csv_bytes(page_df), file_name="page_rankings.csv", mime="text/csv")
        with col_e4:
            st.download_button("下载全部CSV", data=df_to_csv_bytes(df), file_name="all_rankings.csv", mime="text/csv")

        # 快速图表（选中股票收盘价折线图）
        if sel_idx:
            st.markdown("#### 📈 选中股票快速图表（近90日）")
            try:
                from web.utils.market_api_client import MarketAnalysisAPIClient
                client = MarketAnalysisAPIClient()
                import plotly.express as _px
                import pandas as _pd
                import datetime as _dt
                now = _dt.date.today()
                start_date = (now - _dt.timedelta(days=90)).isoformat()
                frames = []
                for _, row in selected_subset.iterrows():
                    code = str(row.get('股票代码') or row.get('symbol') or '')
                    if not code:
                        continue
                    # 兼容A股6位代码：缺少交易所时也可尝试
                    resp = client.get_daily(code=code, start_date=start_date, end_date=now.isoformat(), adj='qfq')
                    recs = resp.get('data', [])
                    if recs:
                        df_line = _pd.DataFrame(recs)
                        # 兼容trade_date/日期字段
                        date_col = 'trade_date' if 'trade_date' in df_line.columns else 'date'
                        price_col = 'close' if 'close' in df_line.columns else df_line.columns[-1]
                        df_line[date_col] = _pd.to_datetime(df_line[date_col])
                        df_line['symbol'] = code
                        df_line.rename(columns={price_col: 'close'}, inplace=True)
                        frames.append(df_line[[date_col, 'close', 'symbol']].rename(columns={date_col: 'date'}))
                if frames:
                    all_line = _pd.concat(frames, ignore_index=True)
                    fig = _px.line(all_line, x='date', y='close', color='symbol')
                    fig.update_layout(height=400, legend_title_text='代码')
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.info(f"无法生成快速图表: {e}")

        # 显示选中行的详细信息（当前页）
        if sel_idx:
            self._show_selected_stocks_details(page_df, sel_idx, key_suffix)
    
    def _render_score_distribution(self, rankings_data: List[Dict], key_suffix: str):
        """渲染评分分布图"""
        
        st.markdown("### 📊 评分分布分析")
        
        df = pd.DataFrame(rankings_data)
        
        # 评分分布直方图
        fig_hist = make_subplots(
            rows=2, cols=2,
            subplot_titles=('综合评分分布', '技术评分分布', '基本面评分分布', '评分对比'),
            specs=[[{"type": "histogram"}, {"type": "histogram"}],
                   [{"type": "histogram"}, {"type": "scatter"}]]
        )
        
        # 综合评分分布
        fig_hist.add_trace(
            go.Histogram(x=df['total_score'], name='综合评分', nbinsx=20),
            row=1, col=1
        )
        
        # 技术评分分布
        fig_hist.add_trace(
            go.Histogram(x=df['technical_score'], name='技术评分', nbinsx=20),
            row=1, col=2
        )
        
        # 基本面评分分布
        fig_hist.add_trace(
            go.Histogram(x=df['fundamental_score'], name='基本面评分', nbinsx=20),
            row=2, col=1
        )
        
        # 技术vs基本面评分散点图
        fig_hist.add_trace(
            go.Scatter(
                x=df['technical_score'], 
                y=df['fundamental_score'],
                mode='markers',
                name='技术vs基本面',
                text=df['name'],
                hovertemplate='%{text}<br>技术: %{x}<br>基本面: %{y}<extra></extra>'
            ),
            row=2, col=2
        )
        
        fig_hist.update_layout(
            height=600,
            title_text="评分分布综合分析",
            showlegend=False
        )
        
        st.plotly_chart(fig_hist, use_container_width=True)
        
        # 评分统计
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("平均综合评分", f"{df['total_score'].mean():.1f}")
            st.metric("评分标准差", f"{df['total_score'].std():.1f}")
        
        with col2:
            st.metric("高分股票数(≥80)", len(df[df['total_score'] >= 80]))
            st.metric("中等股票数(60-80)", len(df[(df['total_score'] >= 60) & (df['total_score'] < 80)]))
        
        with col3:
            st.metric("技术领先股票数", len(df[df['technical_score'] > df['fundamental_score']]))
            st.metric("基本面优势股票数", len(df[df['fundamental_score'] > df['technical_score']]))
    
    def _render_recommendation_analysis(self, rankings_data: List[Dict], key_suffix: str):
        """渲染推荐分析"""
        
        st.markdown("### 🎯 投资建议分析")
        
        df = pd.DataFrame(rankings_data)
        
        # 投资建议饼图
        rec_counts = df['recommendation'].value_counts()
        
        fig_pie = go.Figure(data=[
            go.Pie(
                labels=rec_counts.index,
                values=rec_counts.values,
                hole=0.4,
                textinfo='label+percent+value',
                textposition='auto'
            )
        ])
        
        fig_pie.update_layout(
            title="投资建议分布",
            annotations=[dict(text='投资建议', x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # 各建议类别的平均评分
            st.markdown("#### 📈 各建议类别平均评分")
            
            rec_stats = df.groupby('recommendation').agg({
                'total_score': 'mean',
                'technical_score': 'mean',
                'fundamental_score': 'mean',
                'change_percent': 'mean'
            }).round(1)
            
            st.dataframe(
                rec_stats,
                column_config={
                    "total_score": "综合评分",
                    "technical_score": "技术评分", 
                    "fundamental_score": "基本面评分",
                    "change_percent": "平均涨跌幅(%)"
                }
            )
        
        # 推荐股票详情
        st.markdown("#### 🌟 重点推荐股票")
        
        buy_stocks = df[df['recommendation'] == '买入'].head(10)
        if not buy_stocks.empty:
            buy_display = buy_stocks[['name', 'symbol', 'total_score', 'current_price', 'target_price', 'change_percent']].copy()
            buy_display['潜在收益'] = ((buy_display['target_price'] - buy_display['current_price']) / buy_display['current_price'] * 100).round(2)
            
            st.dataframe(
                buy_display,
                column_config={
                    "name": "股票名称",
                    "symbol": "代码",
                    "total_score": st.column_config.ProgressColumn("评分", min_value=0, max_value=100),
                    "current_price": st.column_config.NumberColumn("当前价", format="%.2f"),
                    "target_price": st.column_config.NumberColumn("目标价", format="%.2f"),
                    "change_percent": st.column_config.NumberColumn("涨跌幅(%)", format="%.2f"),
                    "潜在收益": st.column_config.NumberColumn("潜在收益(%)", format="%.2f")
                },
                use_container_width=True
            )
        else:
            st.info("当前没有评级为'买入'的股票")
    
    def _render_price_analysis(self, rankings_data: List[Dict], key_suffix: str):
        """渲染价格分析"""
        
        st.markdown("### 📈 价格与估值分析")
        
        df = pd.DataFrame(rankings_data)
        
        # 价格vs评分散点图
        fig_price = make_subplots(
            rows=2, cols=2,
            subplot_titles=('价格vs综合评分', '涨跌幅分布', '目标价vs当前价', 'PE-PB分布'),
            specs=[[{"type": "scatter"}, {"type": "histogram"}],
                   [{"type": "scatter"}, {"type": "scatter"}]]
        )
        
        # 价格vs评分
        fig_price.add_trace(
            go.Scatter(
                x=df['current_price'],
                y=df['total_score'],
                mode='markers',
                name='价格vs评分',
                text=df['name'],
                hovertemplate='%{text}<br>价格: ¥%{x}<br>评分: %{y}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 涨跌幅分布
        fig_price.add_trace(
            go.Histogram(x=df['change_percent'], nbinsx=30, name='涨跌幅分布'),
            row=1, col=2
        )
        
        # 目标价vs当前价
        fig_price.add_trace(
            go.Scatter(
                x=df['current_price'],
                y=df['target_price'],
                mode='markers',
                name='目标价vs当前价',
                text=df['name'],
                hovertemplate='%{text}<br>当前: ¥%{x}<br>目标: ¥%{y}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # PE-PB分布（如果有数据）
        if 'pe_ratio' in df.columns and 'pb_ratio' in df.columns:
            # 过滤异常值
            pe_pb_df = df[(df['pe_ratio'] > 0) & (df['pe_ratio'] < 100) & 
                         (df['pb_ratio'] > 0) & (df['pb_ratio'] < 20)]
            
            fig_price.add_trace(
                go.Scatter(
                    x=pe_pb_df['pe_ratio'],
                    y=pe_pb_df['pb_ratio'],
                    mode='markers',
                    name='PE-PB分布',
                    text=pe_pb_df['name'],
                    hovertemplate='%{text}<br>PE: %{x}<br>PB: %{y}<extra></extra>'
                ),
                row=2, col=2
            )
        
        # 添加目标价=当前价的对角线
        min_price = df['current_price'].min()
        max_price = df['current_price'].max()
        fig_price.add_trace(
            go.Scatter(
                x=[min_price, max_price],
                y=[min_price, max_price],
                mode='lines',
                name='目标价=当前价',
                line=dict(dash='dash', color='red')
            ),
            row=2, col=1
        )
        
        fig_price.update_layout(
            height=700,
            title_text="价格与估值综合分析",
            showlegend=False
        )
        
        st.plotly_chart(fig_price, use_container_width=True)
        
        # 价格统计
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("平均股价", f"¥{df['current_price'].mean():.2f}")
            st.metric("价格中位数", f"¥{df['current_price'].median():.2f}")
        
        with col2:
            st.metric("平均涨跌幅", f"{df['change_percent'].mean():.2f}%")
            st.metric("上涨股票占比", f"{(df['change_percent'] > 0).mean()*100:.1f}%")
        
        with col3:
            avg_upside = ((df['target_price'] - df['current_price']) / df['current_price'] * 100).mean()
            st.metric("平均上涨空间", f"{avg_upside:.1f}%")
            st.metric("有上涨空间股票", len(df[df['target_price'] > df['current_price']]))
        
        with col4:
            if 'pe_ratio' in df.columns:
                pe_filtered = df[(df['pe_ratio'] > 0) & (df['pe_ratio'] < 100)]
                st.metric("平均PE", f"{pe_filtered['pe_ratio'].mean():.1f}")
            if 'pb_ratio' in df.columns:
                pb_filtered = df[(df['pb_ratio'] > 0) & (df['pb_ratio'] < 20)]
                st.metric("平均PB", f"{pb_filtered['pb_ratio'].mean():.2f}")
    
    def _prepare_rankings_dataframe(self, rankings_data: List[Dict], controls: Dict) -> pd.DataFrame:
        """准备排名数据框"""
        
        if not rankings_data:
            return pd.DataFrame()
        
        df = pd.DataFrame(rankings_data)
        
        # 应用筛选条件
        recommendation_filter = controls.get('recommendation_filter', [])
        if recommendation_filter:
            df = df[df['recommendation'].isin(recommendation_filter)]
        
        # 应用排序
        sort_by = controls.get('sort_by', '综合评分')
        order = controls.get('order', '降序')
        
        sort_field_map = {
            '综合评分': 'total_score',
            '技术评分': 'technical_score',
            '基本面评分': 'fundamental_score',
            '涨跌幅': 'change_percent',
            '市值': 'market_cap'
        }
        
        sort_field = sort_field_map.get(sort_by, 'total_score')
        ascending = (order == '升序')
        
        if sort_field in df.columns:
            df = df.sort_values(sort_field, ascending=ascending)
        
        # 限制显示数量
        display_count = controls.get('display_count', 50)
        df = df.head(display_count)
        
        # 重新编号
        df = df.reset_index(drop=True)
        df['排名'] = range(1, len(df) + 1)
        
        # 选择显示列
        display_columns = ['排名', 'symbol', 'name', 'total_score', 'technical_score', 
                          'fundamental_score', 'current_price', 'change_percent', 
                          'recommendation', 'target_price']
        
        # 重命名列
        column_rename_map = {
            'symbol': '股票代码',
            'name': '股票名称',
            'total_score': '综合评分',
            'technical_score': '技术评分',
            'fundamental_score': '基本面评分',
            'current_price': '当前价格',
            'change_percent': '涨跌幅',
            'recommendation': '建议',
            'target_price': '目标价'
        }
        
        # 只选择存在的列
        available_columns = [col for col in display_columns if col in df.columns]
        df_display = df[available_columns].copy()
        df_display = df_display.rename(columns=column_rename_map)
        
        return df_display
    
    def _get_recommendation_column_config(self):
        """获取建议列的配置"""
        return st.column_config.TextColumn(
            "建议",
            width="small",
            help="投资建议：买入、持有、关注、卖出"
        )
    
    def _show_selected_stocks_details(self, df: pd.DataFrame, selected_rows: List[int], key_suffix: str):
        """显示选中股票的详细信息"""
        
        if not selected_rows:
            return
        
        st.markdown("---")
        st.markdown("### 📋 选中股票详情")
        
        selected_df = df.iloc[selected_rows]
        
        for _, stock in selected_df.iterrows():
            with st.expander(f"📊 {stock.get('股票名称', '')} ({stock.get('股票代码', '')})"):
                
                detail_col1, detail_col2, detail_col3 = st.columns(3)
                
                with detail_col1:
                    st.metric("综合评分", f"{stock.get('综合评分', 0):.1f}")
                    st.metric("当前价格", f"¥{stock.get('当前价格', 0):.2f}")
                
                with detail_col2:
                    st.metric("技术评分", f"{stock.get('技术评分', 0):.1f}")
                    st.metric("目标价格", f"¥{stock.get('目标价', 0):.2f}")
                
                with detail_col3:
                    st.metric("基本面评分", f"{stock.get('基本面评分', 0):.1f}")
                    change_pct = stock.get('涨跌幅', 0)
                    st.metric("涨跌幅", f"{change_pct:+.2f}%", delta=f"{change_pct:+.2f}%")
                
                recommendation = stock.get('建议', '')
                if recommendation == '买入':
                    st.success(f"💚 投资建议: {recommendation}")
                elif recommendation == '持有':
                    st.info(f"💙 投资建议: {recommendation}")
                elif recommendation == '关注':
                    st.warning(f"💛 投资建议: {recommendation}")
                else:
                    st.error(f"❤️ 投资建议: {recommendation}")


class SectorHeatmapDisplay:
    """板块热力图展示组件"""
    
    def render(self, sectors_data: Dict[str, Any], key_suffix: str = "") -> None:
        """
        渲染板块热力图
        
        Args:
            sectors_data: 板块数据
            key_suffix: 组件key后缀
        """
        
        if not sectors_data:
            st.info("🔥 暂无板块数据")
            return
        
        st.markdown("### 🔥 板块表现热力图")
        
        # 创建热力图数据
        self._render_sector_performance_heatmap(sectors_data)
        
        # 板块详细分析
        self._render_sector_detailed_analysis(sectors_data, key_suffix)
    
    def _render_sector_performance_heatmap(self, sectors_data: Dict):
        """渲染板块表现热力图"""
        
        # 准备数据
        sector_names = list(sectors_data.keys())
        metrics = ['涨跌幅', '成交额', '活跃度', '推荐度']
        
        # 创建数据矩阵
        matrix_data = []
        for metric in metrics:
            row = []
            for sector in sector_names:
                sector_info = sectors_data[sector]
                if metric == '涨跌幅':
                    value = sector_info.get('change_percent', 0)
                elif metric == '成交额':
                    value = sector_info.get('volume', 0) / 100  # 归一化
                elif metric == '活跃度':
                    value = sector_info.get('activity_score', 0)
                elif metric == '推荐度':
                    value = sector_info.get('recommendation_score', 0)
                else:
                    value = 0
                row.append(value)
            matrix_data.append(row)
        
        # 创建热力图
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=matrix_data,
            x=sector_names,
            y=metrics,
            colorscale='RdYlGn',
            text=[[f"{val:.1f}" for val in row] for row in matrix_data],
            texttemplate="%{text}",
            textfont={"size": 12},
            hovertemplate='板块: %{x}<br>指标: %{y}<br>数值: %{z:.1f}<extra></extra>'
        ))
        
        fig_heatmap.update_layout(
            title="板块综合表现热力图",
            xaxis_title="板块",
            yaxis_title="指标",
            height=400
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # 板块排名
        col1, col2 = st.columns(2)
        
        with col1:
            # 按涨跌幅排序
            sector_by_change = sorted(
                sectors_data.items(),
                key=lambda x: x[1].get('change_percent', 0),
                reverse=True
            )
            
            st.markdown("#### 📈 涨跌幅排名")
            for i, (sector, data) in enumerate(sector_by_change[:8]):
                change = data.get('change_percent', 0)
                emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
                st.write(f"{i+1}. {emoji} {sector}: {change:+.2f}%")
        
        with col2:
            # 按推荐度排序
            sector_by_rec = sorted(
                sectors_data.items(),
                key=lambda x: x[1].get('recommendation_score', 0),
                reverse=True
            )
            
            st.markdown("#### 🎯 推荐度排名")
            for i, (sector, data) in enumerate(sector_by_rec[:8]):
                rec_score = data.get('recommendation_score', 0)
                st.write(f"{i+1}. ⭐ {sector}: {rec_score:.1f}分")
    
    def _render_sector_detailed_analysis(self, sectors_data: Dict, key_suffix: str):
        """渲染板块详细分析"""
        
        st.markdown("### 📊 板块详细分析")
        
        # 选择板块
        selected_sector = st.selectbox(
            "选择板块查看详情",
            options=list(sectors_data.keys()),
            key=f"sector_select_{key_suffix}"
        )
        
        if selected_sector and selected_sector in sectors_data:
            sector_data = sectors_data[selected_sector]
            
            # 板块基本信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                change_pct = sector_data.get('change_percent', 0)
                st.metric("板块涨跌幅", f"{change_pct:+.2f}%", delta=f"{change_pct:+.2f}%")
            
            with col2:
                volume = sector_data.get('volume', 0)
                st.metric("成交额", f"{volume:.1f}亿")
            
            with col3:
                activity = sector_data.get('activity_score', 0)
                st.metric("活跃度", f"{activity:.1f}")
            
            with col4:
                rec_score = sector_data.get('recommendation_score', 0)
                st.metric("推荐度", f"{rec_score:.1f}")
            
            # 板块内股票推荐
            if 'recommended_stocks' in sector_data:
                st.markdown(f"#### 🌟 {selected_sector}板块推荐股票")
                
                recommended_stocks = sector_data['recommended_stocks']
                if recommended_stocks:
                    # 创建推荐股票表格
                    rec_df = pd.DataFrame(recommended_stocks)
                    
                    if not rec_df.empty:
                        # 选择显示列
                        display_cols = ['name', 'symbol', 'total_score', 'current_price', 'change_percent', 'recommendation']
                        available_cols = [col for col in display_cols if col in rec_df.columns]
                        
                        if available_cols:
                            rec_display = rec_df[available_cols].copy()
                            
                            # 重命名列
                            column_rename = {
                                'name': '股票名称',
                                'symbol': '代码',
                                'total_score': '综合评分',
                                'current_price': '当前价格',
                                'change_percent': '涨跌幅',
                                'recommendation': '建议'
                            }
                            
                            rec_display = rec_display.rename(columns=column_rename)
                            
                            st.dataframe(
                                rec_display,
                                use_container_width=True,
                                column_config={
                                    "综合评分": st.column_config.ProgressColumn("综合评分", min_value=0, max_value=100),
                                    "当前价格": st.column_config.NumberColumn("当前价格", format="%.2f"),
                                    "涨跌幅": st.column_config.NumberColumn("涨跌幅(%)", format="%.2f")
                                }
                            )
                        else:
                            st.info("推荐股票数据结构不完整")
                    else:
                        st.info("暂无推荐股票数据")
                else:
                    st.info(f"{selected_sector}板块暂无推荐股票")
            
            # 板块趋势图（模拟）
            self._render_sector_trend_chart(selected_sector, sector_data)
    
    def _render_sector_trend_chart(self, sector_name: str, sector_data: Dict):
        """渲染板块趋势图"""
        
        st.markdown(f"#### 📈 {sector_name}板块趋势")
        
        # 模拟历史数据
        import random
        from datetime import datetime, timedelta
        
        dates = []
        values = []
        base_change = sector_data.get('change_percent', 0)
        
        # 生成过去30天的模拟数据
        for i in range(30):
            date = datetime.now() - timedelta(days=29-i)
            dates.append(date.strftime('%m-%d'))
            
            # 模拟价格变化
            daily_change = random.uniform(-2, 3) + (base_change / 30)
            if i == 0:
                values.append(100)
            else:
                values.append(values[-1] * (1 + daily_change/100))
        
        # 创建趋势图
        fig_trend = go.Figure(data=go.Scatter(
            x=dates,
            y=values,
            mode='lines+markers',
            name=f'{sector_name}指数',
            line=dict(width=2),
            marker=dict(size=4)
        ))
        
        fig_trend.update_layout(
            title=f"{sector_name}板块30日走势",
            xaxis_title="日期",
            yaxis_title="指数",
            height=300,
            showlegend=False
        )
        
        st.plotly_chart(fig_trend, use_container_width=True)


class MarketBreadthGauge:
    """市场广度仪表盘组件"""
    
    def render(self, breadth_data: Dict[str, Any]) -> None:
        """
        渲染市场广度仪表盘
        
        Args:
            breadth_data: 市场广度数据
        """
        
        if not breadth_data:
            st.info("📈 暂无市场广度数据")
            return
        
        st.markdown("### 📈 市场广度仪表盘")
        
        # 主要指标仪表盘
        col1, col2 = st.columns(2)
        
        with col1:
            self._render_gauge_chart("市场情绪指数", breadth_data.get('sentiment_index', 50))
            
        with col2:
            self._render_gauge_chart("市场强度指数", breadth_data.get('market_strength', 50))
        
        # 详细指标
        self._render_detailed_metrics(breadth_data)
        
        # 市场状态总结
        self._render_market_status_summary(breadth_data)
    
    def _render_gauge_chart(self, title: str, value: float):
        """渲染单个仪表盘图表"""
        
        # 确定颜色
        if value >= 70:
            color = "green"
        elif value >= 40:
            color = "orange"  
        else:
            color = "red"
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title, 'font': {'size': 16}},
            delta={'reference': 50},
            gauge={
                'axis': {'range': [None, 100], 'tickwidth': 1},
                'bar': {'color': color, 'thickness': 0.8},
                'steps': [
                    {'range': [0, 30], 'color': "lightgray"},
                    {'range': [30, 70], 'color': "lightblue"},
                    {'range': [70, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 80
                }
            }
        ))
        
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)
    
    def _render_detailed_metrics(self, breadth_data: Dict):
        """渲染详细指标"""
        
        st.markdown("#### 📊 详细市场指标")
        
        # 指标网格
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            up_ratio = breadth_data.get('up_ratio', 50)
            st.metric("上涨股票占比", f"{up_ratio:.1f}%", 
                     delta=f"{breadth_data.get('up_ratio_change', 0):+.1f}%")
            
            limit_up = breadth_data.get('limit_up_count', 0)
            st.metric("涨停股票数", f"{limit_up}只")
        
        with col2:
            activity = breadth_data.get('activity_index', 50)
            st.metric("成交活跃度", f"{activity:.1f}", 
                     delta=f"{breadth_data.get('activity_change', 0):+.1f}")
            
            limit_down = breadth_data.get('limit_down_count', 0)
            st.metric("跌停股票数", f"{limit_down}只")
        
        with col3:
            net_inflow = breadth_data.get('net_inflow', 0)
            st.metric("资金净流入", f"{net_inflow:.1f}亿", 
                     delta=f"{breadth_data.get('net_inflow_change', 0):+.1f}亿")
            
            new_high = breadth_data.get('new_high_count', 0)
            st.metric("创新高股票数", f"{new_high}只")
        
        with col4:
            sentiment = breadth_data.get('sentiment_index', 50)
            st.metric("市场情绪", f"{sentiment:.1f}", 
                     delta=f"{breadth_data.get('sentiment_change', 0):+.1f}")
            
            new_low = breadth_data.get('new_low_count', 0)
            st.metric("创新低股票数", f"{new_low}只")
        
        # 市场广度雷达图
        self._render_breadth_radar_chart(breadth_data)
    
    def _render_breadth_radar_chart(self, breadth_data: Dict):
        """渲染市场广度雷达图"""
        
        st.markdown("#### 🎯 市场广度雷达图")
        
        # 准备雷达图数据
        categories = ['上涨占比', '活跃度', '资金流入', '情绪指数', '市场强度']
        
        values = [
            breadth_data.get('up_ratio', 50),
            breadth_data.get('activity_index', 50),
            min(100, max(0, breadth_data.get('net_inflow', 0) + 50)),  # 归一化到0-100
            breadth_data.get('sentiment_index', 50),
            breadth_data.get('market_strength', 50)
        ]
        
        fig_radar = go.Figure()
        
        fig_radar.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='当前市场状态',
            line_color='blue'
        ))
        
        # 添加理想状态对比
        ideal_values = [70, 80, 60, 70, 75]
        fig_radar.add_trace(go.Scatterpolar(
            r=ideal_values,
            theta=categories,
            fill='toself',
            name='理想状态',
            line_color='green',
            opacity=0.3
        ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            showlegend=True,
            height=400
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)
    
    def _render_market_status_summary(self, breadth_data: Dict):
        """渲染市场状态总结"""
        
        st.markdown("#### 💡 市场状态总结")
        
        # 计算综合得分
        scores = [
            breadth_data.get('up_ratio', 50),
            breadth_data.get('activity_index', 50), 
            breadth_data.get('sentiment_index', 50),
            breadth_data.get('market_strength', 50)
        ]
        
        overall_score = sum(scores) / len(scores)
        
        # 状态判断
        if overall_score >= 70:
            status_color = "success"
            status_emoji = "🟢"
            status_text = "强势"
            status_desc = "市场表现强劲，多数指标向好，建议积极参与投资机会"
        elif overall_score >= 50:
            status_color = "info"
            status_emoji = "🟡"
            status_text = "中性"
            status_desc = "市场处于平衡状态，建议谨慎选股，关注个股机会"
        else:
            status_color = "error"
            status_emoji = "🔴"
            status_text = "弱势"
            status_desc = "市场表现疲弱，建议控制仓位，等待更好的入场时机"
        
        # 显示状态
        if status_color == "success":
            st.success(f"{status_emoji} **市场状态: {status_text}** (得分: {overall_score:.1f})")
            st.success(status_desc)
        elif status_color == "info":
            st.info(f"{status_emoji} **市场状态: {status_text}** (得分: {overall_score:.1f})")
            st.info(status_desc)
        else:
            st.error(f"{status_emoji} **市场状态: {status_text}** (得分: {overall_score:.1f})")
            st.error(status_desc)
        
        # 关键观察点
        st.markdown("**📋 关键观察点:**")
        observations = []
        
        if breadth_data.get('up_ratio', 50) > 60:
            observations.append("✅ 上涨股票占比较高，市场整体向上")
        elif breadth_data.get('up_ratio', 50) < 40:
            observations.append("❌ 下跌股票较多，市场承压")
        
        if breadth_data.get('net_inflow', 0) > 50:
            observations.append("✅ 资金净流入明显，买盘积极")
        elif breadth_data.get('net_inflow', 0) < -50:
            observations.append("❌ 资金净流出严重，抛压较重")
        
        if breadth_data.get('limit_up_count', 0) > breadth_data.get('limit_down_count', 0) * 2:
            observations.append("✅ 涨停股票远多于跌停，市场情绪乐观")
        elif breadth_data.get('limit_down_count', 0) > breadth_data.get('limit_up_count', 0) * 2:
            observations.append("❌ 跌停股票较多，市场恐慌情绪较重")
        
        if breadth_data.get('new_high_count', 0) > breadth_data.get('new_low_count', 0):
            observations.append("✅ 创新高股票多于创新低，强势股较多")
        
        if not observations:
            observations.append("📊 各项指标相对均衡，市场处于震荡状态")
        
        for obs in observations:
            st.write(f"• {obs}")


# 工具函数
def create_comparison_chart(data1: List, data2: List, labels: List[str], 
                          title: str, y_title: str) -> go.Figure:
    """创建对比图表"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name=labels[0],
        x=list(range(len(data1))),
        y=data1,
        marker_color='lightblue'
    ))
    
    fig.add_trace(go.Bar(
        name=labels[1], 
        x=list(range(len(data2))),
        y=data2,
        marker_color='lightcoral'
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="类别",
        yaxis_title=y_title,
        barmode='group'
    )
    
    return fig


def format_large_number(num: float) -> str:
    """格式化大数字显示"""
    
    if num >= 1e8:
        return f"{num/1e8:.1f}亿"
    elif num >= 1e4:
        return f"{num/1e4:.1f}万"
    else:
        return f"{num:.0f}"


def get_trend_color(value: float, reference: float = 0) -> str:
    """根据趋势获取颜色"""
    
    if value > reference:
        return "green"
    elif value < reference:
        return "red"
    else:
        return "gray"
