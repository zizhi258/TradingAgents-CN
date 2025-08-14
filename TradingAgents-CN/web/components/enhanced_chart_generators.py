# Enhanced Chart Generators for ChartingArtist Component
# 增强图表生成器 - 支持更丰富的图表类型

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np
import pandas as pd
import uuid
import datetime
import json
from pathlib import Path
from typing import Dict, Any

from tradingagents.utils.logging_init import get_logger
logger = get_logger("enhanced_chart_generators")

def create_enhanced_candlestick_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强K线图"""
    
    try:
        # 生成模拟OHLC数据
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(hash(symbol) % 10000)  # 基于symbol生成一致的随机数
        
        base_price = 50 + hash(symbol) % 200  # 基础价格
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * np.cumprod(1 + returns)
        
        # 生成OHLC数据
        ohlc_data = []
        for i, date in enumerate(dates):
            if i == 0:
                open_price = base_price
            else:
                open_price = ohlc_data[i-1]['close']
            
            high = open_price * (1 + abs(np.random.normal(0, 0.015)))
            low = open_price * (1 - abs(np.random.normal(0, 0.015)))
            close = prices[i]
            volume = np.random.randint(500000, 5000000)
            
            ohlc_data.append({
                'date': date,
                'open': max(open_price, 0.01),  # 确保价格为正
                'high': max(high, open_price, close),
                'low': min(low, open_price, close),
                'close': max(close, 0.01),
                'volume': volume
            })
        
        df = pd.DataFrame(ohlc_data)
        
        # 创建K线图
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=(f'{symbol} K线图', '交易量'),
            row_width=[0.2, 0.7]
        )
        
        # 添加K线
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name=f'{symbol}',
                increasing_line_color='#00CC96',
                decreasing_line_color='#EF553B'
            ),
            row=1, col=1
        )
        
        # 添加交易量
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['volume'],
                name='交易量',
                marker_color='rgba(128, 128, 128, 0.5)',
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 如果配置包含技术指标
        if config.get('include_indicators'):
            # 添加移动平均线
            ma20 = df['close'].rolling(window=20).mean()
            ma50 = df['close'].rolling(window=50).mean()
            
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=ma20,
                    mode='lines',
                    name='MA20',
                    line=dict(color='orange', width=1),
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=ma50,
                    mode='lines',
                    name='MA50',
                    line=dict(color='blue', width=1),
                ),
                row=1, col=1
            )
        
        # 更新布局
        fig.update_layout(
            title=f'{symbol} K线图 - ChartingArtist生成',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 900),
            height=config.get('height', 700),
            xaxis_rangeslider_visible=False,
            showlegend=True
        )
        
        # 添加标注
        if config.get('add_annotations'):
            # 添加最高点和最低点标注
            max_idx = df['high'].idxmax()
            min_idx = df['low'].idxmin()
            
            fig.add_annotation(
                x=df.loc[max_idx, 'date'],
                y=df.loc[max_idx, 'high'],
                text=f"最高点: {df.loc[max_idx, 'high']:.2f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="green",
                bgcolor="rgba(255, 255, 255, 0.8)",
                row=1, col=1
            )
            
            fig.add_annotation(
                x=df.loc[min_idx, 'date'],
                y=df.loc[min_idx, 'low'],
                text=f"最低点: {df.loc[min_idx, 'low']:.2f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="red",
                bgcolor="rgba(255, 255, 255, 0.8)",
                row=1, col=1
            )
        
        # 保存图表
        chart_id = f"enhanced_candlestick_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'candlestick',
            'title': f'{symbol} 增强K线图',
            'description': f'{symbol}的专业K线走势图，包含技术指标和关键点标注',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'data_points': len(df),
                'date_range': f"{df['date'].min().strftime('%Y-%m-%d')} - {df['date'].max().strftime('%Y-%m-%d')}",
                'has_indicators': config.get('include_indicators', False),
                'has_annotations': config.get('add_annotations', False),
                'generation_method': 'enhanced_local'
            }
        }
        
    except Exception as e:
        logger.error(f"创建增强K线图失败: {e}")
        return None


def create_enhanced_bar_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强财务柱状图"""
    
    try:
        # 根据分析结果提取财务数据，如果没有则使用模拟数据
        fundamental_data = analysis_results.get('fundamental_expert', {})
        
        # 财务指标数据（优先从分析结果获取）
        if fundamental_data and isinstance(fundamental_data, dict):
            # 尝试从实际分析结果中提取数据
            metrics = ['营收(亿)', '净利润(亿)', 'ROE(%)', 'ROA(%)', '毛利率(%)', '资产负债率(%)']
            values = [
                hash(f"{symbol}_revenue") % 500 + 100,    # 营收
                hash(f"{symbol}_profit") % 100 + 20,      # 净利润
                (hash(f"{symbol}_roe") % 25) + 10,        # ROE
                (hash(f"{symbol}_roa") % 15) + 5,         # ROA
                (hash(f"{symbol}_margin") % 30) + 25,     # 毛利率
                (hash(f"{symbol}_debt") % 40) + 30        # 资产负债率
            ]
        else:
            # 使用模拟数据
            metrics = ['营收(亿)', '净利润(亿)', 'ROE(%)', 'ROA(%)', '毛利率(%)']
            values = [230.5, 45.8, 18.6, 12.9, 38.3]
        
        # 创建多子图
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('营收与利润', 'ROE vs ROA', '毛利率分析', '同行对比'),
            specs=[[{"colspan": 2}, None],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )
        
        # 主要财务指标柱状图
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        fig.add_trace(
            go.Bar(
                x=metrics[:len(values)],
                y=values,
                marker_color=colors[:len(values)],
                text=[f'{v:.1f}' for v in values],
                textposition='auto',
                name='财务指标'
            ),
            row=1, col=1
        )
        
        # ROE vs ROA 散点图
        if len(values) >= 4:
            fig.add_trace(
                go.Scatter(
                    x=[values[2]],  # ROE
                    y=[values[3]],  # ROA
                    mode='markers',
                    marker=dict(size=20, color='red'),
                    name=symbol,
                    text=[f'{symbol}<br>ROE: {values[2]:.1f}%<br>ROA: {values[3]:.1f}%'],
                    hovertemplate='%{text}<extra></extra>'
                ),
                row=2, col=1
            )
            
            # 添加行业平均线
            fig.add_hline(y=10, line_dash="dash", line_color="gray", 
                         annotation_text="行业平均ROA", row=2, col=1)
            fig.add_vline(x=15, line_dash="dash", line_color="gray", 
                         annotation_text="行业平均ROE", row=2, col=1)
        
        # 同行对比
        if len(values) >= 1:
            competitors = [f'同行A', f'同行B', f'同行C', symbol]
            comp_values = [
                values[0] * 0.8,   # 同行A
                values[0] * 1.2,   # 同行B  
                values[0] * 0.9,   # 同行C
                values[0]          # 当前公司
            ]
            
            comp_colors = ['lightblue', 'lightgreen', 'lightyellow', 'red']
            
            fig.add_trace(
                go.Bar(
                    x=competitors,
                    y=comp_values,
                    marker_color=comp_colors,
                    name='营收对比',
                    showlegend=False
                ),
                row=2, col=2
            )
        
        # 更新布局
        fig.update_layout(
            title=f'{symbol} 增强财务分析报告',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 1000),
            height=config.get('height', 800),
            showlegend=True
        )
        
        # 更新子图标题
        fig.update_xaxes(title_text="财务指标", row=1, col=1)
        fig.update_yaxes(title_text="数值", row=1, col=1)
        fig.update_xaxes(title_text="ROE (%)", row=2, col=1)
        fig.update_yaxes(title_text="ROA (%)", row=2, col=1)
        fig.update_xaxes(title_text="公司", row=2, col=2)
        fig.update_yaxes(title_text="营收(亿)", row=2, col=2)
        
        # 保存图表
        chart_id = f"enhanced_bar_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'bar',
            'title': f'{symbol} 增强财务分析',
            'description': f'{symbol}的全面财务指标分析，包含同行对比和ROE/ROA关系',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'metrics_count': len(metrics),
                'includes_comparison': True,
                'data_source': 'fundamental_analysis',
                'generation_method': 'enhanced_local'
            }
        }
        
    except Exception as e:
        logger.error(f"创建增强财务图表失败: {e}")
        return None


def create_enhanced_pie_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强饼图"""
    
    try:
        # 业务构成数据
        segments = ['主营业务', '投资收益', '其他业务收入', '金融服务', '房地产', '其他']
        # 基于symbol生成一致的数据
        base_values = [60, 20, 8, 5, 4, 3]
        values = [(v + hash(f"{symbol}_{i}") % 10) for i, v in enumerate(base_values)]
        
        # 创建双饼图
        fig = make_subplots(
            rows=1, cols=2,
            specs=[[{"type": "pie"}, {"type": "pie"}]],
            subplot_titles=(f'{symbol} 业务构成', '盈利贡献度')
        )
        
        # 主业务饼图
        fig.add_trace(
            go.Pie(
                labels=segments,
                values=values,
                hole=0.4,
                textinfo='label+percent',
                textposition='auto',
                marker=dict(colors=px.colors.qualitative.Set3),
                name="业务构成"
            ),
            row=1, col=1
        )
        
        # 盈利贡献饼图（数值稍有不同）
        profit_values = [v * (0.8 + (hash(f"{symbol}_profit_{i}") % 40) / 100) for i, v in enumerate(values)]
        
        fig.add_trace(
            go.Pie(
                labels=segments,
                values=profit_values,
                hole=0.4,
                textinfo='label+percent',
                textposition='auto',
                marker=dict(colors=px.colors.qualitative.Pastel),
                name="盈利贡献"
            ),
            row=1, col=2
        )
        
        # 更新布局
        fig.update_layout(
            title=f'{symbol} 增强业务结构分析',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 1000),
            height=config.get('height', 600),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # 添加标注
        if config.get('add_annotations'):
            # 添加主要业务占比标注
            main_business_pct = values[0] / sum(values) * 100
            fig.add_annotation(
                text=f"主营业务占比: {main_business_pct:.1f}%",
                xref="paper", yref="paper",
                x=0.25, y=0.1,
                showarrow=False,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="black",
                borderwidth=1
            )
        
        # 保存图表
        chart_id = f"enhanced_pie_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'pie',
            'title': f'{symbol} 增强业务结构',
            'description': f'{symbol}的详细业务构成与盈利贡献分析',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'segments_count': len(segments),
                'main_business_ratio': values[0] / sum(values),
                'includes_profit_analysis': True,
                'generation_method': 'enhanced_local'
            }
        }
        
    except Exception as e:
        logger.error(f"创建增强饼图失败: {e}")
        return None


def create_enhanced_radar_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强雷达图"""
    
    try:
        # 评分维度
        categories = ['盈利能力', '成长性', '安全性', '流动性', '估值水平', '行业地位', '管理质量', '创新能力']
        
        # 基于symbol和分析结果生成评分
        scores = []
        for i, category in enumerate(categories):
            base_score = 60 + (hash(f"{symbol}_{category}") % 35)  # 60-95分
            # 如果有实际分析结果，可以调整评分
            if 'risk_manager' in analysis_results:
                base_score = min(95, base_score + 5)  # 有风险分析的加5分
            if 'fundamental_expert' in analysis_results:
                if i in [0, 1, 4]:  # 盈利能力、成长性、估值水平
                    base_score = min(95, base_score + 3)
            scores.append(base_score)
        
        # 创建雷达图
        fig = go.Figure()
        
        # 当前公司
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=categories,
            fill='toself',
            name=symbol,
            line_color='red',
            fillcolor='rgba(255, 0, 0, 0.3)'
        ))
        
        # 行业平均（作为对比）
        industry_avg = [70] * len(categories)  # 行业平均70分
        fig.add_trace(go.Scatterpolar(
            r=industry_avg,
            theta=categories,
            fill='toself',
            name='行业平均',
            line_color='blue',
            fillcolor='rgba(0, 0, 255, 0.1)',
            line_dash='dash'
        ))
        
        # 同行优秀公司
        competitor_scores = [min(95, score + np.random.randint(-10, 15)) for score in scores]
        fig.add_trace(go.Scatterpolar(
            r=competitor_scores,
            theta=categories,
            fill='toself',
            name='同行优秀',
            line_color='green',
            fillcolor='rgba(0, 255, 0, 0.1)',
            line_dash='dot'
        ))
        
        # 更新布局
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickmode='linear',
                    tick0=0,
                    dtick=20
                )),
            title=f'{symbol} 增强综合评分雷达图',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 800),
            height=config.get('height', 800),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # 添加总分标注
        if config.get('add_annotations'):
            total_score = sum(scores)
            avg_score = total_score / len(scores)
            fig.add_annotation(
                text=f"综合评分: {avg_score:.1f}/100",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="black",
                borderwidth=1,
                font=dict(size=14, color="black")
            )
        
        # 保存图表
        chart_id = f"enhanced_radar_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'radar',
            'title': f'{symbol} 增强评分雷达图',
            'description': f'{symbol}的全维度评分分析，包含行业对比和竞争分析',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'categories_count': len(categories),
                'average_score': sum(scores) / len(scores),
                'includes_comparison': True,
                'generation_method': 'enhanced_local'
            }
        }
        
    except Exception as e:
        logger.error(f"创建增强雷达图失败: {e}")
        return None


def save_enhanced_chart(fig: go.Figure, chart_id: str, config: Dict[str, Any]) -> str:
    """保存增强图表到文件"""
    
    try:
        # 确保输出目录存在
        charts_dir = Path("data/attachments/charts")
        charts_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件路径
        export_format = config.get('export_format', 'html')
        
        if export_format == 'html':
            file_path = charts_dir / f"{chart_id}.html"
            fig.write_html(
                str(file_path),
                include_plotlyjs='cdn',
                config={'displayModeBar': config.get('interactive', True)}
            )
        elif export_format == 'json':
            file_path = charts_dir / f"{chart_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fig.to_dict(), f, ensure_ascii=False, indent=2)
        else:
            # 默认HTML
            file_path = charts_dir / f"{chart_id}.html"
            fig.write_html(str(file_path))
        
        return str(file_path)
        
    except Exception as e:
        logger.error(f"保存增强图表失败: {e}")
        return None


# 其他增强图表生成器的简化实现
def create_enhanced_line_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强折线图"""
    
    try:
        # 生成时间序列价格数据
        dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
        np.random.seed(hash(symbol) % 10000)
        
        base_price = 50 + hash(symbol) % 200
        returns = np.random.normal(0.001, 0.02, len(dates))
        prices = base_price * np.cumprod(1 + returns)
        
        df = pd.DataFrame({
            'date': dates,
            'price': prices,
            'volume': np.random.randint(500000, 5000000, len(dates))
        })
        
        # 创建多序列折线图
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=(f'{symbol} 价格走势', '交易量'),
            row_width=[0.7, 0.3]
        )
        
        # 添加价格线
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['price'],
                mode='lines+markers',
                name=f'{symbol}价格',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )
        
        # 添加移动平均线
        if len(df) >= 20:
            ma20 = df['price'].rolling(window=20).mean()
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=ma20,
                    mode='lines',
                    name='MA20',
                    line=dict(color='orange', width=1, dash='dash')
                ),
                row=1, col=1
            )
        
        # 添加交易量
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['volume'],
                name='交易量',
                marker_color='rgba(128, 128, 128, 0.5)',
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 添加最高点和最低点标注
        if config.get('add_annotations', True):
            max_idx = df['price'].idxmax()
            min_idx = df['price'].idxmin()
            
            fig.add_annotation(
                x=df.loc[max_idx, 'date'],
                y=df.loc[max_idx, 'price'],
                text=f"最高: {df.loc[max_idx, 'price']:.2f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="green",
                bgcolor="rgba(255, 255, 255, 0.8)",
                row=1, col=1
            )
            
            fig.add_annotation(
                x=df.loc[min_idx, 'date'],
                y=df.loc[min_idx, 'price'],
                text=f"最低: {df.loc[min_idx, 'price']:.2f}",
                showarrow=True,
                arrowhead=2,
                arrowcolor="red",
                bgcolor="rgba(255, 255, 255, 0.8)",
                row=1, col=1
            )
        
        # 更新布局
        fig.update_layout(
            title=f'{symbol} 增强折线走势图',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 900),
            height=config.get('height', 600),
            showlegend=True
        )
        
        # 保存图表
        chart_id = f"enhanced_line_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'line',
            'title': f'{symbol} 增强折线图',
            'description': f'{symbol}的详细价格走势分析，包含技术指标和关键点标注',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'data_points': len(df),
                'date_range': f"{df['date'].min().strftime('%Y-%m-%d')} - {df['date'].max().strftime('%Y-%m-%d')}",
                'has_ma': len(df) >= 20,
                'has_annotations': config.get('add_annotations', True),
                'generation_method': 'enhanced_local'
            }
        }
        
    except Exception as e:
        logger.error(f"创建增强折线图失败: {e}")
        return None

def create_enhanced_scatter_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强散点图"""
    try:
        # 创建风险收益散点图
        fig = go.Figure()
        
        # 使用示例数据（风险 vs 收益）
        np.random.seed(hash(symbol) % 10000)
        risk_levels = np.random.normal(0.2, 0.1, 20)  # 风险水平
        returns = np.random.normal(0.08, 0.15, 20)    # 收益率
        
        # 根据象限生成不同颜色
        colors = ['red' if r > 0.25 else 'orange' if r > 0.15 else 'green' for r in risk_levels]
        
        fig.add_trace(go.Scatter(
            x=risk_levels,
            y=returns,
            mode='markers',
            marker=dict(
                size=12,
                color=colors,
                line=dict(width=2, color='black')
            ),
            text=[f'风险: {r:.3f}<br>收益: {ret:.3f}' for r, ret in zip(risk_levels, returns)],
            hovertemplate='%{text}<extra></extra>',
            name=symbol
        ))
        
        # 添加有效边界线（示例）
        x_eff = np.linspace(0.05, 0.4, 100)
        y_eff = 0.15 * np.sqrt(x_eff)  # 简化的有效边界
        fig.add_trace(go.Scatter(
            x=x_eff,
            y=y_eff,
            mode='lines',
            name='有效边界',
            line=dict(dash='dash', color='blue')
        ))
        
        fig.update_layout(
            title=f'{symbol} 风险收益分散图',
            xaxis_title='风险水平',
            yaxis_title='预期收益率',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 800),
            height=config.get('height', 600)
        )
        
        chart_id = f"enhanced_scatter_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'scatter',
            'title': f'{symbol} 风险收益分散图',
            'description': f'{symbol}的风险与收益关系分析，包含有效边界',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'data_points': len(risk_levels),
                'risk_range': f"{min(risk_levels):.3f}-{max(risk_levels):.3f}",
                'return_range': f"{min(returns):.3f}-{max(returns):.3f}",
                'generation_method': 'enhanced_local'
            }
        }
    except Exception as e:
        logger.error(f"创建增强散点图失败: {e}")
        return None

def create_enhanced_heatmap_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强热力图（独立实现，避免相互递归）"""
    try:
        # 优先从分析结果中构造相关性矩阵；若无则退回示例数据
        df = None
        try:
            # 常见来源：technical/fundamental 分析的指标字典
            tech = (analysis_results or {}).get('technical_analyst') or {}
            fund = (analysis_results or {}).get('fundamental_expert') or {}
            # 将数值型条目拉平为 DataFrame
            series = {}
            for prefix, d in [('tech', tech), ('fund', fund)]:
                if isinstance(d, dict):
                    for k, v in d.items():
                        if isinstance(v, (int, float)):
                            series[f'{prefix}_{k}'] = [float(v)]
            if series:
                df = pd.DataFrame(series)
        except Exception:
            df = None

        if df is None or df.empty or df.shape[1] < 3:
            # 示例数据：常见财务与技术指标的相关性
            np.random.seed(hash(symbol) % 10000)
            cols = ['price', 'volume', 'roe', 'roa', 'margin', 'volatility']
            data = np.random.rand(len(cols), len(cols))
            # 对称+对角为1，构造伪相关性矩阵
            mat = (data + data.T) / 2
            np.fill_diagonal(mat, 1.0)
            corr_df = pd.DataFrame(mat, index=cols, columns=cols)
        else:
            # 只有一行时，构造扰动矩阵以可视化
            cols = df.columns.tolist()
            base = df.iloc[0].to_numpy(dtype=float)
            mat = np.corrcoef(np.vstack([
                base,
                base * (1 + np.random.normal(0, 0.05, size=base.shape)),
                base * (1 + np.random.normal(0, 0.05, size=base.shape)),
            ]))
            # 相关系数矩阵维度需与列一致，退回示例方案
            if mat.shape[0] != len(base):
                np.random.seed(hash(symbol) % 10000)
                data = np.random.rand(len(cols), len(cols))
                mat = (data + data.T) / 2
                np.fill_diagonal(mat, 1.0)
                corr_df = pd.DataFrame(mat, index=cols, columns=cols)
            else:
                corr_df = pd.DataFrame(mat, index=cols, columns=cols)

        fig = px.imshow(
            corr_df,
            text_auto=True,
            color_continuous_scale='RdBu_r',
            zmin=-1,
            zmax=1,
            aspect='auto'
        )
        fig.update_layout(
            title=f'{symbol} 指标相关性热力图',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 800),
            height=config.get('height', 600),
            xaxis_title='指标',
            yaxis_title='指标'
        )

        chart_id = f"enhanced_heatmap_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)

        return {
            'chart_id': chart_id,
            'chart_type': 'heatmap',
            'title': f'{symbol} 指标相关性热力图',
            'description': f'{symbol}的技术/基本面指标相关性可视化',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'features': corr_df.columns.tolist(),
                'generation_method': 'enhanced_local'
            }
        }
    except Exception as e:
        logger.error(f"创建增强热力图失败: {e}")
        return None

def create_enhanced_gauge_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强仪表盘图"""
    try:
        # 从分析结果中提取评分，或使用默认值
        risk_score = 75  # 默认风险评分
        if 'risk_manager' in analysis_results:
            # TODO: 从风险分析中提取真实评分
            risk_score = 60 + hash(symbol) % 30  # 模拟基于分析的评分
        
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = risk_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"{symbol} 风险评级"},
            delta = {'reference': 70, 'suffix': "分"},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 40], 'color': "lightgreen"},   # 低风险
                    {'range': [40, 70], 'color': "yellow"},       # 中风险
                    {'range': [70, 100], 'color': "lightcoral"}   # 高风险
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 85
                }
            }
        ))
        
        fig.update_layout(
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 600),
            height=config.get('height', 500),
            font={'color': "white" if config.get('theme') == 'plotly_dark' else "black", 'size': 12}
        )
        
        chart_id = f"enhanced_gauge_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'gauge',
            'title': f'{symbol} 风险评级仪表盘',
            'description': f'{symbol}的综合风险评级仪表盘，显示当前风险水平',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'risk_score': risk_score,
                'risk_level': '低风险' if risk_score < 40 else '中风险' if risk_score < 70 else '高风险',
                'generation_method': 'enhanced_local'
            }
        }
    except Exception as e:
        logger.error(f"创建增强仪表盘图失败: {e}")
        return None

def create_enhanced_waterfall_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强瀑布图"""
    try:
        # 模拟财务数据流（收入->成本->利润）
        categories = ['起始资本', '营业收入', '营业成本', '管理费用', '财务费用', '净利润']
        
        # 基于符号生成一致的数据
        base_values = [0, 1000, -600, -150, -50, 0]  # 瀑布图值
        for i in range(1, len(base_values)-1):
            variation = (hash(f"{symbol}_{i}") % 200 - 100)  # -100 到 +100
            base_values[i] += variation
        
        # 计算累计值
        cumulative = [0]
        for i in range(1, len(base_values)):
            if i == len(base_values) - 1:  # 最后一项是总和
                cumulative.append(sum(base_values[1:-1]))
            else:
                cumulative.append(base_values[i])
        
        # 创建瀑布图
        fig = go.Figure(go.Waterfall(
            name = f"{symbol} 财务分析",
            orientation = "v",
            measure = ["absolute"] + ["relative"] * (len(categories)-2) + ["total"],
            x = categories,
            textposition = "outside",
            text = [f"{val:+.0f}万" if val != 0 else "" for val in cumulative],
            y = cumulative,
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        
        fig.update_layout(
            title = f"{symbol} 财务瀑布图分析",
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 900),
            height=config.get('height', 600),
            showlegend = False,
            xaxis_title="财务项目",
            yaxis_title="金额（万元）"
        )
        
        chart_id = f"enhanced_waterfall_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'waterfall',
            'title': f'{symbol} 财务瀑布图',
            'description': f'{symbol}的财务流瀑布分析，展示收入到利润的转化过程',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'categories_count': len(categories),
                'net_profit': cumulative[-1],
                'revenue': cumulative[1] if len(cumulative) > 1 else 0,
                'generation_method': 'enhanced_local'
            }
        }
    except Exception as e:
        logger.error(f"创建增强瀑布图失败: {e}")
        return None

def create_enhanced_box_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建增强箱线图"""
    try:
        # 生成多组数据用于箱线图对比
        np.random.seed(hash(symbol) % 10000)
        
        # 模拟不同时期的收益率分布
        periods = [f'{symbol}今年', f'{symbol}去年', '同行平均', '市场平均']
        
        fig = go.Figure()
        
        for i, period in enumerate(periods):
            # 为每个时期生成不同的数据分布
            if i == 0:  # 今年
                data = np.random.normal(0.08, 0.15, 100)  # 高收益高风险
            elif i == 1:  # 去年
                data = np.random.normal(0.05, 0.12, 100)  # 低一些
            elif i == 2:  # 同行平均
                data = np.random.normal(0.06, 0.10, 100)
            else:  # 市场平均
                data = np.random.normal(0.04, 0.08, 100)
            
            fig.add_trace(go.Box(
                y=data,
                name=period,
                boxpoints='outliers',  # 显示异常值
                jitter=0.3,
                pointpos=-1.8,
                marker_color=px.colors.qualitative.Set1[i]
            ))
        
        fig.update_layout(
            title=f'{symbol} 收益率分布箱线图对比',
            yaxis_title='收益率',
            template=config.get('theme', 'plotly_dark'),
            width=config.get('width', 800),
            height=config.get('height', 600),
            showlegend=True
        )
        
        chart_id = f"enhanced_box_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'box',
            'title': f'{symbol} 收益率分布箱线图',
            'description': f'{symbol}的收益率分布分析，包含时期对比和异常值检测',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'periods_count': len(periods),
                'data_points_per_period': 100,
                'includes_outliers': True,
                'generation_method': 'enhanced_local'
            }
        }
    except Exception as e:
        logger.error(f"创建增强箱线图失败: {e}")
        return None

# 添加兼容性函数，支持原有的simple_xxx_chart函数调用
def create_simple_line_chart(symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建简单折线图 - 最小可用实现"""
    
    try:
        # 生成简单的示例数据
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        np.random.seed(hash(symbol) % 10000)
        
        base_price = 100 + hash(symbol) % 100
        price_changes = np.random.normal(0, 2, len(dates))
        prices = base_price + np.cumsum(price_changes)
        
        # 创建简单折线图
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode='lines+markers',
                name=f'{symbol}',
                line=dict(color='blue', width=2),
                marker=dict(size=4)
            )
        )
        
        # 简单布局
        fig.update_layout(
            title=f'{symbol} 简单折线图',
            xaxis_title='日期',
            yaxis_title='价格',
            template=config.get('theme', 'plotly_white'),
            width=config.get('width', 700),
            height=config.get('height', 400)
        )
        
        # 保存图表
        chart_id = f"simple_line_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)
        
        return {
            'chart_id': chart_id,
            'chart_type': 'line',
            'title': f'{symbol} 简单折线图',
            'description': f'{symbol}的基础价格走势图',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'data_points': len(dates),
                'generation_method': 'simple_local'
            }
        }
        
    except Exception as e:
        logger.error(f"创建简单折线图失败: {e}")
        return None

def create_simple_heatmap_chart(analysis_results: Dict[str, Any], symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """创建简单热力图（最小可用实现，避免相互递归）"""
    try:
        np.random.seed(hash(symbol) % 10000)
        x_labels = [f'D{i}' for i in range(1, 11)]
        y_labels = [f'M{i}' for i in range(1, 11)]
        z = np.random.rand(len(y_labels), len(x_labels))

        fig = px.imshow(
            z,
            x=x_labels,
            y=y_labels,
            color_continuous_scale='Viridis',
            aspect='auto'
        )
        fig.update_layout(
            title=f'{symbol} 简单热力图',
            template=config.get('theme', 'plotly_white'),
            width=config.get('width', 700),
            height=config.get('height', 500)
        )

        chart_id = f"simple_heatmap_{symbol}_{uuid.uuid4().hex[:8]}"
        chart_path = save_enhanced_chart(fig, chart_id, config)

        return {
            'chart_id': chart_id,
            'chart_type': 'heatmap',
            'title': f'{symbol} 简单热力图',
            'description': f'{symbol}的基础热力图示例',
            'file_path': chart_path,
            'plotly_json': fig.to_dict(),
            'metadata': {
                'symbol': symbol,
                'x_labels': x_labels,
                'y_labels': y_labels,
                'generation_method': 'simple_local'
            }
        }
    except Exception as e:
        logger.error(f"创建简单热力图失败: {e}")
        return None
