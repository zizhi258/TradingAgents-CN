#!/usr/bin/env python3
"""
邮件配置诊断工具 - 增强版
支持SMTP连接测试、订阅管理测试和端到端邮件发送测试
"""

import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

from tradingagents.services.mailer.email_sender import EmailSender  # noqa: E402
from tradingagents.services.subscription.subscription_manager import (
    SubscriptionManager,  # noqa: E402
)
from tradingagents.utils.logging_manager import get_logger  # noqa: E402

logger = get_logger("diagnosis")


def load_environment():
    """加载环境变量"""
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ 环境变量加载自: {env_file}")
    else:
        print(f"⚠️  环境文件不存在: {env_file}")


def get_smtp_config() -> dict[str, str]:
    """获取SMTP配置"""
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", 587)),
        "user": os.getenv("SMTP_USER", ""),
        "password": os.getenv("SMTP_PASS", ""),
    }


def test_smtp_connection(config: dict) -> bool:
    """测试SMTP连接"""
    try:
        print(f"🔗 正在连接到 {config['host']}:{config['port']}...")

        # 创建SSL上下文
        context = ssl.create_default_context()

        # 根据端口选择连接方式
        if config["port"] == 465:
            # SSL 连接
            with smtplib.SMTP_SSL(
                config["host"], config["port"], context=context
            ) as server:
                server.login(config["user"], config["password"])
                print("✅ SMTP SSL连接成功")
                return True
        else:
            # TLS 连接
            with smtplib.SMTP(config["host"], config["port"]) as server:
                server.starttls(context=context)
                server.login(config["user"], config["password"])
                print("✅ SMTP TLS连接成功")
                return True

    except smtplib.SMTPAuthenticationError:
        print("❌ SMTP认证失败 - 请检查用户名和密码")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False


def send_test_email(config: dict, to_email: str) -> bool:
    """发送测试邮件"""
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg["From"] = config["user"]
        msg["To"] = to_email
        msg["Subject"] = (
            f"TradingAgents-CN 邮件测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # 邮件内容
        body = f"""
这是一封来自 TradingAgents-CN 系统的测试邮件。

测试时间: {datetime.now().isoformat()}
发送方式: 诊断脚本
SMTP服务器: {config['host']}:{config['port']}

如果您收到这封邮件，说明邮件系统配置正确。
        """

        msg.attach(MIMEText(body, "plain", "utf-8"))

        # 发送邮件
        context = ssl.create_default_context()

        if config["port"] == 465:
            with smtplib.SMTP_SSL(
                config["host"], config["port"], context=context
            ) as server:
                server.login(config["user"], config["password"])
                text = msg.as_string()
                server.sendmail(config["user"], to_email, text)
        else:
            with smtplib.SMTP(config["host"], config["port"]) as server:
                server.starttls(context=context)
                server.login(config["user"], config["password"])
                text = msg.as_string()
                server.sendmail(config["user"], to_email, text)

        print(f"✅ 测试邮件已发送到: {to_email}")
        return True

    except Exception as e:
        print(f"❌ 发送邮件失败: {e}")
        return False


def diagnose_email_config():
    """诊断邮件配置"""
    print("🔍 邮件配置诊断")
    print("=" * 50)

    # 检查环境变量
    smtp_configs = {
        "SMTP_HOST": os.getenv("SMTP_HOST", "未设置"),
        "SMTP_PORT": os.getenv("SMTP_PORT", "未设置"),
        "SMTP_USER": os.getenv("SMTP_USER", "未设置"),
        "SMTP_PASS": "***" if os.getenv("SMTP_PASS") else "未设置",
    }

    print("📧 SMTP配置:")
    for key, value in smtp_configs.items():
        status = "✅" if value != "未设置" else "❌"
        print(f"  {status} {key}: {value}")

    # 检查邮件发送器初始化
    print("\n📤 邮件发送器测试:")
    try:
        sender = EmailSender()
        print("  ✅ 邮件发送器初始化成功")

        if sender.smtp_user and sender.smtp_pass:
            print("  ✅ SMTP认证信息完整")
        else:
            print("  ❌ SMTP认证信息缺失")

    except Exception as e:
        print(f"  ❌ 邮件发送器初始化失败: {e}")

    # 检查订阅管理器
    print("\n📋 订阅管理器测试:")
    try:
        manager = SubscriptionManager()
        print("  ✅ 订阅管理器初始化成功")

        # 获取统计信息
        try:
            stats = manager.get_statistics()
            print(f"  ✅ 统计信息获取成功: {stats}")
        except Exception as e:
            print(f"  ⚠️ 统计信息获取失败: {e}")

    except Exception as e:
        print(f"  ❌ 订阅管理器初始化失败: {e}")


def test_subscription_add():
    """测试添加订阅"""
    print("\n🧪 测试订阅添加")
    print("=" * 50)

    try:
        manager = SubscriptionManager()

        # 测试添加订阅
        test_email = "test@example.com"
        test_symbols = ["000001.SZ", "AAPL"]

        subscription = {
            "email": test_email,
            "symbols": test_symbols,
            "frequency": "daily",
            "attachment_format": "pdf",
            "language": "zh",
            "name": "测试用户",
            "source": "email_diagnosis",
        }

        result = manager.add_subscription(subscription)
        if result:
            print("  ✅ 测试订阅添加成功")

            # 验证订阅是否存在
            subscriptions = manager.get_active_subscriptions(["daily"])
            test_subs = [s for s in subscriptions if s.get("email") == test_email]
            print(f"  ✅ 找到测试订阅数量: {len(test_subs)}")

            # 清理测试数据
            if test_subs:
                for sub in test_subs:
                    manager.remove_subscription(sub.get("_id"))
                print(f"  🧹 清理测试数据: {len(test_subs)} 个订阅已移除")
        else:
            print("  ❌ 测试订阅添加失败")

    except Exception as e:
        print(f"  ❌ 订阅添加测试失败: {e}")
        import traceback

        traceback.print_exc()


def add_test_subscription() -> str | None:
    """添加测试订阅用于E2E测试"""
    try:
        manager = SubscriptionManager()

        # 测试订阅数据
        test_email = input("请输入测试邮箱地址: ").strip()
        if not test_email:
            print("❌ 未提供邮箱地址")
            return None

        subscription = {
            "email": test_email,
            "symbols": ["000001.SZ", "AAPL"],  # 平安银行和苹果
            "frequency": "daily",
            "attachment_format": "pdf",
            "language": "zh",
            "name": "TradingAgents测试用户",
            "source": "email_diagnosis",
        }

        result = manager.add_subscription(subscription)
        if result:
            print(f"✅ 测试订阅已添加: {test_email}")
            return test_email
        else:
            print("❌ 添加测试订阅失败")
            return None

    except Exception as e:
        print(f"❌ 订阅管理器错误: {e}")
        return None


def create_test_trigger():
    """创建测试触发器"""
    try:
        # 动态导入避免循环依赖
        import sys

        sys.path.insert(0, str(project_root / "web"))
        from web.modules.scheduler_admin import create_manual_trigger

        trigger_file = create_manual_trigger(
            "daily",
            {
                "triggered_by": "email_diagnosis",
                "trigger_time": datetime.now().isoformat(),
                "user_agent": "diagnose_email_script",
            },
        )

        if trigger_file:
            print(f"✅ 测试触发器已创建: {Path(trigger_file).name}")
            print("📨 调度器将在30秒内处理该触发器")
            return True
        else:
            print("❌ 创建测试触发器失败")
            return False

    except Exception as e:
        print(f"❌ 触发器创建错误: {e}")
        return False


def main():
    """主函数"""
    print("🔍 TradingAgents-CN 邮件系统诊断工具 - 增强版")
    print("=" * 60)

    # 加载环境变量
    load_environment()

    # 基础诊断
    diagnose_email_config()
    test_subscription_add()

    # 获取SMTP配置用于高级测试
    config = get_smtp_config()

    print("\n📋 SMTP 配置:")
    print(f"服务器: {config['host']}")
    print(f"端口: {config['port']}")
    print(f"用户: {config['user']}")
    print(f"密码: {'*' * len(config['password']) if config['password'] else '未设置'}")

    # 验证配置
    if not all([config["host"], config["port"], config["user"], config["password"]]):
        print("\n❌ SMTP 配置不完整，请检查 .env 文件中的以下变量:")
        print("- SMTP_HOST")
        print("- SMTP_PORT")
        print("- SMTP_USER")
        print("- SMTP_PASS")
        print("\n⚠️  跳过高级测试")
        return

    # 高级测试选项
    print("\n🧪 高级测试选项")
    print("1. 测试SMTP连接")
    print("2. 发送测试邮件")
    print("3. E2E订阅流程测试")
    print("0. 退出")

    while True:
        choice = input("\n请选择测试项目 (0-3): ").strip()

        if choice == "0":
            break
        elif choice == "1":
            print("\n🔗 测试SMTP连接")
            test_smtp_connection(config)
        elif choice == "2":
            print("\n📧 发送测试邮件")
            test_email = input("请输入测试邮箱地址: ").strip()
            if test_email:
                send_test_email(config, test_email)
            else:
                print("❌ 未提供测试邮箱地址")
        elif choice == "3":
            print("\n🎯 E2E订阅流程测试")
            print("此测试将:")
            print("1. 添加测试订阅")
            print("2. 创建手动触发器")
            print("3. 触发调度器生成并发送邮件")

            confirm = input("确认执行？(y/N): ").strip().lower()
            if confirm == "y":
                subscription_email = add_test_subscription()

                if subscription_email:
                    print("🚀 创建手动触发器...")
                    if create_test_trigger():
                        print("\n✅ E2E测试流程启动成功！")
                        print("📬 请检查邮箱，应在2-3分钟内收到股票分析邮件")
                        print("📋 可通过以下方式查看执行日志:")
                        print("   docker compose logs -f scheduler")
                        print("   tail -f logs/tradingagents.log")
                    else:
                        print("❌ 触发器创建失败")
                else:
                    print("❌ 订阅添加失败")
        else:
            print("❌ 无效选择，请输入 0-3")

    print("\n🎉 邮件系统诊断完成")
    print("如需进一步帮助，请查看:")
    print("- 应用日志: logs/tradingagents.log")
    print("- 调度器日志: logs/scheduler.log")
    print("- Docker日志: docker compose logs scheduler")


if __name__ == "__main__":
    main()
