import os

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_safe_debator(llm):
    def safe_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # Feature Flags（默认关闭，兼容旧流程）
        def _env_bool(name: str, default: bool = False) -> bool:
            v = os.getenv(name)
            if v is None:
                return default
            return str(v).strip().lower() in {"1", "true", "yes", "on"}

        react_enabled = _env_bool("DEBATE_REACT_ENABLED", False)
        crossq_enabled = _env_bool("DEBATE_CROSS_QUESTION_ENABLED", False)

        react_instructions = ""
        if react_enabled:
            react_instructions = (
                "\n\n[证据与行动要求]\n"
                "- 若提出任何事实性主张，请引用上方提供的报告内容（使用 [cite:来源/段落] 标注），并尽量标明出处类型（市场/情绪/新闻/基本面）。\n"
                "- 若需要，请明确指出需要进一步检索/工具调用的点（例如: [tool:search/news/fundamentals 提示]），但为保持兼容性，此处仅做显式说明，不调用外部工具。\n"
            )
        crossq_note = ""
        if crossq_enabled:
            crossq_note = (
                "\n- 在回答结尾向对方提出一个具体的交叉质询问题（cross-question）。"
            )

        prompt = f"""作为安全/保守风险分析师，您的主要目标是保护资产、最小化波动性，并确保稳定、可靠的增长。您优先考虑稳定性、安全性和风险缓解，仔细评估潜在损失、经济衰退和市场波动。在评估交易员的决策或计划时，请批判性地审查高风险要素，指出决策可能使公司面临不当风险的地方，以及更谨慎的替代方案如何能够确保长期收益。以下是交易员的决策：

{trader_decision}

您的任务是积极反驳激进和中性分析师的论点，突出他们的观点可能忽视的潜在威胁或未能优先考虑可持续性的地方。直接回应他们的观点，利用以下数据来源为交易员决策的低风险方法调整建立令人信服的案例：

市场研究报告：{market_research_report}
社交媒体情绪报告：{sentiment_report}
最新世界事务报告：{news_report}
公司基本面报告：{fundamentals_report}
以下是当前对话历史：{history} 以下是激进分析师的最后回应：{current_risky_response} 以下是中性分析师的最后回应：{current_neutral_response}。如果其他观点没有回应，请不要虚构，只需提出您的观点。

通过质疑他们的乐观态度并强调他们可能忽视的潜在下行风险来参与讨论。解决他们的每个反驳点，展示为什么保守立场最终是公司资产最安全的道路。专注于辩论和批评他们的论点，证明低风险策略相对于他们方法的优势。请用中文以对话方式输出，就像您在说话一样，不使用任何特殊格式。{react_instructions}{crossq_note}"""

        response = llm.invoke(prompt)

        argument = f"Safe Analyst: {response.content}"
        try:
            has_citation = (
                ("[cite:" in response.content)
                or ("来源:" in response.content)
                or ("参考:" in response.content)
            )
            logger.debug(f"🛡️ [DEBUG] 保守发言包含引用标记: {has_citation}")
            try:
                from tradingagents.monitoring.debate_metrics import record_citation

                record_citation("safe", bool(has_citation))
            except Exception:
                pass
        except Exception:
            has_citation = False
        # 可选解析 tool_calls
        tool_calls = []
        citations = []
        try:
            import re

            citations = re.findall(r"\[cite:([^\]]+)\]", response.content or "")
            for m in re.finditer(
                r"\[tool:([a-zA-Z_]+)([^\]]*)\]", response.content or ""
            ):
                tool = m.group(1)
                args = (m.group(2) or "").strip()
                observation = "not_executed (compat mode)"
                try:
                    from tradingagents.utils.evidence_search import (
                        extract_evidence_snippets,
                    )

                    sources = {
                        "market": market_research_report,
                        "sentiment": sentiment_report,
                        "news": news_report,
                        "fundamentals": fundamentals_report,
                    }
                    q = args or response.content
                    ev = extract_evidence_snippets(q, sources, top_k=2)
                    if ev:
                        observation = " | ".join(
                            [f"{src}:{snippet}" for src, snippet in ev]
                        )
                        for src, snippet in ev:
                            citations.append(f"{src}:{snippet[:30]}...")
                except Exception:
                    pass
                tool_calls.append(
                    {
                        "tool": tool,
                        "args": args,
                        "observation": observation,
                        "citations": citations,
                    }
                )
        except Exception:
            pass

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": safe_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Safe",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": argument,
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return safe_node
