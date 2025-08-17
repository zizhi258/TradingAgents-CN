"""
分析结果显示组件 - 增强版，集成ChartingArtist可视化功能
"""

import os
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from components.email_sender import render_email_sender
from utils.markdown_sanitizer import sanitize_markdown_for_streamlit

# 导入导出功能和邮件发送功能
from utils.report_exporter import render_export_buttons
from utils.kb_ingestor import ingest_analysis_results

# 导入ChartingArtist相关组件
try:
    from components.charting_artist_component import render_visualization_section
    from components.enhanced_visualization_tab import render_enhanced_visualization_tab
    from components.role_alignment_display import render_role_alignment_dashboard

    CHARTING_ARTIST_AVAILABLE = True
except ImportError as e:
    CHARTING_ARTIST_AVAILABLE = False
    print(f"ChartingArtist组件导入失败: {e}")

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("web")


def render_results(results):
    """渲染分析结果"""

    if not results:
        st.warning("暂无分析结果")
        return

    # 添加CSS确保结果内容不被右侧遮挡
    st.markdown(
        """
    <style>
    /* 确保分析结果内容有足够的右边距 */
    .element-container, .stMarkdown, .stExpander {
        margin-right: 1.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* 特别处理展开组件 */
    .streamlit-expanderHeader {
        margin-right: 1rem !important;
    }

    /* 确保文本内容不被截断 */
    .stMarkdown p, .stMarkdown div {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    stock_symbol = results.get("stock_symbol", "N/A")
    decision = results.get("decision", {})
    state = results.get("state", {})
    is_demo = results.get("is_demo", False)

    st.markdown("<div class='ta-section'>", unsafe_allow_html=True)
    st.header(f"📊 {stock_symbol} 分析结果")

    # 如果是演示数据，显示提示
    if is_demo:
        st.info(
            "🎭 **演示模式**: 当前显示的是模拟分析数据，用于界面演示。要获取真实分析结果，请配置正确的API密钥。"
        )
        if results.get("demo_reason"):
            with st.expander("查看详细信息"):
                st.text(results["demo_reason"])

    # 投资决策摘要
    render_decision_summary(decision, stock_symbol)

    # 分析配置信息
    render_analysis_info(results)

    # 详细分析报告（合并主笔人长文与逐个智能体展示）
    render_detailed_analysis(results)

    # ChartingArtist可视化图表（如果启用）
    render_charting_artist_section(results, stock_symbol)

    # 置顶操作区（导出/订阅/再次分析）
    with st.container():
        cols = st.columns([2, 1, 1, 1, 1])
        with cols[0]:
            st.caption("操作")
            render_export_buttons(results)
            # 追加：摘要数据 CSV/Excel/JSON 导出
            try:
                import io

                import pandas as _pd

                decision_row = {
                    "stock_symbol": stock_symbol,
                    "action": decision.get("action"),
                    "confidence": decision.get("confidence"),
                    "risk_score": decision.get("risk_score"),
                    "target_price": decision.get("target_price"),
                    "llm_provider": results.get("llm_provider"),
                    "llm_model": results.get("llm_model"),
                    "research_depth": results.get("research_depth"),
                }
                df_summary = _pd.DataFrame([decision_row])
                csv_bytes = df_summary.to_csv(index=False, encoding="utf-8-sig").encode(
                    "utf-8-sig"
                )
                st.download_button(
                    label="下载摘要 CSV",
                    data=csv_bytes,
                    file_name=f"{stock_symbol}_summary.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key=f"dl_summary_csv_{stock_symbol}",
                )
                try:
                    excel_b = io.BytesIO()
                    with _pd.ExcelWriter(excel_b, engine="openpyxl") as writer:
                        df_summary.to_excel(writer, index=False, sheet_name="summary")
                    excel_b.seek(0)
                    st.download_button(
                        label="下载摘要 Excel",
                        data=excel_b.getvalue(),
                        file_name=f"{stock_symbol}_summary.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"dl_summary_xlsx_{stock_symbol}",
                    )
                except Exception:
                    pass
                # 原始结果 JSON
                import json as _json

                st.download_button(
                    label="下载结果 JSON",
                    data=_json.dumps(results, ensure_ascii=False, indent=2).encode(
                        "utf-8"
                    ),
                    file_name=f"{stock_symbol}_results.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"dl_results_json_{stock_symbol}",
                )
            except Exception:
                pass
        with cols[1]:
            st.caption("邮件")
            render_email_sender(results)
        with cols[2]:
            st.caption("订阅发送")
            if st.button("📧 发送到订阅邮箱", use_container_width=True):
                try:
                    from datetime import datetime as _dt

                    from tradingagents.services.mailer.email_sender import EmailSender
                    from tradingagents.services.subscription.subscription_manager import (
                        SubscriptionManager,
                    )

                    symbol = results.get("stock_symbol") or ""
                    # 推断市场类型
                    import re as _re

                    if _re.match(r"^\d{6}$", str(symbol)):
                        pass
                    elif str(symbol).upper().endswith(".HK"):
                        pass
                    else:
                        pass

                    sm = SubscriptionManager()
                    # 仅针对个股订阅
                    subs = [
                        s
                        for s in sm.get_active_subscriptions(subscription_type="stock")
                        if s.get("symbol") == str(symbol).upper()
                    ]
                    recipients = sorted(
                        list({s.get("email") for s in subs if s.get("email")})
                    )
                    if not recipients:
                        st.warning("未找到匹配该股票的订阅邮箱")
                    else:
                        # 组装分析结果摘要
                        analysis_result = {
                            "analysis_date": results.get("analysis_date")
                            or _dt.now().strftime("%Y-%m-%d"),
                            "decision": results.get("decision", {}),
                            "full_analysis": "\n\n".join(
                                [
                                    results.get("state", {}).get("market_report", ""),
                                    results.get("state", {}).get(
                                        "fundamentals_report", ""
                                    ),
                                    results.get("state", {}).get(
                                        "sentiment_report", ""
                                    ),
                                    results.get("state", {}).get("news_report", ""),
                                ]
                            ),
                        }
                        es = EmailSender()
                        ok = es.send_analysis_report(
                            recipients=recipients,
                            stock_symbol=str(symbol),
                            analysis_result=analysis_result,
                            attachments=None,
                        )
                        if ok:
                            st.success(f"✅ 已发送至 {len(recipients)} 个订阅邮箱")
                        else:
                            st.error("发送失败，请检查邮件配置")
                except Exception as e:
                    st.error(f"发送失败: {e}")
        with cols[3]:
            st.caption("再次分析")
            if st.button("🔁 再次分析", use_container_width=True):
                st.session_state.analysis_results = None
                st.session_state.show_analysis_results = False
                st.rerun()

        with cols[4]:
            st.caption("知识库索引")
            if st.button("📚 仅索引本次分析", use_container_width=True):
                try:
                    with st.spinner("正在将本次分析写入文库并重建索引…"):
                        res = ingest_analysis_results(results)
                    export_dir = (res.get("export") or {}).get("target_dir")
                    idx = res.get("index") or {}
                    if idx.get("success"):
                        st.success(
                            f"索引完成：新增 {idx.get('added',0)}，跳过 {idx.get('skipped',0)}\n目录: {export_dir}"
                        )
                    else:
                        st.warning(f"索引未完成：{idx}")
                except Exception as _e:
                    st.error(f"索引失败：{_e}")

    # 风险提示
    render_risk_warning(is_demo)

    # 已将导出与订阅上移到置顶操作区
    st.markdown("</div>", unsafe_allow_html=True)


def render_analysis_info(results):
    """渲染分析配置信息"""

    with st.expander("📋 分析配置信息", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            llm_provider = results.get("llm_provider", "google")
            provider_name = {
                "google": "Google AI",
                "deepseek": "DeepSeek",
                "openai": "OpenAI",
            }.get(llm_provider, llm_provider)

            st.metric(label="LLM提供商", value=provider_name, help="使用的AI模型提供商")

        with col2:
            llm_model = results.get("llm_model", "N/A")
            logger.debug(f"🔍 [DEBUG] llm_model from results: {llm_model}")
            model_display = {
                "gemini-2.5-pro": "Gemini 2.5 Pro",
                "gemini-2.5-flash": "Gemini 2.5 Flash",
                "deepseek-chat": "DeepSeek Chat",
            }.get(llm_model, llm_model)

            st.metric(label="AI模型", value=model_display, help="使用的具体AI模型")

        with col3:
            analysts = results.get("analysts", [])
            logger.debug(f"🔍 [DEBUG] analysts from results: {analysts}")
            analysts_count = len(analysts) if analysts else 0

            st.metric(
                label="分析师数量",
                value=f"{analysts_count}个",
                help="参与分析的AI分析师数量",
            )

        # 展示双模型位与路由策略（若有）
        extra_cols = st.columns(3)
        with extra_cols[0]:
            quick_model = results.get("metadata", {}).get(
                "llm_quick_model"
            ) or results.get("llm_quick_model")
            if quick_model:
                st.caption("快速模型(Quick)")
                st.code(str(quick_model))
        with extra_cols[1]:
            deep_model = results.get("metadata", {}).get(
                "llm_deep_model"
            ) or results.get("llm_model")
            if deep_model:
                st.caption("深度模型(Deep)")
                st.code(str(deep_model))
        with extra_cols[2]:
            routing = results.get("metadata", {}).get(
                "routing_strategy"
            ) or results.get("routing_strategy")
            if routing:
                st.caption("路由策略")
                st.code(str(routing))

        # 显示分析师列表（兼容单模型与多模型角色键）
        if analysts:
            st.write("**参与的分析师/智能体:**")

            # 优先通过角色库获取中文名
            def _role_name(role_key: str) -> str:
                try:
                    from web.utils.ui_utils import get_role_display_name as _disp

                    name = _disp(role_key)
                except Exception:
                    name = None
                # 兜底映射（覆盖单模型与多模型常见键）
                fallback = {
                    # 单模型旧键
                    "market": "📈 市场技术分析师",
                    "fundamentals": "💰 基本面分析师",
                    "news": "📰 新闻分析师",
                    "social_media": "💭 社交媒体分析师",
                    "risk": "⚠️ 风险评估师",
                    # 多模型新键
                    "news_hunter": "📰 快讯猎手",
                    "fundamental_expert": "💰 基本面专家",
                    "technical_analyst": "📈 技术分析师",
                    "sentiment_analyst": "💭 情绪分析师",
                    "risk_manager": "🛡️ 风控经理",
                    "policy_researcher": "📋 政策研究员",
                    "tool_engineer": "🔧 工具工程师",
                    "compliance_officer": "⚖️ 合规官",
                    "chief_decision_officer": "🎯 首席决策官",
                }
                base = name or fallback.get(role_key, role_key)
                return base

            analyst_list = [_role_name(a) for a in analysts]
            st.write(" • ".join(analyst_list))


def render_decision_summary(decision, stock_symbol=None):
    """渲染投资决策摘要（卡片化）"""

    st.subheader("🎯 投资决策摘要")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        action = decision.get("action", "N/A")

        # 将英文投资建议转换为中文
        action_translation = {
            "BUY": "买入",
            "SELL": "卖出",
            "HOLD": "持有",
            "买入": "买入",
            "卖出": "卖出",
            "持有": "持有",
        }

        # 获取中文投资建议
        chinese_action = action_translation.get(action.upper(), action)

        {
            "BUY": "normal",
            "SELL": "inverse",
            "HOLD": "off",
            "买入": "normal",
            "卖出": "inverse",
            "持有": "off",
        }.get(action.upper(), "normal")

        st.markdown(
            f"""
        <div class="ta-card">
          <h4>投资建议</h4>
          <p style="font-size:1.25rem;font-weight:700;">{chinese_action}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        confidence = decision.get("confidence", 0)
        if isinstance(confidence, (int, float)):
            confidence_str = f"{confidence:.1%}"
            f"{confidence-0.5:.1%}" if confidence != 0 else None
        else:
            confidence_str = str(confidence)

        st.markdown(
            f"""
        <div class="ta-card">
          <h4>置信度</h4>
          <p style="font-size:1.25rem;font-weight:700;">{confidence_str}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col3:
        risk_score = decision.get("risk_score", 0)
        if isinstance(risk_score, (int, float)):
            risk_str = f"{risk_score:.1%}"
            f"{risk_score-0.3:.1%}" if risk_score != 0 else None
        else:
            risk_str = str(risk_score)

        st.markdown(
            f"""
        <div class="ta-card">
          <h4>风险评分</h4>
          <p style="font-size:1.25rem;font-weight:700;">{risk_str}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col4:
        target_price = decision.get("target_price")
        logger.debug(
            f"🔍 [DEBUG] target_price from decision: {target_price}, type: {type(target_price)}"
        )
        logger.debug(
            f"🔍 [DEBUG] decision keys: {list(decision.keys()) if isinstance(decision, dict) else 'Not a dict'}"
        )

        # 根据股票代码确定货币符号
        def is_china_stock(ticker_code):
            import re

            return re.match(r"^\d{6}$", str(ticker_code)) if ticker_code else False

        is_china = is_china_stock(stock_symbol)
        currency_symbol = "¥" if is_china else "$"

        # 处理目标价格显示
        if (
            target_price is not None
            and isinstance(target_price, (int, float))
            and target_price > 0
        ):
            price_display = f"{currency_symbol}{target_price:.2f}"
        else:
            price_display = "待分析"

        st.markdown(
            f"""
        <div class="ta-card">
          <h4>目标价位</h4>
          <p style="font-size:1.25rem;font-weight:700;">{price_display}</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

    # 分析推理
    if "reasoning" in decision and decision["reasoning"]:
        with st.expander("🧠 AI分析推理", expanded=True):
            try:
                st.markdown(sanitize_markdown_for_streamlit(str(decision["reasoning"])))
            except Exception:
                st.markdown(str(decision["reasoning"]))


def render_detailed_analysis(results):
    """渲染详细分析报告（按智能体与主笔人长文分组）"""

    st.subheader("📋 详细分析报告")

    stock_symbol = results.get("stock_symbol", "")

    agents_used = results.get("agents_used") or []
    nested_results = results.get("results")

    has_agent_results = isinstance(nested_results, dict) or bool(agents_used)

    if has_agent_results:
        # 智能体显示顺序与名称
        AGENT_INFO = {
            "news_hunter": ("📰", "快讯猎手"),
            "technical_analyst": ("📈", "技术分析师"),
            "policy_researcher": ("📋", "政策研究员"),
            "fundamental_expert": ("💰", "基本面专家"),
            "sentiment_analyst": ("💭", "情绪分析师"),
            "tool_engineer": ("🔧", "工具工程师"),
            "risk_manager": ("🛡️", "风控经理"),
            "compliance_officer": ("⚖️", "合规官"),
            "chief_decision_officer": ("🎯", "首席决策官"),
        }
        agent_order = list(AGENT_INFO.keys())

        # 构建标签名：主笔人长文 + 智能体
        tab_titles = ["📝 主笔人长文"] + [
            f"{AGENT_INFO[a][0]} {AGENT_INFO[a][1]}" for a in agent_order
        ]
        tabs = st.tabs(tab_titles)

        # 主笔人长文
        with tabs[0]:
            render_main_article_section(results, stock_symbol)

        # 智能体逐个标签（合并自原‘逐个’区域）
        for idx, agent in enumerate(agent_order, start=1):
            with tabs[idx]:
                # 未勾选 → 显示占位
                if agents_used and agent not in agents_used:
                    st.info("未启用智能体")
                    continue

                # 尝试解析该智能体的输出
                agent_result = None
                if isinstance(nested_results, dict):
                    # 直接键命中
                    if agent in nested_results and isinstance(nested_results[agent], dict):
                        agent_result = nested_results.get(agent)
                    else:
                        # 顶层扫描含 agent_type 的对象
                        for _, v in nested_results.items():
                            if isinstance(v, dict) and v.get("agent_type") == agent:
                                agent_result = v
                                break

                if not agent_result:
                    st.info("暂无内容")
                    continue

                analysis_content = (
                    agent_result.get("analysis")
                    or agent_result.get("result")
                    or agent_result.get("content")
                    or ""
                )

                if analysis_content:
                    st.markdown("**分析内容**")
                    try:
                        st.markdown(sanitize_markdown_for_streamlit(str(analysis_content)))
                    except Exception:
                        st.write(analysis_content)
                else:
                    st.info("该智能体本次未产生可展示的输出。")

                col1, col2, col3 = st.columns(3)
                with col1:
                    confidence = agent_result.get("confidence", 0)
                    st.metric(
                        "置信度",
                        (
                            f"{confidence:.1%}"
                            if isinstance(confidence, (int, float)) and confidence > 0
                            else "N/A"
                        ),
                    )
                with col2:
                    model_used = agent_result.get("model_used") or "unknown"
                    if model_used != "unknown":
                        st.info(f"🤖 使用模型: {model_used}")
                with col3:
                    exec_time = agent_result.get("execution_time") or 0
                    if isinstance(exec_time, (int, float)) and exec_time > 0:
                        st.info(f"⏱️ 耗时: {int(exec_time)}ms")

                recommendations = agent_result.get("recommendations")
                if recommendations and recommendations != "暂无建议":
                    st.markdown("**投资建议**")
                    st.success(str(recommendations))
        return

    # 回退：使用旧的六大板块布局（state）
    state = results.get("state", {})
    analysis_modules = [
        {
            "key": "market_report",
            "title": "📈 市场技术分析",
            "icon": "📈",
            "description": "技术指标、价格趋势、支撑阻力位分析",
        },
        {
            "key": "fundamentals_report",
            "title": "💰 基本面分析",
            "icon": "💰",
            "description": "财务数据、估值水平、盈利能力分析",
        },
        {
            "key": "sentiment_report",
            "title": "💭 市场情绪分析",
            "icon": "💭",
            "description": "投资者情绪、社交媒体情绪指标",
        },
        {
            "key": "news_report",
            "title": "📰 新闻事件分析",
            "icon": "📰",
            "description": "相关新闻事件、市场动态影响分析",
        },
        {
            "key": "risk_assessment",
            "title": "⚠️ 风险评估",
            "icon": "⚠️",
            "description": "风险因素识别、风险等级评估",
        },
        {
            "key": "investment_plan",
            "title": "📋 投资建议",
            "icon": "📋",
            "description": "具体投资策略、仓位管理建议",
        },
    ]

    try:
        show_risk = bool(
            __import__("streamlit").session_state.get("ui_show_risk_assessment", True)
        )
    except Exception:
        show_risk = True
    if not show_risk:
        analysis_modules = [
            m for m in analysis_modules if m.get("key") != "risk_assessment"
        ]

    tabs = st.tabs(
        [f"{module['icon']} {module['title']}" for module in analysis_modules]
    )
    for i, (tab, module) in enumerate(zip(tabs, analysis_modules, strict=False)):
        with tab:
            if module["key"] in state and state[module["key"]]:
                st.markdown(f"*{module['description']}*")
                content = state[module["key"]]
                if isinstance(content, str):
                    st.markdown(sanitize_markdown_for_streamlit(content))
                elif isinstance(content, dict):
                    for key, value in content.items():
                        st.subheader(key.replace("_", " ").title())
                        st.write(value)
                else:
                    st.write(content)
            else:
                st.info(f"暂无{module['title']}数据")


def render_risk_warning(is_demo=False):
    """渲染风险提示"""

    st.markdown("---")
    st.subheader("⚠️ 重要风险提示")

    # 使用Streamlit的原生组件而不是HTML
    if is_demo:
        st.warning("**演示数据**: 当前显示的是模拟数据，仅用于界面演示")
        st.info("**真实分析**: 要获取真实分析结果，请配置正确的API密钥")

    st.error(
        """
    **投资风险提示**:
    - **仅供参考**: 本分析结果仅供参考，不构成投资建议
    - **投资风险**: 股票投资有风险，可能导致本金损失
    - **理性决策**: 请结合多方信息进行理性投资决策
    - **专业咨询**: 重大投资决策建议咨询专业财务顾问
    - **自担风险**: 投资决策及其后果由投资者自行承担
    """
    )

    # 添加时间戳
    st.caption(f"分析生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def create_price_chart(price_data):
    """创建价格走势图"""

    if not price_data:
        return None

    fig = go.Figure()

    # 添加价格线
    fig.add_trace(
        go.Scatter(
            x=price_data["date"],
            y=price_data["price"],
            mode="lines",
            name="股价",
            line=dict(color="#1f77b4", width=2),
        )
    )

    # 设置图表样式
    fig.update_layout(
        title="股价走势图",
        xaxis_title="日期",
        yaxis_title="价格 ($)",
        hovermode="x unified",
        showlegend=True,
    )

    return fig


def create_sentiment_gauge(sentiment_score):
    """创建情绪指标仪表盘"""

    if sentiment_score is None:
        return None

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=sentiment_score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "市场情绪指数"},
            delta={"reference": 50},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0, 25], "color": "lightgray"},
                    {"range": [25, 50], "color": "gray"},
                    {"range": [50, 75], "color": "lightgreen"},
                    {"range": [75, 100], "color": "green"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        )
    )

    return fig


def render_charting_artist_section(results, stock_symbol):
    """渲染ChartingArtist可视化图表部分"""

    if not CHARTING_ARTIST_AVAILABLE:
        return

    # 检查是否启用ChartingArtist
    charting_enabled = os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() == "true"

    if not charting_enabled:
        # 显示简化的启用提示
        with st.expander("📊 智能图表分析 (未启用)", expanded=False):
            st.info(
                """
            🎨 **ChartingArtist绘图师功能**
            
            启用后可自动生成专业的个股分析图表：
            - 📈 K线图与技术指标
            - 📊 财务数据可视化
            - 🎯 风险评估图表
            - 🔥 相关性热力图
            
            启用方法：设置 `CHARTING_ARTIST_ENABLED=true` 并重启应用
            """
            )
        return

    # 渲染完整的可视化界面
    try:
        # 获取分析ID（如果存在）
        analysis_id = results.get("analysis_id") or results.get("current_analysis_id")

        # 使用增强版可视化组件
        render_enhanced_visualization_tab(
            analysis_results=results, analysis_id=analysis_id, symbol=stock_symbol
        )

    except Exception as e:
        logger.error(f"渲染ChartingArtist可视化失败: {e}")
        # 回退到基础可视化组件
        try:
            render_visualization_section(
                analysis_results=results, symbol=stock_symbol, analysis_id=analysis_id
            )
        except Exception as e2:
            logger.error(f"回退渲染也失败: {e2}")
            st.error("可视化组件加载失败")


def render_enhanced_results_with_tabs(results):
    """渲染增强版结果，使用标签页布局"""

    if not results:
        st.warning("暂无分析结果")
        return

    stock_symbol = results.get("stock_symbol", "N/A")

    # 创建主要标签页
    main_tabs = st.tabs(["📋 分析报告", "📊 可视化图表", "🎯 角色对齐", "⚙️ 配置信息"])

    with main_tabs[0]:
        # 原有的分析报告内容
        render_traditional_results_content(results)

    with main_tabs[1]:
        # ChartingArtist可视化图表
        if (
            CHARTING_ARTIST_AVAILABLE
            and os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() == "true"
        ):
            analysis_id = results.get("analysis_id") or results.get(
                "current_analysis_id"
            )
            render_enhanced_visualization_tab(
                analysis_results=results, analysis_id=analysis_id, symbol=stock_symbol
            )
        else:
            st.info("🎨 ChartingArtist功能未启用")
            st.caption("设置 CHARTING_ARTIST_ENABLED=true 启用专业图表功能")

    with main_tabs[2]:
        # 角色对齐展示
        if CHARTING_ARTIST_AVAILABLE:
            render_role_alignment_dashboard()
        else:
            st.info("角色对齐功能需要启用ChartingArtist组件")

    with main_tabs[3]:
        # 分析配置信息
        render_analysis_info(results)

        # 系统状态信息
        render_system_status_info(results)


def render_traditional_results_content(results):
    """渲染传统的分析结果内容"""

    stock_symbol = results.get("stock_symbol", "N/A")
    decision = results.get("decision", {})
    state = results.get("state", {})
    is_demo = results.get("is_demo", False)

    # 如果是演示数据，显示提示
    if is_demo:
        st.info("🎭 **演示模式**: 当前显示的是模拟分析数据，用于界面演示。")
        if results.get("demo_reason"):
            with st.expander("查看详细信息"):
                st.text(results["demo_reason"])

    # 投资决策摘要
    render_decision_summary(decision, stock_symbol)

    # 详细分析报告
    render_detailed_analysis(results)

    # 置顶操作区
    with st.container():
        cols = st.columns([2, 1, 1])
        with cols[0]:
            st.caption("操作")
            render_export_buttons(results)
        with cols[1]:
            st.caption("邮件")
            render_email_sender(results)
        with cols[2]:
            st.caption("再次分析")
            if st.button("🔁 再次分析", use_container_width=True):
                st.session_state.analysis_results = None
                st.session_state.show_analysis_results = False
                st.rerun()

    # 主笔人长文（上方已处理），避免重复渲染
    # render_main_article_section(results, stock_symbol)

    # 风险提示（上方已处理），避免重复渲染
    # render_risk_warning(is_demo)


def render_main_article_section(results, stock_symbol):
    """渲染主笔人长文部分"""

    final_article = results.get("final_article")
    final_article_metrics = results.get("final_article_metrics", {})

    if isinstance(final_article, str) and final_article.strip():
        st.markdown("---")
        st.subheader("📝 主笔人长文（融合多方观点）")
        with st.expander("点击展开查看主笔人长文", expanded=True):
            st.markdown(final_article)
            import io

            article_bytes = final_article.encode("utf-8")
            st.download_button(
                label="下载主笔人长文 (Markdown)",
                data=io.BytesIO(article_bytes),
                file_name=f"final_article_{stock_symbol}.md",
                mime="text/markdown",
                key=f"dl_final_article_md2_{stock_symbol}",
            )
            if final_article_metrics:
                cols = st.columns(2)
                with cols[0]:
                    st.caption(
                        f"文章长度: {final_article_metrics.get('word_count', 0)} 字符"
                    )
                with cols[1]:
                    st.caption(
                        f"章节覆盖数: {final_article_metrics.get('sections_covered', 0)}"
                    )


def render_system_status_info(results):
    """渲染系统状态信息"""

    with st.expander("🔧 系统状态", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            # ChartingArtist状态
            charting_enabled = (
                os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() == "true"
            )
            status_icon = "✅" if charting_enabled else "⚠️"
            st.markdown(f"**ChartingArtist:** {status_icon}")

        with col2:
            # 组件可用性
            components_status = "✅" if CHARTING_ARTIST_AVAILABLE else "❌"
            st.markdown(f"**可视化组件:** {components_status}")

        with col3:
            # 分析时间
            analysis_time = results.get("analysis_time", "N/A")
            st.markdown(f"**分析耗时:** {analysis_time}")


# 导出新增的函数
__all__ = [
    "render_results",
    "render_enhanced_results_with_tabs",
    "render_charting_artist_section",
    "render_traditional_results_content",
]
