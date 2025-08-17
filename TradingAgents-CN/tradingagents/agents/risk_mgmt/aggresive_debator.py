import os

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_risky_debator(llm):
    def risky_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        risky_history = risk_debate_state.get("risky_history", "")

        current_safe_response = risk_debate_state.get("current_safe_response", "")
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

        prompt = f"""作为激进风险分析师，您的职责是积极倡导高回报、高风险的投资机会，强调大胆策略和竞争优势。在评估交易员的决策或计划时，请重点关注潜在的上涨空间、增长潜力和创新收益——即使这些伴随着较高的风险。使用提供的市场数据和情绪分析来加强您的论点，并挑战对立观点。具体来说，请直接回应保守和中性分析师提出的每个观点，用数据驱动的反驳和有说服力的推理进行反击。突出他们的谨慎态度可能错过的关键机会，或者他们的假设可能过于保守的地方。以下是交易员的决策：

{trader_decision}

您的任务是通过质疑和批评保守和中性立场来为交易员的决策创建一个令人信服的案例，证明为什么您的高回报视角提供了最佳的前进道路。将以下来源的见解纳入您的论点：

市场研究报告：{market_research_report}
社交媒体情绪报告：{sentiment_report}
最新世界事务报告：{news_report}
公司基本面报告：{fundamentals_report}
以下是当前对话历史：{history} 以下是保守分析师的最后论点：{current_safe_response} 以下是中性分析师的最后论点：{current_neutral_response}。如果其他观点没有回应，请不要虚构，只需提出您的观点。

积极参与，解决提出的任何具体担忧，反驳他们逻辑中的弱点，并断言承担风险的好处以超越市场常规。专注于辩论和说服，而不仅仅是呈现数据。挑战每个反驳点，强调为什么高风险方法是最优的。请用中文以对话方式输出，就像您在说话一样，不使用任何特殊格式。{react_instructions}{crossq_note}"""

        response = llm.invoke(prompt)

        argument = f"Risky Analyst: {response.content}"
        # 记录 metrics + 可选 tool_calls/cross_question
        try:
            has_citation = (
                ("[cite:" in response.content)
                or ("来源:" in response.content)
                or ("参考:" in response.content)
            )
            logger.debug(f"⚡ [DEBUG] 激进发言包含引用标记: {has_citation}")
            try:
                from tradingagents.monitoring.debate_metrics import record_citation

                record_citation("risky", bool(has_citation))
            except Exception:
                pass
        except Exception:
            has_citation = False

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
            "risky_history": risky_history + "\n" + argument,
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Risky",
            "current_risky_response": argument,
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return risky_node
