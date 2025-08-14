"""
Base Multi-Model Adapter Abstract Class
统一的多模型适配器抽象基类，为不同LLM提供商提供统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import time
import uuid


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ModelProvider(Enum):
    """模型提供商枚举"""
    SILICONFLOW = "siliconflow"
    GOOGLE = "google"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass
class ModelSpec:
    """模型规格定义"""
    name: str
    provider: ModelProvider
    model_type: str  # 'reasoning', 'speed', 'general', 'premium', etc.
    cost_per_1k_tokens: float
    max_tokens: int
    supports_streaming: bool = True
    context_window: int = 4096


@dataclass
class TaskSpec:
    """任务规格定义"""
    task_type: str
    complexity: TaskComplexity
    estimated_tokens: int
    requires_reasoning: bool = False
    requires_chinese: bool = False
    requires_speed: bool = False
    context_data: Dict[str, Any] = None


@dataclass
class ModelSelection:
    """模型选择结果"""
    model_spec: ModelSpec
    confidence_score: float
    reasoning: str
    estimated_cost: float
    estimated_time: int  # milliseconds
    selection_id: str = None
    
    def __post_init__(self):
        if not self.selection_id:
            self.selection_id = str(uuid.uuid4())


@dataclass
class TaskResult:
    """任务执行结果"""
    result: str
    model_used: ModelSpec
    execution_time: int  # milliseconds
    actual_cost: float
    token_usage: Dict[str, int]
    success: bool = True
    error_message: str = None
    task_id: str = None
    user_friendly_error: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())


class BaseMultiModelAdapter(ABC):
    """
    多模型适配器抽象基类
    定义所有LLM适配器必须实现的核心接口
    """
    
    def __init__(self, provider: ModelProvider, config: Dict[str, Any]):
        self.provider = provider
        self.config = config
        self._client = None
        self._supported_models = {}
        self._performance_cache = {}
        
    @abstractmethod
    def initialize_client(self) -> None:
        """初始化API客户端"""
        pass
        
    @abstractmethod
    def get_supported_models(self) -> Dict[str, ModelSpec]:
        """获取支持的模型列表"""
        pass
    
    @abstractmethod
    def execute_task(self, 
                    model_name: str,
                    prompt: str,
                    task_spec: TaskSpec,
                    **kwargs) -> TaskResult:
        """
        执行具体任务
        
        Args:
            model_name: 模型名称
            prompt: 提示词
            task_spec: 任务规格
            **kwargs: 其他参数
            
        Returns:
            TaskResult: 任务执行结果
        """
        pass
    
    @abstractmethod
    def estimate_cost(self, 
                     model_name: str,
                     estimated_tokens: int) -> float:
        """估算任务成本"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查，确认API可用性"""
        pass
    
    def get_model_fitness_score(self, 
                               model_name: str,
                               task_spec: TaskSpec) -> float:
        """
        计算模型对特定任务的适配度评分
        
        Args:
            model_name: 模型名称
            task_spec: 任务规格
            
        Returns:
            float: 适配度评分 (0.0-1.0)
        """
        if model_name not in self._supported_models:
            return 0.0
            
        model = self._supported_models[model_name]
        score = 0.0
        
        # 基础兼容性评分
        base_score = 0.6
        
        # 任务类型匹配度
        type_bonus = 0.0
        if task_spec.requires_reasoning and model.model_type in ['reasoning', 'premium']:
            type_bonus += 0.2
        elif task_spec.requires_speed and model.model_type in ['speed', 'general']:
            type_bonus += 0.2
        elif task_spec.requires_chinese and model.model_type == 'chinese':
            type_bonus += 0.15
            
        # 复杂度匹配度
        complexity_bonus = 0.0
        if task_spec.complexity == TaskComplexity.HIGH:
            if model.model_type in ['reasoning', 'premium']:
                complexity_bonus = 0.15
        elif task_spec.complexity == TaskComplexity.LOW:
            if model.model_type in ['speed', 'general']:
                complexity_bonus = 0.1
                
        # 成本效益考虑
        cost_penalty = min(model.cost_per_1k_tokens / 0.01, 0.1)  # 成本越高扣分越多
        
        score = base_score + type_bonus + complexity_bonus - cost_penalty
        return min(max(score, 0.0), 1.0)
    
    def update_performance_metrics(self,
                                  model_name: str,
                                  task_type: str,
                                  execution_time: int,
                                  success: bool) -> None:
        """更新模型性能指标缓存"""
        key = f"{model_name}_{task_type}"
        if key not in self._performance_cache:
            self._performance_cache[key] = {
                'total_calls': 0,
                'successful_calls': 0,
                'avg_response_time': 0,
                'total_time': 0
            }
            
        metrics = self._performance_cache[key]
        metrics['total_calls'] += 1
        metrics['total_time'] += execution_time
        metrics['avg_response_time'] = metrics['total_time'] / metrics['total_calls']
        
        if success:
            metrics['successful_calls'] += 1
    
    def get_performance_metrics(self, model_name: str, task_type: str) -> Dict[str, float]:
        """获取模型性能指标"""
        key = f"{model_name}_{task_type}"
        if key not in self._performance_cache:
            return {}
            
        metrics = self._performance_cache[key]
        success_rate = metrics['successful_calls'] / metrics['total_calls'] if metrics['total_calls'] > 0 else 0
        
        return {
            'avg_response_time': metrics['avg_response_time'],
            'success_rate': success_rate,
            'total_calls': metrics['total_calls']
        }