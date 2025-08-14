"""
邮件服务模块
"""

# 延迟导入，避免循环依赖
def get_email_sender():
    """获取邮件发送器实例"""
    from .email_sender import EmailSender
    return EmailSender()

__all__ = ['get_email_sender']
