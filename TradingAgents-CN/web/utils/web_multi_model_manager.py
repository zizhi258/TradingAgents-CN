"""
Web Multi-Model Collaboration Manager
专为Web界面设计的多模型协作管理器
"""

from datetime import datetime
from typing import Any

from tradingagents.agents.specialized import (  # Alias roles exposed in UI
    ChiefDecisionOfficer,
    ChiefWriter,
    ComplianceOfficer,
    ChartingArtist,
    FundamentalExpert,
    NewsHunter,
    PolicyResearcher,
    RiskManager,
    SentimentAnalyst,
    TechnicalAnalyst,
    ToolEngineer,
)
from tradingagents.core.multi_model_manager import MultiModelManager

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("web_multi_model_manager")


class WebMultiModelCollaborationManager:
    """专为Web界面设计的多模型协作管理器"""

    def __init__(self, config: dict[str, Any]):
        """
        初始化Web多模型协作管理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.collaboration_mode = config.get("collaboration_mode", "sequential")
        self.selected_agents = config.get("selected_agents", [])
        self.use_smart_routing = config.get("use_smart_routing", True)

        # 初始化多模型管理器
        self.multi_model_manager = MultiModelManager(config)

        # 初始化专业智能体
        self.agents = {}
        self._initialize_agents()

        logger.info("Web多模型协作管理器初始化完成")

    def _initialize_agents(self):
        """初始化专业智能体"""
        try:
            agent_classes = {
                "news_hunter": NewsHunter,
                "fundamental_expert": FundamentalExpert,
                "technical_analyst": TechnicalAnalyst,
                "sentiment_analyst": SentimentAnalyst,
                "risk_manager": RiskManager,
                "policy_researcher": PolicyResearcher,
                "tool_engineer": ToolEngineer,
                "compliance_officer": ComplianceOfficer,
                "chief_decision_officer": ChiefDecisionOfficer,
                # 新增：绘图师
                "charting_artist": ChartingArtist,
            }

            for agent_type in self.selected_agents:
                if agent_type in agent_classes:
                    try:
                        self.agents[agent_type] = agent_classes[agent_type](
                            multi_model_manager=self.multi_model_manager,
                            config=self.config,
                        )
                        logger.info(f"✅ 初始化智能体: {agent_type}")
                    except Exception as e:
                        logger.warning(f"⚠️ 智能体初始化失败 {agent_type}: {e}")

        except Exception as e:
            logger.error(f"智能体初始化失败: {e}")

    def run_collaboration_analysis(
        self,
        stock_symbol: str,
        market_type: str = "A股",
        analysis_date: str = None,
        research_depth: int = 3,
        custom_requirements: str = "",
        show_process_details: bool = True,
        progress_callback=None,
    ) -> dict[str, Any]:
        """
        运行协作分析

        Args:
            stock_symbol: 股票代码
            market_type: 市场类型
            analysis_date: 分析日期
            research_depth: 研究深度
            custom_requirements: 自定义要求
            show_process_details: 显示过程详情

        Returns:
            分析结果字典
        """
        try:
            # 演示模式：仅模拟“输入股票数据”，其余流程与正式版一致
            demo_sections = None
            try:
                import os as _os

                if str(_os.getenv("DEMO_MODE", "false")).lower() == "true":
                    if progress_callback:
                        try:
                            progress_callback(
                                {
                                    "stage": "demo",
                                    "message": "演示模式：已加载本地示例数据，其他流程保持一致",
                                }
                            )
                        except Exception:
                            pass
                    from .demo_data import (
                        build_markdown_sections_from_demo,
                        load_demo_json,
                    )

                    demo_sections = build_markdown_sections_from_demo(load_demo_json())
            except Exception:
                demo_sections = None

            logger.info(f"🚀 开始多模型协作分析: {stock_symbol}")
            aid = f"web_multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{stock_symbol}"
            telemetry.emit(
                "multi_model.start",
                analysis_id=aid,
                component="web",
                data={
                    "stock_symbol": stock_symbol,
                    "market_type": market_type,
                    "research_depth": research_depth,
                    "agents": list(self.selected_agents),
                },
            )

            # 轻量预校验/补齐：解析公司名称与基本可用性（不改变主流程）
            # 目的：为提示词注入 company_name，降低模型“乱指名”的概率
            resolved_name = None
            try:
                # 根据研究深度收敛预取窗口，避免额外时延
                _depth_days = {1: 14, 2: 21, 3: 30, 4: 60, 5: 90}
                _period_days = _depth_days.get(int(research_depth) if research_depth else 3, 30)
            except Exception:
                _period_days = 30
            try:
                from tradingagents.utils.stock_validator import prepare_stock_data as _prep

                prep = _prep(
                    stock_code=stock_symbol,
                    market_type=market_type,
                    period_days=_period_days,
                    analysis_date=analysis_date or datetime.now().strftime("%Y-%m-%d"),
                )
                if getattr(prep, "is_valid", False) and getattr(prep, "stock_name", None):
                    name = str(prep.stock_name).strip()
                    if name and name not in {"未知", "N/A"}:
                        resolved_name = name
            except Exception:
                resolved_name = None

            # 准备分析数据
            analysis_data = {
                "stock_symbol": stock_symbol,
                "market_type": market_type,
                "analysis_date": analysis_date or datetime.now().isoformat(),
                "research_depth": research_depth,
                "custom_requirements": custom_requirements,
                # 解析出的公司名（若可用）
                "stock_name": resolved_name,
                # 若为演示模式，附加各模块的“输入数据”片段供提示词使用
                "demo_sections": demo_sections if demo_sections else None,
            }

            # 根据协作模式执行分析
            if self.collaboration_mode == "sequential":
                results = self._run_sequential_analysis(
                    analysis_data, progress_callback
                )
            elif self.collaboration_mode == "parallel":
                results = self._run_parallel_analysis(analysis_data, progress_callback)
            elif self.collaboration_mode == "debate":
                results = self._run_debate_analysis(analysis_data, progress_callback)
            else:
                raise ValueError(f"未支持的协作模式: {self.collaboration_mode}")

            # 主笔人生成规整长文
            if progress_callback:
                try:
                    progress_callback(
                        {
                            "stage": "chief_writer_prepare",
                            "message": "准备生成主笔人长文",
                        }
                    )
                except Exception:
                    pass
            final_article, article_metrics = self._compose_final_article(
                results, analysis_data
            )
            if progress_callback:
                try:
                    progress_callback(
                        {
                            "stage": "chief_writer_done",
                            "percent": 95,
                            "message": "主笔人长文生成完成",
                        }
                    )
                except Exception:
                    pass

            logger.info("✅ 多模型协作分析完成")
            # 若选择了绘图师，基于前序结果生成可视化并并入结果
            try:
                if "charting_artist" in self.selected_agents:
                    ca = self.agents.get("charting_artist")
                    if ca is None:
                        ca = ChartingArtist(self.multi_model_manager, config=self.config)
                        self.agents["charting_artist"] = ca

                    # 尝试准备结构化OHLC，优先走统一接口（DEMO_MODE下自动回放）
                    market_data_payload = None
                    try:
                        from tradingagents.dataflows.interface import (
                            get_stock_ohlc_json,
                        )

                        # 取近 _period_days 天的数据窗口
                        from datetime import datetime, timedelta

                        end_dt = (
                            datetime.strptime(
                                str(analysis_data.get("analysis_date")[:10]),
                                "%Y-%m-%d",
                            )
                            if analysis_data.get("analysis_date")
                            else datetime.now()
                        )
                        _depth_days = {1: 14, 2: 21, 3: 30, 4: 60, 5: 90}
                        period_days = _depth_days.get(
                            int(analysis_data.get("research_depth") or 3), 30
                        )
                        start_dt = end_dt - timedelta(days=period_days)
                        ohlc = get_stock_ohlc_json(
                            analysis_data.get("stock_symbol"),
                            start_dt.strftime("%Y-%m-%d"),
                            end_dt.strftime("%Y-%m-%d"),
                        )
                        recs = ohlc.get("records") or []
                        if recs:
                            # 列表转列式结构
                            cols = {k: [] for k in ["date", "open", "high", "low", "close", "volume"]}
                            for r in recs:
                                for k in cols.keys():
                                    cols[k].append(r.get(k))
                            market_data_payload = {"price_data": cols}
                    except Exception:
                        market_data_payload = None

                    symbol = analysis_data.get("stock_symbol", "N/A")
                    with telemetry.span(
                        "charting.generate",
                        analysis_id=aid,
                        component="charting",
                        data={"symbol": symbol},
                    ) as span:
                        viz = ca.generate_visualizations(
                            symbol=symbol,
                            analysis_results=results,
                            market_data=market_data_payload,
                            runtime_config={},
                        )
                        try:
                            span.update(
                                {
                                    "charts": len(viz.get("charts_generated") or []),
                                    "errors": len(viz.get("errors") or []),
                                }
                            )
                        except Exception:
                            pass
                    results["charting_artist"] = {
                        "agent_type": "charting_artist",
                        "analysis": ca.get_chart_summary(viz),
                        "visualizations": viz,
                        "timestamp": datetime.now().isoformat(),
                    }
            except Exception as _viz_e:
                try:
                    results["charting_artist"] = {
                        "agent_type": "charting_artist",
                        "analysis": f"绘图师生成失败: {_viz_e}",
                        "status": "failed",
                        "timestamp": datetime.now().isoformat(),
                    }
                except Exception:
                    pass

            out = {
                "status": "success",
                "collaboration_mode": self.collaboration_mode,
                "agents_used": list(self.selected_agents),
                "analysis_data": analysis_data,
                "results": results,
                "final_article": final_article,
                "final_article_metrics": article_metrics,
                "is_demo": bool(demo_sections),
                "timestamp": datetime.now().isoformat(),
            }
            telemetry.emit(
                "multi_model.done",
                analysis_id=aid,
                component="web",
                data={
                    "agents": list(self.selected_agents),
                    "has_article": bool(final_article),
                    "charts": len(
                        ((results.get("charting_artist") or {}).get("visualizations") or {}
                        ).get("charts_generated")
                        or []
                    ),
                },
            )
            return out

        except Exception as e:
            logger.error(f"❌ 协作分析失败: {e}")
            try:
                telemetry.emit(
                    "multi_model.error",
                    analysis_id=locals().get("aid"),
                    component="web",
                    level="error",
                    data={"error": str(e)},
                )
            except Exception:
                pass
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _run_sequential_analysis(
        self, analysis_data: dict[str, Any], progress_callback=None
    ) -> dict[str, Any]:
        """运行串行协作分析"""
        results = {}
        previous_results = []
        # 预先构建模型覆盖映射（会话 > 持久化）
        try:
            built_overrides = self._build_model_overrides()
        except Exception:
            built_overrides = {}

        for agent_type in self.selected_agents:
            try:
                logger.info(f"🤖 运行智能体: {agent_type}")
                if progress_callback:
                    try:
                        progress_callback(
                            {
                                "stage": "agent_start",
                                "agent": agent_type,
                                "message": f"{agent_type} 开始分析",
                            }
                        )
                    except Exception:
                        pass

                # 准备智能体输入数据

                # 真正执行AI分析
                try:
                    # 构建智能体任务提示词（支持角色库自定义）
                    task_prompt = self._build_prompt_for_role(
                        agent_type, analysis_data, previous_results
                    )

                    # 透传上下文（含模型覆盖）；低研究深度优先快速响应
                    fast_pref = (
                        analysis_data.get("research_depth", 3) is not None
                        and analysis_data.get("research_depth", 3) <= 2
                    )
                    exec_context = {
                        "session_id": f"web_multi_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "market_type": analysis_data.get("market_type", "A股"),
                        "stock_symbol": analysis_data["stock_symbol"],
                        # 速度偏好与软超时提示（供路由引擎与默认选择使用）
                        "priority": "high" if fast_pref else "normal",
                        "time_limit": 8000 if fast_pref else None,  # ms（提示性质）
                        "real_time": True if fast_pref else False,
                        "model_params": {
                            "stream": True,
                            "on_token": (
                                lambda t, agent=agent_type: (
                                    progress_callback(
                                        {"stage": "token", "agent": agent, "delta": t}
                                    )
                                    if progress_callback
                                    else None
                                )
                            ),
                        },
                    }
                    if built_overrides:
                        exec_context["model_overrides"] = built_overrides

                    # 使用多模型管理器执行任务
                    task_result = self.multi_model_manager.execute_task(
                        agent_role=agent_type,
                        task_prompt=task_prompt,
                        task_type=self._get_task_type_for_agent(agent_type),
                        complexity_level=(
                            "medium"
                            if analysis_data.get("research_depth", 3) <= 3
                            else "high"
                        ),
                        context=exec_context,
                    )

                    if task_result.success:
                        agent_result = {
                            "agent_type": agent_type,
                            "analysis": task_result.result,
                            "confidence": 0.85,
                            "recommendations": self._extract_recommendations(
                                task_result.result
                            ),
                            "timestamp": datetime.now().isoformat(),
                            "model_used": (
                                task_result.model_used.name
                                if task_result.model_used
                                else "unknown"
                            ),
                            "execution_time": task_result.execution_time,
                            "token_usage": task_result.token_usage,
                        }
                    else:
                        # 如果AI调用失败，回退到模拟结果
                        agent_result = {
                            "agent_type": agent_type,
                            "analysis": f"分析失败: {task_result.error_message}",
                            "confidence": 0.0,
                            "recommendations": "暂无建议",
                            "timestamp": datetime.now().isoformat(),
                            "error": task_result.error_message,
                        }
                except Exception as ai_error:
                    logger.warning(f"AI分析失败，使用模拟结果: {ai_error}")
                    # 回退到模拟结果
                    agent_result = {
                        "agent_type": agent_type,
                        "analysis": f"这是 {agent_type} 对 {analysis_data['stock_symbol']} 的分析结果（模拟）",
                        "confidence": 0.85,
                        "recommendations": f"{agent_type} 的投资建议",
                        "timestamp": datetime.now().isoformat(),
                    }

                results[agent_type] = agent_result
                previous_results.append(agent_result)

                logger.info(f"✅ {agent_type} 分析完成")
                if progress_callback:
                    try:
                        progress_callback(
                            {
                                "stage": "agent_done",
                                "agent": agent_type,
                                "message": f"{agent_type} 分析完成",
                            }
                        )
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"❌ {agent_type} 分析失败: {e}")
                results[agent_type] = {"error": str(e), "status": "failed"}
        # 补全占位：确保所有被选择的智能体在结果中都有条目（即便无输出/失败）
        try:
            for agent_type in self.selected_agents:
                if agent_type not in results:
                    results[agent_type] = {
                        "agent_type": agent_type,
                        "analysis": "",
                        "status": "no_output",
                    }
        except Exception:
            pass

        return results

    def _run_parallel_analysis(
        self, analysis_data: dict[str, Any], progress_callback=None
    ) -> dict[str, Any]:
        """运行并行协作分析"""
        results = {}
        # 预先构建模型覆盖映射（会话 > 持久化）
        try:
            built_overrides = self._build_model_overrides()
        except Exception:
            built_overrides = {}

        # 并行执行分析（线程池并发）
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
        except Exception:
            ThreadPoolExecutor = None

        def _run_one(agent_type: str):
            try:
                logger.info(f"🤖 并行运行智能体: {agent_type}")
                if progress_callback:
                    try:
                        progress_callback(
                            {
                                "stage": "agent_start",
                                "agent": agent_type,
                                "message": f"{agent_type} 开始分析",
                            }
                        )
                    except Exception:
                        pass
                # 构建提示词与上下文
                task_prompt = self._build_prompt_for_role(agent_type, analysis_data)
                fast_pref = (
                    analysis_data.get("research_depth", 3) is not None
                    and analysis_data.get("research_depth", 3) <= 2
                )
                exec_context = {
                    "session_id": f"web_multi_parallel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "market_type": analysis_data.get("market_type", "A股"),
                    "stock_symbol": analysis_data["stock_symbol"],
                    "priority": "high" if fast_pref else "normal",
                    "time_limit": 8000 if fast_pref else None,
                    "real_time": True if fast_pref else False,
                    "model_params": {
                        "stream": True,
                        "on_token": (
                            lambda t, agent=agent_type: (
                                progress_callback(
                                    {"stage": "token", "agent": agent, "delta": t}
                                )
                                if progress_callback
                                else None
                            )
                        ),
                    },
                }
                if built_overrides:
                    exec_context["model_overrides"] = built_overrides
                task_result = self.multi_model_manager.execute_task(
                    agent_role=agent_type,
                    task_prompt=task_prompt,
                    task_type=self._get_task_type_for_agent(agent_type),
                    complexity_level=(
                        "medium"
                        if analysis_data.get("research_depth", 3) <= 3
                        else "high"
                    ),
                    context=exec_context,
                )
                if task_result.success:
                    return agent_type, {
                        "agent_type": agent_type,
                        "analysis": task_result.result,
                        "confidence": 0.80,
                        "recommendations": self._extract_recommendations(
                            task_result.result
                        ),
                        "timestamp": datetime.now().isoformat(),
                        "model_used": (
                            task_result.model_used.name
                            if task_result.model_used
                            else "unknown"
                        ),
                    }
                else:
                    return agent_type, {
                        "agent_type": agent_type,
                        "analysis": f"分析失败: {task_result.error_message}",
                        "confidence": 0.0,
                        "recommendations": "暂无建议",
                        "timestamp": datetime.now().isoformat(),
                    }
            except Exception as _e:
                logger.error(f"❌ {agent_type} 并行分析失败: {_e}")
                return agent_type, {"error": str(_e), "status": "failed"}
            finally:
                if progress_callback:
                    try:
                        progress_callback(
                            {
                                "stage": "agent_done",
                                "agent": agent_type,
                                "message": f"{agent_type} 分析完成",
                            }
                        )
                    except Exception:
                        pass

        if ThreadPoolExecutor is None:
            # 兜底：顺序执行
            for a in self.selected_agents:
                k, v = _run_one(a)
                results[k] = v
        else:
            max_workers = max(
                1,
                min(
                    len(self.selected_agents),
                    getattr(self.multi_model_manager, "max_concurrent_tasks", 5),
                ),
            )
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {ex.submit(_run_one, a): a for a in self.selected_agents}
                for fut in as_completed(futs):
                    k, v = fut.result()
                    results[k] = v

        # 补全占位：确保所有被选择的智能体在结果中都有条目（即便无输出/失败）
        try:
            for agent_type in self.selected_agents:
                if agent_type not in results:
                    results[agent_type] = {
                        "agent_type": agent_type,
                        "analysis": "",
                        "status": "no_output",
                    }
        except Exception:
            pass

        # 整合并行分析结果
        results["summary"] = self._integrate_parallel_results(results)

        return results

    def _run_debate_analysis(
        self, analysis_data: dict[str, Any], progress_callback=None
    ) -> dict[str, Any]:
        """运行辩论协作分析"""
        results = {}

        # 第一轮：各智能体独立分析
        independent_results = {}
        for agent_type in self.selected_agents:
            try:
                logger.info(f"🤖 辩论第1轮 - {agent_type}")
                if progress_callback:
                    try:
                        progress_callback(
                            {
                                "stage": "debate_round1",
                                "agent": agent_type,
                                "message": f"{agent_type} 提交初始观点",
                            }
                        )
                    except Exception:
                        pass

                agent_result = {
                    "agent_type": agent_type,
                    "analysis": f"{agent_type} 对 {analysis_data['stock_symbol']} 的初始观点（模拟）",
                    "stance": (
                        "bullish"
                        if agent_type in ["fundamental_expert", "news_hunter"]
                        else "bearish"
                    ),
                    "confidence": 0.75,
                    "timestamp": datetime.now().isoformat(),
                }

                independent_results[agent_type] = agent_result

            except Exception as e:
                logger.error(f"❌ {agent_type} 辩论分析失败: {e}")
                independent_results[agent_type] = {"error": str(e), "status": "failed"}

        # 第二轮：辩论和共识
        consensus_result = self._generate_consensus(independent_results, analysis_data)
        if progress_callback:
            try:
                progress_callback(
                    {"stage": "debate_consensus", "message": "辩论共识生成完成"}
                )
            except Exception:
                pass

        results["independent_analyses"] = independent_results
        results["consensus"] = consensus_result

        return results

    def _integrate_parallel_results(self, results: dict[str, Any]) -> dict[str, Any]:
        """整合并行分析结果"""
        return {
            "integration_method": "weighted_average",
            "overall_recommendation": "基于多智能体并行分析的综合建议（模拟）",
            "confidence_score": 0.82,
            "risk_level": "medium",
            "timestamp": datetime.now().isoformat(),
        }

    def _compose_final_article(
        self, results: dict[str, Any], analysis_data: dict[str, Any]
    ) -> (str, dict[str, Any]):
        """使用主笔人（Gemini-2.5-Pro）生成规整长文"""
        try:
            # 准备专家分析列表（兼容顺序/并行结果字典），按角色一致顺序并裁剪过长文本
            def _clip(txt: str, limit: int = 3000) -> str:
                if not isinstance(txt, str):
                    return ""
                return txt if len(txt) <= limit else txt[:limit] + "\n...(内容截断)"

            role_order = [
                "news_hunter",
                "fundamental_expert",
                "technical_analyst",
                "sentiment_analyst",
                "risk_manager",
                "policy_researcher",
                "compliance_officer",
                "tool_engineer",
                "chief_decision_officer",
            ]

            expert_analyses: list[dict[str, Any]] = []
            # 先按既定顺序收集
            for rk in role_order:
                val = results.get(rk)
                if isinstance(val, dict) and isinstance(val.get("analysis"), str):
                    expert_analyses.append(
                        {
                            "agent_role": val.get("agent_type", rk),
                            "analysis_content": _clip(val.get("analysis", "")),
                            "confidence_score": val.get("confidence", 0.7),
                            "recommendations": val.get("recommendations", []),
                            "key_points": [],
                            "risk_factors": [],
                        }
                    )
            # 再合并其他可能键（并行/辩论结果等）
            for key, value in results.items():
                if key in role_order:
                    continue
                if isinstance(value, dict) and isinstance(value.get("analysis"), str):
                    expert_analyses.append(
                        {
                            "agent_role": value.get("agent_type", key),
                            "analysis_content": _clip(value.get("analysis", "")),
                            "confidence_score": value.get("confidence", 0.7),
                            "recommendations": value.get("recommendations", []),
                            "key_points": [],
                            "risk_factors": [],
                        }
                    )

            if not expert_analyses:
                return "", {}

            # 初始化或复用主笔人
            writer = self.agents.get("chief_writer")
            if writer is None:
                try:
                    writer = ChiefWriter(self.multi_model_manager, config=self.config)
                    self.agents["chief_writer"] = writer
                except Exception:
                    return "", {}

            writer_input = {
                "expert_analyses": expert_analyses,
                "market_context": {
                    "market_type": analysis_data.get("market_type"),
                    "stock_symbol": analysis_data.get("stock_symbol"),
                    "stock_name": analysis_data.get("stock_name"),
                    "analysis_date": analysis_data.get("analysis_date"),
                },
                "collaboration_mode": self.collaboration_mode,
            }

            # 构建模型覆盖（优先使用本次会话的覆盖，其次使用持久化的角色中心绑定）
            context_payload = {"priority": "quality_first"}
            try:
                model_overrides = self._build_model_overrides()
                if isinstance(model_overrides, dict) and model_overrides:
                    context_payload["model_overrides"] = model_overrides
            except Exception:
                pass

            article_result = writer.analyze(
                input_data=writer_input,
                context=context_payload,
                complexity_level="high",
            )

            return article_result.analysis_content, article_result.supporting_data
        except Exception as e:
            logger.error(f"主笔人生成长文失败: {e}")
            return "", {}

    def _generate_consensus(
        self, independent_results: dict[str, Any], analysis_data: dict[str, Any]
    ) -> dict[str, Any]:
        """生成辩论共识"""
        return {
            "consensus_method": "debate_resolution",
            "final_recommendation": f"经过多轮辩论，对 {analysis_data['stock_symbol']} 的最终共识（模拟）",
            "agreement_level": 0.78,
            "dissenting_opinions": ["部分智能体持保留意见"],
            "timestamp": datetime.now().isoformat(),
        }

    def _build_agent_prompt(
        self,
        agent_type: str,
        analysis_data: dict[str, Any],
        previous_results: list[dict[str, Any]] = None,
    ) -> str:
        """构建智能体的任务提示词"""
        stock_symbol = analysis_data.get("stock_symbol", "")
        stock_name = analysis_data.get("stock_name") or ""
        market_type = analysis_data.get("market_type", "A股")
        analysis_date = analysis_data.get(
            "analysis_date", datetime.now().strftime("%Y-%m-%d")
        )
        custom_requirements = analysis_data.get("custom_requirements", "")

        name_part = f"（{stock_name}）" if stock_name else ""
        base_prompt = f"""请作为{self._get_agent_chinese_name(agent_type)}分析{market_type}股票 {stock_symbol}{name_part}。
分析日期：{analysis_date}

请提供专业、深入的分析，包括：
1. 从你的专业角度分析这只股票
2. 给出具体的投资建议
3. 评估相关风险和机会
"""

        if custom_requirements:
            base_prompt += f"\n特别要求：{custom_requirements}\n"

        # 若演示模式传入了已准备好的“输入数据”片段，则将其作为上下文附加
        demo_sections = analysis_data.get("demo_sections") or {}
        if isinstance(demo_sections, dict) and demo_sections:
            section_map = {
                "fundamental_expert": "fundamentals_report",
                "news_hunter": "news_report",
                "technical_analyst": "market_report",
                "sentiment_analyst": "sentiment_report",
                "risk_manager": "risk_assessment",
                "policy_researcher": "policy_report",
                "compliance_officer": "compliance_report",
                "tool_engineer": "engineering_report",
            }
            key = section_map.get(agent_type)
            if key and demo_sections.get(key):
                base_prompt += (
                    "\n\n【参考数据(演示)】\n" + str(demo_sections.get(key)) + "\n"
                )

        if (
            previous_results and agent_type != "news_hunter"
        ):  # 第一个智能体不需要前置结果
            base_prompt += "\n前面的分析结果：\n"
            for prev in previous_results[-2:]:  # 只包含最近2个分析
                base_prompt += (
                    f"- {prev['agent_type']}: {prev.get('analysis', '')[:200]}...\n"
                )

        return base_prompt

    def _build_prompt_for_role(
        self,
        agent_type: str,
        analysis_data: dict[str, Any],
        previous_results: list[dict[str, Any]] = None,
    ) -> str:
        """优先使用角色库模板生成提示，否则回退到通用提示。

        修复点：原实现仅返回 system_prompt，且上下文键使用了 ticker 等不匹配占位符，
        导致未包含具体标的（如 000625），模型易输出与标的不符的示例内容（如贵州茅台）。
        现合并 system_prompt + analysis_prompt_template，并提供匹配占位符的上下文。"""
        try:
            from tradingagents.config.role_library import format_prompt, get_prompt

            # 构建上下文，兼容常见占位符命名
            symbol = analysis_data.get("stock_symbol", "")
            company_name = analysis_data.get("stock_name") or symbol
            market_type = analysis_data.get("market_type", "")
            analysis_date = analysis_data.get("analysis_date", "")
            custom_requirements = analysis_data.get("custom_requirements", "")

            # 计算可选时间范围（部分模板可能需要）
            start_date = ""
            end_date = ""
            try:
                from datetime import datetime, timedelta

                if analysis_date:
                    dt = datetime.strptime(str(analysis_date), "%Y-%m-%d")
                else:
                    dt = datetime.now()
                end_date = dt.strftime("%Y-%m-%d")
                start_date = (dt - timedelta(days=60)).strftime("%Y-%m-%d")
            except Exception:
                pass

            ctx = {
                # 常用占位符
                "symbol": symbol,
                "ticker": symbol,
                "company_name": company_name,
                "market_type": market_type,
                "current_date": analysis_date,
                "analysis_date": analysis_date,
                "start_date": start_date,
                "end_date": end_date,
                "custom_requirements": custom_requirements,
                "previous_results": previous_results or [],
            }

            sys_tpl = get_prompt(agent_type, "system_prompt") or ""
            ana_tpl = get_prompt(agent_type, "analysis_prompt_template") or ""

            parts: list[str] = []
            if sys_tpl.strip():
                parts.append(format_prompt(sys_tpl, ctx))

            if ana_tpl.strip():
                # 角色分析模板存在 → 使用模板并注入上下文
                parts.append(format_prompt(ana_tpl, ctx))
            else:
                # 无分析模板 → 回退到基础提示（确保包含标的与前置结果）
                parts.append(
                    self._build_agent_prompt(
                        agent_type, analysis_data, previous_results
                    )
                )

            # 附带前置结果摘要（若模板未涵盖）
            if previous_results and ana_tpl.strip():
                try:
                    snippet = "\n前置分析摘要（最近2条）：\n"
                    for prev in previous_results[-2:]:
                        txt = str(prev.get("analysis", ""))[:200]
                        snippet += f"- {prev.get('agent_type', '')}: {txt}...\n"
                    parts.append(snippet)
                except Exception:
                    pass

            final_prompt = "\n\n".join([p for p in parts if p and p.strip()])

            # 若演示模式传入了已准备好的“输入数据”片段，则在模板后追加对应片段
            demo_sections = analysis_data.get("demo_sections") or {}
            if isinstance(demo_sections, dict) and demo_sections:
            section_map = {
                "fundamental_expert": "fundamentals_report",
                "news_hunter": "news_report",
                "technical_analyst": "market_report",
                "sentiment_analyst": "sentiment_report",
                "risk_manager": "risk_assessment",
                "policy_researcher": "policy_report",
                "compliance_officer": "compliance_report",
                "tool_engineer": "engineering_report",
            }
                key = section_map.get(agent_type)
                if key and demo_sections.get(key):
                    final_prompt += (
                        "\n\n【参考数据(演示)】\n" + str(demo_sections.get(key)) + "\n"
                    )

            # 统一增加“禁止无数据免责声明”约束，避免出现“无法获取数据”等措辞
            try:
                import os as _os

                demo_mode = str(_os.getenv("DEMO_MODE", "false")).lower() == "true"
            except Exception:
                demo_mode = False

            no_excuses_clause = (
                "\n\n[重要约束]\n"
                "- 请严格基于以上提供的数据与上下文进行分析；"
                "禁止出现如“无法获取数据/无法实时获取/数据不可用”之类的免责声明。"
                "如需提示不确定性，请使用“需进一步验证”表述，不得以无法获取为理由。"
            )

            # 在演示模式或常规模式都加，增强一致性
            final_prompt += no_excuses_clause
            return final_prompt
        except Exception:
            # 任何异常下回退到基础提示，确保包含标的
            return self._build_agent_prompt(agent_type, analysis_data, previous_results)

    def _get_task_type_for_agent(self, agent_type: str) -> str:
        """获取智能体对应的任务类型"""
        # 先尝试角色库覆盖
        try:
            from tradingagents.config.provider_models import model_provider_manager

            custom = model_provider_manager.role_task_types.get(agent_type)
            if isinstance(custom, str) and custom:
                return custom
        except Exception:
            pass
        task_mapping = {
            "news_hunter": "news_analysis",
            "fundamental_expert": "fundamental_analysis",
            "technical_analyst": "technical_analysis",
            "sentiment_analyst": "sentiment_analysis",
            "risk_manager": "risk_assessment",
            "policy_researcher": "policy_analysis",
            "tool_engineer": "technical_analysis",
            "compliance_officer": "compliance_check",
            "chief_decision_officer": "decision_making",
        }
        return task_mapping.get(agent_type, "general")

    def _get_agent_chinese_name(self, agent_type: str) -> str:
        """获取智能体的中文名称"""
        try:
            from tradingagents.config.provider_models import model_provider_manager

            cfg = model_provider_manager.role_definitions.get(agent_type)
            if cfg and cfg.name:
                return cfg.name
        except Exception:
            pass
        name_mapping = {
            "news_hunter": "快讯猎手",
            "fundamental_expert": "基本面专家",
            "technical_analyst": "技术分析师",
            "sentiment_analyst": "情绪分析师",
            "risk_manager": "风控经理",
            "policy_researcher": "政策研究员",
            "tool_engineer": "工具工程师",
            "compliance_officer": "合规官",
            "chief_decision_officer": "首席决策官",
        }
        return name_mapping.get(agent_type, agent_type)

    def _extract_recommendations(self, analysis_text: str) -> str:
        """从分析文本中提取投资建议"""
        # 简单的关键词提取逻辑
        if "建议买入" in analysis_text or "强烈推荐" in analysis_text:
            return "买入建议"
        elif "建议卖出" in analysis_text or "建议减持" in analysis_text:
            return "卖出建议"
        elif "建议持有" in analysis_text or "观望" in analysis_text:
            return "持有建议"
        else:
            # 尝试提取包含"建议"的句子
            import re

            matches = re.findall(r"[^。]*建议[^。]*。", analysis_text)
            if matches:
                return matches[0]
            return "请参考详细分析"

    def _build_model_overrides(self) -> dict[str, str]:
        """构建按角色的模型覆盖映射。

        优先级：Session 会话覆盖 > 持久化的角色中心绑定（config/ui_role_overrides.json）。
        返回值示例：{"chief_writer": "moonshotai/Kimi-K2-Instruct", ...}
        """
        overrides: dict[str, str] = {}

        # 1) 先加载持久化的角色中心绑定
        try:
            from .ui_utils import load_persistent_role_configs

            cfg = load_persistent_role_configs()
            role_overrides = cfg.get("role_overrides", {})
            if isinstance(role_overrides, dict):
                for role_key, role_cfg in role_overrides.items():
                    if isinstance(role_cfg, dict):
                        model = role_cfg.get("model")
                        if isinstance(model, str) and model:
                            overrides[role_key] = model
        except Exception:
            pass

        # 2) 再叠加本次会话中的临时覆盖（若存在则覆盖掉持久化）
        try:
            import streamlit as st  # 仅在 Web 环境可用

            session_overrides = getattr(st.session_state, "model_overrides", None)
            if isinstance(session_overrides, dict):
                for role_key, model in session_overrides.items():
                    if isinstance(model, str) and model:
                        overrides[role_key] = model
        except Exception:
            pass

        return overrides
