"""
DeepSeek API 客户端
使用DeepSeek官方API端点
"""

import os
import time
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.base_multi_model_adapter import (
    BaseMultiModelAdapter, ModelSpec, TaskSpec, TaskResult, 
    ModelProvider
)

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('deepseek_client')


class DeepSeekClient(BaseMultiModelAdapter):
    """DeepSeek官方API客户端"""
    
    # DeepSeek支持的模型配置
    SUPPORTED_MODELS = {
        "deepseek-chat": {
            "type": "general",
            "cost_per_1k": 0.008,
            "max_tokens": 8192,
            "context_window": 128000,
            "description": "DeepSeek-V3-0324，MoE 671B参数，超越GPT-4.5性能"
        },
        "deepseek-reasoner": {
            "type": "reasoning",
            "cost_per_1k": 0.012,
            "max_tokens": 8192,
            "context_window": 160000,
            "description": "DeepSeek-R1-0528，强化学习推理模型，顶级性能"
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化DeepSeek客户端
        
        Args:
            config: 配置字典
        """
        super().__init__(ModelProvider.OPENAI, config)  # 使用OPENAI作为提供商类型，因为兼容
        
        # 配置参数
        self.base_url = config.get('base_url', 'https://api.deepseek.com')
        self.api_key = config.get('api_key') or os.getenv('DEEPSEEK_API_KEY')
        self.default_model = config.get('default_model', 'deepseek-chat')
        self.timeout = config.get('timeout', 60)
        
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")
            
        self.initialize_client()
        logger.info(f"✅ DeepSeek客户端初始化成功，支持{len(self.SUPPORTED_MODELS)}个模型")
    
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
                provider=self.provider,
                model_type=model_info['type'],
                cost_per_1k_tokens=model_info['cost_per_1k'],
                max_tokens=model_info['max_tokens'],
                supports_streaming=True,
                context_window=model_info['context_window']
            )
    
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
        if model_name not in self._supported_models:
            return TaskResult(
                result="",
                model_used=None,
                execution_time=0,
                actual_cost=0.0,
                token_usage={},
                success=False,
                error_message=f"不支持的模型: {model_name}"
            )
        
        model_spec = self._supported_models[model_name]
        start_time = time.time()
        
        try:
            # 构建请求数据
            streaming = bool(kwargs.get('stream', False))
            on_token = kwargs.get('on_token')
            request_data = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": kwargs.get('max_tokens', model_spec.max_tokens),
                "temperature": kwargs.get('temperature', 0.7),
                "top_p": kwargs.get('top_p', 0.8),
                "stream": streaming
            }
            
            # 根据模型动态调整超时时间
            model_timeout = self.timeout
            if model_name == 'deepseek-reasoner':
                # DeepSeek-R1 推理模型需要更长时间
                model_timeout = 120  # 2分钟
                logger.info(f"使用DeepSeek推理模型，超时时间调整为{model_timeout}秒")
            
            # 发送API请求
            logger.info(f"🤖 调用DeepSeek API: {model_name}")
            if streaming and callable(on_token):
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=request_data,
                    timeout=model_timeout,
                    stream=True
                )

                if response.status_code != 200:
                    execution_time = int((time.time() - start_time) * 1000)
                    error_msg = f"DeepSeek API请求失败: {response.status_code} - {response.text}"
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
                        try:
                            line = raw_line.decode('utf-8', errors='ignore').strip()
                        except Exception:
                            line = str(raw_line).strip()
                        if line.startswith("data: "):
                            line = line[6:].strip()
                        if line in ("[DONE]", "{\"event\":\"done\"}"):
                            break
                        try:
                            chunk = json.loads(line)
                        except Exception:
                            continue
                        # DeepSeek兼容：choices[0].delta.content
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

                logger.info(f"✅ DeepSeek API调用成功(流式): {model_name}, 耗时: {execution_time}ms")
                return TaskResult(
                    result=full_text,
                    model_used=model_spec,
                    execution_time=execution_time,
                    actual_cost=actual_cost,
                    token_usage=usage if isinstance(usage, dict) else {},
                    success=True
                )
            else:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=request_data,
                    timeout=model_timeout
                )

                execution_time = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    error_msg = f"DeepSeek API请求失败: {response.status_code} - {response.text}"
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
                if 'choices' not in response_data or not response_data['choices']:
                    error_msg = "DeepSeek API返回格式错误"
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

                # 提取结果
                result_text = response_data['choices'][0]['message']['content']

                # 计算token使用量和成本
                token_usage = response_data.get('usage', {})
                input_tokens = token_usage.get('prompt_tokens', 0)
                output_tokens = token_usage.get('completion_tokens', 0)
                total_tokens = token_usage.get('total_tokens', input_tokens + output_tokens)

                # 计算成本 (按千token计算)
                actual_cost = (total_tokens / 1000) * model_spec.cost_per_1k_tokens

                # 更新性能指标
                self.update_performance_metrics(
                    model_name, task_spec.task_type, execution_time, True
                )

                logger.info(f"✅ DeepSeek API调用成功: {model_name}, 耗时: {execution_time}ms, tokens: {total_tokens}")

                return TaskResult(
                    result=result_text,
                    model_used=model_spec,
                    execution_time=execution_time,
                    actual_cost=actual_cost,
                    token_usage={
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'total_tokens': total_tokens
                    },
                    success=True
                )
                
        except requests.exceptions.Timeout:
            execution_time = int((time.time() - start_time) * 1000)
            # 使用实际的超时时间
            actual_timeout = model_timeout if 'model_timeout' in locals() else self.timeout
            error_msg = f"DeepSeek API请求超时 ({actual_timeout}s)"
            logger.error(error_msg)
            
            # 更新性能指标
            self.update_performance_metrics(
                model_name, task_spec.task_type, execution_time, False
            )
            
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
            error_msg = f"DeepSeek API调用异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # 更新性能指标
            self.update_performance_metrics(
                model_name, task_spec.task_type, execution_time, False
            )
            
            return TaskResult(
                result="",
                model_used=model_spec,
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
            # 发送一个简单的测试请求
            test_data = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=test_data,
                timeout=10
            )
            
            success = response.status_code == 200
            if success:
                logger.info("✅ DeepSeek API健康检查通过")
            else:
                logger.warning(f"⚠️ DeepSeek API健康检查失败: {response.status_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ DeepSeek API健康检查异常: {e}")
            return False
