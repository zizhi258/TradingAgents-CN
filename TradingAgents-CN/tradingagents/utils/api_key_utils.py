"""
API密钥工具模块
提供统一的API密钥获取和管理功能
"""

import os
from typing import Optional


def get_google_api_key() -> Optional[str]:
    """
    统一获取 Google/Gemini API 密钥
    按优先级顺序尝试不同的环境变量名称
    
    优先级顺序：
    1. GOOGLE_API_KEY (标准名称)
    2. GEMINI_API_KEY (Gemini专用)
    3. GOOGLE_AI_API_KEY (Google AI Studio)
    4. GOOGLE_GENAI_API_KEY (Google GenAI SDK)
    
    Returns:
        str: API密钥，如果未找到返回None
    """
    
    # 按优先级顺序尝试不同的环境变量
    key_names = [
        'GOOGLE_API_KEY',        # 标准名称，优先使用
        'GEMINI_API_KEY',        # Gemini专用
        'GOOGLE_AI_API_KEY',     # Google AI Studio
        'GOOGLE_GENAI_API_KEY'   # Google GenAI SDK
    ]
    
    for key_name in key_names:
        api_key = os.getenv(key_name)
        if api_key and api_key.strip():
            return api_key.strip()
    
    return None


def get_deepseek_api_key() -> Optional[str]:
    """
    获取 DeepSeek API 密钥
    
    Returns:
        str: API密钥，如果未找到返回None
    """
    return os.getenv('DEEPSEEK_API_KEY')


def get_dashscope_api_key() -> Optional[str]:
    """
    获取 DashScope (阿里百炼) API 密钥
    
    Returns:
        str: API密钥，如果未找到返回None
    """
    return os.getenv('DASHSCOPE_API_KEY')


def get_openrouter_api_key() -> Optional[str]:
    """
    获取 OpenRouter API 密钥
    优先使用 OPENROUTER_API_KEY，否则使用 OPENAI_API_KEY
    
    Returns:
        str: API密钥，如果未找到返回None
    """
    return os.getenv('OPENROUTER_API_KEY') or os.getenv('OPENAI_API_KEY')


def get_openai_api_key() -> Optional[str]:
    """
    获取 OpenAI API 密钥
    
    Returns:
        str: API密钥，如果未找到返回None
    """
    return os.getenv('OPENAI_API_KEY')


def get_anthropic_api_key() -> Optional[str]:
    """
    获取 Anthropic API 密钥
    
    Returns:
        str: API密钥，如果未找到返回None
    """
    return os.getenv('ANTHROPIC_API_KEY')


def validate_api_key(api_key: Optional[str], provider: str) -> str:
    """
    验证API密钥是否有效
    
    Args:
        api_key: API密钥
        provider: 提供商名称
        
    Returns:
        str: 有效的API密钥
        
    Raises:
        ValueError: 如果API密钥无效
    """
    if not api_key or not api_key.strip():
        raise ValueError(
            f"{provider} API密钥未找到或为空。"
            f"请检查相应的环境变量设置。"
        )
    
    return api_key.strip()


def mask_api_key(api_key: str, show_chars: int = 4) -> str:
    """
    掩码API密钥，用于安全日志记录
    
    Args:
        api_key: 原始API密钥
        show_chars: 显示的字符数（默认显示最后4个字符）
        
    Returns:
        str: 掩码后的API密钥
    """
    if not api_key or len(api_key) <= show_chars:
        return "*" * 8
    
    return "*" * (len(api_key) - show_chars) + api_key[-show_chars:]


# API密钥获取函数映射
API_KEY_GETTERS = {
    'google': get_google_api_key,
    'gemini': get_google_api_key,  # Gemini使用Google API Key
    'deepseek': get_deepseek_api_key,
    'dashscope': get_dashscope_api_key,
    'alibaba': get_dashscope_api_key,  # 阿里百炼别名
    'openrouter': get_openrouter_api_key,
    'openai': get_openai_api_key,
    'anthropic': get_anthropic_api_key
}


def get_api_key_for_provider(provider: str) -> Optional[str]:
    """
    根据提供商名称获取对应的API密钥
    
    Args:
        provider: 提供商名称
        
    Returns:
        str: API密钥，如果未找到返回None
    """
    provider_lower = provider.lower()
    
    if provider_lower in API_KEY_GETTERS:
        return API_KEY_GETTERS[provider_lower]()
    
    # 如果没有找到对应的获取器，尝试直接从环境变量获取
    env_var = f"{provider.upper()}_API_KEY"
    return os.getenv(env_var)