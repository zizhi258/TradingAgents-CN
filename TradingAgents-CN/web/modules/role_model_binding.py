#!/usr/bin/env python3
"""
角色-模型绑定独立页面

目标：提供一个整洁的集中式界面，统一管理各角色的模型绑定，
支持“本次会话”与“永久保存”两种作用域，避免在主分析页面出现
零散的配置按钮带来的混乱体验。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import streamlit as st

# 确保可导入 web/utils 与项目根目录模块
CURRENT_DIR = Path(__file__).resolve()
WEB_DIR = CURRENT_DIR.parent.parent
PROJECT_ROOT = WEB_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(WEB_DIR) not in sys.path:
    sys.path.append(str(WEB_DIR))

from tradingagents.config.provider_models import (  # noqa: E402
    ProviderType,
    RoutingStrategy,
    model_provider_manager,
)
from utils.ui_utils import (  # noqa: E402
    clear_role_config,
    get_available_agents_for_ui,
    load_persistent_role_configs,
    save_persistent_role_config,
)


def _get_all_roles() -> list[str]:
    """获取当前启用的全部角色键名（按后端可用性优先排序/过滤）。"""
    # 基础角色（启用状态）
    base = [
        rk
        for rk, rc in model_provider_manager.role_definitions.items()
        if getattr(rc, "enabled", True)
    ]
    # 后端可用性（API优先，本地回退）
    try:
        meta = get_available_agents_for_ui()
        available = meta.get("available_agents", []) or []
        if available:
            # 按 base 的顺序保留且仅取后端可用角色
            filtered = [rk for rk in base if rk in available]
            return filtered if filtered else base
    except Exception:
        pass
    return base


def _display_role_card(
    role_key: str,
    default_value: str | None,
    session_overrides: dict[str, str],
    persistent_overrides: dict[str, Any],
) -> str:
    """渲染单个角色的绑定卡片，返回选择的模型名或"(不锁定)"。"""
    role_cfg = model_provider_manager.get_role_config(role_key)
    if not role_cfg:
        st.warning(f"未知角色: {role_key}")
        return "(不锁定)"

    display_name = role_cfg.name or role_key
    allowed_models = role_cfg.allowed_models or []
    recommended = (
        role_cfg.locked_model
        or role_cfg.preferred_model
        or model_provider_manager.get_best_model_for_role(
            role_key, RoutingStrategy.BALANCED
        )
    )

    # 当前值：优先会话，其次永久，再次默认/推荐
    current_value = (
        session_overrides.get(role_key)
        or (
            persistent_overrides.get(role_key, {}).get("model")
            if persistent_overrides
            else None
        )
        or default_value
        or "(不锁定)"
    )

    # 卡片样式
    st.markdown(
        """
        <style>
        .role-card { background: #ffffff; border: 1px solid #e9ecef; border-radius: 10px; padding: 12px; }
        .role-card h4 { margin: 0 0 8px 0; font-size: 1rem; }
        .role-meta { color: #6c757d; font-size: 0.85rem; margin-bottom: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="role-card">', unsafe_allow_html=True)
        st.markdown(f"<h4>{display_name}</h4>", unsafe_allow_html=True)
        st.caption(
            f"允许: {', '.join(allowed_models)}"
            if allowed_models
            else "该角色未设置允许模型"
        )

        # 根据允许模型分组到提供商，若有多个提供商则先选择提供商，再筛选模型
        # 与“主笔人模型绑定”保持一致的交互体验
        provider_to_models: dict[str, list[str]] = {}
        try:
            for m in allowed_models:
                info = model_provider_manager.get_model_info(m)
                if info:
                    provider_to_models.setdefault(info.provider.value, []).append(m)
        except Exception:
            provider_to_models = {}

        provider_labels = {
            "google": "Google AI (Gemini)",
            "deepseek": "DeepSeek",
            "siliconflow": "SiliconFlow 聚合",
            "openai": "OpenAI",
            "ollama": "Ollama",
        }

        selected_model: str = "(不锁定)"

        if allowed_models and len(provider_to_models.keys()) > 1:
            # 推断当前值对应的提供商
            def _infer_provider(model_name: str) -> str:
                info = (
                    model_provider_manager.get_model_info(model_name)
                    if model_name and model_name not in ("(不锁定)", None)
                    else None
                )
                return info.provider.value if info else next(iter(provider_to_models.keys()))

            default_provider = _infer_provider(current_value)
            provider = st.selectbox(
                label=f"选择提供商 - {display_name}",
                options=list(provider_to_models.keys()),
                index=(
                    list(provider_to_models.keys()).index(default_provider)
                    if default_provider in provider_to_models
                    else 0
                ),
                format_func=lambda k: provider_labels.get(k, k),
                key=f"provider_{role_key}",
            )

            models_in_provider = provider_to_models.get(provider, [])
            options = ["(不锁定)"] + models_in_provider
            try:
                index = options.index(current_value) if current_value in options else 0
            except Exception:
                index = 0
            selected_model = st.selectbox(
                label=f"绑定模型 - {display_name}",
                options=options,
                index=index,
                # 关键：当供应商切换时，改变控件key，强制Streamlit重建控件并重置非法值
                key=f"bind_{role_key}_{provider}",
                help=(f"推荐: {recommended}" if recommended else None),
            )
            # 再次校验：若当前选择不在该供应商模型内，回退为(不锁定)
            if selected_model not in options:
                selected_model = "(不锁定)"
        else:
            # 单一提供商或无法解析提供商：回退为简单下拉
            options = ["(不锁定)"] + allowed_models
            try:
                index = options.index(current_value) if current_value in options else 0
            except Exception:
                index = 0
            selected_model = st.selectbox(
                label=f"绑定模型 - {display_name}",
                options=options,
                index=index,
                key=f"bind_{role_key}",
                help=(f"推荐: {recommended}" if recommended else None),
            )

        st.markdown("</div>", unsafe_allow_html=True)

    return selected_model


def render_role_model_binding() -> None:
    """渲染“主笔人模型绑定”优先视图，并提供高级模式供全角色绑定。"""
    # ========= 主笔人模型绑定（主视图） =========
    st.title("✍️ 主笔人模型绑定")
    st.caption(
        "为主笔人（长文写作）选择模型，支持多提供商；其他角色的绑定请展开下方高级设置。"
    )

    # 会话与永久绑定读取
    persistent_config = load_persistent_role_configs() or {"role_overrides": {}}
    persistent_overrides = persistent_config.get("role_overrides", {})
    session_overrides = st.session_state.get("model_overrides", {}) or {}

    # 角色键与允许模型
    role_key = "chief_writer"
    role_cfg = model_provider_manager.get_role_config(role_key)
    allowed_models = role_cfg.allowed_models if role_cfg else []

    # 计算可用提供商与分组
    provider_to_models: dict[str, list[str]] = {p.value: [] for p in ProviderType}
    for m in allowed_models:
        info = model_provider_manager.get_model_info(m)
        if info:
            provider_to_models.setdefault(info.provider.value, [])
            provider_to_models[info.provider.value].append(m)

    # 清理空提供商，仅保留有可用模型的项
    provider_to_models = {k: v for k, v in provider_to_models.items() if v}

    # 当前已选（会话优先）
    current_value = (
        session_overrides.get(role_key)
        or (
            persistent_overrides.get(role_key, {}).get("model")
            if persistent_overrides
            else None
        )
        or role_cfg.preferred_model
        if role_cfg
        else None
    )

    # 提供商选择
    provider_keys = list(provider_to_models.keys())
    provider_labels = {
        "google": "Google AI (Gemini)",
        "deepseek": "DeepSeek",
        "siliconflow": "SiliconFlow 聚合",
        "openai": "OpenAI",
        "ollama": "Ollama",
    }

    # 推断当前值对应的提供商，默认取第一项
    def _infer_provider(model_name: str) -> str:
        info = model_provider_manager.get_model_info(model_name) if model_name else None
        return (
            info.provider.value if info else (provider_keys[0] if provider_keys else "")
        )

    default_provider = _infer_provider(current_value)
    provider = st.selectbox(
        "选择提供商",
        options=provider_keys,
        index=(
            provider_keys.index(default_provider)
            if default_provider in provider_keys
            else 0
        ),
        format_func=lambda k: provider_labels.get(k, k),
        key="chief_writer_provider_select",
    )

    # 模型选择（限该提供商且在允许集内）
    models_in_provider = provider_to_models.get(provider, [])
    default_idx = 0
    if current_value in models_in_provider:
        default_idx = models_in_provider.index(current_value)
    selected_model = st.selectbox(
        "绑定模型（主笔人）",
        options=models_in_provider,
        index=default_idx if models_in_provider else 0,
        key="chief_writer_model_select",
        help=f"允许模型: {len(allowed_models)} 个 | 提供商: {provider_labels.get(provider, provider)}",
    )

    # 保存/重置操作
    c1, c2, c3, _ = st.columns([2, 2, 2, 6])
    with c1:
        if st.button("💾 保存本次会话"):
            if selected_model:
                st.session_state.setdefault("model_overrides", {})
                st.session_state.model_overrides[role_key] = selected_model
                st.success("✅ 已保存到本次会话（主笔人）。")
    with c2:
        if st.button("📌 永久保存"):
            if selected_model and save_persistent_role_config(role_key, selected_model):
                st.session_state.setdefault("model_overrides", {})
                st.session_state.model_overrides[role_key] = selected_model
                st.success("✅ 主笔人永久配置已更新。")
            else:
                st.error("❌ 保存失败")
    with c3:
        if st.button("🧹 重置主笔人"):
            clear_role_config(role_key)
            if role_key in st.session_state.get("model_overrides", {}):
                del st.session_state.model_overrides[role_key]
            st.success("✅ 已重置主笔人绑定。")

    # 当前生效展示（仅主笔人）
    st.markdown("### 当前生效（主笔人）")
    active_model = (
        st.session_state.get("model_overrides", {}).get(role_key)
        or (
            persistent_overrides.get(role_key, {}).get("model")
            if persistent_overrides
            else None
        )
        or "(未绑定，将按策略自动选择)"
    )
    st.json({role_key: active_model})

    # 提示：全局角色绑定入口迁移至“角色库”
    st.markdown("---")
    st.info(
        "全局角色绑定已移动至 ‘🧭 角色中心 > 🧰 角色库’ 页面下的『🔗 全局角色绑定（所有角色）』分区。此处仅保留主笔人模型绑定。"
    )
