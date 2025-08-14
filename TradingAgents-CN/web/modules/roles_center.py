#!/usr/bin/env python3
"""
角色中心（合并页）

将“角色模型绑定”和“角色库”整合为一个页面，提供：
- 概览：智能体架构与当前生效绑定概览
- 模型绑定：集中管理各角色的模型绑定（会话/永久）
- 角色库：管理角色的提示词与模型策略

尽量复用现有模块的渲染逻辑，避免重复实现与状态割裂。
"""

from __future__ import annotations

import streamlit as st
from pathlib import Path
import sys
from typing import Any, Dict

# 确保可导入 web/utils 与项目根目录模块
CURRENT_DIR = Path(__file__).resolve()
WEB_DIR = CURRENT_DIR.parent.parent
PROJECT_ROOT = WEB_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(WEB_DIR) not in sys.path:
    sys.path.append(str(WEB_DIR))

# 复用现有模块
from components.role_alignment_display import render_role_alignment_dashboard
from modules.role_model_binding import render_role_model_binding
from modules.role_library_manager import render_role_library
from utils.ui_utils import load_persistent_role_configs


def _render_overview() -> None:
    """概览标签：角色架构 + 当前生效绑定"""
    st.subheader("🎯 角色与架构概览")
    try:
        render_role_alignment_dashboard()
    except Exception as e:
        st.warning(f"⚠️ 架构可视化加载失败：{e}")

    st.markdown("---")
    st.subheader("🔎 当前生效的模型绑定")
    # 会话优先，其次持久
    session_overrides: Dict[str, Any] = st.session_state.get("model_overrides", {}) or {}
    persistent_config = load_persistent_role_configs() or {"role_overrides": {}}
    persistent_overrides = persistent_config.get("role_overrides", {})

    if session_overrides:
        st.caption("本次会话（优先级更高）")
        st.json(session_overrides)
    elif persistent_overrides:
        st.caption("永久配置（会话未设置时生效）")
        st.json({k: v.get("model") for k, v in persistent_overrides.items()})
    else:
        st.info("暂无任何绑定。系统将按路由策略与推荐模型自动选择。")


def render_roles_center() -> None:
    """渲染合并后的角色中心页面。"""
    st.title("🧭 角色中心")
    st.caption("合并‘角色模型绑定’与‘角色库’，集中完成角色策略配置与模型绑定。")

    tab_overview, tab_binding, tab_library = st.tabs(["📌 概览", "✍️ 主笔人模型", "🧰 角色库"])

    with tab_overview:
        _render_overview()

    with tab_binding:
        # 直接复用原绑定页面，避免逻辑分叉
        render_role_model_binding()

    with tab_library:
        # 直接复用原角色库管理
        render_role_library()
