import os

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        # 修复：应为基本面报告
        fundamentals_report = state["fundamentals_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

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

        def _anonymize(h: str) -> str:
            try:
                h2 = h.replace("Risky Analyst:", "Analyst X:")
                h2 = h2.replace("Safe Analyst:", "Analyst Y:")
                h2 = h2.replace("Neutral Analyst:", "Analyst Z:")
                return h2
            except Exception:
                return h

        history_for_prompt = _anonymize(history) if judge_anon else history

        prompt = f"""作为风险管理委员会主席和辩论主持人，您的目标是评估三位风险分析师——激进、中性和安全/保守——之间的辩论，并确定交易员的最佳行动方案。您的决策必须产生明确的建议：买入、卖出或持有。只有在有具体论据强烈支持时才选择持有，而不是在所有方面都似乎有效时作为后备选择。力求清晰和果断。

决策指导原则：
1. **总结关键论点**：提取每位分析师的最强观点，重点关注与背景的相关性。
2. **提供理由**：用辩论中的直接引用和反驳论点支持您的建议。
3. **完善交易员计划**：从交易员的原始计划**{trader_plan}**开始，根据分析师的见解进行调整。
4. **从过去的错误中学习**：使用**{past_memory_str}**中的经验教训来解决先前的误判，改进您现在做出的决策，确保您不会做出错误的买入/卖出/持有决定而亏损。

交付成果：
- 明确且可操作的建议：买入、卖出或持有。
- 基于辩论和过去反思的详细推理。

---

**分析师辩论历史：**
{history_for_prompt}

---

专注于可操作的见解和持续改进。建立在过去经验教训的基础上，批判性地评估所有观点，确保每个决策都能带来更好的结果。请用中文撰写所有分析内容和建议。"""

        # 尝试从角色库覆盖
        try:
            from tradingagents.config.role_library import format_prompt, get_prompt

            custom_sys = get_prompt("risk_manager", "system_prompt")
            if custom_sys:
                prompt = format_prompt(
                    custom_sys,
                    {
                        "history": history,
                        "market_research_report": market_research_report,
                        "sentiment_report": sentiment_report,
                        "news_report": news_report,
                        "fundamentals_report": fundamentals_report,
                        "trader_plan": trader_plan,
                        "past_memory_str": past_memory_str,
                        "company_name": company_name,
                    },
                )
        except Exception:
            pass

        # 简单的裁决偏置缓解记录（位置交换实验）
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

        vote_weights = {"risky": 1.0, "safe": 1.0, "neutral": 1.0}
        # SC-Weighted 代理：基于引用比率进行轻量打分（仅在开启时）
        try:
            sc_enabled = (
                _os.getenv("DEBATE_SC_WEIGHTED_ENABLED") or "false"
            ).strip().lower() in {"1", "true", "yes", "on"}
            if sc_enabled:
                import re

                risky_last = risk_debate_state.get("risky_history", "").split("\n")[-1]
                safe_last = risk_debate_state.get("safe_history", "").split("\n")[-1]
                neutral_last = risk_debate_state.get("neutral_history", "").split("\n")[
                    -1
                ]

                def _evidence_ratio(text: str) -> float:
                    cites = len(re.findall(r"\[cite:", text or ""))
                    tokens = max(1, len(text.split()))
                    return min(1.0, cites / tokens * 10.0)

                vote_weights = {
                    "risky": 0.5 + 0.5 * _evidence_ratio(risky_last),
                    "safe": 0.5 + 0.5 * _evidence_ratio(safe_last),
                    "neutral": 0.5 + 0.5 * _evidence_ratio(neutral_last),
                }
        except Exception:
            pass
        round_ranking = {
            "method": vote_method,
            "final_order": ["risky", "safe", "neutral"],
        }
        try:
            if early_flag and risk_debate_state.get("count", 0) >= 3:
                round_ranking["early_stop"] = True
                if min(vote_weights.values()) < 0.55:
                    round_ranking.setdefault("synthesis_metadata", {})[
                        "escalation"
                    ] = "more_compute"
        except Exception:
            pass

        try:
            if judge_swap:
                # 粗略交换标签（仅用于试验记录）
                swapped_hist = history_for_prompt
                if judge_anon:
                    swapped_hist = (
                        swapped_hist.replace("Analyst X:", "__TMP_A__")
                        .replace("Analyst Y:", "Analyst X:")
                        .replace("__TMP_A__", "Analyst Y:")
                    )
                else:
                    swapped_hist = (
                        history.replace("Risky Analyst:", "__TMP_A__")
                        .replace("Safe Analyst:", "Risky Analyst:")
                        .replace("__TMP_A__", "Safe Analyst:")
                    )
                prompt_swapped = prompt.replace(
                    history_for_prompt if judge_anon else history, swapped_hist
                )
                response_swapped = llm.invoke(prompt_swapped)
                d1 = _extract_simple_decision(response.content)
                d2 = _extract_simple_decision(response_swapped.content)
                flip = d1 != d2 and d1 != "UNKNOWN" and d2 != "UNKNOWN"
                logger.debug(
                    f"🧪 [RISK JUDGE] 位置交换试验：原={d1}, 交换={d2}, flip={flip}"
                )
                try:
                    from tradingagents.monitoring.debate_metrics import (
                        record_judge_flip,
                    )

                    record_judge_flip(flip)
                except Exception:
                    pass
        except Exception as _e:
            logger.debug(f"🧪 [RISK JUDGE] 位置交换试验异常：{_e}")

        # 简化 Borda 聚合（当选择 borda 时，仅基于权重计算）
        vote_results = None
        try:
            if vote_method == "borda":
                ranking = sorted(vote_weights.items(), key=lambda x: x[1], reverse=True)
                n = len(ranking)
                scores = {name: (n - 1 - i) for i, (name, _) in enumerate(ranking)}
                vote_results = {
                    "method": "borda",
                    "scores": scores,
                    "ranking": [name for name, _ in ranking],
                }
        except Exception:
            pass

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "risky_history": risk_debate_state["risky_history"],
            "safe_history": risk_debate_state["safe_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_risky_response": risk_debate_state["current_risky_response"],
            "current_safe_response": risk_debate_state["current_safe_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
            "vote_weights": vote_weights,
            "round_ranking": round_ranking,
        }
        if vote_results is not None:
            new_risk_debate_state["vote_results"] = vote_results

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return risk_manager_node
