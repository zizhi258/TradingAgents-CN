"""
SiliconFlow API Client
硅基流动API客户端，支持DeepSeek、Qwen、GLM、Kimi等多种模型
"""

import os
import time
import json
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..core.base_multi_model_adapter import (
    BaseMultiModelAdapter, ModelProvider, ModelSpec, TaskSpec, 
    TaskResult, TaskComplexity
)

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('siliconflow_client')


class SiliconFlowClient(BaseMultiModelAdapter):
    """硅基流动API客户端"""
    
    # 支持的模型配置 (2025年最新)
    SUPPORTED_MODELS = {
        # DeepSeek 系列
        "deepseek-ai/DeepSeek-R1": {
            "type": "reasoning",
            "cost_per_1k": 0.016,
            "max_tokens": 8192,
            "context_window": 160000,
            "description": "DeepSeek-R1 强化学习推理模型，MoE 671B参数，媲美OpenAI-o1"
        },
        "Pro/deepseek-ai/DeepSeek-R1": {
            "type": "reasoning",
            "cost_per_1k": 0.016,
            "max_tokens": 8192,
            "context_window": 160000,
            "description": "DeepSeek-R1 Pro版本，强化学习推理模型，顶级性能"
        },
        "deepseek-ai/DeepSeek-V3": {
            "type": "general",
            "cost_per_1k": 0.008,
            "max_tokens": 8192,
            "context_window": 128000,
            "description": "DeepSeek-V3-0324，MoE 671B参数，超越GPT-4.5性能"
        },
        "Pro/deepseek-ai/DeepSeek-V3": {
            "type": "general",
            "cost_per_1k": 0.008,
            "max_tokens": 8192,
            "context_window": 128000,
            "description": "DeepSeek-V3 Pro版本，工具调用、角色扮演全面提升"
        },
        
        # 千问 Qwen 系列
        "Qwen/Qwen3-Coder-480B-A35B-Instruct": {
            "type": "coder",
            "cost_per_1k": 0.016,
            "max_tokens": 8192,
            "context_window": 256000,
            "description": "千问3代码480B，最强代理编程能力，MoE 480B参数"
        },
        "Qwen/Qwen3-235B-A22B-Thinking-2507": {
            "type": "thinking",
            "cost_per_1k": 0.010,
            "max_tokens": 8192,
            "context_window": 256000,
            "description": "千问3思考模型235B，专注复杂推理，开源思考模型顶尖"
        },
        "Qwen/Qwen3-235B-A22B-Instruct-2507": {
            "type": "instruct",
            "cost_per_1k": 0.010,
            "max_tokens": 8192,
            "context_window": 256000,
            "description": "千问3指令模型235B，MoE架构，多语言长上下文"
        },
        
        # 智谱 GLM 系列
        "zai-org/GLM-4.5": {
            "type": "agent",
            "cost_per_1k": 0.014,
            "max_tokens": 8192,
            "context_window": 128000,
            "description": "GLM-4.5，专为智能体应用打造，MoE 335B参数"
        },
        "zai-org/GLM-4.5-Air": {
            "type": "agent",
            "cost_per_1k": 0.006,
            "max_tokens": 8192,
            "context_window": 128000,
            "description": "GLM-4.5-Air，轻量级智能体模型，MoE 106B参数"
        },
        
        # Step 系列
        "stepfun-ai/step3": {
            "type": "multimodal",
            "cost_per_1k": 0.010,
            "max_tokens": 8192,
            "context_window": 64000,
            "description": "Step3多模态推理模型，MoE 321B参数，视觉语言推理顶级"
        },
        
        # Kimi 系列
        "moonshotai/Kimi-K2-Instruct": {
            "type": "agent",
            "cost_per_1k": 0.016,
            "max_tokens": 8192,
            "context_window": 128000,
            "description": "Kimi K2，超强代码和Agent能力，MoE 1T参数"
        },
        "Pro/moonshotai/Kimi-K2-Instruct": {
            "type": "agent",
            "cost_per_1k": 0.016,
            "max_tokens": 8192,
            "context_window": 128000,
            "description": "Kimi K2 Pro版本，顶级代码和智能体能力"
        },
        
        # 百度文心系列
        "baidu/ERNIE-4.5-300B-A47B": {
            "type": "chinese",
            "cost_per_1k": 0.008,
            "max_tokens": 8192,
            "context_window": 32000,
            "description": "文心4.5，MoE 300B参数，专为中文优化"
        },
        
        # 兼容旧版本模型
        "Qwen/Qwen2.5-7B-Instruct": {
            "type": "balanced",
            "cost_per_1k": 0.0005,
            "max_tokens": 4096,
            "context_window": 32768,
            "description": "千问2.5 7B指令模型，平衡性能"
        },
        "Qwen/Qwen2.5-72B-Instruct": {
            "type": "premium",
            "cost_per_1k": 0.0015,
            "max_tokens": 4096,
            "context_window": 131072,
            "description": "千问2.5 72B指令模型，高性能大模型"
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ModelProvider.SILICONFLOW, config)
        self.api_key = config.get('api_key') or os.getenv('SILICONFLOW_API_KEY')
        self.base_url = config.get('base_url', 'https://api.siliconflow.cn/v1')
        self.default_model = config.get('default_model', 'Qwen/Qwen3-Coder-480B-A35B-Instruct')
        self.timeout = config.get('timeout', 60)
        
        if not self.api_key:
            raise ValueError("SiliconFlow API密钥未配置")
            
        self.initialize_client()
    
    def initialize_client(self) -> None:
        """初始化API客户端"""
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # 初始化支持的模型规格
        self._supported_models = {}
        for model_name, model_info in self.SUPPORTED_MODELS.items():
            self._supported_models[model_name] = ModelSpec(
                name=model_name,
                provider=ModelProvider.SILICONFLOW,
                model_type=model_info['type'],
                cost_per_1k_tokens=model_info['cost_per_1k'],
                max_tokens=model_info['max_tokens'],
                context_window=model_info['context_window'],
                supports_streaming=True
            )
        
        logger.info(f"SiliconFlow客户端初始化完成，支持{len(self._supported_models)}个模型")
    
    def get_supported_models(self) -> Dict[str, ModelSpec]:
        """获取支持的模型列表"""
        return self._supported_models.copy()
    
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
        start_time = time.time()
        
        try:
            # 检查模型是否支持
            if model_name not in self._supported_models:
                raise ValueError(f"不支持的模型: {model_name}")
            
            model_spec = self._supported_models[model_name]
            
            # 准备请求参数
            streaming = bool(kwargs.get('stream', False))
            on_token = kwargs.get('on_token')
            request_data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": min(model_spec.max_tokens, kwargs.get('max_tokens', 4096)),
                "temperature": kwargs.get('temperature', self._get_optimal_temperature(task_spec)),
                "top_p": kwargs.get('top_p', 0.8),
                "stream": streaming
            }
            
            # 根据模型动态调整超时时间
            model_timeout = self.timeout
            if 'DeepSeek-R1' in model_name:
                # DeepSeek-R1 推理模型需要更长时间
                model_timeout = 120  # 2分钟
                logger.info(f"使用DeepSeek-R1模型，超时时间调整为{model_timeout}秒")
            elif 'Thinking' in model_name or 'reasoning' in model_spec.model_type:
                # 思考类模型也需要更长时间
                model_timeout = 90  # 1.5分钟
            
            # 发送API请求
            if streaming and callable(on_token):
                # 使用SSE流式响应
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=request_data,
                    timeout=model_timeout,
                    stream=True
                )

                if response.status_code != 200:
                    execution_time = int((time.time() - start_time) * 1000)
                    error_msg = f"API请求失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return TaskResult(
                        result="",
                        model_used=model_spec,
                        execution_time=execution_time,
                        actual_cost=0.0,
                        token_usage={},
                        success=False,
                        error_message=error_msg
                    )

                full_text = ""
                usage = {}
                try:
                    # 显式按UTF-8解码SSE，避免在某些环境下出现乱码
                    for raw_line in response.iter_lines(decode_unicode=False):
                        if not raw_line:
                            continue
                        # 原始字节按UTF-8解码，忽略非法字节
                        try:
                            line = raw_line.decode('utf-8', errors='ignore').strip()
                        except Exception:
                            # 兜底：退回原始bytes的str表示
                            line = str(raw_line).strip()
                        if line.startswith("data: "):
                            line = line[6:].strip()
                        if line in ("[DONE]", "{\"event\":\"done\"}"):
                            break
                        # 尝试解析JSON块
                        try:
                            chunk = json.loads(line)
                        except Exception:
                            # 兼容非标准行，忽略
                            continue
                        # SiliconFlow兼容：choices[0].delta.content
                        delta_text = ""
                        if isinstance(chunk, dict):
                            if 'choices' in chunk and chunk['choices']:
                                choice = chunk['choices'][0]
                                delta_text = (
                                    (choice.get('delta') or {}).get('content') or
                                    (choice.get('message') or {}).get('content') or
                                    ""
                                )
                            if 'usage' in chunk and not usage:
                                usage = chunk.get('usage') or {}
                        if delta_text:
                            full_text += delta_text
                            try:
                                on_token(delta_text)
                            except Exception:
                                pass
                finally:
                    execution_time = int((time.time() - start_time) * 1000)

                # 计算成本/用量兜底
                total_tokens = usage.get('total_tokens') if isinstance(usage, dict) else None
                if not total_tokens and full_text:
                    approx_in = max(1, int(len(prompt) / 2))
                    approx_out = int(len(full_text) / 2)
                    usage = {
                        'prompt_tokens': approx_in,
                        'completion_tokens': approx_out,
                        'total_tokens': approx_in + approx_out
                    }
                actual_cost = ((usage.get('total_tokens', 0)) / 1000) * model_spec.cost_per_1k_tokens if isinstance(usage, dict) else 0.0

                # 更新性能指标
                self.update_performance_metrics(
                    model_name, task_spec.task_type, execution_time, True
                )

                logger.info(f"任务执行成功(流式): {model_name}, 耗时: {execution_time}ms")
                return TaskResult(
                    result=full_text,
                    model_used=model_spec,
                    execution_time=execution_time,
                    actual_cost=actual_cost,
                    token_usage=usage if isinstance(usage, dict) else {},
                    success=True
                )
            else:
                # 普通非流式请求
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=request_data,
                    timeout=model_timeout
                )

                execution_time = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    error_msg = f"API请求失败: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return TaskResult(
                        result="",
                        model_used=model_spec,
                        execution_time=execution_time,
                        actual_cost=0.0,
                        token_usage={},
                        success=False,
                        error_message=error_msg
                    )

                response_data = response.json()

                # 解析响应
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    result_text = response_data['choices'][0]['message']['content']
                    usage = response_data.get('usage', {})

                    # 计算实际成本
                    total_tokens = usage.get('total_tokens', 0)
                    actual_cost = (total_tokens / 1000) * model_spec.cost_per_1k_tokens

                    # 更新性能指标
                    self.update_performance_metrics(
                        model_name, task_spec.task_type, execution_time, True
                    )

                    logger.info(f"任务执行成功: {model_name}, 耗时: {execution_time}ms, 成本: ${actual_cost:.6f}")

                    return TaskResult(
                        result=result_text,
                        model_used=model_spec,
                        execution_time=execution_time,
                        actual_cost=actual_cost,
                        token_usage=usage,
                        success=True
                    )
                else:
                    error_msg = "API响应格式异常"
                    logger.error(f"{error_msg}: {response_data}")
                    return TaskResult(
                        result="",
                        model_used=model_spec,
                        execution_time=execution_time,
                        actual_cost=0.0,
                        token_usage={},
                        success=False,
                        error_message=error_msg
                    )
                
        except requests.exceptions.Timeout:
            execution_time = int((time.time() - start_time) * 1000)
            # 使用实际的超时时间
            actual_timeout = model_timeout if 'model_timeout' in locals() else self.timeout
            error_msg = f"请求超时 ({actual_timeout}s)"
            logger.error(error_msg)
            
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
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            error_msg = f"执行异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
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
        """健康检查，确认API可用性"""
        try:
            test_data = {
                "model": self.default_model,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=test_data,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("SiliconFlow API健康检查通过")
                return True
            else:
                logger.warning(f"SiliconFlow API健康检查失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"SiliconFlow API健康检查异常: {e}")
            return False
    
    def get_model_recommendations(self, task_spec: TaskSpec) -> List[str]:
        """
        根据任务规格推荐最适合的模型
        
        Args:
            task_spec: 任务规格
            
        Returns:
            List[str]: 推荐的模型名称列表，按优先级排序
        """
        recommendations = []
        
        # 根据任务复杂度推荐
        if task_spec.complexity == TaskComplexity.HIGH:
            if task_spec.requires_reasoning:
                recommendations.extend(['deepseek-r1', 'step-3', 'deepseek-v3'])
            elif task_spec.requires_chinese:
                recommendations.extend(['ernie-4.5', 'glm-4.5', 'qwen2.5-72b'])
            else:
                recommendations.extend(['deepseek-v3', 'qwen2.5-72b', 'glm-4.5'])
                
        elif task_spec.complexity == TaskComplexity.MEDIUM:
            if task_spec.requires_speed:
                recommendations.extend(['qwen3-turbo', 'yi-lightning', 'doubao-pro'])
            elif task_spec.requires_chinese:
                recommendations.extend(['glm-4.5', 'ernie-4.5', 'doubao-pro'])
            else:
                recommendations.extend(['deepseek-v3', 'glm-4.5', 'doubao-pro'])
                
        else:  # LOW complexity
            if task_spec.requires_speed:
                recommendations.extend(['yi-lightning', 'qwen3-turbo'])
            else:
                recommendations.extend(['qwen3-turbo', 'doubao-pro', 'glm-4.5'])
        
        # 如果需要长上下文，优先推荐kimi-k2
        if task_spec.estimated_tokens > 8000:
            recommendations.insert(0, 'kimi-k2')
        
        # 去重并保持顺序
        seen = set()
        unique_recommendations = []
        for model in recommendations:
            if model not in seen and model in self._supported_models:
                seen.add(model)
                unique_recommendations.append(model)
        
        return unique_recommendations
    
    def _get_optimal_temperature(self, task_spec: TaskSpec) -> float:
        """根据任务规格获取最优温度参数"""
        if task_spec.requires_reasoning:
            return 0.1  # 推理任务需要更确定性的输出
        elif task_spec.task_type in ['sentiment_analysis', 'creative_writing']:
            return 0.7  # 情感分析和创作任务可以更有创意
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
