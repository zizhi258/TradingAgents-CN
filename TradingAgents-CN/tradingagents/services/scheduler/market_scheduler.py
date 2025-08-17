#!/usr/bin/env python3
"""
市场收市调度器
根据不同交易所的收市时间自动触发研报生成和发送
支持每日和每周定时任务
"""

import json
import os
from collections.abc import Callable
from datetime import datetime, time
from pathlib import Path
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from tradingagents.config.config_manager import ConfigManager
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("scheduler")


class MarketScheduler:
    """市场收市调度器"""

    # 各交易所收市时间配置
    MARKET_CLOSE_TIMES = {
        "A股": {
            "timezone": "Asia/Shanghai",
            "close_time": time(15, 5),  # 15:05 收市后5分钟
            "trading_days": "mon-fri",  # 周一到周五
            "exchanges": ["SH", "SZ"],
            "name_cn": "A股市场",
        },
        "港股": {
            "timezone": "Asia/Hong_Kong",
            "close_time": time(16, 10),  # 16:10 收市后10分钟
            "trading_days": "mon-fri",
            "exchanges": ["HK"],
            "name_cn": "港股市场",
        },
        "美股": {
            "timezone": "America/New_York",
            "close_time": time(16, 5),  # 16:05 收市后5分钟
            "trading_days": "mon-fri",
            "exchanges": ["NYSE", "NASDAQ"],
            "name_cn": "美股市场",
        },
    }

    def __init__(self):
        """初始化调度器"""
        self.scheduler = BackgroundScheduler()
        self.config_manager = ConfigManager()
        self._subscription_manager = None
        self._email_sender = None
        self._analysis_runner = None
        self._running = False

        # 配置调度器监听器
        self.scheduler.add_listener(
            self._job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED
        )

    @property
    def subscription_manager(self):
        """延迟加载订阅管理器，避免循环依赖"""
        if self._subscription_manager is None:
            from tradingagents.services.subscription.subscription_manager import (
                SubscriptionManager,
            )

            self._subscription_manager = SubscriptionManager()
        return self._subscription_manager

    @property
    def email_sender(self):
        """延迟加载邮件发送器"""
        if self._email_sender is None:
            from tradingagents.services.mailer.email_sender import EmailSender

            self._email_sender = EmailSender()
        return self._email_sender

    @property
    def analysis_runner(self):
        """延迟加载分析运行器"""
        if self._analysis_runner is None:
            from tradingagents.web.utils.analysis_runner import run_stock_analysis

            self._analysis_runner = run_stock_analysis
        return self._analysis_runner

    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已经在运行中")
            return

        logger.info("📅 正在启动市场收市调度器...")

        # 检查是否启用调度功能
        if not os.getenv("SCHEDULER_ENABLED", "false").lower() == "true":
            logger.warning("⚠️ 调度功能未启用，请在.env中设置 SCHEDULER_ENABLED=true")
            return

        # 为每个市场添加收市任务
        for market_type, config in self.MARKET_CLOSE_TIMES.items():
            self._add_market_job(market_type, config)

        # 启动调度器
        self.scheduler.start()
        self._running = True

        # 加载Email调度任务
        self.refresh_jobs_from_settings()

        logger.info("✅ 市场收市调度器启动成功")
        self._log_scheduled_jobs()

    def stop(self):
        """停止调度器"""
        if not self._running:
            return

        logger.info("⏹️ 正在停止调度器...")
        self.scheduler.shutdown()
        self._running = False
        logger.info("✅ 调度器已停止")

    def _add_market_job(self, market_type: str, config: dict):
        """添加市场收市任务"""
        try:
            trigger = CronTrigger(
                hour=config["close_time"].hour,
                minute=config["close_time"].minute,
                day_of_week=config["trading_days"],
                timezone=config["timezone"],
            )

            job_id = f"close_report_{market_type}"
            job_name = f'{config["name_cn"]}收市报告'

            self.scheduler.add_job(
                func=self._run_close_report,
                trigger=trigger,
                args=[market_type, config],
                id=job_id,
                name=job_name,
                replace_existing=True,
            )

            logger.info(
                f"✅ 添加定时任务: {job_name} "
                f"({config['timezone']} {config['close_time']})"
            )

        except Exception as e:
            logger.error(f"❌ 添加{market_type}任务失败: {e}")

    def _run_close_report(self, market_type: str, config: dict):
        """执行收市报告任务"""
        start_time = datetime.now()
        logger.info(f"🔔 {config['name_cn']}收市，开始生成分析报告...")

        try:
            # 获取该市场的订阅列表
            subscriptions = self.subscription_manager.get_subscriptions_by_market(
                config["exchanges"]
            )

            if not subscriptions:
                logger.info(f"📭 {market_type}暂无订阅")
                return

            logger.info(f"📋 找到 {len(subscriptions)} 个订阅")

            # 按股票分组，避免重复分析
            stock_groups = self._group_subscriptions_by_stock(subscriptions)

            # 批量分析
            analysis_results = {}
            for symbol, subs in stock_groups.items():
                try:
                    logger.info(f"📊 正在分析 {symbol}...")
                    result = self._analyze_stock(symbol, subs[0]["market_type"])
                    analysis_results[symbol] = result

                except Exception as e:
                    logger.error(f"❌ 分析{symbol}失败: {e}")

            # 发送邮件
            self._send_batch_emails(stock_groups, analysis_results)

            # 同步发送市场摘要给市场级订阅
            try:
                market_subs = self.subscription_manager.get_market_subscriptions(
                    scope=market_type, frequency_filter=["close"]
                )
                if market_subs:
                    logger.info(
                        f"📬 为市场摘要订阅发送 {market_type} 收市摘要: {len(market_subs)} 个订阅"
                    )
                    self._send_market_digest(
                        scope=market_type, subscriptions=market_subs, mode="close"
                    )
                else:
                    logger.info(f"📭 {market_type} 无市场摘要订阅")
            except Exception as e:
                logger.error(f"❌ 发送{market_type}市场摘要失败: {e}")

            # 发送该市场相关的指数订阅（收市频率）
            try:
                index_subs = self.subscription_manager.get_index_subscriptions(
                    market=market_type, frequency_filter=["close"]
                )
                if index_subs:
                    self._send_index_digests(index_subs, mode="close")
                else:
                    logger.info(f"📭 {market_type} 无指数订阅需要发送（收市）")
            except Exception as e:
                logger.error(f"❌ 发送{market_type}指数摘要失败: {e}")

            # 记录完成时间
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ {config['name_cn']}收市报告完成，耗时 {elapsed:.1f}秒")

        except Exception as e:
            logger.error(f"❌ 执行{market_type}收市报告失败: {e}")
            import traceback

            traceback.print_exc()

    def _group_subscriptions_by_stock(
        self, subscriptions: list[dict]
    ) -> dict[str, list[dict]]:
        """按股票代码分组订阅"""
        groups = {}
        for sub in subscriptions:
            symbol = sub["symbol"]
            if symbol not in groups:
                groups[symbol] = []
            groups[symbol].append(sub)
        return groups

    def _analyze_stock(self, symbol: str, market_type: str) -> dict:
        """分析单只股票"""
        # 使用快速分析配置
        analysis_date = datetime.now().strftime("%Y-%m-%d")

        # 配置快速分析参数
        config = {
            "selected_analysts": ["market", "fundamentals"],  # 只用关键分析师
            "research_depth": 2,  # 基础深度
            "llm_provider": os.getenv("LLM_PROVIDER", "dashscope"),
            "llm_model": os.getenv("QUICK_THINK_LLM", "qwen-turbo"),
        }

        # 执行分析
        state, decision = self.analysis_runner(
            stock_symbol=symbol,
            analysis_date=analysis_date,
            analysts=config["selected_analysts"],
            research_depth=config["research_depth"],
            llm_provider=config["llm_provider"],
            llm_model=config["llm_model"],
            market_type=market_type,
        )

        return {
            "symbol": symbol,
            "analysis_date": analysis_date,
            "decision": decision,
            "state": state,
            "market_type": market_type,
        }

    def _send_batch_emails(self, stock_groups: dict, analysis_results: dict):
        """批量发送邮件"""
        for symbol, subscriptions in stock_groups.items():
            if symbol not in analysis_results:
                continue

            result = analysis_results[symbol]

            # 按附件配置分组邮件，避免重复生成附件
            attachment_groups = {}
            for sub in subscriptions:
                attachment_config = sub.get("attachment_config", {})
                # 将配置转换为字符串作为分组key
                config_key = str(sorted(attachment_config.items()))
                if config_key not in attachment_groups:
                    attachment_groups[config_key] = {
                        "emails": [],
                        "config": attachment_config,
                    }
                attachment_groups[config_key]["emails"].append(sub["email"])

            # 为每个附件配置组发送邮件
            for config_key, group in attachment_groups.items():
                emails = group["emails"]
                attachment_config = group["config"]

                try:
                    # 生成附件列表
                    attachments = self._generate_attachments(
                        result, symbol, attachment_config
                    )

                    self.email_sender.send_analysis_report(
                        recipients=emails,
                        stock_symbol=symbol,
                        analysis_result=result,
                        attachments=attachments,
                    )

                    attachment_info = (
                        f"（附件：{', '.join([att['filename'] for att in attachments])}）"
                        if attachments
                        else "（无附件）"
                    )
                    logger.info(
                        f"✉️ 已发送 {symbol} 报告至 {len(emails)} 个邮箱 {attachment_info}"
                    )

                except Exception as e:
                    logger.error(f"❌ 发送{symbol}邮件失败: {e}")

    def _generate_attachments(
        self, analysis_result: dict, symbol: str, attachment_config: dict
    ) -> list[dict]:
        """根据配置生成附件列表

        Args:
            analysis_result: 分析结果
            symbol: 股票代码
            attachment_config: 附件配置

        Returns:
            附件列表
        """
        attachments = []

        if not attachment_config:
            return attachments

        try:
            # PDF报告
            if attachment_config.get("pdf_report", False):
                attachments.append(
                    {
                        "type": "report",
                        "format": "pdf",
                        "filename": f'{symbol}_股票分析报告_{analysis_result.get("analysis_date", "")}.pdf',
                        "analysis_result": analysis_result,
                        "stock_symbol": symbol,
                    }
                )

            # Word报告
            if attachment_config.get("word_report", False):
                attachments.append(
                    {
                        "type": "report",
                        "format": "docx",
                        "filename": f'{symbol}_股票分析报告_{analysis_result.get("analysis_date", "")}.docx',
                        "analysis_result": analysis_result,
                        "stock_symbol": symbol,
                    }
                )

            # Markdown报告
            if attachment_config.get("markdown_report", False):
                attachments.append(
                    {
                        "type": "report",
                        "format": "md",
                        "filename": f'{symbol}_股票分析报告_{analysis_result.get("analysis_date", "")}.md',
                        "analysis_result": analysis_result,
                        "stock_symbol": symbol,
                    }
                )

            # 其他附件类型可以在这里扩展
            # 例如：技术图表、数据Excel等

        except Exception as e:
            logger.error(f"❌ 生成{symbol}附件失败: {e}")

        return attachments

    # === 市场摘要支持 ===
    def _send_market_digest(
        self, scope: str, subscriptions: list[dict], mode: str = "daily"
    ):
        """发送市场摘要邮件（按范围聚合）"""
        if not subscriptions:
            return

        try:
            # 聚合邮件列表（不区分附件配置，摘要默认无附件）
            recipients = list({sub["email"] for sub in subscriptions})
            digest = self._generate_market_digest(scope)
            subject_symbol = f"MARKET-{scope}"
            self.email_sender.send_analysis_report(
                recipients=recipients,
                stock_symbol=subject_symbol,
                analysis_result=digest,
                attachments=None,
            )
            logger.info(f"✉️ 已发送{scope}市场摘要至 {len(recipients)} 个邮箱")
        except Exception as e:
            logger.error(f"❌ 发送{scope}市场摘要失败: {e}")

    def _generate_market_digest(self, scope: str) -> dict:
        """基于最近的市场扫描结果生成摘要内容。

        优先使用 data/market_sessions/results 下的最近结果；若不可用，则提供简要占位内容。
        """
        import json
        from pathlib import Path

        now_date = datetime.now().strftime("%Y-%m-%d")

        results_dir = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "market_sessions"
            / "results"
        )
        best_file = None
        best_mtime = None

        # 映射范围到结果文件内可能的提示（文件内容通常含“扫描完成：共评估” + 市场名）
        # 我们通过文件内容 summary.key_insights 的首项是否包含对应市场字样来粗匹配
        def file_matches_scope(payload: dict) -> bool:
            try:
                res = payload.get("results") or payload
                summary = res.get("summary", {})
                insights = summary.get("key_insights", [])
                text = "\n".join(insights)
                if scope == "全球":
                    return True  # 全局不限制
                return scope in text
            except Exception:
                return False

        if results_dir.exists():
            for p in results_dir.glob("*.json"):
                try:
                    stat = p.stat()
                    with open(p, encoding="utf-8") as f:
                        data = json.load(f)
                    if file_matches_scope(data):
                        if (best_mtime is None) or (stat.st_mtime > best_mtime):
                            best_file = p
                            best_mtime = stat.st_mtime
                except Exception:
                    continue

        if best_file is not None:
            try:
                with open(best_file, encoding="utf-8") as f:
                    data = json.load(f)
                res = data.get("results") or data
                summary = res.get("summary", {})
                key_insights = summary.get("key_insights", [])
                # 组装简要分析
                reasoning = (
                    "\n".join(f"- {item}" for item in key_insights[:6])
                    or f"{scope} 市场摘要"
                )
                decision = {
                    "action": "DIGEST",
                    "confidence": 0.0,
                    "risk_score": 0.0,
                    "reasoning": reasoning,
                }
                return {
                    "analysis_date": now_date,
                    "decision": decision,
                    "full_analysis": json.dumps(summary, ensure_ascii=False, indent=2),
                }
            except Exception:
                pass

        # 退化：无扫描结果，输出占位摘要
        reasoning = f"{scope} 市场摘要：\n- 本次未找到可用的扫描结果数据\n- 请在Web界面执行一次‘全球市场分析’以生成摘要数据"
        return {
            "analysis_date": now_date,
            "decision": {
                "action": "DIGEST",
                "confidence": 0.0,
                "risk_score": 0.0,
                "reasoning": reasoning,
            },
            "full_analysis": reasoning,
        }

    # === 指数摘要支持 ===
    def _send_index_digests(self, subscriptions: list[dict], mode: str = "daily"):
        """分组并发送指数订阅摘要。"""
        if not subscriptions:
            return
        # 按指数代码分组
        groups: dict[str, dict[str, Any]] = {}
        for sub in subscriptions:
            code = (sub.get("symbol") or "").upper()
            name = sub.get("index_name") or None
            if code not in groups:
                groups[code] = {"name": name, "subs": []}
            groups[code]["subs"].append(sub)

        for code, info in groups.items():
            try:
                name = info.get("name")
                digest = self._generate_index_digest(code, name)
                recipients = list({s["email"] for s in info["subs"]})
                subject_symbol = f"{name}({code})" if name else f"INDEX-{code}"
                self.email_sender.send_analysis_report(
                    recipients=recipients,
                    stock_symbol=subject_symbol,
                    analysis_result=digest,
                    attachments=None,
                )
                logger.info(
                    f"✉️ 已发送指数摘要 {subject_symbol} 至 {len(recipients)} 个邮箱"
                )
            except Exception as e:
                logger.error(f"❌ 发送指数摘要失败: {code}: {e}")

    def _generate_index_digest(
        self, index_code: str, index_name: str | None = None
    ) -> dict:
        """生成指数摘要内容。尽量查询当日涨跌与权重前列成分；失败则退化为占位摘要。"""
        from datetime import datetime as _dt
        from datetime import timedelta as _td

        now_date = _dt.now().strftime("%Y-%m-%d")
        reasoning_parts: list[str] = []
        last_text = None
        try:
            # 使用Tushare（若可用）查询近5个交易日，取最新一日
            try:
                from tradingagents.dataflows.tushare_utils import get_tushare_provider

                prov = get_tushare_provider()
                api = getattr(prov, "api", None)
            except Exception:
                api = None

            if api is not None:
                start = (_dt.now() - _td(days=14)).strftime("%Y%m%d")
                end = _dt.now().strftime("%Y%m%d")
                try:
                    df = api.index_daily(
                        ts_code=index_code, start_date=start, end_date=end
                    )
                    if df is not None and hasattr(df, "empty") and not df.empty:
                        df = df.sort_values("trade_date")
                        row = df.iloc[-1]
                        close_v = float(row.get("close", 0.0))
                        pct = float(row.get("pct_chg", 0.0))
                        last_text = f"收盘 {close_v:.2f}，涨跌幅 {pct:+.2f}%"
                        reasoning_parts.append(f"- 最新：{last_text}")
                except Exception:
                    pass

                # 读取当月成分权重
                try:
                    month = _dt.now().strftime("%Y%m")
                    w = api.index_weight(index_code=index_code, trade_date=month)
                    if w is not None and hasattr(w, "empty") and not w.empty:
                        w = w.sort_values("weight", ascending=False)
                        top = w.head(10)
                        items = [
                            f"{it.get('con_name', it.get('con_code'))}:{float(it.get('weight', 0.0)):.2f}%"
                            for it in top.to_dict("records")
                        ]
                        reasoning_parts.append("- 前十大权重：" + ", ".join(items))
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"指数摘要生成失败: {index_code}: {e}")

        title = index_name or index_code
        if not reasoning_parts:
            reasoning_parts = [f"- {title} 指数摘要：暂无数据源，稍后重试"]

        return {
            "analysis_date": now_date,
            "decision": {
                "action": "INDEX_DIGEST",
                "confidence": 0.0,
                "risk_score": 0.0,
                "reasoning": "\n".join(reasoning_parts),
            },
            "full_analysis": "\n".join(reasoning_parts),
        }

    def _job_listener(self, event):
        """监听任务执行事件"""
        if event.exception:
            logger.error(f"❌ 任务执行失败: {event.job_id}")
            logger.error(f"错误信息: {event.exception}")
        else:
            logger.debug(f"✅ 任务执行成功: {event.job_id}")

    def _log_scheduled_jobs(self):
        """记录已调度的任务"""
        jobs = self.scheduler.get_jobs()
        if jobs:
            logger.info("📋 已调度的任务:")
            for job in jobs:
                logger.info(f"  - {job.name}: {job.next_run_time}")
        else:
            logger.info("📋 暂无调度任务")

    def add_custom_job(
        self, job_id: str, func: Callable, trigger: str = "interval", **trigger_args
    ):
        """添加自定义任务

        Args:
            job_id: 任务ID
            func: 要执行的函数
            trigger: 触发器类型 ('interval', 'cron', 'date')
            **trigger_args: 触发器参数
        """
        self.scheduler.add_job(
            func=func, trigger=trigger, id=job_id, replace_existing=True, **trigger_args
        )
        logger.info(f"✅ 添加自定义任务: {job_id}")

    def remove_job(self, job_id: str):
        """移除任务"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"✅ 已移除任务: {job_id}")
        except Exception as e:
            logger.error(f"❌ 移除任务失败: {e}")

    def get_job_status(self, job_id: str) -> dict | None:
        """获取任务状态"""
        job = self.scheduler.get_job(job_id)
        if job:
            return {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time,
                "pending": job.pending,
            }
        return None

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._running

    def refresh_jobs_from_settings(self):
        """从设置中刷新email调度任务"""
        try:
            settings = self.config_manager.load_settings()
            email_schedules = settings.get("email_schedules", {})

            # 移除现有的digest任务
            self._remove_digest_jobs()

            # 添加每日任务
            daily_config = email_schedules.get("daily", {})
            if daily_config.get("enabled", False):
                self._add_daily_digest_job(daily_config)

            # 添加每周任务
            weekly_config = email_schedules.get("weekly", {})
            if weekly_config.get("enabled", False):
                self._add_weekly_digest_job(weekly_config)

            # 添加触发器监控任务
            self._add_trigger_watcher_job()

            logger.info("✅ 邮件调度任务已从设置中刷新")

        except Exception as e:
            logger.error(f"❌ 刷新邮件调度任务失败: {e}")

    def _remove_digest_jobs(self):
        """移除digest相关任务"""
        digest_job_ids = ["daily_digest", "weekly_digest", "trigger_watcher"]
        for job_id in digest_job_ids:
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass  # 任务不存在时忽略

    def _add_daily_digest_job(self, daily_config: dict):
        """添加每日摘要任务"""
        try:
            timezone = os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai")
            hour = daily_config.get("hour", 18)
            minute = daily_config.get("minute", 0)

            trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone)

            self.scheduler.add_job(
                func=self._run_digest_report,
                trigger=trigger,
                args=["daily"],
                id="daily_digest",
                name="每日邮件摘要",
                replace_existing=True,
            )

            logger.info(f"✅ 添加每日摘要任务: {hour:02d}:{minute:02d} ({timezone})")

        except Exception as e:
            logger.error(f"❌ 添加每日摘要任务失败: {e}")

    def _add_weekly_digest_job(self, weekly_config: dict):
        """添加每周摘要任务"""
        try:
            timezone = os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai")
            hour = weekly_config.get("hour", 9)
            minute = weekly_config.get("minute", 0)
            weekdays = weekly_config.get("weekday", [1])  # 默认周一

            # 转换weekday格式 (APScheduler uses 0=Monday, 6=Sunday)
            if isinstance(weekdays, int):
                weekdays = [weekdays]

            # 确保weekday在有效范围内
            valid_weekdays = [w for w in weekdays if 0 <= w <= 6]
            if not valid_weekdays:
                valid_weekdays = [0]  # 默认周一

            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                day_of_week=",".join(map(str, valid_weekdays)),
                timezone=timezone,
            )

            self.scheduler.add_job(
                func=self._run_digest_report,
                trigger=trigger,
                args=["weekly"],
                id="weekly_digest",
                name="每周邮件摘要",
                replace_existing=True,
            )

            weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            weekday_str = ",".join([weekday_names[w] for w in valid_weekdays])
            logger.info(
                f"✅ 添加每周摘要任务: {weekday_str} {hour:02d}:{minute:02d} ({timezone})"
            )

        except Exception as e:
            logger.error(f"❌ 添加每周摘要任务失败: {e}")

    def _add_trigger_watcher_job(self):
        """添加触发器文件监控任务"""
        try:
            # 每30秒检查一次触发器文件
            self.scheduler.add_job(
                func=self._check_trigger_files,
                trigger="interval",
                seconds=30,
                id="trigger_watcher",
                name="触发器文件监控",
                replace_existing=True,
            )

            logger.info("✅ 添加触发器文件监控任务")

        except Exception as e:
            logger.error(f"❌ 添加触发器文件监控任务失败: {e}")

    def _check_trigger_files(self):
        """检查并处理触发器文件"""
        try:
            # 获取项目根目录下的data/triggers目录
            project_root = Path(__file__).parent.parent.parent.parent
            trigger_dir = project_root / "data" / "triggers"

            if not trigger_dir.exists():
                return

            # 查找所有触发器文件
            trigger_files = list(trigger_dir.glob("*.json"))

            for trigger_file in trigger_files:
                try:
                    with open(trigger_file, encoding="utf-8") as f:
                        trigger_data = json.load(f)

                    # 解析触发器类型
                    trigger_type = trigger_data.get("type", "manual")

                    if trigger_type in ["daily", "weekly", "manual"]:
                        logger.info(
                            f"🔔 处理触发器: {trigger_file.name} (类型: {trigger_type})"
                        )
                        self._run_digest_report(trigger_type, trigger_data)

                    # 处理完成后删除触发器文件
                    trigger_file.unlink()

                except Exception as e:
                    logger.error(f"❌ 处理触发器文件 {trigger_file.name} 失败: {e}")
                    # 删除损坏的触发器文件
                    try:
                        trigger_file.unlink()
                    except Exception:
                        pass

        except Exception as e:
            logger.error(f"❌ 检查触发器文件失败: {e}")

    def _run_digest_report(self, mode: str, trigger_data: dict | None = None):
        """执行摘要报告任务

        Args:
            mode: 'daily', 'weekly', 'manual'
            trigger_data: 触发器数据（用于手动触发）
        """
        start_time = datetime.now()
        logger.info(f"🔔 开始执行{mode}邮件摘要任务...")

        try:
            # 获取所有活跃订阅
            frequency_filter = None
            if mode == "daily":
                frequency_filter = ["daily", "close"]
            elif mode == "weekly":
                frequency_filter = ["weekly"]

            # 使用订阅管理器获取订阅列表
            subscriptions = self.subscription_manager.get_active_subscriptions(
                frequency_filter=frequency_filter
            )

            if not subscriptions:
                logger.info(f"📭 {mode}摘要暂无活跃订阅")
                return

            logger.info(f"📋 找到 {len(subscriptions)} 个活跃订阅")

            # 按股票分组，避免重复分析
            stock_groups = self._group_subscriptions_by_stock(subscriptions)

            # 批量分析
            analysis_results = {}
            success_count = 0
            error_count = 0

            for symbol, subs in stock_groups.items():
                try:
                    logger.info(f"📊 正在分析 {symbol}...")
                    result = self._analyze_stock(symbol, subs[0]["market_type"])
                    analysis_results[symbol] = result
                    success_count += 1

                except Exception as e:
                    logger.error(f"❌ 分析{symbol}失败: {e}")
                    error_count += 1

            # 发送个股订阅邮件
            email_success_count = 0
            email_error_count = 0

            for symbol, subscriptions_list in stock_groups.items():
                if symbol not in analysis_results:
                    continue

                try:
                    result = analysis_results[symbol]
                    self._send_batch_emails(
                        {symbol: subscriptions_list}, {symbol: result}
                    )
                    email_success_count += len(subscriptions_list)

                except Exception as e:
                    logger.error(f"❌ 发送{symbol}邮件失败: {e}")
                    email_error_count += len(subscriptions_list)

            # 发送市场摘要（市场级订阅）
            try:
                market_subs = self.subscription_manager.get_market_subscriptions(
                    frequency_filter=frequency_filter
                )
                # 按scope分组
                subs_by_scope = {}
                for sub in market_subs:
                    scope = sub.get("market_scope") or "全球"
                    subs_by_scope.setdefault(scope, []).append(sub)
                for scope, subs in subs_by_scope.items():
                    self._send_market_digest(scope=scope, subscriptions=subs, mode=mode)
            except Exception as e:
                logger.error(f"❌ 发送市场摘要失败: {e}")

            # 发送指数摘要（指数订阅）
            try:
                idx_subs = self.subscription_manager.get_index_subscriptions(
                    market=None, frequency_filter=frequency_filter
                )
                if idx_subs:
                    self._send_index_digests(idx_subs, mode=mode)
            except Exception as e:
                logger.error(f"❌ 发送指数摘要失败: {e}")

            # 记录完成时间和统计
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"✅ {mode}邮件摘要完成 - 耗时: {elapsed:.1f}秒, "
                f"分析: {success_count}成功/{error_count}失败, "
                f"邮件: {email_success_count}成功/{email_error_count}失败"
            )

        except Exception as e:
            logger.error(f"❌ 执行{mode}邮件摘要失败: {e}")
            import traceback

            traceback.print_exc()

    def create_manual_trigger(
        self, trigger_type: str = "daily", custom_data: dict | None = None
    ):
        """创建手动触发器文件"""
        try:
            # 获取项目根目录下的data/triggers目录
            project_root = Path(__file__).parent.parent.parent.parent
            trigger_dir = project_root / "data" / "triggers"
            trigger_dir.mkdir(parents=True, exist_ok=True)

            # 生成触发器文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            trigger_file = trigger_dir / f"trigger_{trigger_type}_{timestamp}.json"

            # 创建触发器数据
            trigger_data = {
                "type": trigger_type,
                "created_at": datetime.now().isoformat(),
                "source": "manual",
            }

            if custom_data:
                trigger_data.update(custom_data)

            # 写入触发器文件
            with open(trigger_file, "w", encoding="utf-8") as f:
                json.dump(trigger_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ 创建手动触发器: {trigger_file.name}")
            return str(trigger_file)

        except Exception as e:
            logger.error(f"❌ 创建手动触发器失败: {e}")
            return None

    def get_scheduler_status(self) -> dict:
        """获取调度器状态信息"""
        try:
            jobs = self.scheduler.get_jobs()
            job_info = []

            for job in jobs:
                job_info.append(
                    {
                        "id": job.id,
                        "name": job.name,
                        "next_run_time": (
                            job.next_run_time.isoformat() if job.next_run_time else None
                        ),
                        "trigger": str(job.trigger),
                    }
                )

            return {
                "running": self.is_running,
                "jobs": job_info,
                "timezone": os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai"),
                "total_jobs": len(jobs),
            }

        except Exception as e:
            logger.error(f"❌ 获取调度器状态失败: {e}")
            return {"running": False, "jobs": [], "error": str(e)}
