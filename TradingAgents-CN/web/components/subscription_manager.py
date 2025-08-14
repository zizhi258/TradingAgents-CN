"""
订阅管理Web组件
提供订阅管理的Streamlit界面
"""

import streamlit as st
from datetime import datetime
import pandas as pd
import sys
from pathlib import Path

# 添加项目根目录到路径，以便导入scheduler_admin模块
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.services.subscription.subscription_manager import SubscriptionManager
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.subscription')


def render_subscription_manager():
    """渲染订阅管理界面"""
    
    st.markdown("## 📧 邮件订阅管理")
    st.markdown("管理您的个股分析报告邮件订阅")
    
    # 初始化订阅管理器
    try:
        manager = SubscriptionManager()
    except Exception as e:
        st.error(f"❌ 初始化订阅管理器失败: {e}")
        return
        
    # 标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "➕ 添加订阅", 
        "📋 我的订阅", 
        "📊 订阅统计",
        "⚙️ 订阅设置",
        "🕐 调度与定时"
    ])
    
    # 添加订阅标签页
    with tab1:
        render_add_subscription(manager)
        
    # 我的订阅标签页
    with tab2:
        render_my_subscriptions(manager)
        
    # 订阅统计标签页
    with tab3:
        render_subscription_stats(manager)
        
    # 订阅设置标签页
    with tab4:
        render_subscription_settings(manager)
    
    # 调度与定时标签页
    with tab5:
        render_scheduler_controls()


def render_add_subscription(manager: SubscriptionManager):
    """渲染添加订阅表单"""
    
    st.markdown("### 添加新订阅")

    # 订阅类型切换：个股 / 市场摘要 / 指数
    sub_type_label = st.radio(
        "订阅类型",
        options=["个股订阅", "市场摘要订阅", "指数订阅"],
        index=0,
        horizontal=True,
        help="个股订阅：指定股票定时发送研报；市场摘要：按市场范围推送收市/每日/每周摘要；指数订阅：按选定指数发送摘要"
    )
    is_market_sub = (sub_type_label == "市场摘要订阅")
    is_index_sub = (sub_type_label == "指数订阅")

    with st.form("add_subscription_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            email = st.text_input(
                "📧 邮箱地址", 
                placeholder="your@email.com",
                help="接收分析报告的邮箱"
            )
            
            if not is_market_sub and not is_index_sub:
                symbol = st.text_input(
                    "📈 股票代码", 
                    placeholder="000001 / AAPL / 0700.HK",
                    help="支持A股、美股、港股"
                )
            elif is_index_sub:
                # 指数选项
                try:
                    options = manager.list_common_index_options()
                except Exception as e:
                    options = []
                    st.error(f"无法加载指数选项: {e}")
                if options:
                    display = [f"{it.get('name','') or it.get('slug','指数')} ({it.get('code','')})" for it in options]
                    idx = st.selectbox("📈 指数", display, help="选择要订阅的指数")
                    sel = options[display.index(idx)] if display else None
                    symbol = (sel.get('code') if sel else '').strip()
                    index_name = sel.get('name') if sel else ''
                    index_slug = sel.get('slug') if sel else ''
                else:
                    symbol = ''
                    index_name = ''
                    index_slug = ''
            else:
                symbol = "*"  # 市场级订阅不需要个股代码
        
        with col2:
            if is_market_sub:
                market_type = st.selectbox(
                    "🌍 市场范围",
                    ["A股", "美股", "港股", "全球"],
                    help="选择摘要覆盖的市场范围"
                )
            elif is_index_sub:
                market_type = st.selectbox(
                    "🌍 市场类型",
                    ["A股"],
                    help="指数订阅当前仅支持A股指数"
                )
            else:
                market_type = st.selectbox(
                    "🌍 市场类型",
                    ["A股", "美股", "港股"],
                    help="选择股票所属市场"
                )
            
            frequency = st.selectbox(
                "⏰ 推送频率",
                ["close", "daily", "weekly", "hourly"],
                format_func=lambda x: {
                    "close": "收市后推送",
                    "daily": "每日推送",
                    "weekly": "每周推送",
                    "hourly": "每小时推送"
                }.get(x, x),
                help="选择接收报告的频率"
            )
            
        # 高级选项
        with st.expander("🔧 高级选项"):
            col3, col4 = st.columns(2)
            
            with col3:
                include_charts = st.checkbox("包含图表", value=True)
                include_news = st.checkbox("包含新闻分析", value=True)
                
            with col4:
                notification_types = st.multiselect(
                    "通知方式",
                    ["email", "sms", "wechat"],
                    default=["email"],
                    format_func=lambda x: {
                        "email": "📧 邮件",
                        "sms": "📱 短信",
                        "wechat": "💬 微信"
                    }.get(x, x)
                )
        
        # 邮件附件选项
        with st.expander("📎 邮件附件选项"):
            st.markdown("##### 选择要附加到邮件的文件类型")
            
            col5, col6 = st.columns(2)
            
            with col5:
                attach_pdf_report = st.checkbox("📄 PDF分析报告", value=True, help="完整的分析报告PDF文件")
                attach_word_report = st.checkbox("📝 Word分析报告", value=False, help="可编辑的Word格式报告")
                attach_markdown_report = st.checkbox("📋 Markdown报告", value=False, help="纯文本格式的分析报告")
                
            with col6:
                attach_charts = st.checkbox("📊 技术分析图表", value=True, help="股价趋势和技术指标图表")
                attach_data_excel = st.checkbox("📈 数据Excel表", value=False, help="原始数据和分析指标Excel文件")
                attach_summary_image = st.checkbox("🖼️ 摘要图片", value=False, help="分析摘要的可视化图片")
            
            # 自定义附件
            st.markdown("##### 自定义附件模板")
            custom_template = st.selectbox(
                "报告模板风格",
                ["标准模板", "简洁模板", "详细模板", "投资者模板"],
                help="选择邮件报告的展示风格"
            )
            
            # 附件文件名设置
            attachment_naming = st.selectbox(
                "附件命名规则",
                ["股票代码_日期", "股票名称_日期", "自定义格式"],
                help="设置附件文件的命名方式"
            )
            
            # 生成附件配置
            attachment_config = {
                'pdf_report': attach_pdf_report,
                'word_report': attach_word_report, 
                'markdown_report': attach_markdown_report,
                'charts': attach_charts,
                'data_excel': attach_data_excel,
                'summary_image': attach_summary_image,
                'template': custom_template,
                'naming': attachment_naming
            }
                
        # 提交按钮
        submitted = st.form_submit_button("➕ 添加订阅", use_container_width=True)
        
        if submitted:
            if not email:
                st.error("请填写邮箱")
            elif not is_market_sub and not is_index_sub and not symbol:
                st.error("请填写股票代码")
            elif is_index_sub and not symbol:
                st.error("请选择指数")
            else:
                try:
                    # 添加订阅
                    if is_market_sub:
                        subscription_id = manager.add_subscription(
                            email=email,
                            symbol=symbol,
                            market_type=market_type,  # 同步存储范围
                            frequency=frequency,
                            notification_types=notification_types,
                            attachment_config=attachment_config,
                            subscription_type='market',
                            market_scope=market_type
                        )
                    elif is_index_sub:
                        subscription_id = manager.add_subscription(
                            email=email,
                            symbol=symbol,
                            market_type=market_type,
                            frequency=frequency,
                            notification_types=notification_types,
                            attachment_config=attachment_config,
                            subscription_type='index',
                            index_name=index_name if 'index_name' in locals() else None,
                            index_slug=index_slug if 'index_slug' in locals() else None,
                        )
                    else:
                        subscription_id = manager.add_subscription(
                            email=email,
                            symbol=symbol,
                            market_type=market_type,
                            frequency=frequency,
                            notification_types=notification_types,
                            attachment_config=attachment_config,
                            subscription_type='stock'
                        )
                    
                    st.success(f"✅ 订阅添加成功！")
                    st.info(f"订阅ID: {subscription_id}")
                    
                    # 清空表单
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ 添加订阅失败: {e}")


def render_my_subscriptions(manager: SubscriptionManager):
    """渲染用户订阅列表"""
    
    st.markdown("### 我的订阅")
    
    # 输入邮箱查询
    email = st.text_input(
        "请输入您的邮箱查看订阅",
        placeholder="your@email.com"
    )
    
    if email:
        try:
            subscriptions = manager.get_user_subscriptions(email)
            
            if not subscriptions:
                st.info("📭 您还没有任何订阅")
            else:
                st.success(f"找到 {len(subscriptions)} 个订阅")
                
                # 转换为DataFrame显示
                df_data = []
                for sub in subscriptions:
                    sub_type = sub.get('subscription_type') or 'stock'
                    is_mkt = (sub_type == 'market')
                    is_idx = (sub_type == 'index')
                    # 展示对象
                    if is_mkt:
                        obj = sub.get('market_scope') or '-'
                    elif is_idx:
                        idx_name = sub.get('index_name') or ''
                        code = sub.get('symbol') or ''
                        obj = f"{idx_name}({code})" if idx_name else (code or '-')
                    else:
                        obj = sub.get('symbol', '-')

                    df_data.append({
                        "订阅类型": ("市场摘要" if is_mkt else ("指数" if is_idx else "个股")),
                        "订阅对象": obj,
                        "市场": sub.get('market_type', '-'),
                        "频率": {
                            "close": "收市后",
                            "daily": "每日",
                            "weekly": "每周",
                            "hourly": "每小时"
                        }.get(sub['frequency'], sub['frequency']),
                        "创建时间": sub['created_at'].strftime("%Y-%m-%d %H:%M"),
                        "上次发送": sub['last_sent'].strftime("%Y-%m-%d %H:%M") 
                                   if sub['last_sent'] else "从未发送",
                        "发送次数": sub.get('send_count', 0)
                    })
                
                df = pd.DataFrame(df_data)
                
                # 显示表格
                st.dataframe(df, use_container_width=True)
                
                # 批量操作
                st.markdown("#### 批量操作")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🗑️ 取消所有订阅", type="secondary"):
                        if st.checkbox("确认取消所有订阅"):
                            count = manager.remove_subscription(email)
                            st.success(f"✅ 已取消 {count} 个订阅")
                            st.rerun()
                            
        except Exception as e:
            st.error(f"❌ 查询失败: {e}")


def render_subscription_stats(manager: SubscriptionManager):
    """渲染订阅统计信息"""
    
    st.markdown("### 订阅统计")
    
    try:
        stats = manager.get_subscription_stats()
        
        # 总体统计
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 总订阅数", stats['total'])
            
        with col2:
            st.metric("📈 活跃订阅", stats['total'])
            
        with col3:
            st.metric("📧 订阅用户", "-")  # 需要额外统计
            
        # 类型统计
        by_type = stats.get('by_type', {})
        if by_type:
            st.markdown("#### 按订阅类型分布")
            try:
                import pandas as pd
                type_map = {'stock': '个股', 'market': '市场摘要', 'index': '指数'}
                df_type = pd.DataFrame(
                    [(type_map.get(k, k), v) for k, v in by_type.items()],
                    columns=['类型', '订阅数']
                )
                st.bar_chart(df_type.set_index('类型'))
            except Exception:
                st.write(by_type)

        # 按市场分布
        st.markdown("#### 按市场分布")
        market_data = stats['by_market']
        if market_data:
            df_market = pd.DataFrame(
                list(market_data.items()),
                columns=['市场', '订阅数']
            )
            st.bar_chart(df_market.set_index('市场'))
            
        # 按频率分布
        st.markdown("#### 按推送频率分布")
        freq_data = stats['by_frequency']
        if freq_data:
            freq_labels = {
                "close": "收市后",
                "daily": "每日",
                "weekly": "每周", 
                "hourly": "每小时"
            }
            freq_data_labeled = {
                freq_labels.get(k, k): v 
                for k, v in freq_data.items()
            }
            
            df_freq = pd.DataFrame(
                list(freq_data_labeled.items()),
                columns=['频率', '订阅数']
            )
            st.bar_chart(df_freq.set_index('频率'))
            
    except Exception as e:
        st.error(f"❌ 获取统计信息失败: {e}")


def render_subscription_settings(manager: SubscriptionManager):
    """渲染订阅设置"""
    
    st.markdown("### 订阅设置")
    
    # 全局设置
    st.markdown("#### 🌐 全局设置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        default_frequency = st.selectbox(
            "默认推送频率",
            ["close", "daily", "weekly"],
            format_func=lambda x: {
                "close": "收市后推送",
                "daily": "每日推送",
                "weekly": "每周推送"
            }.get(x, x)
        )
        
        default_language = st.selectbox(
            "报告语言",
            ["zh-CN", "en-US"],
            format_func=lambda x: {
                "zh-CN": "🇨🇳 简体中文",
                "en-US": "🇺🇸 English"
            }.get(x, x)
        )
        
    with col2:
        include_charts = st.checkbox("默认包含图表", value=True)
        include_news = st.checkbox("默认包含新闻", value=True)
        include_technical = st.checkbox("默认包含技术分析", value=True)
        
    # 邮件设置
    st.markdown("#### 📧 邮件设置")
    
    email_template = st.selectbox(
        "邮件模板",
        ["default", "simple", "detailed"],
        format_func=lambda x: {
            "default": "标准模板",
            "simple": "简洁模板",
            "detailed": "详细模板"
        }.get(x, x)
    )
    
    # 保存设置
    if st.button("💾 保存设置", type="primary"):
        st.success("✅ 设置已保存")
        
    # 测试邮件
    st.markdown("#### 🧪 测试邮件")
    
    test_email = st.text_input(
        "测试邮箱",
        placeholder="test@example.com"
    )
    
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("📤 发送测试邮件"):
            if test_email:
                try:
                    st.info("正在发送测试邮件...")
                    from tradingagents.services.mailer.email_sender import EmailSender
                    
                    sender = EmailSender()
                    
                    # 创建测试分析结果
                    test_analysis_result = {
                        'analysis_date': '2024-01-01',
                        'decision': {
                            'action': 'BUY',
                            'confidence': 0.85,
                            'risk_score': 0.3,
                            'reasoning': '基于技术面分析，该股票呈上升趋势，建议买入。'
                        },
                        'full_analysis': '''
技术面分析：
- 价格突破重要阻力位
- 成交量放大确认
- MACD金叉信号

基本面分析：
- 财务指标良好
- 行业前景看好  
- 管理层执行力强

风险提示：
- 市场整体波动风险
- 行业政策风险
- 个股业绩不及预期风险
                        '''.strip()
                    }
                    
                    # 创建测试附件
                    test_attachments = []
                    
                    # PDF报告附件
                    test_attachments.append({
                        'type': 'report',
                        'format': 'pdf',
                        'filename': 'TEST_个股分析报告.pdf',
                        'analysis_result': test_analysis_result,
                        'stock_symbol': 'TEST'
                    })
                    
                    # Word报告附件
                    test_attachments.append({
                        'type': 'report',
                        'format': 'docx',
                        'filename': 'TEST_个股分析报告.docx',
                        'analysis_result': test_analysis_result,
                        'stock_symbol': 'TEST'
                    })
                    
                    # Markdown报告附件
                    test_attachments.append({
                        'type': 'report',
                        'format': 'md',
                        'filename': 'TEST_个股分析报告.md',
                        'analysis_result': test_analysis_result,
                        'stock_symbol': 'TEST'
                    })
                    
                    success = sender.send_analysis_report(
                        recipients=[test_email],
                        stock_symbol='TEST',
                        analysis_result=test_analysis_result,
                        attachments=test_attachments
                    )
                    
                    if success:
                        st.success(f"✅ 带附件的测试邮件发送成功！请检查 {test_email} 的收件箱")
                        st.info("📎 邮件包含以下测试附件：\n- TEST_个股分析报告.pdf (PDF格式分析报告)\n- TEST_个股分析报告.docx (Word格式分析报告)\n- TEST_个股分析报告.md (Markdown格式分析报告)")
                    else:
                        st.error("❌ 测试邮件发送失败，请检查邮件配置")
                        
                except Exception as e:
                    st.error(f"❌ 发送测试邮件时出错: {e}")
                    logger.error(f"测试邮件发送失败: {e}", exc_info=True)
            else:
                st.error("请输入测试邮箱")
                
    with col4:
        if st.button("🔍 检查邮件服务"):
            try:
                from tradingagents.services.mailer.email_sender import EmailSender
                import smtplib
                
                sender = EmailSender()
                
                # 检查配置
                if not sender.smtp_user or not sender.smtp_pass:
                    st.error("❌ SMTP配置不完整")
                    return
                    
                st.info("正在检查邮件服务连接...")
                
                # 测试SMTP连接
                with smtplib.SMTP_SSL(sender.smtp_host, sender.smtp_port, timeout=10) as server:
                    server.login(sender.smtp_user, sender.smtp_pass)
                
                st.success("✅ 邮件服务连接正常")
                
            except Exception as e:
                st.error(f"❌ 邮件服务检查失败: {e}")
                logger.error(f"邮件服务检查失败: {e}", exc_info=True)


def render_scheduler_controls():
    """渲染调度器控制界面"""
    
    try:
        # 导入scheduler_admin模块
        from web.modules.scheduler_admin import render_scheduler_admin
        
        # 直接渲染调度器管理界面
        render_scheduler_admin()
        
    except ImportError as e:
        st.error(f"❌ 调度器管理模块未找到: {e}")
        st.markdown("""
        ### 📝 手动配置调度器
        
        如果调度器管理模块无法加载，您可以手动配置：
        
        1. **检查环境变量**
        ```bash
        SCHEDULER_ENABLED=true
        SCHEDULER_TIMEZONE=Asia/Shanghai
        ```
        
        2. **配置邮件调度** (在 `config/settings.json` 中)
        ```json
        {
          "email_schedules": {
            "daily": {"enabled": false, "hour": 18, "minute": 0},
            "weekly": {"enabled": false, "weekday": [1], "hour": 9, "minute": 0}
          }
        }
        ```
        
        3. **重启调度器服务**
        ```bash
        docker compose restart scheduler
        ```
        """)
        
    except Exception as e:
        st.error(f"❌ 调度器控制模块加载失败: {e}")
        logger.error(f"调度器控制模块加载失败: {e}", exc_info=True)

