import os

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

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

        judge_swap = _env_bool("DEBATE_JUDGE_SWAP_ORDER", False)
        judge_anon = _env_bool("DEBATE_JUDGE_ANONYMIZE", False)

        # 生成（可匿名）历史文本
        def _anonymize(h: str) -> str:
            try:
                h2 = h.replace("Bull Analyst:", "Analyst A:")
                h2 = h2.replace("Bear Analyst:", "Analyst B:")
                return h2
            except Exception:
                return h

        history_for_prompt = _anonymize(history) if judge_anon else history

        prompt = f"""作为投资组合经理和辩论主持人，您的职责是批判性地评估这轮辩论并做出明确决策：支持看跌分析师、看涨分析师，或者仅在基于所提出论点有强有力理由时选择持有。

简洁地总结双方的关键观点，重点关注最有说服力的证据或推理。您的建议——买入、卖出或持有——必须明确且可操作。避免仅仅因为双方都有有效观点就默认选择持有；要基于辩论中最强有力的论点做出承诺。

此外，为交易员制定详细的投资计划。这应该包括：

您的建议：基于最有说服力论点的明确立场。
理由：解释为什么这些论点导致您的结论。
战略行动：实施建议的具体步骤。
📊 目标价格分析：基于所有可用报告（基本面、新闻、情绪），提供全面的目标价格区间和具体价格目标。考虑：
- 基本面报告中的基本估值
- 新闻对价格预期的影响
- 情绪驱动的价格调整
- 技术支撑/阻力位
- 风险调整价格情景（保守、基准、乐观）
- 价格目标的时间范围（1个月、3个月、6个月）
💰 您必须提供具体的目标价格 - 不要回复"无法确定"或"需要更多信息"。

考虑您在类似情况下的过去错误。利用这些见解来完善您的决策制定，确保您在学习和改进。以对话方式呈现您的分析，就像自然说话一样，不使用特殊格式。

以下是您对错误的过去反思：
\"{past_memory_str}\"

以下是综合分析报告：
市场研究：{market_research_report}

情绪分析：{sentiment_report}

新闻分析：{news_report}

基本面分析：{fundamentals_report}

以下是辩论：
辩论历史：
{history_for_prompt}

请用中文撰写所有分析内容和建议。"""

        # 简单的裁决偏置缓解：顺序/身份交换试验（仅记录，不改变输出）
        def _extract_simple_decision(text: str) -> str:
            t = (text or "").upper()
            if ("STRONG BUY" in t) or ("强烈买入" in text):
                return "STRONG_BUY"
            if ("STRONG SELL" in t) or ("强烈卖出" in text):
                return "STRONG_SELL"
            if ("BUY" in t) or ("买入" in text):
                return "BUY"
            if ("SELL" in t) or ("卖出" in text):
                return "SELL"
            if ("HOLD" in t) or ("持有" in text):
                return "HOLD"
            return "UNKNOWN"

        response = llm.invoke(prompt)

        position_flip = False
        try:
            if judge_swap:
                swapped_hist = history_for_prompt
                # 简单交换 A/B 或 Bull/Bear 标签
                swapped_hist = (
                    swapped_hist.replace("Analyst A:", "__TMP_B__")
                    .replace("Analyst B:", "Analyst A:")
                    .replace("__TMP_B__", "Analyst B:")
                    if judge_anon
                    else history.replace("Bull Analyst:", "__TMP_B__")
                    .replace("Bear Analyst:", "Bull Analyst:")
                    .replace("__TMP_B__", "Bear Analyst:")
                )

                prompt_swapped = prompt.replace(
                    history_for_prompt if judge_anon else history, swapped_hist
                )
                response_swapped = llm.invoke(prompt_swapped)

                d1 = _extract_simple_decision(response.content)
                d2 = _extract_simple_decision(response_swapped.content)
                position_flip = d1 != d2 and d1 != "UNKNOWN" and d2 != "UNKNOWN"
                logger.debug(
                    f"🧪 [JUDGE] 位置交换试验：原={d1}, 交换={d2}, flip={position_flip}"
                )
                try:
                    from tradingagents.monitoring.debate_metrics import (
                        record_judge_flip,
                    )

                    record_judge_flip(position_flip)
                except Exception:
                    pass
        except Exception as _e:
            logger.debug(f"🧪 [JUDGE] 位置交换试验异常：{_e}")

        # 占位：投票方法与权重（默认 majority，权重=1）
        try:
            import os as _os

            vote_method = (
                (_os.getenv("DEBATE_VOTE_METHOD") or "majority").strip().lower()
            )
            if vote_method not in ("majority", "borda", "kemeny"):
                vote_method = "majority"
            early_flag = (
                _os.getenv("DEBATE_EARLY_STOP_BY_ENTROPY") or "false"
            ).strip().lower() in {"1", "true", "yes", "on"}
        except Exception:
            vote_method = "majority"
            early_flag = False

        # SC-Weighted 代理：基于引用比率进行轻量打分（仅在开启时）
        vote_weights = {"bull": 1.0, "bear": 1.0}
        try:
            sc_enabled = (
                _os.getenv("DEBATE_SC_WEIGHTED_ENABLED") or "false"
            ).strip().lower() in {"1", "true", "yes", "on"}
            if sc_enabled:
                import re

                bull_last = investment_debate_state.get("bull_history", "").split("\n")[
                    -1
                ]
                bear_last = investment_debate_state.get("bear_history", "").split("\n")[
                    -1
                ]

                def _evidence_ratio(text: str) -> float:
                    cites = len(re.findall(r"\[cite:", text or ""))
                    tokens = max(1, len(text.split()))
                    return min(1.0, cites / tokens * 10.0)

                vote_weights = {
                    "bull": 0.5 + 0.5 * _evidence_ratio(bull_last),
                    "bear": 0.5 + 0.5 * _evidence_ratio(bear_last),
                }
        except Exception:
            pass
        round_ranking = {
            "method": vote_method,
            "position_flip": position_flip,
            "final_order": ["bull", "bear"],
        }
        # 早停/弃权/上诉占位（不改变流程，仅记录）
        try:
            if early_flag and investment_debate_state.get("count", 0) >= 2:
                round_ranking["early_stop"] = True
                # 简单弃权与上诉建议：若证据比率很低，建议 more_compute
                if min(vote_weights.values()) < 0.55:
                    round_ranking["synthesis_metadata"] = {"escalation": "more_compute"}
        except Exception:
            pass

        # 简化 Borda 聚合（当选择 borda 时，仅基于权重计算）
        vote_results = None
        try:
            if vote_method == "borda":
                # 两候选：高权重得1分，低权重得0分
                ranking = sorted(vote_weights.items(), key=lambda x: x[1], reverse=True)
                scores = {
                    name: (1 if i == 0 else 0) for i, (name, _) in enumerate(ranking)
                }
                vote_results = {
                    "method": "borda",
                    "scores": scores,
                    "ranking": [name for name, _ in ranking],
                }
        except Exception:
            pass

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
            "vote_weights": vote_weights,
            "round_ranking": round_ranking,
        }
        if vote_results is not None:
            new_investment_debate_state["vote_results"] = vote_results

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
