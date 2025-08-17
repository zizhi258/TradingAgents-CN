"""
专业智能体模块
包含各种专业分析智能体，用于多模型协作分析
"""

import re
from typing import Any

# 导入基类
from .base_specialized_agent import AgentAnalysisResult, BaseSpecializedAgent
from .charting_artist import ChartingArtist
from .chief_decision_officer import ChiefDecisionOfficer
from .chief_writer import ChiefWriter
from .fundamental_expert import FundamentalExpert

# 导入具体的专业智能体
from .news_hunter import NewsHunter


class TechnicalAnalyst(BaseSpecializedAgent):
    """技术分析师智能体"""

    def __init__(self, multi_model_manager, config: dict[str, Any] = None):
        super().__init__(
            agent_role="technical_analyst",
            description="技术分析专家，专注于图表分析、趋势识别和价格预测",
            multi_model_manager=multi_model_manager,
            config=config,
        )

        self.key_indicators = {
            "trend": ["SMA", "EMA", "趋势线", "MACD"],
            "momentum": ["RSI", "CCI", "Stochastic", "Williams %R"],
            "volume": ["成交量", "OBV", "Volume Profile"],
            "volatility": ["布林带", "ATR", "VIX"],
            "patterns": ["头肩顶", "双底", "三角形", "楔形"],
        }

    def _build_system_prompt_template(self) -> str:
        # 允许从角色库覆盖
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("technical_analyst", "system_prompt")
            if custom:
                return custom
        except Exception:
            pass
        return """你是一名专业的技术分析师，具备以下核心能力：

📈 **技术分析专长**
- 图表形态识别和分析
- 技术指标计算和解读
- 支撑阻力位判断
- 趋势方向和强度评估

🔍 **分析工具**
- 移动平均线系统分析
- 动量指标(RSI、MACD、KDJ)
- 成交量分析
- 布林带和价格通道
- 经典图表形态

📊 **预测能力**
- 短期价格走势预测
- 关键价位识别
- 买卖信号生成
- 风险回报比评估

你的分析应该客观、基于数据，提供可操作的交易建议。"""

    def _build_analysis_prompt_template(self) -> str:
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("technical_analyst", "analysis_prompt_template")
            if custom:
                return custom
        except Exception:
            pass
        return """请对提供的技术数据进行专业的技术分析：

🎯 **分析重点**
1. 当前趋势方向和强度
2. 关键支撑和阻力位
3. 技术指标信号
4. 图表形态特征
5. 成交量配合情况

📈 **技术预测**
- 短期价格目标位
- 止损和止盈建议
- 入场时机判断
- 风险预警信号"""

    def get_specialized_task_type(self) -> str:
        return "technical_analysis"

    def validate_input_data(self, data: dict[str, Any]) -> bool:
        required_fields = ["price_data"]
        return all(field in data and data[field] for field in required_fields)

    def extract_key_metrics(self, analysis_result: str) -> dict[str, Any]:
        metrics = {
            "trend_direction": "neutral",
            "trend_strength": 0.5,
            "support_level": 0.0,
            "resistance_level": 0.0,
            "rsi_signal": "neutral",
            "macd_signal": "neutral",
            "volume_confirmation": False,
        }

        # 提取趋势方向
        if any(
            keyword in analysis_result for keyword in ["上升趋势", "看涨", "bullish"]
        ):
            metrics["trend_direction"] = "bullish"
        elif any(
            keyword in analysis_result for keyword in ["下降趋势", "看跌", "bearish"]
        ):
            metrics["trend_direction"] = "bearish"

        # 提取支撑阻力位
        support_match = re.search(r"支撑位[:：]\s*([0-9.]+)", analysis_result)
        if support_match:
            metrics["support_level"] = float(support_match.group(1))

        resistance_match = re.search(r"阻力位[:：]\s*([0-9.]+)", analysis_result)
        if resistance_match:
            metrics["resistance_level"] = float(resistance_match.group(1))

        return metrics


class RiskManager(BaseSpecializedAgent):
    """风控经理智能体"""

    def __init__(self, multi_model_manager, config: dict[str, Any] = None):
        super().__init__(
            agent_role="risk_manager",
            description="风险管理专家，负责投资风险评估和控制策略制定",
            multi_model_manager=multi_model_manager,
            config=config,
        )

    def _build_system_prompt_template(self) -> str:
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("risk_manager", "system_prompt")
            if custom:
                return custom
        except Exception:
            pass
        return """你是一名专业的风险管理经理，职责包括：

⚠️ **风险识别**
- 市场风险评估
- 信用风险分析
- 流动性风险监控
- 操作风险管理

📊 **风险量化**
- VaR计算和压力测试
- 风险敞口测量
- 相关性分析
- 波动率预测

🛡️ **风控策略**
- 仓位管理建议
- 对冲策略设计
- 止损机制设置
- 资产配置优化

你的分析应该全面、谨慎，为投资决策提供风险保障。"""

    def _build_analysis_prompt_template(self) -> str:
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("risk_manager", "analysis_prompt_template")
            if custom:
                return custom
        except Exception:
            pass
        return """请进行全面的投资风险评估：

🔍 **风险评估重点**
1. 系统性风险分析
2. 特定风险识别
3. 风险量化评估
4. 风险应对策略

💡 **风控建议**
- 最大仓位限制
- 止损止盈设置
- 对冲方案
- 分散化建议"""

    def get_specialized_task_type(self) -> str:
        return "risk_assessment"

    def validate_input_data(self, data: dict[str, Any]) -> bool:
        required_fields = ["investment_proposal"]
        return all(field in data and data[field] for field in required_fields)

    def extract_key_metrics(self, analysis_result: str) -> dict[str, Any]:
        return {
            "risk_score": 0.5,
            "max_position_size": 0.0,
            "stop_loss_level": 0.0,
            "risk_reward_ratio": 1.0,
        }


class SentimentAnalyst(BaseSpecializedAgent):
    """情绪分析师智能体"""

    def __init__(self, multi_model_manager, config: dict[str, Any] = None):
        super().__init__(
            agent_role="sentiment_analyst",
            description="市场情绪分析专家，专注于投资者情绪和市场心理分析",
            multi_model_manager=multi_model_manager,
            config=config,
        )

    def _build_system_prompt_template(self) -> str:
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("sentiment_analyst", "system_prompt")
            if custom:
                return custom
        except Exception:
            pass
        return """你是一名市场情绪分析专家：

😊 **情绪分析能力**
- 投资者情绪指标解读
- 社交媒体情绪挖掘
- 新闻舆情分析
- 市场恐慌/贪婪指数评估

📈 **心理分析**
- 群体心理效应分析
- 情绪拐点识别
- 逆向投资信号
- 情绪传导机制

你需要客观分析市场情绪，识别情绪极端点的投资机会。"""

    def _build_analysis_prompt_template(self) -> str:
        try:
            from tradingagents.config.role_library import get_prompt

            custom = get_prompt("sentiment_analyst", "analysis_prompt_template")
            if custom:
                return custom
        except Exception:
            pass
        return """请分析当前的市场情绪状况：

🎭 **情绪分析重点**
1. 整体市场情绪水平
2. 情绪变化趋势
3. 极端情绪信号
4. 情绪驱动因子

💫 **投资含义**
- 情绪对价格的影响
- 逆向投资机会
- 情绪风险提示"""

    def get_specialized_task_type(self) -> str:
        return "sentiment_analysis"

    def validate_input_data(self, data: dict[str, Any]) -> bool:
        required_fields = ["sentiment_data"]
        return all(field in data and data[field] for field in required_fields)

    def extract_key_metrics(self, analysis_result: str) -> dict[str, Any]:
        return {
            "sentiment_score": 0.0,  # -1 to 1
            "fear_greed_index": 50,  # 0-100
            "volatility_sentiment": "normal",
        }


# 为了向后兼容，创建其他专业智能体的别名
PolicyResearcher = TechnicalAnalyst  # 可以扩展为独立类
ToolEngineer = TechnicalAnalyst  # 可以扩展为独立类
ComplianceOfficer = RiskManager  # 可以扩展为独立类


# 导出所有智能体类
__all__ = [
    "BaseSpecializedAgent",
    "AgentAnalysisResult",
    "NewsHunter",
    "FundamentalExpert",
    "ChiefDecisionOfficer",
    "ChiefWriter",
    "ChartingArtist",  # 新增绘图师智能体
    "TechnicalAnalyst",
    "RiskManager",
    "SentimentAnalyst",
    "PolicyResearcher",
    "ToolEngineer",
    "ComplianceOfficer",
]
