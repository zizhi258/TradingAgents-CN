"""
OpenAI兼容适配器基类
为所有支持OpenAI接口的LLM提供商提供统一的基础实现
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import CallbackManagerForLLMRun

# 导入统一日志系统
from tradingagents.utils.logging_manager import get_logger, get_logger_manager
logger = get_logger('llm_adapters')

# 导入token跟踪器
try:
    from tradingagents.config.config_manager import token_tracker
    TOKEN_TRACKING_ENABLED = True
    logger.info("✅ Token跟踪功能已启用")
except ImportError:
    TOKEN_TRACKING_ENABLED = False
    logger.warning("⚠️ Token跟踪功能未启用")


class OpenAICompatibleBase(ChatOpenAI):
    """
    OpenAI兼容适配器基类
    为所有支持OpenAI接口的LLM提供商提供统一实现
    """
    
    def __init__(
        self,
        provider_name: str,
        model: str,
        api_key_env_var: str,
        base_url: str,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        初始化OpenAI兼容适配器
        
        Args:
            provider_name: 提供商名称 (如: "deepseek", "dashscope")
            model: 模型名称
            api_key_env_var: API密钥环境变量名
            base_url: API基础URL
            api_key: API密钥，如果不提供则从环境变量获取
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数
        """
        
        self.provider_name = provider_name
        self.model_name = model
        
        # 获取API密钥
        if api_key is None:
            api_key = os.getenv(api_key_env_var)
            if not api_key:
                raise ValueError(
                    f"{provider_name} API密钥未找到。"
                    f"请设置{api_key_env_var}环境变量或传入api_key参数。"
                )
        
        # 设置OpenAI兼容参数
        openai_kwargs = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        # 根据LangChain版本使用不同的参数名
        try:
            # 新版本LangChain
            openai_kwargs.update({
                "api_key": api_key,
                "base_url": base_url
            })
        except:
            # 旧版本LangChain
            openai_kwargs.update({
                "openai_api_key": api_key,
                "openai_api_base": base_url
            })
        
        # 初始化父类
        super().__init__(**openai_kwargs)

        logger.info(f"✅ {provider_name} OpenAI兼容适配器初始化成功")
        logger.info(f"   模型: {model}")
        logger.info(f"   API Base: {base_url}")
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        生成聊天响应，并记录token使用量
        """
        
        # 记录开始时间
        start_time = time.time()
        
        # 调用父类生成方法
        result = super()._generate(messages, stop, run_manager, **kwargs)
        
        # 记录token使用量
        if TOKEN_TRACKING_ENABLED:
            try:
                self._track_token_usage(result, kwargs, start_time)
            except Exception as e:
                logger.error(f"⚠️ {self.provider_name} Token追踪失败: {e}", exc_info=True)
        
        return result
    
    def _track_token_usage(self, result: ChatResult, kwargs: Dict, start_time: float):
        """追踪token使用量"""
        
        # 提取token使用信息
        if hasattr(result, 'llm_output') and result.llm_output:
            token_usage = result.llm_output.get('token_usage', {})
            
            input_tokens = token_usage.get('prompt_tokens', 0)
            output_tokens = token_usage.get('completion_tokens', 0)
            
            if input_tokens > 0 or output_tokens > 0:
                # 生成会话ID
                session_id = kwargs.get('session_id', f"{self.provider_name}_{hash(str(kwargs))%10000}")
                analysis_type = kwargs.get('analysis_type', 'stock_analysis')
                
                # 记录使用量
                token_tracker.track_usage(
                    provider=self.provider_name,
                    model_name=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    session_id=session_id,
                    analysis_type=analysis_type
                )
                
                # 计算成本
                cost = token_tracker.calculate_cost(
                    provider=self.provider_name,
                    model_name=self.model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
                
                # 使用统一日志管理器记录Token使用
                logger_manager = get_logger_manager()
                logger_manager.log_token_usage(
                    logger, self.provider_name, self.model_name,
                    input_tokens, output_tokens, cost,
                    session_id
                )


class ChatDeepSeekOpenAI(OpenAICompatibleBase):
    """DeepSeek OpenAI兼容适配器"""
    
    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        super().__init__(
            provider_name="deepseek",
            model=model,
            api_key_env_var="DEEPSEEK_API_KEY",
            base_url="https://api.deepseek.com",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )


# DashScope (阿里百炼) 已废弃：移除相关适配器


# 支持的OpenAI兼容模型配置
OPENAI_COMPATIBLE_PROVIDERS = {
    "deepseek": {
        "adapter_class": ChatDeepSeekOpenAI,
        "base_url": "https://api.deepseek.com",
        "api_key_env": "DEEPSEEK_API_KEY",
        "models": {
            "deepseek-chat": {"context_length": 65536, "supports_function_calling": True},  # DeepSeek V3: 64K context
            "deepseek-reasoner": {"context_length": 65536, "supports_function_calling": True}  # DeepSeek R1: 64K context
        }
    },
    "siliconflow": {
        "adapter_class": ChatOpenAI,
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "SILICONFLOW_API_KEY",
        "models": {
            "deepseek-ai/DeepSeek-R1": {"context_length": 163840, "supports_function_calling": True},  # R1 推理模型
            "deepseek-ai/DeepSeek-V3": {"context_length": 131072, "supports_function_calling": True},  # V3 通用模型
            "zai-org/GLM-4.5": {"context_length": 131072, "supports_function_calling": True},  # GLM-4.5
            "Qwen/Qwen3-Coder-480B-A35B-Instruct": {"context_length": 262144, "supports_function_calling": True},  # Qwen3 Coder
            "moonshotai/Kimi-K2-Instruct": {"context_length": 131072, "supports_function_calling": True},  # Kimi K2
            "Qwen/Qwen3-235B-A22B-Thinking-2507": {"context_length": 262144, "supports_function_calling": True},  # Qwen3 Thinking
            "Qwen/Qwen3-235B-A22B-Instruct-2507": {"context_length": 262144, "supports_function_calling": True},  # Qwen3 Instruct
            "Qwen/Qwen3-Embedding-8B": {"context_length": 8192, "supports_function_calling": False},  # Embedding模型
            "Qwen/Qwen3-Reranker-8B": {"context_length": 8192, "supports_function_calling": False}  # Reranker模型
        }
    },
    # 注意：不再包含 dashscope
}


def create_openai_compatible_llm(
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    **kwargs
) -> OpenAICompatibleBase:
    """
    创建OpenAI兼容LLM实例的统一工厂函数
    
    Args:
        provider: 提供商名称 ("deepseek", "dashscope")
        model: 模型名称
        api_key: API密钥
        temperature: 温度参数
        max_tokens: 最大token数
        **kwargs: 其他参数
    
    Returns:
        OpenAI兼容的LLM实例
    """
    
    if provider not in OPENAI_COMPATIBLE_PROVIDERS:
        raise ValueError(f"不支持的提供商: {provider}。支持的提供商: {list(OPENAI_COMPATIBLE_PROVIDERS.keys())}")
    
    provider_config = OPENAI_COMPATIBLE_PROVIDERS[provider]
    adapter_class = provider_config["adapter_class"]
    
    return adapter_class(
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs
    )


def test_openai_compatible_adapters():
    """测试所有OpenAI兼容适配器"""

    logger.info("🧪 测试OpenAI兼容适配器")
    logger.info("=" * 50)

    for provider_name, config in OPENAI_COMPATIBLE_PROVIDERS.items():
        logger.info(f"\n🔧 测试 {provider_name}...")

        try:
            # 获取第一个可用模型
            first_model = list(config["models"].keys())[0]

            # 创建适配器
            llm = create_openai_compatible_llm(
                provider=provider_name,
                model=first_model,
                max_tokens=100
            )

            logger.info(f"✅ {provider_name} 适配器创建成功")

            # 测试工具绑定
            from langchain_core.tools import tool

            @tool
            def test_tool(text: str) -> str:
                """测试工具"""
                return f"工具返回: {text}"

            llm_with_tools = llm.bind_tools([test_tool])
            logger.info(f"✅ {provider_name} 工具绑定成功")

        except Exception as e:
            logger.error(f"❌ {provider_name} 测试失败: {e}", exc_info=True)


if __name__ == "__main__":
    test_openai_compatible_adapters()
