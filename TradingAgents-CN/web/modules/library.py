#!/usr/bin/env python3
"""
图书馆（Library）页面
将“缓存管理”和“附件管理”整合为一个统一入口：集中浏览、搜索、统计与清理。
新增“知识库”页签：浏览按日归档的离线分析资料，支持单日重建索引与删除目录。
"""


import os
from pathlib import Path
import shutil

import streamlit as st

from web.components.attachment_manager import render_attachment_manager

# 局部导入，保持与原页面的松耦合
# 使用绝对导入避免 "attempted relative import beyond top-level package" 错误
from web.modules.cache_management import render_cache_management
from web.utils.kb_ingestor import trigger_kb_reindex


def _lib_root() -> Path:
    base = os.getenv("LIBRARY_ROOT") or os.getenv("TRADINGAGENTS_DATA_DIR")
    if base:
        p = Path(base)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[2] / p
    else:
        p = Path(__file__).resolve().parents[2] / "data" / "library"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _scan_analyses():
    root = _lib_root() / "analyses"
    data: dict[str, list[str]] = {}
    if not root.exists():
        return data
    for sym_dir in root.iterdir():
        if not sym_dir.is_dir():
            continue
        dates = [d.name for d in sorted(sym_dir.iterdir()) if d.is_dir()]
        data[sym_dir.name] = dates
    return data


def render_kb_manager():
    st.subheader("📚 知识库（离线索引）")
    root = _lib_root() / "analyses"
    st.caption(f"根目录: {root}")
    data = _scan_analyses()
    if not data:
        st.info("暂无已归档的分析。完成一轮分析后可在此重建索引或清理。")
        return
    symbols = sorted(list(data.keys()))
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        sym = st.selectbox("证券", options=symbols)
    with c2:
        dates = data.get(sym, [])
        date = st.selectbox("日期", options=dates)
    target_dir = root / sym / date
    st.write(f"目标目录: `{target_dir}`")
    # 操作按钮
    b1, b2 = st.columns(2)
    with b1:
        if st.button("🔄 仅重建此日期索引", use_container_width=True):
            with st.spinner("正在重建索引…"):
                res = trigger_kb_reindex(str(target_dir), symbol=sym)
            if res.get("success"):
                st.success(
                    f"索引完成：新增 {res.get('added',0)}，跳过 {res.get('skipped',0)}"
                )
            else:
                st.error(f"索引失败：{res}")
    with b2:
        if st.button("🗑️ 删除该目录", use_container_width=True):
            try:
                shutil.rmtree(target_dir)
                st.success("已删除。刷新查看最新状态。")
            except Exception as e:
                st.error(f"删除失败：{e}")


def render_library(default_tab: str | None = None):
    st.header("📚 图书馆")
    st.caption("统一查看历史产物：缓存与附件；支持上传、统计、清理")

    # 选项卡：附件 / 缓存
    tab_titles = ["📎 附件", "💾 缓存", "📚 知识库"]
    tab_map = {"attachments": 0, "cache": 1, "kb": 2}
    tab_map.get(default_tab, 0)

    tabs = st.tabs(tab_titles)

    with tabs[0]:
        render_attachment_manager(embedded=True)

    with tabs[1]:
        render_cache_management(embedded=True)

    with tabs[2]:
        render_kb_manager()
