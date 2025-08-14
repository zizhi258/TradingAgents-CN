"""
Market-Wide Analysis Page
全球市场分析页面 - 基于TradingAgents-CN框架的市场分析功能
"""

import streamlit as st
import datetime
import time
import json
import os
import uuid
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('market_wide_analysis')

# 导入组件和工具
from components.model_selection_panel import render_model_selection_panel
from components.header import render_header
from components.market_analysis_components import MarketConfigurationPanel, MarketProgressDisplay, MarketResultsDisplay
from components.market_results_display import AdvancedStockRankingsDisplay, SectorHeatmapDisplay, MarketBreadthGauge
from utils.market_session_manager import get_market_session_manager, init_market_session_state
from utils.market_export_utils import render_export_interface

def render_market_wide_analysis():
    """渲染全球市场分析页面 - 使用增强版本"""
    
    try:
        # 尝试使用增强版本
        from modules.enhanced_market_wide_analysis import render_enhanced_market_wide_analysis
        render_enhanced_market_wide_analysis()
        logger.info("使用增强版全球市场分析界面")
        
    except ImportError as e:
        logger.warning(f"增强版界面导入失败，使用标准版本: {e}")
        # 回退到标准版本
        render_standard_market_analysis()


def render_standard_market_analysis():
    """渲染标准版全球市场分析页面"""
    
    # 页面标题
    st.header("🌍 全球市场分析")
    st.caption("智能市场分析 | 股票排名 | 板块分析 | 市场指标")
    
    # 初始化会话状态和管理器
    init_market_session_state()
    session_manager = get_market_session_manager()
    
    # 创建标签页布局
    tab_config, tab_progress, tab_results = st.tabs(["⚙️ 配置", "📊 进度", "📋 结果"])
    
    with tab_config:
        render_configuration_tab(session_manager)
    
    with tab_progress:
        render_progress_tab(session_manager)
    
    with tab_results:
        render_results_tab(session_manager)


def render_configuration_tab(session_manager):
    """渲染配置标签页"""
    
    # 使用配置组件
    config_panel = MarketConfigurationPanel()
    # 先渲染业务层配置（市场/范围/深度等）
    config_data = config_panel.render("main_config")

    # 方法层：分析模式 + 模型与路由配置
    st.markdown("---")
    st.markdown("### 🧠 方法层配置（单/多模型 与 路由）")
    method_col1, method_col2 = st.columns([1, 2])
    with method_col1:
        analysis_mode_label = st.radio(
            "分析模式",
            options=["单模型", "多模型"],
            horizontal=True,
            key="market_analysis_mode"
        )
        analysis_mode = "single" if analysis_mode_label == "单模型" else "multi"
    with method_col2:
        st.caption("单模型：同一模型串联产出研报；多模型：按角色分配模型，可并行/辩论协作")

    # 供应商与模型选择、路由与回退等（与个股一致）
    model_cfg = render_model_selection_panel(location="market")

    # 组装方法层配置
    ai_model_config = {
        'analysis_mode': analysis_mode,
        'llm_provider': model_cfg.get('llm_provider'),
        'llm_model': model_cfg.get('llm_model'),
        'llm_quick_model': model_cfg.get('llm_quick_model'),
        'llm_deep_model': model_cfg.get('llm_deep_model'),
        'routing_strategy': model_cfg.get('routing_strategy'),
        'fallback_candidates': model_cfg.get('fallbacks'),
        'max_budget': model_cfg.get('max_budget'),
        # per-role 策略从 session_state 读取（由面板写入）
        'allowed_models_by_role': st.session_state.get('allowed_models_by_role', {}),
        'model_overrides': st.session_state.get('model_overrides', {}),
    }

    # 写回到 config_data，供会话管理器与后端透传
    config_data['ai_model_config'] = ai_model_config
    
    # 处理配置提交
    if config_data.get('submitted', False):
        try:
            # 创建分析会话
            scan_id = session_manager.create_scan_session(config_data)
            
            # 更新Streamlit会话状态
            st.session_state.current_market_scan_id = scan_id
            st.session_state.market_scan_running = True
            st.session_state.market_scan_results = None
            
            st.success(f"🚀 全球市场分析已启动！分析ID: {scan_id}")
            st.info("➡️ 请切换到 '📊 进度' 标签页查看分析进度")
            
            # 自动切换到进度标签页
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 启动分析失败: {e}")
            logger.error(f"启动市场分析失败: {e}")
    
    elif config_data.get('estimate_requested', False):
        # 成本预估
        estimated_cost = calculate_scan_cost(config_data)
        st.info(f"💰 预估成本: ¥{estimated_cost:.2f}")
        st.caption(f"基于{config_data.get('stock_limit', 100)}只股票，{config_data.get('scan_depth', 3)}级深度分析")
    
    elif config_data.get('save_requested', False):
        # 保存配置
        st.session_state.market_config = config_data
        st.success("✅ 配置已保存")
    
    # 显示分析历史
    render_scan_history(session_manager)


def render_progress_tab(session_manager):
    """渲染进度标签页"""
    
    current_scan_id = st.session_state.get('current_market_scan_id')
    
    if not current_scan_id:
        st.info("📝 尚未开始分析。请在 '⚙️ 配置' 标签页启动分析。")
        return
    
    # 使用进度显示组件
    progress_display = MarketProgressDisplay()
    
    # 获取进度数据
    progress_data = session_manager.get_session_progress(current_scan_id)

    if not progress_data:
        st.error("❌ 无法获取分析进度数据")
        return

    if progress_data.get('status') == 'not_found':
        st.warning("⚠️ 当前分析已不存在或已过期，请重新发起分析。")
        st.session_state.market_scan_running = False
        st.session_state.current_market_scan_id = None
        return

    # 渲染进度显示
    is_completed = progress_display.render(current_scan_id, progress_data)
    
    # 更新Streamlit状态
    if is_completed and progress_data:
        if progress_data.get('status') == 'completed':
            st.session_state.market_scan_running = False
            
            # 获取完整结果
            if not st.session_state.market_scan_results:
                results = session_manager.get_session_results(current_scan_id)
                if results:
                    st.session_state.market_scan_results = results
                    st.success("✅ 分析完成，结果已就绪！")
                    st.info("👉 请切换到 '📋 结果' 标签页查看详细分析结果")
        
        elif progress_data.get('status') in ['failed', 'cancelled', 'not_found']:
            st.session_state.market_scan_running = False
            st.session_state.current_market_scan_id = None
    
    # 自动刷新逻辑
    if st.session_state.market_scan_running and progress_data:
        auto_refresh = st.session_state.get('auto_refresh_enabled', True)
        if auto_refresh:
            time.sleep(3)
            st.rerun()


def render_results_tab(session_manager):
    """渲染结果标签页"""
    
    current_scan_id = st.session_state.get('current_market_scan_id')
    results_data = st.session_state.get('market_scan_results')
    
    if not current_scan_id or not results_data:
        st.info("📊 暂无分析结果。请先在 '⚙️ 配置' 标签页启动分析，并等待完成。")
        return
    
    # 使用结果显示组件
    results_display = MarketResultsDisplay()
    results_display.render(current_scan_id, results_data)
    
    # 高级可视化组件
    st.markdown("---")
    st.markdown("## 🎨 高级可视化分析")
    
    viz_tabs = st.tabs(["📊 股票深度分析", "🔥 板块热力图", "📈 市场仪表盘"])
    
    with viz_tabs[0]:
        if 'rankings' in results_data:
            advanced_rankings = AdvancedStockRankingsDisplay()
            advanced_rankings.render(results_data['rankings'], "advanced")
    
    with viz_tabs[1]:
        if 'sectors' in results_data:
            sector_heatmap = SectorHeatmapDisplay()
            sector_heatmap.render(results_data['sectors'], "advanced")
    
    with viz_tabs[2]:
        if 'breadth' in results_data:
            breadth_gauge = MarketBreadthGauge()
            breadth_gauge.render(results_data['breadth'])
    
    # 导出功能
    st.markdown("---")
    render_export_interface(current_scan_id, results_data)


def render_scan_history(session_manager):
    """渲染分析历史"""
    
    with st.expander("📚 分析历史", expanded=False):
        
        try:
            history = session_manager.get_session_history(limit=20)
            
            if not history:
                st.info("暂无分析历史记录")
                return
            
            st.markdown("### 📜 最近分析记录")
            
            for i, session_data in enumerate(history):
                scan_id = session_data.get('scan_id', '')
                created_at = session_data.get('created_at', '')
                status = session_data.get('status', 'unknown')
                config = session_data.get('config', {})
                
                # 状态图标
                status_icon = {
                    'completed': '✅',
                    'running': '🔄',
                    'failed': '❌',
                    'cancelled': '⏹️'
                }.get(status, '❓')
                
                # 显示记录
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"{status_icon} **{scan_id}**")
                    st.caption(f"{config.get('market_type', '')} | {config.get('preset_type', '')} | {config.get('stock_limit', 0)}只股票")
                
                with col2:
                    try:
                        created_time = datetime.datetime.fromisoformat(created_at)
                        st.write(created_time.strftime('%m-%d %H:%M'))
                    except:
                        st.write(created_at)
                    st.caption(f"状态: {status}")
                
                with col3:
                    if st.button(f"查看", key=f"view_history_{i}"):
                        st.session_state.current_market_scan_id = scan_id
                        # 尝试获取结果
                        results = session_manager.get_session_results(scan_id)
                        if results:
                            st.session_state.market_scan_results = results
                            st.session_state.market_scan_running = False
                            st.success(f"已加载分析结果: {scan_id}")
                            st.rerun()
                        else:
                            st.warning(f"无法加载分析结果: {scan_id}")
                
                if i < len(history) - 1:
                    st.markdown("---")
        
        except Exception as e:
            st.error(f"获取分析历史失败: {e}")
            logger.error(f"获取分析历史失败: {e}")


def calculate_scan_cost(config_data):
    """计算分析成本预估"""
    
    # 基础成本参数
    base_cost_per_stock = {
        1: 0.01,  # 1级 - 基础筛选
        2: 0.02,  # 2级 - 技术分析
        3: 0.05,  # 3级 - 综合分析
        4: 0.08,  # 4级 - 深度研究
        5: 0.12   # 5级 - 全面调研
    }
    
    # 市场系数
    market_factor = {
        'A股': 1.0,
        '美股': 1.2,
        '港股': 1.1
    }
    
    # 分析重点系数
    focus_multiplier = 1.0
    analysis_focus = config_data.get('analysis_focus', {})
    enabled_focus_count = sum(1 for enabled in analysis_focus.values() if enabled)
    focus_multiplier = 0.8 + (enabled_focus_count * 0.1)  # 基础0.8，每个重点+0.1
    
    # 计算总成本
    stock_limit = config_data.get('stock_limit', 100)
    scan_depth = config_data.get('scan_depth', 3)
    market_type = config_data.get('market_type', 'A股')
    
    base_cost = stock_limit * base_cost_per_stock.get(scan_depth, 0.05)
    market_adjusted_cost = base_cost * market_factor.get(market_type, 1.0)
    final_cost = market_adjusted_cost * focus_multiplier
    
    return final_cost


# 主入口
if __name__ == "__main__":
    render_market_wide_analysis()
