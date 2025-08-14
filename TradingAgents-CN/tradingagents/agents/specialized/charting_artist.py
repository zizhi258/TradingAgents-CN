"""
ChartingArtist Specialized Agent
绘图师智能体 - 专门负责生成专业的金融可视化图表
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from .base_specialized_agent import BaseSpecializedAgent, AgentAnalysisResult
from tradingagents.utils.logging_init import get_logger


class ChartingArtist(BaseSpecializedAgent):
    """绘图师智能体 - 基于分析结果生成专业可视化图表"""
    
    def __init__(self, multi_model_manager, config: Dict[str, Any] = None):
        """
        初始化绘图师智能体
        
        Args:
            multi_model_manager: 多模型管理器实例
            config: 配置参数
        """
        super().__init__(
            agent_role="charting_artist",
            description="基于分析结果生成专业的可视化图表和技术图形",
            multi_model_manager=multi_model_manager,
            config=config
        )
        
        # 绘图师特定配置
        self.chart_config = self._load_chart_config()
        self.output_dir = Path("data/attachments/charts")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # 互动渲染增强配置
        self.inline_js = (
            self.chart_config.get("charting_artist", {})
            .get("chart_settings", {})
            .get("inline_js", True)
        )
        self.fancy_interactions = (
            self.chart_config.get("charting_artist", {})
            .get("chart_settings", {})
            .get("fancy_interactions", True)
        )
        self.enable_animation = (
            self.chart_config.get("charting_artist", {})
            .get("chart_settings", {})
            .get("enable_animation", True)
        )
        self.animation_max_points = int(
            self.chart_config.get("charting_artist", {})
            .get("chart_settings", {})
            .get("animation_max_points", 150)
        )
        ann = (
            self.chart_config.get("charting_artist", {})
            .get("chart_settings", {})
            .get("annotations", {})
        )
        self.annotate_sr = bool(ann.get("support_resistance", True))
        self.annotate_key_levels = bool(ann.get("key_levels", True))
        # 高级参数
        adv = (
            self.chart_config.get("charting_artist", {})
            .get("chart_settings", {})
            .get("advanced", {})
        )
        hover = adv.get("hover_metrics", {}) if isinstance(adv, dict) else {}
        self.hover_pct_change = bool((hover or {}).get("pct_change", True))
        self.hover_ma_spread_periods = (hover or {}).get("ma_spread_periods", [5, 20])
        self.pivot_levels_enabled = bool((adv or {}).get("pivot_levels", True))
        tr = (adv or {}).get("trendline", {})
        self.trendline_enabled = bool((tr or {}).get("enabled", True))
        self.trendline_window = int((tr or {}).get("window", 60))
        
        # 图表生成器映射
        self.chart_generators = {
            "candlestick": self._generate_candlestick_chart,
            "line_chart": self._generate_line_chart, 
            "bar_chart": self._generate_bar_chart,
            "pie_chart": self._generate_pie_chart,
            "scatter_plot": self._generate_scatter_plot,
            "heatmap": self._generate_heatmap,
            "radar_chart": self._generate_radar_chart,
            "gauge_chart": self._generate_gauge_chart,
            "waterfall": self._generate_waterfall_chart,
            "box_plot": self._generate_box_plot
        }
        
        self.logger.info("绘图师智能体初始化完成，支持10种图表类型")
    
    def _build_system_prompt_template(self) -> str:
        """构建系统提示词模板"""
        return """你是一位专业的金融图表绘图师（ChartingArtist），具备以下核心能力：

🎨 **专业技能**
- 深谙各类金融图表的最佳实践
- 精通技术分析图表设计原理
- 了解不同投资者的可视化需求
- 具备数据故事讲述能力

📊 **图表类型专长**
- K线图：价格走势、成交量、技术指标叠加
- 柱状图：财务指标对比、收益分析
- 饼图：资产配置、行业分布、风险占比
- 折线图：趋势分析、业绩变化
- 散点图：相关性分析、风险收益分布
- 热力图：相关性矩阵、行业表现
- 雷达图：综合评分、多维度对比
- 仪表盘：风险评级、置信度显示

🎯 **设计原则**
- 信息传达准确、清晰
- 视觉层次分明，突出重点
- 颜色搭配专业，符合金融惯例
- 交互性强，便于深度探索
- 响应式设计，适配多终端

💡 **分析导向**
- 基于前序分析结果确定图表类型
- 突出关键发现和投资要点
- 辅助投资决策，降低理解成本
- 提供多角度视觉验证

你的任务是分析各智能体的分析结果，选择最合适的可视化方式，生成专业、美观、实用的金融图表。"""

    def _build_analysis_prompt_template(self) -> str:
        """构建分析提示词模板"""
        return """请作为专业绘图师，分析提供的数据和前序分析结果，完成以下任务：

1️⃣ **数据分析与图表选择**
   - 识别数据类型和结构特征
   - 分析前序智能体的核心发现
   - 确定最适合的图表类型组合
   - 评估数据质量和完整性

2️⃣ **可视化方案设计**
   - 设计图表布局和样式方案
   - 确定颜色配色和视觉层次
   - 规划交互功能和用户体验
   - 制定图表组合和展示顺序

3️⃣ **图表代码生成**
   - 生成完整的Plotly图表代码
   - 确保代码可直接执行且无错误
   - 添加适当的注释和说明
   - 优化性能和渲染效果

4️⃣ **专业建议**
   - 解释图表设计的理论依据
   - 提供图表解读指导
   - 建议潜在的改进方向
   - 评估图表的投资参考价值

**注意事项：**
- 优先使用K线图展示价格数据
- 遵循中国股市惯例（红涨绿跌）
- 确保所有图表支持交互缩放
- 代码必须基于提供的真实数据"""

    def get_specialized_task_type(self) -> str:
        """获取专业化的任务类型"""
        return "visualization"

    def validate_input_data(self, data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        try:
            # 检查是否有前序分析结果
            if "analysis_results" not in data:
                self.logger.warning("缺少前序分析结果")
                return False
            
            # 检查是否有可视化的数据源
            required_fields = ["symbol", "analysis_results"]
            for field in required_fields:
                if field not in data:
                    self.logger.warning(f"缺少必要字段: {field}")
                    return False
            
            # 检查分析结果结构
            analysis_results = data["analysis_results"]
            if not isinstance(analysis_results, dict) or len(analysis_results) == 0:
                self.logger.warning("分析结果为空或格式错误")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"输入数据验证失败: {e}")
            return False

    def extract_key_metrics(self, analysis_result: str) -> Dict[str, Any]:
        """从分析结果中提取关键指标"""
        metrics = {
            "chart_types_generated": [],
            "visualization_count": 0,
            "data_points_processed": 0,
            "chart_files_created": [],
            "generation_success_rate": 0.0,
            "interactive_features": [],
            "chart_quality_score": 0.0
        }
        
        try:
            # 解析分析结果中的图表信息
            lines = analysis_result.split('\n')
            chart_count = 0
            
            for line in lines:
                line = line.strip().lower()
                
                # 检测生成的图表类型
                for chart_type in self.chart_generators.keys():
                    if chart_type in line or chart_type.replace('_', ' ') in line:
                        if chart_type not in metrics["chart_types_generated"]:
                            metrics["chart_types_generated"].append(chart_type)
                
                # 统计可视化相关关键词
                viz_keywords = ["图表", "chart", "可视化", "visualization", "plotly", "interactive"]
                if any(keyword in line for keyword in viz_keywords):
                    chart_count += 1
            
            metrics["visualization_count"] = len(metrics["chart_types_generated"])
            metrics["generation_success_rate"] = 1.0 if chart_count > 0 else 0.0
            metrics["chart_quality_score"] = min(0.8 + len(metrics["chart_types_generated"]) * 0.05, 1.0)
            
        except Exception as e:
            self.logger.warning(f"提取图表指标失败: {e}")
        
        return metrics

    def _load_chart_config(self) -> Dict[str, Any]:
        """加载图表配置"""
        try:
            import yaml
            config_path = Path("config/charting_config.yaml")
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                self.logger.warning("图表配置文件不存在，使用默认配置")
        
        except Exception as e:
            self.logger.warning(f"加载图表配置失败: {e}")
        
        # 默认配置
        return {
            "charting_artist": {
                "enabled": os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() == "true",
                "chart_settings": {
                    "default_theme": "plotly_dark",
                    "width": 800,
                    "height": 600,
                    "interactive": True
                }
            }
        }

    def is_enabled(self) -> bool:
        """检查绘图师是否启用"""
        return self.chart_config.get("charting_artist", {}).get("enabled", False)

    def generate_visualizations(self, 
                              symbol: str,
                              analysis_results: Dict[str, Any],
                              market_data: Dict[str, Any] = None,
                              runtime_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        基于分析结果生成可视化图表
        
        Args:
            symbol: 股票代码
            analysis_results: 前序分析结果
            market_data: 市场数据
            
        Returns:
            Dict包含生成的图表信息
        """
        if not self.is_enabled():
            return {"enabled": False, "message": "绘图师功能未启用"}
        
        visualization_results = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "charts_generated": [],
            "total_charts": 0,
            "generation_time": 0,
            "errors": []
        }
        
        start_time = datetime.now()
        
        try:
            # 读取运行时覆写
            runtime_config = runtime_config or {}
            llm_enabled = runtime_config.get(
                "llm_enabled",
                self.chart_config.get("charting_artist", {}).get("llm_enabled", False)
            ) or (os.getenv("CHARTING_ARTIST_LLM_ENABLED", "false").lower() == "true")
            render_mode = runtime_config.get(
                "render_mode",
                self.chart_config.get("charting_artist", {}).get("render_mode", "python")
            )

            # 分析需要生成的图表类型
            chart_plan = self._analyze_chart_requirements(analysis_results, market_data)

            # 生成各类图表（优先尝试LLM，失败回退程序化）
            for chart_spec in chart_plan:
                try:
                    chart_result = None
                    if llm_enabled:
                        chart_result = self._generate_chart_via_llm(
                            chart_type=chart_spec["type"],
                            data=chart_spec["data"],
                            config={**(chart_spec.get("config") or {}), **runtime_config},
                            symbol=symbol,
                            render_mode=render_mode,
                            model_override=runtime_config.get("model_override")
                        )
                    if not chart_result or not chart_result.get("success"):
                        chart_result = self._generate_chart(
                            chart_type=chart_spec["type"],
                            data=chart_spec["data"],
                            config=chart_spec["config"],
                            symbol=symbol
                        )

                    if chart_result["success"]:
                        visualization_results["charts_generated"].append(chart_result)
                    else:
                        visualization_results["errors"].append({
                            "chart_type": chart_spec["type"],
                            "error": chart_result["error"]
                        })

                except Exception as e:
                    self.logger.error(f"生成图表失败 {chart_spec['type']}: {e}")
                    visualization_results["errors"].append({
                        "chart_type": chart_spec["type"],
                        "error": str(e)
                    })
            
            visualization_results["total_charts"] = len(visualization_results["charts_generated"])
            visualization_results["generation_time"] = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )
            
        except Exception as e:
            self.logger.error(f"可视化生成过程失败: {e}")
            visualization_results["errors"].append({"general_error": str(e)})
        
        return visualization_results

    def _generate_chart_via_llm(
        self,
        chart_type: str,
        data: Dict[str, Any],
        config: Dict[str, Any],
        symbol: str,
        render_mode: str = "python",
        model_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """使用LLM（如 Kimi K2）生成图表（Plotly 代码或可嵌入HTML）。"""
        try:
            # 构造提示词
            chart_title_map = {
                "candlestick": "K线图",
                "line_chart": "价格折线图",
                "bar_chart": "财务指标柱状图",
                "pie_chart": "占比饼图",
                "scatter_plot": "散点图",
                "heatmap": "相关性热力图",
                "radar_chart": "雷达图",
                "gauge_chart": "仪表盘",
                "waterfall": "瀑布图",
                "box_plot": "箱线图",
            }

            # 简化数据作为上下文
            safe_context = {
                "symbol": symbol,
                "chart_type": chart_type,
            }
            market_data = data.get("market_data") or {}
            if isinstance(market_data.get("price_data"), dict):
                # 附带前60行OHLC（避免巨大prompt）
                pdict = market_data["price_data"]
                safe_context["price_data_sample"] = {
                    k: (v[:60] if isinstance(v, list) else v) for k, v in pdict.items()
                    if k in ("date", "open", "high", "low", "close", "volume")
                }

            system = (
                "你是专业金融图表绘图师。使用中文标签、Plotly Dark 主题，遵循红涨绿跌习惯。"
            )

            if render_mode == "python":
                instruction = (
                    "仅输出一个Python代码块，不要解释文字。"
                    "代码必须构建变量 fig = plotly.graph_objects.Figure 或由 plotly.express 返回。"
                    "不要调用 fig.show()。不要包含导入语句；你可以直接使用变量 go, px, pd。"
                    "基于给定的 price_data_sample 或分析结果构造数据。"
                )
            else:
                instruction = (
                    "仅输出一个HTML代码块，不要解释文字。"
                    "HTML需可直接嵌入，包含渲染所需的Plotly脚本（可内联）。"
                    "标题使用中文，主题接近深色。"
                )

            user = {
                "task": f"为 {symbol} 生成 {chart_title_map.get(chart_type, chart_type)}",
                "render_mode": render_mode,
                "context": safe_context,
                "style": {
                    "title": f"{symbol} {chart_title_map.get(chart_type, chart_type)}",
                    "theme": (config.get("theme") or self.chart_config.get("charting_artist", {}).get("chart_settings", {}).get("default_theme", "plotly_dark")),
                    "width": int(config.get("width", 800)),
                    "height": int(config.get("height", 600)),
                },
            }

            # 执行任务
            task_prompt = (
                f"{system}\n\n{instruction}\n\n数据与上下文(精简):\n" + json.dumps(user, ensure_ascii=False)
            )

            task_result = self.multi_model_manager.execute_task(
                agent_role=self.agent_role,
                task_prompt=task_prompt,
                task_type=self.get_specialized_task_type(),
                complexity_level="medium",
                context={},
                model_override=model_override,
            )

            if not task_result.success or not task_result.result:
                return {"success": False, "error": task_result.error_message or "LLM生成失败"}

            content = task_result.result

            if render_mode == "python":
                code = self._extract_code_block(content, lang_hint=("python",))
                if not code:
                    return {"success": False, "error": "未检测到Python代码块"}
                fig = self._execute_plotly_code_safely(code)
                if not isinstance(fig, go.Figure):
                    return {"success": False, "error": "代码未生成有效的Plotly Figure(fig)"}

                # 保存HTML
                chart_filename = f"{symbol}_{chart_type}_{uuid.uuid4().hex[:8]}.html"
                chart_path = self.output_dir / chart_filename
                fig.write_html(
                    str(chart_path),
                    include_plotlyjs="inline" if self.inline_js else "cdn",
                    full_html=True,
                    config={
                        "responsive": True,
                        "displaylogo": False,
                        "modeBarButtonsToRemove": [
                            "resetViews",
                            "resetScale2d",
                        ],
                    },
                )

                # 额外导出静态PNG（用于PDF/DOC嵌入），若kaleido可用
                image_filename = None
                try:
                    image_filename = chart_filename.replace('.html', '.png')
                    image_path = self.output_dir / image_filename
                    fig.write_image(str(image_path))
                except Exception as _e_img:
                    image_filename = None
                    self.logger.debug(f"绘图师静态图片导出失败(可忽略): {_e_img}")

                return {
                    "success": True,
                    "chart_type": chart_type,
                    "filename": chart_filename,
                    "path": str(chart_path),
                    "image_filename": image_filename,
                    "image_path": (str(self.output_dir / image_filename) if image_filename else None),
                    "title": chart_title_map.get(chart_type, chart_type),
                    "description": f"{symbol} 的 {chart_title_map.get(chart_type, chart_type)} (LLM生成)",
                    "model_used": task_result.model_used.name if task_result.model_used else None,
                }

            else:
                html = self._extract_code_block(content, lang_hint=("html",)) or content.strip()
                if not html or ("<html" not in html and "<div" not in html and "<script" not in html):
                    return {"success": False, "error": "未检测到可嵌入的HTML内容"}

                chart_filename = f"{symbol}_{chart_type}_{uuid.uuid4().hex[:8]}.html"
                chart_path = self.output_dir / chart_filename
                chart_path.write_text(html, encoding="utf-8")
                
                return {
                    "success": True,
                    "chart_type": chart_type,
                    "filename": chart_filename,
                    "path": str(chart_path),
                    "title": chart_title_map.get(chart_type, chart_type),
                    "description": f"{symbol} 的 {chart_title_map.get(chart_type, chart_type)} (LLM生成HTML)",
                    "model_used": task_result.model_used.name if task_result.model_used else None,
                }

        except Exception as e:
            self.logger.warning(f"LLM绘图失败({chart_type}): {e}")
            return {"success": False, "error": str(e)}

    def _extract_code_block(self, text: str, lang_hint: tuple = ("python", "py")) -> Optional[str]:
        """提取三反引号代码块。"""
        try:
            import re
            pattern = r"```(?:%s)?\s*([\s\S]*?)```" % ("|".join(lang_hint))
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
            return None
        except Exception:
            return None

    def _execute_plotly_code_safely(self, code: str) -> Optional[go.Figure]:
        """在受限环境中执行Plotly代码，要求生成变量 fig。"""
        # 受限执行环境
        minimal_builtins = {
            "len": len,
            "range": range,
            "min": min,
            "max": max,
            "sum": sum,
            "abs": abs,
        }
        safe_globals = {
            "__builtins__": minimal_builtins,
            "go": go,
            "px": px,
            "pd": pd,
            "json": json,
        }
        safe_locals: Dict[str, Any] = {}
        try:
            exec(compile(code, filename="<llm_plotly>", mode="exec"), safe_globals, safe_locals)
            fig = safe_locals.get("fig") or safe_globals.get("fig")
            return fig
        except Exception as e:
            self.logger.warning(f"安全执行Plotly代码失败: {e}")
            return None

    def _analyze_chart_requirements(self, 
                                  analysis_results: Dict[str, Any],
                                  market_data: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """分析图表需求并返回图表计划"""
        chart_plan = []
        
        # 构建传递给图表生成器的完整数据结构
        full_data = {
            "analysis_results": analysis_results,
            "market_data": market_data or {}
        }
        
        try:
            # 总是生成基础图表
            # 1. K线图 (优先级最高)
            chart_plan.append({
                "type": "candlestick",
                "data": full_data,
                "config": {"indicators": True, "volume": True},
                "priority": "high"
            })
            
            # 2. 价格折线图
            chart_plan.append({
                "type": "line_chart", 
                "data": full_data,
                "config": {"moving_averages": True},
                "priority": "medium"
            })
            
            # 基于分析结果确定其他图表类型
            if "fundamental_expert" in analysis_results:
                # 基本面分析：财务指标图
                chart_plan.append({
                    "type": "bar_chart",
                    "data": full_data,
                    "config": {"metrics": ["revenue", "profit", "pe_ratio"]},
                    "priority": "medium"
                })
                
            if "risk_manager" in analysis_results:
                # 风险分析：雷达图
                chart_plan.append({
                    "type": "radar_chart",
                    "data": full_data,
                    "config": {"dimensions": ["volatility", "beta", "var"]},
                    "priority": "medium"
                })
            
        except Exception as e:
            self.logger.warning(f"分析图表需求失败: {e}")
            # 即使失败也要返回基础图表
            if not chart_plan:
                chart_plan = [{
                    "type": "candlestick",
                    "data": full_data,
                    "config": {},
                    "priority": "high"
                }]
        
        return chart_plan

    def _generate_chart(self, 
                       chart_type: str,
                       data: Dict[str, Any],
                       config: Dict[str, Any],
                       symbol: str) -> Dict[str, Any]:
        """生成单个图表"""
        try:
            if chart_type not in self.chart_generators:
                return {
                    "success": False,
                    "error": f"不支持的图表类型: {chart_type}"
                }
            
            # 调用对应的图表生成器
            generator = self.chart_generators[chart_type]
            chart_fig = generator(data, config, symbol)
            
            # 保存HTML
            chart_filename = f"{symbol}_{chart_type}_{uuid.uuid4().hex[:8]}.html"
            chart_path = self.output_dir / chart_filename
            chart_fig.write_html(
                str(chart_path),
                include_plotlyjs="inline" if self.inline_js else "cdn",
                full_html=True,
                config={
                    "responsive": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": [
                        "resetViews",
                        "resetScale2d",
                    ],
                },
            )

            # 额外导出静态PNG（若kaleido可用）
            image_filename = None
            try:
                image_filename = chart_filename.replace('.html', '.png')
                image_path = self.output_dir / image_filename
                chart_fig.write_image(str(image_path))
            except Exception as _e_img:
                image_filename = None
                self.logger.debug(f"绘图师静态图片导出失败(可忽略): {_e_img}")

            return {
                "success": True,
                "chart_type": chart_type,
                "filename": chart_filename,
                "path": str(chart_path),
                "image_filename": image_filename,
                "image_path": (str(self.output_dir / image_filename) if image_filename else None),
                "title": chart_fig.layout.title.text if chart_fig.layout.title else f"{symbol} {chart_type}",
                "description": f"{symbol}的{chart_type}可视化分析"
            }
            
        except Exception as e:
            self.logger.error(f"生成{chart_type}图表失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _prepare_price_df(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        从分析结果或市场数据中提取标准价格DataFrame
        
        Args:
            data: 包含market_data和analysis_results的数据字典
            
        Returns:
            pd.DataFrame: 标准格式的价格数据，包含date/open/high/low/close/volume列
        """
        try:
            # 尝试从market_data中获取价格数据
            market_data = data.get('market_data', {})
            price_data = market_data.get('price_data')
            
            if price_data and isinstance(price_data, dict):
                # 处理字典格式的价格数据
                if 'date' in price_data or 'trade_date' in price_data:
                    df_dict = {}
                    
                    # 统一键名映射
                    key_mapping = {
                        'date': ['date', 'trade_date', 'timestamp'],
                        'open': ['open', 'topen', 'opening_price'],
                        'high': ['high', 'thigh', 'highest_price'],  
                        'low': ['low', 'tlow', 'lowest_price'],
                        'close': ['close', 'tclose', 'closing_price'],
                        'volume': ['volume', 'tvol', 'trading_volume', 'vol']
                    }
                    
                    # 提取数据
                    for standard_key, possible_keys in key_mapping.items():
                        for key in possible_keys:
                            if key in price_data:
                                df_dict[standard_key] = price_data[key]
                                break
                        
                        # 如果没有找到对应的键，使用默认值
                        if standard_key not in df_dict:
                            if standard_key == 'date':
                                # 生成默认日期序列
                                df_dict[standard_key] = pd.date_range('2024-01-01', periods=30, freq='D')
                            elif standard_key == 'volume':
                                # 使用默认成交量
                                df_dict[standard_key] = [1000000] * 30
                            else:
                                # 价格相关字段使用默认值
                                df_dict[standard_key] = [100] * 30
                    
                    # 创建DataFrame
                    df = pd.DataFrame(df_dict)
                    
                    # 确保日期列为datetime类型
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                    
                    # 确保数值列为float类型
                    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
                    for col in numeric_cols:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(100)
                    
                    self.logger.debug(f"成功从market_data提取{len(df)}条价格记录")
                    return df
            
            # 尝试从analysis_results中获取价格信息
            analysis_results = data.get('analysis_results', {})
            if analysis_results and isinstance(analysis_results, dict):
                # 检查是否有市场分析结果
                market_report = analysis_results.get('market_report')
                if market_report and isinstance(market_report, str):
                    # 尝试从市场报告中提取价格信息（简化处理）
                    self.logger.debug("从market_report中提取价格信息")
                    # TODO: 实现从文本报告中提取结构化数据的逻辑
            
            # 如果都没有找到，返回模拟数据但记录警告
            self.logger.warning("未找到真实价格数据，使用模拟数据作为降级方案")
            return self._generate_mock_price_data()
            
        except Exception as e:
            self.logger.error(f"提取价格数据失败: {e}，使用模拟数据")
            return self._generate_mock_price_data()
    
    def _generate_mock_price_data(self) -> pd.DataFrame:
        """生成模拟价格数据作为降级方案"""
        dates = pd.date_range('2024-01-01', periods=60, freq='D')
        
        # 生成更真实的价格走势
        base_price = 100
        prices = []
        for i in range(len(dates)):
            if i == 0:
                price = base_price
            else:
                # 添加随机波动
                change = (hash(str(dates[i])) % 1000 - 500) / 10000  # -0.05 到 0.05
                price = prices[-1] * (1 + change)
            prices.append(max(price, 10))  # 确保价格为正
        
        return pd.DataFrame({
            'date': dates,
            'open': [p * 0.99 for p in prices],
            'high': [p * 1.02 for p in prices], 
            'low': [p * 0.98 for p in prices],
            'close': prices,
            'volume': [1000000 + (i * 50000) + (hash(str(dates[i])) % 500000) for i in range(len(dates))]
        })

    def _generate_candlestick_chart(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成K线图"""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.03,
            subplot_titles=[f'{symbol} 价格走势', '成交量']
        )
        
        # 使用真实数据
        df = self._prepare_price_df(data)
        
        # K线图
        fig.add_trace(
            go.Candlestick(
                x=df['date'],
                open=df['open'],
                high=df['high'], 
                low=df['low'],
                close=df['close'],
                name=f'{symbol} K线',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ),
            row=1, col=1
        )
        
        # 移动平均线（可选）
        try:
            ma_periods = self.chart_config.get("technical_indicators", {}).get("ma_periods", [5, 10, 20])
            if self.chart_config.get("charting_artist", {}).get("chart_settings", {}).get("show_ma", True):
                for p in ma_periods:
                    if len(df) >= p:
                        fig.add_trace(
                            go.Scatter(
                                x=df['date'],
                                y=df['close'].rolling(p).mean(),
                                name=f'MA{p}',
                                mode='lines',
                                line=dict(width=1.5),
                            ),
                            row=1, col=1
                        )
        except Exception:
            pass

        # 成交量（按红涨绿跌着色）
        try:
            up = df['close'] >= df['open']
            vol_colors = up.map({True: '#26a69a', False: '#ef5350'})
        except Exception:
            vol_colors = 'rgba(158,202,225,0.6)'
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['volume'],
                name='成交量',
                marker_color=vol_colors
            ),
            row=2, col=1
        )

        # 交互与布局增强
        theme = self.chart_config.get("charting_artist", {}).get("chart_settings", {}).get("default_theme", "plotly_dark")
        fig.update_layout(
            title=f'{symbol} K线图分析 - {len(df)}个数据点',
            template=theme,
            height=720,
            hovermode='x unified',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        if self.fancy_interactions:
            fig.update_xaxes(
                rangeselector=dict(
                    buttons=list([
                        dict(count=5, label="5D", step="day", stepmode="backward"),
                        dict(count=1, label="1M", step="month", stepmode="backward"),
                        dict(count=3, label="3M", step="month", stepmode="backward"),
                        dict(step="all")
                    ])
                ),
                rangeslider=dict(visible=True),
                showspikes=True,
                spikemode='across',
                spikesnap='cursor',
                row=1, col=1
            )
            # 周末rangebreaks
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], row=1, col=1)
        else:
            fig.update_xaxes(rangeslider=dict(visible=False), row=1, col=1)

        # Hover 模板与自定义数据（涨跌幅、均线差）
        try:
            pct_list = []
            spread_list = []
            p1, p2 = None, None
            if isinstance(self.hover_ma_spread_periods, (list, tuple)) and len(self.hover_ma_spread_periods) >= 2:
                p1, p2 = int(self.hover_ma_spread_periods[0]), int(self.hover_ma_spread_periods[1])
            prev_close = df['close'].shift(1)
            for i in range(len(df)):
                # pct change
                if self.hover_pct_change and prev_close.iloc[i] and prev_close.iloc[i] != 0:
                    pct = (df['close'].iloc[i] - prev_close.iloc[i]) / prev_close.iloc[i] * 100.0
                else:
                    pct = None
                # MA spread
                if p1 and p2 and i >= max(p1, p2) - 1:
                    m1 = df['close'].rolling(p1).mean().iloc[i]
                    m2 = df['close'].rolling(p2).mean().iloc[i]
                    spread = m1 - m2 if m1 is not None and m2 is not None else None
                else:
                    spread = None
                pct_list.append(pct)
                spread_list.append(spread)

            # 将两列打包成 customdata
            customdata = [[pct_list[i], spread_list[i]] for i in range(len(df))]
            for trc in fig.data:
                if isinstance(trc, go.Candlestick):
                    trc.customdata = customdata
                    trc.hovertemplate = (
                        "日期=%{x|%Y-%m-%d}<br>"
                        "开=%{open:.2f} 高=%{high:.2f} 低=%{low:.2f} 收=%{close:.2f}<br>"
                        + ("涨跌=%{customdata[0]:+.2f}%<br>" if self.hover_pct_change else "")
                        + ("MA差=%{customdata[1]:.2f}<br>" if p1 and p2 else "")
                        + "<extra></extra>"
                    )
                elif isinstance(trc, go.Bar) and trc.name == '成交量':
                    trc.hovertemplate = ("日期=%{x|%Y-%m-%d}<br>量=%{y:,}<extra></extra>")
        except Exception:
            pass

        # 自动标注 支撑/阻力/关键价位/枢轴点/趋势线
        try:
            if self.annotate_sr and len(df) >= 10:
                win = min(len(df), 60)
                support = float(df['low'].tail(win).min())
                resistance = float(df['high'].tail(win).max())
                x0 = df['date'].min(); x1 = df['date'].max()
                # 支撑线
                fig.add_shape(type='line', x0=x0, x1=x1, y0=support, y1=support,
                              xref='x1', yref='y1', line=dict(color='#26a69a', width=1, dash='dot'))
                fig.add_annotation(x=x1, y=support, xref='x1', yref='y1',
                                   text=f"支撑位 {support:.2f}", showarrow=False,
                                   font=dict(color='#26a69a'), xanchor='left', yanchor='bottom')
                # 阻力线
                fig.add_shape(type='line', x0=x0, x1=x1, y0=resistance, y1=resistance,
                              xref='x1', yref='y1', line=dict(color='#ef5350', width=1, dash='dot'))
                fig.add_annotation(x=x1, y=resistance, xref='x1', yref='y1',
                                   text=f"阻力位 {resistance:.2f}", showarrow=False,
                                   font=dict(color='#ef5350'), xanchor='left', yanchor='top')
            if self.annotate_key_levels and len(df) >= 1:
                last_close = float(df['close'].iloc[-1])
                x0 = df['date'].min(); x1 = df['date'].max()
                fig.add_shape(type='line', x0=x0, x1=x1, y0=last_close, y1=last_close,
                              xref='x1', yref='y1', line=dict(color='#ffa726', width=1, dash='dash'))
                fig.add_annotation(x=x1, y=last_close, xref='x1', yref='y1',
                                   text=f"收 {last_close:.2f}", showarrow=False,
                                   font=dict(color='#ffa726'), xanchor='left', yanchor='middle')
            # 枢轴点（经典法）
            if self.pivot_levels_enabled and len(df) >= 2:
                H = float(df['high'].iloc[-2])
                L = float(df['low'].iloc[-2])
                C = float(df['close'].iloc[-2])
                P = (H + L + C) / 3
                R1 = 2 * P - L
                S1 = 2 * P - H
                x0 = df['date'].min(); x1 = df['date'].max()
                for level, name, color, ya in [
                    (P, 'P', '#90caf9', 'middle'),
                    (R1, 'R1', '#ef5350', 'bottom'),
                    (S1, 'S1', '#26a69a', 'top'),
                ]:
                    fig.add_shape(type='line', x0=x0, x1=x1, y0=level, y1=level,
                                  xref='x1', yref='y1', line=dict(color=color, width=1, dash='dot'))
                    fig.add_annotation(x=x1, y=level, xref='x1', yref='y1', text=f"{name} {level:.2f}",
                                       showarrow=False, font=dict(color=color), xanchor='left', yanchor=ya)
            # 简单趋势线（回归）
            if self.trendline_enabled and len(df) >= 5:
                n = min(self.trendline_window, len(df))
                y = list(df['close'].tail(n))
                x_idx = list(range(n))
                sx = sum(x_idx); sy = sum(y)
                sxx = sum(i*i for i in x_idx); sxy = sum(i*y[i] for i in range(n))
                denom = (n * sxx - sx * sx) or 1
                slope = (n * sxy - sx * sy) / denom
                intercept = (sy - slope * sx) / n
                y0 = intercept
                y1 = slope * (n - 1) + intercept
                dates_tail = list(df['date'].tail(n))
                fig.add_trace(go.Scatter(x=[dates_tail[0], dates_tail[-1]], y=[y0, y1],
                                         mode='lines', name='趋势线', line=dict(color='#ab47bc', dash='dash')),
                              row=1, col=1)
        except Exception:
            pass

        return fig

    def _generate_line_chart(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成折线图（支持HTML动画）"""
        df = self._prepare_price_df(data)
        theme = self.chart_config.get("charting_artist", {}).get("chart_settings", {}).get("default_theme", "plotly_dark")
        if self.enable_animation and len(df) <= self.animation_max_points:
            # 构造简单时间步动画（HTML端展示）
            df2 = df[['date', 'close']].copy()
            df2 = df2.sort_values('date').reset_index(drop=True)
            df2['step'] = df2.index.astype(int)
            try:
                fig = px.line(df2, x='date', y='close', animation_frame='step', title=f'{symbol} 价格走势（动画）')
                fig.update_layout(template=theme, hovermode='x')
                return fig
            except Exception:
                pass  # 回退到静态
        # 静态折线
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['close'], mode='lines+markers', name=f'{symbol}价格',
            line=dict(color='#1f77b4', width=2), marker=dict(size=4)
        ))
        if len(df) >= 20:
            fig.add_trace(go.Scatter(x=df['date'], y=df['close'].rolling(20).mean(), mode='lines', name='MA20', line=dict(color='orange', dash='dash')))
        if len(df) >= 50:
            fig.add_trace(go.Scatter(x=df['date'], y=df['close'].rolling(50).mean(), mode='lines', name='MA50', line=dict(color='red', dash='dot')))
        fig.update_layout(title=f'{symbol} 价格走势分析 - {len(df)}个数据点', xaxis_title='日期', yaxis_title='价格', template=theme, hovermode='x')
        return fig

    def _generate_bar_chart(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成柱状图"""
        fig = go.Figure()

        # 优先使用真实基本面数据
        metrics_map = self._extract_fundamental_metrics(data)
        if metrics_map:
            metrics = list(metrics_map.keys())
            values = list(metrics_map.values())
        else:
            # 示例数据（降级）
            metrics = ['营收(亿)', '净利润(亿)', 'ROE(%)', 'ROA(%)', '负债率(%)']
            values = [1000, 200, 15.5, 8.2, 35.6]

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        fig.add_trace(go.Bar(
            x=metrics,
            y=values,
            marker_color=colors[:len(metrics)],
            text=[
                f"{v:.1f}%" if '(%)' in m or '率' in m or '比' in m else f"{v:.1f}"
                for m, v in zip(metrics, values)
            ],
            textposition='auto',
            name='基本面指标'
        ))

        fig.update_layout(
            title=f'{symbol} 关键财务指标',
            xaxis_title='指标',
            yaxis_title='数值',
            template='plotly_dark'
        )

        return fig

    def _extract_fundamental_metrics(self, data: Dict[str, Any]) -> Dict[str, float]:
        """从 market_data 或 analysis_results 提取可视化用的基本面指标

        返回键值均为可绘制的数值；常见来源键进行容错映射。
        """
        metrics: Dict[str, float] = {}
        try:
            # 1) market_data -> fundamentals
            md = (data or {}).get('market_data') or {}
            fundamentals = md.get('fundamentals') or md.get('fundamental_data') or {}
            candidates = {}
            if isinstance(fundamentals, dict):
                candidates = fundamentals

            # 2) analysis_results -> fundamental_expert (结构化或半结构化)
            ar = (data or {}).get('analysis_results') or {}
            fund_report = ar.get('fundamental_expert') or ar.get('fundamentals_report') or {}
            if isinstance(fund_report, dict):
                # 直接并入候选
                candidates = {**candidates, **fund_report}

            # 数值提取和常见字段映射
            def pick(keys: list[str], label: str, scale: float = 1.0):
                for k in keys:
                    if k in candidates and isinstance(candidates[k], (int, float)):
                        metrics[label] = float(candidates[k]) * scale
                        return True
                return False

            # 尝试提取营收、净利润、ROE、ROA、负债率
            pick(['revenue', '营业收入', '营收'], '营收(亿)', scale=1.0)
            pick(['net_profit', '净利润', 'profit'], '净利润(亿)', scale=1.0)
            pick(['roe', 'ROE', '净资产收益率'], 'ROE(%)')
            pick(['roa', 'ROA', '资产回报率'], 'ROA(%)')
            pick(['debt_ratio', '资产负债率', '负债率'], '负债率(%)')

            # 过滤掉非数值或NaN
            metrics = {k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))}
            return metrics
        except Exception:
            return {}

    def _generate_pie_chart(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成饼图"""
        fig = go.Figure()
        
        # 示例行业分布数据
        sectors = ['科技', '金融', '医疗', '消费', '工业']
        values = [35, 25, 15, 15, 10]
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc']
        
        fig.add_trace(go.Pie(
            labels=sectors,
            values=values,
            hole=0.4,
            marker=dict(colors=colors),
            textinfo='label+percent',
            textposition='auto'
        ))
        
        fig.update_layout(
            title=f'{symbol} 行业分布分析',
            template='plotly_dark'
        )
        
        return fig

    def _generate_scatter_plot(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成散点图"""
        fig = go.Figure()
        
        # 示例风险收益数据
        returns = [i + (i % 5) * 2 for i in range(20)]
        risks = [5 + (i % 8) for i in range(20)]
        
        fig.add_trace(go.Scatter(
            x=risks,
            y=returns,
            mode='markers',
            marker=dict(
                size=10,
                color=returns,
                colorscale='Viridis',
                showscale=True
            ),
            text=[f'资产{i+1}' for i in range(20)],
            name='风险收益分布'
        ))
        
        fig.update_layout(
            title=f'{symbol} 风险收益分析',
            xaxis_title='风险水平',
            yaxis_title='预期收益',
            template='plotly_dark'
        )
        
        return fig

    def _generate_heatmap(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成热力图"""
        import numpy as np
        
        # 示例相关性矩阵
        assets = ['股票A', '股票B', '股票C', '股票D', '股票E']
        correlation_matrix = np.random.rand(5, 5)
        np.fill_diagonal(correlation_matrix, 1)  # 对角线为1
        
        fig = go.Figure(data=go.Heatmap(
            z=correlation_matrix,
            x=assets,
            y=assets,
            colorscale='RdYlBu',
            reversescale=True,
            text=np.round(correlation_matrix, 2),
            texttemplate="%{text}",
            textfont={"size": 10}
        ))
        
        fig.update_layout(
            title=f'{symbol} 相关性热力图',
            template='plotly_dark'
        )
        
        return fig

    def _generate_radar_chart(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成雷达图"""
        fig = go.Figure()
        
        # 示例多维度评分
        dimensions = ['盈利能力', '成长性', '估值', '质量', '动量', '流动性']
        scores = [75, 85, 60, 90, 70, 80]
        
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=dimensions,
            fill='toself',
            name=f'{symbol} 综合评分',
            marker_color='rgba(31, 119, 180, 0.6)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )),
            title=f'{symbol} 多维度评估雷达图',
            template='plotly_dark'
        )
        
        return fig

    def _generate_gauge_chart(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成仪表盘图"""
        fig = go.Figure()
        
        # 示例风险评分
        risk_score = data.get('risk_score', 65)
        
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=risk_score,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"{symbol} 风险评级"},
            delta={'reference': 50},
            gauge={
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 30], 'color': "lightgray"},
                    {'range': [30, 70], 'color': "gray"},
                    {'range': [70, 100], 'color': "lightgray"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        fig.update_layout(
            template='plotly_dark',
            height=400
        )
        
        return fig

    def _generate_waterfall_chart(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成瀑布图"""
        fig = go.Figure()
        
        # 示例利润分解数据
        categories = ['营收', '营业成本', '管理费用', '财务费用', '税费', '净利润']
        values = [1000, -600, -150, -50, -80, 120]
        
        fig.add_trace(go.Waterfall(
            name=f'{symbol} 利润分析',
            orientation="v",
            measure=["relative", "relative", "relative", "relative", "relative", "total"],
            x=categories,
            y=values,
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        
        fig.update_layout(
            title=f'{symbol} 利润结构瀑布图',
            template='plotly_dark'
        )
        
        return fig

    def _generate_box_plot(self, data: Dict[str, Any], config: Dict[str, Any], symbol: str) -> go.Figure:
        """生成箱线图"""
        import numpy as np
        
        fig = go.Figure()
        
        # 示例收益率分布数据
        returns_data = np.random.normal(0.05, 0.15, 100)  # 正态分布收益率
        
        fig.add_trace(go.Box(
            y=returns_data,
            name=f'{symbol} 收益率分布',
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8,
            marker_color='rgb(107,174,214)'
        ))
        
        fig.update_layout(
            title=f'{symbol} 收益率分布箱线图',
            yaxis_title='收益率',
            template='plotly_dark'
        )
        
        return fig

    def _extract_financial_metrics(self, fundamental_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """从基本面分析中提取财务指标"""
        # 这里应该从实际的基本面分析结果中提取数据
        return {
            "revenue": 1000,
            "profit": 200,
            "pe_ratio": 15.5,
            "pb_ratio": 2.1,
            "roe": 18.5
        }

    def _extract_risk_metrics(self, risk_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """从风险分析中提取风险指标"""
        # 这里应该从实际的风险分析结果中提取数据
        return {
            "risk_score": 65,
            "volatility": 0.25,
            "beta": 1.2,
            "var": 0.08,
            "max_drawdown": 0.15
        }

    def get_chart_summary(self, visualization_results: Dict[str, Any]) -> str:
        """生成图表摘要"""
        if not visualization_results.get("charts_generated"):
            return "未生成任何图表"
        
        chart_types = [chart["chart_type"] for chart in visualization_results["charts_generated"]]
        total_charts = len(chart_types)
        generation_time = visualization_results.get("generation_time", 0) / 1000
        
        summary = f"""
📊 **图表生成摘要**

🎯 **生成统计**
- 总计生成: {total_charts} 张图表
- 图表类型: {', '.join(set(chart_types))}
- 生成耗时: {generation_time:.1f} 秒

📈 **图表清单**
"""
        
        for i, chart in enumerate(visualization_results["charts_generated"], 1):
            summary += f"{i}. {chart.get('title', chart['chart_type'])} ({chart['chart_type']})\n"
        
        if visualization_results.get("errors"):
            summary += f"\n⚠️ **生成错误**: {len(visualization_results['errors'])} 个"
        
        return summary
