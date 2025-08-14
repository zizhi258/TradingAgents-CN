"""
分析模式配置
管理单模型和多模型的执行策略
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from .provider_models import (
    CollaborationMode, 
    RoutingStrategy, 
    model_provider_manager
)

# 导入统一日志系统
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('analysis_modes')


class AnalysisMode(Enum):
    """分析模式"""
    SINGLE = "single"    # 单模型模式
    MULTI = "multi"      # 多模型模式


@dataclass
class MethodConfig:
    """方法层配置"""
    analysis_mode: AnalysisMode
    collaboration_mode: CollaborationMode
    routing_strategy: RoutingStrategy
    
    # 成本和性能限制
    max_budget: float = 2.0
    max_concurrent_tasks: int = 5
    enable_caching: bool = True
    
    # 单模型配置
    single_model_provider: Optional[str] = None
    single_model_name: Optional[str] = None
    
    # 多模型配置
    role_model_policies: Dict[str, Any] = field(default_factory=dict)
    fallback_models: List[Dict[str, str]] = field(default_factory=list)


@dataclass 
class BusinessConfig:
    """业务层配置"""
    market_type: str  # A股|美股|港股|全球
    targets: List[str]  # 股票代码列表
    analysis_date: str
    research_depth: int = 3  # 1-5级深度


class AnalysisModeManager:
    """分析模式管理器"""
    
    def __init__(self):
        self.model_manager = model_provider_manager
        logger.info("分析模式管理器初始化完成")
    
    def create_single_model_config(
        self,
        provider: str = "deepseek",
        model: str = "deepseek-chat",
        max_budget: float = 1.0
    ) -> MethodConfig:
        """创建单模型配置"""
        return MethodConfig(
            analysis_mode=AnalysisMode.SINGLE,
            collaboration_mode=CollaborationMode.SEQUENTIAL,
            routing_strategy=RoutingStrategy.BALANCED,
            max_budget=max_budget,
            single_model_provider=provider,
            single_model_name=model
        )
    
    def create_multi_model_config(
        self,
        collaboration_mode: CollaborationMode = CollaborationMode.DEBATE,
        routing_strategy: RoutingStrategy = RoutingStrategy.QUALITY_FIRST,
        role_model_policies: Optional[Dict[str, Any]] = None,
        max_budget: float = 2.0
    ) -> MethodConfig:
        """创建多模型配置"""
        
        # 如果没有提供角色-模型策略，使用默认配置
        if role_model_policies is None:
            role_model_policies = self._get_default_role_model_policies(routing_strategy)
        
        return MethodConfig(
            analysis_mode=AnalysisMode.MULTI,
            collaboration_mode=collaboration_mode,
            routing_strategy=routing_strategy,
            max_budget=max_budget,
            role_model_policies=role_model_policies,
            fallback_models=[
                {"provider": "siliconflow", "model": "zai-org/GLM-4.5"},
                {"provider": "deepseek", "model": "deepseek-chat"}
            ]
        )
    
    def _get_default_role_model_policies(
        self, 
        strategy: RoutingStrategy
    ) -> Dict[str, Any]:
        """获取默认的角色-模型策略"""
        
        policies = {
            "allowed_models_by_role": {},
            "model_overrides": {}
        }
        
        # 根据策略为每个角色选择最佳模型
        for role_key in self.model_manager.role_definitions.keys():
            role_config = self.model_manager.get_role_config(role_key)
            if role_config:
                # 获取允许的模型列表
                policies["allowed_models_by_role"][role_key] = role_config.allowed_models
                
                # 如果有锁定模型，设置覆盖
                if role_config.locked_model:
                    policies["model_overrides"][role_key] = role_config.locked_model
                else:
                    # 根据策略选择最佳模型
                    best_model = self.model_manager.get_best_model_for_role(role_key, strategy)
                    if best_model:
                        policies["model_overrides"][role_key] = best_model
        
        return policies
    
    def merge_config_with_overrides(
        self,
        base_config: MethodConfig,
        user_overrides: Dict[str, Any]
    ) -> MethodConfig:
        """合并用户覆盖配置"""
        
        # 复制基础配置
        import copy
        merged_config = copy.deepcopy(base_config)
        
        # 应用用户覆盖
        for key, value in user_overrides.items():
            if hasattr(merged_config, key):
                setattr(merged_config, key, value)
            elif key in ["allowed_models_by_role", "model_overrides"]:
                # 处理角色-模型策略
                if "role_model_policies" not in merged_config.__dict__:
                    merged_config.role_model_policies = {}
                merged_config.role_model_policies[key] = value
        
        return merged_config
    
    def validate_config(self, config: MethodConfig) -> tuple[bool, List[str]]:
        """验证配置有效性"""
        errors = []
        
        # 单模型模式验证
        if config.analysis_mode == AnalysisMode.SINGLE:
            if not config.single_model_name:
                errors.append("单模型模式必须指定模型名称")
            elif config.single_model_name not in self.model_manager.model_catalog:
                errors.append(f"未知模型: {config.single_model_name}")
        
        # 多模型模式验证
        elif config.analysis_mode == AnalysisMode.MULTI:
            if not config.role_model_policies:
                errors.append("多模型模式必须提供角色-模型策略")
            else:
                # 验证角色-模型分配
                model_overrides = config.role_model_policies.get("model_overrides", {})
                is_valid, validation_errors = self.model_manager.validate_role_model_assignment(
                    model_overrides
                )
                if not is_valid:
                    errors.extend(validation_errors)
        
        # 预算验证
        if config.max_budget <= 0:
            errors.append("最大预算必须大于0")
        
        return len(errors) == 0, errors
    
    def get_preset_configs(self) -> Dict[str, MethodConfig]:
        """获取预设配置"""
        return {
            "single_fast": self.create_single_model_config(
                provider="deepseek",
                model="deepseek-chat",
                max_budget=0.5
            ),
            "single_quality": self.create_single_model_config(
                provider="google",
                model="gemini-2.5-pro",
                max_budget=1.0
            ),
            "multi_balanced": self.create_multi_model_config(
                collaboration_mode=CollaborationMode.PARALLEL,
                routing_strategy=RoutingStrategy.BALANCED,
                max_budget=1.5
            ),
            "multi_debate": self.create_multi_model_config(
                collaboration_mode=CollaborationMode.DEBATE,
                routing_strategy=RoutingStrategy.QUALITY_FIRST,
                max_budget=2.0
            ),
            "multi_cost_optimized": self.create_multi_model_config(
                collaboration_mode=CollaborationMode.SEQUENTIAL,
                routing_strategy=RoutingStrategy.COST_FIRST,
                max_budget=0.8
            )
        }


# 全局实例
analysis_mode_manager = AnalysisModeManager()