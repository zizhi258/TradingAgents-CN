"""
Google AI Client - 新版Google GenAI SDK
使用官方Google GenAI SDK (google-genai) 支持Gemini 2.5系列模型
"""

import os
import time
import json
from typing import Dict, Any, List, Optional

try:
    from google import genai
    from google.genai import types
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    genai = None
    types = None

from ..core.base_multi_model_adapter import (
    BaseMultiModelAdapter, ModelProvider, ModelSpec, TaskSpec, 
    TaskResult, TaskComplexity
)

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('google_ai_client')


class GoogleAIClient(BaseMultiModelAdapter):
    """Google AI API客户端 - 使用新版google-genai SDK"""
    
    # 支持的模型配置（根据官方2025年1月文档更新）
    SUPPORTED_MODELS = {
        "gemini-2.5-pro": {
            "type": "premium",
            "cost_per_1k": 0.0125,
            "max_tokens": 65536,  # 官方文档：输出token限制65,536
            "context_window": 1048576,  # 官方文档：输入token限制1,048,576
            "description": "Gemini 2.5 Pro，Google最先进的推理模型，支持思考模式"
        },
        "gemini-2.5-flash": {
            "type": "speed", 
            "cost_per_1k": 0.0025,
            "max_tokens": 8192,  # Flash版本输出限制较小
            "context_window": 1048576,  # 1M tokens输入
            "description": "Gemini 2.5 Flash，快速响应版本"
        },
        "gemini-2.0-flash": {
            "type": "balanced",
            "cost_per_1k": 0.0020,
            "max_tokens": 8192,
            "context_window": 1048576,
            "description": "Gemini 2.0 Flash，平衡性能与速度"
        },
        "gemini-1.5-pro": {
            "type": "general",
            "cost_per_1k": 0.0075,
            "max_tokens": 8192,
            "context_window": 2097152,
            "description": "Gemini 1.5 Pro，通用大模型"
        },
        "gemini-1.5-flash": {
            "type": "speed",
            "cost_per_1k": 0.0015,
            "max_tokens": 8192,
            "context_window": 1048576,
            "description": "Gemini 1.5 Flash，快速版本"
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ModelProvider.GOOGLE, config)
        
        if not GOOGLE_AI_AVAILABLE:
            raise ImportError(
                "Google GenAI SDK未安装。请运行: pip install google-genai"
            )
        
        # 检查环境变量 - 新版SDK优先使用 GEMINI_API_KEY
        self.api_key = (
            config.get('api_key') or 
            os.getenv('GEMINI_API_KEY') or  # 新版SDK推荐
            os.getenv('GOOGLE_AI_API_KEY') or 
            os.getenv('GOOGLE_API_KEY')
        )
        
        self.default_model = config.get('default_model', 'gemini-2.5-pro')
        self.timeout = config.get('timeout', 60)
        
        if not self.api_key:
            raise ValueError(
                "Google AI API密钥未配置。请设置环境变量: GEMINI_API_KEY, GOOGLE_AI_API_KEY, 或 GOOGLE_API_KEY"
            )
            
        self.initialize_client()
    
    def initialize_client(self) -> None:
        """初始化API客户端 - 使用新版google-genai SDK"""
        try:
            # 设置API密钥到环境变量（新版SDK会自动读取）
            if not os.getenv('GEMINI_API_KEY'):
                os.environ['GEMINI_API_KEY'] = self.api_key
            
            # 初始化客户端 - 新版API方式
            self.client = genai.Client()
            
            # 初始化支持的模型规格
            self._supported_models = {}
            for model_name, model_info in self.SUPPORTED_MODELS.items():
                self._supported_models[model_name] = ModelSpec(
                    name=model_name,
                    provider=ModelProvider.GOOGLE,
                    model_type=model_info['type'],
                    cost_per_1k_tokens=model_info['cost_per_1k'],
                    max_tokens=model_info['max_tokens'],
                    context_window=model_info['context_window'],
                    supports_streaming=True
                )
            
            logger.info(f"Google AI客户端初始化完成（新版SDK），支持{len(self._supported_models)}个模型")
            
        except Exception as e:
            logger.error(f"Google AI客户端初始化失败: {e}")
            raise
    
    def get_supported_models(self) -> Dict[str, ModelSpec]:
        """获取支持的模型列表"""
        return self._supported_models.copy()
    
    def execute_task(self,
                    model_name: str,
                    prompt: str,
                    task_spec: TaskSpec,
                    **kwargs) -> TaskResult:
        """
        执行具体任务 - 使用新版google-genai API
        
        Args:
            model_name: 模型名称
            prompt: 提示词
            task_spec: 任务规格
            **kwargs: 其他参数
            
        Returns:
            TaskResult: 任务执行结果
        """
        start_time = time.time()
        
        try:
            # 检查模型是否支持
            if model_name not in self._supported_models:
                raise ValueError(f"不支持的模型: {model_name}")
            
            model_spec = self._supported_models[model_name]
            
            # 创建生成配置 - 新版API方式
            max_output_tokens = min(
                model_spec.max_tokens,
                kwargs.get('max_tokens', 8192)
            )
            
            # 对于推理任务，禁用思考模式以获得确定性结果
            thinking_config = None
            if model_name.startswith("gemini-2.5"):
                thinking_budget = 0 if task_spec.requires_reasoning else None
                if thinking_budget is not None:
                    thinking_config = types.ThinkingConfig(thinking_budget=thinking_budget)
            
            # 构建生成配置
            config = types.GenerateContentConfig(
                temperature=kwargs.get('temperature', self._get_optimal_temperature(task_spec)),
                top_p=kwargs.get('top_p', 0.8),
                top_k=kwargs.get('top_k', 40),
                max_output_tokens=max_output_tokens,
            )
            
            # 添加思考配置（如果适用）
            if thinking_config:
                config.thinking_config = thinking_config
            
            # 使用新版API调用
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # 处理响应
            if response.text:
                # 计算token使用量
                estimated_input_tokens = len(prompt.split()) * 1.3  # 粗略估算
                estimated_output_tokens = len(response.text.split()) * 1.3
                total_tokens = int(estimated_input_tokens + estimated_output_tokens)
                
                # 如果响应中有usage信息，使用精确值
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    usage = response.usage_metadata
                    if hasattr(usage, 'prompt_token_count'):
                        estimated_input_tokens = usage.prompt_token_count
                    if hasattr(usage, 'candidates_token_count'):
                        estimated_output_tokens = usage.candidates_token_count
                    total_tokens = int(estimated_input_tokens + estimated_output_tokens)
                
                # 计算实际成本
                actual_cost = (total_tokens / 1000) * model_spec.cost_per_1k_tokens
                
                token_usage = {
                    'prompt_tokens': int(estimated_input_tokens),
                    'completion_tokens': int(estimated_output_tokens),
                    'total_tokens': total_tokens
                }
                
                # 更新性能指标
                self.update_performance_metrics(
                    model_name, task_spec.task_type, execution_time, True
                )
                
                logger.info(f"任务执行成功: {model_name}, 耗时: {execution_time}ms, 成本: ${actual_cost:.6f}")
                
                return TaskResult(
                    result=response.text,
                    model_used=model_spec,
                    execution_time=execution_time,
                    actual_cost=actual_cost,
                    token_usage=token_usage,
                    success=True
                )
            else:
                error_msg = "模型返回空响应"
                
                # 检查是否有候选结果被过滤
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'finish_reason'):
                        error_msg = f"响应被过滤: {candidate.finish_reason}"
                
                logger.error(f"{error_msg}: 模型={model_name}")
                
                return TaskResult(
                    result="",
                    model_used=model_spec,
                    execution_time=execution_time,
                    actual_cost=0.0,
                    token_usage={},
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"执行异常: {str(e)}"
            logger.error(f"Google AI任务执行失败: {error_msg}", exc_info=True)
            
            # 更新性能指标
            self.update_performance_metrics(
                model_name, task_spec.task_type, execution_time, False
            )
            
            return TaskResult(
                result="",
                model_used=self._supported_models.get(model_name),
                execution_time=execution_time,
                actual_cost=0.0,
                token_usage={},
                success=False,
                error_message=error_msg
            )
    
    def estimate_cost(self, model_name: str, estimated_tokens: int) -> float:
        """估算任务成本"""
        if model_name not in self._supported_models:
            return 0.0
            
        model_spec = self._supported_models[model_name]
        return (estimated_tokens / 1000) * model_spec.cost_per_1k_tokens
    
    def health_check(self) -> bool:
        """健康检查，确认API可用性 - 使用新版API"""
        try:
            # 使用最轻量级的模型进行健康检查（降低成本）
            response = self.client.models.generate_content(
                model="gemini-1.5-flash",
                contents="Hello, please respond with 'OK'",
                config=types.GenerateContentConfig(
                    max_output_tokens=10,
                    temperature=0.1
                )
            )
            
            if response.text and 'OK' in response.text:
                logger.info("Google AI API健康检查通过（新版SDK）")
                return True
            else:
                logger.warning(f"Google AI API健康检查失败: 响应异常 - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Google AI API健康检查异常: {e}")
            return False
    
    def get_model_recommendations(self, task_spec: TaskSpec) -> List[str]:
        """
        根据任务规格推荐最适合的模型 - 统一优先推荐gemini-2.5-pro
        
        Args:
            task_spec: 任务规格
            
        Returns:
            List[str]: 推荐的模型名称列表，按优先级排序
        """
        # 始终优先推荐gemini-2.5-pro，然后是其他备选模型
        recommendations = ['gemini-2.5-pro']
        
        # 根据任务复杂度添加备选模型
        if task_spec.complexity == TaskComplexity.HIGH:
            if task_spec.requires_reasoning:
                recommendations.extend(['gemini-1.5-pro'])
            else:
                recommendations.extend(['gemini-2.0-flash', 'gemini-1.5-pro'])
                
        elif task_spec.complexity == TaskComplexity.MEDIUM:
            if task_spec.requires_speed:
                recommendations.extend(['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'])
            else:
                recommendations.extend(['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-2.5-flash'])
                
        else:  # LOW complexity
            recommendations.extend(['gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-2.0-flash'])
        
        # 对于超长文本，确保2.5 Pro在首位
        if task_spec.estimated_tokens > 500000:
            if 'gemini-2.5-pro' in recommendations:
                recommendations.remove('gemini-2.5-pro')
            recommendations.insert(0, 'gemini-2.5-pro')
            recommendations.insert(1, 'gemini-1.5-pro')
        
        # 去重并保持顺序，gemini-2.5-pro始终在首位
        seen = set()
        unique_recommendations = []
        for model in recommendations:
            if model not in seen and model in self._supported_models:
                seen.add(model)
                unique_recommendations.append(model)
        
        # 确保gemini-2.5-pro总是第一个
        if 'gemini-2.5-pro' in unique_recommendations:
            unique_recommendations.remove('gemini-2.5-pro')
        unique_recommendations.insert(0, 'gemini-2.5-pro')
        
        return unique_recommendations
    
    def _get_optimal_temperature(self, task_spec: TaskSpec) -> float:
        """根据任务规格获取最优温度参数"""
        if task_spec.requires_reasoning:
            return 0.1  # 推理任务需要更确定性的输出
        elif task_spec.task_type in ['sentiment_analysis', 'creative_writing']:
            return 0.8  # 情感分析和创作任务可以更有创意
        elif task_spec.complexity == TaskComplexity.HIGH:
            return 0.3  # 复杂任务需要平衡创造性和准确性
        else:
            return 0.5  # 默认中等温度
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """获取模型详细信息"""
        if model_name not in self._supported_models:
            return {}
            
        model_spec = self._supported_models[model_name]
        model_info = self.SUPPORTED_MODELS.get(model_name, {})
        
        return {
            'name': model_spec.name,
            'provider': model_spec.provider.value,
            'type': model_spec.model_type,
            'cost_per_1k_tokens': model_spec.cost_per_1k_tokens,
            'max_tokens': model_spec.max_tokens,
            'context_window': model_spec.context_window,
            'description': model_info.get('description', ''),
            'supports_streaming': model_spec.supports_streaming
        }
    
    def generate_with_thinking(self,
                              model_name: str,
                              prompt: str,
                              task_spec: TaskSpec,
                              thinking_prompt: str = None,
                              **kwargs) -> TaskResult:
        """
        使用思维链生成内容（仅适用于Gemini 2.5系列模型）
        
        Args:
            model_name: 模型名称
            prompt: 主要提示词
            task_spec: 任务规格
            thinking_prompt: 思维链提示词
            **kwargs: 其他参数
            
        Returns:
            TaskResult: 任务执行结果
        """
        # 对于Gemini 2.5系列，使用内建的思考模式
        if model_name.startswith("gemini-2.5"):
            # 启用思考模式
            kwargs['thinking_budget'] = kwargs.get('thinking_budget', 5000)
            return self.execute_task(model_name, prompt, task_spec, **kwargs)
        
        # 对于其他模型，使用传统的思维链提示词方法
        if thinking_prompt is None:
            thinking_prompt = """
请按以下步骤分析：
1. 理解问题的核心
2. 分解问题要素
3. 逐步推理分析
4. 得出结论并给出理由

现在开始分析：
"""
        
        # 构建思维链提示词
        enhanced_prompt = f"{thinking_prompt}\n\n{prompt}"
        
        return self.execute_task(model_name, enhanced_prompt, task_spec, **kwargs)