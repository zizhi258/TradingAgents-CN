#!/usr/bin/env python3
"""
调度服务启动脚本
用于Docker容器启动调度服务
"""

import signal
import sys
import time
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from tradingagents.services.scheduler.market_scheduler import (
    MarketScheduler,  # noqa: E402
)
from tradingagents.utils.logging_manager import get_logger  # noqa: E402

logger = get_logger("scheduler_service")

# 全局调度器实例
scheduler = None


def signal_handler(sig, frame):
    """处理退出信号"""
    global scheduler
    logger.info("收到退出信号，正在停止调度服务...")
    if scheduler:
        scheduler.stop()
    sys.exit(0)


def main():
    """主函数"""
    global scheduler

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("🚀 正在启动TradingAgents调度服务...")

    try:
        # 创建并启动调度器
        scheduler = MarketScheduler()
        scheduler.start()

        logger.info("✅ 调度服务启动成功")
        logger.info("📅 调度服务正在运行，等待任务触发...")

        # 保持运行
        while True:
            time.sleep(60)  # 每分钟检查一次

    except KeyboardInterrupt:
        logger.info("⏹️ 收到键盘中断，正在停止...")
    except Exception as e:
        logger.error(f"❌ 调度服务异常: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if scheduler:
            scheduler.stop()
        logger.info("调度服务已停止")


if __name__ == "__main__":
    main()
