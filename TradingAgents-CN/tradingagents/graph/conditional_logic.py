# TradingAgents/graph/conditional_logic.py

import os

from tradingagents.agents.utils.agent_states import AgentState

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, max_risk_discuss_rounds=1):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.max_risk_discuss_rounds = max_risk_discuss_rounds

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_market"
        return "Msg Clear Market"

    def should_continue_social(self, state: AgentState):
        """Determine if social media analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_social"
        return "Msg Clear Social"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_news"
        return "Msg Clear News"

    def should_continue_fundamentals(self, state: AgentState):
        """Determine if fundamentals analysis should continue."""
        messages = state["messages"]
        last_message = messages[-1]

        # 只有AIMessage才有tool_calls属性
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools_fundamentals"
        return "Msg Clear Fundamentals"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""
        # 早停开关（占位，默认关闭）：减少一轮对话阈值
        early_flag = str(
            os.getenv("DEBATE_EARLY_STOP_BY_ENTROPY", "false")
        ).strip().lower() in {"1", "true", "yes", "on"}
        if early_flag:
            if state["investment_debate_state"]["count"] >= max(
                1, 2 * self.max_debate_rounds - 1
            ):
                return "Research Manager"
        if state["investment_debate_state"]["count"] >= 2 * self.max_debate_rounds:
            return "Research Manager"
        if state["investment_debate_state"]["current_response"].startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"

    def should_continue_risk_analysis(self, state: AgentState) -> str:
        """Determine if risk analysis should continue."""
        # 早停（占位）：若开启，则少一轮
        early_flag = str(
            os.getenv("DEBATE_EARLY_STOP_BY_ENTROPY", "false")
        ).strip().lower() in {"1", "true", "yes", "on"}
        if early_flag:
            if state["risk_debate_state"]["count"] >= max(
                2, 3 * self.max_risk_discuss_rounds - 1
            ):
                return "Risk Judge"
        if state["risk_debate_state"]["count"] >= 3 * self.max_risk_discuss_rounds:
            return "Risk Judge"
        if state["risk_debate_state"]["latest_speaker"].startswith("Risky"):
            return "Safe Analyst"
        if state["risk_debate_state"]["latest_speaker"].startswith("Safe"):
            return "Neutral Analyst"
        return "Risky Analyst"
