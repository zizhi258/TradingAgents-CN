"""
页面头部组件 + 顶部导航
现代化设计，增强用户体验
"""

from pathlib import Path

import streamlit as st


def _inject_theme_css_once():
    """将主题样式注入到页面（幂等）。"""
    try:
        css_path = Path(__file__).parent.parent / "static" / "theme.css"
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except Exception:
        # CSS 不是强依赖，失败时静默
        pass


def render_modern_hero():
    """渲染现代化的英雄区域"""
    st.markdown(
        """
    <div class="ta-hero">
        <h1>📈 TradingAgents-CN</h1>
        <p>基于多智能体的现代化股票分析平台 · 智能决策 · 数据驱动</p>
        <div class="ta-badges">
            <span class="ta-badge">AI驱动</span>
            <span class="ta-badge">实时分析</span>
            <span class="ta-badge">多市场支持</span>
            <span class="ta-badge">智能报告</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_top_nav(menu_pages: list[str], default_page: str | None = None) -> str:
    """渲染顶部横向导航，返回当前选中的页面名。

    - 使用水平 `radio` 实现，视觉轻量；
    - 选中项存入 `st.session_state.nav_page`，以便跨重载保持；
    - 默认页可通过 `default_page` 指定，否则使用 session 中的值或第一个。
    """
    _inject_theme_css_once()

    key = "nav_page"
    if default_page and key not in st.session_state:
        st.session_state[key] = default_page
    if key in st.session_state and st.session_state[key] in menu_pages:
        index = menu_pages.index(st.session_state[key])
    else:
        index = 0

    with st.container():
        st.markdown('<div class="ta-topbar"></div>', unsafe_allow_html=True)
        # 放在同一容器内，避免与后续区块产生过多间距
        page = st.radio(
            label="页面导航",
            options=menu_pages,
            index=index,
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav_radio",
        )

    st.session_state[key] = page
    return page


def render_browser_tabs(menu_pages: list[str], default_index: int = 0) -> str:
    """渲染"浏览器标签页"风格的顶部导航（本页切换，无新标签）。

    使用水平 radio 实现状态切换，配合 CSS 呈现为现代化卡片式标签外观。
    不依赖 query_params，避免实验 API 警告。
    """
    _inject_theme_css_once()

    # 读取/初始化当前页
    current = st.session_state.get("top_nav_page", menu_pages[default_index])
    if current not in menu_pages:
        current = menu_pages[default_index]

    # 水平 radio（用 CSS 做成现代化卡片标签外观）
    with st.container():
        st.markdown("<div class='ta-tabbar-sticky ta-glass'>", unsafe_allow_html=True)
        selected = st.radio(
            label="页面导航",
            options=menu_pages,
            index=menu_pages.index(current),
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav_page",
        )
        st.markdown("</div>", unsafe_allow_html=True)

    return selected


def render_header():
    """渲染页面头部（现代化版）：注入主题CSS并可选择性渲染英雄区。"""

    _inject_theme_css_once()

    # 检查是否需要显示英雄区（仅在主页显示）
    current_page = st.session_state.get("top_nav_page", "📊 个股分析")

    if current_page == "📊 个股分析":
        render_modern_hero()
    else:
        # 其他页面显示简化标题
        st.markdown(
            f"""
        <div class="ta-hero" style="padding: 16px 20px;">
            <h1 style="font-size: 1.3rem; margin: 0;">{current_page}</h1>
        </div>
        """,
            unsafe_allow_html=True,
        )


def render_feature_cards():
    """渲染功能特性卡片（可选）"""
    st.markdown(
        """
    <div class="ta-grid">
        <div class="ta-card ta-elevation-2">
            <h4>🤖 多智能体协作</h4>
            <p>分析师、研究员、交易员协同工作，提供全面分析</p>
        </div>
        <div class="ta-card ta-elevation-2">
            <h4>📊 实时数据</h4>
            <p>支持A股、港股、美股实时行情数据获取</p>
        </div>
        <div class="ta-card ta-elevation-2">
            <h4>🧠 AI驱动</h4>
            <p>集成多种大语言模型，智能分析市场趋势</p>
        </div>
        <div class="ta-card ta-elevation-2">
            <h4>📈 专业报告</h4>
            <p>生成详细的投资分析报告，支持多种格式导出</p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
