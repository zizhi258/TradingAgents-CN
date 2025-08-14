#!/usr/bin/env python3
"""
UI工具函数
提供通用的UI组件和样式，以及简易的持久化小工具。
"""

import json
from pathlib import Path
import streamlit as st

# 计算项目根目录与配置目录
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[2]
_CONFIG_DIR = _PROJECT_ROOT / "config"
_UI_OVERRIDES_FILE = _CONFIG_DIR / "ui_overrides.json"


def _ensure_config_dir():
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def load_ui_overrides() -> dict:
    """加载UI持久化配置（如按角色的模型锁定/允许集）。

    返回结构示例：
    {
      "model_overrides": {"fundamental_expert": "gemini-2.5-pro"},
      "allowed_models_by_role": {"technical_analyst": ["deepseek-ai/DeepSeek-V3"]}
    }
    """
    try:
        if _UI_OVERRIDES_FILE.exists():
            with _UI_OVERRIDES_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if not isinstance(data, dict):
                    return {}
                return data
    except Exception:
        pass
    return {}


def save_ui_overrides(data: dict) -> None:
    """保存UI持久化配置到 config/ui_overrides.json。"""
    _ensure_config_dir()
    try:
        with _UI_OVERRIDES_FILE.open("w", encoding="utf-8") as f:
            json.dump(data or {}, f, ensure_ascii=False, indent=2)
    except Exception:
        # 静默失败，避免阻塞页面
        pass


def save_role_model_override(role_key: str, model_name: str) -> None:
    """为某个角色持久化锁定模型。"""
    data = load_ui_overrides()
    model_overrides = data.get("model_overrides", {}) or {}
    if model_name:
        model_overrides[role_key] = model_name
    else:
        model_overrides.pop(role_key, None)
    data["model_overrides"] = model_overrides
    save_ui_overrides(data)


def clear_role_model_override(role_key: str) -> None:
    """清除某个角色的持久化锁定模型。"""
    data = load_ui_overrides()
    model_overrides = data.get("model_overrides", {}) or {}
    if role_key in model_overrides:
        model_overrides.pop(role_key, None)
        data["model_overrides"] = model_overrides
        save_ui_overrides(data)

def apply_hide_deploy_button_css():
    """
    应用隐藏Deploy按钮和工具栏的CSS样式
    在所有页面中调用此函数以确保一致的UI体验
    """
    st.markdown("""
    <style>
        /* 隐藏Streamlit顶部工具栏和Deploy按钮 - 多种选择器确保兼容性 */
        .stAppToolbar {
            display: none !important;
        }
        
        header[data-testid="stHeader"] {
            display: none !important;
        }
        
        .stDeployButton {
            display: none !important;
        }
        
        /* 新版本Streamlit的Deploy按钮选择器 */
        [data-testid="stToolbar"] {
            display: none !important;
        }
        
        [data-testid="stDecoration"] {
            display: none !important;
        }
        
        [data-testid="stStatusWidget"] {
            display: none !important;
        }
        
        /* 隐藏整个顶部区域 */
        .stApp > header {
            display: none !important;
        }
        
        .stApp > div[data-testid="stToolbar"] {
            display: none !important;
        }
        
        /* 隐藏主菜单按钮 */
        #MainMenu {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* 隐藏页脚 */
        footer {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* 隐藏"Made with Streamlit"标识 */
        .viewerBadge_container__1QSob {
            display: none !important;
        }
        
        /* 隐藏所有可能的工具栏元素 */
        div[data-testid="stToolbar"] {
            display: none !important;
        }
        
        /* 隐藏右上角的所有按钮 */
        .stApp > div > div > div > div > section > div {
            padding-top: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)

def apply_common_styles():
    """
    应用通用的页面样式
    包括隐藏Deploy按钮和其他美化样式
    """
    # 隐藏Deploy按钮
    apply_hide_deploy_button_css()
    
    # 其他通用样式
    st.markdown("""
    <style>
        /* 应用样式 */
        .main-header {
            background: linear-gradient(90deg, #1f77b4, #ff7f0e);
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            color: white;
            text-align: center;
        }
        
        .metric-card {
            background: #f0f2f6;
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #1f77b4;
            margin: 0.5rem 0;
        }
        
        .analysis-section {
            background: white;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        
        .success-box {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .warning-box {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .error-box {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
        }
    </style>
    """, unsafe_allow_html=True)


def inject_top_anchor(anchor_id: str = "ta-top-anchor") -> None:
    """在页面顶部注入一个命名锚点，供无JS的跳转使用。"""
    st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)


def inject_back_to_top_button(anchor_id: str = "ta-top-anchor") -> None:
    """在页面右下角注入“回到顶部”悬浮按钮（无JS实现，兼容性更好）。"""
    st.markdown(
        f"""
        <style>
        html {{ scroll-behavior: smooth; }}
        .ta-back-to-top {{position: fixed; right: 24px; bottom: 24px; z-index: 9999;}}
        .ta-back-to-top a {{
            display: inline-block;
            border-radius: 24px; padding: 10px 14px; font-weight: 600;
            background: var(--zen-surface); color: var(--zen-text);
            border: 1px solid var(--zen-border);
            box-shadow: 0 4px 12px rgba(0,0,0,.12);
            cursor: pointer; text-decoration: none;
        }}
        .ta-back-to-top a:hover {{ background: var(--zen-accent); color: #ffffff; }}
        </style>
        <div class="ta-back-to-top">
          <a href="#{anchor_id}" role="button" aria-label="回到页面顶部">⬆️ 回到顶部</a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_floating_config_button(image_path: str | None = None, size_px: int = 56, bottom_px: int = 84, right_px: int = 24) -> None:
    """在页面右下角注入一个悬浮的“配置”图片按钮。

    Args:
        image_path: 图片路径，默认使用项目根目录下的 'image copy.png'。
        size_px: 图标显示尺寸（保持等比缩放，最大边为该值）。
        bottom_px: 距底部距离（像素）。
        right_px: 距右侧距离（像素）。
    """
    try:
        import base64
        from pathlib import Path
        import streamlit as st

        # 计算默认图片路径
        if image_path is None:
            project_root = Path(__file__).resolve().parents[2]
            default_path = project_root / "image copy.png"
            # 兜底：如果不存在则尝试另一个名字
            if not default_path.exists():
                alt = project_root / "image.png"
                image_path = str(alt) if alt.exists() else None
            else:
                image_path = str(default_path)

        img_src = None
        if image_path and Path(image_path).exists():
            with open(image_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                img_src = f"data:image/png;base64,{b64}"

        # 如果无法加载图片，则显示一个圆形的文字按钮作为兜底
        if not img_src:
            st.markdown(
                f"""
                <style>
                .config-fab {{
                    position: fixed; right: {right_px}px; bottom: {bottom_px}px; z-index: 9999;
                    width: {size_px}px; height: {size_px}px; border-radius: {size_px//2}px;
                    background: var(--zen-accent, #0EA5A4); color: #fff; display: flex;
                    align-items: center; justify-content: center; font-weight: 700;
                    box-shadow: 0 6px 18px rgba(0,0,0,.24);
                    text-decoration: none;
                }}
                .config-fab:hover {{ filter: brightness(1.05); }}
                </style>
                <a class="config-fab" href="?open_config=1" title="打开配置">⚙️</a>
                """,
                unsafe_allow_html=True,
            )
            return

        # 使用图片的悬浮按钮
        st.markdown(
            f"""
            <style>
            .config-fab {{
                position: fixed; right: {right_px}px; bottom: {bottom_px}px; z-index: 9999;
                width: {size_px}px; height: {size_px}px; display: block;
                border-radius: 50%; box-shadow: 0 6px 18px rgba(0,0,0,.24);
                overflow: hidden; background: transparent;
            }}
            .config-fab img {{
                width: 100%; height: 100%; object-fit: contain; display: block;
            }}
            .config-fab:hover img {{ transform: scale(1.02); }}
            </style>
            <a class="config-fab" href="?open_config=1" title="打开配置">
              <img src="{img_src}" alt="配置" />
            </a>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        # 静默失败，避免阻塞页面
        pass


# ===== 角色模型持久化配置工具 =====

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any


def get_config_dir() -> Path:
    """获取配置目录路径"""
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent  # web/utils/ui_utils.py -> project_root
    return project_root / "config"


def get_role_overrides_file() -> Path:
    """获取角色覆盖配置文件路径"""
    return get_config_dir() / "ui_role_overrides.json"


def get_role_display_name(role_key: str) -> str:
    """返回角色中文显示名，优先从 provider_models 读取配置。

    若未找到，则回退到内置映射，最后回退为原始key。
    """
    try:
        from tradingagents.config.provider_models import model_provider_manager
        rc = model_provider_manager.get_role_config(role_key)
        if rc and getattr(rc, 'name', None):
            return rc.name
    except Exception:
        pass
    fallback = {
        'fundamental_expert': '基本面专家',
        'technical_analyst': '技术分析师',
        'news_hunter': '快讯猎手',
        'sentiment_analyst': '情绪分析师',
        'policy_researcher': '政策研究员',
        'risk_manager': '风控经理',
        'compliance_officer': '合规官',
        'chief_decision_officer': '首席决策官',
        'bull_researcher': '看涨研究员',
        'bear_researcher': '看跌研究员',
    }
    return fallback.get(role_key, role_key)


def load_persistent_role_configs() -> Dict[str, Any]:
    """加载持久化的角色配置"""
    config_file = get_role_overrides_file()
    
    if not config_file.exists():
        return {"role_overrides": {}, "last_modified": None}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"警告: 加载角色配置失败: {e}")
        return {"role_overrides": {}, "last_modified": None}


def save_persistent_role_config(role_key: str, model: str, is_locked: bool = True) -> bool:
    """保存角色的持久化配置
    
    Args:
        role_key: 角色键名
        model: 模型名称
        is_locked: 是否锁定到该模型
    
    Returns:
        bool: 保存是否成功
    """
    try:
        # 确保配置目录存在
        config_dir = get_config_dir()
        config_dir.mkdir(exist_ok=True)
        
        # 加载现有配置
        config = load_persistent_role_configs()
        
        # 更新配置
        config["role_overrides"][role_key] = {
            "model": model,
            "is_locked": is_locked
        }
        config["last_modified"] = datetime.now().isoformat()
        
        # 保存配置
        config_file = get_role_overrides_file()
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"错误: 保存角色配置失败: {e}")
        return False


def clear_role_config(role_key: str) -> bool:
    """清除角色的持久化配置
    
    Args:
        role_key: 角色键名
    
    Returns:
        bool: 清除是否成功
    """
    try:
        config = load_persistent_role_configs()
        
        if role_key in config["role_overrides"]:
            del config["role_overrides"][role_key]
            config["last_modified"] = datetime.now().isoformat()
            
            # 保存更新后的配置
            config_file = get_role_overrides_file()
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"错误: 清除角色配置失败: {e}")
        return False


def get_role_config(role_key: str) -> Optional[Dict[str, Any]]:
    """获取特定角色的配置
    
    Args:
        role_key: 角色键名
        
    Returns:
        角色配置字典或None
    """
    config = load_persistent_role_configs()
    return config["role_overrides"].get(role_key)


def render_role_config_button(role_key: str, role_label: str, available_models: list, in_form: bool = False) -> bool:
    """渲染角色配置按钮和弹窗
    
    Args:
        role_key: 角色键名
        role_label: 角色显示名称
        available_models: 可用模型列表
        
    Returns:
        bool: 是否有配置变更
    """
    try:
        import streamlit as st
    except ImportError:
        return False
    
    config_changed = False
    current_config = get_role_config(role_key)
    
    # 配置按钮
    config_key = f"config_{role_key}"
    # 注意：如果该函数在 st.form 内调用，则必须使用 st.form_submit_button
    if in_form:
        # 注意：form_submit_button 不支持 key 参数；使用唯一标签避免重复ID
        toggled = st.form_submit_button(f"⚙️ 配置（{role_label}）", help=f"配置{role_label}的模型")
    else:
        toggled = st.button("⚙️", key=f"btn_{config_key}", help=f"配置{role_label}的模型")
    if toggled:
        st.session_state[f"show_{config_key}"] = not st.session_state.get(f"show_{config_key}", False)
    
    # 如果显示配置面板
    if st.session_state.get(f"show_{config_key}", False):
        with st.container():
            # 标题更紧凑
            st.markdown(f"**🔧 {role_label} 模型配置**")

            # 顶部状态行：更轻量的 caption，减少大块提示的视觉噪声
            if current_config:
                st.caption(f"当前永久配置: {current_config['model']}")

            # 主体区域：左右两列，避免纵向一长条
            left, right = st.columns([3, 2])

            # 模型选择（左侧）
            model_options = ["(不限制)"] + available_models
            default_idx = 0
            if current_config and current_config['model'] in available_models:
                default_idx = available_models.index(current_config['model']) + 1

            with left:
                selected_model = st.selectbox(
                    "选择模型",
                    options=model_options,
                    index=default_idx,
                    key=f"model_select_{role_key}"
                )

            # 应用范围（右侧，横向单行）
            with right:
                scope = st.radio(
                    "应用范围",
                    options=["本次会话", "永久保存"],
                    key=f"scope_{role_key}",
                    horizontal=True
                )

            # 按钮区：一行三小按钮 + 右侧留白，整体更紧凑
            btn_col1, btn_col2, btn_col3, _spacer = st.columns([1, 1, 1, 6])

            # 生成不可见后缀，保证表单内标签唯一又不显眼
            def _invisible_suffix(seed: str) -> str:
                try:
                    count = abs(hash(seed)) % 7 + 1
                except Exception:
                    count = 1
                return "\u200B" * count

            # 保存按钮
            with btn_col1:
                save_label_visible = "💾 保存" if in_form else "💾 保存"
                save_label = save_label_visible + (_invisible_suffix(f"save_{role_key}") if in_form else "")
                if (st.form_submit_button(save_label) if in_form else st.button(save_label, key=f"save_{role_key}")):
                    if selected_model != "(不限制)":
                        if scope == "永久保存":
                            # 保存到持久化配置
                            if save_persistent_role_config(role_key, selected_model):
                                st.success("✅ 永久配置已保存")
                                config_changed = True
                            else:
                                st.error("❌ 保存失败")

                        # 更新session state（本次会话）
                        if 'model_overrides' not in st.session_state:
                            st.session_state.model_overrides = {}
                        st.session_state.model_overrides[role_key] = selected_model
                        config_changed = True
                    else:
                        # 清除配置
                        if scope == "永久保存":
                            clear_role_config(role_key)
                        if role_key in st.session_state.get('model_overrides', {}):
                            del st.session_state.model_overrides[role_key]
                        config_changed = True

            # 重置按钮
            with btn_col2:
                reset_label_visible = "🔄 重置" if in_form else "🔄 重置"
                reset_label = reset_label_visible + (_invisible_suffix(f"reset_{role_key}") if in_form else "")
                if (st.form_submit_button(reset_label) if in_form else st.button(reset_label, key=f"reset_{role_key}")):
                    clear_role_config(role_key)
                    if role_key in st.session_state.get('model_overrides', {}):
                        del st.session_state.model_overrides[role_key]
                    st.success("✅ 配置已重置")
                    config_changed = True

            # 关闭按钮
            with btn_col3:
                close_label_visible = "❌ 关闭" if in_form else "❌ 关闭"
                close_label = close_label_visible + (_invisible_suffix(f"close_{role_key}") if in_form else "")
                if (st.form_submit_button(close_label) if in_form else st.button(close_label, key=f"close_{role_key}")):
                    st.session_state[f"show_{config_key}"] = False
                    st.rerun()
    
    return config_changed


def load_persistent_configs_to_session():
    """将持久化配置加载到session state"""
    try:
        import streamlit as st
    except ImportError:
        return
    
    config = load_persistent_role_configs()
    role_overrides = config.get("role_overrides", {})
    
    if role_overrides:
        # 初始化session state中的model_overrides
        if 'model_overrides' not in st.session_state:
            st.session_state.model_overrides = {}
        
        # 将持久化配置合并到session state（不覆盖临时配置）
        for role_key, role_config in role_overrides.items():
            if role_key not in st.session_state.model_overrides:
                st.session_state.model_overrides[role_key] = role_config['model']
