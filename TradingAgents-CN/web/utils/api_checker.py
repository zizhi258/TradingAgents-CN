"""
API密钥检查工具
"""

import os

def _get_google_family_key():
    """从一组等价变量中获取Google/Gemini密钥与来源名"""
    sources = [
        ("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY")),
        ("GOOGLE_AI_API_KEY", os.getenv("GOOGLE_AI_API_KEY")),
        ("GOOGLE_GENAI_API_KEY", os.getenv("GOOGLE_GENAI_API_KEY")),
        ("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY")),
    ]
    for name, val in sources:
        if val:
            return name, val
    return None, None


def check_api_keys():
    """检查所有必要的API密钥是否已配置"""

    # 检查各个API密钥
    dashscope_key = None  # DashScope 已移除
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    siliconflow_key = os.getenv("SILICONFLOW_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_api_compat_key = os.getenv("GEMINI_API_COMPAT_API_KEY") or os.getenv("OPENAI_API_KEY")
    tushare_token = os.getenv("TUSHARE_TOKEN")
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    google_key_name, google_key = _get_google_family_key()
    
    # 构建详细状态
    details = {
        # DashScope 已移除
        "FINNHUB_API_KEY": {
            "configured": bool(finnhub_key),
            "display": f"{finnhub_key[:12]}..." if finnhub_key else "未配置",
            "required": True,
            "description": "金融数据API密钥"
        },
        "DEEPSEEK_API_KEY": {
            "configured": bool(deepseek_key),
            "display": f"{deepseek_key[:12]}..." if deepseek_key else "未配置",
            "required": False,
            "description": "DeepSeek 官方API密钥"
        },
        "SILICONFLOW_API_KEY": {
            "configured": bool(siliconflow_key),
            "display": f"{siliconflow_key[:12]}..." if siliconflow_key else "未配置",
            "required": False,
            "description": "SiliconFlow API密钥"
        },
        "OPENROUTER_API_KEY": {
            "configured": bool(openrouter_key),
            "display": f"{openrouter_key[:12]}..." if openrouter_key else "未配置",
            "required": False,
            "description": "OpenRouter 聚合平台 API 密钥"
        },
        "GEMINI_API_COMPAT_API_KEY": {
            "configured": bool(gemini_api_compat_key),
            "display": f"{gemini_api_compat_key[:12]}..." if gemini_api_compat_key else "未配置",
            "required": False,
            "description": "Gemini-API 兼容(OpenAI协议反代) 密钥（或使用 OPENAI_API_KEY）"
        },
        "TUSHARE_TOKEN": {
            "configured": bool(tushare_token),
            "display": f"{tushare_token[:12]}..." if tushare_token else "未配置",
            "required": False,
            "description": "Tushare 金融数据令牌"
        },
        "OPENAI_API_KEY": {
            "configured": bool(openai_key),
            "display": f"{openai_key[:12]}..." if openai_key else "未配置",
            "required": False,
            "description": "OpenAI API密钥"
        },
        "ANTHROPIC_API_KEY": {
            "configured": bool(anthropic_key),
            "display": f"{anthropic_key[:12]}..." if anthropic_key else "未配置",
            "required": False,
            "description": "Anthropic API密钥"
        },
        # 统一显示Google/Gemini系列密钥，兼容多种变量名
        "GOOGLE_FAMILY_API_KEY": {
            "configured": bool(google_key),
            "display": (f"{google_key[:12]}... (via {google_key_name})" if google_key else "未配置"),
            "required": False,
            "description": "Google AI / Gemini API密钥 (支持 GEMINI/GOOGLE_AI/GOOGLE_GENAI/GOOGLE_API_KEY)"
        }
    }
    
    # 检查必需的API密钥
    required_keys = [key for key, info in details.items() if info["required"]]
    missing_required = [key for key in required_keys if not details[key]["configured"]]
    
    return {
        "all_configured": len(missing_required) == 0,
        "required_configured": len(missing_required) == 0,
        "missing_required": missing_required,
        "details": details,
        "summary": {
            "total": len(details),
            "configured": sum(1 for info in details.values() if info["configured"]),
            "required": len(required_keys),
            "required_configured": len(required_keys) - len(missing_required)
        }
    }

def get_api_key_status_message():
    """获取API密钥状态消息"""
    
    status = check_api_keys()
    
    if status["all_configured"]:
        return "✅ 所有必需的API密钥已配置完成"
    elif status["required_configured"]:
        return "✅ 必需的API密钥已配置，可选API密钥未配置"
    else:
        missing = ", ".join(status["missing_required"])
        return f"❌ 缺少必需的API密钥: {missing}"

def validate_api_key_format(key_type, api_key):
    """验证API密钥格式"""
    
    if not api_key:
        return False, "API密钥不能为空"
    
    # 基本长度检查
    if len(api_key) < 10:
        return False, "API密钥长度过短"
    
    # 特定格式检查
    if key_type == "DASHSCOPE_API_KEY":
        if not api_key.startswith("sk-"):
            return False, "阿里百炼API密钥应以'sk-'开头"
    elif key_type == "OPENAI_API_KEY":
        if not api_key.startswith("sk-"):
            return False, "OpenAI API密钥应以'sk-'开头"
    
    return True, "API密钥格式正确"

def test_api_connection(key_type, api_key):
    """测试API连接（简单验证）"""
    
    # 这里可以添加实际的API连接测试
    # 为了简化，现在只做格式验证
    
    is_valid, message = validate_api_key_format(key_type, api_key)
    
    if not is_valid:
        return False, message
    
    # 可以在这里添加实际的API调用测试
    # 例如：调用一个简单的API端点验证密钥有效性
    
    return True, "API密钥验证通过"
