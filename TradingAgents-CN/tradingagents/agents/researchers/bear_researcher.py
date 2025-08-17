import os

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        # 使用统一的股票类型检测
        company_name = state.get("company_of_interest", "Unknown")
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(company_name)
        market_info["is_china"]
        market_info["is_hk"]
        market_info["is_us"]

        currency = market_info["currency_name"]
        currency_symbol = market_info["currency_symbol"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"

        # 安全检查：确保memory不为None
        if memory is not None:
            past_memories = memory.get_memories(curr_situation, n_matches=2)
        else:
            logger.warning("⚠️ [DEBUG] memory为None，跳过历史记忆检索")
            past_memories = []

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

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
                "- 优先引用带来源的论据；无来源主张需谨慎。\n"
            )
        crossq_note = ""
        if crossq_enabled:
            crossq_note = "\n- 在回答结尾向对方提出一个具体的交叉质询问题（cross-question），以推动辩论收敛。"

        prompt = f"""你是一位看跌分析师，负责论证不投资股票 {company_name} 的理由。

⚠️ 重要提醒：当前分析的是 {market_info['market_name']}，所有价格和估值请使用 {currency}（{currency_symbol}）作为单位。

你的目标是提出合理的论证，强调风险、挑战和负面指标。利用提供的研究和数据来突出潜在的不利因素并有效反驳看涨论点。

请用中文回答，重点关注以下几个方面：

- 风险和挑战：突出市场饱和、财务不稳定或宏观经济威胁等可能阻碍股票表现的因素
- 竞争劣势：强调市场地位较弱、创新下降或来自竞争对手威胁等脆弱性
- 负面指标：使用财务数据、市场趋势或最近不利消息的证据来支持你的立场
- 反驳看涨观点：用具体数据和合理推理批判性分析看涨论点，揭露弱点或过度乐观的假设
- 参与讨论：以对话风格呈现你的论点，直接回应看涨分析师的观点并进行有效辩论，而不仅仅是列举事实

可用资源：

市场研究报告：{market_research_report}
社交媒体情绪报告：{sentiment_report}
最新世界事务新闻：{news_report}
公司基本面报告：{fundamentals_report}
辩论对话历史：{history}
最后的看涨论点：{current_response}
类似情况的反思和经验教训：{past_memory_str}

请使用这些信息提供令人信服的看跌论点，反驳看涨声明，并参与动态辩论，展示投资该股票的风险和弱点。你还必须处理反思并从过去的经验教训和错误中学习。

请确保所有回答都使用中文。{react_instructions}{crossq_note}
"""

        # 尝试从角色库覆盖
        try:
            from tradingagents.config.role_library import format_prompt, get_prompt

            custom_sys = get_prompt("bear_researcher", "system_prompt")
            if custom_sys:
                prompt = format_prompt(
                    custom_sys,
                    {
                        "company_name": company_name,
                        "market_info": market_info,
                        "currency": market_info["currency_name"],
                        "currency_symbol": market_info["currency_symbol"],
                        "history": history,
                        "current_response": current_response,
                        "market_research_report": market_research_report,
                        "sentiment_report": sentiment_report,
                        "news_report": news_report,
                        "fundamentals_report": fundamentals_report,
                        "past_memory_str": past_memory_str,
                    },
                )
        except Exception:
            pass

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        # 简单埋点：是否包含引用标记 & 记录metrics
        try:
            has_citation = (
                ("[cite:" in response.content)
                or ("来源:" in response.content)
                or ("参考:" in response.content)
            )
            logger.debug(f"🐻 [DEBUG] 看跌发言包含引用标记: {has_citation}")
            try:
                from tradingagents.monitoring.debate_metrics import record_citation

                record_citation("bear", bool(has_citation))
            except Exception:
                pass
        except Exception:
            has_citation = False

        # 提取工具与引用标记写入 tool_calls / cross_question（可选）
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

        cross_question_text = None
        if crossq_enabled:
            try:
                last = (response.content or "").strip().splitlines()[-1]
                if last.endswith("？") or last.endswith("?"):
                    cross_question_text = last
            except Exception:
                pass

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }
        if tool_calls:
            new_investment_debate_state["tool_calls"] = tool_calls
        if cross_question_text:
            new_investment_debate_state["cross_question"] = cross_question_text

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
