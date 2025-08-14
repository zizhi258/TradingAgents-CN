#!/usr/bin/env python3
"""
调度器管理Web组件
提供调度器状态管理和配置的Streamlit界面
"""

import streamlit as st
import os
import json
import pytz
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import sys

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.config.config_manager import ConfigManager
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.scheduler')


def render_scheduler_overview(scheduler_status: Dict):
    """渲染调度器状态概览"""
    
    st.markdown("### 📊 调度器状态")
    
    # 创建状态指示器
    col1, col2, col3 = st.columns(3)
    
    with col1:
        running = scheduler_status.get('running', False)
        status_color = "🟢" if running else "🔴"
        status_text = "运行中" if running else "已停止"
        st.metric("调度器状态", f"{status_color} {status_text}")
    
    with col2:
        total_jobs = scheduler_status.get('total_jobs', 0)
        st.metric("调度任务数", total_jobs)
    
    with col3:
        timezone = scheduler_status.get('timezone', 'Asia/Shanghai')
        current_time = datetime.now().strftime('%H:%M:%S')
        st.metric("当前时间", f"{current_time} ({timezone})")
    
    # 信息与告警显示（不阻断页面）
    if 'error' in scheduler_status:
        st.error(f"❌ 调度器错误: {scheduler_status['error']}")
        return
    if 'warning' in scheduler_status:
        st.warning(f"⚠️ {scheduler_status['warning']}")
    if 'note' in scheduler_status:
        st.info(f"ℹ️ {scheduler_status['note']}")
    
    # 任务列表
    jobs = scheduler_status.get('jobs', [])
    if jobs:
        st.markdown("### 📋 调度任务列表")
        
        job_data = []
        for job in jobs:
            next_run = job.get('next_run_time', '')
            if next_run:
                try:
                    # 解析ISO格式时间
                    next_run_dt = datetime.fromisoformat(next_run.replace('Z', '+00:00'))
                    next_run_str = next_run_dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    next_run_str = next_run
            else:
                next_run_str = "未设置"
            
            job_data.append({
                "任务ID": job.get('id', ''),
                "任务名称": job.get('name', ''),
                "下次执行时间": next_run_str,
                "触发器": job.get('trigger', '')[:50] + '...' if len(str(job.get('trigger', ''))) > 50 else job.get('trigger', '')
            })
        
        st.dataframe(job_data, use_container_width=True)
    else:
        st.info("📭 暂无活跃的调度任务")


def render_schedule_editor(settings: Dict):
    """渲染调度配置编辑器"""
    
    st.markdown("### ⚙️ 邮件调度配置")
    
    email_schedules = settings.get('email_schedules', {
        'daily': {'enabled': False, 'hour': 18, 'minute': 0},
        'weekly': {'enabled': False, 'weekday': [1], 'hour': 9, 'minute': 0}
    })
    
    # 每日调度配置
    with st.expander("📅 每日邮件调度", expanded=True):
        daily_config = email_schedules.get('daily', {})
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            daily_enabled = st.checkbox(
                "启用每日邮件", 
                value=daily_config.get('enabled', False),
                key='daily_enabled'
            )
        
        with col2:
            daily_hour = st.number_input(
                "小时 (0-23)",
                min_value=0,
                max_value=23,
                value=daily_config.get('hour', 18),
                key='daily_hour',
                help="24小时制，0-23范围内"
            )
        
        with col3:
            daily_minute = st.number_input(
                "分钟 (0-59)",
                min_value=0,
                max_value=59,
                value=daily_config.get('minute', 0),
                key='daily_minute',
                help="0-59分钟范围内"
            )
        
        # 输入验证
        if daily_hour < 0 or daily_hour > 23:
            st.error("❌ 小时必须在0-23范围内")
        if daily_minute < 0 or daily_minute > 59:
            st.error("❌ 分钟必须在0-59范围内")
        
        if daily_enabled:
            st.info(f"📧 每日邮件将在 {daily_hour:02d}:{daily_minute:02d} 发送")
            # 计算距离下次执行的时间
            try:
                tz = pytz.timezone(os.getenv('SCHEDULER_TIMEZONE', 'Asia/Shanghai'))
                now = datetime.now(tz)
                next_run = now.replace(hour=daily_hour, minute=daily_minute, second=0, microsecond=0)
                
                # 如果时间已过，设为明天
                if next_run <= now:
                    next_run += timedelta(days=1)
                
                time_diff = next_run - now
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                
                st.caption(f"⏰ 距离下次执行: {hours}小时{minutes}分钟")
            except Exception as e:
                st.caption(f"⚠️ 无法计算下次执行时间: {e}")
    
    # 每周调度配置
    with st.expander("📆 每周邮件调度", expanded=True):
        weekly_config = email_schedules.get('weekly', {})
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            weekly_enabled = st.checkbox(
                "启用每周邮件",
                value=weekly_config.get('enabled', False),
                key='weekly_enabled'
            )
        
        with col2:
            weekly_hour = st.number_input(
                "小时 (0-23)",
                min_value=0,
                max_value=23,
                value=weekly_config.get('hour', 9),
                key='weekly_hour',
                help="24小时制，0-23范围内"
            )
        
        with col3:
            weekly_minute = st.number_input(
                "分钟 (0-59)",
                min_value=0,
                max_value=59,
                value=weekly_config.get('minute', 0),
                key='weekly_minute',
                help="0-59分钟范围内"
            )
        
        # 输入验证
        if weekly_hour < 0 or weekly_hour > 23:
            st.error("❌ 小时必须在0-23范围内")
        if weekly_minute < 0 or weekly_minute > 59:
            st.error("❌ 分钟必须在0-59范围内")
        
        # 星期选择
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        current_weekdays = weekly_config.get('weekday', [1])
        
        # 验证weekday数据
        if not isinstance(current_weekdays, list):
            current_weekdays = [1]
        
        # 确保weekday在有效范围内
        current_weekdays = [w for w in current_weekdays if 0 <= w <= 6]
        if not current_weekdays:
            current_weekdays = [1]
        
        selected_weekdays = st.multiselect(
            "选择执行日期",
            options=list(range(7)),
            default=current_weekdays,
            format_func=lambda x: weekday_names[x],
            key='weekly_weekdays',
            disabled=not weekly_enabled,
            help="选择一周中哪些天执行任务"
        )
        
        # 验证至少选择一天
        if weekly_enabled and not selected_weekdays:
            st.error("❌ 启用每周邮件时必须至少选择一天")
            selected_weekdays = [1]  # 默认周一
        
        if weekly_enabled and selected_weekdays:
            weekday_str = ', '.join([weekday_names[w] for w in selected_weekdays])
            st.info(f"📧 每周邮件将在 {weekday_str} {weekly_hour:02d}:{weekly_minute:02d} 发送")
            
            # 计算距离下次执行的时间
            try:
                tz = pytz.timezone(os.getenv('SCHEDULER_TIMEZONE', 'Asia/Shanghai'))
                now = datetime.now(tz)
                
                # 找到下一个符合条件的工作日
                next_run = None
                for days_ahead in range(7):  # 查看接下来7天
                    check_date = now + timedelta(days=days_ahead)
                    if check_date.weekday() in selected_weekdays:
                        next_run = check_date.replace(hour=weekly_hour, minute=weekly_minute, second=0, microsecond=0)
                        
                        # 如果是今天但时间已过，跳到下一个符合的日期
                        if days_ahead == 0 and next_run <= now:
                            continue
                        break
                
                if next_run:
                    time_diff = next_run - now
                    days = time_diff.days
                    hours = int(time_diff.seconds // 3600)
                    minutes = int((time_diff.seconds % 3600) // 60)
                    
                    time_str = []
                    if days > 0:
                        time_str.append(f"{days}天")
                    if hours > 0:
                        time_str.append(f"{hours}小时")
                    if minutes > 0:
                        time_str.append(f"{minutes}分钟")
                    
                    if time_str:
                        st.caption(f"⏰ 距离下次执行: {''.join(time_str)}")
                    else:
                        st.caption("⏰ 即将执行")
                        
            except Exception as e:
                st.caption(f"⚠️ 无法计算下次执行时间: {e}")
    
    # 返回配置数据（包含验证）
    return {
        'email_schedules': {
            'daily': {
                'enabled': daily_enabled,
                'hour': max(0, min(23, daily_hour)),  # 确保在有效范围内
                'minute': max(0, min(59, daily_minute))
            },
            'weekly': {
                'enabled': weekly_enabled,
                'weekday': selected_weekdays,
                'hour': max(0, min(23, weekly_hour)),
                'minute': max(0, min(59, weekly_minute))
            }
        }
    }


def render_manual_triggers():
    """渲染手动触发器控件"""
    
    st.markdown("### 🚀 手动触发")
    
    # 检查调度器是否运行
    scheduler_status = get_scheduler_status()
    is_scheduler_running = scheduler_status.get('running', False)
    
    if not is_scheduler_running:
        st.warning("⚠️ 调度器未运行，手动触发可能无法正常工作")
        st.caption("请确保调度器服务已启动：`docker compose up -d scheduler`")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📅 每日邮件摘要")
        if st.button("▶️ 立即执行每日邮件", key="trigger_daily", 
                    disabled=not is_scheduler_running,
                    help="立即执行一次每日邮件发送任务"):
            
            with st.spinner("⏳ 正在创建每日邮件触发器..."):
                trigger_file = create_manual_trigger('daily', {
                    'triggered_by': 'web_ui',
                    'trigger_time': datetime.now().isoformat(),
                    'user_agent': 'scheduler_admin'
                })
                
            if trigger_file:
                st.success("✅ 每日邮件触发器已创建")
                st.info("📨 任务将在30秒内执行，请查看日志了解执行状态")
                
                # 显示触发器文件信息
                with st.expander("🔍 触发器详情"):
                    st.code(f"触发器文件: {Path(trigger_file).name}")
                    st.caption("该文件将在任务执行后自动删除")
                    
            else:
                st.error("❌ 创建每日邮件触发器失败")
                st.error("请检查data/triggers目录权限或查看系统日志")
    
    with col2:
        st.markdown("#### 📆 每周邮件摘要")
        if st.button("▶️ 立即执行每周邮件", key="trigger_weekly",
                    disabled=not is_scheduler_running,
                    help="立即执行一次每周邮件发送任务"):
            
            with st.spinner("⏳ 正在创建每周邮件触发器..."):
                trigger_file = create_manual_trigger('weekly', {
                    'triggered_by': 'web_ui',
                    'trigger_time': datetime.now().isoformat(),
                    'user_agent': 'scheduler_admin'
                })
                
            if trigger_file:
                st.success("✅ 每周邮件触发器已创建")
                st.info("📨 任务将在30秒内执行，请查看日志了解执行状态")
                
                # 显示触发器文件信息
                with st.expander("🔍 触发器详情"):
                    st.code(f"触发器文件: {Path(trigger_file).name}")
                    st.caption("该文件将在任务执行后自动删除")
                    
            else:
                st.error("❌ 创建每周邮件触发器失败")
                st.error("请检查data/triggers目录权限或查看系统日志")
    
    st.markdown("---")
    
    # 触发器状态检查
    st.markdown("#### 📊 触发器状态")
    
    # 检查待处理的触发器文件
    try:
        project_root = Path(__file__).parent.parent.parent
        trigger_dir = project_root / "data" / "triggers"
        
        if trigger_dir.exists():
            pending_triggers = list(trigger_dir.glob("*.json"))
            
            if pending_triggers:
                st.warning(f"⏳ 发现 {len(pending_triggers)} 个待处理的触发器文件")
                
                # 显示待处理触发器的详情
                with st.expander("📋 待处理触发器列表"):
                    for trigger_file in pending_triggers:
                        try:
                            with open(trigger_file, 'r', encoding='utf-8') as f:
                                trigger_data = json.load(f)
                            
                            trigger_type = trigger_data.get('type', 'unknown')
                            created_time = trigger_data.get('created_at', 'unknown')
                            
                            col1, col2, col3 = st.columns([2, 2, 1])
                            with col1:
                                st.text(f"📁 {trigger_file.name}")
                            with col2:
                                st.text(f"⏰ {created_time}")
                            with col3:
                                st.text(f"🏷️ {trigger_type}")
                                
                        except Exception as e:
                            st.error(f"❌ 读取触发器文件失败: {trigger_file.name}")
            else:
                st.success("✅ 暂无待处理的触发器文件")
        else:
            st.warning("⚠️ 触发器目录不存在")
            st.caption("将在首次使用时自动创建")
            
    except Exception as e:
        st.error(f"❌ 检查触发器状态失败: {e}")
    
    # 使用说明
    st.markdown("---")
    st.markdown("#### 💡 使用说明")
    st.markdown("""
    - **手动触发**: 立即执行对应的邮件发送任务，无视调度设置
    - **执行时间**: 触发器创建后，调度器会在30秒内检查并执行任务
    - **任务状态**: 任务执行后，可在"日志查看"标签页中查看详细执行日志
    - **前提条件**: 确保已添加相关订阅，否则不会发送邮件
    """)
    
    # 快速操作区
    st.markdown("#### ⚡ 快速操作")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 刷新状态", help="刷新触发器和调度器状态"):
            st.rerun()
    
    with col2:
        if st.button("🧹 清理触发器", help="清理所有待处理的触发器文件"):
            try:
                trigger_dir = Path(__file__).parent.parent.parent / "data" / "triggers"
                if trigger_dir.exists():
                    cleared_count = 0
                    for trigger_file in trigger_dir.glob("*.json"):
                        trigger_file.unlink()
                        cleared_count += 1
                    
                    if cleared_count > 0:
                        st.success(f"✅ 已清理 {cleared_count} 个触发器文件")
                    else:
                        st.info("📭 没有需要清理的触发器文件")
                else:
                    st.info("📁 触发器目录不存在")
                    
            except Exception as e:
                st.error(f"❌ 清理触发器失败: {e}")
    
    with col3:
        if st.button("📋 查看日志", help="快速跳转到日志查看"):
            st.session_state.jump_to_logs = True


def create_manual_trigger(trigger_type: str, trigger_data: Optional[Dict] = None) -> Optional[str]:
    """创建手动触发器文件"""
    try:
        # 获取项目根目录下的data/triggers目录
        project_root = Path(__file__).parent.parent.parent
        trigger_dir = project_root / "data" / "triggers"
        trigger_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成触发器文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        trigger_file = trigger_dir / f"trigger_{trigger_type}_{timestamp}.json"
        
        # 创建触发器数据
        default_trigger_data = {
            'type': trigger_type,
            'created_at': datetime.now().isoformat(),
            'source': 'web_ui'
        }
        
        # 合并传入的触发器数据
        if trigger_data:
            default_trigger_data.update(trigger_data)
        
        # 写入触发器文件
        with open(trigger_file, 'w', encoding='utf-8') as f:
            json.dump(default_trigger_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Web UI创建手动触发器: {trigger_file.name}")
        return str(trigger_file)
        
    except Exception as e:
        logger.error(f"❌ 创建手动触发器失败: {e}")
        return None


def render_scheduler_logs():
    """渲染调度器日志"""
    
    st.markdown("### 📄 调度器日志")
    
    # 添加标签页用于不同类型的日志
    log_tab1, log_tab2, log_tab3 = st.tabs(["📋 应用日志", "📊 运行报告", "📈 性能统计"])
    
    with log_tab1:
        # 原有的日志显示功能
        try:
            # 获取日志文件路径
            project_root = Path(__file__).parent.parent.parent
            log_file = project_root / "logs" / "tradingagents.log"
            
            if not log_file.exists():
                st.info("📭 暂无日志文件")
                return
            
            # 读取最后200行日志
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 只显示调度器相关的日志
            scheduler_lines = [
                line for line in lines[-500:]  # 最后500行
                if 'scheduler' in line.lower() or 'digest' in line.lower()
            ]
            
            if scheduler_lines:
                # 只显示最后50行调度器日志
                recent_logs = scheduler_lines[-50:]
                
                log_text = ''.join(recent_logs)
                st.text_area(
                    f"最近的调度器日志 ({len(recent_logs)} 行)",
                    value=log_text,
                    height=400,
                    key="scheduler_logs"
                )
            else:
                st.info("📭 暂无调度器相关日志")
        
        except Exception as e:
            st.error(f"❌ 读取日志失败: {e}")
    
    with log_tab2:
        # 显示运行报告
        try:
            # 动态导入运行报告管理器
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from tradingagents.utils.run_reporter import get_run_report_manager
            
            manager = get_run_report_manager()
            recent_reports = manager.get_recent_reports(20)
            
            if recent_reports:
                st.markdown("#### 最近的运行报告")
                
                # 创建报告数据表
                report_data = []
                for report in recent_reports:
                    status_icon = {
                        'completed': '✅',
                        'failed': '❌', 
                        'running': '⏳',
                        'cancelled': '🚫'
                    }.get(report.get('status', 'unknown'), '❓')
                    
                    duration = report.get('duration_seconds', 0)
                    duration_str = f"{duration:.1f}s" if duration else "未知"
                    
                    report_data.append({
                        "状态": f"{status_icon} {report.get('status', 'unknown')}",
                        "类型": report.get('trigger_type', 'unknown'),
                        "开始时间": report.get('start_time', '')[:19] if report.get('start_time') else '',
                        "持续时间": duration_str,
                        "订阅数": report.get('subscriptions_processed', 0),
                        "股票数": report.get('symbols_analyzed', 0),
                        "邮件发送": f"{report.get('emails_sent', 0)}/{report.get('emails_sent', 0) + report.get('emails_failed', 0)}",
                        "成本": f"¥{report.get('total_cost', 0):.2f}",
                        "错误数": len(report.get('errors', []))
                    })
                
                st.dataframe(report_data, use_container_width=True)
                
                # 显示详细报告选择器
                if report_data:
                    selected_report_idx = st.selectbox(
                        "选择报告查看详情",
                        options=range(len(recent_reports)),
                        format_func=lambda x: f"{recent_reports[x].get('trigger_type', 'unknown')} - {recent_reports[x].get('start_time', '')[:19]}",
                        key="selected_report"
                    )
                    
                    if selected_report_idx is not None:
                        selected_report = recent_reports[selected_report_idx]
                        
                        # 显示详细信息
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("**基本信息**")
                            st.text(f"运行ID: {selected_report.get('run_id', '')}")
                            st.text(f"类型: {selected_report.get('trigger_type', '')}")
                            st.text(f"状态: {selected_report.get('status', '')}")
                            st.text(f"开始时间: {selected_report.get('start_time', '')}")
                            st.text(f"结束时间: {selected_report.get('end_time', '')}")
                            
                        with col2:
                            st.markdown("**执行结果**")
                            st.text(f"处理订阅: {selected_report.get('subscriptions_processed', 0)}")
                            st.text(f"分析股票: {selected_report.get('symbols_analyzed', 0)}")
                            st.text(f"发送邮件: {selected_report.get('emails_sent', 0)}")
                            st.text(f"失败邮件: {selected_report.get('emails_failed', 0)}")
                            st.text(f"总成本: ¥{selected_report.get('total_cost', 0):.2f}")
                        
                        # 显示附件和错误信息
                        if selected_report.get('attachments_generated'):
                            st.markdown("**生成的附件**")
                            st.json(selected_report.get('attachments_generated', []))
                        
                        if selected_report.get('errors'):
                            st.markdown("**错误信息**")
                            for error in selected_report.get('errors', []):
                                st.error(error)
                        
                        if selected_report.get('performance_metrics'):
                            st.markdown("**性能指标**")
                            st.json(selected_report.get('performance_metrics', {}))
                    
            else:
                st.info("📭 暂无运行报告")
                
        except Exception as e:
            st.error(f"❌ 读取运行报告失败: {e}")
    
    with log_tab3:
        # 显示性能统计
        try:
            # 获取统计信息
            if 'manager' in locals():
                stats_7d = manager.get_statistics_summary(7)
                stats_30d = manager.get_statistics_summary(30)
                
                st.markdown("#### 📊 性能统计")
                
                # 显示统计信息
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**📅 最近7天**")
                    if stats_7d and 'error' not in stats_7d:
                        st.metric("总运行次数", stats_7d.get('total_runs', 0))
                        st.metric("成功率", f"{stats_7d.get('success_rate', 0):.1%}")
                        st.metric("平均持续时间", f"{stats_7d.get('average_duration', 0):.1f}秒")
                        st.metric("总邮件发送", stats_7d.get('total_emails_sent', 0))
                        st.metric("总成本", f"¥{stats_7d.get('total_cost', 0):.2f}")
                    else:
                        st.info("暂无7天统计数据")
                
                with col2:
                    st.markdown("**📅 最近30天**")
                    if stats_30d and 'error' not in stats_30d:
                        st.metric("总运行次数", stats_30d.get('total_runs', 0))
                        st.metric("成功率", f"{stats_30d.get('success_rate', 0):.1%}")
                        st.metric("平均持续时间", f"{stats_30d.get('average_duration', 0):.1f}秒")
                        st.metric("总邮件发送", stats_30d.get('total_emails_sent', 0))
                        st.metric("总成本", f"¥{stats_30d.get('total_cost', 0):.2f}")
                    else:
                        st.info("暂无30天统计数据")
                
                # 清理选项
                st.markdown("---")
                st.markdown("#### 🧹 维护操作")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("清理30天前的报告", help="删除30天前的旧运行报告"):
                        try:
                            cleaned_count = manager.cleanup_old_reports(30)
                            st.success(f"✅ 已清理 {cleaned_count} 个旧报告")
                        except Exception as e:
                            st.error(f"❌ 清理失败: {e}")
                
                with col2:
                    if st.button("刷新统计数据", help="重新计算统计信息"):
                        st.rerun()
                        
        except Exception as e:
            st.error(f"❌ 获取性能统计失败: {e}")


def get_scheduler_status() -> Dict:
    """获取调度器状态（模拟方法，实际应该通过API调用）"""
    
    # 在生产环境中，这里应该通过API调用获取真实的调度器状态
    # 现在我们提供一个基础的状态检查
    
    scheduler_enabled = os.getenv('SCHEDULER_ENABLED', 'false').lower() == 'true'
    
    if not scheduler_enabled:
        return {
            'running': False,
            'jobs': [],
            'total_jobs': 0,
            'timezone': os.getenv('SCHEDULER_TIMEZONE', 'Asia/Shanghai'),
            'error': '调度器未启用，请在.env中设置 SCHEDULER_ENABLED=true'
        }
    
    # 简单的状态检查
    try:
        import shutil
        docker_path = shutil.which('docker')

        # 如果系统未安装 docker，优雅降级为“不可用”而非报错
        if not docker_path:
            return {
                'running': False,
                'jobs': [],
                'total_jobs': 0,
                'timezone': os.getenv('SCHEDULER_TIMEZONE', 'Asia/Shanghai'),
                'docker_available': False,
                'note': '未检测到 Docker，可忽略此检查或使用本地调度器。'
            }

        # 检查是否有调度器进程在运行（Docker环境）
        import subprocess
        result = subprocess.run([docker_path, 'ps'], capture_output=True, text=True, timeout=5)
        scheduler_running = 'scheduler' in (result.stdout or '')

        return {
            'running': scheduler_running,
            'jobs': [
                {
                    'id': 'market_close_A股',
                    'name': 'A股收市报告',
                    'next_run_time': '2024-01-15T15:05:00+08:00',
                    'trigger': 'CronTrigger(hour=15, minute=5, timezone=Asia/Shanghai)'
                }
            ] if scheduler_running else [],
            'total_jobs': 1 if scheduler_running else 0,
            'timezone': os.getenv('SCHEDULER_TIMEZONE', 'Asia/Shanghai'),
            'docker_available': True
        }

    except FileNotFoundError:
        # 极端情况下 which 找到但执行失败，也做降级
        return {
            'running': False,
            'jobs': [],
            'total_jobs': 0,
            'timezone': os.getenv('SCHEDULER_TIMEZONE', 'Asia/Shanghai'),
            'docker_available': False,
            'note': '未检测到 Docker 命令，跳过容器状态检查。'
        }
    except Exception as e:
        # 其他错误保留信息，但不阻塞页面
        return {
            'running': False,
            'jobs': [],
            'total_jobs': 0,
            'timezone': os.getenv('SCHEDULER_TIMEZONE', 'Asia/Shanghai'),
            'warning': f'调度器状态检查受限: {e}'
        }


def render_scheduler_admin():
    """渲染完整的调度器管理界面"""
    
    st.markdown("## ⚙️ 调度与定时")
    
    # 检查调度功能是否启用
    scheduler_enabled = os.getenv('SCHEDULER_ENABLED', 'false').lower() == 'true'
    
    if not scheduler_enabled:
        st.warning("⚠️ 调度功能未启用")
        st.markdown("""
        **启用步骤：**
        1. 在项目根目录的 `.env` 文件中添加：`SCHEDULER_ENABLED=true`
        2. 重启Docker服务或应用程序
        
        **Docker重启命令：**
        ```bash
        docker compose restart scheduler
        ```
        """)
        return
    
    # 获取当前配置
    config_manager = ConfigManager()
    current_settings = config_manager.load_settings()
    
    # 获取调度器状态
    scheduler_status = get_scheduler_status()
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 状态监控",
        "⚙️ 调度配置", 
        "🚀 手动触发",
        "📄 日志查看"
    ])
    
    with tab1:
        render_scheduler_overview(scheduler_status)
    
    with tab2:
        # 调度配置编辑
        new_schedule_config = render_schedule_editor(current_settings)
        
        # 保存按钮
        if st.button("💾 保存调度配置", type="primary", key="save_scheduler_config"):
            # 合并新配置到现有设置
            updated_settings = current_settings.copy()
            updated_settings.update(new_schedule_config)
            
            try:
                config_manager.save_settings(updated_settings)
                st.success("✅ 调度配置已保存！")
                st.info("🔄 请重启调度器服务以应用新配置：\n```bash\ndocker compose restart scheduler\n```")
                
                # 重新加载页面以显示最新配置
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 保存配置失败: {e}")
    
    with tab3:
        render_manual_triggers()
    
    with tab4:
        render_scheduler_logs()


if __name__ == "__main__":
    # 用于独立测试
    st.set_page_config(
        page_title="调度器管理",
        page_icon="⚙️",
        layout="wide"
    )
    
    render_scheduler_admin()
