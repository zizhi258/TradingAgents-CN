"""
简单模式配置画像面板

提供四个一键入口：速度优先、均衡、质量优先、自动（推荐）。
输出统一的配置字典，供上层组装运行参数。
"""

from __future__ import annotations

import os
import streamlit as st


def _default_profile() -> str:
    return os.getenv("DEFAULT_PROFILE", "自动")


def render_profile_panel() -> dict:
    """渲染一键画像面板并返回配置。

    Returns:
        dict: {
            profile_id: str,               # 自动/速度优先/均衡/质量优先
            max_budget: float,             # 每次分析成本上限（¥）
            time_cap_minutes: int | None,  # 可选时间上限
            routing_strategy: str,         # 质量优先/均衡/成本优先
            llm_provider: str,             # 推荐提供商（可用性检测在上层做）
            llm_quick_model: str,
            llm_deep_model: str,
            analysts: list[str],           # 推荐分析师组合
            collaboration_mode: str        # 依次/并行/辩论
        }
    """

    st.markdown("### 🎯 快速选择套餐（简单模式）")

    col1, col2 = st.columns([2, 1])
    with col1:
        profile = st.radio(
            "选择模式",
            options=["自动", "速度优先", "均衡", "质量优先"],
            index=["自动", "速度优先", "均衡", "质量优先"].index(_default_profile())
            if _default_profile() in ["自动", "速度优先", "均衡", "质量优先"]
            else 0,
            horizontal=True,
            key="simple_profile_choice",
        )
    with col2:
        max_budget = st.number_input(
            "本次成本上限(¥)", min_value=0.0, value=float(os.getenv("DEFAULT_BUDGET", "0") or 0.0), step=0.1
        )

    with st.expander("⏱️ 可选：时间上限"):
        time_cap_minutes = st.number_input("最长分析时长(分钟)", min_value=0, value=0, step=1)
        time_cap_minutes = int(time_cap_minutes) or None

    # 推荐规则（可被上层自动调整）
    if profile == "速度优先":
        routing = "成本优先"
        analysts = ["market", "fundamentals", "quick"]  # quick 为内部快速处理节点占位
        provider, quick, deep = "deepseek", "deepseek-chat", "deepseek-chat"
        collaboration = "依次"
    elif profile == "质量优先":
        routing = "质量优先"
        analysts = ["market", "fundamentals", "news", "social", "risk", "compliance"]
        provider, quick, deep = "google", "gemini-2.5-flash", "gemini-2.5-pro"
        collaboration = "并行+辩论"
    elif profile == "均衡":
        routing = "均衡"
        analysts = ["market", "fundamentals", "news"]
        provider, quick, deep = "deepseek", "deepseek-chat", "deepseek-chat"
        collaboration = "并行"
    else:  # 自动
        routing = "质量优先"
        analysts = ["market", "fundamentals", "news"]
        provider, quick, deep = "deepseek", "deepseek-chat", "deepseek-chat"
        collaboration = "并行"

    # 返回统一配置
    return {
        "profile_id": profile,
        "max_budget": max_budget,
        "time_cap_minutes": time_cap_minutes,
        "routing_strategy": routing,
        "llm_provider": provider,
        "llm_quick_model": quick,
        "llm_deep_model": deep,
        "analysts": analysts,
        "collaboration_mode": collaboration,
    }
