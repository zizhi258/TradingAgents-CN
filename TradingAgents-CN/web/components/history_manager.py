"""
历史记录页面组件
提供分析历史记录的查看、搜索、导出功能
包含Token使用统计和成本分析
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from web.modules.history_service import HistoryService
from tradingagents.utils.logging_manager import get_logger
from tradingagents.config.config_manager import config_manager, UsageRecord

logger = get_logger('web.history')


def render_history_page():
    """渲染历史记录页面"""
    
    st.markdown("## 📈 历史记录")
    st.markdown("查看和管理个股分析历史记录")
    
    # 初始化历史记录服务
    try:
        history_service = HistoryService()
    except Exception as e:
        st.error(f"❌ 初始化历史记录服务失败: {e}")
        return
    
    # 页面标签
    tab1, tab2, tab3 = st.tabs([
        "📋 记录列表",
        "🔍 搜索过滤", 
        "📊 统计分析"
    ])
    
    # 记录列表标签页
    with tab1:
        render_history_list(history_service)
        
    # 搜索过滤标签页
    with tab2:
        render_history_search(history_service)
        
    # 统计分析标签页
    with tab3:
        render_history_statistics(history_service)


def render_history_list(history_service: HistoryService):
    """渲染历史记录列表"""
    
    st.markdown("### 分析记录列表")
    
    # 分页设置
    col1, col2, col3 = st.columns(3)
    
    with col1:
        items_per_page = st.selectbox(
            "每页显示",
            [10, 20, 50, 100],
            index=1,
            key="history_items_per_page"
        )
    
    with col2:
        # 获取总记录数用于计算页数
        all_records = history_service.get_analysis_history(limit=10000)
        total_records = len(all_records)
        total_pages = (total_records + items_per_page - 1) // items_per_page
        
        if total_pages > 1:
            current_page = st.selectbox(
                f"页面 (共{total_pages}页)",
                range(1, total_pages + 1),
                key="history_current_page"
            )
        else:
            current_page = 1
    
    with col3:
        if st.button("🔄 刷新数据"):
            st.rerun()
    
    # 获取当前页数据
    offset = (current_page - 1) * items_per_page
    records = history_service.get_analysis_history(limit=items_per_page, offset=offset)
    
    if not records:
        st.info("📭 暂无历史记录")
        return
    
    st.markdown(f"**找到 {total_records} 条记录，显示第 {current_page} 页**")
    
    # 转换为表格数据
    table_data = []
    for record in records:
        # 格式化时间
        try:
            timestamp = datetime.fromisoformat(record.get('timestamp', '').replace('Z', ''))
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
        except:
            formatted_time = record.get('timestamp', '未知')
        
        # 格式化智能体列表
        agents = record.get('agents_used', [])
        agents_str = ', '.join(agents[:3])  # 只显示前3个
        if len(agents) > 3:
            agents_str += f" (+{len(agents)-3})"
        
        table_data.append({
            "分析ID": record['analysis_id'][:16] + "..." if len(record['analysis_id']) > 16 else record['analysis_id'],
            "时间": formatted_time,
            "股票代码": record.get('stock_symbol', '未知'),
            "市场": record.get('market_type', '未知'),
            "模式": record.get('analysis_mode', '未知'),
            "深度": f"L{record.get('research_depth', 0)}",
            "模型": record.get('model_provider', '未知'),
            "状态": "✅ 完成" if record.get('status') == 'completed' else "❌ 失败",
            "建议": record.get('action', '-'),
            "置信度": f"{record.get('confidence', 0):.0%}" if record.get('confidence') else '-',
            "智能体": agents_str
        })
    
    df = pd.DataFrame(table_data)
    
    # 显示表格（支持选择）
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row"
    )
    
    # 操作按钮
    st.markdown("#### 批量操作")
    col4, col5, col6, col7 = st.columns(4)
    
    with col4:
        if st.button("👁️ 查看详情"):
            selected_rows = event.selection.get('rows', []) if hasattr(event, 'selection') else []
            if len(selected_rows) == 1:
                selected_record = records[selected_rows[0]]
                _show_analysis_detail(history_service, selected_record['analysis_id'])
            elif len(selected_rows) > 1:
                st.warning("请选择单条记录查看详情")
            else:
                st.warning("请先选择记录")
    
    with col5:
        if st.button("📄 导出JSON"):
            selected_rows = event.selection.get('rows', []) if hasattr(event, 'selection') else []
            if selected_rows:
                selected_records = [records[i] for i in selected_rows]
                _export_records_json(selected_records)
            else:
                st.warning("请先选择要导出的记录")
    
    with col6:
        if st.button("📝 导出Markdown"):
            selected_rows = event.selection.get('rows', []) if hasattr(event, 'selection') else []
            if selected_rows:
                selected_records = [records[i] for i in selected_rows]
                _export_records_markdown(selected_records)
            else:
                st.warning("请先选择要导出的记录")
    
    with col7:
        if st.button("🗑️ 删除记录"):
            selected_rows = event.selection.get('rows', []) if hasattr(event, 'selection') else []
            if selected_rows:
                _confirm_delete_records(history_service, [records[i] for i in selected_rows])
            else:
                st.warning("请先选择要删除的记录")


def render_history_search(history_service: HistoryService):
    """渲染搜索过滤页面"""
    
    st.markdown("### 搜索与过滤")
    
    # 搜索表单
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            stock_symbol = st.text_input(
                "股票代码",
                placeholder="如：000001, AAPL, 0700.HK",
                help="输入完整股票代码进行精确搜索"
            )
            
            analysis_mode = st.selectbox(
                "分析模式",
                ["全部", "单模型分析", "多模型协作"],
                help="选择分析模式类型"
            )
        
        with col2:
            market_type = st.selectbox(
                "市场类型", 
                ["全部", "A股", "港股", "美股"],
                help="选择股票市场"
            )
            
            model_provider = st.text_input(
                "模型提供商",
                placeholder="如：DeepSeek, Google, Mixed",
                help="模型提供商名称（支持模糊匹配）"
            )
        
        # 时间范围
        st.markdown("#### 时间范围")
        col3, col4 = st.columns(2)
        
        with col3:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now().date() - timedelta(days=30),
                help="选择搜索的开始日期"
            )
        
        with col4:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now().date(),
                help="选择搜索的结束日期"
            )
        
        # 搜索按钮
        submitted = st.form_submit_button("🔍 搜索", type="primary")
    
    if submitted:
        # 构建搜索过滤条件
        filters = {}
        
        if stock_symbol:
            filters['stock_symbol'] = stock_symbol.strip()
        
        if analysis_mode != "全部":
            filters['analysis_mode'] = analysis_mode
        
        if market_type != "全部":
            filters['market_type'] = market_type
        
        if start_date:
            filters['start_date'] = start_date.strftime('%Y-%m-%d')
        
        if end_date:
            filters['end_date'] = end_date.strftime('%Y-%m-%d')
        
        # 执行搜索
        try:
            search_results = history_service.search_analyses(**filters)
            
            st.markdown(f"### 搜索结果 ({len(search_results)} 条)")
            
            if search_results:
                # 显示搜索结果表格
                _display_search_results(search_results)
            else:
                st.info("🔍 未找到匹配的记录")
                
        except Exception as e:
            st.error(f"❌ 搜索失败: {e}")


def render_history_statistics(history_service: HistoryService):
    """渲染统计分析页面（整合Token统计功能）"""
    
    st.markdown("### 📊 统计分析")
    
    # 创建两个主要部分的标签页
    sub_tab1, sub_tab2 = st.tabs([
        "📈 分析记录统计",
        "💰 Token使用统计"
    ])
    
    # 分析记录统计
    with sub_tab1:
        _render_analysis_statistics(history_service)
    
    # Token使用统计
    with sub_tab2:
        _render_token_statistics()


def _render_analysis_statistics(history_service: HistoryService):
    """渲染分析记录统计"""
    
    try:
        stats = history_service.get_statistics()
        
        # 总体统计
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 总分析次数", stats['total_analyses'])
        
        with col2:
            st.metric("📅 近7天", stats['recent_7_days'])
        
        with col3:
            st.metric("📆 近30天", stats['recent_30_days'])
        
        with col4:
            if stats['total_analyses'] > 0:
                avg_per_day = stats['recent_30_days'] / 30
                st.metric("📈 日均分析", f"{avg_per_day:.1f}")
            else:
                st.metric("📈 日均分析", "0")
        
        # 分布统计图表
        col5, col6 = st.columns(2)
        
        with col5:
            st.markdown("#### 市场分布")
            if stats['market_distribution']:
                market_df = pd.DataFrame(
                    list(stats['market_distribution'].items()),
                    columns=['市场', '数量']
                )
                st.bar_chart(market_df.set_index('市场'))
            else:
                st.info("暂无数据")
        
        with col6:
            st.markdown("#### 模式分布")
            if stats['mode_distribution']:
                mode_df = pd.DataFrame(
                    list(stats['mode_distribution'].items()),
                    columns=['模式', '数量']
                )
                st.bar_chart(mode_df.set_index('模式'))
            else:
                st.info("暂无数据")
        
        # 模型使用统计
        st.markdown("#### 模型提供商使用统计")
        if stats['model_distribution']:
            model_data = []
            for provider, count in stats['model_distribution'].items():
                percentage = (count / stats['total_analyses']) * 100
                model_data.append({
                    "提供商": provider,
                    "使用次数": count,
                    "使用比例": f"{percentage:.1f}%"
                })
            
            model_df = pd.DataFrame(model_data)
            st.dataframe(model_df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无模型使用数据")
            
    except Exception as e:
        st.error(f"❌ 获取统计信息失败: {e}")


def _render_token_statistics():
    """渲染Token使用统计（从token_statistics.py迁移）"""
    
    # 侧边栏控制
    with st.sidebar:
        st.subheader("📊 Token统计设置")
        
        # 时间范围选择
        time_range = st.selectbox(
            "统计时间范围",
            ["今天", "最近7天", "最近30天", "最近90天", "全部"],
            index=2,
            key="token_time_range"
        )
        
        # 转换为天数
        days_map = {
            "今天": 1,
            "最近7天": 7,
            "最近30天": 30,
            "最近90天": 90,
            "全部": 365  # 使用一年作为"全部"
        }
        days = days_map[time_range]
        
        # 刷新按钮
        if st.button("🔄 刷新Token数据", use_container_width=True, key="token_refresh"):
            st.rerun()
        
        # 导出数据按钮
        if st.button("📥 导出Token统计", use_container_width=True, key="token_export"):
            _export_token_statistics_data(days)
    
    # 获取Token统计数据
    try:
        stats = config_manager.get_usage_statistics(days)
        records = _load_usage_records_filtered(days)
        
        if not stats or stats.get('total_requests', 0) == 0:
            st.info(f"📊 {time_range}内暂无Token使用记录")
            st.markdown("""
            ### 💡 如何开始记录Token使用？
            
            1. **进行个股分析**: 使用主页面的个股分析功能
            2. **确保API配置**: 检查Google/DeepSeek等API密钥是否正确配置
            3. **启用成本跟踪**: 在配置管理中启用Token成本跟踪
            
            系统会自动记录所有LLM调用的Token使用情况。
            """)
            return
        
        # 1) 概览指标
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 总成本", f"¥{stats['total_cost']:.4f}")
        with col2:
            st.metric("🔢 总调用次数", f"{stats['total_requests']:,}")
        with col3:
            total_tokens = stats['total_input_tokens'] + stats['total_output_tokens']
            st.metric("📊 总Token数", f"{total_tokens:,}")
        with col4:
            avg_cost = stats['total_cost']/stats['total_requests'] if stats['total_requests'] else 0
            st.metric("⚖️ 平均每次成本", f"¥{avg_cost:.4f}")
        
        # 2) Token分布饼图与供应商对比
        col1, col2 = st.columns(2)
        with col1:
            if stats['total_input_tokens'] > 0 or stats['total_output_tokens'] > 0:
                fig_pie = px.pie(
                    values=[stats['total_input_tokens'], stats['total_output_tokens']],
                    names=['输入Token', '输出Token'], 
                    title="Token使用分布",
                    color_discrete_sequence=['#FF6B6B', '#4ECDC4']
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("暂无Token分布数据")
        
        # 3) 供应商对比
        with col2:
            provider_stats = stats.get('provider_stats', {})
            if provider_stats:
                providers = list(provider_stats.keys())
                costs = [provider_stats[p]['cost'] for p in providers]
                
                fig_cost = px.bar(
                    x=providers, 
                    y=costs,
                    title="各供应商成本对比", 
                    labels={'x':'供应商','y':'成本(¥)'},
                    color_discrete_sequence=['#36A2EB', '#FF6384', '#FFCE56', '#4BC0C0']
                )
                st.plotly_chart(fig_cost, use_container_width=True)
            else:
                st.info("暂无供应商对比数据")
        
        # 4) 成本/Token 趋势（双轴）
        if records:
            st.markdown("#### 📈 成本与Token使用趋势")
            df = pd.DataFrame([
                {
                    'date': datetime.fromisoformat(r.timestamp).date(),
                    'cost': r.cost,
                    'tokens': r.input_tokens + r.output_tokens,
                } for r in records if hasattr(r, 'timestamp') and hasattr(r, 'cost')
            ])
            
            if not df.empty:
                daily = df.groupby('date').agg({'cost':'sum','tokens':'sum'}).reset_index()
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                fig.add_trace(
                    go.Scatter(
                        x=daily['date'], 
                        y=daily['cost'], 
                        name='每日成本(¥)', 
                        line=dict(color='#FF6B6B', width=3)
                    ), 
                    secondary_y=False
                )
                fig.add_trace(
                    go.Scatter(
                        x=daily['date'], 
                        y=daily['tokens'], 
                        name='每日Token数', 
                        line=dict(color='#4ECDC4', width=3)
                    ), 
                    secondary_y=True
                )
                
                fig.update_xaxes(title_text="日期")
                fig.update_yaxes(title_text="成本(¥)", secondary_y=False)
                fig.update_yaxes(title_text="Token数量", secondary_y=True)
                fig.update_layout(title_text="成本与Token使用趋势")
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暂无趋势数据")
        
        # 5) 明细表 + 分页
        if records:
            _render_token_usage_table(records)
        
        # 6) 供应商详细统计
        if provider_stats:
            _render_provider_detailed_stats(provider_stats)
        
    except Exception as e:
        st.error(f"❌ 获取Token统计失败: {e}")
        logger.error(f"Token统计获取失败: {e}", exc_info=True)


def _load_usage_records_filtered(days: int) -> List[UsageRecord]:
    """加载过滤后的使用记录"""
    try:
        all_records = config_manager.load_usage_records()
        cutoff = datetime.now() - timedelta(days=days)
        filtered_records = []
        
        for record in all_records:
            try:
                if hasattr(record, 'timestamp'):
                    record_time = datetime.fromisoformat(record.timestamp)
                    if record_time >= cutoff:
                        filtered_records.append(record)
            except Exception:
                # 忽略时间解析失败的记录
                continue
        
        return filtered_records
        
    except Exception as e:
        st.error(f"加载Token使用记录失败: {e}")
        return []


def _render_token_usage_table(records: List[UsageRecord]):
    """渲染Token使用明细表"""
    
    st.markdown("#### 📋 详细使用记录")
    
    # 分页设置
    items_per_page = st.selectbox(
        "每页显示记录数",
        [10, 20, 50, 100],
        index=1,
        key="token_table_items_per_page"
    )
    
    total_records = len(records)
    total_pages = (total_records + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        current_page = st.selectbox(
            f"页面 (共{total_pages}页)",
            range(1, total_pages + 1),
            key="token_table_current_page"
        )
    else:
        current_page = 1
    
    # 获取当前页数据
    start_idx = (current_page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_records = records[start_idx:end_idx]
    
    if page_records:
        # 转换为表格数据
        table_data = []
        for record in page_records:
            try:
                timestamp = datetime.fromisoformat(record.timestamp)
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = record.timestamp if hasattr(record, 'timestamp') else '未知'
            
            table_data.append({
                "时间": formatted_time,
                "提供商": getattr(record, 'provider', '未知'),
                "模型": getattr(record, 'model_name', '未知'),
                "输入Token": getattr(record, 'input_tokens', 0),
                "输出Token": getattr(record, 'output_tokens', 0),
                "总Token": getattr(record, 'input_tokens', 0) + getattr(record, 'output_tokens', 0),
                "成本(¥)": f"{getattr(record, 'cost', 0):.4f}",
                "分析类型": getattr(record, 'analysis_type', '未知'),
                "会话ID": getattr(record, 'session_id', '未知')[:16] + "..." if len(getattr(record, 'session_id', '')) > 16 else getattr(record, 'session_id', '未知')
            })
        
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        st.markdown(f"**显示 {start_idx + 1}-{min(end_idx, total_records)} 条，共 {total_records} 条记录**")
    else:
        st.info("当前页面暂无记录")


def _render_provider_detailed_stats(provider_stats: Dict):
    """渲染供应商详细统计"""
    
    st.markdown("#### 🏢 供应商详细统计")
    
    for provider, stats in provider_stats.items():
        with st.expander(f"📊 {provider} 详细统计", expanded=False):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("总成本", f"¥{stats.get('cost', 0):.4f}")
            
            with col2:
                st.metric("调用次数", f"{stats.get('requests', 0):,}")
            
            with col3:
                total_tokens = stats.get('input_tokens', 0) + stats.get('output_tokens', 0)
                st.metric("总Token", f"{total_tokens:,}")
            
            with col4:
                avg_cost = stats.get('cost', 0) / stats.get('requests', 1)
                st.metric("平均成本", f"¥{avg_cost:.4f}")
            
            # 模型分布
            models = stats.get('models', {})
            if models:
                st.markdown("**模型使用分布**")
                model_data = []
                for model, count in models.items():
                    model_data.append({"模型": model, "使用次数": count})
                
                model_df = pd.DataFrame(model_data)
                st.dataframe(model_df, use_container_width=True, hide_index=True)


def _export_token_statistics_data(days: int):
    """导出Token统计数据"""
    try:
        stats = config_manager.get_usage_statistics(days)
        records = _load_usage_records_filtered(days)
        
        export_data = {
            "export_info": {
                "export_time": datetime.now().isoformat(),
                "time_range_days": days,
                "total_records": len(records)
            },
            "summary_statistics": stats,
            "detailed_records": [
                {
                    "timestamp": getattr(r, 'timestamp', ''),
                    "provider": getattr(r, 'provider', ''),
                    "model_name": getattr(r, 'model_name', ''),
                    "input_tokens": getattr(r, 'input_tokens', 0),
                    "output_tokens": getattr(r, 'output_tokens', 0),
                    "cost": getattr(r, 'cost', 0),
                    "analysis_type": getattr(r, 'analysis_type', ''),
                    "session_id": getattr(r, 'session_id', '')
                } for r in records
            ]
        }
        
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="📥 下载Token统计数据 (JSON)",
            data=json_str,
            file_name=f"token_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            key="download_token_stats"
        )
        
        st.success(f"✅ 准备导出 {len(records)} 条Token使用记录")
        
    except Exception as e:
        st.error(f"❌ 导出Token统计数据失败: {e}")


# 保持原有的其他函数不变...


def _show_analysis_detail(history_service: HistoryService, analysis_id: str):
    """显示分析详情"""
    
    detail_data = history_service.get_analysis_detail(analysis_id)
    if not detail_data:
        st.error("❌ 无法获取分析详情")
        return
    
    with st.expander(f"📄 分析详情: {analysis_id}", expanded=True):
        # 基础信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**分析ID**: `{analysis_id}`")
            st.write(f"**状态**: {detail_data.get('status', '未知')}")
            st.write(f"**股票代码**: {detail_data.get('results', {}).get('analysis_data', {}).get('stock_symbol', '未知')}")
            st.write(f"**市场类型**: {detail_data.get('results', {}).get('analysis_data', {}).get('market_type', '未知')}")
        
        with col2:
            st.write(f"**研究深度**: {detail_data.get('results', {}).get('analysis_data', {}).get('research_depth', '未知')}")
            st.write(f"**协作模式**: {detail_data.get('results', {}).get('collaboration_mode', '未知')}")
            st.write(f"**使用的智能体**: {', '.join(detail_data.get('results', {}).get('agents_used', []))}")
        
        # 分析结果摘要
        results = detail_data.get('results', {}).get('results', {})
        if results:
            st.markdown("#### 分析结果摘要")
            for agent_name, agent_result in results.items():
                if isinstance(agent_result, dict):
                    with st.expander(f"🤖 {agent_name.replace('_', ' ').title()}", expanded=False):
                        
                        # 显示基本信息
                        if 'confidence' in agent_result:
                            st.write(f"**置信度**: {agent_result['confidence']:.0%}")
                        
                        if 'execution_time' in agent_result:
                            exec_time = agent_result['execution_time'] / 1000  # 转换为秒
                            st.write(f"**执行时间**: {exec_time:.1f}秒")
                        
                        if 'model_used' in agent_result:
                            st.write(f"**使用模型**: {agent_result['model_used']}")
                        
                        # 显示分析内容（截断显示）
                        analysis = agent_result.get('analysis', '')
                        if analysis:
                            if len(analysis) > 500:
                                st.markdown(f"**分析内容**: {analysis[:500]}...")
                                if st.button(f"显示完整内容 - {agent_name}", key=f"show_full_{agent_name}"):
                                    st.markdown(analysis)
                            else:
                                st.markdown(f"**分析内容**: {analysis}")
        
        # 原始数据下载
        st.markdown("#### 原始数据")
        json_str = json.dumps(detail_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 下载完整数据 (JSON)",
            data=json_str,
            file_name=f"analysis_{analysis_id}.json",
            mime="application/json"
        )


def _display_search_results(results: List[Dict]):
    """显示搜索结果"""
    
    # 转换为表格格式
    table_data = []
    for record in results:
        try:
            timestamp = datetime.fromisoformat(record.get('timestamp', '').replace('Z', ''))
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
        except:
            formatted_time = record.get('timestamp', '未知')
        
        table_data.append({
            "时间": formatted_time,
            "股票代码": record.get('stock_symbol', '未知'),
            "市场": record.get('market_type', '未知'),
            "模式": record.get('analysis_mode', '未知'),
            "建议": record.get('action', '-'),
            "置信度": f"{record.get('confidence', 0):.0%}" if record.get('confidence') else '-'
        })
    
    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _export_records_json(records: List[Dict]):
    """导出记录为JSON格式"""
    try:
        json_data = json.dumps(records, ensure_ascii=False, indent=2)
        
        st.download_button(
            label="📥 下载 JSON 文件",
            data=json_data,
            file_name=f"analysis_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
        
        st.success(f"✅ 准备导出 {len(records)} 条记录")
        
    except Exception as e:
        st.error(f"❌ 导出JSON失败: {e}")


def _export_records_markdown(records: List[Dict]):
    """导出记录为Markdown格式"""
    try:
        md_content = "# 个股分析历史记录\n\n"
        md_content += f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        md_content += f"记录数量: {len(records)}\n\n"
        
        for i, record in enumerate(records, 1):
            md_content += f"## {i}. {record.get('stock_symbol', '未知')} - {record.get('analysis_id', '')}\n\n"
            
            try:
                timestamp = datetime.fromisoformat(record.get('timestamp', '').replace('Z', ''))
                formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except:
                formatted_time = record.get('timestamp', '未知')
            
            md_content += f"- **分析时间**: {formatted_time}\n"
            md_content += f"- **股票代码**: {record.get('stock_symbol', '未知')}\n"
            md_content += f"- **市场类型**: {record.get('market_type', '未知')}\n"
            md_content += f"- **分析模式**: {record.get('analysis_mode', '未知')}\n"
            md_content += f"- **研究深度**: L{record.get('research_depth', 0)}\n"
            md_content += f"- **投资建议**: {record.get('action', '未知')}\n"
            md_content += f"- **置信度**: {record.get('confidence', 0):.0%}\n" if record.get('confidence') else "- **置信度**: 未知\n"
            md_content += f"- **状态**: {record.get('status', '未知')}\n\n"
        
        st.download_button(
            label="📥 下载 Markdown 文件",
            data=md_content,
            file_name=f"analysis_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown"
        )
        
        st.success(f"✅ 准备导出 {len(records)} 条记录")
        
    except Exception as e:
        st.error(f"❌ 导出Markdown失败: {e}")


def _confirm_delete_records(history_service: HistoryService, records: List[Dict]):
    """确认删除记录"""
    
    with st.expander(f"⚠️ 确认删除 {len(records)} 条记录？", expanded=True):
        st.warning("此操作将永久删除选中的分析记录，无法恢复！")
        
        # 显示要删除的记录
        for record in records:
            st.write(f"• {record.get('stock_symbol', '未知')} - {record['analysis_id']}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ 确认删除", type="primary", key="confirm_delete"):
                deleted_count = 0
                for record in records:
                    if history_service.delete_analysis(record['analysis_id']):
                        deleted_count += 1
                
                if deleted_count > 0:
                    st.success(f"✅ 成功删除 {deleted_count} 条记录")
                    st.rerun()
                else:
                    st.error("❌ 删除失败")
        
        with col2:
            if st.button("❌ 取消", key="cancel_delete"):
                st.info("已取消删除操作")
