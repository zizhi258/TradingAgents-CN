"""
统一的模型提供商与模型目录配置
实现角色与模型的解耦，支持单模型和多模型模式
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# 导入统一日志系统
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('provider_models')


class ProviderType(Enum):
    """供应商类型"""
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    SILICONFLOW = "siliconflow"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI_API = "gemini_api"  # 自建 Gemini 反代（OpenAI协议）


class CollaborationMode(Enum):
    """协作模式"""
    SEQUENTIAL = "sequential"  # 串行执行
    PARALLEL = "parallel"      # 并行执行
    DEBATE = "debate"          # 辩论模式


class RoutingStrategy(Enum):
    """路由策略"""
    QUALITY_FIRST = "quality_first"      # 质量优先
    COST_FIRST = "cost_first"            # 成本优先
    LATENCY_FIRST = "latency_first"      # 时延优先
    BALANCED = "balanced"                # 均衡模式


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    provider: ProviderType
    context_length: int
    supports_function_calling: bool
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    latency_ms: int = 1000  # 平均延迟
    quality_score: float = 0.8  # 质量评分 0-1


@dataclass
class RoleConfig:
    """角色配置"""
    name: str
    description: str
    allowed_models: List[str] = field(default_factory=list)
    preferred_model: Optional[str] = None
    locked_model: Optional[str] = None  # 锁定模型，不允许更改
    enabled: bool = True  # 是否启用该角色（用于在UI中过滤显示）


# 模型目录
MODEL_CATALOG = {
    # Google AI (Gemini)
    "gemini-2.5-pro": ModelInfo(
        name="gemini-2.5-pro",
        provider=ProviderType.GOOGLE,
        context_length=2097152,  # 2M tokens
        supports_function_calling=True,
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
        latency_ms=1500,
        quality_score=0.95
    ),
    # Gemini-API 兼容渠道（与名称保持一致，便于UI区分渠道）
    "gemini-api/gemini-2.5-pro": ModelInfo(
        name="gemini-api/gemini-2.5-pro",
        provider=ProviderType.GEMINI_API,
        context_length=1048576,
        supports_function_calling=True,
        cost_per_1k_input=0.00125,
        cost_per_1k_output=0.005,
        latency_ms=1200,
        quality_score=0.94,
    ),
    "gemini-api/gemini-2.0-flash": ModelInfo(
        name="gemini-api/gemini-2.0-flash",
        provider=ProviderType.GEMINI_API,
        context_length=1048576,
        supports_function_calling=True,
        cost_per_1k_input=0.0020,
        cost_per_1k_output=0.0020,
        latency_ms=700,
        quality_score=0.83,
    ),
    "gemini-2.5-flash": ModelInfo(
        name="gemini-2.5-flash",
        provider=ProviderType.GOOGLE,
        context_length=1048576,  # 1M tokens
        supports_function_calling=True,
        cost_per_1k_input=0.000075,
        cost_per_1k_output=0.0003,
        latency_ms=800,
        quality_score=0.85
    ),
    "gemini-2.0-flash": ModelInfo(
        name="gemini-2.0-flash",
        provider=ProviderType.GOOGLE,
        context_length=1048576,
        supports_function_calling=True,
        cost_per_1k_input=0.000075,
        cost_per_1k_output=0.0003,
        latency_ms=800,
        quality_score=0.83
    ),
    
    # DeepSeek
    "deepseek-chat": ModelInfo(
        name="deepseek-chat",
        provider=ProviderType.DEEPSEEK,
        context_length=65536,
        supports_function_calling=True,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        latency_ms=1200,
        quality_score=0.88
    ),
    "deepseek-reasoner": ModelInfo(
        name="deepseek-reasoner",
        provider=ProviderType.DEEPSEEK,
        context_length=65536,
        supports_function_calling=True,
        cost_per_1k_input=0.00055,
        cost_per_1k_output=0.0022,
        latency_ms=2000,
        quality_score=0.92
    ),
    
    # SiliconFlow聚合模型
    "deepseek-ai/DeepSeek-V3": ModelInfo(
        name="deepseek-ai/DeepSeek-V3",
        provider=ProviderType.SILICONFLOW,
        context_length=131072,
        supports_function_calling=True,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        latency_ms=1200,
        quality_score=0.88
    ),
    "deepseek-ai/DeepSeek-R1": ModelInfo(
        name="deepseek-ai/DeepSeek-R1",
        provider=ProviderType.SILICONFLOW,
        context_length=163840,
        supports_function_calling=True,
        cost_per_1k_input=0.00055,
        cost_per_1k_output=0.0022,
        latency_ms=2000,
        quality_score=0.92
    ),
    "zai-org/GLM-4.5": ModelInfo(
        name="zai-org/GLM-4.5",
        provider=ProviderType.SILICONFLOW,
        context_length=131072,
        supports_function_calling=True,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00025,
        latency_ms=1100,
        quality_score=0.86
    ),
    "moonshotai/Kimi-K2-Instruct": ModelInfo(
        name="moonshotai/Kimi-K2-Instruct",
        provider=ProviderType.SILICONFLOW,
        context_length=131072,
        supports_function_calling=True,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00025,
        latency_ms=1000,
        quality_score=0.87
    ),
    "Qwen/Qwen3-235B-A22B-Instruct-2507": ModelInfo(
        name="Qwen/Qwen3-235B-A22B-Instruct-2507",
        provider=ProviderType.SILICONFLOW,
        context_length=262144,
        supports_function_calling=True,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00025,
        latency_ms=1500,
        quality_score=0.90
    ),
}


# 角色定义
ROLE_DEFINITIONS = {
    # 分析师角色
    "technical_analyst": RoleConfig(
        name="技术分析师",
        description="负责技术指标分析和价格走势预测",
        allowed_models=["deepseek-chat", "deepseek-ai/DeepSeek-V3", "gemini-2.5-flash"],
        preferred_model="deepseek-chat"
    ),
    "fundamental_expert": RoleConfig(
        name="基本面专家",
        description="负责财务分析和公司价值评估",
        allowed_models=["gemini-2.5-pro", "deepseek-reasoner", "deepseek-ai/DeepSeek-R1"],
        preferred_model="gemini-2.5-pro"
    ),
    "news_hunter": RoleConfig(
        name="快讯猎手",
        description="负责新闻收集和舆情分析",
        allowed_models=["gemini-2.5-flash", "moonshotai/Kimi-K2-Instruct", "zai-org/GLM-4.5"],
        preferred_model="gemini-2.5-flash"
    ),
    "sentiment_analyst": RoleConfig(
        name="情绪分析师",
        description="负责市场情绪和投资者心理分析",
        allowed_models=["deepseek-chat", "zai-org/GLM-4.5", "gemini-2.0-flash"],
        preferred_model="deepseek-chat"
    ),
    
    # 研究员角色
    "bull_researcher": RoleConfig(
        name="看涨研究员",
        description="从乐观角度分析投资机会",
        allowed_models=["gemini-2.5-pro", "deepseek-ai/DeepSeek-V3", "Qwen/Qwen3-235B-A22B-Instruct-2507"],
        preferred_model="gemini-2.5-pro"
    ),
    "bear_researcher": RoleConfig(
        name="看跌研究员",
        description="从谨慎角度分析投资风险",
        allowed_models=["deepseek-reasoner", "deepseek-ai/DeepSeek-R1", "gemini-2.5-pro"],
        preferred_model="deepseek-reasoner"
    ),
    
    # 管理层角色
    "risk_manager": RoleConfig(
        name="风控经理",
        description="负责风险评估和管理",
        allowed_models=["deepseek-reasoner", "gemini-2.5-pro", "deepseek-ai/DeepSeek-R1"],
        preferred_model="deepseek-reasoner"
    ),
    "chief_decision_officer": RoleConfig(
        name="首席决策官",
        description="负责最终投资决策和裁决",
        allowed_models=["gemini-2.5-pro", "deepseek-ai/DeepSeek-R1"],
        preferred_model="gemini-2.5-pro",
        locked_model="gemini-2.5-pro"  # CDO模型锁定，确保决策质量
    ),
    
    # 支持角色
    "compliance_officer": RoleConfig(
        name="合规官",
        description="负责法规合规和监管要求",
        allowed_models=["gemini-2.5-pro", "deepseek-reasoner"],
        preferred_model="gemini-2.5-pro"
    ),
    "policy_researcher": RoleConfig(
        name="政策研究员",
        description="负责政策分析和宏观研究",
        allowed_models=["zai-org/GLM-4.5", "moonshotai/Kimi-K2-Instruct", "gemini-2.5-flash"],
        preferred_model="zai-org/GLM-4.5"
    ),
    
    # 主笔人（长文写作/报告整合）
    "chief_writer": RoleConfig(
        name="主笔人",
        description="融合多方观点撰写结构化研究报告",
        # 允许多提供商、多模型，以便在UI中按提供商筛选
        allowed_models=[
            # Google AI
            "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash",
            # DeepSeek 原生
            "deepseek-chat", "deepseek-reasoner",
            # SiliconFlow 聚合（国产主流）
            "moonshotai/Kimi-K2-Instruct",
            "zai-org/GLM-4.5",
            "deepseek-ai/DeepSeek-V3",
            "deepseek-ai/DeepSeek-R1",
            # Gemini-API 兼容渠道（OpenAI协议反代）
            "gemini-api/gemini-2.5-pro",
            "gemini-api/gemini-2.0-flash",
        ],
        preferred_model="gemini-2.5-pro",
        locked_model=None,
        enabled=True,
    ),
}


class ModelProviderManager:
    """模型提供商管理器"""

    def __init__(self):
        self.model_catalog: Dict[str, ModelInfo] = MODEL_CATALOG
        # 使用拷贝以便后续合并自定义角色
        self.role_definitions: Dict[str, RoleConfig] = dict(ROLE_DEFINITIONS)
        # 记录来自角色库的额外信息
        self.role_prompts: Dict[str, Dict[str, str]] = {}
        self.role_task_types: Dict[str, str] = {}
        # 首次运行时尝试用内置角色 + 默认提示词初始化角色库
        try:
            from .role_library import seed_role_library_if_absent
            base_roles = {
                rk: {
                    'name': rc.name,
                    'description': rc.description,
                    'allowed_models': list(rc.allowed_models),
                    'preferred_model': rc.preferred_model,
                    'locked_model': rc.locked_model,
                    'enabled': getattr(rc, 'enabled', True),
                }
                for rk, rc in self.role_definitions.items()
            }
            seed_role_library_if_absent(base_roles)
        except Exception as e:
            logger.warning(f"初始化角色库失败: {e}")
        # 应用角色库覆盖
        try:
            self.apply_role_library_overrides()
        except Exception as e:
            logger.warning(f"应用角色库覆盖失败: {e}")
        logger.info("模型提供商管理器初始化完成")

    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return self.model_catalog.get(model_name)

    def get_role_config(self, role_key: str) -> Optional[RoleConfig]:
        """获取角色配置"""
        return self.role_definitions.get(role_key)

    def get_models_by_provider(self, provider: ProviderType) -> List[str]:
        return [name for name, info in self.model_catalog.items() if info.provider == provider]

    def get_allowed_models_for_role(self, role_key: str) -> List[str]:
        role = self.get_role_config(role_key)
        return list(role.allowed_models) if role else []

    def get_best_model_for_role(self, role_key: str, strategy: RoutingStrategy = RoutingStrategy.BALANCED) -> Optional[str]:
        """根据策略为角色选择最佳模型。"""
        role = self.get_role_config(role_key)
        if not role or not role.allowed_models:
            return None
        # 锁定优先
        if role.locked_model:
            return role.locked_model
        # 首选优先
        if role.preferred_model:
            return role.preferred_model

        allowed = role.allowed_models
        # 依据策略选择
        if strategy == RoutingStrategy.COST_FIRST:
            best = min(allowed, key=lambda m: self.model_catalog.get(m, ModelInfo(m, ProviderType.OPENAI, 0, False)).cost_per_1k_input)
        elif strategy == RoutingStrategy.LATENCY_FIRST:
            best = min(allowed, key=lambda m: self.model_catalog.get(m, ModelInfo(m, ProviderType.OPENAI, 0, False)).latency_ms)
        elif strategy == RoutingStrategy.QUALITY_FIRST:
            best = max(allowed, key=lambda m: self.model_catalog.get(m, ModelInfo(m, ProviderType.OPENAI, 0, False)).quality_score)
        else:  # BALANCED
            best = allowed[0]
        return best

    # ===== 角色库支持 =====
    def apply_role_library_overrides(self) -> None:
        """从 config/role_library.json 读取自定义角色，合并到角色定义中。"""
        try:
            from .role_library import load_role_library
        except Exception:
            return

        data = load_role_library() or {"roles": {}}
        roles = data.get("roles", {})
        if not isinstance(roles, dict):
            return

        for key, cfg in roles.items():
            if not isinstance(cfg, dict):
                continue
            name = cfg.get("name")
            description = cfg.get("description")
            allowed_models = cfg.get("allowed_models") or []
            preferred_model = cfg.get("preferred_model")
            locked_model = cfg.get("locked_model")
            enabled_val = cfg.get("enabled")

            if key in self.role_definitions:
                base = self.role_definitions[key]
                self.role_definitions[key] = RoleConfig(
                    name=name or base.name,
                    description=description or base.description,
                    allowed_models=allowed_models or base.allowed_models,
                    preferred_model=preferred_model or base.preferred_model,
                    locked_model=locked_model or base.locked_model,
                    enabled=enabled_val if isinstance(enabled_val, bool) else getattr(base, 'enabled', True),
                )
            else:
                # 新增角色
                self.role_definitions[key] = RoleConfig(
                    name=name or key,
                    description=description or "",
                    allowed_models=allowed_models or [],
                    preferred_model=preferred_model,
                    locked_model=locked_model,
                    enabled=enabled_val if isinstance(enabled_val, bool) else True,
                )

            # 提示词与任务类型记录
            prompts = cfg.get("prompts") or {}
            if isinstance(prompts, dict):
                self.role_prompts[key] = {k: v for k, v in prompts.items() if isinstance(v, str)}
            task_type = cfg.get("task_type")
            if isinstance(task_type, str) and task_type:
                self.role_task_types[key] = task_type

    def reload_role_library(self) -> None:
        """重新加载角色库并应用覆盖。"""
        self.role_definitions = dict(ROLE_DEFINITIONS)
        self.role_prompts = {}
        self.role_task_types = {}
        self.apply_role_library_overrides()

    def get_role_prompts(self, role_key: str) -> Dict[str, str]:
        return dict(self.role_prompts.get(role_key, {}))
    
    def get_role_config(self, role_key: str) -> Optional[RoleConfig]:
        """获取角色配置"""
        return self.role_definitions.get(role_key)
    
    def get_models_by_provider(self, provider: ProviderType) -> List[str]:
        """获取指定提供商的所有模型"""
        return [
            name for name, info in self.model_catalog.items()
            if info.provider == provider
        ]
    
    def get_allowed_models_for_role(self, role_key: str) -> List[str]:
        """获取角色允许使用的模型列表"""
        role_config = self.get_role_config(role_key)
        if role_config:
            return role_config.allowed_models
        return []
    
    def get_best_model_for_role(
        self, 
        role_key: str, 
        strategy: RoutingStrategy = RoutingStrategy.BALANCED
    ) -> Optional[str]:
        """根据策略为角色选择最佳模型"""
        role_config = self.get_role_config(role_key)
        if not role_config:
            return None
        
        # 如果有锁定模型，直接返回
        if role_config.locked_model:
            return role_config.locked_model
        
        # 根据策略选择模型
        allowed_models = role_config.allowed_models
        if not allowed_models:
            return None
        
        if strategy == RoutingStrategy.QUALITY_FIRST:
            # 选择质量最高的模型
            best_model = max(
                allowed_models,
                key=lambda m: self.model_catalog.get(m, ModelInfo("", ProviderType.OPENAI, 0, False)).quality_score
            )
        elif strategy == RoutingStrategy.COST_FIRST:
            # 选择成本最低的模型
            best_model = min(
                allowed_models,
                key=lambda m: self.model_catalog.get(m, ModelInfo("", ProviderType.OPENAI, 0, False)).cost_per_1k_input
            )
        elif strategy == RoutingStrategy.LATENCY_FIRST:
            # 选择延迟最低的模型
            best_model = min(
                allowed_models,
                key=lambda m: self.model_catalog.get(m, ModelInfo("", ProviderType.OPENAI, 0, False)).latency_ms
            )
        else:  # BALANCED
            # 使用优先模型或第一个允许的模型
            best_model = role_config.preferred_model or allowed_models[0]
        
        return best_model
    
    def validate_role_model_assignment(
        self, 
        role_assignments: Dict[str, str]
    ) -> tuple[bool, List[str]]:
        """
        验证角色-模型分配是否有效
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        
        for role_key, model_name in role_assignments.items():
            # 检查角色是否存在
            role_config = self.get_role_config(role_key)
            if not role_config:
                errors.append(f"未知角色: {role_key}")
                continue
            
            # 检查模型是否存在
            if model_name not in self.model_catalog:
                errors.append(f"未知模型: {model_name}")
                continue
            
            # 检查是否为锁定模型
            if role_config.locked_model and model_name != role_config.locked_model:
                errors.append(
                    f"角色 {role_key} 已锁定为模型 {role_config.locked_model}，"
                    f"不能使用 {model_name}"
                )
                continue
            
            # 检查模型是否在允许列表中
            if model_name not in role_config.allowed_models:
                errors.append(
                    f"角色 {role_key} 不允许使用模型 {model_name}，"
                    f"允许的模型: {role_config.allowed_models}"
                )
        
        return len(errors) == 0, errors


# 全局实例
model_provider_manager = ModelProviderManager()
