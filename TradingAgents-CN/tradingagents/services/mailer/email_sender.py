#!/usr/bin/env python3
"""
邮件发送服务
支持SMTP和HTTP API两种发送方式
"""

import json
import os
import smtplib
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape as _html_escape
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader

try:
    # 仅用于清理分析结果中可能含有的 $ 分隔符，避免下游渲染器误判数学环境
    from web.utils.markdown_sanitizer import (
        sanitize_markdown_for_streamlit as _sanitize_md,
    )
except Exception:

    def _sanitize_md(s: str) -> str:  # type: ignore
        return s


from tradingagents.utils.logging_manager import get_logger

logger = get_logger("mailer")


class EmailSender:
    """邮件发送服务 - 支持SMTP和HTTP API"""

    def __init__(self):
        """初始化邮件发送器"""
        # 从环境变量读取配置
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.qq.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.sender_name = os.getenv("SENDER_NAME", "TradingAgents研报系统")

        # Brevo HTTP API 配置
        self.brevo_api_key = os.getenv("BREVO_API_KEY")
        self.use_http_api = os.getenv("BREVO_USE_HTTP_API", "false").lower() == "true"

        # 选择发送方式
        if self.use_http_api and self.brevo_api_key:
            logger.info("📧 使用Brevo HTTP API发送邮件 (绕过DNS劫持)")
        elif self.smtp_user and self.smtp_pass:
            logger.info("📧 使用SMTP发送邮件")
        else:
            logger.warning("⚠️ 邮件配置不完整")

        # 加载邮件模板
        template_dir = Path(__file__).parent / "templates"
        if template_dir.exists():
            self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        else:
            self.jinja_env = None
            logger.warning(f"⚠️ 邮件模板目录不存在: {template_dir}")

    def send_analysis_report(
        self,
        recipients: list[str],
        stock_symbol: str,
        analysis_result: dict,
        attachments: list[dict] | None = None,
    ) -> bool:
        """发送分析报告邮件"""

        # 选择发送方式
        if self.use_http_api and self.brevo_api_key:
            return self._send_via_http_api(recipients, stock_symbol, analysis_result)
        else:
            return self._send_via_smtp(
                recipients, stock_symbol, analysis_result, attachments
            )

    def _send_via_http_api(
        self, recipients: list[str], stock_symbol: str, analysis_result: dict
    ) -> bool:
        """通过HTTP API发送邮件"""
        try:
            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": self.brevo_api_key,
            }

            # 构建邮件数据
            email_data = {
                "sender": {
                    "name": self.sender_name,
                    "email": self.smtp_user or "noreply@tradingagents.local",
                },
                "to": [
                    {"email": email, "name": email.split("@")[0]}
                    for email in recipients
                ],
                "subject": f"【{stock_symbol}】股票分析报告 - {analysis_result.get('analysis_date', '')}",
                "htmlContent": self._create_simple_html(stock_symbol, analysis_result),
            }

            # 发送请求
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers=headers,
                data=json.dumps(email_data),
                timeout=30,
            )

            if response.status_code == 201:
                result = response.json()
                message_id = result.get("messageId", "")
                logger.info(
                    f"✅ HTTP API邮件发送成功: {stock_symbol} -> {', '.join(recipients)}"
                )
                logger.info(f"📨 MessageID: {message_id}")
                return True
            else:
                logger.error(f"❌ HTTP API邮件发送失败: {response.status_code}")
                logger.error(f"错误详情: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ HTTP API邮件发送异常: {e}")
            return False

    def _send_via_smtp(
        self,
        recipients: list[str],
        stock_symbol: str,
        analysis_result: dict,
        attachments: list[dict] | None = None,
    ) -> bool:
        """通过SMTP发送邮件"""
        if not self.smtp_user or not self.smtp_pass:
            logger.error("❌ 邮件配置不完整，无法发送邮件")
            return False

        try:
            # 构建邮件内容
            if self.jinja_env:
                # 使用模板
                try:
                    template = self.jinja_env.get_template("analysis_report.html")

                    # 对关键字段进行预处理：恢复 $ 并转义HTML
                    def _prep_text(txt: str) -> str:
                        if txt is None:
                            return ""
                        cleaned = _sanitize_md(str(txt)).replace("\\$", "$")
                        return _html_escape(cleaned)

                    _decision = dict(analysis_result.get("decision", {}) or {})
                    if "reasoning" in _decision:
                        _decision["reasoning"] = _prep_text(_decision.get("reasoning"))
                    html_content = template.render(
                        stock_symbol=stock_symbol,
                        analysis_date=analysis_result.get("analysis_date", ""),
                        decision=_decision,
                        full_analysis=_prep_text(
                            analysis_result.get("full_analysis", "")
                        ),
                    )
                except Exception as e:
                    logger.warning(f"⚠️ 模板渲染失败，使用简单格式: {e}")
                    html_content = self._create_simple_html(
                        stock_symbol, analysis_result
                    )
            else:
                # 使用简单HTML
                html_content = self._create_simple_html(stock_symbol, analysis_result)

            # 构建邮件
            msg = MIMEMultipart("mixed")

            # 严格按照RFC标准设置邮件头 - 最兼容的方式
            sender_email = self.smtp_user
            sender_display_name = self.sender_name

            # 最兼容的From字段格式
            # 优先使用纯邮箱地址，避免编码问题导致的退信
            if sender_display_name and sender_display_name != sender_email:
                # 检查是否包含中文字符
                try:
                    sender_display_name.encode("ascii")
                    # 纯ASCII字符，使用标准格式
                    from_field = f'"{sender_display_name}" <{sender_email}>'
                except UnicodeEncodeError:
                    # 包含中文字符，为了最大兼容性，只使用邮箱地址
                    logger.info(
                        "📧 发件人名称包含中文字符，使用纯邮箱地址格式以确保兼容性"
                    )
                    from_field = sender_email
            else:
                from_field = sender_email

            msg["From"] = from_field
            msg["To"] = ", ".join(recipients)

            # 主题也采用最兼容的方式
            subject = f'[{stock_symbol}] Stock Analysis Report - {analysis_result.get("analysis_date", "")}'
            msg["Subject"] = subject

            # 添加必需的邮件头
            msg["Reply-To"] = sender_email
            msg["Return-Path"] = sender_email
            msg["X-Mailer"] = "TradingAgents-CN v1.0"
            msg["X-Priority"] = "3"

            # 生成符合RFC标准的Message-ID
            import hashlib
            import time

            timestamp = str(int(time.time()))
            unique_id = hashlib.md5(
                f"{timestamp}{sender_email}{stock_symbol}".encode()
            ).hexdigest()[:8]
            domain = (
                sender_email.split("@")[-1]
                if "@" in sender_email
                else "tradingagents.local"
            )
            msg["Message-ID"] = f"<{timestamp}.{unique_id}@{domain}>"

            # 设置日期头
            from email.utils import formatdate

            msg["Date"] = formatdate(localtime=True)

            # 添加HTML正文
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 添加附件
            successful_attachments = 0
            if attachments:
                for attachment in attachments:
                    if self._add_attachment(msg, attachment):
                        successful_attachments += 1

            # 发送邮件 - 增强错误处理和重试机制
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if self.smtp_port == 465:
                        # SSL连接
                        with smtplib.SMTP_SSL(
                            self.smtp_host, self.smtp_port, timeout=60
                        ) as server:
                            server.set_debuglevel(0)  # 关闭调试输出
                            server.login(self.smtp_user, self.smtp_pass)
                            server.send_message(msg)
                    else:
                        # TLS连接 - Brevo推荐配置
                        with smtplib.SMTP(
                            self.smtp_host, self.smtp_port, timeout=60
                        ) as server:
                            server.set_debuglevel(0)  # 关闭调试输出
                            server.ehlo()  # 标识客户端
                            server.starttls()  # 启用TLS
                            server.ehlo()  # TLS后重新标识
                            server.login(self.smtp_user, self.smtp_pass)
                            server.send_message(msg)

                    logger.info(
                        f"✅ 邮件发送成功: {stock_symbol} -> {', '.join(recipients)}"
                    )
                    if successful_attachments > 0:
                        logger.info(f"📎 成功添加 {successful_attachments} 个附件")
                    return True

                except (
                    smtplib.SMTPConnectError,
                    smtplib.SMTPServerDisconnected,
                    ConnectionError,
                ) as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ 邮件发送失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                        )
                        import time

                        time.sleep(2**attempt)  # 指数退避
                        continue
                    else:
                        logger.error(
                            f"❌ 邮件发送最终失败 (已重试 {max_retries} 次): {e}"
                        )
                        return False

                except smtplib.SMTPAuthenticationError as e:
                    logger.error(f"❌ SMTP认证失败: {e}")
                    logger.error("💡 请检查SMTP用户名和密钥是否正确")
                    return False

                except Exception as e:
                    logger.error(f"❌ 邮件发送未知错误: {e}")
                    return False

        except Exception as e:
            logger.error(f"❌ 邮件发送失败: {e}")
            return False

    def _create_simple_html(self, stock_symbol: str, analysis_result: dict) -> str:
        """创建简单的HTML邮件内容"""
        decision = analysis_result.get("decision", {})

        # 预处理文本（邮件客户端不运行KaTeX，恢复\$为$，并进行HTML转义以防注入）
        def _prep_text(txt: str) -> str:
            if txt is None:
                return ""
            cleaned = _sanitize_md(str(txt)).replace("\\$", "$")
            return _html_escape(cleaned)

        html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .metric {{ display: inline-block; margin: 10px 20px; }}
                .metric-label {{ font-size: 14px; color: #666; }}
                .metric-value {{ font-size: 24px; font-weight: bold; }}
                .disclaimer {{ background-color: #fff3cd; padding: 15px; margin-top: 20px; border: 1px solid #ffeaa7; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>[{stock_symbol}] Stock Analysis Report</h1>
                    <p>Analysis Date: {analysis_result.get('analysis_date', '')}</p>
                </div>
                
                <div class="content">
                    <h2>Investment Decision Summary</h2>
                    
                    <div class="metric">
                        <div class="metric-label">Recommendation</div>
                        <div class="metric-value">{decision.get('action', 'N/A')}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Confidence</div>
                        <div class="metric-value">{decision.get('confidence', 0):.1%}</div>
                    </div>
                    
                    <div class="metric">
                        <div class="metric-label">Risk Score</div>
                        <div class="metric-value">{decision.get('risk_score', 0):.1%}</div>
                    </div>
                    
                    <h3>Key Analysis</h3>
                    <p>{_prep_text(decision.get('reasoning', 'No analysis available'))}</p>
                    
                    <h3>Detailed Analysis</h3>
                    <pre style="white-space: pre-wrap;">{_prep_text(analysis_result.get('full_analysis', 'No detailed analysis available'))}</pre>
                    
                    <div class="disclaimer">
                        <strong>Important Notice</strong><br>
                        This report is generated by TradingAgents-CN system for reference only. Not investment advice.
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        return html

    def _add_attachment(self, msg: MIMEMultipart, attachment: dict) -> bool:
        """添加附件到邮件

        Args:
            msg: 邮件对象
            attachment: 附件信息字典，包含以下键：
                - type: 附件类型 ('file', 'content', 'report')
                - filename: 文件名
                - content: 文件内容（字节）
                - path: 文件路径（仅当type='file'时）
                - format: 报告格式（仅当type='report'时，如'pdf', 'docx', 'md'）

        Returns:
            bool: 是否成功添加附件
        """
        try:
            attachment_type = attachment.get("type", "content")
            filename = attachment.get("filename", "attachment")

            if attachment_type == "file":
                # 从文件路径读取
                file_path = attachment.get("path")
                if file_path and os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        content = f.read()
                else:
                    logger.warning(f"⚠️ 附件文件不存在: {file_path}")
                    return False
            elif attachment_type == "content":
                # 直接使用提供的内容
                content = attachment.get("content")
                if not content:
                    logger.warning("⚠️ 附件内容为空")
                    return False
            elif attachment_type == "report":
                # 生成分析报告附件
                content = self._generate_report_attachment(attachment)
                if not content:
                    logger.warning("⚠️ 生成报告附件失败")
                    return False
            else:
                logger.warning(f"⚠️ 不支持的附件类型: {attachment_type}")
                return False

            # 根据文件扩展名确定MIME类型
            file_ext = filename.split(".")[-1].lower()

            if file_ext in ["jpg", "jpeg", "png", "gif", "bmp"]:
                # 图片附件
                part = MIMEImage(content)
                part.add_header("Content-Disposition", "attachment", filename=filename)
            elif file_ext in ["pdf"]:
                # PDF附件
                part = MIMEApplication(content, _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename=filename)
            elif file_ext in ["docx", "doc"]:
                # Word文档
                part = MIMEApplication(
                    content,
                    _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
                part.add_header("Content-Disposition", "attachment", filename=filename)
            elif file_ext in ["xlsx", "xls"]:
                # Excel文档
                part = MIMEApplication(
                    content,
                    _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                part.add_header("Content-Disposition", "attachment", filename=filename)
            elif file_ext in ["txt", "md"]:
                # 文本文件
                part = MIMEText(
                    content.decode("utf-8") if isinstance(content, bytes) else content,
                    "plain",
                    "utf-8",
                )
                part.add_header("Content-Disposition", "attachment", filename=filename)
            else:
                # 默认二进制附件
                part = MIMEBase("application", "octet-stream")
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", "attachment", filename=filename)

            msg.attach(part)
            logger.info(f"✅ 添加附件成功: {filename}")
            return True

        except Exception as e:
            logger.error(f"❌ 添加附件失败 {filename}: {e}")
            return False

    def _generate_report_attachment(self, attachment: dict) -> bytes | None:
        """生成分析报告附件

        Args:
            attachment: 附件配置，包含format和analysis_result

        Returns:
            生成的报告内容（字节）
        """
        try:
            report_format = attachment.get("format", "pdf")
            analysis_result = attachment.get("analysis_result", {})
            stock_symbol = attachment.get("stock_symbol", "UNKNOWN")

            # 导入报告导出功能
            from web.utils.report_exporter import ReportExporter

            exporter = ReportExporter()

            # 构建results字典，符合ReportExporter的输入格式
            results = {
                "stock_symbol": stock_symbol,
                "decision": analysis_result.get("decision", {}),
                "state": {
                    "market_report": analysis_result.get("full_analysis", ""),
                    "fundamentals_report": "",
                    "sentiment_report": "",
                    "news_report": "",
                },
                "analysis_date": analysis_result.get("analysis_date", ""),
                "analysts": [],
                "llm_provider": "N/A",
                "llm_model": "N/A",
                "is_demo": False,
            }

            # 使用正确的export_report方法
            logger.info(f"🔄 开始生成{report_format}格式附件")
            content = exporter.export_report(results, report_format)

            if content:
                logger.info(
                    f"✅ {report_format}附件生成成功，大小: {len(content)} 字节"
                )
                return content
            else:
                logger.warning(f"⚠️ {report_format}附件生成返回空内容")
                return None

        except ImportError:
            logger.warning("⚠️ 报告导出功能未安装，跳过生成附件")
            return None
        except Exception as e:
            logger.error(f"❌ 生成报告附件失败: {e}")
            return None

    def send_test_email(self, recipient: str) -> bool:
        """发送测试邮件

        Args:
            recipient: 收件人邮箱

        Returns:
            是否发送成功
        """
        test_result = {
            "analysis_date": "2024-01-01",
            "decision": {
                "action": "测试",
                "confidence": 0.85,
                "risk_score": 0.3,
                "reasoning": "这是一封测试邮件，用于验证邮件服务配置是否正确。",
            },
            "full_analysis": "邮件服务配置测试成功！",
        }

        return self.send_analysis_report(
            recipients=[recipient], stock_symbol="TEST", analysis_result=test_result
        )
