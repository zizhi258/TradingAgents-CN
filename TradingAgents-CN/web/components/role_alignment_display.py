"""
Role Alignment Display Component
角色对齐显示组件 - 展示统一的7+2智能体架构
"""

import streamlit as st
import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

from tradingagents.utils.logging_init import get_logger

logger = get_logger("role_alignment_display")


def render_role_alignment_dashboard() -> None:
    """渲染角色对齐仪表盘"""
    
    st.markdown("## 🎯 智能体角色对齐")
    st.markdown("---")
    
    # 加载角色配置
    roles_config = load_agent_roles_config()
    
    if not roles_config:
        st.error("❌ 无法加载智能体角色配置")
        return
    
    # 创建主要布局
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 角色架构可视化
        render_agent_architecture_chart(roles_config)
        
        # 角色详细信息表
        render_roles_details_table(roles_config)
    
    with col2:
        # 系统状态监控
        render_system_status_panel()
        
        # ChartingArtist状态
        render_charting_artist_status()


def render_agent_architecture_chart(roles_config: Dict[str, Any]) -> None:
    """渲染智能体架构图表"""
    
    st.markdown("### 🏗️ 智能体协作架构")
    
    # 获取协作层级
    collaboration = roles_config.get('collaboration_patterns', {})
    information_flow = collaboration.get('information_flow', {})
    
    if not information_flow:
        st.warning("协作模式配置缺失")
        return
    
    # 创建桑基图显示信息流
    create_agent_flow_diagram(information_flow, roles_config.get('agents', {}))
    
    # 角色分层展示
    render_tier_visualization(information_flow, roles_config.get('agents', {}))


def create_agent_flow_diagram(flow_config: Dict[str, Any], agents_config: Dict[str, Any]) -> None:
    """创建智能体信息流图"""
    
    try:
        # 准备数据用于网络图
        nodes = []
        edges = []
        
        # 定义层级颜色
        tier_colors = {
            'tier_1': '#FF6B6B',  # 红色 - 信息收集
            'tier_2': '#4ECDC4',  # 青色 - 专业分析
            'tier_3': '#45B7D1',  # 蓝色 - 风控合规
            'tier_4': '#96CEB4',  # 绿色 - 决策写作
            'tier_5': '#FFEAA7'   # 黄色 - 可视化
        }
        
        tier_names = {
            'tier_1': '信息收集层',
            'tier_2': '专业分析层', 
            'tier_3': '风控合规层',
            'tier_4': '决策输出层',
            'tier_5': '可视化层'
        }
        
        # 收集所有节点
        all_agents = set()
        for tier, agent_list in flow_config.items():
            if isinstance(agent_list, list):
                all_agents.update(agent_list)
        
        # 创建节点数据
        for tier, agent_list in flow_config.items():
            if isinstance(agent_list, list):
                for agent in agent_list:
                    if agent in agents_config:
                        agent_info = agents_config[agent]
                        nodes.append({
                            'id': agent,
                            'name': agent_info.get('name', agent),
                            'tier': tier,
                            'color': tier_colors.get(tier, '#95A5A6'),
                            'description': agent_info.get('description', ''),
                            'role_type': agent_info.get('role_type', ''),
                            'is_optional': agent_info.get('is_optional', False)
                        })
        
        # 创建可视化图表
        fig = go.Figure()
        
        # 按层级绘制节点
        tier_positions = {
            'tier_1': {'y': 4, 'x_start': 0},
            'tier_2': {'y': 3, 'x_start': 0},
            'tier_3': {'y': 2, 'x_start': 0},
            'tier_4': {'y': 1, 'x_start': 0},
            'tier_5': {'y': 0, 'x_start': 0}
        }
        
        for tier, position in tier_positions.items():
            tier_agents = [node for node in nodes if node['tier'] == tier]
            if not tier_agents:
                continue
                
            x_positions = []
            y_positions = []
            colors = []
            text_labels = []
            hover_texts = []
            
            # 计算X轴位置
            for i, agent in enumerate(tier_agents):
                x_pos = i * 2 - (len(tier_agents) - 1)
                x_positions.append(x_pos)
                y_positions.append(position['y'])
                
                # 设置颜色
                color = agent['color']
                if agent['is_optional']:
                    color = '#FFA500'  # 可选角色用橙色
                colors.append(color)
                
                # 设置标签
                label = agent['name']
                if agent['is_optional']:
                    label += " (可选)"
                text_labels.append(label)
                
                # 设置悬停信息
                hover_text = f"<b>{agent['name']}</b><br>" + \
                            f"角色类型: {agent['role_type']}<br>" + \
                            f"描述: {agent['description'][:100]}..."
                hover_texts.append(hover_text)
            
            # 添加散点图
            fig.add_trace(go.Scatter(
                x=x_positions,
                y=y_positions,
                mode='markers+text',
                marker=dict(
                    size=25,
                    color=colors,
                    line=dict(width=2, color='white')
                ),
                text=text_labels,
                textposition='bottom center',
                textfont=dict(size=10),
                name=tier_names.get(tier, tier),
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=hover_texts
            ))
        
        # 添加连接线
        for i in range(len(tier_positions) - 1):
            current_tier = f'tier_{i+1}'
            next_tier = f'tier_{i+2}'
            
            current_agents = [node for node in nodes if node['tier'] == current_tier]
            next_agents = [node for node in nodes if node['tier'] == next_tier]
            
            if current_agents and next_agents:
                # 添加层级间的连接线
                for curr_agent in current_agents:
                    curr_idx = [n['id'] for n in nodes if n['tier'] == current_tier].index(curr_agent['id'])
                    curr_x = curr_idx * 2 - (len(current_agents) - 1)
                    
                    for next_agent in next_agents:
                        next_idx = [n['id'] for n in nodes if n['tier'] == next_tier].index(next_agent['id'])
                        next_x = next_idx * 2 - (len(next_agents) - 1)
                        
                        fig.add_trace(go.Scatter(
                            x=[curr_x, next_x],
                            y=[tier_positions[current_tier]['y'], tier_positions[next_tier]['y']],
                            mode='lines',
                            line=dict(color='rgba(100,100,100,0.3)', width=1),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
        
        # 更新布局
        fig.update_layout(
            title="智能体协作架构图",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        logger.error(f"创建智能体流程图失败: {e}")
        st.error("架构图生成失败")


def render_tier_visualization(flow_config: Dict[str, Any], agents_config: Dict[str, Any]) -> None:
    """渲染分层可视化"""
    
    st.markdown("### 📊 智能体分层统计")
    
    # 统计各层级的智能体数量
    tier_stats = {}
    tier_names = {
        'tier_1': '信息收集层',
        'tier_2': '专业分析层',
        'tier_3': '风控合规层', 
        'tier_4': '决策输出层',
        'tier_5': '可视化层'
    }
    
    for tier, agent_list in flow_config.items():
        if isinstance(agent_list, list):
            tier_stats[tier_names.get(tier, tier)] = len(agent_list)
    
    # 创建柱状图
    fig = go.Figure(data=[
        go.Bar(
            x=list(tier_stats.keys()),
            y=list(tier_stats.values()),
            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'][:len(tier_stats)]
        )
    ])
    
    fig.update_layout(
        title="各层级智能体数量分布",
        xaxis_title="层级",
        yaxis_title="智能体数量",
        height=300
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_roles_details_table(roles_config: Dict[str, Any]) -> None:
    """渲染角色详细信息表"""
    
    st.markdown("### 📋 智能体详细信息")
    
    agents = roles_config.get('agents', {})
    
    if not agents:
        st.warning("未找到智能体配置")
        return
    
    # 准备表格数据
    table_data = []
    
    for agent_id, agent_info in agents.items():
        # 检查是否为ChartingArtist
        is_charting_artist = agent_id == 'charting_artist'
        is_enabled = not agent_info.get('is_optional', False) or (
            is_charting_artist and is_charting_artist_enabled()
        )
        
        table_data.append({
            '智能体': agent_info.get('name', agent_id),
            '英文名': agent_info.get('name_en', ''),
            '角色类型': agent_info.get('role_type', '').replace('_', ' ').title(),
            '优先级': agent_info.get('priority', '').title(),
            '描述': agent_info.get('description', '')[:80] + '...' if len(agent_info.get('description', '')) > 80 else agent_info.get('description', ''),
            '状态': '✅ 启用' if is_enabled else ('🟡 可选' if agent_info.get('is_optional', False) else '❌ 禁用'),
            '成本限制': f"${agent_info.get('performance', {}).get('cost_limit', 0):.2f}"
        })
    
    # 显示表格
    if table_data:
        import pandas as pd
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.warning("未找到智能体数据")


def render_system_status_panel() -> None:
    """渲染系统状态面板"""
    
    st.markdown("### 📊 系统状态")
    
    # 检查各个组件的状态
    status_data = get_system_status()
    
    # 整体状态指标
    col1, col2 = st.columns(2)
    
    with col1:
        # 可用智能体数量
        available_agents = len([s for s in status_data if s['status'] == '正常'])
        total_agents = len(status_data)
        
        st.metric(
            label="可用智能体",
            value=f"{available_agents}/{total_agents}",
            delta=f"{(available_agents/total_agents)*100:.0f}%"
        )
    
    with col2:
        # 系统健康度
        health_score = (available_agents / total_agents) * 100 if total_agents > 0 else 0
        health_status = "优秀" if health_score >= 90 else ("良好" if health_score >= 75 else "需要关注")
        
        st.metric(
            label="系统健康度", 
            value=f"{health_score:.0f}%",
            delta=health_status
        )
    
    # 详细状态列表
    st.markdown("**组件状态详情:**")
    for item in status_data:
        status_icon = "✅" if item['status'] == '正常' else ("⚠️" if item['status'] == '警告' else "❌")
        st.markdown(f"**{status_icon} {item['component']}**: {item['message']}")


def render_charting_artist_status() -> None:
    """渲染ChartingArtist状态"""
    
    st.markdown("### 🎨 ChartingArtist状态")
    
    is_enabled = is_charting_artist_enabled()
    
    if is_enabled:
        st.success("✅ 绘图师已启用")
        
        # 显示图表统计
        charts_dir = Path("data/attachments/charts")
        if charts_dir.exists():
            chart_count = len(list(charts_dir.glob("*.html"))) + len(list(charts_dir.glob("*.json")))
            st.metric("生成图表数", chart_count)
            
            if chart_count > 0:
                # 最近生成时间
                chart_files = list(charts_dir.glob("*"))
                if chart_files:
                    latest_file = max(chart_files, key=lambda x: x.stat().st_mtime)
                    import datetime
                    latest_time = datetime.datetime.fromtimestamp(latest_file.stat().st_mtime)
                    st.caption(f"最近生成: {latest_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 支持的图表类型
        with st.expander("支持的图表类型"):
            chart_types = [
                "📈 K线图 (Candlestick)",
                "📊 柱状图 (Bar Chart)", 
                "🥧 饼图 (Pie Chart)",
                "📉 折线图 (Line Chart)",
                "🎯 散点图 (Scatter Plot)",
                "🔥 热力图 (Heatmap)",
                "🕸️ 雷达图 (Radar Chart)",
                "📏 仪表盘 (Gauge Chart)",
                "🌊 瀑布图 (Waterfall)",
                "📦 箱线图 (Box Plot)"
            ]
            
            for chart_type in chart_types:
                st.markdown(f"• {chart_type}")
    else:
        st.warning("⚠️ 绘图师未启用")
        st.caption("设置环境变量 CHARTING_ARTIST_ENABLED=true 以启用")
        
        if st.button("🔧 启用绘图师"):
            st.info("请在系统设置中配置环境变量")


def get_system_status() -> List[Dict[str, str]]:
    """获取系统各组件状态"""
    
    status_list = []
    
    # 检查基本组件
    status_list.append({
        'component': 'Web界面',
        'status': '正常',
        'message': 'Streamlit服务运行正常'
    })
    
    # 检查数据目录
    data_dir = Path("data")
    if data_dir.exists():
        status_list.append({
            'component': '数据目录',
            'status': '正常',
            'message': '数据目录可访问'
        })
    else:
        status_list.append({
            'component': '数据目录',
            'status': '异常',
            'message': '数据目录不存在'
        })
    
    # 检查配置文件
    config_file = Path("config/agent_roles.yaml")
    if config_file.exists():
        status_list.append({
            'component': '智能体配置',
            'status': '正常',
            'message': '角色配置文件存在'
        })
    else:
        status_list.append({
            'component': '智能体配置',
            'status': '警告',
            'message': '角色配置文件缺失'
        })
    
    # 检查ChartingArtist
    if is_charting_artist_enabled():
        status_list.append({
            'component': 'ChartingArtist',
            'status': '正常',
            'message': '绘图师功能已启用'
        })
    else:
        status_list.append({
            'component': 'ChartingArtist',
            'status': '警告',
            'message': '绘图师功能未启用'
        })
    
    # 检查API配置
    api_keys = ['GOOGLE_API_KEY', 'FINNHUB_API_KEY', 'DEEPSEEK_API_KEY']
    configured_apis = sum(1 for key in api_keys if os.getenv(key))
    
    if configured_apis >= len(api_keys) // 2:
        status_list.append({
            'component': 'API配置',
            'status': '正常',
            'message': f'已配置 {configured_apis}/{len(api_keys)} 个API'
        })
    else:
        status_list.append({
            'component': 'API配置',
            'status': '警告',
            'message': f'仅配置 {configured_apis}/{len(api_keys)} 个API'
        })
    
    return status_list


def load_agent_roles_config() -> Optional[Dict[str, Any]]:
    """加载智能体角色配置"""
    
    config_path = Path("config/agent_roles.yaml")
    
    try:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.warning("智能体角色配置文件不存在")
            return None
            
    except Exception as e:
        logger.error(f"加载智能体角色配置失败: {e}")
        return None


def is_charting_artist_enabled() -> bool:
    """检查ChartingArtist是否启用"""
    return os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() == "true"


def render_collaboration_modes() -> None:
    """渲染协作模式选择"""
    
    st.markdown("### 🤝 协作模式")
    
    modes = {
        'sequential': {
            'name': '顺序协作',
            'description': '智能体按层级依次执行分析',
            'icon': '🔄',
            'pros': ['逻辑清晰', '易于调试', '结果可控'],
            'cons': ['耗时较长', '并行度低']
        },
        'parallel': {
            'name': '并行协作', 
            'description': '同层智能体并行执行，提高效率',
            'icon': '⚡',
            'pros': ['执行快速', '资源利用率高', '响应迅速'],
            'cons': ['复杂度高', '需要同步机制']
        },
        'debate': {
            'name': '辩论协作',
            'description': '核心智能体通过辩论达成一致',
            'icon': '🗣️',
            'pros': ['观点全面', '决策质量高', '避免偏见'],
            'cons': ['耗时最长', '成本较高']
        }
    }
    
    selected_mode = st.selectbox(
        "选择协作模式",
        options=list(modes.keys()),
        format_func=lambda x: f"{modes[x]['icon']} {modes[x]['name']}"
    )
    
    if selected_mode:
        mode_info = modes[selected_mode]
        st.info(f"**{mode_info['name']}**: {mode_info['description']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**优点:**")
            for pro in mode_info['pros']:
                st.markdown(f"• {pro}")
                
        with col2:
            st.markdown("**缺点:**")
            for con in mode_info['cons']:
                st.markdown(f"• {con}")


# 导出主要功能函数
__all__ = [
    'render_role_alignment_dashboard',
    'render_agent_architecture_chart',
    'render_roles_details_table',
    'render_system_status_panel',
    'render_charting_artist_status',
    'render_collaboration_modes'
]