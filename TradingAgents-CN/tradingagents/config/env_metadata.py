#!/usr/bin/env python3
"""
环境变量元数据定义
定义已知的环境变量的类型、分组和描述
"""

# 环境变量字段定义
ENV_FIELDS = [
    # API Keys - 敏感信息
    {
        "key": "GOOGLE_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "Google AI API 密钥",
        "desc": "用于调用 Google Gemini 等模型的密钥。建议保存在 .env，不要提交到版本库。",
        "placeholder": "AIza...",
        "example": "AIzaSyA***************"
    },
    {
        "key": "GEMINI_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "Gemini API 密钥（别名）",
        "desc": "等价于 Google AI 密钥的别名变量名，任选其一配置即可。",
        "placeholder": "AIza...",
        "example": "AIzaSyA***************"
    },
    {
        "key": "GOOGLE_AI_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "Google AI API 密钥（别名2）",
        "desc": "另一个常见的别名变量名，功能同上。",
        "placeholder": "AIza...",
        "example": "AIzaSyA***************"
    },
    {
        "key": "DEEPSEEK_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "DeepSeek API 密钥",
        "desc": "调用 DeepSeek 模型所需的密钥，支持 deepseek-chat/V3、R1 等。",
        "placeholder": "sk-...",
        "example": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
    },
    {
        "key": "SILICONFLOW_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "SiliconFlow API 密钥",
        "desc": "用于调用 SiliconFlow 聚合平台模型的密钥。",
        "placeholder": "sk-...",
        "example": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
    },
    {
        "key": "OPENAI_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "OpenAI API 密钥",
        "desc": "用于调用 OpenAI 平台模型的密钥。",
        "placeholder": "sk-...",
        "example": "sk-..."
    },
    {
        "key": "ANTHROPIC_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "Anthropic API 密钥",
        "desc": "用于调用 Claude 模型的密钥。",
        "placeholder": "sk-...",
        "example": "sk-ant-..."
    },
    {
        "key": "FINNHUB_API_KEY",
        "type": "secret",
        "group": "API Keys",
        "label": "Finnhub 金融数据密钥",
        "desc": "用于获取美股行情/财务等数据。",
        "placeholder": "xxxxx",
        "example": "c0a1b2c3d4e5..."
    },
    {
        "key": "TUSHARE_TOKEN",
        "type": "secret",
        "group": "API Keys",
        "label": "Tushare Token",
        "desc": "用于获取 A 股数据的 Token。免费额度有限，建议根据需要申请更高权限。",
        "placeholder": "xxxxxxxx",
        "example": "7c7a7e..."
    },
    
    # LLM / 路由
    {
        "key": "MULTI_MODEL_ENABLED",
        "type": "bool",
        "group": "LLM / 路由",
        "label": "启用多模型协作",
        "desc": "开启后启用多模型智能路由/协作能力，在 Web 页'股票分析'可切换'多模型'模式。"
    },
    {
        "key": "ROUTING_STRATEGY",
        "type": "select",
        "group": "LLM / 路由",
        "label": "模型路由策略",
        "desc": "选择模型分配策略：智能优选/成本优先/性能优先/均衡或轮询。",
        "options": ["intelligent", "balanced", "cost_first", "performance_first", "round_robin"],
        "options_cn": {
            "intelligent": "智能优选",
            "balanced": "均衡",
            "cost_first": "成本优先",
            "performance_first": "性能优先",
            "round_robin": "轮询"
        }
    },
    {
        "key": "DEFAULT_COLLABORATION_MODE",
        "type": "select",
        "group": "LLM / 路由",
        "label": "默认协作模式",
        "desc": "多智能体如何协作：串行/并行/辩论。",
        "options": ["sequential", "parallel", "debate"],
        "options_cn": {
            "sequential": "串行",
            "parallel": "并行",
            "debate": "辩论"
        }
    },
    
    # 预算
    {
        "key": "MAX_COST_PER_SESSION",
        "type": "float",
        "group": "预算",
        "label": "单次会话成本上限（USD）",
        "desc": "每次分析可消耗的最高费用（美元）。达到阈值将终止或降级。",
        "example": "1.0"
    },
    {
        "key": "ENABLE_PERFORMANCE_MONITORING",
        "type": "bool",
        "group": "预算",
        "label": "启用性能监控",
        "desc": "记录每次调用的耗时/成本/错误率，用于统计与告警。"
    },
    
    # SiliconFlow
    {
        "key": "SILICONFLOW_BASE_URL",
        "type": "string",
        "group": "SiliconFlow",
        "label": "SiliconFlow 接口地址",
        "desc": "SiliconFlow OpenAI 兼容接口地址。国内默认：https://api.siliconflow.cn/v1",
        "placeholder": "https://api.siliconflow.cn/v1",
        "example": "https://api.siliconflow.cn/v1"
    },
    {
        "key": "SILICONFLOW_DEFAULT_MODEL",
        "type": "string",
        "group": "SiliconFlow",
        "label": "SiliconFlow 默认模型",
        "desc": "例如 deepseek-ai/DeepSeek-V3、moonshotai/Kimi-K2-Instruct 等。",
        "placeholder": "deepseek-ai/DeepSeek-V3",
        "example": "deepseek-ai/DeepSeek-V3"
    },
    
    # Google AI
    {
        "key": "GOOGLE_AI_DEFAULT_MODEL",
        "type": "string",
        "group": "Google AI",
        "label": "Google AI 默认模型",
        "desc": "例如 gemini-2.5-pro 或 gemini-2.0-flash。",
        "placeholder": "gemini-2.5-pro",
        "example": "gemini-2.5-pro"
    },
    
    # 数据库
    {
        "key": "MONGODB_ENABLED",
        "type": "bool",
        "group": "数据库",
        "label": "启用 MongoDB 数据库",
        "desc": "开启后将使用 MongoDB 做数据持久化与统计存储（Docker 默认包含）。"
    },
    {
        "key": "REDIS_ENABLED",
        "type": "bool",
        "group": "数据库",
        "label": "启用 Redis 缓存",
        "desc": "开启后使用 Redis 提升缓存/会话性能（Docker 默认包含）。"
    },
    {
        "key": "MONGODB_HOST",
        "type": "string",
        "group": "数据库",
        "label": "MongoDB 主机",
        "desc": "本地部署一般为 localhost；Docker 为 mongodb。",
        "placeholder": "localhost",
        "example": "mongodb"
    },
    {
        "key": "MONGODB_PORT",
        "type": "int",
        "group": "数据库",
        "label": "MongoDB 端口",
        "desc": "默认 27017。",
        "placeholder": "27017",
        "example": "27017"
    },
    {
        "key": "REDIS_HOST",
        "type": "string",
        "group": "数据库",
        "label": "Redis 主机",
        "desc": "本地部署一般为 localhost；Docker 为 redis。",
        "placeholder": "localhost",
        "example": "redis"
    },
    {
        "key": "REDIS_PORT",
        "type": "int",
        "group": "数据库",
        "label": "Redis 端口",
        "desc": "默认 6379。",
        "placeholder": "6379",
        "example": "6379"
    },
    
    # 调度/邮件
    {
        "key": "SCHEDULER_ENABLED",
        "type": "bool",
        "group": "调度/邮件",
        "label": "启用定时调度",
        "desc": "用于每日/每周定时分析与报告推送。"
    },
    {
        "key": "SMTP_HOST",
        "type": "string",
        "group": "调度/邮件",
        "label": "SMTP 服务器",
        "desc": "邮件发送服务器地址。",
        "placeholder": "smtp.qq.com",
        "example": "smtp.qq.com"
    },
    {
        "key": "SMTP_PORT",
        "type": "int",
        "group": "调度/邮件",
        "label": "SMTP 端口",
        "desc": "SSL 常用 465，STARTTLS 常用 587。",
        "placeholder": "465",
        "example": "465"
    },
    {
        "key": "SMTP_USER",
        "type": "string",
        "group": "调度/邮件",
        "label": "SMTP 用户名",
        "desc": "发件邮箱账号。",
        "placeholder": "your_email@qq.com",
        "example": "your_email@qq.com"
    },
    {
        "key": "SMTP_PASS",
        "type": "secret",
        "group": "调度/邮件",
        "label": "SMTP 密码/授权码",
        "desc": "部分邮箱为客户端授权码而非登录密码，请到邮箱安全设置获取。",
        "placeholder": "********",
        "example": "授权码示例"
    },
    
    # 应用
    {
        "key": "DEBUG_MODE",
        "type": "bool",
        "group": "应用",
        "label": "调试模式",
        "desc": "输出更详细的日志并显示调试按钮。"
    },
    {
        "key": "STREAMLIT_PORT",
        "type": "int",
        "group": "应用",
        "label": "Web 端口 (Streamlit)",
        "desc": "默认 8501。Docker 部署如端口冲突可修改映射。",
        "placeholder": "8501",
        "example": "8501"
    },
    {
        "key": "MEMORY_ENABLED",
        "type": "bool",
        "group": "应用",
        "label": "启用内存功能 (ChromaDB)",
        "desc": "Windows 10 如遇兼容性问题可关闭。"
    },
    
    # Reddit
    {
        "key": "REDDIT_CLIENT_ID",
        "type": "secret",
        "group": "Reddit",
        "label": "Reddit 客户端 ID",
        "desc": "用于社交媒体情绪数据。"
    },
    {
        "key": "REDDIT_CLIENT_SECRET",
        "type": "secret",
        "group": "Reddit",
        "label": "Reddit 客户端密钥",
        "desc": "与客户端 ID 配套使用。"
    },
    {
        "key": "REDDIT_USER_AGENT",
        "type": "string",
        "group": "Reddit",
        "label": "Reddit User-Agent",
        "desc": "形如 TradingAgents-CN/1.0。",
        "placeholder": "TradingAgents-CN/1.0",
        "example": "TradingAgents-CN/1.0"
    }
]

# 分组顺序（在UI中的显示顺序）
GROUP_ORDER = [
    "API Keys",
    "LLM / 路由", 
    "预算",
    "SiliconFlow",
    "Google AI",
    "数据库",
    "调度/邮件",
    "应用",
    "Reddit"
]

# 获取按分组组织的字段
def get_fields_by_group():
    """获取按分组组织的字段字典"""
    groups = {}
    for field in ENV_FIELDS:
        group = field["group"]
        if group not in groups:
            groups[group] = []
        groups[group].append(field)
    return groups

# 获取字段元数据
def get_field_metadata(key: str):
    """根据键名获取字段元数据"""
    for field in ENV_FIELDS:
        if field["key"] == key:
            return field
    return None

# 是否为已知字段
def is_known_field(key: str) -> bool:
    """检查是否为已知的环境变量字段"""
    return any(field["key"] == key for field in ENV_FIELDS)


# 新增工具函数
def get_field_label(key: str) -> str:
    """获取字段的中文标签"""
    field = get_field_metadata(key)
    return (field or {}).get("label", key)


def get_field_help(key: str) -> str:
    """获取字段的悬浮帮助文本"""
    field = get_field_metadata(key) or {}
    desc = field.get("desc") or ""
    example = field.get("example")
    extra = f"\n示例：{example}" if example else ""
    return (desc or "").strip() + extra


def get_field_placeholder(key: str) -> str | None:
    """获取字段的占位符文本"""
    field = get_field_metadata(key) or {}
    return field.get("placeholder")


# 分组帮助文本
GROUP_HELP = {
    "API Keys": "管理各类 API 密钥，建议仅在 .env 配置，避免泄露。",
    "LLM / 路由": "控制是否启用多模型与模型分配策略。",
    "预算": "设置单次会话的成本上限与监控。",
    "SiliconFlow": "SiliconFlow 聚合平台相关默认配置。",
    "Google AI": "Google Gemini 默认模型配置。",
    "数据库": "MongoDB/Redis 服务的启用与连接。",
    "调度/邮件": "定时任务与邮件发送服务配置。",
    "应用": "应用运行时相关开关与端口。",
    "Reddit": "用于社交媒体数据抓取的凭证。",
}