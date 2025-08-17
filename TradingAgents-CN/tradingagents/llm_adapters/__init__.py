# LLM Adapters for TradingAgents

# 导入OpenAI兼容适配器
# DashScope 已废弃，不再导出对应适配器
# DeepSeek 专用适配器
from .deepseek_adapter import ChatDeepSeek
from .openai_compatible_base import (
    OPENAI_COMPATIBLE_PROVIDERS,
    ChatDeepSeekOpenAI,
    OpenAICompatibleBase,
    create_openai_compatible_llm,
)

__all__ = [
    "OpenAICompatibleBase",
    "ChatDeepSeekOpenAI",
    "ChatDeepSeek",
    "create_openai_compatible_llm",
    "OPENAI_COMPATIBLE_PROVIDERS",
]
