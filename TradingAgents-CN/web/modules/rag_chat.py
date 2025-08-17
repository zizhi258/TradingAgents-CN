#!/usr/bin/env python3
"""
💬 智能对话（RAG）页面

提供基于知识库的问答能力：调用后端 /api/kb/query 返回带引用的回答。
"""

import os

import streamlit as st


def _get_kb_client():
    try:
        from web.utils.kb_api_client import KBApiClient

        return KBApiClient()
    except Exception as e:
        st.error(f"❌ 初始化知识库客户端失败：{e}")
        return None


def render_rag_chat():
    st.header("💬 智能对话（RAG）")
    st.caption("面向对话场景的检索增强问答（不影响报告生成流程）")

    client = _get_kb_client()
    if client is None:
        st.stop()

    # 初始化会话历史
    if "rag_chat_history" not in st.session_state:
        st.session_state.rag_chat_history = []  # list of dicts: {q,a,sources}

    # 左右布局：左侧聊天，右侧库统计/管理
    col_chat, col_stats = st.columns([7, 3])

    with col_stats:
        st.subheader("📚 知识库")
        try:
            stats = client.kb_stats()
            kb = stats.get("knowledge_base", {})
            st.metric("文档数量", kb.get("total_documents", 0))
            st.write("向量库可用:", "✅" if kb.get("vector_db_available") else "❌")
            if kb.get("documents_by_type"):
                st.write("类型分布:")
                st.json(kb["documents_by_type"])
        except Exception as e:
            st.info(f"无法获取知识库状态：{e}")

        with st.expander("索引管理", expanded=False):
            default_root = os.getenv("LIBRARY_ROOT", "./data/library")
            root_dir = st.text_input(
                "根目录", value=default_root, help="RAG 文库根目录"
            )
            user_id = st.text_input("用户ID（可选）", value="")
            symbol = st.text_input("默认证券（可选）", value="")
            # 嵌入配置（仅作用于本次重建流程）
            st.markdown("**嵌入配置（Qwen3-Embedding-8B）**")
            c1, c2 = st.columns([1, 1])
            with c1:
                emb_dim = st.number_input(
                    "嵌入维度 (32–4096)",
                    value=4096,
                    min_value=32,
                    max_value=4096,
                    step=32,
                )
            with c2:
                emb_model = st.text_input("模型ID", value="Qwen/Qwen3-Embedding-8B")
            # provider 固定为 siliconflow（统一策略）
            emb_provider = "siliconflow"

            # 简易上传到文库根目录
            st.markdown("**上传文件到文库**（保存到上述根目录）")
            uploads = st.file_uploader(
                "选择文件（txt/md/csv/html 建议）", accept_multiple_files=True
            )
            if uploads:
                from pathlib import Path as _Path

                try:
                    troot = _Path(root_dir)
                    troot.mkdir(parents=True, exist_ok=True)
                    count = 0
                    for f in uploads:
                        data = f.read()
                        (troot / f.name).write_bytes(data)
                        count += 1
                    st.success(f"已保存 {count} 个文件到 {troot}")
                except Exception as e:
                    st.error(f"保存失败：{e}")

            if st.button("🔄 重建索引", use_container_width=True):
                try:
                    res = client.kb_reindex(
                        root_dir=root_dir or None,
                        user_id=user_id or None,
                        symbol=symbol or None,
                        embedding_dim=int(emb_dim),
                        embedding_model=emb_model,
                        embedding_provider=emb_provider,
                    )
                    if res.get("success"):
                        st.success(
                            f"索引完成：新增 {res.get('added',0)}，跳过 {res.get('skipped',0)}"
                        )
                        if res.get("warnings"):
                            st.warning("\n".join(res["warnings"]))
                    else:
                        st.error(str(res))
                except Exception as e:
                    st.error(f"重建索引失败：{e}")

    with col_chat:
        st.subheader("聊天")

        CHAT_AVAILABLE = all(
            hasattr(st, name) for name in ("chat_input", "chat_message")
        )

        # 默认参数（可在设置中调整）
        if "rag_chat_settings" not in st.session_state:
            st.session_state.rag_chat_settings = {
                "query_type": "general",
                "top_k": 5,
                "relevance_threshold": 0.7,
                "symbols": [],
            }

        with st.expander("⚙️ 设置", expanded=False):
            s = st.session_state.rag_chat_settings
            s["query_type"] = st.selectbox(
                "问题类型",
                ["general", "technical", "fundamental", "news", "risk"],
                index=["general", "technical", "fundamental", "news", "risk"].index(
                    s["query_type"]
                ),
            )
            c1, c2 = st.columns(2)
            with c1:
                s["top_k"] = int(st.slider("Top K", 1, 10, int(s["top_k"])))
            with c2:
                s["relevance_threshold"] = float(
                    st.slider(
                        "相关性阈值", 0.0, 1.0, float(s["relevance_threshold"]), 0.05
                    )
                )
            symbols_raw = st.text_input(
                "相关证券（逗号分隔，可选）", value=",".join(s.get("symbols") or [])
            )
            s["symbols"] = [x.strip() for x in symbols_raw.split(",") if x.strip()]

            # 对话角色（生成模型绑定）
            try:
                from tradingagents.config.provider_models import model_provider_manager
                all_roles = [
                    rk
                    for rk, rc in model_provider_manager.role_definitions.items()
                    if getattr(rc, "enabled", True)
                ]
            except Exception:
                all_roles = [
                    "fundamental_expert",
                    "technical_analyst",
                    "chief_writer",
                    "news_hunter",
                    "risk_manager",
                ]
            default_role = (
                s.get("agent_role") or os.getenv("RAG_CHAT_AGENT_ROLE") or "fundamental_expert"
            )
            if all_roles and default_role not in all_roles:
                default_role = all_roles[0]
            role_index = all_roles.index(default_role) if default_role in all_roles else 0
            s["agent_role"] = st.selectbox(
                "对话角色（生成模型绑定）",
                options=all_roles,
                index=role_index,
                help="与‘角色中心’绑定的模型联动，用该角色的锁定/首选模型生成答案",
            )

        # 使用 Streamlit 聊天组件渲染历史（若不可用则回退到简易表单）
        if CHAT_AVAILABLE:
            if "rag_chat_messages" not in st.session_state:
                st.session_state.rag_chat_messages = (
                    []
                )  # [{role:'user'|'assistant', content:str, sources?:list}]

            for msg in st.session_state.rag_chat_messages:
                with st.chat_message(msg.get("role", "assistant")):
                    st.markdown(msg.get("content", ""))
                    if msg.get("sources"):
                        st.caption("引用来源：")
                        for s in msg["sources"]:
                            st.write(f"- {s}")

            # 输入框（回车发送）
            user_input = st.chat_input("请输入你的问题…")
            if user_input:
                # 先回显用户消息
                st.session_state.rag_chat_messages.append(
                    {"role": "user", "content": user_input}
                )
                with st.chat_message("user"):
                    st.markdown(user_input)

                # 调用后端 RAG 问答
                s = st.session_state.rag_chat_settings
                try:
                    # 传递最近对话历史以启用多轮检索
                    history = st.session_state.get("rag_chat_messages") or []
                    res = client.kb_query(
                        query_text=user_input.strip(),
                        query_type=s.get("query_type", "general"),
                        symbols=(s.get("symbols") or None),
                        top_k=int(s.get("top_k", 5)),
                        relevance_threshold=float(s.get("relevance_threshold", 0.7)),
                        history=history,
                        conversation_id=None,
                        agent_role=(s.get("agent_role") or os.getenv('RAG_CHAT_AGENT_ROLE') or 'fundamental_expert'),
                    )
                    if not res.get("success"):
                        answer = f"❌ 出错：{res}"
                        sources = []
                    else:
                        answer = res.get("answer") or "（未生成回答）"
                        sources = res.get("sources") or []
                    # 展示助手消息
                    with st.chat_message("assistant"):
                        st.markdown(answer)
                        if sources:
                            st.caption("引用来源：")
                            for s in sources:
                                st.write(f"- {s}")
                    # 存入历史
                    st.session_state.rag_chat_messages.append(
                        {"role": "assistant", "content": answer, "sources": sources}
                    )
                except Exception as e:
                    err = f"调用失败：{e}"
                    with st.chat_message("assistant"):
                        st.error(err)
                    st.session_state.rag_chat_messages.append(
                        {"role": "assistant", "content": err}
                    )
        else:
            # 兼容旧版Streamlit：回退到一次一问一答表单
            with st.form("rag_chat_form_compat", clear_on_submit=True):
                q = st.text_area("请输入你的问题", placeholder="输入问题后提交")
                submitted = st.form_submit_button("发送")
            if submitted and q and len(q.strip()) >= 3:
                s = st.session_state.rag_chat_settings
                try:
                    history = st.session_state.get("rag_chat_messages") or []
                    res = client.kb_query(
                        query_text=q.strip(),
                        query_type=s.get("query_type", "general"),
                        symbols=(s.get("symbols") or None),
                        top_k=int(s.get("top_k", 5)),
                        relevance_threshold=float(s.get("relevance_threshold", 0.7)),
                        history=history,
                        conversation_id=None,
                        agent_role=(s.get("agent_role") or os.getenv('RAG_CHAT_AGENT_ROLE') or 'fundamental_expert'),
                    )
                    ans = res.get("answer") if res.get("success") else str(res)
                    st.write(ans)
                except Exception as e:
                    st.error(f"调用失败：{e}")
