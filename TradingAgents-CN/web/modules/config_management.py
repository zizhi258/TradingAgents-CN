#!/usr/bin/env python3
"""
配置管理页面
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import os

# 添加项目根目录到路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入UI工具函数
sys.path.append(str(Path(__file__).parent.parent))
from utils.ui_utils import apply_hide_deploy_button_css

from tradingagents.config.config_manager import (
    config_manager, ModelConfig, PricingConfig
)

# 导入环境变量编辑器
from tradingagents.config.env_editor import (
    read_env, merge_and_write_env, get_effective_env_value, 
    mask_secret_value, validate_env_value
)
from tradingagents.config.env_metadata import (
    ENV_FIELDS, GROUP_ORDER, get_fields_by_group,
    get_field_metadata, is_known_field,
    get_field_label, get_field_help, get_field_placeholder, GROUP_HELP
)
from tradingagents.config.env_utils import parse_bool_env  # 布尔解析


def render_config_management():
    """渲染配置管理页面"""
    # 应用隐藏Deploy按钮的CSS样式
    apply_hide_deploy_button_css()
    
    st.title("⚙️ 配置管理")

    # 显示.env配置状态
    render_env_status()

    # 由于主应用全局CSS隐藏了Sidebar，这里改为页内Tab导航，避免功能被隐藏
    tabs = st.tabs(["模型配置", "定价设置", "使用统计", "系统设置", "环境变量 (.env)"])

    with tabs[0]:
        render_model_config()
    with tabs[1]:
        render_pricing_config()
    with tabs[2]:
        render_usage_statistics()
    with tabs[3]:
        render_system_settings()
    with tabs[4]:
        render_env_editor()


def render_model_config():
    """渲染模型配置页面"""
    st.subheader("当前：模型配置")
    
    # 加载现有配置
    models = config_manager.load_models()

    # 显示当前配置
    st.markdown("**当前模型配置**")
    
    if models:
        # 创建DataFrame显示
        model_data = []
        env_status = config_manager.get_env_config_status()

        for i, model in enumerate(models):
            # 检查API密钥来源
            env_has_key = env_status["api_keys"].get(model.provider.lower(), False)
            api_key_display = "***" + model.api_key[-4:] if model.api_key else "未设置"
            if env_has_key:
                api_key_display += " (.env)"

            model_data.append({
                "序号": i,
                "供应商": model.provider,
                "模型名称": model.model_name,
                "API密钥": api_key_display,
                "最大Token": model.max_tokens,
                "温度": model.temperature,
                "状态": "✅ 启用" if model.enabled else "❌ 禁用"
            })
        
        df = pd.DataFrame(model_data)
        st.dataframe(df, use_container_width=True)
        
        # 编辑模型配置
        st.markdown("**编辑模型配置**")
        
        # 选择要编辑的模型
        model_options = [f"{m.provider} - {m.model_name}" for m in models]
        selected_model_idx = st.selectbox("选择要编辑的模型", range(len(model_options)),
                                         format_func=lambda x: model_options[x],
                                         key="select_model_to_edit")
        
        if selected_model_idx is not None:
            model = models[selected_model_idx]

            # 检查是否来自.env
            env_has_key = env_status["api_keys"].get(model.provider.lower(), False)
            if env_has_key:
                st.info(f"💡 此模型的API密钥来自 .env 文件，修改 .env 文件后需重启应用生效")

            col1, col2 = st.columns(2)

            with col1:
                new_api_key = st.text_input("API密钥", value=model.api_key, type="password", key=f"edit_api_key_{selected_model_idx}")
                if env_has_key:
                    st.caption("⚠️ 此密钥来自 .env 文件，Web修改可能被覆盖")
                new_max_tokens = st.number_input("最大Token数", value=model.max_tokens, min_value=1000, max_value=128000, key=f"edit_max_tokens_{selected_model_idx}")
                new_temperature = st.slider("温度参数", 0.0, 2.0, model.temperature, 0.1, key=f"edit_temperature_{selected_model_idx}")

            with col2:
                new_enabled = st.checkbox("启用模型", value=model.enabled, key=f"edit_enabled_{selected_model_idx}")
                new_base_url = st.text_input("自定义API地址 (可选)", value=model.base_url or "", key=f"edit_base_url_{selected_model_idx}")
            
            if st.button("保存配置", type="primary", key=f"save_model_config_{selected_model_idx}"):
                # 更新模型配置
                models[selected_model_idx] = ModelConfig(
                    provider=model.provider,
                    model_name=model.model_name,
                    api_key=new_api_key,
                    base_url=new_base_url if new_base_url else None,
                    max_tokens=new_max_tokens,
                    temperature=new_temperature,
                    enabled=new_enabled
                )
                
                config_manager.save_models(models)
                st.success("✅ 配置已保存！")
                st.rerun()
                return
    
    else:
        st.warning("没有找到模型配置")
    
    # 添加新模型
    st.markdown("**添加新模型**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_provider = st.selectbox("供应商", ["deepseek", "google", "openrouter", "siliconflow", "other"], key="new_provider")
        new_model_name = st.text_input("模型名称", placeholder="例如: gemini-1.5-pro, deepseek-chat", key="new_model_name")
        new_api_key = st.text_input("API密钥", type="password", key="new_api_key")

    with col2:
        new_max_tokens = st.number_input("最大Token数", value=32000, min_value=1000, max_value=128000, key="new_max_tokens")
        new_temperature = st.slider("温度参数", 0.0, 2.0, 0.7, 0.1, key="new_temperature")
        new_enabled = st.checkbox("启用模型", value=True, key="new_enabled")
    
    if st.button("添加模型", key="add_new_model"):
        if new_provider and new_model_name and new_api_key:
            new_model = ModelConfig(
                provider=new_provider,
                model_name=new_model_name,
                api_key=new_api_key,
                max_tokens=new_max_tokens,
                temperature=new_temperature,
                enabled=new_enabled
            )
            
            models.append(new_model)
            config_manager.save_models(models)
            st.success("✅ 新模型已添加！")
            st.rerun()
            return
        else:
            st.error("请填写所有必需字段")


def render_pricing_config():
    """渲染定价配置页面"""
    st.subheader("当前：定价设置")

    # 加载现有定价
    pricing_configs = config_manager.load_pricing()

    # 显示当前定价
    st.markdown("**当前定价配置**")
    
    if pricing_configs:
        pricing_data = []
        for i, pricing in enumerate(pricing_configs):
            pricing_data.append({
                "序号": i,
                "供应商": pricing.provider,
                "模型名称": pricing.model_name,
                "输入价格 (每1K token)": f"{pricing.input_price_per_1k} {pricing.currency}",
                "输出价格 (每1K token)": f"{pricing.output_price_per_1k} {pricing.currency}",
                "货币": pricing.currency
            })
        
        df = pd.DataFrame(pricing_data)
        st.dataframe(df, use_container_width=True)
        
        # 编辑定价
        st.markdown("**编辑定价**")
        
        pricing_options = [f"{p.provider} - {p.model_name}" for p in pricing_configs]
        selected_pricing_idx = st.selectbox("选择要编辑的定价", range(len(pricing_options)),
                                          format_func=lambda x: pricing_options[x],
                                          key="select_pricing_to_edit")
        
        if selected_pricing_idx is not None:
            pricing = pricing_configs[selected_pricing_idx]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                new_input_price = st.number_input("输入价格 (每1K token)",
                                                value=pricing.input_price_per_1k,
                                                min_value=0.0, step=0.001, format="%.6f",
                                                key=f"edit_input_price_{selected_pricing_idx}")

            with col2:
                new_output_price = st.number_input("输出价格 (每1K token)",
                                                 value=pricing.output_price_per_1k,
                                                 min_value=0.0, step=0.001, format="%.6f",
                                                 key=f"edit_output_price_{selected_pricing_idx}")

            with col3:
                new_currency = st.selectbox("货币", ["CNY", "USD", "EUR"],
                                          index=["CNY", "USD", "EUR"].index(pricing.currency),
                                          key=f"edit_currency_{selected_pricing_idx}")
            
            if st.button("保存定价", type="primary", key=f"save_pricing_config_{selected_pricing_idx}"):
                pricing_configs[selected_pricing_idx] = PricingConfig(
                    provider=pricing.provider,
                    model_name=pricing.model_name,
                    input_price_per_1k=new_input_price,
                    output_price_per_1k=new_output_price,
                    currency=new_currency
                )
                
                config_manager.save_pricing(pricing_configs)
                st.success("✅ 定价已保存！")
                st.rerun()
                return
    
    # 添加新定价
    st.markdown("**添加新定价**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        new_provider = st.text_input("供应商", placeholder="例如: deepseek, google", key="new_pricing_provider")
        new_model_name = st.text_input("模型名称", placeholder="例如: gpt-4, deepseek-chat", key="new_pricing_model")
        new_currency = st.selectbox("货币", ["CNY", "USD", "EUR"], key="new_pricing_currency")

    with col2:
        new_input_price = st.number_input("输入价格 (每1K token)", min_value=0.0, step=0.001, format="%.6f", key="new_pricing_input")
        new_output_price = st.number_input("输出价格 (每1K token)", min_value=0.0, step=0.001, format="%.6f", key="new_pricing_output")
    
    if st.button("添加定价", key="add_new_pricing"):
        if new_provider and new_model_name:
            new_pricing = PricingConfig(
                provider=new_provider,
                model_name=new_model_name,
                input_price_per_1k=new_input_price,
                output_price_per_1k=new_output_price,
                currency=new_currency
            )
            
            pricing_configs.append(new_pricing)
            config_manager.save_pricing(pricing_configs)
            st.success("✅ 新定价已添加！")
            st.rerun()
            return
        else:
            st.error("请填写供应商和模型名称")


def render_usage_statistics():
    """渲染使用统计页面（摘要 + 跳转型）"""
    st.subheader("当前：使用统计")

    # 显示页面迁移提示
    st.info("💡 **完整的Token使用统计功能已迁移至 📈 历史记录 > 统计分析 > 💰 Token使用统计**")
    
    # 获取近30天的统计数据作为摘要
    stats = config_manager.get_usage_statistics(30)

    if stats["total_requests"] == 0:
        st.warning("📝 近30天暂无使用记录")
        
        # 提供跳转按钮
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔗 前往历史记录页面查看详细统计", type="primary", use_container_width=True):
                # 使用安全的导航重定向键，避免直接修改已实例化的控件状态
                st.session_state['_nav_redirect_to'] = "📈 历史记录"
                st.session_state.history_active_tab = 'stats'
                st.rerun()
                return
        
        return

    # 近30天使用摘要（仅显示核心指标）
    st.markdown("**📊 近30天使用摘要**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 总成本", f"¥{stats['total_cost']:.4f}")
    
    with col2:
        st.metric("🔢 总请求数", f"{stats['total_requests']:,}")
    
    with col3:
        total_tokens = stats['total_input_tokens'] + stats['total_output_tokens']
        st.metric("📊 总Token数", f"{total_tokens:,}")
    
    with col4:
        avg_cost = stats['total_cost'] / stats['total_requests'] if stats['total_requests'] > 0 else 0
        st.metric("⚖️ 平均每次成本", f"¥{avg_cost:.4f}")
    
    # 提供跳转到完整统计页面的按钮
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔗 查看完整Token使用统计与图表分析", type="primary", use_container_width=True):
            # 设置跳转到历史记录页面，并激活统计分析标签页（使用安全重定向键）
            st.session_state['_nav_redirect_to'] = "📈 历史记录"
            st.session_state.history_active_tab = 'stats'
            st.rerun()
            return
    
    st.caption("💡 点击上方按钮查看详细的Token使用统计、图表分析、供应商对比和明细记录")


def render_system_settings():
    """渲染系统设置页面"""
    st.subheader("当前：系统设置")

    # 加载当前设置
    settings = config_manager.load_settings()

    st.markdown("**基本设置**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        providers = ["deepseek", "google", "siliconflow"]
        raw_default = str(settings.get("default_provider", "deepseek")).lower()
        try:
            idx = providers.index(raw_default)
        except ValueError:
            idx = 0  # fallback to first provider
        
        default_provider = st.selectbox(
            "默认供应商",
            providers,
            index=idx,
            key="settings_default_provider"
        )

        enable_cost_tracking = st.checkbox(
            "启用成本跟踪",
            value=settings.get("enable_cost_tracking", True),
            key="settings_enable_cost_tracking"
        )

        currency_preference = st.selectbox(
            "首选货币",
            ["CNY", "USD", "EUR"],
            index=["CNY", "USD", "EUR"].index(
                settings.get("currency_preference", "CNY")
            ),
            key="settings_currency_preference"
        )
    
    with col2:
        default_model = st.text_input(
            "默认模型",
            value=settings.get("default_model", "deepseek-chat"),
            key="settings_default_model"
        )

        cost_alert_threshold = st.number_input(
            "成本警告阈值",
            value=settings.get("cost_alert_threshold", 100.0),
            min_value=0.0,
            step=10.0,
            key="settings_cost_alert_threshold"
        )

        max_usage_records = st.number_input(
            "最大使用记录数",
            value=settings.get("max_usage_records", 10000),
            min_value=1000,
            max_value=100000,
            step=1000,
            key="settings_max_usage_records"
        )

    auto_save_usage = st.checkbox(
        "自动保存使用记录",
        value=settings.get("auto_save_usage", True),
        key="settings_auto_save_usage"
    )
    
    if st.button("保存设置", type="primary", key="save_system_settings"):
        new_settings = {
            "default_provider": default_provider,
            "default_model": default_model,
            "enable_cost_tracking": enable_cost_tracking,
            "cost_alert_threshold": cost_alert_threshold,
            "currency_preference": currency_preference,
            "auto_save_usage": auto_save_usage,
            "max_usage_records": max_usage_records
        }
        
        config_manager.save_settings(new_settings)
        st.success("✅ 设置已保存！")
        st.rerun()
        return
    
    # 数据管理
    st.markdown("**数据管理**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("导出配置", help="导出所有配置到JSON文件", key="export_config"):
            # 这里可以实现配置导出功能
            st.info("配置导出功能开发中...")
    
    with col2:
        if st.button("清空使用记录", help="清空所有使用记录", key="clear_usage_records"):
            if st.session_state.get("confirm_clear", False):
                config_manager.save_usage_records([])
                st.success("✅ 使用记录已清空！")
                st.session_state.confirm_clear = False
                st.rerun()
                return
            else:
                st.session_state.confirm_clear = True
                st.warning("⚠️ 再次点击确认清空")
    
    with col3:
        if st.button("重置配置", help="重置所有配置到默认值", key="reset_all_config"):
            if st.session_state.get("confirm_reset", False):
                # 删除配置文件，重新初始化
                import shutil
                if config_manager.config_dir.exists():
                    shutil.rmtree(config_manager.config_dir)
                config_manager._init_default_configs()
                st.success("✅ 配置已重置！")
                st.session_state.confirm_reset = False
                st.rerun()
                return
            else:
                st.session_state.confirm_reset = True
                st.warning("⚠️ 再次点击确认重置")


def render_env_status():
    """显示.env配置状态"""
    st.markdown("**📋 配置状态概览**")

    # 获取.env配置状态
    env_status = config_manager.get_env_config_status()

    # 显示.env文件状态
    col1, col2 = st.columns(2)

    with col1:
        if env_status["env_file_exists"]:
            st.success("✅ .env 文件已存在")
        else:
            st.error("❌ .env 文件不存在")
            st.info("💡 请复制 .env.example 为 .env 并配置API密钥")

    with col2:
        # 统计已配置的API密钥数量
        configured_keys = sum(1 for configured in env_status["api_keys"].values() if configured)
        total_keys = len(env_status["api_keys"])
        st.metric("API密钥配置", f"{configured_keys}/{total_keys}")

    # 显示演示模式状态（仅替换输入数据，其余流程不变）
    try:
        from tradingagents.config.env_editor import read_env, get_effective_env_value
        env_path = project_root / ".env"
        _raw, env_kv = read_env(env_path)
        # 读取并解析 DEMO_MODE
        demo_mode_effective = get_effective_env_value("DEMO_MODE", env_kv.get("DEMO_MODE", "")) or "false"
        demo_mode_on = str(demo_mode_effective).strip().lower() in {"true", "1", "yes", "on", "enable", "enabled", "t", "y", "ok", "okay"}
        # 读取 DEMO_DATA_FILE
        demo_file_effective = get_effective_env_value("DEMO_DATA_FILE", env_kv.get("DEMO_DATA_FILE", ""))
        if not demo_file_effective:
            demo_file_effective = "data/demo/changan_000625_demo.json"
        # 解析存在性
        demo_file_path = Path(demo_file_effective)
        if not demo_file_path.is_absolute():
            demo_file_path = project_root / demo_file_path
        exists = demo_file_path.exists()

        st.markdown("**🧪 演示模式（仅替代输入数据）**")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.metric("演示模式", "开启" if demo_mode_on else "关闭")
        with c2:
            st.caption("演示数据文件：")
            st.code(str(demo_file_path), language="bash")
        with c3:
            if exists:
                st.success("演示数据文件存在")
            else:
                st.error("演示数据文件不存在")
    except Exception as e:
        st.warning(f"无法读取演示模式状态：{e}")

    # 详细API密钥状态
    with st.expander("🔑 API密钥详细状态", expanded=False):
        api_col1, api_col2 = st.columns(2)

        with api_col1:
            st.write("**大模型API密钥:**")
            for provider, configured in env_status["api_keys"].items():
                if provider in ["deepseek", "google"]:
                    status = "✅ 已配置" if configured else "❌ 未配置"
                    provider_name = {
                        "deepseek": "DeepSeek",
                        "google": "Google AI"
                    }.get(provider, provider)
                    st.write(f"- {provider_name}: {status}")

        with api_col2:
            st.write("**其他API密钥:**")
            finnhub_status = "✅ 已配置" if env_status["api_keys"]["finnhub"] else "❌ 未配置"
            st.write(f"- FinnHub (金融数据): {finnhub_status}")

            reddit_status = "✅ 已配置" if env_status["other_configs"]["reddit_configured"] else "❌ 未配置"
            st.write(f"- Reddit API: {reddit_status}")

    # 配置优先级说明
    st.info("""
    📌 **配置优先级说明:**
    - API密钥优先从 `.env` 文件读取
    - Web界面配置作为补充和管理工具
    - 修改 `.env` 文件后需重启应用生效
    - 推荐使用 `.env` 文件管理敏感信息
    """)

    st.divider()

    # 演示模式状态概览
    demo_mode = str(os.getenv('DEMO_MODE', 'false')).lower() == 'true'
    demo_path = os.getenv('DEMO_DATA_FILE', 'data/demo/changan_000625_demo.json')
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.metric("演示模式", "开启" if demo_mode else "关闭")
        if st.toggle("切换演示模式", value=demo_mode, key="demo_mode_toggle", help="切换演示模式后需要重启应用才能生效"):
            if not demo_mode:
                st.session_state['DEMO_MODE'] = 'true'
            else:
                st.session_state['DEMO_MODE'] = 'false'
        else:
            if not demo_mode:
                st.session_state['DEMO_MODE'] = 'false'
            else:
                st.session_state['DEMO_MODE'] = 'true'

    with dcol2:
        st.caption(f"演示数据文件: {demo_path}")


def render_env_editor():
    """渲染环境变量(.env)编辑器"""
    st.subheader("当前：环境变量 (.env)")
    
    # .env文件路径
    env_path = project_root / ".env"
    
    # 读取.env文件
    raw_text, env_dict = read_env(env_path)
    
    # 文件状态信息
    col1, col2, col3 = st.columns(3)
    with col1:
        if env_path.exists():
            st.success("✅ .env 文件存在")
        else:
            st.error("❌ .env 文件不存在")
            
    with col2:
        configured_count = len(env_dict)
        st.metric("已配置变量", f"{configured_count}")
        
    with col3:
        total_known = len(ENV_FIELDS)
        st.metric("已知变量", f"{total_known}")
    
    st.info("💡 修改环境变量后需要重启应用才能生效")
    
    # 分组显示环境变量
    fields_by_group = get_fields_by_group()
    
    # 初始化会话状态
    if 'env_changes' not in st.session_state:
        st.session_state.env_changes = {}
    if 'env_to_remove' not in st.session_state:
        st.session_state.env_to_remove = set()
    
    # 操作按钮
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("💾 保存所有变更", type="primary", key="save_env_changes"):
            if st.session_state.env_changes or st.session_state.env_to_remove:
                try:
                    merge_and_write_env(
                        env_path, 
                        raw_text, 
                        st.session_state.env_changes,
                        list(st.session_state.env_to_remove)
                    )
                    st.success(f"✅ 已保存 {len(st.session_state.env_changes)} 个变更")
                    st.info("🔄 请重启应用以应用变更: docker-compose restart web")
                    
                    # 清理会话状态
                    st.session_state.env_changes = {}
                    st.session_state.env_to_remove = set()
                    st.rerun()
                    return
                    
                except Exception as e:
                    st.error(f"❌ 保存失败: {e}")
            else:
                st.warning("没有需要保存的变更")
    
    with col2:
        if st.button("🔄 重新加载", key="reload_env"):
            st.session_state.env_changes = {}
            st.session_state.env_to_remove = set()
            st.rerun()
            return
            
    with col3:
        if st.button("🧹 清理变更", key="clear_env_changes"):
            st.session_state.env_changes = {}
            st.session_state.env_to_remove = set()
            st.success("已清理所有未保存的变更")
    
    with col4:
        # 显示待保存的变更数量
        changes_count = len(st.session_state.env_changes) + len(st.session_state.env_to_remove)
        if changes_count > 0:
            st.warning(f"⚠️ 有 {changes_count} 个未保存变更")
    
    # 按组显示字段
    for group in GROUP_ORDER:
        if group not in fields_by_group:
            continue
            
        with st.expander(f"📁 {group}", expanded=(group == "API Keys")):
            # 显示分组帮助文本
            help_text = GROUP_HELP.get(group)
            if help_text:
                st.caption(help_text)
                
            fields = fields_by_group[group]
            
            for field in fields:
                key = field["key"]
                field_type = field["type"]
                
                # 获取中文标签和帮助文本
                label = get_field_label(key)
                help_text = get_field_help(key)
                placeholder = get_field_placeholder(key)
                
                # 当前值（.env文件中的值）
                env_value = env_dict.get(key, "")
                # 实际生效值（环境变量优先）
                effective_value = get_effective_env_value(key, env_value)
                # 显示值（考虑用户的修改）
                display_value = st.session_state.env_changes.get(key, env_value)
                
                # 创建两列布局
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    # 根据类型渲染不同的输入控件
                    if field_type == "secret":
                        # 密钥字段
                        if display_value:
                            default_placeholder = mask_secret_value(display_value)
                        else:
                            default_placeholder = "输入API密钥..."
                        
                        actual_placeholder = placeholder or default_placeholder
                            
                        new_value = st.text_input(
                            f"🔑 {label}",
                            value="",  # 不显示实际值
                            placeholder=actual_placeholder,
                            type="password",
                            help=help_text,
                            key=f"env_input_{key}"
                        )
                        
                        # 显示变量名
                        st.caption(f"变量名：{key}")
                        
                        # 只有在输入了新值时才记录变更
                        if new_value and new_value != display_value:
                            is_valid, err = validate_env_value(key, new_value, field_type)
                            if not is_valid:
                                st.error(err or "该取值不合法，请检查格式或范围")
                            else:
                                st.session_state.env_changes[key] = new_value
                            
                    elif field_type == "bool":
                        # 布尔值
                        current_bool = display_value.lower() == "true"
                        new_bool = st.toggle(
                            f"⚡ {label}",
                            value=current_bool,
                            help=help_text,
                            key=f"env_toggle_{key}"
                        )
                        
                        # 显示变量名
                        st.caption(f"变量名：{key}")
                        
                        new_value = "true" if new_bool else "false"
                        if new_value != display_value:
                            is_valid, err = validate_env_value(key, new_value, field_type)
                            if not is_valid:
                                st.error(err or "该取值不合法，请检查格式或范围")
                            else:
                                st.session_state.env_changes[key] = new_value
                            
                    elif field_type == "int":
                        # 整数
                        try:
                            current_int = int(display_value) if display_value else 0
                        except ValueError:
                            current_int = 0
                            
                        new_int = st.number_input(
                            f"🔢 {label}",
                            value=current_int,
                            help=help_text,
                            key=f"env_number_{key}"
                        )
                        
                        # 显示变量名
                        st.caption(f"变量名：{key}")
                        
                        new_value = str(new_int)
                        if new_value != display_value:
                            is_valid, err = validate_env_value(key, new_value, field_type)
                            if not is_valid:
                                st.error(err or "该取值不合法，请检查格式或范围")
                            else:
                                st.session_state.env_changes[key] = new_value
                            
                    elif field_type == "float":
                        # 浮点数
                        try:
                            current_float = float(display_value) if display_value else 0.0
                        except ValueError:
                            current_float = 0.0
                            
                        new_float = st.number_input(
                            f"💰 {label}",
                            value=current_float,
                            format="%.2f",
                            help=help_text,
                            key=f"env_float_{key}"
                        )
                        
                        # 显示变量名
                        st.caption(f"变量名：{key}")
                        
                        new_value = str(new_float)
                        if new_value != display_value:
                            is_valid, err = validate_env_value(key, new_value, field_type)
                            if not is_valid:
                                st.error(err or "该取值不合法，请检查格式或范围")
                            else:
                                st.session_state.env_changes[key] = new_value
                            
                    elif field_type == "select":
                        # 选择框
                        meta = get_field_metadata(key) or {}
                        options = meta.get("options", [])
                        options_cn = meta.get("options_cn", {})
                        
                        # 构造显示列表
                        display_options = [options_cn.get(opt, opt) for opt in options]
                        
                        # 当前值对应的 index
                        if display_value in options:
                            current_index = options.index(display_value)
                        else:
                            current_index = 0
                            
                        # 选择中文展示
                        new_display = st.selectbox(
                            f"📋 {label}",
                            options=display_options,
                            index=current_index,
                            help=help_text,
                            key=f"env_select_{key}"
                        )
                        
                        # 显示变量名
                        st.caption(f"变量名：{key}")
                        
                        # 反解英文值
                        new_selection = options[display_options.index(new_display)] if new_display in display_options else options[0]
                        
                        if new_selection != display_value:
                            is_valid, err = validate_env_value(key, new_selection, field_type)
                            if not is_valid:
                                st.error(err or "该取值不合法，请检查格式或范围")
                            else:
                                st.session_state.env_changes[key] = new_selection
                            
                    else:
                        # 普通字符串
                        actual_placeholder = placeholder or "输入配置值..."
                        
                        new_value = st.text_input(
                            f"📝 {label}",
                            value=display_value,
                            placeholder=actual_placeholder,
                            help=help_text,
                            key=f"env_text_{key}"
                        )
                        
                        # 显示变量名
                        st.caption(f"变量名：{key}")
                        
                        if new_value != display_value:
                            is_valid, err = validate_env_value(key, new_value, field_type)
                            if not is_valid:
                                st.error(err or "该取值不合法，请检查格式或范围")
                            else:
                                st.session_state.env_changes[key] = new_value
                
                with col2:
                    # 显示状态信息
                    if effective_value != env_value:
                        st.warning("🔄 系统环境变量覆盖")
                        if field_type == "secret":
                            st.caption(f"生效值: {mask_secret_value(effective_value)}")
                        else:
                            st.caption(f"生效值: {effective_value}")
                    elif env_value:
                        if field_type == "secret":
                            st.success(f"📁 {mask_secret_value(env_value)}")
                        else:
                            st.success(f"📁 {env_value}")
                    else:
                        st.info("未设置")
                    
                    # 删除按钮
                    if env_value:  # 只有已设置的值才能删除
                        if st.button("🗑️", help=f"删除 {key}", key=f"delete_{key}"):
                            st.session_state.env_to_remove.add(key)
                            if key in st.session_state.env_changes:
                                del st.session_state.env_changes[key]
                            st.rerun()
                            return
    
    # 显示未知字段（.env中存在但不在元数据中的字段）
    unknown_keys = [k for k in env_dict.keys() if not is_known_field(k)]
    if unknown_keys:
        with st.expander(f"❓ 其他字段 ({len(unknown_keys)} 个)", expanded=False):
            st.caption("这些字段在.env文件中存在，但不在已知字段列表中")
            
            for key in unknown_keys:
                value = env_dict[key]
                effective_value = get_effective_env_value(key, value)
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    new_value = st.text_input(
                        f"❓ {key}",
                        value=st.session_state.env_changes.get(key, value),
                        help="未知字段，请谨慎修改",
                        key=f"env_unknown_{key}"
                    )
                    
                    if new_value != value:
                        st.session_state.env_changes[key] = new_value
                
                with col2:
                    if effective_value != value:
                        st.warning("🔄 系统覆盖")
                        st.caption(f"生效: {effective_value}")
                    else:
                        st.info(f"📁 {value}")
                        
                    if st.button("🗑️", help=f"删除 {key}", key=f"delete_unknown_{key}"):
                        st.session_state.env_to_remove.add(key)
                        if key in st.session_state.env_changes:
                            del st.session_state.env_changes[key]
                        st.rerun()
                        return
    
    # 添加新字段
    with st.expander("➕ 添加新字段", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_key = st.text_input("字段名", placeholder="NEW_VARIABLE", key="new_env_key")
        with col2:
            new_value = st.text_input("值", placeholder="value", key="new_env_value") 
        with col3:
            if st.button("添加", key="add_new_env_field"):
                if new_key and new_value:
                    if new_key.upper() == new_key and new_key.replace('_', '').isalnum():
                        st.session_state.env_changes[new_key] = new_value
                        st.success(f"已添加 {new_key}")
                        st.rerun()
                        return
                    else:
                        st.error("字段名必须是大写字母、数字和下划线的组合")
                else:
                    st.error("请填写字段名和值")


def main():
    """主函数"""
    st.set_page_config(
        page_title="配置管理 - TradingAgents",
        page_icon="⚙️",
        layout="wide"
    )
    
    render_config_management()

if __name__ == "__main__":
    main()
