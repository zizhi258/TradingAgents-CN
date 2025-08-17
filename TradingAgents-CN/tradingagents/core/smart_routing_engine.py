"""
Smart Routing Engine
AI驱动的智能路由系统，负责根据任务特性选择最优模型
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

from .base_multi_model_adapter import ModelProvider, ModelSpec, TaskComplexity, TaskSpec

logger = get_logger("smart_routing_engine")


@dataclass
class RoutingDecision:
    """路由决策结果"""

    selected_model: str
    provider: str
    confidence_score: float
    reasoning: str
    estimated_cost: float
    estimated_time: int
    alternative_models: list[str] = None
    routing_strategy: str = "intelligent"


@dataclass
class ModelPerformanceData:
    """模型性能数据"""

    model_name: str
    provider: str
    task_type: str
    avg_response_time: float
    success_rate: float
    cost_efficiency: float  # 性价比分数
    quality_score: float
    last_updated: datetime


class SmartRoutingEngine:
    """AI驱动的智能路由系统"""

    def __init__(self, database_path: str = None, config: dict[str, Any] = None):
        self.config = config or {}
        self.database_path = database_path or self._get_default_db_path()

        # 三池旗舰模型路由策略权重配置（质量优先）
        self.routing_weights = self.config.get(
            "weights",
            {
                "quality": 0.6,  # 质量权重最高
                "performance": 0.3,  # 性能权重
                "cost": 0.1,  # 成本权重最低（质量优先）
                "availability": 0.0,  # 可用性通过fallback保证
            },
        )

        # 强制多样化配置
        self.force_diversity = self.config.get("force_diversity", True)  # 默认启用
        self.model_usage_tracker = {}  # 跟踪模型使用情况
        self.diversity_threshold = self.config.get(
            "diversity_threshold", 0.4
        )  # 降低阈值到40%
        self.diversity_weight = self.config.get(
            "diversity_weight", 0.8
        )  # 提高多样化权重

        # 三池映射配置 - 调整为两池架构
        self.pool_mapping = self.config.get(
            "pool_mapping",
            {
                "deep_reasoning": {
                    "flagship_model": "gemini-2.5-pro",
                    "target_agents": [
                        "fundamental_expert",
                        "chief_decision_officer",
                        "risk_manager",
                        "policy_researcher",
                        "compliance_officer",
                    ],
                    "task_types": [
                        "financial_report",
                        "risk_assessment",
                        "decision_making",
                        "policy_analysis",
                        "compliance_check",
                    ],
                    "capabilities": [
                        "multimodal",
                        "long_context",
                        "financial_analysis",
                        "reasoning_chains",
                    ],
                },
                "technical_longseq": {
                    "flagship_model": "deepseek-ai/DeepSeek-V3",
                    "target_agents": [
                        "technical_analyst",
                        "news_hunter",
                        "sentiment_analyst",
                        "tool_engineer",
                    ],
                    "task_types": [
                        "technical_analysis",
                        "news_analysis",
                        "sentiment_analysis",
                        "tool_development",
                        "code_generation",
                        "backtesting",
                    ],
                    "capabilities": [
                        "long_context",
                        "chinese_optimized",
                        "technical_analysis",
                        "time_series",
                        "code_generation",
                    ],
                },
            },
        )

        # 三池旗舰模型能力映射
        self.flagship_model_capabilities = {
            # 🧠 通用深度推理池旗舰
            "gemini-2.5-pro": {
                "reasoning": 0.95,  # 最强推理能力
                "multimodal": 0.95,  # 原生多模态
                "long_context": 0.9,  # 30K+上下文
                "chinese": 0.8,  # 中文能力良好
                "financial_analysis": 0.92,  # 金融分析最佳
                "cost_efficiency": 0.6,  # 质量优先，成本次要
                "speed": 0.5,  # 深度推理需时
                "reliability": 0.95,  # 极高可靠性
            },
            # 🔄 技术面&长序列池旗舰
            "deepseek-ai/DeepSeek-V3": {
                "reasoning": 0.9,  # 强推理能力
                "multimodal": 0.7,  # 有限多模态
                "long_context": 0.95,  # 100K+上下文最佳
                "chinese": 0.95,  # 中文能力最强
                "technical_analysis": 0.92,  # 技术分析专长
                "time_series": 0.9,  # 长序列数据处理
                "cost_efficiency": 0.85,  # 高性价比
                "speed": 0.7,  # 较快速度
                "reliability": 0.9,  # 高可靠性
            },
        }

        # 旗舰模型专用token限制（不计成本）- 基于官网实际限制
        self.flagship_token_limits = self.config.get(
            "flagship_token_limits",
            {
                "gemini-2.5-pro": 1000000,  # Google官网 - 1M tokens
                "deepseek-ai/DeepSeek-V3": 128000,  # SiliconFlow平台 - 128K tokens (比DeepSeek官网64K更高)
            },
        )

        # 任务类型到池的映射权重 - 调整为两池架构
        self.task_pool_affinity = {
            "financial_report": {"deep_reasoning": 0.9, "technical_longseq": 0.1},
            "technical_analysis": {"deep_reasoning": 0.3, "technical_longseq": 0.9},
            "news_analysis": {"deep_reasoning": 0.2, "technical_longseq": 0.9},
            "sentiment_analysis": {"deep_reasoning": 0.3, "technical_longseq": 0.9},
            "risk_assessment": {"deep_reasoning": 0.9, "technical_longseq": 0.2},
            "decision_making": {"deep_reasoning": 0.95, "technical_longseq": 0.4},
            "policy_analysis": {"deep_reasoning": 0.9, "technical_longseq": 0.1},
            "code_generation": {
                "deep_reasoning": 0.1,
                "technical_longseq": 0.95,
            },  # 代码任务转给technical_longseq
            "tool_development": {"deep_reasoning": 0.2, "technical_longseq": 0.9},
            "backtesting": {"deep_reasoning": 0.3, "technical_longseq": 0.9},  # 新增
            "compliance_check": {"deep_reasoning": 0.9, "technical_longseq": 0.0},
            "fundamental_analysis": {"deep_reasoning": 0.9, "technical_longseq": 0.1},
            "general": {"deep_reasoning": 0.6, "technical_longseq": 0.4},
        }

        # 模型特性配置
        self.model_capabilities = {
            # SiliconFlow模型 - 使用正确的模型名称
            "deepseek-ai/DeepSeek-R1": {
                "reasoning": 0.95,
                "speed": 0.5,
                "chinese": 0.8,
                "cost": 0.6,
                "reliability": 0.9,
            },
            "deepseek-ai/DeepSeek-V3": {
                "reasoning": 0.9,
                "speed": 0.7,
                "chinese": 0.85,
                "cost": 0.8,
                "reliability": 0.9,
            },
            "moonshotai/Kimi-K2-Instruct": {
                "reasoning": 0.8,
                "speed": 0.6,
                "chinese": 0.8,
                "long_context": 0.95,
                "cost": 0.6,
                "reliability": 0.8,
            },
            "Qwen/Qwen2.5-Coder-32B-Instruct": {
                "reasoning": 0.8,
                "speed": 0.7,
                "chinese": 0.9,
                "code_generation": 0.95,
                "cost": 0.8,
                "reliability": 0.85,
            },
            # 移除 Qwen2.5 旧系列（72B）
            "deepseek-ai/deepseek-llm-67b-chat": {
                "reasoning": 0.8,
                "speed": 0.6,
                "chinese": 0.8,
                "cost": 0.7,
                "reliability": 0.85,
            },
            "meta-llama/Meta-Llama-3.1-405B-Instruct": {
                "reasoning": 0.9,
                "speed": 0.4,
                "chinese": 0.6,
                "cost": 0.5,
                "reliability": 0.85,
            },
            "meta-llama/Meta-Llama-3.1-70B-Instruct": {
                "reasoning": 0.85,
                "speed": 0.6,
                "chinese": 0.6,
                "cost": 0.7,
                "reliability": 0.85,
            },
            # Google模型 - 保持 2.5 家族配置，gemini-2.5-pro优先级最高
            "gemini-2.5-pro": {
                "reasoning": 0.95,
                "multimodal": 0.95,
                "long_context": 0.9,
                "chinese": 0.8,
                "financial_analysis": 0.92,
                "speed": 0.5,
                "cost": 0.3,
                "reliability": 0.95,
            },
            "Qwen/Qwen3-235B-A22B-Instruct-2507": {
                "reasoning": 0.92,
                "speed": 0.5,
                "chinese": 0.95,
                "long_context": 0.9,
                "cost": 0.4,
                "reliability": 0.9,
            },
            # 已移除 1.5/2.0 系列
            "gemini-2.5-flash": {
                "reasoning": 0.85,
                "speed": 0.9,
                "chinese": 0.8,
                "cost": 0.8,
                "reliability": 0.9,
            },
            # DeepSeek直连
            "deepseek-chat": {
                "reasoning": 0.85,
                "speed": 0.7,
                "chinese": 0.85,
                "cost": 0.8,
                "reliability": 0.85,
            },
        }

        # 初始化数据库表结构（如果需要）
        self._initialize_database_tables()

        # 验证路由引擎可用性
        usability_status = self._validate_engine_usability()
        if usability_status["usable"]:
            logger.info(f"智能路由引擎初始化完成 - {usability_status['message']}")
        else:
            logger.warning(
                f"智能路由引擎初始化完成但存在问题 - {usability_status['message']}"
            )

    def route_task(
        self,
        task_description: str,
        agent_role: str,
        task_spec: TaskSpec,
        available_models: dict[str, ModelSpec],
        context: dict[str, Any] = None,
    ) -> RoutingDecision:
        """
        基于三池旗舰模型架构进行任务路由（支持强制多样化）

        Args:
            task_description: 任务描述
            agent_role: 智能体角色
            task_spec: 任务规格
            available_models: 可用模型列表
            context: 上下文信息

        Returns:
            RoutingDecision: 路由决策结果
        """
        context = context or {}

        try:
            # 如果启用强制多样化，先检查是否需要多样化路由
            if self.force_diversity and self._should_diversify_routing(
                agent_role, available_models
            ):
                diverse_decision = self._route_with_diversity(
                    task_description, agent_role, task_spec, available_models, context
                )
                if diverse_decision:
                    return diverse_decision

            # 优先尝试三池旗舰模型路由
            pool_decision = self._route_with_flagship_pools(
                task_description, agent_role, task_spec, available_models, context
            )
            if pool_decision:
                return pool_decision

            # 回退到传统路由逻辑
            return self._route_with_traditional_logic(
                task_description, agent_role, task_spec, available_models, context
            )

        except Exception as e:
            logger.error(f"智能路由失败: {e}", exc_info=True)
            # 最终回退到默认选择
            default_model = self._get_default_model(available_models, task_spec)
            return RoutingDecision(
                selected_model=default_model.name,
                provider=default_model.provider.value,
                confidence_score=0.3,
                reasoning=f"路由失败，使用默认模型: {str(e)}",
                estimated_cost=0.01,
                estimated_time=5000,
                routing_strategy="fallback",
            )

    def _route_with_flagship_pools(
        self,
        task_description: str,
        agent_role: str,
        task_spec: TaskSpec,
        available_models: dict[str, ModelSpec],
        context: dict[str, Any],
    ) -> RoutingDecision | None:
        """使用三池旗舰模型架构进行路由"""
        try:
            # 1. 确定目标池
            target_pool = self._determine_target_pool(agent_role, task_spec, context)
            if not target_pool:
                return None

            # 2. 获取目标池的旗舰模型（若速度优先，深度推理池尝试使用Flash）
            flagship_model = self.pool_mapping[target_pool]["flagship_model"]
            try:
                speed_preferred = bool(getattr(task_spec, "requires_speed", False))
            except Exception:
                speed_preferred = False
            if speed_preferred and target_pool == "deep_reasoning":
                # 在可用模型中优先选择Flash系列
                for candidate in [
                    "gemini-2.5-flash",
                ]:
                    if candidate in available_models:
                        flagship_model = candidate
                        break

            # 3. 检查旗舰模型是否可用
            if flagship_model in available_models:
                model_spec = available_models[flagship_model]

                # 4. 计算置信度和成本
                confidence_score = self._calculate_pool_confidence(
                    target_pool, agent_role, task_spec
                )
                estimated_cost = self._estimate_task_cost(model_spec, task_spec)
                estimated_time = self._estimate_flagship_execution_time(
                    flagship_model, task_spec
                )

                # 5. 生成推理说明
                reasoning = self._generate_pool_reasoning(
                    target_pool, flagship_model, agent_role, task_spec
                )

                # 6. 获取备选模型
                alternative_models = self._get_pool_alternatives(
                    target_pool, available_models
                )

                decision = RoutingDecision(
                    selected_model=flagship_model,
                    provider=model_spec.provider.value,
                    confidence_score=confidence_score,
                    reasoning=reasoning,
                    estimated_cost=estimated_cost,
                    estimated_time=estimated_time,
                    alternative_models=alternative_models,
                    routing_strategy="flagship_pool",
                )

                # 7. 记录路由决策和更新使用统计
                self._log_routing_decision(decision, agent_role, task_spec, context)
                if self.force_diversity:
                    self._update_model_usage(flagship_model)

                logger.info(
                    f"三池路由决策完成: {target_pool} 池 -> {flagship_model} (置信度: {confidence_score:.3f})"
                )
                return decision

            return None

        except Exception as e:
            logger.warning(f"三池路由失败: {e}")
            return None

    def _determine_target_pool(
        self, agent_role: str, task_spec: TaskSpec, context: dict[str, Any]
    ) -> str | None:
        """确定目标池"""
        # 1. 根据智能体角色确定池
        for pool_name, pool_config in self.pool_mapping.items():
            if agent_role in pool_config["target_agents"]:
                logger.debug(f"根据智能体角色 {agent_role} 选择池: {pool_name}")
                return pool_name

        # 2. 根据任务类型确定池
        if task_spec.task_type in self.task_pool_affinity:
            affinities = self.task_pool_affinity[task_spec.task_type]
            best_pool = max(affinities.items(), key=lambda x: x[1])[0]
            logger.debug(f"根据任务类型 {task_spec.task_type} 选择池: {best_pool}")
            return best_pool

        # 3. 根据特殊需求确定池
        if context.get("code_generation_required") or task_spec.task_type in [
            "code_generation",
            "tool_development",
            "backtesting",
        ]:
            return "technical_longseq"  # 代码任务分配给technical_longseq池

        if context.get("long_context") or task_spec.estimated_tokens > 20000:
            return "technical_longseq"

        if task_spec.requires_reasoning or task_spec.complexity == TaskComplexity.HIGH:
            return "deep_reasoning"

        # 4. 默认选择深度推理池
        logger.debug("无特定匹配，默认选择深度推理池")
        return "deep_reasoning"

    def _calculate_pool_confidence(
        self, pool_name: str, agent_role: str, task_spec: TaskSpec
    ) -> float:
        """计算池选择置信度"""
        confidence = 0.7  # 基础置信度

        # 智能体匹配加分
        if agent_role in self.pool_mapping[pool_name]["target_agents"]:
            confidence += 0.15

        # 任务类型匹配加分
        if task_spec.task_type in self.task_pool_affinity:
            affinity_score = self.task_pool_affinity[task_spec.task_type].get(
                pool_name, 0
            )
            confidence += affinity_score * 0.15

        # 复杂度匹配加分
        if (
            pool_name == "deep_reasoning"
            and task_spec.complexity == TaskComplexity.HIGH
        ):
            confidence += 0.1
        elif pool_name == "technical_longseq" and task_spec.estimated_tokens > 10000:
            confidence += 0.1
        elif pool_name == "technical_longseq" and task_spec.task_type in [
            "code_generation",
            "tool_development",
            "backtesting",
        ]:
            confidence += 0.15

        return min(confidence, 0.95)

    def _generate_pool_reasoning(
        self, pool_name: str, model_name: str, agent_role: str, task_spec: TaskSpec
    ) -> str:
        """生成池选择推理说明"""
        pool_descriptions = {
            "deep_reasoning": f"🧠 通用深度推理池旗舰模型 {model_name}，擅长多模态逻辑推理和金融分析",
            "technical_longseq": f"🔄 技术面&长序列&代码池旗舰模型 {model_name}，支持100K+上下文、中文优化和代码生成",
        }

        base_reason = pool_descriptions.get(
            pool_name, f"使用{pool_name}池的{model_name}模型"
        )

        # 添加具体选择理由
        reasons = []
        if agent_role in self.pool_mapping[pool_name]["target_agents"]:
            reasons.append(f"针对{agent_role}智能体优化")

        if (
            task_spec.complexity == TaskComplexity.HIGH
            and pool_name == "deep_reasoning"
        ):
            reasons.append("高复杂度任务需求最强推理能力")

        if task_spec.estimated_tokens > 20000 and pool_name == "technical_longseq":
            reasons.append(f"长上下文({task_spec.estimated_tokens} tokens)任务")

        if (
            task_spec.task_type
            in ["code_generation", "tool_development", "backtesting"]
            and pool_name == "technical_longseq"
        ):
            reasons.append("代码生成和开发任务")

        if reasons:
            return f"{base_reason}，选择理由：{'、'.join(reasons)}"
        else:
            return base_reason

    def _get_pool_alternatives(
        self, pool_name: str, available_models: dict[str, ModelSpec]
    ) -> list[str]:
        """获取池内备选模型"""
        alternatives = []

        # 获取池内所有模型（除了旗舰模型）
        flagship = self.pool_mapping[pool_name]["flagship_model"]

        # 添加池内其他模型 - 调整为两池架构
        pool_models = {
            "deep_reasoning": ["Qwen/Qwen3-235B-A22B-Instruct-2507", "gemini-2.5-pro"],
            "technical_longseq": [
                # 已移除 R1
                "moonshotai/Kimi-K2-Instruct",
                # 已移除 Qwen2.5-72B 旧系列
                "deepseek-chat",
            ],
        }

        for model in pool_models.get(pool_name, []):
            if model in available_models and model != flagship:
                alternatives.append(model)

        return alternatives[:3]  # 最多3个备选

    def _estimate_flagship_execution_time(
        self, model_name: str, task_spec: TaskSpec
    ) -> int:
        """估算旗舰模型执行时间"""
        base_times = {
            "gemini-2.5-pro": 8000,  # 深度推理需要更多时间
            "deepseek-ai/DeepSeek-V3": 5000,  # 中等速度，包含代码能力
        }

        base_time = base_times.get(model_name, 5000)

        # 根据任务复杂度调整
        if task_spec.complexity == TaskComplexity.HIGH:
            base_time = int(base_time * 1.5)
        elif task_spec.complexity == TaskComplexity.LOW:
            base_time = int(base_time * 0.8)

        # 根据token数调整
        if task_spec.estimated_tokens > 20000:
            base_time = int(base_time * 1.3)

        return base_time

    def _get_flagship_max_tokens(self, model_name: str) -> int:
        """获取旗舰模型的最大token限制（不计成本）"""
        return self.flagship_token_limits.get(model_name, 100000)  # 默认10万tokens

    def _should_diversify_routing(
        self, agent_role: str, available_models: dict[str, ModelSpec]
    ) -> bool:
        """判断是否应该进行多样化路由"""
        if not self.model_usage_tracker:
            return False

        # 计算当前主导模型的使用率
        total_usage = sum(self.model_usage_tracker.values())
        if total_usage < 2:  # 至少需要2次请求才开始判断
            return False

        # 找到使用最多的模型
        most_used_model = max(self.model_usage_tracker.items(), key=lambda x: x[1])
        dominant_usage_rate = most_used_model[1] / total_usage

        # 计算理想的平均使用率（如果所有模型都均匀使用）
        num_available_models = len(
            [m for m in available_models.keys() if m in self.model_capabilities]
        )
        ideal_usage_rate = (
            1.0 / num_available_models if num_available_models > 0 else 1.0
        )

        # 动态阈值：基于理想值 + 容忍值
        dynamic_threshold = ideal_usage_rate + 0.15  # 理想值 + 15%容忍度
        effective_threshold = min(self.diversity_threshold, dynamic_threshold)

        # 如果某个模型的使用率超过动态阈值，则需要多样化
        needs_diversification = dominant_usage_rate > effective_threshold

        if needs_diversification:
            logger.info(
                f"触发多样化路由：{most_used_model[0]} 使用率 {dominant_usage_rate:.2%} 超过动态阈值 {effective_threshold:.0%} (理想值:{ideal_usage_rate:.0%})"
            )

        return needs_diversification

    def _route_with_diversity(
        self,
        task_description: str,
        agent_role: str,
        task_spec: TaskSpec,
        available_models: dict[str, ModelSpec],
        context: dict[str, Any],
    ) -> RoutingDecision | None:
        """基于多样化策略进行路由"""
        try:
            # 找到使用最少的可用模型
            model_usage_scores = {}

            for model_name, model_spec in available_models.items():
                if model_name in self.model_capabilities:
                    # 使用情况得分（使用越少得分越高）
                    usage_count = self.model_usage_tracker.get(model_name, 0)
                    total_usage = sum(self.model_usage_tracker.values()) or 1
                    usage_score = 1.0 - (usage_count / total_usage)

                    # 基础能力得分
                    task_analysis = self._analyze_task_characteristics(
                        task_description, task_spec, context
                    )
                    capability_score = self._calculate_model_score(
                        model_name, model_spec, task_analysis, task_spec
                    )

                    # 综合得分：提高多样化权重到0.8，能力权重为0.2
                    diversity_weight = self.diversity_weight
                    capability_weight = 1.0 - diversity_weight
                    final_score = (
                        usage_score * diversity_weight
                        + capability_score * capability_weight
                    )
                    model_usage_scores[model_name] = {
                        "score": final_score,
                        "usage_score": usage_score,
                        "capability_score": capability_score,
                        "usage_count": usage_count,
                    }

            if not model_usage_scores:
                return None

            # 选择综合得分最高的模型
            best_model_name = max(
                model_usage_scores.items(), key=lambda x: x[1]["score"]
            )[0]
            best_model_spec = available_models[best_model_name]
            best_scores = model_usage_scores[best_model_name]

            # 计算置信度和成本
            confidence_score = min(best_scores["score"], 0.9)  # 多样化路由置信度稍低
            estimated_cost = self._estimate_task_cost(best_model_spec, task_spec)
            estimated_time = self._estimate_execution_time(best_model_name, task_spec)

            # 生成推理说明
            reasoning = self._generate_diversity_reasoning(
                best_model_name, best_scores, model_usage_scores
            )

            # 获取备选模型
            sorted_models = sorted(
                model_usage_scores.items(), key=lambda x: x[1]["score"], reverse=True
            )
            alternative_models = [model[0] for model in sorted_models[1:4]]

            decision = RoutingDecision(
                selected_model=best_model_name,
                provider=best_model_spec.provider.value,
                confidence_score=confidence_score,
                reasoning=reasoning,
                estimated_cost=estimated_cost,
                estimated_time=estimated_time,
                alternative_models=alternative_models,
                routing_strategy="diversity_forced",
            )

            # 更新使用统计
            self._update_model_usage(best_model_name)

            # 记录路由决策
            self._log_routing_decision(decision, agent_role, task_spec, context)

            logger.info(
                f"多样化路由决策完成: {best_model_name} (综合得分: {best_scores['score']:.3f}, 使用次数: {best_scores['usage_count']})"
            )
            return decision

        except Exception as e:
            logger.warning(f"多样化路由失败: {e}")
            return None

    def _generate_diversity_reasoning(
        self,
        selected_model: str,
        selected_scores: dict[str, float],
        all_scores: dict[str, dict],
    ) -> str:
        """生成多样化路由推理说明"""
        usage_count = selected_scores["usage_count"]
        usage_score = selected_scores["usage_score"]
        capability_score = selected_scores["capability_score"]

        base_reason = f"多样化路由选择 {selected_model}"

        reasons = []
        reasons.append(f"使用次数较少({usage_count}次)")
        reasons.append(f"多样化得分{usage_score:.2f}")
        reasons.append(f"能力匹配度{capability_score:.2f}")

        # 添加对比信息
        most_used_model = max(all_scores.items(), key=lambda x: x[1]["usage_count"])
        if most_used_model[0] != selected_model:
            reasons.append(
                f"避免过度使用{most_used_model[0]}({most_used_model[1]['usage_count']}次)"
            )

        return f"{base_reason}，原因：{','.join(reasons)}"

    def _update_model_usage(self, model_name: str) -> None:
        """更新模型使用统计"""
        self.model_usage_tracker[model_name] = (
            self.model_usage_tracker.get(model_name, 0) + 1
        )

        # 定期重置统计，避免累积效应
        total_usage = sum(self.model_usage_tracker.values())
        if total_usage > 50:  # 每50次使用后重置
            # 保持相对比例，但减少绝对数量
            for model in self.model_usage_tracker:
                self.model_usage_tracker[model] = max(
                    1, self.model_usage_tracker[model] // 2
                )
            logger.debug("重置模型使用统计以保持多样化效果")

    def _route_with_traditional_logic(
        self,
        task_description: str,
        agent_role: str,
        task_spec: TaskSpec,
        available_models: dict[str, ModelSpec],
        context: dict[str, Any],
    ) -> RoutingDecision:
        """使用传统逻辑进行路由（向后兼容）"""
        try:
            # 1. 分析任务特性
            task_analysis = self._analyze_task_characteristics(
                task_description, task_spec, context
            )

            # 2. 计算模型适配度分数
            model_scores = {}
            for model_name, model_spec in available_models.items():
                if model_name in self.model_capabilities:
                    score = self._calculate_model_score(
                        model_name, model_spec, task_analysis, task_spec
                    )
                    model_scores[model_name] = score

            # 3. 选择最优模型
            if not model_scores:
                # 回退到默认选择
                default_model = self._get_default_model(available_models, task_spec)
                return RoutingDecision(
                    selected_model=default_model.name,
                    provider=default_model.provider.value,
                    confidence_score=0.5,
                    reasoning="使用默认模型选择",
                    estimated_cost=0.01,
                    estimated_time=5000,
                    routing_strategy="traditional_fallback",
                )

            # 按分数排序
            sorted_models = sorted(
                model_scores.items(), key=lambda x: x[1], reverse=True
            )
            best_model_name, best_score = sorted_models[0]
            best_model_spec = available_models[best_model_name]

            # 4. 生成决策推理
            reasoning = self._generate_routing_reasoning(
                best_model_name, task_analysis, best_score, sorted_models[:3]
            )

            # 5. 估算成本和时间
            estimated_cost = self._estimate_task_cost(best_model_spec, task_spec)
            estimated_time = self._estimate_execution_time(best_model_name, task_spec)

            # 6. 获取备选模型
            alternative_models = [model[0] for model in sorted_models[1:4]]

            decision = RoutingDecision(
                selected_model=best_model_name,
                provider=best_model_spec.provider.value,
                confidence_score=min(best_score, 0.95),
                reasoning=f"传统路由: {reasoning}",
                estimated_cost=estimated_cost,
                estimated_time=estimated_time,
                alternative_models=alternative_models,
                routing_strategy="traditional",
            )

            # 7. 记录路由决策和更新使用统计
            self._log_routing_decision(decision, agent_role, task_spec, context)
            if self.force_diversity:
                self._update_model_usage(best_model_name)

            logger.info(
                f"传统路由决策完成: {best_model_name} (置信度: {best_score:.3f})"
            )

            return decision

        except Exception as e:
            logger.error(f"传统路由失败: {e}", exc_info=True)
            # 回退到默认选择
            default_model = self._get_default_model(available_models, task_spec)
            return RoutingDecision(
                selected_model=default_model.name,
                provider=default_model.provider.value,
                confidence_score=0.3,
                reasoning=f"传统路由失败，使用默认模型: {str(e)}",
                estimated_cost=0.01,
                estimated_time=5000,
                routing_strategy="fallback",
            )

    def _analyze_task_characteristics(
        self, task_description: str, task_spec: TaskSpec, context: dict[str, Any]
    ) -> dict[str, float]:
        """分析任务特性（适配三池架构）"""
        characteristics = {
            "reasoning_required": 0.5,
            "speed_priority": 0.5,
            "chinese_content": 0.5,
            "cost_sensitivity": 0.5,
            "complexity_level": 0.5,
            "multimodal_required": 0.0,
            "long_context_required": 0.0,
            "code_generation_required": 0.0,
        }

        # 基于任务类型的基础特性
        task_type_characteristics = {
            "financial_report": {
                "reasoning_required": 0.9,
                "multimodal_required": 0.8,
                "complexity_level": 0.8,
            },
            "technical_analysis": {
                "reasoning_required": 0.8,
                "long_context_required": 0.7,
                "chinese_content": 0.8,
            },
            "news_analysis": {
                "speed_priority": 0.8,
                "long_context_required": 0.6,
                "chinese_content": 0.9,
            },
            "sentiment_analysis": {"chinese_content": 0.9, "speed_priority": 0.7},
            "risk_assessment": {"reasoning_required": 0.9, "complexity_level": 0.8},
            "decision_making": {
                "reasoning_required": 0.95,
                "multimodal_required": 0.7,
                "complexity_level": 0.9,
            },
            "code_generation": {
                "code_generation_required": 0.95,
                "reasoning_required": 0.7,
            },
            "tool_development": {
                "code_generation_required": 0.9,
                "reasoning_required": 0.8,
            },
            "policy_analysis": {
                "reasoning_required": 0.8,
                "chinese_content": 0.95,
                "multimodal_required": 0.6,
            },
        }

        if task_spec.task_type in task_type_characteristics:
            task_chars = task_type_characteristics[task_spec.task_type]
            for key, value in task_chars.items():
                characteristics[key] = max(characteristics[key], value)

        # 基于任务复杂度调整
        if task_spec.complexity == TaskComplexity.HIGH:
            characteristics["reasoning_required"] *= 1.2
            characteristics["cost_sensitivity"] *= 0.8
            characteristics["complexity_level"] = 0.9
        elif task_spec.complexity == TaskComplexity.LOW:
            characteristics["speed_priority"] *= 1.2
            characteristics["cost_sensitivity"] *= 1.2
            characteristics["complexity_level"] = 0.3

        # 基于任务描述的文本分析
        description_lower = task_description.lower()

        # 检测中文内容
        chinese_chars = sum(
            1 for char in task_description if "\u4e00" <= char <= "\u9fff"
        )
        if chinese_chars > len(task_description) * 0.3:
            characteristics["chinese_content"] = min(
                characteristics["chinese_content"] * 1.3, 1.0
            )

        # 检测推理需求关键词
        reasoning_keywords = [
            "分析",
            "推理",
            "判断",
            "评估",
            "决策",
            "analysis",
            "reasoning",
            "evaluate",
        ]
        if any(keyword in description_lower for keyword in reasoning_keywords):
            characteristics["reasoning_required"] = min(
                characteristics["reasoning_required"] * 1.2, 1.0
            )

        # 检测速度需求关键词
        speed_keywords = ["快速", "急", "立即", "quick", "fast", "urgent"]
        if any(keyword in description_lower for keyword in speed_keywords):
            characteristics["speed_priority"] = min(
                characteristics["speed_priority"] * 1.3, 1.0
            )

        # 检测代码生成需求
        code_keywords = ["代码", "编程", "脚本", "code", "script", "python", "function"]
        if any(keyword in description_lower for keyword in code_keywords):
            characteristics["code_generation_required"] = min(
                characteristics["code_generation_required"] * 1.5, 1.0
            )

        # 检测多模态需求
        multimodal_keywords = ["图片", "图表", "表格", "pdf", "image", "chart", "table"]
        if any(keyword in description_lower for keyword in multimodal_keywords):
            characteristics["multimodal_required"] = min(
                characteristics["multimodal_required"] * 1.5, 1.0
            )

        # 检测长上下文需求
        if task_spec.estimated_tokens > 20000:
            characteristics["long_context_required"] = 0.8
        elif task_spec.estimated_tokens > 10000:
            characteristics["long_context_required"] = 0.6

        # 基于上下文调整
        if context.get("time_limit"):
            characteristics["speed_priority"] = min(
                characteristics["speed_priority"] * 1.2, 1.0
            )

        if context.get("budget_limit"):
            characteristics["cost_sensitivity"] = min(
                characteristics["cost_sensitivity"] * 1.3, 1.0
            )

        if context.get("code_generation_required"):
            characteristics["code_generation_required"] = 0.9

        if context.get("multimodal_required"):
            characteristics["multimodal_required"] = 0.8

        return characteristics

    def _calculate_model_score(
        self,
        model_name: str,
        model_spec: ModelSpec,
        task_characteristics: dict[str, float],
        task_spec: TaskSpec,
    ) -> float:
        """计算模型适配度分数"""
        if model_name not in self.model_capabilities:
            return 0.0

        capabilities = self.model_capabilities[model_name]

        # 计算各维度得分
        reasoning_score = (
            capabilities.get("reasoning", 0)
            * task_characteristics["reasoning_required"]
        )
        speed_score = (
            capabilities.get("speed", 0.5) * task_characteristics["speed_priority"]
        )
        chinese_score = (
            capabilities.get("chinese", 0.5) * task_characteristics["chinese_content"]
        )
        cost_score = (
            capabilities.get("cost", 0.5) * task_characteristics["cost_sensitivity"]
        )
        reliability_score = capabilities.get("reliability", 0.8) * 0.8  # 稳定性基础权重

        # 专业能力加分
        code_score = capabilities.get("code_generation", 0) * task_characteristics.get(
            "code_generation_required", 0
        )
        multimodal_score = capabilities.get("multimodal", 0) * task_characteristics.get(
            "multimodal_required", 0
        )
        financial_score = capabilities.get("financial_analysis", 0) * (
            1.0
            if task_spec.task_type in ["financial_report", "fundamental_analysis"]
            else 0
        )

        # 加权平均（适配新的权重配置）
        total_score = (
            (reasoning_score + code_score + multimodal_score + financial_score)
            * self.routing_weights.get("quality", 0.6)
            + (speed_score + reliability_score)
            * self.routing_weights.get("performance", 0.3)
            + chinese_score
            * self.routing_weights.get("performance", 0.3)
            * 0.5  # 中文能力作为性能的一部分
            + cost_score * self.routing_weights.get("cost", 0.1)
        )

        # 根据历史性能调整
        historical_performance = self._get_historical_performance(
            model_name, task_spec.task_type
        )
        if historical_performance:
            performance_factor = (
                historical_performance["success_rate"] * 0.6
                + min(historical_performance["avg_response_time"] / 10000, 1.0) * 0.4
            )
            total_score *= performance_factor

        # 确保分数在合理范围内
        return max(0.0, min(total_score, 1.0))

    def _get_historical_performance(
        self, model_name: str, task_type: str
    ) -> dict[str, float] | None:
        """获取模型历史性能数据"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT avg_response_time, success_rate, last_updated
                    FROM model_performance
                    WHERE model_name = ? AND task_type = ?
                    ORDER BY last_updated DESC
                    LIMIT 1
                """,
                    (model_name, task_type),
                )

                result = cursor.fetchone()
                if result:
                    return {
                        "avg_response_time": result[0],
                        "success_rate": result[1],
                        "last_updated": result[2],
                    }
        except Exception as e:
            logger.warning(f"获取历史性能数据失败: {e}")

        return None

    def _generate_routing_reasoning(
        self,
        selected_model: str,
        task_characteristics: dict[str, float],
        score: float,
        top_models: list[tuple[str, float]],
    ) -> str:
        """生成路由决策推理说明"""
        reasoning_parts = []

        # 选择原因
        model_caps = self.model_capabilities.get(selected_model, {})

        if (
            task_characteristics["reasoning_required"] > 0.7
            and model_caps.get("reasoning", 0) > 0.8
        ):
            reasoning_parts.append(f"{selected_model}具有强大的推理能力")

        if (
            task_characteristics["speed_priority"] > 0.7
            and model_caps.get("speed", 0) > 0.8
        ):
            reasoning_parts.append("优先考虑响应速度")

        if (
            task_characteristics["chinese_content"] > 0.7
            and model_caps.get("chinese", 0) > 0.8
        ):
            reasoning_parts.append("针对中文内容优化")

        if (
            task_characteristics["cost_sensitivity"] > 0.7
            and model_caps.get("cost", 0) > 0.8
        ):
            reasoning_parts.append("具备良好的成本效益")

        # 构建推理说明
        base_reasoning = f"选择{selected_model}（置信度: {score:.2f}）"

        if reasoning_parts:
            reasons = "，".join(reasoning_parts)
            base_reasoning += f"，主要原因: {reasons}"

        # 添加备选方案
        if len(top_models) > 1:
            alternatives = [f"{model}({score:.2f})" for model, score in top_models[1:]]
            base_reasoning += f"。备选方案: {', '.join(alternatives)}"

        return base_reasoning

    def _estimate_task_cost(self, model_spec: ModelSpec, task_spec: TaskSpec) -> float:
        """估算任务成本"""
        estimated_tokens = max(task_spec.estimated_tokens, 1000)  # 最少1000 tokens
        return (estimated_tokens / 1000) * model_spec.cost_per_1k_tokens

    def _estimate_execution_time(self, model_name: str, task_spec: TaskSpec) -> int:
        """估算执行时间（毫秒）"""
        base_time = 3000  # 基础3秒

        # 根据模型速度特性调整
        if model_name in self.model_capabilities:
            speed_factor = self.model_capabilities[model_name].get("speed", 0.5)
            base_time = int(base_time * (1.5 - speed_factor))

        # 根据任务复杂度调整
        if task_spec.complexity == TaskComplexity.HIGH:
            base_time *= 2
        elif task_spec.complexity == TaskComplexity.LOW:
            base_time = int(base_time * 0.6)

        # 根据估算token数调整
        if task_spec.estimated_tokens > 4000:
            token_factor = min(task_spec.estimated_tokens / 4000, 3.0)
            base_time = int(base_time * token_factor)

        return max(base_time, 1000)  # 最少1秒

    def _initialize_database_tables(self) -> None:
        """初始化必要的数据库表"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                # 创建模型性能表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS model_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model_name TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        avg_response_time REAL NOT NULL,
                        success_rate REAL NOT NULL,
                        cost_efficiency REAL DEFAULT 1.0,
                        quality_score REAL DEFAULT 1.0,
                        last_updated TEXT NOT NULL,
                        created_at TEXT DEFAULT (datetime('now')),
                        UNIQUE(model_name, provider, task_type)
                    )
                """
                )

                # 创建路由决策表
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS routing_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        agent_role TEXT NOT NULL,
                        task_type TEXT NOT NULL,
                        selected_model TEXT NOT NULL,
                        selected_provider TEXT NOT NULL,
                        routing_reason TEXT,
                        confidence_score REAL,
                        execution_time INTEGER,
                        cost_estimate REAL,
                        created_at TEXT DEFAULT (datetime('now'))
                    )
                """
                )

                conn.commit()
                logger.debug("数据库表结构初始化完成")

        except Exception as e:
            logger.warning(f"数据库表初始化失败（将使用内存模式）: {e}")

    def _validate_engine_usability(self) -> dict[str, Any]:
        """验证路由引擎的可用性"""
        issues = []

        # 检查模型能力配置
        if not self.model_capabilities:
            issues.append("缺少模型能力配置")

        # 检查任务-池亲和度配置
        if not self.task_pool_affinity:
            issues.append("缺少任务-池亲和度配置")

        # 检查数据库连接
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.execute("SELECT 1").fetchone()
        except Exception as e:
            issues.append(f"数据库连接问题: {str(e)[:50]}")

        # 检查权重配置
        total_weight = sum(self.routing_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            issues.append(f"路由权重配置异常 (总和: {total_weight:.3f})")

        if issues:
            return {
                "usable": False,
                "message": f"发现{len(issues)}个问题: {'; '.join(issues[:2])}",
                "issues": issues,
            }
        else:
            model_count = len(self.model_capabilities)
            task_count = len(self.task_pool_affinity)
            return {
                "usable": True,
                "message": f"支持{model_count}个模型，{task_count}种任务类型",
                "issues": [],
            }

    def _get_default_model(
        self, available_models: dict[str, ModelSpec], task_spec: TaskSpec
    ) -> ModelSpec:
        """获取默认模型"""
        # 优先选择成本效益较好的模型 - 只保留可用的模型
        cost_efficient_models = [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "deepseek-ai/DeepSeek-V3",
            "deepseek-chat",
            "moonshotai/Kimi-K2-Instruct",
        ]

        for model_name in cost_efficient_models:
            if model_name in available_models:
                return available_models[model_name]

        # 如果没有找到，返回第一个可用模型
        if available_models:
            return next(iter(available_models.values()))

        # 这种情况不应该发生，但作为保险
        return ModelSpec(
            name="fallback",
            provider=ModelProvider.SILICONFLOW,
            model_type="general",
            cost_per_1k_tokens=0.001,
            max_tokens=2048,
            context_window=4096,
        )

    def _log_routing_decision(
        self,
        decision: RoutingDecision,
        agent_role: str,
        task_spec: TaskSpec,
        context: dict[str, Any],
    ) -> None:
        """记录路由决策到数据库"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO routing_decisions 
                    (session_id, agent_role, task_type, selected_model, selected_provider,
                     routing_reason, confidence_score, execution_time, cost_estimate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        context.get("session_id", "unknown"),
                        agent_role,
                        task_spec.task_type,
                        decision.selected_model,
                        decision.provider,
                        decision.reasoning,
                        decision.confidence_score,
                        decision.estimated_time,
                        decision.estimated_cost,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"路由决策记录失败: {e}")

    def reset_diversity_tracker(self) -> None:
        """重置多样化跟踪器"""
        self.model_usage_tracker.clear()
        logger.info("多样化跟踪器已重置")

    def _get_default_db_path(self) -> str:
        """获取默认数据库路径"""
        # 尝试使用项目数据库路径
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "trading_agents.db"

        if db_path.parent.exists():
            return str(db_path)
        else:
            # 回退到临时数据库
            return ":memory:"

    def update_model_performance(
        self,
        model_name: str,
        provider: str,
        task_type: str,
        execution_time: int,
        success: bool,
        cost: float = None,
    ) -> None:
        """更新模型性能数据"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                # 获取现有数据
                cursor.execute(
                    """
                    SELECT avg_response_time, success_rate, last_updated
                    FROM model_performance
                    WHERE model_name = ? AND provider = ? AND task_type = ?
                """,
                    (model_name, provider, task_type),
                )

                existing = cursor.fetchone()

                if existing:
                    # 更新现有记录
                    old_time, old_success_rate, _ = existing
                    # 简单的移动平均
                    new_avg_time = (old_time + execution_time) / 2
                    new_success_rate = (
                        old_success_rate + (1.0 if success else 0.0)
                    ) / 2

                    cursor.execute(
                        """
                        UPDATE model_performance 
                        SET avg_response_time = ?, success_rate = ?, last_updated = ?
                        WHERE model_name = ? AND provider = ? AND task_type = ?
                    """,
                        (
                            new_avg_time,
                            new_success_rate,
                            datetime.now().isoformat(),
                            model_name,
                            provider,
                            task_type,
                        ),
                    )
                else:
                    # 插入新记录
                    cursor.execute(
                        """
                        INSERT INTO model_performance 
                        (model_name, provider, task_type, avg_response_time, success_rate, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            model_name,
                            provider,
                            task_type,
                            execution_time,
                            1.0 if success else 0.0,
                            datetime.now().isoformat(),
                        ),
                    )

                conn.commit()

        except Exception as e:
            logger.warning(f"性能数据更新失败: {e}")

    def get_routing_statistics(self, time_window_hours: int = 24) -> dict[str, Any]:
        """获取路由统计信息"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()

                since_time = datetime.now() - timedelta(hours=time_window_hours)

                # 模型使用统计
                cursor.execute(
                    """
                    SELECT selected_model, COUNT(*) as usage_count,
                           AVG(confidence_score) as avg_confidence,
                           AVG(cost_estimate) as avg_cost
                    FROM routing_decisions 
                    WHERE created_at > ?
                    GROUP BY selected_model
                    ORDER BY usage_count DESC
                """,
                    (since_time.isoformat(),),
                )

                model_stats = cursor.fetchall()

                return {
                    "time_window_hours": time_window_hours,
                    "total_decisions": sum(stat[1] for stat in model_stats),
                    "model_usage": [
                        {
                            "model": stat[0],
                            "usage_count": stat[1],
                            "avg_confidence": round(stat[2], 3),
                            "avg_cost": round(stat[3], 6),
                        }
                        for stat in model_stats
                    ],
                }
        except Exception as e:
            logger.error(f"获取路由统计失败: {e}")
            return {"error": str(e)}

    def get_diversity_statistics(self) -> dict[str, Any]:
        """获取多样化统计信息"""
        if not self.model_usage_tracker:
            return {
                "diversity_enabled": self.force_diversity,
                "total_usage": 0,
                "model_usage": {},
                "diversity_score": 1.0,
            }

        total_usage = sum(self.model_usage_tracker.values())
        model_usage = dict(
            sorted(self.model_usage_tracker.items(), key=lambda x: x[1], reverse=True)
        )

        # 计算多样化得分（基尼系数的简化版本）
        diversity_score = 1.0
        if total_usage > 0:
            usage_rates = [
                count / total_usage for count in self.model_usage_tracker.values()
            ]
            # 计算分布的均匀程度
            n = len(usage_rates)
            if n > 1:
                max_rate = max(usage_rates)
                diversity_score = 1.0 - (max_rate - 1 / n) / (1.0 - 1 / n)

        return {
            "diversity_enabled": self.force_diversity,
            "diversity_threshold": self.diversity_threshold,
            "total_usage": total_usage,
            "model_usage": model_usage,
            "diversity_score": round(diversity_score, 3),
            "needs_diversification": (
                self._should_diversify_routing("", {})
                if self.model_usage_tracker
                else False
            ),
        }
