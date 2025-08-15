"""
Multi-Model Manager
多模型管理器，负责模型选择、任务分发和结果协调
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import sqlite3
from pathlib import Path

from .base_multi_model_adapter import (
    BaseMultiModelAdapter, ModelSpec, TaskSpec, TaskResult, 
    ModelSelection, TaskComplexity, ModelProvider
)
from .smart_routing_engine import SmartRoutingEngine, RoutingDecision
from ..api.siliconflow_client import SiliconFlowClient
from ..api.google_ai_client import GoogleAIClient
from ..api.deepseek_client import DeepSeekClient
from ..api.gemini_openai_compat_client import GeminiOpenAICompatClient

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
from tradingagents.config.config_manager import token_tracker
from datetime import datetime
logger = get_logger('multi_model_manager')


@dataclass
class CollaborationResult:
    """协作执行结果"""
    final_result: str
    participating_models: List[str]
    individual_results: List[TaskResult]
    collaboration_metadata: Dict[str, Any]
    total_cost: float
    total_time: int
    success: bool = True
    error_message: str = None


@dataclass
class SessionMetrics:
    """会话性能指标"""
    session_id: str
    total_tasks: int
    successful_tasks: int
    total_cost: float
    total_time: int
    models_used: Dict[str, int]
    avg_confidence: float
    start_time: datetime
    end_time: datetime = None


class MultiModelManager:
    """多模型管理器，负责模型选择和任务分发"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化多模型管理器
        
        Args:
            config: 配置字典，包含各个API的配置信息
        """
        self.config = config
        self.clients: Dict[str, BaseMultiModelAdapter] = {}
        self.routing_engine = None
        self.database_path = self._get_database_path()
        
        # 会话管理
        self.active_sessions: Dict[str, SessionMetrics] = {}
        
        # 性能限制配置
        self.max_cost_per_session = config.get('max_cost_per_session', 1.0)
        self.max_concurrent_tasks = config.get('max_concurrent_tasks', 5)
        self.enable_caching = config.get('enable_caching', True)
        
        # 策略与绑定（来自 multi_model_config.yaml 或上层传入）
        self.agent_bindings: Dict[str, Any] = config.get('agent_bindings', {})
        self.task_bindings: Dict[str, Any] = config.get('task_bindings', {})
        self.intra_pool_weights: Dict[str, Any] = config.get('intra_pool_weights', {})
        self.model_catalog: Dict[str, Any] = config.get('model_catalog', {})
        self.runtime_overrides: Dict[str, Any] = config.get('runtime_overrides', {})

        # 初始化各个客户端
        self._initialize_clients()
        self._initialize_routing_engine()
        
        logger.info("多模型管理器初始化完成")
    
    def _initialize_clients(self) -> None:
        """初始化各个API客户端"""
        successful_clients = []
        failed_clients = []

        # 初始化 Gemini-API 兼容（OpenAI 协议反代）
        if 'gemini_api' in self.config:
            gcfg = self.config['gemini_api']
            if gcfg.get('enabled', True):
                try:
                    self.clients['gemini_api'] = GeminiOpenAICompatClient(gcfg)
                    successful_clients.append('gemini_api')
                    logger.info("Gemini-API(兼容) 客户端初始化成功")
                except Exception as e:
                    failed_clients.append(('gemini_api', str(e)))
                    logger.warning(f"Gemini-API(兼容) 客户端初始化失败: {e}")

        # 初始化SiliconFlow客户端
        if 'siliconflow' in self.config:
            siliconflow_config = self.config['siliconflow']
            if siliconflow_config.get('enabled', True):
                try:
                    self.clients['siliconflow'] = SiliconFlowClient(siliconflow_config)
                    successful_clients.append('siliconflow')
                    logger.info("SiliconFlow客户端初始化成功")
                except Exception as e:
                    failed_clients.append(('siliconflow', str(e)))
                    logger.warning(f"SiliconFlow客户端初始化失败: {e}")
        
        # 初始化Google AI客户端
        if 'google_ai' in self.config:
            google_config = self.config['google_ai']
            if google_config.get('enabled', True):
                try:
                    self.clients['google_ai'] = GoogleAIClient(google_config)
                    successful_clients.append('google_ai')
                    logger.info("Google AI客户端初始化成功")
                except ImportError as e:
                    failed_clients.append(('google_ai', str(e)))
                    logger.warning(f"Google AI客户端初始化失败（依赖缺失）: {e}")
                except Exception as e:
                    failed_clients.append(('google_ai', str(e)))
                    logger.warning(f"Google AI客户端初始化失败: {e}")
        
        # 初始化DeepSeek客户端
        if 'deepseek' in self.config:
            deepseek_config = self.config['deepseek']
            if deepseek_config.get('enabled', True):
                try:
                    self.clients['deepseek'] = DeepSeekClient(deepseek_config)
                    successful_clients.append('deepseek')
                    logger.info("DeepSeek客户端初始化成功")
                except Exception as e:
                    failed_clients.append(('deepseek', str(e)))
                    logger.warning(f"DeepSeek客户端初始化失败: {e}")
        
        # 检查是否有可用的客户端
        if not self.clients:
            error_details = "; ".join([f"{name}: {error}" for name, error in failed_clients])
            raise ValueError(f"没有可用的API客户端。失败详情: {error_details}")
        
        # 记录初始化结果
        if successful_clients:
            logger.info(f"客户端初始化完成，成功: {successful_clients}")
        if failed_clients:
            failed_names = [name for name, _ in failed_clients]
            logger.warning(f"部分客户端初始化失败: {failed_names}，系统将使用可用客户端继续运行")
            
        # 执行健康检查
        self._health_check_all()
    
    def _initialize_routing_engine(self) -> None:
        """初始化智能路由引擎"""
        try:
            routing_config = self.config.get('routing', {})
            self.routing_engine = SmartRoutingEngine(
                database_path=self.database_path,
                config=routing_config
            )
            logger.info("智能路由引擎初始化成功")
        except ImportError as e:
            if "toml" in str(e):
                logger.error("路由引擎初始化失败: 缺少toml依赖包")
                logger.info("解决方案: pip install toml")
            else:
                logger.error(f"路由引擎初始化失败: 缺少依赖包 {e}")
            logger.warning("路由引擎初始化失败，将使用简单模型选择策略")
            self.routing_engine = None
        except Exception as e:
            # 使用用户友好的错误处理
            from .user_friendly_error_handler import handle_user_friendly_error
            user_error = handle_user_friendly_error(e, {'action': 'routing_engine_initialization'})
            logger.error(f"路由引擎初始化失败: {e}", exc_info=True)
            # 提供降级功能：无路由引擎时使用简单的模型选择
            logger.warning("路由引擎初始化失败，将使用简单模型选择策略")
            self.routing_engine = None  # 允许None值，后续代码会处理
    
    def _health_check_all(self) -> None:
        """对所有客户端执行健康检查"""
        failed_clients = []
        for name, client in self.clients.items():
            try:
                if not client.health_check():
                    failed_clients.append(name)
                    logger.warning(f"{name} 客户端健康检查失败")
            except Exception as e:
                failed_clients.append(name)
                logger.error(f"{name} 客户端健康检查异常: {e}")
        
        # 移除失败的客户端
        for name in failed_clients:
            self.clients.pop(name, None)
        
        if not self.clients:
            raise RuntimeError("所有API客户端都不可用")
        
        logger.info(f"健康检查完成，可用客户端: {list(self.clients.keys())}")
    
    def select_optimal_model(self,
                           agent_role: str,
                           task_type: str,
                           task_description: str = "",
                           complexity_level: str = "medium",
                           context: Dict[str, Any] = None) -> ModelSelection:
        """
        智能选择最优模型
        
        Args:
            agent_role: 智能体角色
            task_type: 任务类型
            task_description: 任务描述
            complexity_level: 复杂度级别 (low, medium, high)
            context: 上下文信息
            
        Returns:
            ModelSelection: 模型选择结果
        """
        try:
            # 构建任务规格
            task_spec = TaskSpec(
                task_type=task_type,
                complexity=TaskComplexity(complexity_level),
                estimated_tokens=self._estimate_tokens(task_description),
                requires_reasoning=self._requires_reasoning(task_type, task_description),
                requires_chinese=self._requires_chinese(task_description),
                requires_speed=self._requires_speed(context or {}),
                context_data=context or {}
            )
            
            # 获取所有可用模型
            available_models = self._get_all_available_models()

            # 先应用“锁定模型 / 允许集”约束（配置+上下文）
            context = context or {}
            locked_model = self._get_locked_model(agent_role, context)
            candidate_models = self._filter_candidates_by_policy(
                agent_role=agent_role,
                task_type=task_type,
                available_models=available_models,
                context=context,
            )
            if not candidate_models:
                # 若策略过滤后为空，退回到全量可用，以免完全不可用
                candidate_models = available_models
                logger.warning(f"策略过滤后候选为空，回退到全量可用模型: agent={agent_role}, task={task_type}")
            
            # 如果存在锁定模型并且可用，直接返回
            if locked_model and locked_model in candidate_models:
                logger.info(f"使用锁定模型: {locked_model} (agent={agent_role}, task={task_type})")
                selected_model_spec = candidate_models[locked_model]
                return ModelSelection(
                    model_spec=selected_model_spec,
                    confidence_score=0.95,
                    reasoning=f"锁定模型策略: {locked_model}",
                    estimated_cost=0.01,
                    estimated_time=3000,
                )
            
            if not candidate_models:
                raise ValueError("没有可用的模型")
            
            # 使用智能路由选择模型（如果可用）
            if self.routing_engine:
                routing_decision = self.routing_engine.route_task(
                    task_description=task_description,
                    agent_role=agent_role,
                    task_spec=task_spec,
                    available_models=candidate_models,
                    context=context or {}
                )
                
                # 转换为ModelSelection
                selected_model_spec = candidate_models[routing_decision.selected_model]
                
                model_selection = ModelSelection(
                    model_spec=selected_model_spec,
                    confidence_score=routing_decision.confidence_score,
                    reasoning=routing_decision.reasoning,
                    estimated_cost=routing_decision.estimated_cost,
                    estimated_time=routing_decision.estimated_time
                )
            else:
                # 路由引擎不可用，使用简单的默认模型选择
                logger.warning("智能路由引擎不可用，使用默认模型选择")
                default_model = self._get_default_model(candidate_models, task_spec)
                
                model_selection = ModelSelection(
                    model_spec=default_model,
                    confidence_score=0.7,
                    reasoning=f"路由引擎不可用，使用默认模型: {default_model.name}",
                    estimated_cost=0.01,
                    estimated_time=3000
                )
            
            logger.info(f"模型选择完成: {model_selection.model_spec.name} (置信度: {model_selection.confidence_score:.3f})")
            
            return model_selection
            
        except Exception as e:
            # 使用用户友好的错误处理和自动回退
            from .user_friendly_error_handler import handle_user_friendly_error
            user_error = handle_user_friendly_error(e, {
                'action': 'model_selection',
                'agent_role': agent_role,
                'task_type': task_type
            })
            logger.error(f"模型选择失败: {e}", exc_info=True)
            
            # 自动回退到默认模型选择
            try:
                available_models = self._get_all_available_models()
                candidates = self._filter_candidates_by_policy(agent_role, task_type, available_models, context or {}) or available_models
                if candidates:
                    default_model = self._get_default_model(candidates, task_spec)
                    logger.warning(f"使用默认模型回退: {default_model.name}")
                    return ModelSelection(
                        model_spec=default_model,
                        confidence_score=0.6,
                        reasoning=f"智能路由失败，使用默认模型: {default_model.name}",
                        estimated_cost=0.01,
                        estimated_time=3000
                    )
            except Exception as fallback_error:
                logger.error(f"模型回退也失败: {fallback_error}")
            
            # 如果连回退都失败，抛出用户友好的错误
            enhanced_error = RuntimeError(f"AI模型选择失败: {user_error['message']}")
            enhanced_error.user_friendly_info = user_error
            raise enhanced_error

    def _get_locked_model(self, agent_role: str, context: Dict[str, Any]) -> Optional[str]:
        """获取锁定模型，优先级：context > runtime_overrides > agent_bindings.locked_model"""
        # 来自每次请求上下文
        overrides = context.get('model_overrides') or {}
        if isinstance(overrides, dict) and agent_role in overrides and overrides[agent_role]:
            return overrides[agent_role]
        # 运行时全局配置
        rt = self.runtime_overrides or {}
        if rt.get('enable_model_lock'):
            locked = rt.get('model_overrides') or {}
            if isinstance(locked, dict) and locked.get(agent_role):
                return locked[agent_role]
        # 绑定配置
        binding = self.agent_bindings.get(agent_role) or {}
        return binding.get('locked_model')

    def _filter_candidates_by_policy(
        self,
        agent_role: str,
        task_type: str,
        available_models: Dict[str, ModelSpec],
        context: Dict[str, Any],
    ) -> Dict[str, ModelSpec]:
        """根据 agent/task 绑定、白/黑名单、运行时允许集合过滤候选模型。"""
        allowed_from_agent = set(self.agent_bindings.get(agent_role, {}).get('allow_models', []))
        denied_from_agent = set(self.agent_bindings.get(agent_role, {}).get('deny_models', []))

        task_cfg = self.task_bindings.get(task_type, {}) if isinstance(self.task_bindings, dict) else {}
        allowed_from_task = set(task_cfg.get('allow_models', []))
        denied_from_task = set(task_cfg.get('deny_models', []))

        # 运行时每次请求的允许列表
        rt_allowed_by_role = None
        if isinstance(context.get('allowed_models_by_role'), dict):
            rt_allowed_by_role = set(context['allowed_models_by_role'].get(agent_role, []) or [])

        # 全局运行时允许列表（启用时）
        rt_cfg = self.runtime_overrides or {}
        global_allowed = None
        if rt_cfg.get('enable_allowed_models_by_role') and isinstance(rt_cfg.get('allowed_models_by_role'), dict):
            global_allowed = set(rt_cfg['allowed_models_by_role'].get(agent_role, []) or [])

        # 组合允许集：若任一层提供了allow，则取交集；否则默认全量
        candidate_names = set(available_models.keys())
        layers = [s for s in [allowed_from_agent, allowed_from_task, rt_allowed_by_role, global_allowed] if s]
        if layers:
            # 从可用全集开始，与每层allow求交集
            for layer in layers:
                candidate_names &= layer
        # 去除黑名单
        candidate_names -= denied_from_agent
        candidate_names -= denied_from_task

        return {name: spec for name, spec in available_models.items() if name in candidate_names}
    
    def execute_task(self,
                    agent_role: str,
                    task_prompt: str,
                    task_type: str = "general",
                    complexity_level: str = "medium",
                    context: Dict[str, Any] = None,
                    model_override: str = None) -> TaskResult:
        """
        执行单个任务
        
        Args:
            agent_role: 智能体角色
            task_prompt: 任务提示词
            task_type: 任务类型
            complexity_level: 复杂度级别
            context: 上下文信息
            model_override: 强制指定模型
            
        Returns:
            TaskResult: 任务执行结果
        """
        context = context or {}
        session_id = context.get('session_id', f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        try:
            # 检查会话成本限制
            if not self._check_session_cost_limit(session_id):
                raise ValueError(f"会话 {session_id} 已达到成本限制")
            
            # 选择模型
            if model_override:
                # 使用指定模型（支持别名映射）
                available_models = self._get_all_available_models()
                chosen_name = model_override
                if chosen_name not in available_models:
                    # 兼容 gemini-api/<name> → <name>
                    if isinstance(chosen_name, str) and chosen_name.startswith('gemini-api/'):
                        alt = chosen_name.split('/', 1)[1]
                        if alt in available_models:
                            chosen_name = alt
                    # 兼容常见别名
                    alias_map = {
                        'deepseek-v3': 'deepseek-ai/DeepSeek-V3',
                        'glm-4.5': 'zai-org/GLM-4.5',
                        'qwen3-235b': 'Qwen/Qwen3-235B-A22B-Instruct-2507',
                    }
                    mapped = alias_map.get(chosen_name.lower())
                    if mapped and mapped in available_models:
                        chosen_name = mapped
                if chosen_name not in available_models:
                    raise ValueError(f"指定的模型不可用: {model_override}")

                model_selection = ModelSelection(
                    model_spec=available_models[chosen_name],
                    confidence_score=1.0,
                    reasoning=f"用户指定模型: {chosen_name}",
                    estimated_cost=0.01,
                    estimated_time=3000
                )
            else:
                # 智能选择模型
                model_selection = self.select_optimal_model(
                    agent_role=agent_role,
                    task_type=task_type,
                    task_description=task_prompt,
                    complexity_level=complexity_level,
                    context=context
                )
            
            # 构建任务规格
            task_spec = TaskSpec(
                task_type=task_type,
                complexity=TaskComplexity(complexity_level),
                estimated_tokens=self._estimate_tokens(task_prompt),
                requires_reasoning=self._requires_reasoning(task_type, task_prompt),
                requires_chinese=self._requires_chinese(task_prompt),
                requires_speed=self._requires_speed(context),
                context_data=context
            )
            
            # 获取对应的客户端
            client = self._get_client_for_model(model_selection.model_spec.name)
            if not client:
                raise ValueError(f"找不到模型 {model_selection.model_spec.name} 对应的客户端")
            
            # 执行任务（带熔断和重试逻辑）
            result = self._execute_task_with_fallback(
                model_selection, task_prompt, task_spec, context, agent_role, task_type
            )
            
            # 更新会话指标
            self._update_session_metrics(session_id, result, model_selection)

            # 记录Token使用与成本（持久化到 usage.json 或 MongoDB）
            try:
                self._record_token_usage(result, model_selection, context, session_id, task_type)
            except Exception as track_err:
                logger.debug(f"记录Token使用失败: {track_err}")
            
            logger.info(f"任务执行完成: {result.model_used.name if result.model_used else 'unknown'}, 成功: {result.success}")
            
            return result
            
        except Exception as e:
            # 使用用户友好的错误处理
            from .user_friendly_error_handler import handle_user_friendly_error
            user_error = handle_user_friendly_error(e, {
                'action': 'task_execution',
                'agent_role': agent_role,
                'task_type': task_type,
                'session_id': session_id
            })
            logger.error(f"任务执行失败: {e}", exc_info=True)
            
            # 尝试降级处理
            fallback_result = self._attempt_task_fallback(e, agent_role, task_prompt, context)
            if fallback_result:
                logger.info("成功使用降级方案执行任务")
                try:
                    # 尝试为降级结果也记录使用
                    self._record_token_usage(fallback_result, None, context, session_id, task_type)
                except Exception:
                    pass
                return fallback_result
            
            # 返回用户友好的失败结果
            return TaskResult(
                result=f"分析暂时无法完成：{user_error['message']}",
                model_used=None,
                execution_time=0,
                actual_cost=0.0,
                token_usage={},
                success=False,
                error_message=user_error['message'],
                user_friendly_error=user_error
            )
    
    def _record_token_usage(self,
                            result: TaskResult,
                            selection: Optional[ModelSelection],
                            context: Dict[str, Any],
                            session_id: str,
                            task_type: str) -> None:
        """将单次任务的Token使用写入持久化记录。

        - provider 映射到成本配置中的 provider 名称
        - 兼容不同客户端的 token_usage 字段命名
        """
        if not result or not result.success:
            return

        # 提取模型与提供商
        model_name = None
        provider_name = None
        if selection and selection.model_spec:
            model_name = selection.model_spec.name
            provider_name = selection.model_spec.provider.value
        elif result.model_used:
            model_name = result.model_used.name
            provider_name = result.model_used.provider.value if hasattr(result.model_used, 'provider') else None

        if not model_name:
            return

        # 纠正提供商名称以匹配 pricing 配置
        if provider_name is None:
            provider_name = "google" if model_name.lower().startswith("gemini") else "deepseek" if "deepseek" in model_name.lower() else "siliconflow"
        # DeepSeek 客户端将 provider 标为 OPENAI，这里统一映射为 deepseek
        if provider_name.lower() == "openai" and "deepseek" in model_name.lower():
            provider_name = "deepseek"

        # 提取 token 使用（兼容不同字段）
        usage = result.token_usage or {}
        input_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        output_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0

        # 当缺少精确用量时进行保守估算
        if (input_tokens == 0 and output_tokens == 0) and isinstance(result.result, str):
            approx_total = int(len(result.result) / 2)
            output_tokens = approx_total

        # 会话ID兜底
        session_id = session_id or context.get('session_id') if context else session_id
        if not session_id:
            session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 写入记录
        token_tracker.track_usage(
            provider=provider_name,
            model_name=model_name,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            session_id=session_id,
            analysis_type=f"multi_model_{task_type}"
        )

    def execute_collaborative_analysis(self,
                                     task_description: str,
                                     participating_agents: List[str],
                                     collaboration_mode: str = "sequential",
                                     context: Dict[str, Any] = None) -> CollaborationResult:
        """
        执行多智能体协作分析
        
        Args:
            task_description: 任务描述
            participating_agents: 参与的智能体列表
            collaboration_mode: 协作模式 (sequential, parallel, debate)
            context: 上下文信息
            
        Returns:
            CollaborationResult: 协作执行结果
        """
        context = context or {}
        session_id = context.get('session_id', f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        try:
            logger.info(f"开始协作分析: {collaboration_mode} 模式，参与者: {participating_agents}")
            
            if collaboration_mode == "sequential":
                return self._execute_sequential_collaboration(
                    task_description, participating_agents, context
                )
            elif collaboration_mode == "parallel":
                return self._execute_parallel_collaboration(
                    task_description, participating_agents, context
                )
            elif collaboration_mode == "debate":
                return self._execute_debate_collaboration(
                    task_description, participating_agents, context
                )
            else:
                raise ValueError(f"不支持的协作模式: {collaboration_mode}")
                
        except Exception as e:
            # 使用用户友好的错误处理
            from .user_friendly_error_handler import handle_user_friendly_error
            user_error = handle_user_friendly_error(e, {
                'action': 'collaborative_analysis',
                'collaboration_mode': collaboration_mode,
                'participating_agents': participating_agents,
                'session_id': session_id
            })
            logger.error(f"协作分析失败: {e}", exc_info=True)
            
            # 尝试简化协作模式的降级处理
            fallback_result = self._attempt_collaboration_fallback(
                e, task_description, participating_agents, context
            )
            if fallback_result:
                logger.info("成功使用简化协作模式")
                return fallback_result
            
            # 返回用户友好的失败结果
            return CollaborationResult(
                final_result=f"多智能体协作分析暂时无法完成：{user_error['message']}",
                participating_models=[],
                individual_results=[],
                collaboration_metadata={
                    "error": user_error['message'],
                    "user_friendly_error": user_error,
                    "fallback_attempted": True
                },
                total_cost=0.0,
                total_time=0,
                success=False,
                error_message=user_error['message']
            )
    
    def _execute_sequential_collaboration(self,
                                        task_description: str,
                                        participating_agents: List[str],
                                        context: Dict[str, Any]) -> CollaborationResult:
        """执行序列协作"""
        individual_results = []
        total_cost = 0.0
        total_time = 0
        participating_models = []
        
        current_context = task_description
        
        for i, agent_role in enumerate(participating_agents):
            # 构建当前阶段的提示词
            if i == 0:
                prompt = f"请作为{agent_role}分析以下任务：\n{task_description}"
            else:
                previous_result = individual_results[-1].result
                prompt = f"""请作为{agent_role}继续分析，基于前面的分析结果：

前面的分析：
{previous_result}

原始任务：
{task_description}

请提供你的专业分析和建议。"""
            
            # 执行当前阶段
            result = self.execute_task(
                agent_role=agent_role,
                task_prompt=prompt,
                task_type=self._get_agent_task_type(agent_role),
                context=context
            )
            
            individual_results.append(result)
            total_cost += result.actual_cost
            total_time += result.execution_time
            
            if result.model_used:
                participating_models.append(result.model_used.name)
        
        # 生成最终结果汇总
        final_result = self._synthesize_sequential_results(individual_results, task_description)
        
        return CollaborationResult(
            final_result=final_result,
            participating_models=participating_models,
            individual_results=individual_results,
            collaboration_metadata={
                "mode": "sequential",
                "stages": len(participating_agents),
                "session_id": context.get('session_id')
            },
            total_cost=total_cost,
            total_time=total_time,
            success=all(result.success for result in individual_results)
        )
    
    def _execute_parallel_collaboration(self,
                                      task_description: str,
                                      participating_agents: List[str],
                                      context: Dict[str, Any]) -> CollaborationResult:
        """执行并行协作"""
        individual_results = []
        total_cost = 0.0
        total_time = 0
        participating_models = []
        
        start_time = datetime.now()
        
        # 并行执行各个智能体的分析
        for agent_role in participating_agents:
            prompt = f"请作为{agent_role}从你的专业角度分析以下任务：\n{task_description}"
            
            result = self.execute_task(
                agent_role=agent_role,
                task_prompt=prompt,
                task_type=self._get_agent_task_type(agent_role),
                context=context
            )
            
            individual_results.append(result)
            total_cost += result.actual_cost
            
            if result.model_used:
                participating_models.append(result.model_used.name)
        
        # 并行执行的总时间是最长的单个任务时间
        total_time = max((result.execution_time for result in individual_results), default=0)
        
        # 生成最终结果汇总
        final_result = self._synthesize_parallel_results(individual_results, task_description)
        
        return CollaborationResult(
            final_result=final_result,
            participating_models=participating_models,
            individual_results=individual_results,
            collaboration_metadata={
                "mode": "parallel",
                "agents": len(participating_agents),
                "session_id": context.get('session_id')
            },
            total_cost=total_cost,
            total_time=total_time,
            success=all(result.success for result in individual_results)
        )
    
    def _execute_debate_collaboration(self,
                                    task_description: str,
                                    participating_agents: List[str],
                                    context: Dict[str, Any]) -> CollaborationResult:
        """执行辩论协作"""
        if len(participating_agents) < 2:
            raise ValueError("辩论模式至少需要2个智能体")
        
        individual_results = []
        total_cost = 0.0
        total_time = 0
        participating_models = []
        
        max_rounds = context.get('max_debate_rounds', 3)
        debate_history = []
        
        # 第一轮：各智能体提出初始观点
        for agent_role in participating_agents:
            prompt = f"""请作为{agent_role}对以下任务提出你的初始分析和观点：
{task_description}

请明确表达你的立场和理由。"""
            
            result = self.execute_task(
                agent_role=agent_role,
                task_prompt=prompt,
                task_type=self._get_agent_task_type(agent_role),
                context=context
            )
            
            individual_results.append(result)
            total_cost += result.actual_cost
            total_time += result.execution_time
            
            if result.model_used:
                participating_models.append(result.model_used.name)
            
            debate_history.append({
                "round": 1,
                "agent": agent_role,
                "position": result.result
            })
        
        # 后续轮次：辩论和反驳
        for round_num in range(2, max_rounds + 1):
            for i, agent_role in enumerate(participating_agents):
                # 收集其他智能体的观点
                other_positions = [
                    entry["position"] for entry in debate_history[-len(participating_agents):]
                    if entry["agent"] != agent_role
                ]
                
                prompt = f"""基于其他专家的观点，请作为{agent_role}提供你的进一步分析：

原始任务：
{task_description}

其他专家的观点：
{chr(10).join([f"观点 {j+1}: {pos}" for j, pos in enumerate(other_positions)])}

请：
1. 回应其他专家的观点
2. 坚持或修正你的立场
3. 提供新的论据或证据
"""
                
                result = self.execute_task(
                    agent_role=agent_role,
                    task_prompt=prompt,
                    task_type=self._get_agent_task_type(agent_role),
                    context=context
                )
                
                individual_results.append(result)
                total_cost += result.actual_cost
                total_time += result.execution_time
                
                debate_history.append({
                    "round": round_num,
                    "agent": agent_role,
                    "position": result.result
                })
        
        # 生成最终共识
        final_result = self._synthesize_debate_results(debate_history, task_description)
        
        return CollaborationResult(
            final_result=final_result,
            participating_models=list(set(participating_models)),
            individual_results=individual_results,
            collaboration_metadata={
                "mode": "debate",
                "rounds": max_rounds,
                "agents": len(participating_agents),
                "debate_history": debate_history,
                "session_id": context.get('session_id')
            },
            total_cost=total_cost,
            total_time=total_time,
            success=all(result.success for result in individual_results)
        )
    
    def _get_all_available_models(self) -> Dict[str, ModelSpec]:
        """获取所有可用模型"""
        all_models = {}
        for client in self.clients.values():
            all_models.update(client.get_supported_models())
        return all_models
    
    def _get_client_for_model(self, model_name: str) -> Optional[BaseMultiModelAdapter]:
        """根据模型名称获取对应的客户端"""
        for client in self.clients.values():
            if model_name in client.get_supported_models():
                return client
        return None
    
    def _get_default_model(self, available_models: Dict[str, ModelSpec], task_spec: TaskSpec) -> ModelSpec:
        """
        获取默认模型，用于智能路由失败时的回退
        
        Args:
            available_models: 可用模型字典
            task_spec: 任务规格
            
        Returns:
            ModelSpec: 默认模型规格
        """
        if not available_models:
            raise ValueError("没有可用的模型")
        
        # 定义模型优先级（按稳定性和通用性排序）- 使用实际可用的模型名称
        fallback_priorities = [
            'gemini-2.5-pro',                     # Google 最强模型优先
            'deepseek-ai/DeepSeek-V3',            # SiliconFlow 稳定模型
            'Qwen/Qwen3-235B-A22B-Instruct-2507', # 通用中文强模型
            'gemini-2.0-flash',                   # Google 快速模型
            'gemini-1.5-flash',                   # Google 轻量模型
            'zai-org/GLM-4.5',                    # GLM 通用模型
        ]
        
        # 首先尝试按优先级选择
        for model_name in fallback_priorities:
            if model_name in available_models:
                logger.info(f"选择优先级默认模型: {model_name}")
                return available_models[model_name]
        
        # 如果优先级模型都不可用，按任务类型选择
        if task_spec.requires_speed:
            # 寻找速度型模型
            speed_models = [name for name, spec in available_models.items() 
                          if 'flash' in name.lower() or 'turbo' in name.lower()]
            if speed_models:
                selected = speed_models[0]
                logger.info(f"选择速度型默认模型: {selected}")
                return available_models[selected]
        
        if task_spec.complexity == TaskComplexity.HIGH:
            # 寻找高性能模型
            premium_models = [name for name, spec in available_models.items() 
                            if 'pro' in name.lower() or 'plus' in name.lower()]
            if premium_models:
                selected = premium_models[0]
                logger.info(f"选择高性能默认模型: {selected}")
                return available_models[selected]
        
        # 如果都没有，选择第一个可用模型
        first_available = next(iter(available_models.values()))
        logger.info(f"选择第一个可用的默认模型: {first_available.name}")
        return first_available
    
    def _estimate_tokens(self, text: str) -> int:
        """估算文本的token数量"""
        # 简单的token估算：中文按字符计算，英文按词计算
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        english_words = len([word for word in text.split() if any(c.isalpha() for c in word)])
        return int(chinese_chars * 1.2 + english_words * 1.3)
    
    def _requires_reasoning(self, task_type: str, description: str) -> bool:
        """判断任务是否需要推理能力"""
        reasoning_types = ['technical_analysis', 'fundamental_analysis', 'risk_assessment', 'decision_making']
        reasoning_keywords = ['分析', '推理', '判断', '评估', '决策', 'analyze', 'reason', 'evaluate']
        
        return (task_type in reasoning_types or 
                any(keyword in description.lower() for keyword in reasoning_keywords))
    
    def _requires_chinese(self, text: str) -> bool:
        """判断文本是否主要是中文"""
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        return chinese_chars > len(text) * 0.3
    
    def _requires_speed(self, context: Dict[str, Any]) -> bool:
        """判断任务是否需要快速响应"""
        return (context.get('priority') == 'high' or 
                context.get('time_limit') is not None or
                context.get('real_time', False))
    
    def _get_agent_task_type(self, agent_role: str) -> str:
        """根据智能体角色获取任务类型"""
        role_task_mapping = {
            'news_hunter': 'news_analysis',
            'fundamental_expert': 'fundamental_analysis',
            'technical_analyst': 'technical_analysis',
            'sentiment_analyst': 'sentiment_analysis',
            'policy_researcher': 'policy_analysis',
            'tool_engineer': 'tool_development',
            'risk_manager': 'risk_assessment',
            'compliance_officer': 'compliance_check',
            'chief_decision_officer': 'decision_making'
        }
        # 允许从角色库覆盖
        try:
            from tradingagents.config.provider_models import model_provider_manager
            custom = model_provider_manager.role_task_types.get(agent_role)
            if isinstance(custom, str) and custom:
                return custom
        except Exception:
            pass
        return role_task_mapping.get(agent_role, 'general')
    
    def _synthesize_sequential_results(self, results: List[TaskResult], original_task: str) -> str:
        """合成序列协作的结果"""
        if not results:
            return "无法生成分析结果"
        
        # 使用最强的模型来进行最终合成
        synthesis_prompt = f"""请综合以下各阶段的分析结果，形成最终的完整分析报告：

原始任务：
{original_task}

各阶段分析结果：
"""
        
        for i, result in enumerate(results):
            synthesis_prompt += f"\n阶段 {i+1} 分析：\n{result.result}\n"
        
        synthesis_prompt += "\n请提供综合性的最终分析和建议。"
        
        # 选择最佳模型进行合成
        synthesis_result = self.execute_task(
            agent_role="chief_decision_officer",
            task_prompt=synthesis_prompt,
            task_type="decision_making",
            complexity_level="high"
        )
        
        return synthesis_result.result if synthesis_result.success else "结果合成失败"
    
    def _synthesize_parallel_results(self, results: List[TaskResult], original_task: str) -> str:
        """合成并行协作的结果"""
        if not results:
            return "无法生成分析结果"
        
        synthesis_prompt = f"""请综合以下来自不同专家的并行分析结果，形成最终的完整分析报告：

原始任务：
{original_task}

专家分析结果：
"""
        
        for i, result in enumerate(results):
            synthesis_prompt += f"\n专家 {i+1} 分析：\n{result.result}\n"
        
        synthesis_prompt += "\n请整合各专家观点，提供综合性的最终分析和建议。"
        
        # 选择最佳模型进行合成
        synthesis_result = self.execute_task(
            agent_role="chief_decision_officer",
            task_prompt=synthesis_prompt,
            task_type="decision_making",
            complexity_level="high"
        )
        
        return synthesis_result.result if synthesis_result.success else "结果合成失败"
    
    def _synthesize_debate_results(self, debate_history: List[Dict], original_task: str) -> str:
        """合成辩论协作的结果"""
        if not debate_history:
            return "无法生成分析结果"
        
        synthesis_prompt = f"""请基于以下专家辩论过程，形成最终的综合分析和共识：

原始任务：
{original_task}

辩论过程：
"""
        
        current_round = 0
        for entry in debate_history:
            if entry["round"] != current_round:
                current_round = entry["round"]
                synthesis_prompt += f"\n=== 第 {current_round} 轮 ===\n"
            
            synthesis_prompt += f"{entry['agent']}: {entry['position']}\n"
        
        synthesis_prompt += """
请分析辩论过程中的不同观点，找出共识点，并形成最终的综合判断和建议。
"""
        
        # 选择最佳模型进行合成
        synthesis_result = self.execute_task(
            agent_role="chief_decision_officer",
            task_prompt=synthesis_prompt,
            task_type="decision_making",
            complexity_level="high"
        )
        
        return synthesis_result.result if synthesis_result.success else "结果合成失败"
    
    def _check_session_cost_limit(self, session_id: str) -> bool:
        """检查会话成本限制"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            return session.total_cost < self.max_cost_per_session
        return True
    
    def _update_session_metrics(self, session_id: str, result: TaskResult, selection: ModelSelection) -> None:
        """更新会话指标"""
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = SessionMetrics(
                session_id=session_id,
                total_tasks=0,
                successful_tasks=0,
                total_cost=0.0,
                total_time=0,
                models_used={},
                avg_confidence=0.0,
                start_time=datetime.now()
            )
        
        session = self.active_sessions[session_id]
        session.total_tasks += 1
        session.total_cost += result.actual_cost
        session.total_time += result.execution_time
        
        if result.success:
            session.successful_tasks += 1
        
        if result.model_used:
            model_name = result.model_used.name
            session.models_used[model_name] = session.models_used.get(model_name, 0) + 1
        
        # 更新平均置信度
        session.avg_confidence = (session.avg_confidence * (session.total_tasks - 1) + selection.confidence_score) / session.total_tasks
    
    def _get_database_path(self) -> str:
        """获取数据库路径"""
        if 'database_path' in self.config:
            return self.config['database_path']
        
        # 尝试使用项目数据库路径
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "trading_agents.db"
        
        if db_path.parent.exists():
            return str(db_path)
        else:
            return ":memory:"
    
    def _execute_task_with_fallback(self, 
                                   model_selection: ModelSelection,
                                   task_prompt: str, 
                                   task_spec: TaskSpec,
                                   context: Dict[str, Any],
                                   agent_role: str,
                                   task_type: str) -> TaskResult:
        """
        执行任务并支持熔断回退逻辑
        
        Args:
            model_selection: 模型选择结果
            task_prompt: 任务提示词
            task_spec: 任务规格
            context: 上下文信息
            agent_role: 智能体角色
            task_type: 任务类型
            
        Returns:
            TaskResult: 任务执行结果
        """
        # 1. 尝试主要模型
        result = self._try_execute_with_model(
            model_selection.model_spec.name, task_prompt, task_spec, context
        )
        
        # 更新路由引擎性能数据
        self._update_routing_performance(model_selection.model_spec, task_type, result)
        
        if result.success:
            return result
        
        logger.warning(f"主模型 {model_selection.model_spec.name} 执行失败，尝试备用模型")
        
        # 2. 获取智能路由的备用模型
        alternative_models = self._get_alternative_models(agent_role, task_type, task_spec, context)
        
        # 3. 尝试备用模型（带指数退避）
        base_delay = 1.0
        max_attempts = 3
        
        for attempt, model_name in enumerate(alternative_models[:max_attempts]):
            if attempt > 0:
                import time
                delay = base_delay * (2 ** (attempt - 1))  # 指数退避: 1s, 2s, 4s
                logger.info(f"等待 {delay}s 后尝试备用模型 {model_name}")
                time.sleep(delay)
            
            try:
                result = self._try_execute_with_model(model_name, task_prompt, task_spec, context)
                
                # 更新路由引擎性能数据
                available_models = self._get_all_available_models()
                if model_name in available_models:
                    model_spec = available_models[model_name]
                    self._update_routing_performance(model_spec, task_type, result)
                
                if result.success:
                    logger.info(f"备用模型 {model_name} 执行成功")
                    return result
                else:
                    logger.warning(f"备用模型 {model_name} 执行失败，尝试下一个")
                    
            except Exception as e:
                logger.error(f"备用模型 {model_name} 异常: {e}")
                continue
        
        # 4. 如果所有备用模型都失败，使用最简单的降级处理
        logger.error("所有备用模型都失败，使用最终降级方案")
        fallback_result = self._attempt_task_fallback(
            RuntimeError("所有模型都失败"), agent_role, task_prompt, context
        )
        
        if fallback_result:
            return fallback_result
        else:
            # 返回最后的失败结果
            return result
    
    def _try_execute_with_model(self, model_name: str, task_prompt: str, 
                               task_spec: TaskSpec, context: Dict[str, Any]) -> TaskResult:
        """尝试使用指定模型执行任务"""
        client = self._get_client_for_model(model_name)
        if not client:
            return TaskResult(
                result=f"找不到模型 {model_name} 对应的客户端",
                model_used=None,
                execution_time=0,
                actual_cost=0.0,
                token_usage={},
                success=False,
                error_message=f"客户端不可用: {model_name}"
            )
        
        try:
            return client.execute_task(
                model_name=model_name,
                prompt=task_prompt,
                task_spec=task_spec,
                **context.get('model_params', {})
            )
        except Exception as e:
            return TaskResult(
                result=f"模型 {model_name} 执行失败: {str(e)}",
                model_used=None,
                execution_time=0,
                actual_cost=0.0,
                token_usage={},
                success=False,
                error_message=str(e)
            )
    
    def _get_alternative_models(self, agent_role: str, task_type: str, 
                               task_spec: TaskSpec, context: Dict[str, Any]) -> List[str]:
        """获取备用模型列表"""
        try:
            # 1) 优先使用绑定配置中的 fallback_chain
            binding = self.agent_bindings.get(agent_role) or {}
            chain = binding.get('fallback_chain') or []
            if chain:
                available = set(self._get_all_available_models().keys())
                # 仅返回当前可用的模型
                candidates = [m for m in chain if m in available]
                if candidates:
                    return candidates
            
            # 如果路由引擎可用，请求备用模型
            if self.routing_engine:
                available_models = self._get_all_available_models()
                # 过滤策略后再请求路由引擎，避免越界
                filtered = self._filter_candidates_by_policy(agent_role, task_type, available_models, context or {}) or available_models
                routing_decision = self.routing_engine.route_task(
                    task_description=f"备用模型选择 for {agent_role}",
                    agent_role=agent_role,
                    task_spec=task_spec,
                    available_models=filtered,
                    context=context or {}
                )
                
                if routing_decision.alternative_models:
                    return routing_decision.alternative_models
            
            # 回退到预定义的备用模型列表
            fallback_models = [
                'Qwen/Qwen3-235B-A22B-Instruct-2507',
                'gemini-2.5-flash', 
                'deepseek-ai/DeepSeek-V3',
                'zai-org/GLM-4.5'
            ]
            
            # 过滤出可用的模型
            available_models = self._get_all_available_models()
            filtered = self._filter_candidates_by_policy(agent_role, task_type, available_models, context or {}) or available_models
            return [model for model in fallback_models if model in filtered]
            
        except Exception as e:
            logger.warning(f"获取备用模型失败: {e}")
            return ['deepseek-ai/DeepSeek-V3']  # 最后的备用选择
    
    def _update_routing_performance(self, model_spec: ModelSpec, task_type: str, result: TaskResult):
        """更新路由引擎性能数据"""
        if self.routing_engine and result:
            try:
                self.routing_engine.update_model_performance(
                    model_name=model_spec.name,
                    provider=model_spec.provider.value,
                    task_type=task_type,
                    execution_time=result.execution_time,
                    success=result.success,
                    cost=result.actual_cost
                )
            except Exception as e:
                logger.debug(f"更新路由性能数据失败: {e}")
        else:
            logger.debug("路由引擎不可用，跳过性能数据更新")
    
    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """获取会话指标"""
        return self.active_sessions.get(session_id)
    
    def _attempt_task_fallback(self, 
                             original_error: Exception,
                             agent_role: str, 
                             task_prompt: str, 
                             context: Dict[str, Any]) -> Optional[TaskResult]:
        """
        尝试使用带有circuit breaker的降级方案执行任务
        
        Args:
            original_error: 原始错误
            agent_role: 智能体角色
            task_prompt: 任务提示词
            context: 上下文信息
            
        Returns:
            Optional[TaskResult]: 降级执行结果，None表示降级也失败
        """
        try:
            logger.info(f"尝试任务降级处理: {agent_role}")
            
            # 1. 获取可用模型和备选方案
            available_models = self._get_all_available_models()
            if not available_models:
                return None
                
            # 2. 使用circuit breaker模式进行多轮回退
            fallback_candidates = [
                'gemini-api/gemini-2.5-pro',
                'gemini-2.5-pro',
                'gemini-2.5-flash',
                'deepseek-ai/DeepSeek-V3',
                'zai-org/GLM-4.5'
            ]
            max_attempts = 3
            attempt_delay = 1.0  # 指数退避初始延迟
            
            for attempt in range(max_attempts):
                for candidate in fallback_candidates:
                    if candidate not in available_models:
                        continue
                    
                    try:
                        selected_model = available_models[candidate]
                        
                        # 3. 简化任务提示词
                        simplified_prompt = self._simplify_task_prompt(task_prompt, agent_role)
                        
                        # 4. 获取对应客户端
                        client = self._get_client_for_model(selected_model.name)
                        if not client:
                            continue
                        
                        # 5. 构建简化的任务规格
                        simplified_task_spec = TaskSpec(
                            task_type="general",
                            complexity=TaskComplexity.LOW,
                            estimated_tokens=min(1000, len(simplified_prompt) // 2),
                            requires_reasoning=False,
                            requires_chinese=True,
                            requires_speed=True,
                            context_data={}
                        )
                        
                        # 6. 执行简化任务
                        result = client.execute_task(
                            model_name=selected_model.name,
                            prompt=simplified_prompt,
                            task_spec=simplified_task_spec,
                            **{"temperature": 0.7, "max_tokens": 1000}
                        )
                        
                        # 7. 成功则返回结果
                        if result.success:
                            result.result = f"[简化模式-尝试{attempt+1}] {result.result}\n\n⚠️ 注意：由于系统负载原因，本次分析使用了简化模式，结果可能不够详细。"
                            logger.info(f"任务降级成功: {selected_model.name} (尝试 {attempt+1})")
                            return result
                    
                    except Exception as model_error:
                        logger.warning(f"降级模型 {candidate} 执行失败 (尝试 {attempt+1}): {model_error}")
                        continue
                
                # 指数退避延迟
                if attempt < max_attempts - 1:
                    delay = attempt_delay * (2 ** attempt)
                    logger.info(f"降级尝试 {attempt+1} 失败，等待 {delay}s 后重试")
                    time.sleep(delay)
            
            logger.error("所有降级尝试均失败")
            return None
            
        except Exception as fallback_error:
            logger.error(f"任务降级处理异常: {fallback_error}")
            return None
    
    def _attempt_collaboration_fallback(self,
                                      original_error: Exception,
                                      task_description: str,
                                      participating_agents: List[str],
                                      context: Dict[str, Any]) -> Optional[CollaborationResult]:
        """
        尝试使用简化协作模式执行分析
        
        Args:
            original_error: 原始错误
            task_description: 任务描述
            participating_agents: 参与的智能体
            context: 上下文信息
            
        Returns:
            Optional[CollaborationResult]: 简化协作结果，None表示降级也失败
        """
        try:
            logger.info("尝试简化协作模式")
            
            # 1. 只选择核心智能体（最多3个）
            core_agents = self._select_core_agents(participating_agents)
            if len(core_agents) > 3:
                core_agents = core_agents[:3]
            
            if not core_agents:
                return None
                
            # 2. 使用串行模式（最稳定）
            simplified_context = context.copy()
            simplified_context.update({
                'fallback_mode': True,
                'max_attempts': 1,
                'timeout': 30  # 30秒超时
            })
            
            # 3. 执行简化的串行协作
            return self._execute_sequential_collaboration(
                task_description, core_agents, simplified_context
            )
            
        except Exception as fallback_error:
            logger.error(f"协作降级处理也失败: {fallback_error}")
            return None
    
    def _simplify_task_prompt(self, original_prompt: str, agent_role: str) -> str:
        """
        简化任务提示词以提高执行成功率
        
        Args:
            original_prompt: 原始提示词
            agent_role: 智能体角色
            
        Returns:
            str: 简化后的提示词
        """
        role_templates = {
            'news_hunter': "请简要分析以下内容的关键信息：\n{content}\n\n请用3-5句话总结主要观点。",
            'fundamental_expert': "请对以下内容进行基础分析：\n{content}\n\n请重点说明主要发现。",
            'technical_analyst': "请对以下内容进行技术观察：\n{content}\n\n请提供简要的技术要点。",
            'risk_manager': "请评估以下内容的主要风险：\n{content}\n\n请列出2-3个关键风险点。"
        }
        
        template = role_templates.get(agent_role, 
            "请分析以下内容：\n{content}\n\n请提供简要分析。")
        
        # 限制内容长度
        content = original_prompt[:800] if len(original_prompt) > 800 else original_prompt
        
        return template.format(content=content)
    
    def _select_core_agents(self, agents: List[str]) -> List[str]:
        """
        从智能体列表中选择核心智能体
        
        Args:
            agents: 智能体列表
            
        Returns:
            List[str]: 核心智能体列表
        """
        # 定义智能体重要性排序
        agent_priority = {
            'fundamental_expert': 1,
            'news_hunter': 2,
            'risk_manager': 3,
            'technical_analyst': 4,
            'sentiment_analyst': 5,
            'policy_researcher': 6,
            'tool_engineer': 7,
            'compliance_officer': 8,
            'chief_decision_officer': 9
        }
        
        # 按重要性排序
        sorted_agents = sorted(agents, key=lambda x: agent_priority.get(x, 999))
        
        return sorted_agents
    
    def get_system_health_status(self) -> Dict[str, Any]:
        """
        获取系统健康状态，用于智能降级决策
        
        Returns:
            Dict[str, Any]: 系统健康状态
        """
        try:
            health_status = {
                'overall_health': 'healthy',
                'available_clients': len(self.clients),
                'total_models': sum(len(client.get_supported_models()) for client in self.clients.values()),
                'active_sessions': len(self.active_sessions),
                'routing_engine_active': self.routing_engine is not None,
                'recommended_fallback': None,
                'last_check': datetime.now().isoformat()
            }
            
            # 检查客户端健康状态
            unhealthy_clients = []
            for name, client in self.clients.items():
                try:
                    if not client.health_check():
                        unhealthy_clients.append(name)
                except Exception:
                    unhealthy_clients.append(name)
            
            if unhealthy_clients:
                health_status['overall_health'] = 'degraded'
                health_status['unhealthy_clients'] = unhealthy_clients
            
            # 检查系统负载
            if len(self.active_sessions) > 10:
                health_status['overall_health'] = 'high_load'
                health_status['recommended_fallback'] = 'reduce_complexity'
            
            # 如果路由引擎不可用
            if not self.routing_engine:
                health_status['overall_health'] = 'limited'
                health_status['recommended_fallback'] = 'simple_model_selection'
            
            return health_status
            
        except Exception as e:
            logger.error(f"获取系统健康状态失败: {e}")
            return {
                'overall_health': 'unknown',
                'error': str(e),
                'last_check': datetime.now().isoformat()
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            health_status = self.get_system_health_status()
            
            status = {
                'active_clients': list(self.clients.keys()),
                'total_models': sum(len(client.get_supported_models()) for client in self.clients.values()),
                'active_sessions': len(self.active_sessions),
                'routing_engine_status': 'active' if self.routing_engine else 'inactive',
                'system_health': health_status['overall_health'],
                'last_updated': datetime.now().isoformat()
            }
            
            # 添加各客户端的模型信息
            status['models_by_provider'] = {}
            for provider, client in self.clients.items():
                try:
                    models = client.get_supported_models()
                    status['models_by_provider'][provider] = [
                        {
                            'name': spec.name,
                            'type': spec.model_type,
                            'cost_per_1k': spec.cost_per_1k_tokens
                        }
                        for spec in models.values()
                    ]
                except Exception as e:
                    logger.warning(f"获取{provider}模型信息失败: {e}")
                    status['models_by_provider'][provider] = []
            
            return status
            
        except Exception as e:
            logger.error(f"获取系统状态失败: {e}")
            return {
                'active_clients': [],
                'total_models': 0,
                'active_sessions': 0,
                'routing_engine_status': 'error',
                'system_health': 'error',
                'error': str(e),
                'last_updated': datetime.now().isoformat()
            }
        """获取系统状态"""
        status = {
            'active_clients': list(self.clients.keys()),
            'total_models': sum(len(client.get_supported_models()) for client in self.clients.values()),
            'active_sessions': len(self.active_sessions),
            'routing_engine_status': 'active' if self.routing_engine else 'inactive'
        }
        
        # 添加各客户端的模型信息
        status['models_by_provider'] = {}
        for provider, client in self.clients.items():
            models = client.get_supported_models()
            status['models_by_provider'][provider] = [
                {
                    'name': spec.name,
                    'type': spec.model_type,
                    'cost_per_1k': spec.cost_per_1k_tokens
                }
                for spec in models.values()
            ]
        
        return status
