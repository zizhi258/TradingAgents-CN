#!/usr/bin/env python3
"""
TradingAgents-CN Streamlit Web界面
基于Streamlit的个股分析Web应用程序
"""

import streamlit as st
import os
import sys
from pathlib import Path
import datetime
import time
from dotenv import load_dotenv

# 添加项目根目录到Python路径
# 注意：这是为了兼容未通过pip install -e .安装的情况
# 推荐做法：先运行pip install -e .，然后不需要此路径注入
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('web')

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

# 导入自定义组件（Docker 兼容：若新函数缺失则回退）
import importlib
_hdr = importlib.import_module("components.header")
render_header = getattr(_hdr, "render_header")
render_browser_tabs = getattr(_hdr, "render_browser_tabs", None)
from components.analysis_form import render_analysis_form
from components.results_display import render_results
from components.profile_panel import render_profile_panel
from utils.api_checker import check_api_keys
from utils.analysis_runner import run_stock_analysis, validate_analysis_params, format_analysis_results
from utils.progress_tracker import SmartStreamlitProgressDisplay, create_smart_progress_callback
from utils.plotly_theme import apply_plotly_theme
try:
    from utils.ui_utils import inject_back_to_top_button, inject_top_anchor  # 新版函数
except Exception:
    # 兼容旧镜像：提供回退实现（无JS锚点方案），避免导入失败
    def inject_top_anchor(anchor_id: str = "ta-top-anchor") -> None:
        st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)

    def inject_back_to_top_button(anchor_id: str = "ta-top-anchor") -> None:
        st.markdown(
            f"""
            <style>
            html {{ scroll-behavior: smooth; }}
            .ta-back-to-top {{position: fixed; right: 24px; bottom: 24px; z-index: 9999;}}
            .ta-back-to-top a {{
                display: inline-block;
                border-radius: 24px; padding: 10px 14px; font-weight: 600;
                background: var(--zen-surface); color: var(--zen-text);
                border: 1px solid var(--zen-border);
                box-shadow: 0 4px 12px rgba(0,0,0,.12);
                cursor: pointer; text-decoration: none;
            }}
            .ta-back-to-top a:hover {{ background: var(--zen-accent); color: #ffffff; }}
            </style>
            <div class="ta-back-to-top">
              <a href="#{anchor_id}" role="button" aria-label="回到页面顶部">⬆️ 回到顶部</a>
            </div>
            """,
            unsafe_allow_html=True,
        )
from utils.async_progress_tracker import AsyncProgressTracker
from components.async_progress_display import display_unified_progress
from utils.smart_session_manager import get_persistent_analysis_id, set_persistent_analysis_id

# 多模型协作相关导入
try:
    from components.multi_model_analysis_form import render_multi_model_analysis_form
    from components.enhanced_multi_model_analysis_form import render_enhanced_multi_model_analysis_form
    from tradingagents.core.multi_model_manager import MultiModelManager
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from utils.web_multi_model_manager import WebMultiModelCollaborationManager
    from tradingagents.core.user_friendly_error_handler import handle_user_friendly_error
    MULTI_MODEL_AVAILABLE = True
    logger.info("✅ 多模型协作组件加载成功，包含增强错误处理")
except ImportError as e:
    logger.warning(f"⚠️ [多模型协作] 导入失败，功能将被禁用: {e}")
    MULTI_MODEL_AVAILABLE = False

# 设置页面配置
st.set_page_config(
    page_title="TradingAgents-CN 个股分析平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# 注入主题CSS + 应用Plotly主题
st.markdown('<link rel="stylesheet" href="/app/static/theme.css">', unsafe_allow_html=True)
apply_plotly_theme()

# 解析URL参数（用于跳转到配置页/角色绑定页）
try:
    qp = getattr(st, 'query_params', None)
    if qp is None:
        qp = st.experimental_get_query_params()
    open_cfg = None
    open_binding = None
    if hasattr(qp, 'get'):
        open_cfg = qp.get('open_config')
        open_binding = qp.get('role_binding')
    if open_cfg is not None and not st.session_state.get('_open_config_routed'):
        v = open_cfg[0] if isinstance(open_cfg, list) else open_cfg
        if str(v).lower() in ['1', 'true', 'yes']:
            st.session_state.top_nav_page = "⚙️ 配置管理"
            st.session_state._open_config_routed = True
            st.rerun()
    if open_binding is not None and not st.session_state.get('_open_role_binding_routed'):
        v = open_binding[0] if isinstance(open_binding, list) else open_binding
        if str(v).lower() in ['1', 'true', 'yes']:
            # 兼容旧参数：跳转到合并后的“角色中心”
            st.session_state.top_nav_page = "🧭 角色中心"
            st.session_state._open_role_binding_routed = True
            st.rerun()
except Exception:
    pass

# 注入页面顶端锚点，供“回到顶部”无JS跳转
try:
    inject_top_anchor()
except Exception:
    pass

# 侧边栏：移除深色/浅色切换，统一使用默认主题（CSS :root 变量）


def _get_llm_base_config_from_state() -> dict:
    """从 session_state 和环境变量构建基础 LLM 配置（无侧边栏依赖）"""
    return {
        'llm_provider': st.session_state.get('llm_provider', os.getenv('DEFAULT_PROVIDER', 'deepseek')),
        'llm_model': st.session_state.get('llm_model', os.getenv('DEFAULT_MODEL', 'deepseek-chat')),
        'llm_quick_model': st.session_state.get('llm_quick_model', st.session_state.get('llm_model', 'deepseek-chat')),
        'llm_deep_model': st.session_state.get('llm_deep_model', st.session_state.get('llm_model', 'deepseek-chat')),
        'routing_strategy': st.session_state.get('routing_strategy_select') or os.getenv('ROUTING_STRATEGY', '均衡'),
        'fallbacks': st.session_state.get('fallback_chain', []),
        'max_budget': float(st.session_state.get('max_budget', 0.0) or 0.0)
    }

def render_multi_model_collaboration_page(config: dict | None = None):
    """渲染多模型协作分析页面

    Args:
        config: 可选，从外部传入的侧边栏配置。如果提供，将避免在此函数内部再次渲染侧边栏，
                防止重复 UI 与状态抖动。
    """
    
    st.header("🤖 多模型协作分析")
    
    # 检查多模型功能是否可用
    if not MULTI_MODEL_AVAILABLE:
        st.error("❌ 多模型协作功能不可用")
        st.info("""
        **可能的原因：**
        - 多模型协作模块未正确安装
        - 相关依赖包缺失
        - 环境变量配置不完整
        
        **解决方案：**
        1. 确保已安装所有依赖：`pip install -e .`
        2. 检查环境变量配置：设置 `MULTI_MODEL_ENABLED=true`
        3. 重启Web应用
        """)
        return
    
    # 检查环境变量配置
    multi_model_enabled = os.getenv('MULTI_MODEL_ENABLED', 'false').lower() == 'true'
    if not multi_model_enabled:
        st.warning("⚠️ 多模型协作功能未启用。此功能为可选增强模块，默认隐藏以保持界面简洁。")
        with st.expander("如何启用多模型协作？"):
            st.markdown("""
            1. 在项目根目录的 `.env` 中添加：`MULTI_MODEL_ENABLED=true`
            2. 确保已安装依赖并正确配置必要 API 密钥
            3. 重启应用后，侧边栏会出现“🤖 多模型协作”入口
            """)
        return
    
    # 获取基础配置（不再依赖侧边栏）
    if config is None:
        config = _get_llm_base_config_from_state()
    
    # 初始化多模型会话状态
    if 'multi_model_analysis_results' not in st.session_state:
        st.session_state.multi_model_analysis_results = None
    if 'multi_model_analysis_running' not in st.session_state:
        st.session_state.multi_model_analysis_running = False
    if 'multi_model_current_analysis_id' not in st.session_state:
        st.session_state.multi_model_current_analysis_id = None
    
    # 创建布局（移除右侧文档说明列，避免重复）
    col1 = st.container()

    with col1:
        # 1. 多模型分析配置区域
        st.subheader("⚙️ 分析配置")
        
        # 渲染多模型分析表单
        try:
            form_data = render_multi_model_analysis_form()
            
            if not isinstance(form_data, dict):
                st.error(f"⚠️ 表单数据格式异常: {type(form_data)}")
                form_data = {'submitted': False}
                
        except Exception as e:
            st.error(f"❌ 多模型表单渲染失败: {e}")
            form_data = {'submitted': False}
        
        # 加载持久化配置到session state
        try:
            from utils.ui_utils import load_persistent_configs_to_session
            load_persistent_configs_to_session()
        except Exception as e:
            logger.warning(f"加载持久化配置失败: {e}")

        # 处理表单提交
        if form_data.get('submitted', False) and not st.session_state.get('multi_model_analysis_running', False):
            
            # 验证必需参数
            if not form_data.get('stock_symbol') or not form_data.get('selected_agents'):
                st.error("❌ 请输入股票代码并选择至少一个智能体")
                return
            
            # 执行多模型协作分析
            st.session_state.multi_model_analysis_running = True
            st.session_state.multi_model_analysis_results = None
            
            # 生成分析ID
            import uuid
            analysis_id = f"multi_model_{uuid.uuid4().hex[:8]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.multi_model_current_analysis_id = analysis_id
            
            # 显示启动信息
            st.success(f"🚀 多模型协作分析已启动！分析ID: {analysis_id}")
            st.info(f"📊 正在分析: {form_data.get('market_type', 'A股')} {form_data['stock_symbol']}")
            st.info(f"🤖 协作模式: {form_data.get('collaboration_mode', 'sequential')}, 智能体数量: {len(form_data['selected_agents'])}")
            
            with st.spinner("🔄 正在初始化多模型协作..."):
                time.sleep(1.5)
            
            # 准备异步进度跟踪器（多模型）
            try:
                mm_tracker = AsyncProgressTracker(
                    analysis_id=analysis_id,
                    analysts=form_data.get('selected_agents') or [],
                    research_depth=form_data.get('research_depth', 3),
                    llm_provider=(config.get('llm_provider') or 'deepseek')
                )
            except Exception:
                mm_tracker = None

            # 采集UI即时策略（按角色允许/锁定）以便在后台线程使用
            ui_allowed_models_by_role = st.session_state.get('allowed_models_by_role') or {}
            ui_model_overrides = st.session_state.get('model_overrides') or {}

            # 在后台线程中运行多模型分析
            import threading
            
            def run_multi_model_analysis_in_background():
                try:
                    # 导入依赖检查器
                    from tradingagents.utils.dependency_checker import get_safe_config, check_dependencies
                    
                    # 创建初始多模型管理器配置
                    initial_config = {
                        'routing_strategy': os.getenv('ROUTING_STRATEGY', 'intelligent'),
                        'cost_optimization': form_data.get('cost_optimization', 'balanced'),
                        'enable_monitoring': form_data.get('enable_real_time_monitoring', True),
                        'max_cost_per_session': float(os.getenv('MAX_COST_PER_SESSION', '1.0')),
                        'max_concurrent_tasks': 5,
                        'enable_caching': True,
                        
                        # SiliconFlow API 配置
                        'siliconflow': {
                            'enabled': True,
                            'api_key': os.getenv('SILICONFLOW_API_KEY'),
                            'base_url': os.getenv('SILICONFLOW_BASE_URL', 'https://api.siliconflow.cn/v1'),
                            'default_model': os.getenv('SILICONFLOW_DEFAULT_MODEL', 'deepseek-v3')
                        },
                        
                        # DeepSeek官方API配置
                        'deepseek': {
                            'enabled': True,
                            'api_key': os.getenv('DEEPSEEK_API_KEY'),
                            'base_url': 'https://api.deepseek.com',
                            'default_model': 'deepseek-chat'
                        },
                        
                        # Google AI API 配置（修正键名匹配MultiModelManager期望的'google_ai'）
                        'google_ai': {
                            'enabled': True,  # 初始启用，依赖检查会自动禁用不可用的
                            'api_key': os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY') or os.getenv('GOOGLE_API_KEY'),
                            'default_model': os.getenv('GOOGLE_AI_DEFAULT_MODEL', 'gemini-2.5-pro'),
                            'timeout': 60
                        }
                    }

                    # 注入运行时策略覆写（来自UI）
                    initial_config['runtime_overrides'] = {
                        'enable_model_lock': True,
                        'enable_allowed_models_by_role': True,
                        'allowed_models_by_role': ui_allowed_models_by_role,
                        'model_overrides': ui_model_overrides,
                    }
                    
                    # 使用依赖检查器过滤配置，禁用不可用的提供商
                    config = get_safe_config(initial_config)
                    
                    # 记录可用的提供商
                    available_deps = check_dependencies('siliconflow', 'google_ai')
                    available_providers = [k for k, v in available_deps.items() if v]
                    logger.info(f"🔍 [依赖检查] 可用的API提供商: {available_providers}")
                    
                    # 添加协作配置
                    config.update({
                        'collaboration_mode': form_data.get('collaboration_mode', 'sequential'),
                        'selected_agents': form_data['selected_agents'],
                        'use_smart_routing': form_data.get('use_smart_routing', True)
                    })
                    
                    # 创建Web多模型协作管理器
                    collaboration_manager = WebMultiModelCollaborationManager(config)
                    
                    # 进度回调：桥接到统一进度跟踪器
                    def _progress_cb(evt):
                        if not mm_tracker:
                            return
                        try:
                            if isinstance(evt, dict):
                                stage = evt.get('stage') or ''
                                agent = evt.get('agent') or ''
                                # 角色中文名映射（用于进度文案）
                                try:
                                    from web.utils.ui_utils import get_role_display_name
                                    agent_disp = get_role_display_name(agent)
                                except Exception:
                                    agent_disp = agent
                                # 支持流式token预览
                                if 'delta' in evt and evt.get('delta'):
                                    delta = str(evt.get('delta'))
                                    preview = delta[-80:]  # 仅保留末尾80字符
                                    text = f"[流式]{agent_disp} {preview}"
                                else:
                                    msg = evt.get('message') or ''
                                    text = f"[多模型]{stage} {agent_disp} {msg}".strip()
                            else:
                                text = str(evt)
                            mm_tracker.update_progress(text)
                        except Exception:
                            pass

                    # 执行分析
                    results = collaboration_manager.run_collaboration_analysis(
                        stock_symbol=form_data['stock_symbol'],
                        market_type=form_data.get('market_type', 'A股'),
                        analysis_date=form_data.get('analysis_date'),
                        research_depth=form_data.get('research_depth', 3),
                        custom_requirements=form_data.get('custom_requirements', ''),
                        show_process_details=form_data.get('show_process_details', True),
                        progress_callback=_progress_cb
                    )
                    
                    # 保存分析结果（不直接修改session_state）
                    # 使用文件或数据库保存结果，稍后在主线程中读取
                    result_file = f"./data/multi_model_results_{analysis_id}.json"
                    os.makedirs(os.path.dirname(result_file), exist_ok=True)
                    
                    import json
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'analysis_id': analysis_id,
                            'status': 'completed',
                            'results': results,
                            'timestamp': datetime.datetime.now().isoformat()
                        }, f, ensure_ascii=False, indent=2)
                    
                    # 进度完成标记
                    if mm_tracker:
                        try:
                            mm_tracker.mark_completed("✅ 多模型协作分析完成", results=results)
                        except Exception:
                            pass
                    
                    logger.info(f"✅ [多模型分析完成] {analysis_id}: 结果已保存到 {result_file}")
                    
                except Exception as e:
                    # 保存错误信息
                    error_file = f"./data/multi_model_results_{analysis_id}.json"
                    os.makedirs(os.path.dirname(error_file), exist_ok=True)
                    
                    import json
                    with open(error_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            'analysis_id': analysis_id,
                            'status': 'failed',
                            'error': str(e),
                            'timestamp': datetime.datetime.now().isoformat()
                        }, f, ensure_ascii=False, indent=2)
                    
                    if mm_tracker:
                        try:
                            mm_tracker.mark_failed(str(e))
                        except Exception:
                            pass
                    
                    logger.error(f"❌ [多模型分析失败] {analysis_id}: {e}")
            
            # 启动后台分析线程
            analysis_thread = threading.Thread(target=run_multi_model_analysis_in_background)
            analysis_thread.daemon = True
            analysis_thread.start()
            
            logger.info(f"🧵 [多模型后台分析] 分析线程已启动: {analysis_id}")
            
            # 页面将自动刷新显示进度
            st.info("⏱️ 页面将自动刷新显示分析进度...")
            time.sleep(2)
            st.rerun()
        
        # 2. 分析进度区域
        current_analysis_id = st.session_state.get('multi_model_current_analysis_id')
        if current_analysis_id:
            st.markdown("---")
            st.subheader("📊 分析进度")
            
            # 统一进度展示（与单模型一致）
            try:
                is_completed = display_unified_progress(current_analysis_id, show_refresh_controls=True)
            except Exception:
                is_completed = False

            # 兼容旧文件轮询（作为兜底）
            result_file = f"./data/multi_model_results_{current_analysis_id}.json"
            
            if os.path.exists(result_file):
                try:
                    import json
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result_data = json.load(f)
                    
                    status = result_data.get('status', 'unknown')
                    
                    if status == 'completed':
                        st.success("✅ 多模型协作分析完成！")
                        st.session_state.multi_model_analysis_running = False
                        # 修复：保存完整的结果数据，而不是仅保存嵌套的results
                        st.session_state.multi_model_analysis_results = result_data.get('results', result_data)

                        # 统一体验：自动展示分析报告（无需再次点击）
                        st.session_state.show_multi_model_results = True
                        st.info("📊 正在展示分析报告…")
                            
                    elif status == 'failed':
                        st.error("❌ 多模型协作分析失败")
                        st.error(f"错误信息: {result_data.get('error', 'Unknown error')}")
                        st.session_state.multi_model_analysis_running = False
                        
                    else:
                        st.info("🔄 多模型协作分析正在进行中...")
                        st.session_state.multi_model_analysis_running = True
                        
                except Exception as e:
                    st.error(f"❌ 读取分析结果失败: {e}")
            else:
                if st.session_state.get('multi_model_analysis_running', False):
                    st.info("🔄 多模型协作分析正在进行中...")
                    # 显示统一进度刷新控件由组件负责；此处仅兜底刷新
                    time.sleep(2)
                    st.rerun()
                
        # 3. 分析报告区域
        if (st.session_state.get('multi_model_analysis_results') and 
            not st.session_state.get('multi_model_analysis_running', False)) or \
            st.session_state.get('show_multi_model_results', False):
            
            st.markdown("---")
            st.subheader("📋 多模型协作分析报告")
            
            try:
                from components.multi_model_analysis_form import render_multi_model_results
                render_multi_model_results(st.session_state.multi_model_analysis_results)
                
                # 清除显示状态
                if st.session_state.get('show_multi_model_results', False):
                    st.session_state.show_multi_model_results = False
                    
            except Exception as e:
                st.error(f"❌ 报告显示失败: {e}")
                st.write("**原始结果数据:**")
                st.json(st.session_state.multi_model_analysis_results)
    
    # 右侧文档说明已移除：保留顶部导航中的“📖 文档”页作为唯一入口


def initialize_session_state():
    """初始化会话状态"""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'analysis_running' not in st.session_state:
        st.session_state.analysis_running = False
    if 'last_analysis_time' not in st.session_state:
        st.session_state.last_analysis_time = None
    if 'current_analysis_id' not in st.session_state:
        st.session_state.current_analysis_id = None
    if 'form_config' not in st.session_state:
        st.session_state.form_config = None

    # 尝试从最新完成的分析中恢复结果
    if not st.session_state.analysis_results:
        try:
            from utils.async_progress_tracker import get_latest_analysis_id, get_progress_by_id
            from utils.analysis_runner import format_analysis_results

            latest_id = get_latest_analysis_id()
            if latest_id:
                progress_data = get_progress_by_id(latest_id)
                if (progress_data and
                    progress_data.get('status') == 'completed' and
                    'raw_results' in progress_data):

                    # 恢复分析结果
                    raw_results = progress_data['raw_results']
                    formatted_results = format_analysis_results(raw_results)

                    if formatted_results:
                        st.session_state.analysis_results = formatted_results
                        st.session_state.current_analysis_id = latest_id
                        # 检查分析状态
                        analysis_status = progress_data.get('status', 'completed')
                        st.session_state.analysis_running = (analysis_status == 'running')
                        # 恢复股票信息
                        if 'stock_symbol' in raw_results:
                            st.session_state.last_stock_symbol = raw_results.get('stock_symbol', '')
                        if 'market_type' in raw_results:
                            st.session_state.last_market_type = raw_results.get('market_type', '')
                        logger.info(f"📊 [结果恢复] 从分析 {latest_id} 恢复结果，状态: {analysis_status}")

        except Exception as e:
            logger.warning(f"⚠️ [结果恢复] 恢复失败: {e}")

    # 使用cookie管理器恢复分析ID（优先级：session state > cookie > Redis/文件）
    try:
        persistent_analysis_id = get_persistent_analysis_id()
        if persistent_analysis_id:
            # 使用线程检测来检查分析状态
            from utils.thread_tracker import check_analysis_status
            actual_status = check_analysis_status(persistent_analysis_id)

            # 只在状态变化时记录日志，避免重复
            current_session_status = st.session_state.get('last_logged_status')
            if current_session_status != actual_status:
                logger.info(f"📊 [状态检查] 分析 {persistent_analysis_id} 实际状态: {actual_status}")
                st.session_state.last_logged_status = actual_status

            if actual_status == 'running':
                st.session_state.analysis_running = True
                st.session_state.current_analysis_id = persistent_analysis_id
            elif actual_status in ['completed', 'failed']:
                st.session_state.analysis_running = False
                st.session_state.current_analysis_id = persistent_analysis_id
            else:  # not_found
                logger.warning(f"📊 [状态检查] 分析 {persistent_analysis_id} 未找到，清理状态")
                st.session_state.analysis_running = False
                st.session_state.current_analysis_id = None
    except Exception as e:
        # 如果恢复失败，保持默认值
        logger.warning(f"⚠️ [状态恢复] 恢复分析状态失败: {e}")
        st.session_state.analysis_running = False
        st.session_state.current_analysis_id = None

    # 恢复表单配置
    try:
        from utils.smart_session_manager import smart_session_manager
        session_data = smart_session_manager.load_analysis_state()

        if session_data and 'form_config' in session_data:
            st.session_state.form_config = session_data['form_config']
            # 只在没有分析运行时记录日志，避免重复
            if not st.session_state.get('analysis_running', False):
                logger.info("📊 [配置恢复] 表单配置已恢复")
    except Exception as e:
        logger.warning(f"⚠️ [配置恢复] 表单配置恢复失败: {e}")

def main():
    """主应用程序"""

    # 初始化会话状态
    initialize_session_state()

    # 在渲染顶部导航前处理任何待处理的导航重定向
    # 通过 '_nav_redirect_to' 传递目标页，避免在控件实例化后直接修改其 key
    try:
        _pending_nav = st.session_state.pop('_nav_redirect_to', None)
        if _pending_nav:
            st.session_state.top_nav_page = _pending_nav
    except Exception:
        pass

    # 自定义CSS - 调整侧边栏宽度
    st.markdown("""
    <style>
    /* 完全隐藏侧边栏，转为顶部导航 */
    section[data-testid="stSidebar"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
    }

    /* 隐藏侧边栏的隐藏按钮 - 更全面的选择器 */
    button[kind="header"],
    button[data-testid="collapsedControl"],
    .css-1d391kg,
    .css-1rs6os,
    .css-17eq0hr,
    .css-1lcbmhc,
    .css-1y4p8pa,
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"],
    [data-testid="collapsedControl"],
    .stSidebar button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* 隐藏侧边栏顶部区域的特定按钮（更精确的选择器，避免影响表单按钮） */
    section[data-testid="stSidebar"] > div:first-child > button[kind="header"],
    section[data-testid="stSidebar"] > div:first-child > div > button[kind="header"],
    section[data-testid="stSidebar"] .css-1lcbmhc > button[kind="header"],
    section[data-testid="stSidebar"] .css-1y4p8pa > button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* 调整侧边栏内容的padding */
    section[data-testid="stSidebar"] > div {
        padding-top: 0.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* 调整主内容区域，设置8px边距 - 使用更强的选择器 */
    .main .block-container,
    section.main .block-container,
    div.main .block-container,
    .stApp .main .block-container {
        padding-left: 8px !important;
        padding-right: 8px !important;
        margin-left: 0px !important;
        margin-right: 0px !important;
        max-width: none !important;
        width: calc(100% - 16px) !important;
    }

    /* 确保内容不被滚动条遮挡 */
    .stApp > div {
        overflow-x: auto !important;
    }

    /* 调整详细分析报告的右边距 */
    .element-container {
        margin-right: 8px !important;
    }

    /* 优化侧边栏标题和元素间距 */
    .sidebar .sidebar-content {
        padding: 0.5rem 0.3rem !important;
    }

    /* 调整侧边栏内所有元素的间距 */
    section[data-testid="stSidebar"] .element-container {
        margin-bottom: 0.5rem !important;
    }

    /* 调整侧边栏分隔线的间距 */
    section[data-testid="stSidebar"] hr {
        margin: 0.8rem 0 !important;
    }

    /* 确保侧边栏标题不被挤压 */
    section[data-testid="stSidebar"] h1 {
        font-size: 1.2rem !important;
        line-height: 1.3 !important;
        margin-bottom: 1rem !important;
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }

    /* 简化功能选择区域样式 */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        font-size: 1.1rem !important;
        font-weight: 500 !important;
    }

    /* 调整选择框等组件的宽度 */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        min-width: 220px !important;
        width: 100% !important;
    }

    /* 修复右侧内容被遮挡的问题 */
    .main {
        padding-right: 8px !important;
    }

    /* 确保页面内容有足够的右边距 */
    .stApp {
        margin-right: 0 !important;
        padding-right: 8px !important;
    }

    /* 特别处理展开的分析报告 */
    .streamlit-expanderContent {
        padding-right: 8px !important;
        margin-right: 8px !important;
    }

    /* 防止水平滚动条出现 */
    .main .block-container {
        overflow-x: visible !important;
    }

    /* 强制设置8px边距给所有可能的容器 */
    .stApp,
    .stApp > div,
    .stApp > div > div,
    .main,
    .main > div,
    .main > div > div,
    div[data-testid="stAppViewContainer"],
    div[data-testid="stAppViewContainer"] > div,
    section[data-testid="stMain"],
    section[data-testid="stMain"] > div {
        padding-left: 8px !important;
        padding-right: 8px !important;
        margin-left: 0px !important;
        margin-right: 0px !important;
    }

    /* 特别处理列容器 */
    div[data-testid="column"],
    .css-1d391kg,
    .css-1r6slb0,
    .css-12oz5g7,
    .css-1lcbmhc {
        padding-left: 8px !important;
        padding-right: 8px !important;
        margin-left: 0px !important;
        margin-right: 0px !important;
    }

    /* 强制设置容器宽度（无侧边栏） */
    .main .block-container {
        width: calc(100vw - 16px) !important;
        max-width: calc(100vw - 16px) !important;
    }

    /* 优化使用指南区域的样式 */
    div[data-testid="column"]:last-child {
        background-color: #f8f9fa !important;
        border-radius: 8px !important;
        padding: 12px !important;
        margin-left: 8px !important;
        border: 1px solid #e9ecef !important;
    }

    /* 使用指南内的展开器样式 */
    div[data-testid="column"]:last-child .streamlit-expanderHeader {
        background-color: #ffffff !important;
        border-radius: 6px !important;
        border: 1px solid #dee2e6 !important;
        font-weight: 500 !important;
    }

    /* 使用指南内的文本样式 */
    div[data-testid="column"]:last-child .stMarkdown {
        font-size: 0.9rem !important;
        line-height: 1.5 !important;
    }

    /* 使用指南标题样式 */
    div[data-testid="column"]:last-child h1 {
        font-size: 1.3rem !important;
        color: #495057 !important;
        margin-bottom: 1rem !important;
    }
    </style>

    <script>
    // JavaScript来强制隐藏侧边栏按钮
    function hideSidebarButtons() {
        // 隐藏所有可能的侧边栏控制按钮
        const selectors = [
            'button[kind="header"]',
            'button[data-testid="collapsedControl"]',
            'button[aria-label="Close sidebar"]',
            'button[aria-label="Open sidebar"]',
            '[data-testid="collapsedControl"]',
            '.css-1d391kg',
            '.css-1rs6os',
            '.css-17eq0hr',
            '.css-1lcbmhc button',
            '.css-1y4p8pa button'
        ];

        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.style.opacity = '0';
                el.style.pointerEvents = 'none';
            });
        });
    }

    // 页面加载后执行
    document.addEventListener('DOMContentLoaded', hideSidebarButtons);

    // 定期检查并隐藏按钮（防止动态生成）
    setInterval(hideSidebarButtons, 1000);

    // 强制修改页面边距为8px
    function forceOptimalPadding() {
        const selectors = [
            '.main .block-container',
            '.stApp',
            '.stApp > div',
            '.main',
            '.main > div',
            'div[data-testid="stAppViewContainer"]',
            'section[data-testid="stMain"]',
            'div[data-testid="column"]'
        ];

        selectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                el.style.paddingLeft = '8px';
                el.style.paddingRight = '8px';
                el.style.marginLeft = '0px';
                el.style.marginRight = '0px';
            });
        });

        // 特别处理主容器宽度
        const mainContainer = document.querySelector('.main .block-container');
        if (mainContainer) {
            mainContainer.style.width = 'calc(100vw - 16px)';
            mainContainer.style.maxWidth = 'calc(100vw - 16px)';
        }
    }

    // 页面加载后执行
    document.addEventListener('DOMContentLoaded', forceOptimalPadding);

    // 定期强制应用样式
    setInterval(forceOptimalPadding, 500);
    </script>
    """, unsafe_allow_html=True)

    # 添加调试按钮（仅在调试模式下显示）
    if os.getenv('DEBUG_MODE') == 'true':
        if st.button("🔄 清除会话状态"):
            st.session_state.clear()
            st.experimental_rerun()

    # 主题切换功能已移除，保持默认浅色主题

    # 顶部“浏览器标签页”式导航（置于页面最顶）
    menu_pages = [
        "📊 个股分析",
        "🌍 全球市场分析",
        "🧮 指数与筛选",
        "🧭 角色中心",
        "📧 邮件订阅管理",
        "📚 图书馆",
        "⚙️ 配置管理",
        "📈 历史记录",
        "🔧 系统状态",
    ]
    # 兼容老镜像：若容器内还未包含新函数，则临时退回到 radio 导航
    if callable(render_browser_tabs):
        page = render_browser_tabs(menu_pages, default_index=0)
    else:
        if 'top_nav_page' not in st.session_state:
            st.session_state.top_nav_page = "📊 个股分析"
        page = st.radio(
            "功能导航",
            menu_pages,
            index=menu_pages.index(st.session_state.top_nav_page) if st.session_state.top_nav_page in menu_pages else 0,
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav_page",
        )

    # 顶部品牌区（位于导航下方）——压缩头部留白
    with st.container():
        render_header()
    # 注：已移除悬浮“配置”图片按钮，顶部已有“⚙️ 配置管理”入口，避免重复

    # 顶部工具区（与标签同一行下方）——更紧凑
    multi_model_enabled = os.getenv('MULTI_MODEL_ENABLED', 'false').lower() == 'true' and MULTI_MODEL_AVAILABLE
    tool_c1, _, tool_c3 = st.columns([3, 7, 2])
    with tool_c1:
        if page == "📊 个股分析":
            if multi_model_enabled:
                st.radio("分析模式", ["单模型", "多模型"], key="analysis_mode", horizontal=True)
            else:
                st.session_state.analysis_mode = '单模型'
    with tool_c3:
        if st.button("🧹 清理分析状态"):
            st.session_state.analysis_running = False
            st.session_state.current_analysis_id = None
            st.session_state.analysis_results = None
            for key in list(st.session_state.keys()):
                if 'auto_refresh' in key:
                    del st.session_state[key]
            from utils.thread_tracker import cleanup_dead_analysis_threads
            cleanup_dead_analysis_threads()
            st.success("✅ 已清理")
            st.rerun()

    # 顶部导航已包含模式切换，这里不再使用侧边栏

    # 根据选择的页面渲染不同内容
    # 注：多模型协作不再作为单独页面展示，而是作为"个股分析"页的一种模式
    if page == "🌍 全球市场分析":
        try:
            from modules.market_wide_analysis import render_market_wide_analysis
            render_market_wide_analysis()
        except ImportError as e:
            st.error(f"全球市场分析模块加载失败: {e}")
            st.info("请确保已安装所有依赖包")
        finally:
            inject_back_to_top_button()
        return
    elif page == "⚙️ 配置管理":
        try:
            from modules.config_management import render_config_management
            render_config_management()
        except ImportError as e:
            st.error(f"配置管理模块加载失败: {e}")
            st.info("请确保已安装所有依赖包")
        finally:
            inject_back_to_top_button()
        return
    elif page == "🧮 指数与筛选":
        try:
            from modules.indices_filters import render_indices_and_filters
            render_indices_and_filters()
        except Exception as e:
            st.error(f"指数与筛选页面加载失败: {e}")
        finally:
            inject_back_to_top_button()
        return
    elif page == "🧭 角色中心":
        try:
            from modules.roles_center import render_roles_center
            render_roles_center()
        except Exception as e:
            st.error(f"角色中心页面加载失败: {e}")
        finally:
            inject_back_to_top_button()
        return
    elif page == "💾 缓存管理":
        try:
            # 兼容旧入口：在“缓存管理”菜单下渲染合并后的图书馆页面
            from modules.library import render_library
            render_library()
        except Exception as e:
            st.error(f"图书馆页面加载失败: {e}")
        finally:
            inject_back_to_top_button()
        return
    elif page == "📚 图书馆":
        try:
            from modules.library import render_library
            render_library()
        except Exception as e:
            st.error(f"图书馆页面加载失败: {e}")
        finally:
            inject_back_to_top_button()
        return
    elif page == "📈 历史记录":
        try:
            from components.history_manager import render_history_page
            render_history_page()
        except ImportError as e:
            st.error(f"历史记录页面加载失败: {e}")
            st.info("请确保已安装所有依赖包")
        finally:
            inject_back_to_top_button()
        return
    elif page == "🔧 系统状态":
        try:
            from components.system_status import render_system_status
            render_system_status()
        except ImportError as e:
            st.error(f"系统状态页面加载失败: {e}")
            st.info("请确保已安装所有依赖包")
        finally:
            inject_back_to_top_button()
        return

    # 默认显示个股分析页面
    # 检查API密钥
    api_status = check_api_keys()
    
    if not api_status['all_configured']:
        st.error("⚠️ API密钥配置不完整，请先配置必要的API密钥")
        
        with st.expander("📋 API密钥配置指南", expanded=True):
            st.markdown("""
            ### 🔑 必需的API密钥
            
            1. **Google AI / Gemini API密钥**（优先 `GEMINI_API_KEY`，也支持 `GOOGLE_AI_API_KEY`/`GOOGLE_GENAI_API_KEY`/`GOOGLE_API_KEY`）
               - 获取地址: https://aistudio.google.com/
               - 用途: AI模型推理（Gemini系列）
            
            2. **金融数据API密钥** (FINNHUB_API_KEY)  
               - 获取地址: https://finnhub.io/
               - 用途: 获取股票数据
            
            ### ⚙️ 配置方法
            
            1. 复制项目根目录的 `.env.example` 为 `.env`
            2. 编辑 `.env` 文件，填入您的真实API密钥
            3. 重启Web应用
            
            ```bash
            # .env 文件示例
            # 推荐使用 GEMINI_API_KEY
            GEMINI_API_KEY=your_google_api_key
            FINNHUB_API_KEY=your-finnhub-key
            ```
            """)
        
        # 显示当前API密钥状态
        st.subheader("🔍 当前API密钥状态")
        for key, status in api_status['details'].items():
            if status['configured']:
                st.success(f"✅ {key}: {status['display']}")
            else:
                st.error(f"❌ {key}: 未配置")
        
        return
    
    # 获取基础配置（无需侧边栏）
    config = _get_llm_base_config_from_state()
    
    # 使用指南显示切换已并入主页面（不再放在侧边栏）

    # 清理按钮已上移到顶部导航

    # 该选择已由顶部下拉菜单提供，这里不再重复渲染二级切换
    if page == "📊 个股分析":
        # 如果开启了多模型模式，则在同一页面渲染多模型协作体验
        if st.session_state.get('analysis_mode') == '多模型' and multi_model_enabled:
            # 在同一页面渲染多模型协作（复用前面渲染得到的config，避免侧边栏重复渲染）
            render_multi_model_collaboration_page(config=config)
            return
    
    # 主内容区域 - 根据是否显示指南调整布局
    if page == "📊 个股分析":
        col1 = st.container()
        col2 = None

        with col1:
            # 单屏三分栏改为主区域标签页：配置 / 进度 / 结果
            tab_config, tab_progress, tab_results = st.tabs(["⚙️ 配置", "📊 进度", "📋 结果"])

            # 若来自进度面板点击“查看分析报告”，自动切换到“📋 结果”标签
            if st.session_state.get('show_analysis_results'):
                st.session_state.show_analysis_results = False  # 防止循环触发
                st.markdown(
                    """
                    <script>
                    setTimeout(function(){
                        const tabs = document.querySelectorAll('div[role="tab"]');
                        for (const t of tabs) {
                            if (t.innerText && t.innerText.indexOf('📋 结果') !== -1) { t.click(); break; }
                        }
                    }, 50);
                    </script>
                    """,
                    unsafe_allow_html=True,
                )

            # ============ 配置 ============
            with tab_config:
                try:
                    form_data = render_analysis_form()
                    if not isinstance(form_data, dict):
                        st.error(f"⚠️ 表单数据格式异常: {type(form_data)}")
                        form_data = {'submitted': False}
                except Exception as e:
                    st.error(f"❌ 表单渲染失败: {e}")
                    form_data = {'submitted': False}
                
                # 简单模式（画像）优先，其次才是完整模型面板
                simple_mode_enabled = os.getenv('SIMPLE_MODE', 'true').lower() == 'true'
                if simple_mode_enabled:
                    try:
                        profile_cfg = render_profile_panel()
                        model_cfg = {
                            'llm_provider': profile_cfg.get('llm_provider'),
                            'llm_model': profile_cfg.get('llm_deep_model'),
                            'llm_quick_model': profile_cfg.get('llm_quick_model'),
                            'llm_deep_model': profile_cfg.get('llm_deep_model'),
                            'routing_strategy': profile_cfg.get('routing_strategy'),
                            'fallbacks': [],
                            'max_budget': profile_cfg.get('max_budget') or 0.0,
                        }
                        # 将关键路由参数注入 session_state 以复用后续逻辑
                        st.session_state.routing_strategy_select = profile_cfg.get('routing_strategy')
                        st.session_state.max_budget = profile_cfg.get('max_budget') or 0.0
                        st.session_state.SIMPLE_MODE_DEFAULT = True
                    except Exception as e:
                        st.warning(f"⚠️ 简单模式面板加载失败，退回高级模式: {e}")
                        try:
                            from components.model_selection_panel import render_model_selection_panel
                            model_cfg = render_model_selection_panel(location="main")
                        except Exception as e2:
                            st.error(f"❌ 模型选择面板渲染失败: {e2}")
                            model_cfg = {}
                else:
                    try:
                        from components.model_selection_panel import render_model_selection_panel
                        model_cfg = render_model_selection_panel(location="main")
                    except Exception as e:
                        st.error(f"❌ 模型选择面板渲染失败: {e}")
                        model_cfg = {}

                # 在主页面展示并合并原侧边栏的 API 密钥状态
                try:
                    api_status_inline = check_api_keys()
                    with st.expander("🔑 API密钥状态", expanded=not api_status_inline['all_configured']):
                        # 必需配置优先显示
                        st.markdown("**必须配置：**")
                        for key, info in api_status_inline['details'].items():
                            if info.get('required'):
                                if info['configured']:
                                    st.success(f"✅ {key}: {info['display']}")
                                else:
                                    st.error(f"❌ {key}: 未配置")
                        # 可选配置
                        st.markdown("**可选配置：**")
                        for key, info in api_status_inline['details'].items():
                            if not info.get('required'):
                                if info['configured']:
                                    st.success(f"✅ {key}: {info['display']}")
                                else:
                                    st.info(f"ℹ️ {key}: 未配置")
                except Exception as e:
                    st.warning(f"⚠️ API密钥状态展示失败: {e}")

                if form_data.get('submitted', False) and not st.session_state.get('analysis_running', False):
                    is_valid, validation_errors = validate_analysis_params(
                        stock_symbol=form_data['stock_symbol'],
                        analysis_date=form_data['analysis_date'],
                        analysts=form_data['analysts'],
                        research_depth=form_data['research_depth'],
                        market_type=form_data.get('market_type', '美股')
                    )
                    if not is_valid:
                        for error in validation_errors:
                            st.error(error)
                    else:
                        # 初始化异步任务
                        st.session_state.analysis_results = None
                        import uuid
                        analysis_id = f"analysis_{uuid.uuid4().hex[:8]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        form_config = st.session_state.get('form_config', {})
                        set_persistent_analysis_id(
                            analysis_id=analysis_id,
                            status="running",
                            stock_symbol=form_data['stock_symbol'],
                            market_type=form_data.get('market_type', '美股'),
                            form_config=form_config
                        )

                        async_tracker = AsyncProgressTracker(
                            analysis_id=analysis_id,
                            analysts=form_data['analysts'],
                            research_depth=form_data['research_depth'],
                            llm_provider=config['llm_provider']
                        )

                        def progress_callback(message: str, step: int = None, total_steps: int = None):
                            async_tracker.update_progress(message, step)

                        st.success(f"🚀 分析已启动！分析ID: {analysis_id}")
                        with st.spinner("🔄 正在初始化分析..."):
                            time.sleep(1.0)

                        st.session_state.analysis_running = True
                        st.session_state.current_analysis_id = analysis_id
                        st.session_state.last_stock_symbol = form_data['stock_symbol']
                        st.session_state.last_market_type = form_data.get('market_type', '美股')

                        auto_refresh_keys = [
                            f"auto_refresh_unified_{analysis_id}",
                            f"auto_refresh_unified_default_{analysis_id}",
                            f"auto_refresh_static_{analysis_id}",
                            f"auto_refresh_streamlit_{analysis_id}"
                        ]
                        for key in auto_refresh_keys:
                            st.session_state[key] = True

                        import threading
                        def run_analysis_in_background():
                            try:
                                # 简单模式下用画像覆盖部分表单项
                                analysts_to_use = form_data['analysts']
                                if simple_mode_enabled:
                                    try:
                                        analysts_to_use = profile_cfg.get('analysts') or analysts_to_use
                                    except Exception:
                                        pass
                                # 过滤到框架支持的分析师集合
                                allowed_analysts = ['market', 'fundamentals', 'news', 'social']
                                analysts_to_use = [a for a in analysts_to_use if a in allowed_analysts]

                                results = run_stock_analysis(
                                    stock_symbol=form_data['stock_symbol'],
                                    analysis_date=form_data['analysis_date'],
                                    analysts=analysts_to_use,
                                    research_depth=form_data['research_depth'],
                                    llm_provider=model_cfg.get('llm_provider') or config['llm_provider'],
                                    market_type=form_data.get('market_type', '美股'),
                                    llm_model=model_cfg.get('llm_model') or model_cfg.get('llm_deep_model') or model_cfg.get('llm_quick_model') or config['llm_model'],
                                    progress_callback=progress_callback,
                                    llm_quick_model=model_cfg.get('llm_quick_model'),
                                    llm_deep_model=model_cfg.get('llm_deep_model'),
                                    routing_strategy=model_cfg.get('routing_strategy'),
                                    fallbacks=model_cfg.get('fallbacks'),
                                    max_budget=model_cfg.get('max_budget') or 0.0
                                )
                                async_tracker.mark_completed("✅ 分析成功完成！", results=results)
                            except Exception as e:
                                async_tracker.mark_failed(str(e))
                            finally:
                                from utils.thread_tracker import unregister_analysis_thread
                                unregister_analysis_thread(analysis_id)

                        analysis_thread = threading.Thread(target=run_analysis_in_background, daemon=True)
                        analysis_thread.start()
                        from utils.thread_tracker import register_analysis_thread
                        register_analysis_thread(analysis_id, analysis_thread)
                        st.info("➡️ 请切换到 ‘📊 进度’ 标签查看实时进度")

            # ============ 进度 ============
            with tab_progress:
                current_analysis_id = st.session_state.get('current_analysis_id')
                if not current_analysis_id:
                    st.info("尚未开始分析。在 ‘⚙️ 配置’ 标签提交表单后查看进度。")
                else:
                    from utils.thread_tracker import check_analysis_status
                    actual_status = check_analysis_status(current_analysis_id)
                    is_running = (actual_status == 'running')
                    if st.session_state.get('analysis_running', False) != is_running:
                        st.session_state.analysis_running = is_running
                    from utils.async_progress_tracker import get_progress_by_id
                    progress_data = get_progress_by_id(current_analysis_id)
                    is_completed = display_unified_progress(current_analysis_id, show_refresh_controls=is_running)
                    if is_running:
                        st.info("⏱️ 分析进行中…")
                    if is_completed and not st.session_state.get('analysis_results') and progress_data and 'raw_results' in progress_data:
                        try:
                            from utils.analysis_runner import format_analysis_results
                            formatted_results = format_analysis_results(progress_data['raw_results'])
                            if formatted_results:
                                st.session_state.analysis_results = formatted_results
                                st.session_state.analysis_running = False
                                st.success("📊 分析完成，结果已就绪。")
                        except Exception as e:
                            logger.warning(f"⚠️ [结果同步] 恢复失败: {e}")

            # ============ 结果 ============
            with tab_results:
                analysis_results = st.session_state.get('analysis_results')
                if analysis_results:
                    # 检查是否有可视化数据，如有则使用增强版标签页布局
                    if 'visualizations' in analysis_results and analysis_results['visualizations']:
                        # 使用标签页布局展示分析结果和可视化图表
                        result_tabs = st.tabs(["📋 分析报告", "📊 可视化图表"])
                        
                        with result_tabs[0]:
                            render_results(analysis_results)
                        
                        with result_tabs[1]:
                            # 渲染可视化图表
                            try:
                                from components.enhanced_visualization_tab import render_visualizations
                                render_visualizations(analysis_results['visualizations'])
                            except ImportError:
                                st.info("可视化组件不可用")
                    else:
                        # 使用标准布局
                        render_results(analysis_results)
                else:
                    st.info("暂无结果。请先在 '⚙️ 配置' 标签启动分析，或稍后在 '📊 进度' 标签等待完成。")
    
        # 右侧不再展示文档入口（已有单独文档页）

        # 悬浮“回到顶部”按钮
        inject_back_to_top_button()
        
        # 显示系统状态
        if st.session_state.last_analysis_time:
            st.info(f"🕒 上次分析时间: {st.session_state.last_analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 兼容：旧菜单进入角色库时，引导到角色中心
    elif page == "🧰 角色库":
        try:
            from modules.roles_center import render_roles_center
            st.info("ℹ️ ‘角色库’与‘角色模型绑定’已合并到‘🧭 角色中心’页面。以下展示合并后的页面。")
            render_roles_center()
        except Exception as e:
            st.error(f"角色中心页面加载失败: {e}")
        finally:
            inject_back_to_top_button()
        
    # 订阅管理页面
    elif page == "📧 邮件订阅管理":
        
        # 检查是否启用了调度服务
        scheduler_enabled = os.getenv('SCHEDULER_ENABLED', 'false').lower() == 'true'
        if not scheduler_enabled:
            st.warning("⚠️ 调度服务未启用，请在.env中设置 SCHEDULER_ENABLED=true")
        
        # 检查邮件配置
        smtp_user = os.getenv('SMTP_USER')
        if not smtp_user:
            st.error("❌ 邮件服务未配置，请在.env中设置SMTP相关参数")
            st.markdown("""
            ### 配置示例：
            ```
            SMTP_HOST=smtp.qq.com
            SMTP_PORT=465
            SMTP_USER=your_email@qq.com
            SMTP_PASS=your_smtp_password
            ```
            """)
        else:
            # 渲染订阅管理界面
            try:
                from components.subscription_manager import render_subscription_manager
                render_subscription_manager()
            except ImportError as e:
                st.error("❌ 订阅管理模块未正确安装")
                st.code(f"错误信息: {e}")
                st.markdown("""
                ### 解决方法：
                1. 确保已安装所有依赖：`pip install -e .`
                2. 重启应用
                """)
            except Exception as e:
                st.error(f"❌ 加载订阅管理模块失败: {e}")
        # 通用“回到顶部”
        inject_back_to_top_button()

    # 附件管理页面
    elif page == "📎 附件管理":
        # 将“附件管理”入口重定向到“图书馆”，避免分散
        try:
            from modules.library import render_library
            render_library(default_tab="attachments")
        except Exception as e:
            st.error(f"图书馆页面加载失败: {e}")
        finally:
            inject_back_to_top_button()

if __name__ == "__main__":
    main()
