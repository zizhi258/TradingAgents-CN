"""
可复用的AI模型选择面板组件
从侧边栏提取的模型配置逻辑，可在页面主内容区域使用
"""

import streamlit as st
import os
import logging
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.utils.persistence import load_model_selection, save_model_selection
from web.utils.model_catalog import (
    get_siliconflow_models,
    get_deepseek_models,
    get_google_models,
    get_openrouter_models,
    get_gemini_api_models,
)
from web.components.custom_model_helper import render_model_help, validate_custom_model_name

logger = logging.getLogger(__name__)

def render_routing_section(location: str = "main") -> tuple:
    """仅渲染路由/回退/预算，返回 (routing_strategy, fallbacks_structured, max_budget)"""
    st.markdown("### 🧭 路由策略与回退")

    routing_strategy = st.selectbox(
        "路由策略",
        options=["质量优先", "时延优先", "成本优先", "均衡"],
        key=f"{location}_routing_strategy_select"
    )

    enable_auto_fallback = st.checkbox(
        "失败自动降级",
        value=True,
        key=f"{location}_enable_auto_fallback"
    )

    # 动态生成（Provider:Model）
    ds = [f"deepseek:{m}" for m in get_deepseek_models()]
    gg = [f"google:{m}" for m in get_google_models()]
    sf = [f"siliconflow:{m}" for m in get_siliconflow_models()]
    # 为避免过长，可按需裁剪；此处全量列出
    fallback_choices_catalog = ds + gg + sf

    selected_fallbacks = st.multiselect(
        "回退候选（从上到下优先）",
        options=fallback_choices_catalog,
        default=([ds[0], (gg[1] if len(gg) > 1 else gg[0])] if (enable_auto_fallback and ds and gg) else []),
        key=f"{location}_selected_fallbacks"
    )

    # 预算上限
    max_budget = st.number_input(
        "每次分析成本上限(¥)",
        min_value=0.0,
        value=0.0,
        step=0.1,
        key=f"{location}_max_budget"
    )

    # 解析为结构化
    def parse_fb(item: str):
        try:
            p, m = item.split(":", 1)
            return {"provider": p, "model": m}
        except Exception:
            return None

    fallbacks_structured = [x for x in (parse_fb(i) for i in selected_fallbacks) if x]

    # 写入会话态，供其他区域使用
    st.session_state.routing_strategy_select = routing_strategy
    st.session_state.fallback_chain = fallbacks_structured
    st.session_state.max_budget = max_budget

    return routing_strategy, fallbacks_structured, max_budget


def render_advanced_overrides_section(location: str = "main") -> dict:
    """仅渲染高级与角色覆盖设置，返回配置字典"""
    with st.expander("⚙️ 高级设置"):
        enable_memory = st.checkbox(
            "启用记忆功能",
            value=False,
            key=f"{location}_enable_memory"
        )

        enable_debug = st.checkbox(
            "调试模式",
            value=False,
            key=f"{location}_enable_debug"
        )

        max_tokens = st.slider(
            "最大输出长度",
            min_value=1000,
            max_value=128000,
            value=32000,
            step=1000,
            key=f"{location}_max_tokens"
        )

        st.markdown("#### 👥 团队策略（按角色控制可用模型）")
        roles = [
            ("fundamental_expert", "基本面专家"),
            ("chief_decision_officer", "首席决策官"),
            ("technical_analyst", "技术分析师"),
            ("news_hunter", "快讯猎手"),
            ("sentiment_analyst", "情绪分析师"),
            ("tool_engineer", "工具工程师"),
        ]

        # 统一来源：三家供应商汇总
        siliconflow_catalog = get_siliconflow_models()
        deepseek_catalog = get_deepseek_models()
        google_catalog = get_google_models()
        unified_catalog = siliconflow_catalog + google_catalog + deepseek_catalog

        allowed_models_by_role = {}
        model_overrides = {}
        for role_key, role_label in roles:
            with st.expander(f"{role_label} ({role_key})", expanded=False):
                allowed = st.multiselect(
                    f"允许的模型（留空则不限制） - {role_label}",
                    options=unified_catalog,
                    default=[],
                    key=f"{location}_allowed_models_{role_key}"
                )
                locked = st.selectbox(
                    f"锁定模型（可选） - {role_label}",
                    options=["(不锁定)"] + unified_catalog,
                    index=0,
                    key=f"{location}_locked_model_{role_key}"
                )
                if allowed:
                    allowed_models_by_role[role_key] = allowed
                if locked and locked != "(不锁定)":
                    model_overrides[role_key] = locked

        st.session_state.allowed_models_by_role = allowed_models_by_role
        st.session_state.model_overrides = model_overrides

    return {
        'enable_memory': enable_memory,
        'enable_debug': enable_debug,
        'max_tokens': max_tokens
    }


def render_basic_advanced_settings(location: str = "main") -> dict:
    """仅渲染基础高级选项（记忆/调试/最大输出），不包含角色配置，界面更紧凑"""
    with st.expander("⚙️ 高级设置", expanded=False):
        enable_memory = st.checkbox(
            "启用记忆功能",
            value=False,
            key=f"{location}_adv_only_enable_memory"
        )
        enable_debug = st.checkbox(
            "调试模式",
            value=False,
            key=f"{location}_adv_only_enable_debug"
        )
        max_tokens = st.slider(
            "最大输出长度",
            min_value=1000,
            max_value=128000,
            value=32000,
            step=1000,
            key=f"{location}_adv_only_max_tokens"
        )
    return {
        'enable_memory': enable_memory,
        'enable_debug': enable_debug,
        'max_tokens': max_tokens,
    }


def render_role_overrides_compact(location: str = "main") -> dict:
    """
    紧凑版角色覆盖配置：左侧选择角色，右侧配置允许/锁定模型，避免纵向无限扩张。
    返回 {'allowed_models_by_role': {...}, 'model_overrides': {...}}
    """
    # 角色清单与标签
    roles = [
        ("fundamental_expert", "基本面专家"),
        ("chief_decision_officer", "首席决策官"),
        ("technical_analyst", "技术分析师"),
        ("news_hunter", "快讯猎手"),
        ("sentiment_analyst", "情绪分析师"),
        ("tool_engineer", "工具工程师"),
    ]
    role_labels = [label for _, label in roles]
    key_by_label = {label: key for key, label in roles}

    # 模型目录（统一来源汇总）
    siliconflow_catalog = get_siliconflow_models()
    deepseek_catalog = get_deepseek_models()
    google_catalog = get_google_models()
    unified_catalog = siliconflow_catalog + google_catalog + deepseek_catalog

    # 从会话恢复
    allowed_models_by_role = dict(st.session_state.get('allowed_models_by_role', {}))
    model_overrides = dict(st.session_state.get('model_overrides', {}))

    # 两列布局：左选择角色，右配置详情
    col_left, col_right = st.columns([1, 2])
    with col_left:
        st.markdown("#### 选择角色")
        selected_label = st.selectbox(
            "需要配置的角色",
            options=role_labels,
            key=f"{location}_role_select"
        )
        # 已配置计数
        configured = sum(1 for k in allowed_models_by_role.keys() if k in [r[0] for r in roles]) + \
                     sum(1 for k in model_overrides.keys() if k in [r[0] for r in roles])
        st.caption(f"已配置角色条目: {configured}")

    with col_right:
        st.markdown("#### 角色详情")
        role_key = key_by_label[selected_label]
        # 当前值
        current_allowed = allowed_models_by_role.get(role_key, [])
        current_locked = model_overrides.get(role_key, "(不锁定)")

        allowed = st.multiselect(
            "允许的模型（留空则不限制）",
            options=unified_catalog,
            default=current_allowed,
            key=f"{location}_allowed_models_compact_{role_key}"
        )
        locked = st.selectbox(
            "锁定模型（可选，优先于允许列表）",
            options=["(不锁定)"] + unified_catalog,
            index=(["(不锁定)"] + unified_catalog).index(current_locked)
                   if current_locked in ["(不锁定)"] + unified_catalog else 0,
            key=f"{location}_locked_model_compact_{role_key}"
        )

        # 写回会话
        if allowed:
            allowed_models_by_role[role_key] = allowed
        elif role_key in allowed_models_by_role:
            # 清空则移除键，避免噪音
            allowed_models_by_role.pop(role_key, None)

        if locked and locked != "(不锁定)":
            model_overrides[role_key] = locked
        else:
            model_overrides.pop(role_key, None)

    # 持久到 session_state，供后续分析使用
    st.session_state.allowed_models_by_role = allowed_models_by_role
    st.session_state.model_overrides = model_overrides

    return {
        'allowed_models_by_role': allowed_models_by_role,
        'model_overrides': model_overrides,
    }


def render_model_selection_panel(location: str = "main", *, show_routing: bool = True, show_advanced: bool = True) -> dict:
    """
    渲染provider/model/routing/cost控件并返回选择结果的字典
    
    Args:
        location: "sidebar" 或 "main" (用于间距/样式差异)
        
    Returns:
        dict: 包含以下键的字典:
            - llm_provider: LLM提供商
            - model_category: 模型类别
            - llm_quick_model: 快速模型
            - llm_deep_model: 深度模型  
            - llm_model: 兼容字段(等于llm_deep_model)
            - routing_strategy: 路由策略
            - fallbacks: 回退候选列表
            - max_budget: 成本上限
    """
    
    # 从持久化存储加载配置
    saved_config = load_model_selection()
    
    # 初始化session state，优先使用保存的配置
    if 'llm_provider' not in st.session_state:
        st.session_state.llm_provider = saved_config['provider']
        logger.debug(f"🔧 [Persistence] 恢复 llm_provider: {st.session_state.llm_provider}")
    if 'model_category' not in st.session_state:
        st.session_state.model_category = saved_config['category']
        logger.debug(f"🔧 [Persistence] 恢复 model_category: {st.session_state.model_category}")
    if 'llm_model' not in st.session_state:
        st.session_state.llm_model = saved_config['model']
        logger.debug(f"🔧 [Persistence] 恢复 llm_model: {st.session_state.llm_model}")
    
    # 初始化双模型位的 session_state
    if 'llm_quick_model' not in st.session_state:
        st.session_state.llm_quick_model = st.session_state.get('llm_model', "") or ""
    if 'llm_deep_model' not in st.session_state:
        st.session_state.llm_deep_model = st.session_state.get('llm_model', "") or ""
    
    # 显示当前session state状态（调试用）
    logger.debug(f"🔍 [Session State] 当前状态 - provider: {st.session_state.llm_provider}, category: {st.session_state.model_category}, model: {st.session_state.llm_model}")

    # 只在主内容区域添加分隔线
    if location == "main":
        st.markdown("---")

    # AI模型配置标题
    st.markdown("### 🧠 AI模型配置")
    
    # LLM提供商选择
    provider_options = ["deepseek", "google", "gemini_api", "openrouter", "siliconflow"]
    llm_provider = st.selectbox(
        "LLM提供商",
        options=provider_options,
        index=(provider_options.index(st.session_state.llm_provider)
               if st.session_state.llm_provider in provider_options else 0),
        format_func=lambda x: {
            "deepseek": "🚀 DeepSeek 官方",
            "google": "🌟 Google AI (Gemini)", 
            "gemini_api": "🌟 Gemini-API (OpenAI兼容反代)",
            "openrouter": "🧭 OpenRouter (聚合/含Gemini)",
            "siliconflow": "🌐 SiliconFlow (聚合)"
        }.get(x, x),
        key=f"{location}_llm_provider_select"
    )
    
    # 更新session state和持久化存储
    if st.session_state.llm_provider != llm_provider:
        logger.info(f"🔄 [Persistence] 提供商变更: {st.session_state.llm_provider} → {llm_provider}")
        st.session_state.llm_provider = llm_provider
        # 提供商变更时清空模型选择
        st.session_state.llm_model = ""
        st.session_state.model_category = "google"  # 重置为默认类别
        logger.info(f"🔄 [Persistence] 清空模型选择")
        
        # 保存到持久化存储
        save_model_selection(llm_provider, st.session_state.model_category, "")
    else:
        st.session_state.llm_provider = llm_provider
    
    # 模型预设选择（与多模型页面的“分析套餐”联动，仅用于初始化默认值）
    preset_options = ["低成本", "均衡", "高质量"]
    pkg = st.session_state.get('analysis_package')
    preset_default = 1  # 均衡
    if pkg == "低成本套餐":
        preset_default = 0
    elif pkg == "高质量套餐":
        preset_default = 2
    # 仅在首次渲染使用 index，后续由控件自身状态管理
    preset = st.selectbox(
        "模型预设",
        options=preset_options,
        index=preset_default,
        help="与多模型‘分析套餐’保持一致：低成本/均衡/高质量",
        key=f"{location}_model_preset_select"
    )
    
    if llm_provider == "deepseek":
        llm_quick_model, llm_deep_model = _render_deepseek_models(location, preset)
        
    elif llm_provider == "google":
        llm_quick_model, llm_deep_model = _render_google_models(location, preset)
        
    elif llm_provider == "openrouter":
        llm_quick_model, llm_deep_model = _render_openrouter_models(location, preset)

    elif llm_provider == "siliconflow":
        llm_quick_model, llm_deep_model = _render_siliconflow_models(location, preset)
    elif llm_provider == "gemini_api":
        llm_quick_model, llm_deep_model = _render_gemini_api_models(location, preset)
    
    # 更新session state
    st.session_state.llm_model = llm_deep_model  # 兼容旧字段
    st.session_state.llm_quick_model = llm_quick_model
    st.session_state.llm_deep_model = llm_deep_model
    
    # 保存到持久化存储
    save_model_selection(st.session_state.llm_provider, st.session_state.model_category, llm_deep_model)
    
    routing_strategy = None
    selected_fallbacks = []
    max_budget = 0.0
    if show_routing:
        if location == "main":
            st.markdown("---")
        # 路由策略与回退配置
        st.markdown("### 🧭 路由策略与回退")

        routing_strategy = st.selectbox(
            "路由策略",
            options=["质量优先", "时延优先", "成本优先", "均衡"],
            key=f"{location}_routing_strategy_select"
        )

        enable_auto_fallback = st.checkbox(
            "失败自动降级",
            value=True,
            key=f"{location}_enable_auto_fallback"
        )

        # 动态生成回退候选（Provider:Model）
        ds = [f"deepseek:{m}" for m in get_deepseek_models()]
        gg = [f"google:{m}" for m in get_google_models()]
        ga = [f"gemini_api:{m}" for m in get_gemini_api_models()]
        orc = [f"openrouter:{m}" for m in get_openrouter_models()]
        sf = [f"siliconflow:{m}" for m in get_siliconflow_models()]
        fallback_choices_catalog = ds + gg + ga + orc + sf

        selected_fallbacks = st.multiselect(
            "回退候选（从上到下优先）",
            options=fallback_choices_catalog,
            default=([ds[0], (gg[1] if len(gg) > 1 else gg[0])] if (enable_auto_fallback and ds and gg) else []),
            key=f"{location}_selected_fallbacks"
        )

        # 预算上限
        max_budget = st.number_input(
            "每次分析成本上限(¥)",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key=f"{location}_max_budget"
        )
    
    # 解析回退候选为结构化
    def parse_fb(item: str):
        try:
            p, m = item.split(":", 1)
            return {"provider": p, "model": m}
        except Exception:
            return None
    
    fallbacks_structured = [x for x in (parse_fb(i) for i in selected_fallbacks) if x]
    
    # 高级设置
    enable_memory = False
    enable_debug = False
    max_tokens = 32000
    if show_advanced:
        with st.expander("⚙️ 高级设置"):
            enable_memory = st.checkbox(
                "启用记忆功能",
                value=False,
                key=f"{location}_enable_memory"
            )

            enable_debug = st.checkbox(
                "调试模式",
                value=False,
                key=f"{location}_enable_debug"
            )

            max_tokens = st.slider(
                "最大输出长度",
                min_value=1000,
                max_value=128000,
                value=32000,
                step=1000,
                key=f"{location}_max_tokens"
            )

            st.markdown("#### 👥 团队策略（按角色控制可用模型）")
            # 允许用户为关键角色指定允许/锁定模型，供本次会话即时覆写
            roles = [
                ("fundamental_expert", "基本面专家"),
                ("chief_decision_officer", "首席决策官"),
                ("technical_analyst", "技术分析师"),
                ("news_hunter", "快讯猎手"),
                ("sentiment_analyst", "情绪分析师"),
                ("tool_engineer", "工具工程师"),
            ]

            # 统一来源：从配置/后端载入硅基流动模型目录
            siliconflow_catalog = get_siliconflow_models()

            allowed_models_by_role = {}
            model_overrides = {}
            for role_key, role_label in roles:
                with st.expander(f"{role_label} ({role_key})", expanded=False):
                    allowed = st.multiselect(
                        f"允许的模型（留空则不限制） - {role_label}",
                        options=siliconflow_catalog + ["gemini-2.5-pro", "gemini-2.5-flash"],
                        default=[],
                        key=f"{location}_allowed_models_{role_key}"
                    )
                    locked = st.selectbox(
                        f"锁定模型（可选） - {role_label}",
                        options=["(不锁定)"] + siliconflow_catalog + ["gemini-2.5-pro", "gemini-2.5-flash"],
                        index=0,
                        key=f"{location}_locked_model_{role_key}"
                    )
                    if allowed:
                        allowed_models_by_role[role_key] = allowed
                    if locked and locked != "(不锁定)":
                        model_overrides[role_key] = locked

            # 将即时策略写入 session_state，供 web/utils/analysis_runner 或 web/app.py 传入 context
            st.session_state.allowed_models_by_role = allowed_models_by_role
            st.session_state.model_overrides = model_overrides
    
    # 保存到session state以供路由策略等使用
    if show_routing:
        st.session_state.routing_strategy_select = routing_strategy
        st.session_state.fallback_chain = fallbacks_structured
        st.session_state.max_budget = max_budget
    
    # 返回配置字典
    return {
        'llm_provider': st.session_state.llm_provider,
        'model_category': st.session_state.get('model_category'),
        'llm_quick_model': st.session_state.get('llm_quick_model'),
        'llm_deep_model': st.session_state.get('llm_deep_model'),
        'llm_model': st.session_state.get('llm_deep_model') or st.session_state.get('llm_model'),
        'routing_strategy': routing_strategy,
        'fallbacks': fallbacks_structured,
        'max_budget': max_budget,
        'enable_memory': enable_memory,
        'enable_debug': enable_debug,
        'max_tokens': max_tokens
    }


def _render_deepseek_models(location: str, preset: str) -> tuple:
    """渲染DeepSeek模型选择（统一来源）"""
    deepseek_options = get_deepseek_models() + ["💡 自定义模型"]
    
    # 预设默认组合
    if preset == "低成本":
        default_quick, default_deep = "deepseek-chat", "deepseek-chat"
    elif preset == "高质量":
        default_quick, default_deep = "deepseek-chat", "deepseek-reasoner"
    else:  # 均衡
        default_quick, default_deep = "deepseek-chat", "deepseek-chat"
    
    # 快速模型
    model_choice_quick = st.selectbox(
        "快速模型 (Quick)",
        options=deepseek_options,
        index=(deepseek_options.index(st.session_state.llm_quick_model)
               if st.session_state.llm_quick_model in deepseek_options else
               deepseek_options.index(default_quick)),
        format_func=lambda x: {
            "deepseek-chat": "DeepSeek Chat (V3) - 快速/高性价比",
            "deepseek-reasoner": "DeepSeek Reasoner (R1) - 推理更强(成本高)",
            "💡 自定义模型": "💡 自定义模型 - 输入任意模型名称"
        }.get(x, x),
        key=f"{location}_deepseek_quick_model_select"
    )
    
    # 深度模型
    model_choice_deep = st.selectbox(
        "深度模型 (Deep)",
        options=deepseek_options,
        index=(deepseek_options.index(st.session_state.llm_deep_model)
               if st.session_state.llm_deep_model in deepseek_options else
               deepseek_options.index(default_deep)),
        format_func=lambda x: {
            "deepseek-chat": "DeepSeek Chat (V3) - 通用/性价比",
            "deepseek-reasoner": "DeepSeek Reasoner (R1) - 深度推理优选",
            "💡 自定义模型": "💡 自定义模型 - 输入任意模型名称"
        }.get(x, x),
        key=f"{location}_deepseek_deep_model_select"
    )
    
    # 处理自定义输入（快速）
    if model_choice_quick == "💡 自定义模型":
        custom_model = st.text_input(
            "🔧 自定义DeepSeek快速模型",
            value=st.session_state.llm_quick_model if st.session_state.llm_quick_model not in deepseek_options else "",
            placeholder="例如: deepseek-chat, deepseek-reasoner等",
            key=f"{location}_deepseek_custom_input_quick"
        )
        
        if custom_model:
            is_valid, message = validate_custom_model_name(custom_model, "deepseek")
            if is_valid:
                if message.startswith("✅"):
                    st.success(message)
                else:
                    st.info(message)
                llm_quick_model = custom_model
            else:
                st.error(message)
                llm_quick_model = "deepseek-chat"
        else:
            st.warning("⚠️ 请输入模型名称，或选择预设模型")
            llm_quick_model = "deepseek-chat"
        
        render_model_help("deepseek")
    else:
        llm_quick_model = model_choice_quick
    
    # 处理自定义输入（深度）
    if model_choice_deep == "💡 自定义模型":
        custom_model_deep = st.text_input(
            "🔧 自定义DeepSeek深度模型",
            value=st.session_state.llm_deep_model if st.session_state.llm_deep_model not in deepseek_options else "",
            placeholder="例如: deepseek-reasoner",
            key=f"{location}_deepseek_custom_input_deep"
        )
        if custom_model_deep:
            is_valid, message = validate_custom_model_name(custom_model_deep, "deepseek")
            if is_valid:
                st.success(message) if message.startswith("✅") else st.info(message)
                llm_deep_model = custom_model_deep
            else:
                st.error(message)
                llm_deep_model = default_deep
        else:
            st.warning("⚠️ 请输入深度模型名称，或选择预设模型")
            llm_deep_model = default_deep
    else:
        llm_deep_model = model_choice_deep
    
    logger.debug(f"💾 [Persistence] DeepSeek模型已保存: quick={llm_quick_model}, deep={llm_deep_model}")
    
    return llm_quick_model, llm_deep_model


def _render_openrouter_models(location: str, preset: str) -> tuple:
    """渲染OpenRouter模型选择（含Gemini/Claude/OpenAI/Llama等）"""
    catalog = get_openrouter_models()
    options = catalog + ["💡 自定义模型"]

    # 预设：优先Gemini系列
    if preset == "低成本":
        default_quick, default_deep = "google/gemini-2.0-flash", "google/gemini-2.0-flash"
    elif preset == "高质量":
        default_quick, default_deep = "google/gemini-2.0-flash", "google/gemini-2.5-pro"
    else:
        default_quick, default_deep = "google/gemini-2.0-flash", "google/gemini-2.5-pro"

    def _fmt(name: str) -> str:
        mapping = {
            "google/gemini-2.5-pro": "Gemini 2.5 Pro (OpenRouter)",
            "google/gemini-2.0-flash": "Gemini 2.0 Flash (OpenRouter)",
            "google/gemini-1.5-pro": "Gemini 1.5 Pro (OpenRouter)",
            "anthropic/claude-3.5-sonnet": "Claude 3.5 Sonnet (OpenRouter)",
            "anthropic/claude-3.5-haiku": "Claude 3.5 Haiku (OpenRouter)",
            "openai/o4-mini-high": "OpenAI o4-mini-high (OpenRouter)",
            "openai/o3-pro": "OpenAI o3-pro (OpenRouter)",
            "meta-llama/llama-3.2-90b-instruct": "Llama 3.2 90B Instruct (OpenRouter)",
            "mistralai/mistral-large-latest": "Mistral Large (OpenRouter)",
            "💡 自定义模型": "💡 自定义模型",
        }
        return mapping.get(name, name)

    model_choice_quick = st.selectbox(
        "快速模型 (Quick)",
        options=options,
        index=(options.index(st.session_state.llm_quick_model)
               if st.session_state.llm_quick_model in options else
               (options.index(default_quick) if default_quick in options else 0)),
        format_func=_fmt,
        key=f"{location}_openrouter_quick_model_select"
    )

    model_choice_deep = st.selectbox(
        "深度模型 (Deep)",
        options=options,
        index=(options.index(st.session_state.llm_deep_model)
               if st.session_state.llm_deep_model in options else
               (options.index(default_deep) if default_deep in options else 0)),
        format_func=_fmt,
        key=f"{location}_openrouter_deep_model_select"
    )

    # 自定义模型（provider/model）
    if model_choice_quick == "💡 自定义模型":
        custom_model = st.text_input(
            "🔧 自定义OpenRouter快速模型",
            value=st.session_state.llm_quick_model if st.session_state.llm_quick_model not in options else "",
            placeholder="例如: google/gemini-2.0-flash 或 anthropic/claude-3.5-sonnet",
            key=f"{location}_openrouter_custom_input_quick"
        )
        if custom_model:
            is_valid, message = validate_custom_model_name(custom_model, "openrouter")
            if is_valid:
                st.success(message) if message.startswith("✅") else st.info(message)
                llm_quick_model = custom_model
            else:
                st.error(message)
                llm_quick_model = default_quick
        else:
            st.warning("⚠️ 请输入模型名称，或选择预设模型")
            llm_quick_model = default_quick
        render_model_help("openrouter")
    else:
        llm_quick_model = model_choice_quick

    if model_choice_deep == "💡 自定义模型":
        custom_model_deep = st.text_input(
            "🔧 自定义OpenRouter深度模型",
            value=st.session_state.llm_deep_model if st.session_state.llm_deep_model not in options else "",
            placeholder="例如: google/gemini-2.5-pro",
            key=f"{location}_openrouter_custom_input_deep"
        )
        if custom_model_deep:
            is_valid, message = validate_custom_model_name(custom_model_deep, "openrouter")
            if is_valid:
                st.success(message) if message.startswith("✅") else st.info(message)
                llm_deep_model = custom_model_deep
            else:
                st.error(message)
                llm_deep_model = default_deep
        else:
            st.warning("⚠️ 请输入深度模型名称，或选择预设模型")
            llm_deep_model = default_deep
    else:
        llm_deep_model = model_choice_deep

    logger.debug(f"💾 [Persistence] OpenRouter模型已保存: quick={llm_quick_model}, deep={llm_deep_model}")
    return llm_quick_model, llm_deep_model


def _render_gemini_api_models(location: str, preset: str) -> tuple:
    """渲染 Gemini-API(兼容) 渠道模型选择。"""
    from web.utils.model_catalog import get_gemini_api_models

    catalog = get_gemini_api_models()
    options = catalog + ["💡 自定义模型"]

    # 预设：与 Google 家族保持一致的默认
    if preset == "低成本":
        default_quick, default_deep = "gemini-2.0-flash", "gemini-2.0-flash"
    elif preset == "高质量":
        default_quick, default_deep = "gemini-2.0-flash", "gemini-2.5-pro"
    else:
        default_quick, default_deep = "gemini-2.0-flash", "gemini-2.5-pro"

    def _fmt(name: str) -> str:
        mapping = {
            "gemini-2.5-pro": "Gemini 2.5 Pro (Gemini-API)",
            "gemini-2.0-flash": "Gemini 2.0 Flash (Gemini-API)",
            "gemini-1.5-pro": "Gemini 1.5 Pro (Gemini-API)",
            "gemini-1.5-flash": "Gemini 1.5 Flash (Gemini-API)",
            "💡 自定义模型": "💡 自定义模型",
        }
        return mapping.get(name, name)

    model_choice_quick = st.selectbox(
        "快速模型 (Quick)",
        options=options,
        index=(options.index(st.session_state.llm_quick_model)
               if st.session_state.llm_quick_model in options else
               (options.index(default_quick) if default_quick in options else 0)),
        format_func=_fmt,
        key=f"{location}_gemini_api_quick_model_select"
    )

    model_choice_deep = st.selectbox(
        "深度模型 (Deep)",
        options=options,
        index=(options.index(st.session_state.llm_deep_model)
               if st.session_state.llm_deep_model in options else
               (options.index(default_deep) if default_deep in options else 0)),
        format_func=_fmt,
        key=f"{location}_gemini_api_deep_model_select"
    )

    # 自定义模型（与 Google 命名保持一致，便于迁移）
    if model_choice_quick == "💡 自定义模型":
        custom_model = st.text_input(
            "🔧 自定义Gemini-API快速模型",
            value=st.session_state.llm_quick_model if st.session_state.llm_quick_model not in options else "",
            placeholder="例如: gemini-2.0-flash, gemini-2.5-pro",
            key=f"{location}_gemini_api_custom_input_quick"
        )
        llm_quick_model = custom_model or default_quick
    else:
        llm_quick_model = model_choice_quick

    if model_choice_deep == "💡 自定义模型":
        custom_model_deep = st.text_input(
            "🔧 自定义Gemini-API深度模型",
            value=st.session_state.llm_deep_model if st.session_state.llm_deep_model not in options else "",
            placeholder="例如: gemini-2.5-pro",
            key=f"{location}_gemini_api_custom_input_deep"
        )
        llm_deep_model = custom_model_deep or default_deep
    else:
        llm_deep_model = model_choice_deep

    return llm_quick_model, llm_deep_model

def _render_google_models(location: str, preset: str) -> tuple:
    """渲染Google AI模型选择（统一来源）"""
    google_options = get_google_models() + ["💡 自定义模型"]
    
    if preset == "低成本":
        default_quick, default_deep = "gemini-2.5-flash", "gemini-2.5-flash"
    elif preset == "高质量":
        default_quick, default_deep = "gemini-2.5-flash", "gemini-2.5-pro"
    else:
        default_quick, default_deep = "gemini-2.0-flash", "gemini-2.5-pro"
    
    model_choice_quick = st.selectbox(
        "快速模型 (Quick)",
        options=google_options,
        index=(google_options.index(st.session_state.llm_quick_model)
               if st.session_state.llm_quick_model in google_options else
               google_options.index(default_quick)),
        format_func=lambda x: {
            "gemini-2.5-pro": "Gemini 2.5 Pro - 深度推理",
            "gemini-2.5-flash": "Gemini 2.5 Flash - 快速",
            "gemini-2.0-flash": "Gemini 2.0 Flash - 均衡",
            "💡 自定义模型": "💡 自定义模型"
        }.get(x, x),
        key=f"{location}_google_quick_model_select"
    )
    
    model_choice_deep = st.selectbox(
        "深度模型 (Deep)",
        options=google_options,
        index=(google_options.index(st.session_state.llm_deep_model)
               if st.session_state.llm_deep_model in google_options else
               google_options.index(default_deep)),
        format_func=lambda x: {
            "gemini-2.5-pro": "Gemini 2.5 Pro - 深度推理优选",
            "gemini-2.5-flash": "Gemini 2.5 Flash - 快速",
            "gemini-2.0-flash": "Gemini 2.0 Flash - 均衡",
            "💡 自定义模型": "💡 自定义模型"
        }.get(x, x),
        key=f"{location}_google_deep_model_select"
    )
    
    # 处理自定义输入
    if model_choice_quick == "💡 自定义模型":
        custom_model = st.text_input(
            "🔧 自定义Google快速模型",
            value=st.session_state.llm_quick_model if st.session_state.llm_quick_model not in google_options else "",
            placeholder="例如: gemini-2.5-flash, gemini-2.5-pro等",
            key=f"{location}_google_custom_input_quick"
        )
        
        if custom_model:
            is_valid, message = validate_custom_model_name(custom_model, "google")
            if is_valid:
                if message.startswith("✅"):
                    st.success(message)
                else:
                    st.info(message)
                llm_quick_model = custom_model
            else:
                st.error(message)
                llm_quick_model = default_quick
        else:
            st.warning("⚠️ 请输入模型名称，或选择预设模型")
            llm_quick_model = default_quick
        
        render_model_help("google")
    else:
        llm_quick_model = model_choice_quick
    
    if model_choice_deep == "💡 自定义模型":
        custom_model_deep = st.text_input(
            "🔧 自定义Google深度模型",
            value=st.session_state.llm_deep_model if st.session_state.llm_deep_model not in google_options else "",
            placeholder="例如: gemini-2.5-pro",
            key=f"{location}_google_custom_input_deep"
        )
        if custom_model_deep:
            is_valid, message = validate_custom_model_name(custom_model_deep, "google")
            if is_valid:
                st.success(message) if message.startswith("✅") else st.info(message)
                llm_deep_model = custom_model_deep
            else:
                st.error(message)
                llm_deep_model = default_deep
        else:
            st.warning("⚠️ 请输入深度模型名称，或选择预设模型")
            llm_deep_model = default_deep
    else:
        llm_deep_model = model_choice_deep
    
    logger.debug(f"💾 [Persistence] Google模型已保存: quick={llm_quick_model}, deep={llm_deep_model}")
    
    return llm_quick_model, llm_deep_model


def _render_siliconflow_models(location: str, preset: str) -> tuple:
    """渲染SiliconFlow模型选择（统一来源）"""
    catalog = get_siliconflow_models()
    # 补充‘自定义模型’入口
    siliconflow_options = catalog + ["💡 自定义模型"]
    
    if preset == "低成本":
        default_quick, default_deep = "deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-V3"
    elif preset == "高质量":
        default_quick, default_deep = "deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1"
    else:
        default_quick, default_deep = "deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1"
    
    def _fmt_model(name: str) -> str:
        mapping = {
            "deepseek-ai/DeepSeek-R1": "DeepSeek R1 - 推理强",
            "deepseek-ai/DeepSeek-V3": "DeepSeek V3 - 通用/推荐",
            "zai-org/GLM-4.5": "GLM-4.5 - 中文优秀",
            "moonshotai/Kimi-K2-Instruct": "Kimi K2 - 长文本",
            "Qwen/Qwen3-Coder-480B-A35B-Instruct": "Qwen3 Coder 480B - 代码/工具",
            "Qwen/Qwen3-235B-A22B-Instruct-2507": "Qwen3 235B Instruct - 通用",
            "Qwen/Qwen3-235B-A22B-Thinking-2507": "Qwen3 235B Thinking - 推理",
            "stepfun-ai/step3": "Step-3 - 多模态推理",
            "💡 自定义模型": "💡 自定义模型",
        }
        return mapping.get(name, name)

    model_choice_quick = st.selectbox(
        "快速模型 (Quick)",
        options=siliconflow_options,
        index=(siliconflow_options.index(st.session_state.llm_quick_model)
               if st.session_state.llm_quick_model in siliconflow_options else
               (siliconflow_options.index(default_quick) if default_quick in siliconflow_options else 0)),
        format_func=_fmt_model,
        key=f"{location}_siliconflow_quick_model_select"
    )
    
    model_choice_deep = st.selectbox(
        "深度模型 (Deep)",
        options=siliconflow_options,
        index=(siliconflow_options.index(st.session_state.llm_deep_model)
               if st.session_state.llm_deep_model in siliconflow_options else
               (siliconflow_options.index(default_deep) if default_deep in siliconflow_options else 0)),
        format_func=_fmt_model,
        key=f"{location}_siliconflow_deep_model_select"
    )
    
    # 处理自定义输入
    if model_choice_quick == "💡 自定义模型":
        custom_model = st.text_input(
            "🔧 自定义SiliconFlow快速模型",
            value=st.session_state.llm_quick_model if st.session_state.llm_quick_model not in siliconflow_options else "",
            placeholder="例如: deepseek-ai/DeepSeek-R1, gemini-1.5-pro 等",
            key=f"{location}_siliconflow_custom_input_quick"
        )
        
        if custom_model:
            is_valid, message = validate_custom_model_name(custom_model, "siliconflow")
            if is_valid:
                if message.startswith("✅"):
                    st.success(message)
                else:
                    st.info(message)
                llm_quick_model = custom_model
            else:
                st.error(message)
                llm_quick_model = default_quick
        else:
            st.warning("⚠️ 请输入模型名称，或选择预设模型")
            llm_quick_model = default_quick
        
        render_model_help("siliconflow")
    else:
        llm_quick_model = model_choice_quick
    
    if model_choice_deep == "💡 自定义模型":
        custom_model_deep = st.text_input(
            "🔧 自定义SiliconFlow深度模型",
            value=st.session_state.llm_deep_model if st.session_state.llm_deep_model not in siliconflow_options else "",
            placeholder="例如: deepseek-ai/DeepSeek-R1",
            key=f"{location}_siliconflow_custom_input_deep"
        )
        if custom_model_deep:
            is_valid, message = validate_custom_model_name(custom_model_deep, "siliconflow")
            if is_valid:
                st.success(message) if message.startswith("✅") else st.info(message)
                llm_deep_model = custom_model_deep
            else:
                st.error(message)
                llm_deep_model = default_deep
        else:
            st.warning("⚠️ 请输入深度模型名称，或选择预设模型")
            llm_deep_model = default_deep
    else:
        llm_deep_model = model_choice_deep
    
    logger.debug(f"💾 [Persistence] SiliconFlow模型已保存: quick={llm_quick_model}, deep={llm_deep_model}")
    
    return llm_quick_model, llm_deep_model
