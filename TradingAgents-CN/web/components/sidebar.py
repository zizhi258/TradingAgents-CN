"""
侧边栏组件
"""

import logging
import os
import sys
from pathlib import Path

import streamlit as st

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.utils.persistence import load_model_selection  # noqa: E402

logger = logging.getLogger(__name__)


def render_sidebar():
    """渲染侧边栏配置"""

    # 添加localStorage支持的JavaScript
    st.markdown(
        """
    <script>
    // 保存到localStorage
    function saveToLocalStorage(key, value) {
        localStorage.setItem('tradingagents_' + key, value);
        console.log('Saved to localStorage:', key, value);
    }

    // 从localStorage读取
    function loadFromLocalStorage(key, defaultValue) {
        const value = localStorage.getItem('tradingagents_' + key);
        console.log('Loaded from localStorage:', key, value || defaultValue);
        return value || defaultValue;
    }

    // 页面加载时恢复设置
    window.addEventListener('load', function() {
        console.log('Page loaded, restoring settings...');
    });
    </script>
    """,
        unsafe_allow_html=True,
    )

    # 优化侧边栏样式
    st.markdown(
        """
    <style>
    /* 优化侧边栏宽度 - 调整为320px */
    section[data-testid="stSidebar"] {
        width: 320px !important;
        min-width: 320px !important;
        max-width: 320px !important;
    }

    /* 优化侧边栏内容容器 */
    section[data-testid="stSidebar"] > div {
        width: 320px !important;
        min-width: 320px !important;
        max-width: 320px !important;
    }

    /* 强制减少侧边栏内边距 - 多种选择器确保生效 */
    section[data-testid="stSidebar"] .block-container,
    section[data-testid="stSidebar"] > div > div,
    .css-1d391kg,
    .css-1lcbmhc,
    .css-1cypcdb {
        padding-top: 0.75rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        padding-bottom: 0.75rem !important;
    }

    /* 侧边栏内所有元素的边距控制 */
    section[data-testid="stSidebar"] * {
        box-sizing: border-box !important;
    }

    /* 优化selectbox容器 */
    section[data-testid="stSidebar"] .stSelectbox {
        margin-bottom: 0.4rem !important;
        width: 100% !important;
    }

    /* 优化selectbox下拉框 - 调整为适合320px */
    section[data-testid="stSidebar"] .stSelectbox > div > div,
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
        width: 100% !important;
        min-width: 260px !important;
        max-width: 280px !important;
    }

    /* 优化下拉框选项文本 */
    section[data-testid="stSidebar"] .stSelectbox label {
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        margin-bottom: 0.2rem !important;
    }

    /* 优化文本输入框 */
    section[data-testid="stSidebar"] .stTextInput > div > div > input {
        font-size: 0.8rem !important;
        padding: 0.3rem 0.5rem !important;
        width: 100% !important;
    }

    /* 优化按钮样式 */
    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        font-size: 0.8rem !important;
        padding: 0.3rem 0.5rem !important;
        margin: 0.1rem 0 !important;
        border-radius: 0.3rem !important;
    }

    /* 优化标题样式 */
    section[data-testid="stSidebar"] h3 {
        font-size: 1rem !important;
        margin-bottom: 0.5rem !important;
        margin-top: 0.3rem !important;
        padding: 0 !important;
    }

    /* 优化info框样式 */
    section[data-testid="stSidebar"] .stAlert {
        padding: 0.4rem !important;
        margin: 0.3rem 0 !important;
        font-size: 0.75rem !important;
    }

    /* 优化markdown文本 */
    section[data-testid="stSidebar"] .stMarkdown {
        margin-bottom: 0.3rem !important;
        padding: 0 !important;
    }

    /* 优化分隔线 */
    section[data-testid="stSidebar"] hr {
        margin: 0.75rem 0 !important;
    }

    /* 确保下拉框选项完全可见 - 调整为适合320px */
    .stSelectbox [data-baseweb="select"] {
        min-width: 260px !important;
        max-width: 280px !important;
    }

    /* 优化下拉框选项列表 */
    .stSelectbox [role="listbox"] {
        min-width: 260px !important;
        max-width: 290px !important;
    }

    /* 额外的边距控制 - 确保左右边距减小 */
    .sidebar .element-container {
        padding: 0 !important;
        margin: 0.2rem 0 !important;
    }

    /* 强制覆盖默认样式 */
    .css-1d391kg .element-container {
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        # 使用组件来从localStorage读取并初始化session state
        st.markdown(
            """
        <div id="localStorage-reader" style="display: none;">
            <script>
            // 从localStorage读取设置并发送给Streamlit
            const provider = loadFromLocalStorage('llm_provider', 'deepseek');
            const category = loadFromLocalStorage('model_category', 'google');
            const model = loadFromLocalStorage('llm_model', '');

            // 通过自定义事件发送数据
            window.parent.postMessage({
                type: 'localStorage_data',
                provider: provider,
                category: category,
                model: model
            }, '*');
            </script>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 从持久化存储加载配置
        saved_config = load_model_selection()

        # 初始化session state，优先使用保存的配置
        if "llm_provider" not in st.session_state:
            st.session_state.llm_provider = saved_config["provider"]
            logger.debug(
                f"🔧 [Persistence] 恢复 llm_provider: {st.session_state.llm_provider}"
            )
        if "model_category" not in st.session_state:
            st.session_state.model_category = saved_config["category"]
            logger.debug(
                f"🔧 [Persistence] 恢复 model_category: {st.session_state.model_category}"
            )
        if "llm_model" not in st.session_state:
            st.session_state.llm_model = saved_config["model"]
            logger.debug(
                f"🔧 [Persistence] 恢复 llm_model: {st.session_state.llm_model}"
            )

        # 显示当前session state状态（调试用）
        logger.debug(
            f"🔍 [Session State] 当前状态 - provider: {st.session_state.llm_provider}, category: {st.session_state.model_category}, model: {st.session_state.llm_model}"
        )

        # AI模型配置 - 紧凑摘要
        st.markdown("### 🧠 AI模型配置")
        st.caption(
            f"提供商: {st.session_state.get('llm_provider','-')} | 快速: {st.session_state.get('llm_quick_model','-')} | 深度: {st.session_state.get('llm_deep_model','-')}"
        )
        st.info("💡 模型选择已移至页面配置区域。请在右侧页面中进行模型配置。")

        st.markdown("---")
        # 侧边栏不再显示API密钥状态，相关信息已移动到主页面

    # 确保返回session state中的值，而不是局部变量
    final_provider = st.session_state.llm_provider
    final_model = st.session_state.llm_model

    logger.debug(
        f"🔄 [Session State] 返回配置 - provider: {final_provider}, model: {final_model}"
    )

    # 为与旧接口兼容，提供安全的默认返回值，避免未定义变量导致的 NameError
    # 详细的路由/回退/预算等由主页面的 `render_model_selection_panel` 提供
    return {
        "llm_provider": final_provider,
        "llm_model": final_model,  # 兼容旧字段
        "llm_quick_model": st.session_state.get("llm_quick_model", final_model),
        "llm_deep_model": st.session_state.get("llm_deep_model", final_model),
        "routing_strategy": st.session_state.get("routing_strategy_select")
        or os.getenv("ROUTING_STRATEGY", "均衡"),
        "fallbacks": st.session_state.get("fallback_chain", []),
        "max_budget": st.session_state.get("max_budget", 0.0),
        "enable_memory": st.session_state.get("enable_memory", False),
        "enable_debug": st.session_state.get("enable_debug", False),
        "max_tokens": st.session_state.get("max_tokens", 32000),
    }
