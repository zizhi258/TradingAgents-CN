#!/usr/bin/env python3
"""
Streamlit 页面：指数与筛选

与后端 Market API 对接，支持：
- 组合筛选（中小板、ST）
- 自定义筛选（市场/代码前缀/名称包含/ST过滤等）
# 注：指数预设与成分功能已移除
"""

from __future__ import annotations

import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

import streamlit as st
import pandas as pd

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('indices_filters')


def _client():
    from web.utils.market_api_client import MarketAnalysisAPIClient
    base_url = os.getenv('MARKET_API_BASE_URL') or os.getenv('API_BASE_URL') or 'http://localhost:8000'
    return MarketAnalysisAPIClient(base_url=base_url)


# ====== 美股/港股快捷面板（利用 Finnhub/AKShare/Yahoo） ======
def _render_us_quick_panel():
    st.subheader("🇺🇸 美股快捷面板")
    st.caption("基于 Finnhub + Yahoo（回退）获取快照/基本面/新闻")

    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("美股代码 (示例 AAPL, NVDA)", value="AAPL").strip().upper()
    with col2:
        lookback_days = st.selectbox("时间范围", [30, 90, 180, 365], index=1, help="用于快照/历史数据的展示")

    show_snapshot = st.checkbox("📊 实时快照", value=True)
    show_fundamentals = st.checkbox("💰 基本面 (Finnhub)", value=True)
    show_news = st.checkbox("📰 实时新闻", value=False)

    if st.button("获取美股数据", type="primary"):
        start_date = (date.today() - timedelta(days=int(lookback_days))).isoformat()
        end_date = date.today().isoformat()

        if show_snapshot:
            try:
                from tradingagents.dataflows.optimized_us_data import get_optimized_us_data_provider
                provider = get_optimized_us_data_provider()
                text = provider.get_stock_data(symbol, start_date, end_date)
                if text:
                    st.markdown(text)
                else:
                    st.info("未获取到快照数据（可能是网络/密钥/代码问题）")
            except Exception as e:
                st.warning(f"快照获取失败: {e}")

        if show_fundamentals:
            try:
                from tradingagents.dataflows.interface import get_fundamentals_finnhub
                text = get_fundamentals_finnhub(symbol, end_date)
                st.markdown(text)
            except Exception as e:
                st.warning(f"基本面获取失败: {e}")

        if show_news:
            try:
                from tradingagents.dataflows.realtime_news_utils import RealtimeNewsAggregator
                agg = RealtimeNewsAggregator()
                items = agg.get_realtime_stock_news(symbol, hours_back=12)
                if not items:
                    st.info("未获取到相关新闻或网络受限")
                else:
                    st.markdown("#### 最新新闻")
                    for it in items[:10]:
                        st.write(f"- [{it.title}]({it.url}) · {it.source} · {it.publish_time.strftime('%Y-%m-%d %H:%M')}")
            except Exception as e:
                st.warning(f"新闻获取失败: {e}")


def _render_hk_quick_panel():
    st.subheader("🇭🇰 港股快捷面板")
    st.caption("优先 AKShare，其次 Yahoo，再回退 Finnhub")

    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.text_input("港股代码 (示例 0700.HK, 09988.HK)", value="0700.HK").strip().upper()
    with col2:
        lookback_days = st.selectbox("时间范围", [30, 90, 180, 365], index=1)

    show_snapshot = st.checkbox("📊 行情与概览", value=True, key="hk_snapshot")
    show_news = st.checkbox("📰 实时新闻", value=False, key="hk_news")

    if st.button("获取港股数据", type="primary"):
        start_date = (date.today() - timedelta(days=int(lookback_days))).isoformat()
        end_date = date.today().isoformat()

        if show_snapshot:
            try:
                from tradingagents.dataflows.interface import get_hk_stock_data_unified
                text = get_hk_stock_data_unified(symbol, start_date, end_date)
                if text:
                    st.markdown(text)
                else:
                    st.info("未获取到港股数据（可能是网络/依赖/代码问题）")
            except Exception as e:
                st.warning(f"港股数据获取失败: {e}")

        if show_news:
            try:
                from tradingagents.dataflows.realtime_news_utils import RealtimeNewsAggregator
                agg = RealtimeNewsAggregator()
                items = agg.get_realtime_stock_news(symbol, hours_back=12)
                if not items:
                    st.info("未获取到相关新闻或网络受限")
                else:
                    st.markdown("#### 最新新闻")
                    for it in items[:10]:
                        st.write(f"- [{it.title}]({it.url}) · {it.source} · {it.publish_time.strftime('%Y-%m-%d %H:%M')}")
            except Exception as e:
                st.warning(f"新闻获取失败: {e}")


def _export_bytes_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')


def _export_bytes_excel(df: pd.DataFrame) -> Optional[bytes]:
    try:
        import io
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='data')
        bio.seek(0)
        return bio.read()
    except Exception:
        return None


def _quick_chart(selected_df: pd.DataFrame, code_fields: List[str]):
    """Render quick line chart for selected symbols (near 90 days)."""
    if selected_df.empty:
        return
    try:
        from web.utils.market_api_client import MarketAnalysisAPIClient
        import plotly.express as px
        client = MarketAnalysisAPIClient()
        today = date.today()
        start_date = (today - timedelta(days=90)).isoformat()
        frames = []
        for _, row in selected_df.iterrows():
            code = None
            for fld in code_fields:
                val = str(row.get(fld) or '').strip()
                if val:
                    code = val
                    break
            if not code:
                continue
            resp = client.get_daily(code=code, start_date=start_date, end_date=today.isoformat(), adj='qfq')
            recs = resp.get('data', [])
            if not recs:
                continue
            df_line = pd.DataFrame(recs)
            if df_line.empty:
                continue
            date_col = 'trade_date' if 'trade_date' in df_line.columns else ('date' if 'date' in df_line.columns else None)
            price_col = 'close' if 'close' in df_line.columns else None
            if not date_col or not price_col:
                continue
            df_line[date_col] = pd.to_datetime(df_line[date_col])
            df_line = df_line.rename(columns={date_col: 'date'})
            df_line['symbol'] = code
            frames.append(df_line[['date', 'symbol', price_col]].rename(columns={price_col: 'close'}))
        if frames:
            data = pd.concat(frames, ignore_index=True)
            fig = px.line(data, x='date', y='close', color='symbol')
            fig.update_layout(height=380, legend_title_text='代码')
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.info(f"无法生成快速图表: {e}")


def _render_table_with_actions(title: str, rows: List[Dict[str, Any]], code_fields: List[str], page_key: str):
    st.subheader(title)
    if not rows:
        st.info("无数据")
        return
    try:
        df_all = pd.DataFrame(rows)
    except Exception as e:
        st.write(rows[:50])
        st.warning(f"数据表渲染失败: {e}")
        return

    # 分页
    col_p1, col_p2, _ = st.columns([1, 1, 4])
    with col_p1:
        page_size = st.slider("每页数量", 10, 500, 100, 10, key=f"{page_key}_ps")
    total_rows = len(df_all)
    total_pages = max(1, (total_rows + page_size - 1) // page_size)
    with col_p2:
        page = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1, key=f"{page_key}_p")
    start = (page - 1) * page_size
    end = start + page_size
    df_page = df_all.iloc[start:end].reset_index(drop=True)

    # 表格 + 选择
    selected = st.dataframe(
        df_page,
        use_container_width=True,
        height=500,
        on_select="rerun",
        selection_mode="multi-row",
    )
    sel_idx = list(getattr(getattr(selected, 'selection', None), 'rows', []) or [])
    df_selected = df_page.iloc[sel_idx] if sel_idx else df_page.iloc[0:0]

    # 导出区
    st.markdown("#### 📤 导出与操作")
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    with col_e1:
        st.download_button("下载选中CSV", data=_export_bytes_csv(df_selected) if not df_selected.empty else b"", file_name="selected.csv", mime="text/csv", disabled=df_selected.empty)
    with col_e2:
        xbytes = _export_bytes_excel(df_selected) if not df_selected.empty else None
        st.download_button("下载选中Excel", data=xbytes or b"", file_name="selected.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", disabled=(xbytes is None))
    with col_e3:
        st.download_button("下载本页CSV", data=_export_bytes_csv(df_page), file_name="page.csv", mime="text/csv")
    with col_e4:
        st.download_button("下载全部CSV", data=_export_bytes_csv(df_all), file_name="all.csv", mime="text/csv")

    # 生成图表 / 启动个股分析
    st.markdown("#### 🎨 生成图表 / 📑 启动个股分析")
    col_a1, col_a2, col_a3 = st.columns(3)
    with col_a1:
        if st.button("为选中生成图表", disabled=df_selected.empty, key=f"gen_charts_{page_key}"):
            try:
                # 限制最大批量，避免阻塞
                max_batch = 5
                from web.components.charting_artist_component import ChartingArtistAPIClient
                from web.utils.market_api_client import MarketAnalysisAPIClient
                chart_client = ChartingArtistAPIClient()
                market_client = MarketAnalysisAPIClient()
                # 基础配置
                import uuid
                generated = 0
                for _, row in df_selected.head(max_batch).iterrows():
                    symbol = None
                    for fld in code_fields:
                        val = str(row.get(fld) or '').strip()
                        if val:
                            symbol = val
                            break
                    if not symbol:
                        continue
                    # 拉取行情
                    from datetime import date, timedelta
                    today = date.today()
                    start_date = (today - timedelta(days=180)).isoformat()
                    mkt = market_client.get_daily(code=symbol, start_date=start_date, end_date=today.isoformat(), adj='qfq')
                    analysis_id = f"idx_{page_key}_{uuid.uuid4().hex[:8]}"
                    req = {
                        "analysis_id": analysis_id,
                        "chart_types": ["candlestick", "line_chart"],
                        "config": {"theme": "plotly_dark", "width": 900},
                        "data_sources": {
                            "symbol": symbol,
                            "analysis_results": {},
                            "market_data": mkt,
                        },
                        "priority": "normal",
                    }
                    resp = chart_client.generate_charts(req)
                    if isinstance(resp, dict) and (resp.get("status") in ("queued", "completed") or resp.get("result")):
                        generated += 1
                if generated:
                    st.success(f"✅ 已提交 {generated} 个股票的图表生成任务（最多 {max_batch} 个）。")
                else:
                    st.info("未能生成图表，请检查所选数据或后端 API 状态。")
            except Exception as e:
                st.error(f"生成图表失败: {e}")
    with col_a2:
        if st.button("为选中启动个股分析", disabled=df_selected.empty, key=f"start_single_analysis_{page_key}"):
            try:
                # 仅取第一个选中项以避免并发复杂度
                first = df_selected.iloc[0] if not df_selected.empty else None
                symbol = None
                for fld in code_fields:
                    val = str(first.get(fld) or '').strip()
                    if val:
                        symbol = val
                        break
                if not symbol:
                    st.warning("未找到可用股票代码")
                else:
                    # 预填表单配置并跳转到个股分析页
                    st.session_state.form_config = {
                        'stock_symbol': symbol,
                        'market_type': 'A股',
                        'research_depth': 3,
                        'selected_analysts': ['market', 'fundamentals', 'news'],
                        'include_sentiment': True,
                        'include_risk_assessment': True,
                        'custom_prompt': '',
                    }
                    st.session_state.top_nav_page = "📊 个股分析"
                    st.success(f"已跳转到个股分析并预填代码: {symbol}")
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"启动个股分析失败: {e}")

    with col_a3:
        # 快捷入口：跳转到图表管理
        if st.button("打开图表管理", key=f"open_chart_mgmt_{page_key}"):
            try:
                st.session_state.top_nav_page = "📊 个股分析"
                # 让主页面切换到“📋 结果”Tab
                st.session_state.show_analysis_results = True
                # 在可视化组件内自动切换到“图表管理”子页
                st.session_state._open_chart_management = True
                st.experimental_rerun()
            except Exception as e:
                st.warning(f"无法跳转: {e}")

    # 一键生成：图表 + 报告（选中项，限量）
    st.markdown("#### 🧰 一键生成：图表 + 报告")
    if st.button("一键生成 (选中 ≤ 3)", disabled=df_selected.empty, key=f"one_click_generate_{page_key}"):
        try:
            max_batch = 3
            from web.components.charting_artist_component import ChartingArtistAPIClient
            from web.utils.market_api_client import MarketAnalysisAPIClient
            from web.utils.analysis_runner import run_stock_analysis
            from web.utils.report_exporter import ReportExporter
            import io, zipfile, json
            chart_client = ChartingArtistAPIClient()
            market_client = MarketAnalysisAPIClient()
            exporter = ReportExporter()

            zip_buffer = io.BytesIO()
            zf = zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED)
            generated = 0

            for _, row in df_selected.head(max_batch).iterrows():
                symbol = None
                for fld in code_fields:
                    val = str(row.get(fld) or '').strip()
                    if val:
                        symbol = val
                        break
                if not symbol:
                    continue

                # 1) 生成基础图表（近180日K线+折线）
                from datetime import date, timedelta
                today = date.today()
                start_date = (today - timedelta(days=180)).isoformat()
                mkt = market_client.get_daily(code=symbol, start_date=start_date, end_date=today.isoformat(), adj='qfq')
                import uuid as _uuid
                analysis_id = f"idx_oc_{page_key}_{_uuid.uuid4().hex[:8]}"
                req = {
                    "analysis_id": analysis_id,
                    "chart_types": ["candlestick", "line_chart"],
                    "config": {"theme": "plotly_dark", "width": 900},
                    "data_sources": {"symbol": symbol, "analysis_results": {}, "market_data": mkt},
                    "priority": "normal",
                }
                chart_resp = chart_client.generate_charts(req)
                # 将图表任务入包记录
                zf.writestr(f"{symbol}/charts_task.json", json.dumps(chart_resp, ensure_ascii=False, indent=2))

                # 2) 运行轻量个股分析并生成报告（Markdown/Docx可用其一）
                try:
                    # 采用默认设置：A股 + 3级深度 + 基本三分析师
                    result = run_stock_analysis(
                        stock_symbol=symbol,
                        analysis_date=today.isoformat(),
                        analysts=['market', 'fundamentals', 'news'],
                        research_depth=3,
                        llm_provider=os.getenv('DEFAULT_PROVIDER', 'deepseek'),
                        llm_model=os.getenv('DEFAULT_MODEL', 'deepseek-chat'),
                        market_type='A股',
                        progress_callback=None,
                        llm_quick_model=os.getenv('DEFAULT_MODEL', 'deepseek-chat'),
                        llm_deep_model=os.getenv('DEFAULT_MODEL', 'deepseek-chat'),
                        routing_strategy=os.getenv('ROUTING_STRATEGY', '均衡'),
                        fallbacks=[],
                        max_budget=float(os.getenv('MAX_COST_PER_SESSION', '1.0') or 1.0),
                    )
                    # 保存原始结果
                    zf.writestr(f"{symbol}/analysis_result.json", json.dumps(result, ensure_ascii=False, indent=2))

                    # 生成 Markdown
                    try:
                        md_bytes = exporter.export_report(result, 'markdown') or b''
                        if md_bytes:
                            zf.writestr(f"{symbol}/report.md", md_bytes)
                    except Exception:
                        pass

                    # 生成 Docx（若环境可用）
                    try:
                        docx_bytes = exporter.export_report(result, 'docx')
                        if docx_bytes:
                            zf.writestr(f"{symbol}/report.docx", docx_bytes)
                    except Exception:
                        # 若 docx 失败则忽略
                        pass
                except Exception as e:
                    # 如果分析失败，记录错误
                    zf.writestr(f"{symbol}/error.txt", str(e))

                generated += 1

            zf.close()
            zip_buffer.seek(0)
            if generated:
                st.success(f"✅ 已为 {generated} 只股票提交图表任务并生成报告包")
                st.download_button(
                    label="下载一键生成结果 (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name="one_click_reports.zip",
                    mime="application/zip",
                )
            else:
                st.info("未能生成任何输出，请检查所选数据或密钥配置")
        except Exception as e:
            st.error(f"一键生成失败: {e}")

    # 快速图表
    if sel_idx:
        st.markdown("#### 📈 选中股票快速图表（近90日）")
        _quick_chart(df_selected, code_fields)


# 指数预设与成分功能已移除


def section_group_filters():
    st.header("🧩 组合筛选")
    c = _client()

    group = st.selectbox("选择组合", ["中小板 (sme)", "ST 股票 (st)"])
    group_slug = group.split('(')[-1].strip(')')
    page_size = st.slider("每页数量", 20, 500, 100, 10)

    if st.button("筛选", type="primary"):
        try:
            resp = c.filter_group(group_slug, page=1, page_size=page_size)
            items = resp.get('items', [])
            rows = [i if isinstance(i, dict) else dict(i) for i in items]
            st.session_state['indices_filters_last_group_rows'] = rows
            st.session_state['indices_filters_last_group_title'] = f"{group} - 前 {len(rows)} 条"
        except Exception as e:
            st.error(f"筛选失败: {e}")
    rows = st.session_state.get('indices_filters_last_group_rows')
    title = st.session_state.get('indices_filters_last_group_title')
    if isinstance(rows, list):
        _render_table_with_actions(title or "组合筛选结果", rows, code_fields=["code", "con_code"], page_key="group_filter")


def section_custom_filter():
    st.header("🧪 自定义筛选")
    c = _client()

    with st.form("custom_filter_form"):
        markets = st.multiselect("市场", ["上海", "深圳"], default=["上海", "深圳"]) 
        code_prefixes = st.text_input("代码前缀（逗号分隔）", value="000,600,002", help="例如 000,600,002")
        name_contains = st.text_input("名称包含")
        col1, col2 = st.columns(2)
        with col1:
            include_st = st.checkbox("仅包含 ST")
        with col2:
            exclude_st = st.checkbox("排除 ST", value=True)
        category_in = st.text_input("类别包含（逗号分隔，可留空）")
        limit = st.slider("返回数量上限", 50, 1000, 200, 50)

        submitted = st.form_submit_button("执行筛选")
        if submitted:
            payload: Dict[str, Any] = {
                "markets": markets or None,
                "code_prefixes": [s.strip() for s in code_prefixes.split(',') if s.strip()] or None,
                "name_contains": name_contains or None,
                "include_st": True if include_st else None,
                "exclude_st": True if exclude_st else None,
                "category_in": [s.strip() for s in category_in.split(',') if s.strip()] or None,
                "limit": int(limit),
                "offset": 0,
            }
            try:
                data = c.filter_custom(**payload)
                items = data.get('items', [])
                rows = [i if isinstance(i, dict) else dict(i) for i in items]
                st.session_state['indices_filters_last_custom_rows'] = rows
                st.session_state['indices_filters_last_custom_title'] = f"筛选结果 - 共 {data.get('total', 0)} 条，显示 {len(rows)} 条"
            except Exception as e:
                st.error(f"执行失败: {e}")
    rows = st.session_state.get('indices_filters_last_custom_rows')
    title = st.session_state.get('indices_filters_last_custom_title')
    if isinstance(rows, list):
        _render_table_with_actions(title or "自定义筛选结果", rows, code_fields=["code", "con_code"], page_key="custom_filter")


def render_indices_and_filters():
    st.markdown("## 🧮 指数与筛选")

    market = st.selectbox("市场", ["A股", "美股", "港股"], index=0, key="indices_filters_market")

    if market == "A股":
        _ = _client()  # 初始化客户端，避免展示端口或地址
        st.caption("使用后端 Market API 进行数据获取")
        # 指数预设与成分功能已移除
        section_group_filters()
        st.divider()
        section_custom_filter()
    elif market == "美股":
        # 仅保留美股快捷面板
        st.info("以下为美股快捷面板（外部接口）。")
        _render_us_quick_panel()
    else:
        # 仅保留港股快捷面板
        st.info("以下为港股快捷面板（外部接口）。")
        _render_hk_quick_panel()
