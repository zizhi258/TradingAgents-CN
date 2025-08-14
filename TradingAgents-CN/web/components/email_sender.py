"""
邮件发送组件
用于在分析结果页面发送分析报告邮件
"""

import streamlit as st
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import os
from datetime import datetime
from dotenv import load_dotenv

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('email_sender')

def render_email_sender(results):
    """渲染邮件发送组件"""
    
    if not results:
        return
    
    st.markdown("---")
    st.subheader("📧 发送分析报告")
    
    # 检查邮件配置
    smtp_user = os.getenv('SMTP_USER')
    smtp_host = os.getenv('SMTP_HOST')
    
    if not smtp_user or not smtp_host:
        st.warning("⚠️ 邮件服务未配置，无法发送报告")
        with st.expander("📋 配置说明"):
            st.markdown("""
            请在 `.env` 文件中配置邮件服务参数：
            ```
            SMTP_HOST=smtp.163.com
            SMTP_PORT=25
            SMTP_USER=your_email@163.com
            SMTP_PASS=your_authorization_code
            ```
            """)
        return
    
    # 创建邮件发送表单
    with st.form("email_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            recipient_email = st.text_input(
                "📧 收件人邮箱",
                placeholder="输入收件人邮箱地址",
                help="支持任何邮箱地址，如Gmail、QQ邮箱、Outlook等"
            )
        
        with col2:
            subject_template = f"📊 {results.get('stock_symbol', 'N/A')} 个股分析报告"
            email_subject = st.text_input(
                "📝 邮件主题",
                value=subject_template,
                help="可以自定义邮件主题"
            )
        
        # 邮件内容选项
        st.markdown("**📋 邮件内容选项：**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            include_summary = st.checkbox("📊 包含投资决策摘要", value=True)
        with col2:
            include_analysis = st.checkbox("📋 包含详细分析", value=True)
        with col3:
            include_config = st.checkbox("⚙️ 包含分析配置", value=False)
        
        # 附件选项
        with st.expander("📎 附件选项", expanded=False):
            st.markdown("**选择要添加到邮件的附件：**")
            
            col1, col2 = st.columns(2)
            with col1:
                attach_pdf = st.checkbox("📄 PDF分析报告", value=True, help="生成完整的PDF格式分析报告")
                attach_word = st.checkbox("📝 Word分析报告", value=False, help="生成可编辑的Word格式分析报告")
                attach_markdown = st.checkbox("📋 Markdown报告", value=False, help="生成纯文本格式的分析报告")
            with col2:
                # 暂时保留这些选项供将来扩展
                attach_charts = st.checkbox("📊 技术分析图表", value=False, help="添加技术指标图表（开发中）", disabled=True)
                attach_excel = st.checkbox("📈 数据Excel表", value=False, help="添加原始数据表格（开发中）", disabled=True)
                attach_images = st.checkbox("🖼️ 分析图片", value=False, help="添加分析摘要图片（开发中）", disabled=True)
        
        # 个性化消息
        personal_message = st.text_area(
            "💬 个性化消息 (可选)",
            placeholder="添加您想说的话...",
            height=80,
            help="将在邮件开头显示您的个人消息"
        )
        
        # 发送按钮
        send_button = st.form_submit_button("📤 立即发送邮件", type="primary")
        
        if send_button:
            if not recipient_email or not recipient_email.strip():
                st.error("❌ 请输入收件人邮箱地址")
            elif not _is_valid_email(recipient_email):
                st.error("❌ 请输入有效的邮箱地址格式")
            else:
                # 发送邮件
                with st.spinner("📤 正在发送邮件..."):
                    success, message = _send_analysis_email(
                        recipient_email=recipient_email.strip(),
                        subject=email_subject,
                        results=results,
                        include_summary=include_summary,
                        include_analysis=include_analysis,
                        include_config=include_config,
                        personal_message=personal_message.strip() if personal_message else None,
                        attach_pdf=attach_pdf,
                        attach_word=attach_word,
                        attach_markdown=attach_markdown
                    )
                
                if success:
                    st.success(f"✅ 邮件发送成功！已发送到：{recipient_email}")
                    st.balloons()
                    st.info("💡 请提醒收件人检查垃圾邮件文件夹")
                else:
                    st.error(f"❌ 邮件发送失败：{message}")

def _is_valid_email(email):
    """验证邮箱格式"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def _send_analysis_email(recipient_email, subject, results, include_summary=True, 
                        include_analysis=True, include_config=False, personal_message=None,
                        attach_pdf=False, attach_word=False, attach_markdown=False):
    """发送分析报告邮件"""
    
    try:
        # 使用新的EmailSender类
        from tradingagents.services.mailer.email_sender import EmailSender
        
        # 准备分析结果数据
        stock_symbol = results.get('stock_symbol', 'UNKNOWN')
        decision = results.get('decision', {})
        state = results.get('state', {})
        
        # 构建分析结果字典
        analysis_result = {
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'decision': decision,
            'full_analysis': state.get('market_report', '') + '\n\n' + 
                           state.get('fundamentals_report', '') + '\n\n' + 
                           state.get('sentiment_report', '') + '\n\n' +
                           state.get('news_report', '')
        }
        
        # 如果有个性化消息，添加到分析结果中
        if personal_message:
            analysis_result['personal_message'] = personal_message
        
        # 生成附件列表
        attachments = []
        
        if attach_pdf:
            attachments.append({
                'type': 'report',
                'format': 'pdf',
                'filename': f'{stock_symbol}_个股分析报告_{analysis_result["analysis_date"]}.pdf',
                'analysis_result': analysis_result,
                'stock_symbol': stock_symbol
            })
        
        if attach_word:
            attachments.append({
                'type': 'report',
                'format': 'docx',
                'filename': f'{stock_symbol}_个股分析报告_{analysis_result["analysis_date"]}.docx',
                'analysis_result': analysis_result,
                'stock_symbol': stock_symbol
            })
            
        if attach_markdown:
            attachments.append({
                'type': 'report',
                'format': 'md',
                'filename': f'{stock_symbol}_个股分析报告_{analysis_result["analysis_date"]}.md',
                'analysis_result': analysis_result,
                'stock_symbol': stock_symbol
            })
        
        # 使用EmailSender发送邮件
        sender = EmailSender()
        success = sender.send_analysis_report(
            recipients=[recipient_email],
            stock_symbol=stock_symbol,
            analysis_result=analysis_result,
            attachments=attachments if attachments else None
        )
        
        if success:
            # Count actual successful attachments from logs
            total_requested = len([a for a in [attach_pdf, attach_word, attach_markdown] if a])
            attachment_info = f"，请求发送{total_requested}个附件" if total_requested > 0 else ""
            logger.info(f"📧 [邮件发送] 分析报告已发送到: {recipient_email}{attachment_info}")
            return True, "邮件发送成功"
        else:
            return False, "邮件发送失败，请检查邮件配置"
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ [邮件发送] 发送失败: {error_msg}")
        return False, error_msg

def _generate_html_report(results, include_summary, include_analysis, include_config, personal_message):
    """生成HTML格式的分析报告"""
    
    stock_symbol = results.get('stock_symbol', 'N/A')
    decision = results.get('decision', {})
    state = results.get('state', {})
    
    # 基础HTML模板
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>{stock_symbol} 个股分析报告</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(90deg, #1f77b4, #ff7f0e); color: white; padding: 20px; text-align: center; border-radius: 10px; margin-bottom: 20px; }}
            .section {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #007bff; }}
            .metric {{ display: inline-block; margin: 10px 15px; padding: 10px; background: white; border-radius: 5px; text-align: center; min-width: 120px; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .metric-value {{ font-size: 18px; font-weight: bold; color: #333; }}
            .analysis-content {{ background: white; padding: 15px; border-radius: 5px; margin: 10px 0; border: 1px solid #dee2e6; }}
            .risk-warning {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; padding: 20px; border-top: 1px solid #eee; margin-top: 30px; }}
            .emoji {{ font-size: 20px; }}
            h1, h2, h3 {{ color: #2c3e50; }}
            .personal-message {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1><span class="emoji">📊</span> TradingAgents-CN 分析报告</h1>
            <h2>{stock_symbol} 个股分析结果</h2>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    """
    
    # 个性化消息
    if personal_message:
        html += f"""
        <div class="personal-message">
            <h3><span class="emoji">💬</span> 个人消息</h3>
            <p>{personal_message}</p>
        </div>
        """
    
    # 投资决策摘要
    if include_summary:
        action = decision.get('action', 'N/A')
        confidence = decision.get('confidence', 0)
        risk_score = decision.get('risk_score', 0)
        target_price = decision.get('target_price', 'N/A')
        
        # 转换投资建议
        action_translation = {'BUY': '买入', 'SELL': '卖出', 'HOLD': '持有'}
        chinese_action = action_translation.get(action.upper(), action)
        
        html += f"""
        <div class="section">
            <h2><span class="emoji">🎯</span> 投资决策摘要</h2>
            <div style="text-align: center;">
                <div class="metric">
                    <div class="metric-label">投资建议</div>
                    <div class="metric-value">{chinese_action}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">置信度</div>
                    <div class="metric-value">{confidence:.1%}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">风险评分</div>
                    <div class="metric-value">{risk_score:.1%}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">目标价位</div>
                    <div class="metric-value">{target_price if target_price != 'N/A' else '待分析'}</div>
                </div>
            </div>
        """
        
        if decision.get('reasoning'):
            html += f"""
            <div class="analysis-content">
                <h3><span class="emoji">🧠</span> AI分析推理</h3>
                <p>{decision['reasoning']}</p>
            </div>
            """
        
        html += "</div>"
    
    # 详细分析报告
    if include_analysis and state:
        html += f"""
        <div class="section">
            <h2><span class="emoji">📋</span> 详细分析报告</h2>
        """
        
        # 分析模块
        analysis_modules = [
            ('market_report', '📈', '市场技术分析'),
            ('fundamentals_report', '💰', '基本面分析'),
            ('sentiment_report', '💭', '市场情绪分析'),
            ('news_report', '📰', '新闻事件分析'),
            ('risk_assessment', '⚠️', '风险评估'),
            ('investment_plan', '📋', '投资建议')
        ]
        
        for key, emoji, title in analysis_modules:
            if key in state and state[key]:
                content = state[key]
                if isinstance(content, str) and content.strip():
                    html += f"""
                    <div class="analysis-content">
                        <h3><span class="emoji">{emoji}</span> {title}</h3>
                        <div>{content.replace(chr(10), '<br>')}</div>
                    </div>
                    """
        
        html += "</div>"
    
    # 分析配置信息
    if include_config:
        html += f"""
        <div class="section">
            <h2><span class="emoji">⚙️</span> 分析配置信息</h2>
            <div style="text-align: center;">
                <div class="metric">
                    <div class="metric-label">LLM提供商</div>
                    <div class="metric-value">{results.get('llm_provider', 'N/A')}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">AI模型</div>
                    <div class="metric-value">{results.get('llm_model', 'N/A')}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">分析师数量</div>
                    <div class="metric-value">{len(results.get('analysts', []))}个</div>
                </div>
            </div>
        </div>
        """
    
    # 风险提示
    html += f"""
    <div class="risk-warning">
        <h3><span class="emoji">⚠️</span> 重要风险提示</h3>
        <ul>
            <li><strong>仅供参考</strong>: 本分析结果仅供参考，不构成投资建议</li>
            <li><strong>投资风险</strong>: 股票投资有风险，可能导致本金损失</li>
            <li><strong>理性决策</strong>: 请结合多方信息进行理性投资决策</li>
            <li><strong>专业咨询</strong>: 重大投资决策建议咨询专业财务顾问</li>
            <li><strong>自担风险</strong>: 投资决策及其后果由投资者自行承担</li>
        </ul>
    </div>
    """
    
    # 页脚
    html += f"""
        <div class="footer">
            <p>此邮件由 TradingAgents-CN 智能交易分析系统自动生成</p>
            <p>如有疑问，请联系系统管理员</p>
            <p><strong>让AI为您的投资决策提供智能支持</strong> 💪</p>
        </div>
    </body>
    </html>
    """
    
    return html

def _generate_text_report(results, include_summary, include_analysis, include_config, personal_message):
    """生成纯文本格式的分析报告"""
    
    stock_symbol = results.get('stock_symbol', 'N/A')
    decision = results.get('decision', {})
    state = results.get('state', {})
    
    text = f"""
{stock_symbol} 个股分析报告
{'='*50}

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
生成系统: TradingAgents-CN 智能交易分析系统

"""
    
    # 个性化消息
    if personal_message:
        text += f"""
个人消息
{'-'*20}
{personal_message}

"""
    
    # 投资决策摘要
    if include_summary:
        action = decision.get('action', 'N/A')
        confidence = decision.get('confidence', 0)
        risk_score = decision.get('risk_score', 0)
        target_price = decision.get('target_price', 'N/A')
        
        # 转换投资建议
        action_translation = {'BUY': '买入', 'SELL': '卖出', 'HOLD': '持有'}
        chinese_action = action_translation.get(action.upper(), action)
        
        text += f"""
投资决策摘要
{'-'*20}
投资建议: {chinese_action}
置信度: {confidence:.1%}
风险评分: {risk_score:.1%}
目标价位: {target_price if target_price != 'N/A' else '待分析'}

"""
        
        if decision.get('reasoning'):
            text += f"""
AI分析推理:
{decision['reasoning']}

"""
    
    # 详细分析报告
    if include_analysis and state:
        text += f"""
详细分析报告
{'-'*20}

"""
        
        analysis_modules = [
            ('market_report', '市场技术分析'),
            ('fundamentals_report', '基本面分析'),
            ('sentiment_report', '市场情绪分析'),
            ('news_report', '新闻事件分析'),
            ('risk_assessment', '风险评估'),
            ('investment_plan', '投资建议')
        ]
        
        for key, title in analysis_modules:
            if key in state and state[key]:
                content = state[key]
                if isinstance(content, str) and content.strip():
                    text += f"""
{title}:
{content}

"""
    
    # 分析配置信息
    if include_config:
        text += f"""
分析配置信息
{'-'*20}
LLM提供商: {results.get('llm_provider', 'N/A')}
AI模型: {results.get('llm_model', 'N/A')}
分析师数量: {len(results.get('analysts', []))}个

"""
    
    # 风险提示
    text += f"""
重要风险提示
{'='*50}
• 仅供参考: 本分析结果仅供参考，不构成投资建议
• 投资风险: 股票投资有风险，可能导致本金损失
• 理性决策: 请结合多方信息进行理性投资决策
• 专业咨询: 重大投资决策建议咨询专业财务顾问
• 自担风险: 投资决策及其后果由投资者自行承担

{'='*50}
此邮件由 TradingAgents-CN 智能交易分析系统自动生成
如有疑问，请联系系统管理员
让AI为您的投资决策提供智能支持 💪
"""
    
    return text
