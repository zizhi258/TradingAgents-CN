#!/usr/bin/env python3
"""
图书馆（Library）页面
将“缓存管理”和“附件管理”整合为一个统一入口：集中浏览、搜索、统计与清理。
"""


import streamlit as st

from web.components.attachment_manager import render_attachment_manager

# 局部导入，保持与原页面的松耦合
# 使用绝对导入避免 "attempted relative import beyond top-level package" 错误
from web.modules.cache_management import render_cache_management


def render_library(default_tab: str | None = None):
    st.header("📚 图书馆")
    st.caption("统一查看历史产物：缓存与附件；支持上传、统计、清理")

    # 选项卡：附件 / 缓存
    tab_titles = ["📎 附件", "💾 缓存"]
    tab_map = {"attachments": 0, "cache": 1}
    tab_map.get(default_tab, 0)

    tabs = st.tabs(tab_titles)

    with tabs[0]:
        render_attachment_manager(embedded=True)

    with tabs[1]:
        render_cache_management(embedded=True)
