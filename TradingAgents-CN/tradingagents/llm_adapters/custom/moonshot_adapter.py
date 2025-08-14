#!/usr/bin/env python3
"""
月之暗面Kimi (Moonshot) LLM适配器
支持moonshot-v1系列模型
"""

import os
import requests
import json
from typing import List, Dict, Optional
import asyncio
import aiohttp

from tradingagents.llm_adapters.plugin_loader import BaseLLMAdapter
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('llm_adapters.moonshot')


class MoonshotAdapter(BaseLLMAdapter):
    """月之暗面Kimi适配器
    
    支持的模型：
    - moonshot-v1-8k: 8K上下文窗口
    - moonshot-v1-32k: 32K上下文窗口  
    - moonshot-v1-128k: 128K上下文窗口
    """
    
    name = "moonshot"
    provider = "月之暗面"
    supported_models = ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]
    
    def __init__(self, 
                 model: str = "moonshot-v1-8k",
                 api_key: str = None,
                 base_url: str = None,
                 **kwargs):
        """初始化Moonshot适配器
        
        Args:
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
            **kwargs: 其他配置
        """
        super().__init__(model, api_key, **kwargs)
        
        # 获取API密钥
        self.api_key = api_key or os.getenv('MOONSHOT_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供MOONSHOT_API_KEY")
            
        # API配置
        self.base_url = base_url or "https://api.moonshot.cn/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 使用统计
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
    def invoke(self, messages: List[Dict], **kwargs) -> str:
        """同步调用Moonshot模型
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            模型响应
        """
        # 构建请求数据
        data = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "temperature": kwargs.get('temperature', 0.7),
            "max_tokens": kwargs.get('max_tokens', 4000),
            "top_p": kwargs.get('top_p', 1.0),
            "n": kwargs.get('n', 1),
            "presence_penalty": kwargs.get('presence_penalty', 0),
            "frequency_penalty": kwargs.get('frequency_penalty', 0),
            "stop": kwargs.get('stop', None)
        }
        
        # 移除None值
        data = {k: v for k, v in data.items() if v is not None}
        
        try:
            # 发送请求
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                timeout=kwargs.get('timeout', 60)
            )
            
            # 检查响应
            if response.status_code != 200:
                error_msg = f"Moonshot API错误: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            # 解析响应
            result = response.json()
            
            # 更新使用统计
            if 'usage' in result:
                self.total_input_tokens += result['usage'].get('prompt_tokens', 0)
                self.total_output_tokens += result['usage'].get('completion_tokens', 0)
                
            # 返回内容
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {e}")
            raise
        except Exception as e:
            logger.error(f"调用Moonshot失败: {e}")
            raise
            
    async def ainvoke(self, messages: List[Dict], **kwargs) -> str:
        """异步调用Moonshot模型
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Returns:
            模型响应
        """
        # 构建请求数据
        data = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "temperature": kwargs.get('temperature', 0.7),
            "max_tokens": kwargs.get('max_tokens', 4000),
            "top_p": kwargs.get('top_p', 1.0),
            "n": kwargs.get('n', 1),
            "presence_penalty": kwargs.get('presence_penalty', 0),
            "frequency_penalty": kwargs.get('frequency_penalty', 0),
            "stop": kwargs.get('stop', None)
        }
        
        # 移除None值
        data = {k: v for k, v in data.items() if v is not None}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=kwargs.get('timeout', 60))
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        error_msg = f"Moonshot API错误: {response.status} - {error_text}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                        
                    result = await response.json()
                    
                    # 更新使用统计
                    if 'usage' in result:
                        self.total_input_tokens += result['usage'].get('prompt_tokens', 0)
                        self.total_output_tokens += result['usage'].get('completion_tokens', 0)
                        
                    return result['choices'][0]['message']['content']
                    
            except Exception as e:
                logger.error(f"异步调用Moonshot失败: {e}")
                raise
                
    def stream(self, messages: List[Dict], **kwargs):
        """流式调用Moonshot模型
        
        Args:
            messages: 消息列表
            **kwargs: 额外参数
            
        Yields:
            响应片段
        """
        # 构建请求数据
        data = {
            "model": self.model,
            "messages": self._format_messages(messages),
            "temperature": kwargs.get('temperature', 0.7),
            "max_tokens": kwargs.get('max_tokens', 4000),
            "stream": True  # 启用流式响应
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data,
                stream=True,
                timeout=kwargs.get('timeout', 60)
            )
            
            if response.status_code != 200:
                error_msg = f"Moonshot API错误: {response.status_code}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
            # 处理流式响应
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # 移除 "data: " 前缀
                        
                        if data == '[DONE]':
                            break
                            
                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and chunk['choices']:
                                delta = chunk['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    yield delta['content']
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析流式响应: {data}")
                            
        except Exception as e:
            logger.error(f"流式调用Moonshot失败: {e}")
            raise
            
    def _format_messages(self, messages: List[Dict]) -> List[Dict]:
        """格式化消息列表
        
        Args:
            messages: 原始消息列表
            
        Returns:
            格式化后的消息列表
        """
        formatted = []
        
        for msg in messages:
            # 支持多种消息格式
            if isinstance(msg, dict):
                if 'role' in msg and 'content' in msg:
                    formatted.append({
                        'role': msg['role'],
                        'content': str(msg['content'])
                    })
                elif 'type' in msg:
                    # 转换LangChain消息格式
                    role_map = {
                        'human': 'user',
                        'ai': 'assistant',
                        'system': 'system'
                    }
                    formatted.append({
                        'role': role_map.get(msg['type'], 'user'),
                        'content': str(msg.get('content', ''))
                    })
            else:
                # 默认作为用户消息
                formatted.append({
                    'role': 'user',
                    'content': str(msg)
                })
                
        return formatted
        
    @classmethod
    def get_required_env_vars(cls) -> List[str]:
        """获取必需的环境变量"""
        return ['MOONSHOT_API_KEY']
        
    @classmethod
    def validate_config(cls, config: Dict) -> bool:
        """验证配置"""
        # 检查模型是否支持
        model = config.get('model')
        if model and model not in cls.supported_models:
            logger.warning(f"不支持的模型: {model}")
            return False
            
        # 检查API密钥
        api_key = config.get('api_key') or os.getenv('MOONSHOT_API_KEY')
        if not api_key:
            logger.warning("缺少MOONSHOT_API_KEY")
            return False
            
        return True
        
    def get_usage_stats(self) -> Dict:
        """获取使用统计"""
        # 估算成本（示例价格，实际请查询官方）
        input_cost = self.total_input_tokens * 0.012 / 1000  # ¥0.012/1K tokens
        output_cost = self.total_output_tokens * 0.012 / 1000
        
        return {
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': input_cost + output_cost,
            'currency': 'CNY'
        }


# 注册适配器
if __name__ != "__main__":
    from tradingagents.llm_adapters.plugin_loader import LLMAdapterRegistry
    LLMAdapterRegistry.register(MoonshotAdapter)
