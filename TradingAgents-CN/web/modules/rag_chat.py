#!/usr/bin/env python3
"""
💬 智能对话（RAG）页面

提供基于知识库的问答能力：调用后端 /api/kb/query 返回带引用的回答。
"""

import os
from datetime import datetime

import streamlit as st



def _get_kb_client():
    try:
        from web.utils.kb_api_client import KBApiClient

        return KBApiClient()
    except Exception as e:
        st.error(f"❌ 初始化知识库客户端失败：{e}")
        return None


def render_rag_chat():
    client = _get_kb_client()
    if client is None:
        st.stop()

    # 初始化会话历史
    if "rag_chat_history" not in st.session_state:
        st.session_state.rag_chat_history = []

    # 改为标签布局：聊天/知识库/索引管理，界面更简洁
    tab_chat, tab_kb, tab_index = st.tabs(["💬 智能对话", "📚 知识库管理", "🛠️ 索引设置"])

    # --- 聊天界面 ---
    with tab_chat:
        # 顶部工具栏（单行紧凑布局）
        tool_cols = st.columns([12, 1, 1, 1])
        with tool_cols[0]:
            messages_count = len(st.session_state.get("rag_chat_messages", []))
            title = f"💬 对话中（{messages_count}）" if messages_count > 0 else "🤖 智能助手"
            st.markdown(f"**{title}**")
        with tool_cols[1]:
            if st.button("⚙️", key="chat_settings", help="设置"):
                st.session_state.show_chat_settings = not st.session_state.get("show_chat_settings", False)
        with tool_cols[2]:
            if st.button("📊", key="chat_stats", help="统计"):
                st.session_state.show_chat_stats = not st.session_state.get("show_chat_stats", False)
        with tool_cols[3]:
            if st.button("🧹", key="clear_chat", help="清空对话"):
                st.session_state.pop("rag_chat_messages", None)
                st.session_state.rag_chat_history = []
                st.rerun()

        # 紧凑设置面板
        if st.session_state.get("show_chat_settings", False):
            with st.expander("⚙️ 聊天设置", expanded=False):
                s = st.session_state.rag_chat_settings
                col1, col2, col3 = st.columns(3)
                with col1:
                    s["query_type"] = st.selectbox("问题类型", ["general", "technical", "fundamental", "news", "risk"])
                with col2:
                    s["top_k"] = st.slider("检索数量", 1, 10, s.get("top_k", 5))
                with col3:
                    s["relevance_threshold"] = st.slider("相关性", 0.0, 1.0, s.get("relevance_threshold", 0.7), 0.1)

        # 紧凑统计（条件显示）
        if st.session_state.get("show_chat_stats", False):
            messages = st.session_state.get("rag_chat_messages", [])
            user_count = len([m for m in messages if m.get("role") == "user"])
            ai_count = len([m for m in messages if m.get("role") == "assistant"])
            st.info(f"📊 总计: {len(messages)}条 | 用户: {user_count}条 | AI: {ai_count}条")

        # 初始化设置
        if "rag_chat_settings" not in st.session_state:
            st.session_state.rag_chat_settings = {
                "query_type": "general",
                "top_k": 5,
                "relevance_threshold": 0.7,
                "symbols": [],
            }

        # 初始化消息历史
        if "rag_chat_messages" not in st.session_state:
            st.session_state.rag_chat_messages = []
        
        CHAT_AVAILABLE = all(hasattr(st, name) for name in ("chat_input", "chat_message"))
        
        # 聊天消息显示区域
        if not st.session_state.rag_chat_messages:
            st.caption("🤖 我是您的智能金融助手，请提问任何股票、投资相关的问题")
        else:
            # 简化消息显示
            for msg in st.session_state.rag_chat_messages:
                with st.chat_message(msg.get("role", "assistant")):
                    st.markdown(msg.get("content", ""))
                    if msg.get("sources"):
                        with st.expander("📚 引用来源", expanded=False):
                            for source in msg["sources"]:
                                st.caption(f"• {source}")

        # 聊天输入
        if CHAT_AVAILABLE:
            user_input = st.chat_input("请输入您的问题...")
            if user_input:
                # 添加用户消息
                st.session_state.rag_chat_messages.append({"role": "user", "content": user_input})
                
                # 调用RAG
                s = st.session_state.rag_chat_settings
                try:
                    res = client.kb_query(
                        query_text=user_input.strip(),
                        query_type=s.get("query_type", "general"),
                        symbols=s.get("symbols"),
                        top_k=s.get("top_k", 5),
                        relevance_threshold=s.get("relevance_threshold", 0.7),
                        history=st.session_state.rag_chat_messages,
                        agent_role=s.get("agent_role", "fundamental_expert"),
                        agent_model=s.get("agent_model"),
                    )
                    
                    answer = res.get("answer", "未获取到回答") if res.get("success") else f"错误: {res}"
                    sources = res.get("sources", [])
                    
                    # 添加AI回复
                    st.session_state.rag_chat_messages.append({
                        "role": "assistant", 
                        "content": answer, 
                        "sources": sources
                    })
                    
                except Exception as e:
                    st.session_state.rag_chat_messages.append({
                        "role": "assistant",
                        "content": f"系统错误: {e}"
                    })
                
                st.rerun()
        else:
            # 简单表单备用
            with st.form("rag_form"):
                q = st.text_area("您的问题:", height=100)
                if st.form_submit_button("发送"):
                    if q.strip():
                        st.write("您的问题:", q)
                        # 处理问题...
                        st.info("正在处理...")

    # --- 知识库 ---
    with tab_kb:
        try:
            stats = client.kb_stats()
            kb = stats.get("knowledge_base", {})
            
            # 紧凑指标
            cols = st.columns(3)
            with cols[0]:
                st.metric("文档数", kb.get("total_documents", 0))
            with cols[1]:
                st.metric("向量库", "✅" if kb.get("vector_db_available") else "❌")
            with cols[2]:
                st.metric("片段数", kb.get("total_chunks", 0))
            
            # 类型分布
            if kb.get("documents_by_type"):
                with st.expander("📂 文档类型分布"):
                    st.json(kb["documents_by_type"])
                    
        except Exception as e:
            st.error(f"无法获取状态: {e}")

    # --- 索引管理 ---
    with tab_index:
        # 基础配置
        col1, col2 = st.columns(2)
        with col1:
            root_dir = st.text_input("根目录", os.getenv("LIBRARY_ROOT", "./data/library"))
            dry_run = st.checkbox("测试模式")
        with col2:
            uploads = st.file_uploader("上传文件", accept_multiple_files=True)
            
        # 嵌入配置
        emb_col1, emb_col2 = st.columns(2) 
        with emb_col1:
            emb_model = st.text_input("嵌入模型", "Qwen/Qwen3-Embedding-8B")
        with emb_col2:
            emb_dim = st.number_input("维度", 512, 4096, 4096, 512)
        
        # 上传处理
        if uploads:
            from pathlib import Path as _Path
            try:
                troot = _Path(root_dir)
                troot.mkdir(parents=True, exist_ok=True)
                for f in uploads:
                    (troot / f.name).write_bytes(f.read())
                st.success(f"上传了 {len(uploads)} 个文件")
            except Exception as e:
                st.error(f"上传失败: {e}")
        
        # 重建索引
        if st.button("🔄 重建索引", type="primary"):
            try:
                res = client.kb_reindex(
                    root_dir=root_dir,
                    embedding_dim=emb_dim,
                    embedding_model=emb_model,
                    embedding_provider="siliconflow",
                    dry_run=dry_run,
                )
                if res.get("success"):
                    st.success(f"完成: 新增{res.get('added',0)}, 跳过{res.get('skipped',0)}")
                else:
                    st.error(str(res))
            except Exception as e:
                st.error(f"失败: {e}")


