"""
Roles Registry for unified role display across modes.

This module centralizes multi-model roles and provides a mapping to
single-model analyst keys for compatibility without changing the
single-model backend pipeline.

Notes
- Single-model recognized analyst keys: "market", "fundamentals",
  "news", "social". We only map extended roles to these when needed
  (e.g., to ensure underlying content exists for post-processed views).
- Some roles do not have a direct single-model mapping (e.g.,
  chief_decision_officer, compliance_officer). For these, we use
  lightweight post-processing in the formatter to add compatible
  sections (kept minimal, without LLM calls).
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, TypedDict


class RoleInfo(TypedDict, total=False):
    key: str
    label: str
    icon: str
    # For single-model compatibility, map to one of
    # {"market", "fundamentals", "news", "social"}
    map_to_single: Optional[str]
    # Optional env var that must be true-ish to enable
    requires_env: Optional[str]


def _define_roles() -> Dict[str, RoleInfo]:
    roles: Dict[str, RoleInfo] = {
        # Core multi-model roles
        "news_hunter": {
            "key": "news_hunter",
            "label": "快讯猎手",
            "icon": "📰",
            "map_to_single": "news",
        },
        "technical_analyst": {
            "key": "technical_analyst",
            "label": "技术分析师",
            "icon": "📈",
            "map_to_single": "market",
        },
        "fundamental_expert": {
            "key": "fundamental_expert",
            "label": "基本面专家",
            "icon": "💰",
            "map_to_single": "fundamentals",
        },
        "sentiment_analyst": {
            "key": "sentiment_analyst",
            "label": "情绪分析师",
            "icon": "💭",
            "map_to_single": "social",
        },
        # Extended roles (typically not first-class in single-model pipeline)
        "risk_manager": {
            "key": "risk_manager",
            "label": "风控经理",
            "icon": "🛡️",
            # Single-model has a dedicated risk section, but it is not
            # a selectable analyst key. Keep map None to avoid altering
            # the analysts param.
            "map_to_single": None,
        },
        "policy_researcher": {
            "key": "policy_researcher",
            "label": "政策研究员",
            "icon": "📋",
            "map_to_single": "news",  # derive from news_report
        },
        "compliance_officer": {
            "key": "compliance_officer",
            "label": "合规官",
            "icon": "⚖️",
            "map_to_single": None,  # appended into risk section
        },
        "tool_engineer": {
            "key": "tool_engineer",
            "label": "工具工程师",
            "icon": "🔧",
            "map_to_single": "market",  # append insights into market report
        },
        "chief_decision_officer": {
            "key": "chief_decision_officer",
            "label": "首席决策官",
            "icon": "🎯",
            "map_to_single": None,  # append sign-off into investment_plan
        },
        "charting_artist": {
            "key": "charting_artist",
            "label": "绘图师",
            "icon": "🎨",
            "map_to_single": None,  # visualizations only if enabled
            "requires_env": "CHARTING_ARTIST_ENABLED",
        },
    }
    return roles


_ROLES = _define_roles()


def get_roles_registry() -> Dict[str, RoleInfo]:
    """Return the full roles registry."""
    return _ROLES.copy()


def list_all_role_keys() -> List[str]:
    return list(_ROLES.keys())


def get_role(role_key: str) -> Optional[RoleInfo]:
    return _ROLES.get(role_key)


def get_role_label(role_key: str) -> str:
    info = _ROLES.get(role_key)
    if not info:
        return role_key
    return f"{info.get('icon','')} {info.get('label', role_key)}".strip()


def role_requires_env(role_key: str) -> bool:
    info = _ROLES.get(role_key) or {}
    env_key = info.get("requires_env")
    if not env_key:
        return False
    return os.getenv(env_key, "false").lower() in {"1", "true", "yes", "on"}


def map_role_to_single_model_key(role_key: str) -> Optional[str]:
    """Map a multi-model role to a single-model analyst key if applicable.

    Returns one of {"market","fundamentals","news","social"} or None.
    """
    info = _ROLES.get(role_key)
    if not info:
        return None
    mapped = info.get("map_to_single")
    if mapped in {"market", "fundamentals", "news", "social"}:
        return mapped
    return None


def list_extended_roles_for_single_model_ui() -> List[RoleInfo]:
    """Roles to present in the single-model UI as additional/compatible roles.

    Excludes the four base single-model analysts (market/news/fundamentals/social)
    to avoid duplication/confusion in the form.
    """
    base_duplicates = {
        "technical_analyst",
        "fundamental_expert",
        "news_hunter",
        "sentiment_analyst",
    }
    items: List[RoleInfo] = []
    for k, v in _ROLES.items():
        if k in base_duplicates:
            continue
        if v.get("requires_env") and not role_requires_env(k):
            continue
        items.append(v)
    # stable order for UI
    order = [
        "risk_manager",
        "policy_researcher",
        "compliance_officer",
        "tool_engineer",
        "chief_decision_officer",
        "charting_artist",
    ]
    items.sort(key=lambda x: order.index(x["key"]) if x["key"] in order else 999)
    return items

