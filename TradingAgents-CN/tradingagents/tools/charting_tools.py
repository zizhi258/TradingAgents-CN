"""
Chart Tools for ChartingArtist
专业图表生成和管理工具集
"""

import os
import json
import uuid
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

from tradingagents.utils.logging_init import get_logger

logger = get_logger("chart_tools")


class ChartGeneratorTools:
    """图表生成器工具类"""
    
    def __init__(self, output_dir: Union[str, Path] = None):
        """初始化图表生成器"""
        self.output_dir = Path(output_dir or "data/attachments/charts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认配置
        self.default_config = {
            "theme": "plotly_dark",
            "width": 800,
            "height": 600,
            "interactive": True,
            "export_format": "html"
        }
        
        # 中文股市颜色配置（红涨绿跌）
        self.colors = {
            "rising": "#FF4444",    # 红色 - 上涨
            "falling": "#00AA00",   # 绿色 - 下跌
            "volume": "#4A90E2",    # 蓝色 - 成交量
            "ma": "#FFD700",        # 金色 - 均线
            "support": "#FF69B4",   # 粉色 - 支撑
            "resistance": "#8A2BE2" # 紫色 - 阻力
        }
        
    def generate_candlestick_chart(
        self, 
        data: pd.DataFrame,
        symbol: str,
        config: Dict[str, Any] = None,
        indicators: List[str] = None
    ) -> Dict[str, Any]:
        """生成专业K线图"""
        
        config = {**self.default_config, **(config or {})}
        indicators = indicators or []
        
        try:
            # 数据验证
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in data.columns for col in required_cols):
                raise ValueError(f"数据必须包含列: {required_cols}")
            
            # 创建子图
            rows = 2 if 'volume' in indicators else 1
            row_heights = [0.7, 0.3] if rows == 2 else [1.0]
            
            fig = make_subplots(
                rows=rows,
                cols=1,
                shared_xaxes=True,
                row_heights=row_heights,
                vertical_spacing=0.03,
                subplot_titles=[f'{symbol} K线图', '成交量'] if rows == 2 else [f'{symbol} K线图']
            )
            
            # K线图
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name=f'{symbol} K线',
                    increasing_line_color=self.colors['rising'],
                    decreasing_line_color=self.colors['falling'],
                    increasing_fillcolor=self.colors['rising'],
                    decreasing_fillcolor=self.colors['falling']
                ),
                row=1, col=1
            )
            
            # 添加均线
            if 'ma' in indicators:
                for period in [5, 10, 20]:
                    if len(data) >= period:
                        ma_data = data['close'].rolling(window=period).mean()
                        fig.add_trace(
                            go.Scatter(
                                x=data.index,
                                y=ma_data,
                                mode='lines',
                                name=f'MA{period}',
                                line=dict(width=1),
                                opacity=0.7
                            ),
                            row=1, col=1
                        )
            
            # 添加成交量
            if 'volume' in indicators and rows == 2:
                colors = [
                    self.colors['rising'] if close >= open else self.colors['falling']
                    for close, open in zip(data['close'], data['open'])
                ]
                
                fig.add_trace(
                    go.Bar(
                        x=data.index,
                        y=data['volume'],
                        name='成交量',
                        marker_color=colors,
                        opacity=0.6
                    ),
                    row=2, col=1
                )
            
            # 添加技术指标
            if 'bollinger' in indicators:
                self._add_bollinger_bands(fig, data, row=1, col=1)
            
            if 'rsi' in indicators:
                self._add_rsi_indicator(fig, data)
            
            # 更新布局
            fig.update_layout(
                title=f'{symbol} 专业K线分析图',
                template=config['theme'],
                xaxis_rangeslider_visible=False,
                width=config['width'],
                height=config['height'],
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            # 保存图表
            chart_info = self._save_chart(fig, f"{symbol}_candlestick", config)
            
            return {
                "success": True,
                "chart_type": "candlestick",
                "chart_info": chart_info,
                "data_points": len(data),
                "indicators_applied": indicators
            }
            
        except Exception as e:
            logger.error(f"K线图生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_technical_analysis_chart(
        self,
        data: pd.DataFrame,
        symbol: str,
        analysis_type: str = "comprehensive",
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成技术分析图表"""
        
        config = {**self.default_config, **(config or {})}
        
        try:
            if analysis_type == "macd":
                return self._generate_macd_chart(data, symbol, config)
            elif analysis_type == "rsi":
                return self._generate_rsi_chart(data, symbol, config)
            elif analysis_type == "bollinger":
                return self._generate_bollinger_chart(data, symbol, config)
            elif analysis_type == "comprehensive":
                return self._generate_comprehensive_technical_chart(data, symbol, config)
            else:
                raise ValueError(f"不支持的技术分析类型: {analysis_type}")
                
        except Exception as e:
            logger.error(f"技术分析图表生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_financial_dashboard(
        self,
        financial_data: Dict[str, Any],
        symbol: str,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成财务仪表板"""
        
        config = {**self.default_config, **(config or {})}
        
        try:
            # 创建4x2子图布局
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=['盈利能力', '偿债能力', '营运能力', '成长能力'],
                specs=[[{"type": "bar"}, {"type": "bar"}],
                       [{"type": "scatter"}, {"type": "bar"}]]
            )
            
            # 盈利能力指标
            profitability = financial_data.get('profitability', {})
            self._add_profitability_chart(fig, profitability, row=1, col=1)
            
            # 偿债能力指标
            solvency = financial_data.get('solvency', {})
            self._add_solvency_chart(fig, solvency, row=1, col=2)
            
            # 营运能力指标
            efficiency = financial_data.get('efficiency', {})
            self._add_efficiency_chart(fig, efficiency, row=2, col=1)
            
            # 成长能力指标
            growth = financial_data.get('growth', {})
            self._add_growth_chart(fig, growth, row=2, col=2)
            
            fig.update_layout(
                title=f'{symbol} 财务分析仪表板',
                template=config['theme'],
                width=config['width'],
                height=config['height'],
                showlegend=False
            )
            
            # 保存图表
            chart_info = self._save_chart(fig, f"{symbol}_financial_dashboard", config)
            
            return {
                "success": True,
                "chart_type": "financial_dashboard",
                "chart_info": chart_info,
                "sections": ["盈利能力", "偿债能力", "营运能力", "成长能力"]
            }
            
        except Exception as e:
            logger.error(f"财务仪表板生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_risk_heatmap(
        self,
        risk_data: Dict[str, Any],
        symbols: List[str],
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成风险热力图"""
        
        config = {**self.default_config, **(config or {})}
        
        try:
            # 构建风险矩阵
            risk_metrics = ['volatility', 'beta', 'max_drawdown', 'var_95', 'sharpe_ratio']
            risk_matrix = []
            
            for symbol in symbols:
                symbol_risks = []
                for metric in risk_metrics:
                    value = risk_data.get(symbol, {}).get(metric, 0)
                    symbol_risks.append(value)
                risk_matrix.append(symbol_risks)
            
            risk_df = pd.DataFrame(risk_matrix, index=symbols, columns=risk_metrics)
            
            # 创建热力图
            fig = go.Figure(data=go.Heatmap(
                z=risk_df.values,
                x=risk_df.columns,
                y=risk_df.index,
                colorscale='RdYlBu_r',
                text=np.round(risk_df.values, 3),
                texttemplate='%{text}',
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title='投资组合风险热力图',
                template=config['theme'],
                width=config['width'],
                height=config['height'],
                xaxis_title='风险指标',
                yaxis_title='资产'
            )
            
            # 保存图表
            chart_info = self._save_chart(fig, "portfolio_risk_heatmap", config)
            
            return {
                "success": True,
                "chart_type": "risk_heatmap",
                "chart_info": chart_info,
                "symbols_count": len(symbols),
                "metrics_count": len(risk_metrics)
            }
            
        except Exception as e:
            logger.error(f"风险热力图生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_sentiment_gauge(
        self,
        sentiment_score: float,
        confidence: float,
        symbol: str,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成情绪仪表盘"""
        
        config = {**self.default_config, **(config or {})}
        
        try:
            # 创建仪表盘图
            fig = go.Figure()
            
            # 主情绪仪表盘
            fig.add_trace(go.Indicator(
                mode="gauge+number+delta",
                value=sentiment_score,
                domain={'x': [0, 0.6], 'y': [0.2, 1]},
                title={'text': f"{symbol} 市场情绪"},
                delta={'reference': 50, 'position': "top"},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': self._get_sentiment_color(sentiment_score)},
                    'steps': [
                        {'range': [0, 20], 'color': "red"},
                        {'range': [20, 40], 'color': "orange"},
                        {'range': [40, 60], 'color': "yellow"},
                        {'range': [60, 80], 'color': "lightgreen"},
                        {'range': [80, 100], 'color': "green"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            # 置信度仪表盘
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=confidence,
                domain={'x': [0.65, 1], 'y': [0.4, 0.8]},
                title={'text': "分析置信度"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 30], 'color': "lightgray"},
                        {'range': [30, 70], 'color': "gray"},
                        {'range': [70, 100], 'color': "lightblue"}
                    ]
                }
            ))
            
            # 情绪分类文本
            sentiment_text = self._get_sentiment_description(sentiment_score)
            fig.add_annotation(
                x=0.3, y=0.1,
                text=f"<b>情绪评级: {sentiment_text}</b>",
                showarrow=False,
                font=dict(size=14)
            )
            
            fig.update_layout(
                title=f'{symbol} 市场情绪分析',
                template=config['theme'],
                width=config['width'],
                height=config['height']
            )
            
            # 保存图表
            chart_info = self._save_chart(fig, f"{symbol}_sentiment_gauge", config)
            
            return {
                "success": True,
                "chart_type": "sentiment_gauge",
                "chart_info": chart_info,
                "sentiment_score": sentiment_score,
                "confidence": confidence,
                "sentiment_level": sentiment_text
            }
            
        except Exception as e:
            logger.error(f"情绪仪表盘生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_correlation_network(
        self,
        correlation_matrix: pd.DataFrame,
        threshold: float = 0.5,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成相关性网络图"""
        
        config = {**self.default_config, **(config or {})}
        
        try:
            # 过滤强相关性
            strong_correlations = []
            symbols = correlation_matrix.index.tolist()
            
            for i in range(len(symbols)):
                for j in range(i + 1, len(symbols)):
                    corr_value = correlation_matrix.iloc[i, j]
                    if abs(corr_value) >= threshold:
                        strong_correlations.append({
                            'source': symbols[i],
                            'target': symbols[j],
                            'correlation': corr_value,
                            'strength': abs(corr_value)
                        })
            
            if not strong_correlations:
                raise ValueError(f"在阈值 {threshold} 下未找到强相关关系")
            
            # 创建网络布局
            import networkx as nx
            
            G = nx.Graph()
            for item in strong_correlations:
                G.add_edge(item['source'], item['target'], weight=item['strength'])
            
            pos = nx.spring_layout(G, k=1, iterations=50)
            
            # 创建边轨迹
            edge_x = []
            edge_y = []
            edge_colors = []
            
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])
                
                # 根据相关性确定颜色
                corr = next(item['correlation'] for item in strong_correlations 
                          if (item['source'] == edge[0] and item['target'] == edge[1]) or
                             (item['source'] == edge[1] and item['target'] == edge[0]))
                color = 'red' if corr > 0 else 'blue'
                edge_colors.append(color)
            
            # 创建节点轨迹
            node_x = [pos[node][0] for node in G.nodes()]
            node_y = [pos[node][1] for node in G.nodes()]
            
            fig = go.Figure()
            
            # 添加边
            fig.add_trace(go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=2, color='gray'),
                hoverinfo='none',
                mode='lines',
                name='相关性连接'
            ))
            
            # 添加节点
            fig.add_trace(go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                hoverinfo='text',
                text=list(G.nodes()),
                textposition="middle center",
                marker=dict(
                    size=30,
                    color='lightblue',
                    line=dict(width=2, color='black')
                ),
                name='资产节点'
            ))
            
            fig.update_layout(
                title='资产相关性网络图',
                template=config['theme'],
                showlegend=False,
                hovermode='closest',
                margin=dict(b=20,l=5,r=5,t=40),
                annotations=[ dict(
                    text=f"显示相关性 >= {threshold} 的资产关系",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002 ,
                    xanchor='left', yanchor='bottom',
                    font=dict(color='gray', size=12)
                )],
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                width=config['width'],
                height=config['height']
            )
            
            # 保存图表
            chart_info = self._save_chart(fig, "correlation_network", config)
            
            return {
                "success": True,
                "chart_type": "correlation_network",
                "chart_info": chart_info,
                "nodes_count": len(G.nodes()),
                "edges_count": len(G.edges()),
                "threshold": threshold
            }
            
        except Exception as e:
            logger.error(f"相关性网络图生成失败: {e}")
            return {"success": False, "error": str(e)}
    
    # 辅助方法
    def _add_bollinger_bands(self, fig, data: pd.DataFrame, row: int, col: int):
        """添加布林带"""
        try:
            period = 20
            if len(data) >= period:
                close_ma = data['close'].rolling(window=period).mean()
                close_std = data['close'].rolling(window=period).std()
                
                upper_band = close_ma + (close_std * 2)
                lower_band = close_ma - (close_std * 2)
                
                fig.add_trace(
                    go.Scatter(
                        x=data.index, y=upper_band,
                        mode='lines', name='布林上轨',
                        line=dict(color='orange', width=1, dash='dash'),
                        opacity=0.7
                    ), row=row, col=col
                )
                
                fig.add_trace(
                    go.Scatter(
                        x=data.index, y=lower_band,
                        mode='lines', name='布林下轨',
                        line=dict(color='orange', width=1, dash='dash'),
                        opacity=0.7,
                        fill='tonexty', fillcolor='rgba(255,165,0,0.1)'
                    ), row=row, col=col
                )
        except Exception as e:
            logger.warning(f"布林带添加失败: {e}")
    
    def _add_rsi_indicator(self, fig, data: pd.DataFrame):
        """添加RSI指标"""
        try:
            rsi = self._calculate_rsi(data['close'])
            
            fig.add_trace(
                go.Scatter(
                    x=data.index, y=rsi,
                    mode='lines', name='RSI',
                    line=dict(color='purple', width=2),
                    yaxis='y2'
                )
            )
            
            # 添加超买超卖线
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5)
            
        except Exception as e:
            logger.warning(f"RSI指标添加失败: {e}")
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _generate_macd_chart(self, data: pd.DataFrame, symbol: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """生成MACD图表"""
        try:
            # 计算MACD
            macd, signal, histogram = self._calculate_macd(data['close'])
            
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                row_heights=[0.7, 0.3],
                subplot_titles=[f'{symbol} 价格', 'MACD']
            )
            
            # 价格线
            fig.add_trace(
                go.Scatter(x=data.index, y=data['close'], mode='lines', name='收盘价'),
                row=1, col=1
            )
            
            # MACD线
            fig.add_trace(
                go.Scatter(x=data.index, y=macd, mode='lines', name='MACD', line=dict(color='blue')),
                row=2, col=1
            )
            
            # 信号线
            fig.add_trace(
                go.Scatter(x=data.index, y=signal, mode='lines', name='Signal', line=dict(color='red')),
                row=2, col=1
            )
            
            # 柱状图
            colors = ['green' if h > 0 else 'red' for h in histogram]
            fig.add_trace(
                go.Bar(x=data.index, y=histogram, name='Histogram', marker_color=colors, opacity=0.6),
                row=2, col=1
            )
            
            fig.update_layout(title=f'{symbol} MACD分析', template=config['theme'])
            
            chart_info = self._save_chart(fig, f"{symbol}_macd", config)
            return {"success": True, "chart_type": "macd", "chart_info": chart_info}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        return macd, signal_line, histogram
    
    def _get_sentiment_color(self, score: float) -> str:
        """根据情绪评分获取颜色"""
        if score >= 80:
            return "green"
        elif score >= 60:
            return "lightgreen"
        elif score >= 40:
            return "yellow"
        elif score >= 20:
            return "orange"
        else:
            return "red"
    
    def _get_sentiment_description(self, score: float) -> str:
        """根据评分获取情绪描述"""
        if score >= 80:
            return "极度乐观"
        elif score >= 60:
            return "乐观"
        elif score >= 40:
            return "中性"
        elif score >= 20:
            return "悲观"
        else:
            return "极度悲观"
    
    def _save_chart(self, fig: go.Figure, chart_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """保存图表到文件"""
        try:
            # 生成唯一ID
            chart_id = f"{chart_name}_{uuid.uuid4().hex[:8]}"
            
            # 根据导出格式保存
            export_format = config.get('export_format', 'html')
            
            if export_format == 'html':
                file_path = self.output_dir / f"{chart_id}.html"
                fig.write_html(str(file_path))
            elif export_format == 'json':
                file_path = self.output_dir / f"{chart_id}.json"
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(fig.to_dict(), f, ensure_ascii=False, indent=2)
            elif export_format == 'png':
                file_path = self.output_dir / f"{chart_id}.png"
                fig.write_image(str(file_path), width=config['width'], height=config['height'])
            elif export_format == 'svg':
                file_path = self.output_dir / f"{chart_id}.svg"
                fig.write_image(str(file_path), format='svg')
            
            return {
                "chart_id": chart_id,
                "file_path": str(file_path),
                "format": export_format,
                "created_at": datetime.now().isoformat(),
                "size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }
            
        except Exception as e:
            logger.error(f"图表保存失败: {e}")
            raise


class ChartManagementTools:
    """图表管理工具类"""
    
    def __init__(self, charts_dir: Union[str, Path] = None):
        self.charts_dir = Path(charts_dir or "data/attachments/charts")
        self.charts_dir.mkdir(parents=True, exist_ok=True)
    
    def cleanup_old_charts(self, retention_days: int = 30) -> Dict[str, Any]:
        """清理旧图表"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            deleted_files = []
            total_size = 0
            
            for chart_file in self.charts_dir.iterdir():
                if chart_file.is_file():
                    file_mtime = datetime.fromtimestamp(chart_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        file_size = chart_file.stat().st_size
                        chart_file.unlink()
                        deleted_files.append(str(chart_file.name))
                        total_size += file_size
            
            return {
                "success": True,
                "deleted_count": len(deleted_files),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "retention_days": retention_days
            }
            
        except Exception as e:
            logger.error(f"清理旧图表失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_chart_statistics(self) -> Dict[str, Any]:
        """获取图表统计信息"""
        try:
            chart_files = list(self.charts_dir.glob("*"))
            
            stats = {
                "total_charts": 0,
                "total_size_mb": 0,
                "chart_types": {},
                "creation_dates": []
            }
            
            for chart_file in chart_files:
                if chart_file.is_file():
                    stats["total_charts"] += 1
                    stats["total_size_mb"] += chart_file.stat().st_size / 1024 / 1024
                    
                    # 提取图表类型
                    parts = chart_file.stem.split('_')
                    chart_type = parts[1] if len(parts) > 1 else "unknown"
                    stats["chart_types"][chart_type] = stats["chart_types"].get(chart_type, 0) + 1
                    
                    # 记录创建时间
                    creation_time = datetime.fromtimestamp(chart_file.stat().st_ctime)
                    stats["creation_dates"].append(creation_time.isoformat())
            
            stats["total_size_mb"] = round(stats["total_size_mb"], 2)
            return {"success": True, "statistics": stats}
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"success": False, "error": str(e)}


# 导出主要类
__all__ = [
    'ChartGeneratorTools',
    'ChartManagementTools'
]