"""
自定义模型帮助组件
为用户提供模型选择的详细帮助信息
"""

import streamlit as st


def render_model_help(provider: str):
    """根据LLM提供商显示相应的模型帮助信息"""

    help_info = {
        "deepseek": {
            "title": "🔧 DeepSeek自定义模型",
            "description": "输入任何DeepSeek平台支持的模型名称",
            "examples": [
                "deepseek-chat - 通用对话模型（推荐）",
                "deepseek-reasoner - 推理增强模型（R1）",
            ],
            "docs_url": "https://platform.deepseek.com/api-docs/",
            "notes": [
                "💡 DeepSeek模型性价比极高，适合大规模使用",
                "⚠️ 确保API密钥有足够的配额",
                "🚀 推荐使用deepseek-chat进行个股分析",
            ],
        },
        "siliconflow": {
            "title": "🔧 SiliconFlow自定义模型",
            "description": "输入任何SiliconFlow平台支持的模型名称",
            "examples": [
                "deepseek-ai/DeepSeek-R1 - 推理专家，最强逻辑分析",
                "deepseek-ai/DeepSeek-V3 - 通用对话模型（推荐）",
                "zai-org/GLM-4.5 - 智谱清言，中文理解优秀",
                "Qwen/Qwen3-Coder-480B-A35B-Instruct - 超大代码专家",
                "moonshotai/Kimi-K2-Instruct - 月之暗面，长文本处理",
                "Qwen/Qwen3-235B-A22B-Thinking-2507 - 思维链推理增强",
                "Qwen/Qwen3-235B-A22B-Instruct-2507 - 超大指令模型",
                "Qwen/Qwen3-Embedding-8B - 文本嵌入向量模型",
                "Qwen/Qwen3-Reranker-8B - 检索重排序模型",
            ],
            "docs_url": "https://docs.siliconflow.cn/en/api-reference/models/get-model-list",
            "notes": [
                "💡 SiliconFlow聚合多家优秀大模型，一个API访问全部",
                "⚠️ 确保使用正确的模型编码格式（如: org/model-name）",
                "🚀 推荐使用deepseek-ai/DeepSeek-V3进行个股分析",
                "🧠 推理任务推荐使用deepseek-ai/DeepSeek-R1",
            ],
        },
        "google": {
            "title": "🔧 Google AI自定义模型",
            "description": "输入任何Google AI Studio支持的模型名称",
            "examples": [
                "gemini-2.5-pro - 最强大的Gemini模型，适合复杂分析",
                "gemini-2.5-flash - 快速版本",
                "gemini-pro-vision - 视觉理解模型",
            ],
            "docs_url": "https://ai.google.dev/gemini-api/docs/models/gemini",
            "notes": [
                "💡 Gemini模型在多语言任务上表现优秀",
                "🚀 推荐gemini-2.5-pro进行深度个股分析",
                "⚡ gemini-2.5-flash适合快速响应场景",
                "⚠️ 2.5-pro模型成本较高但分析更全面",
                "🌟 系统已针对不同模型自动优化参数",
            ],
        },
        "openrouter": {
            "title": "🔧 OpenRouter自定义模型",
            "description": "输入任何OpenRouter平台支持的模型ID",
            "examples": [
                "anthropic/claude-3.5-sonnet - Claude 3.5 Sonnet",
                "meta-llama/llama-3.2-90b-instruct - Llama 3.2大模型",
                "google/gemini-2.5-flash - Gemini 2.5 Flash",
                "openai/gpt-4o-2024-11-20 - GPT-4o最新版",
            ],
            "docs_url": "https://openrouter.ai/models",
            "notes": [
                "💡 OpenRouter聚合了50+种模型，选择丰富",
                "⚠️ 注意不同模型的定价差异较大",
                "🔗 建议先在OpenRouter网站查看模型详情",
            ],
        },
    }

    if provider not in help_info:
        return

    info = help_info[provider]

    with st.expander("📚 模型选择帮助", expanded=False):
        st.markdown(f"### {info['title']}")
        st.markdown(info["description"])

        st.markdown("**📋 常用模型示例:**")
        for example in info["examples"]:
            st.markdown(f"- `{example}`")

        st.markdown("**💡 使用提示:**")
        for note in info["notes"]:
            st.markdown(f"- {note}")

        st.markdown(f"**📖 完整模型列表:** [{info['docs_url']}]({info['docs_url']})")


def show_custom_model_tips():
    """显示自定义模型的通用使用技巧"""

    st.info(
        """
    ### 💡 自定义模型使用技巧
    
    **🎯 选择原则:**
    - **个股分析**: 选择逻辑推理能力强的模型
    - **快速响应**: 优先选择Turbo或Flash系列
    - **深度分析**: 选择参数量大的Pro或Max模型
    
    **⚡ 性能优化:**
    - 建议先用小模型测试，确认无误后再使用大模型
    - 对于简单任务，使用轻量级模型可以显著降低成本
    - 复杂分析任务推荐使用最新版本的模型
    
    **💰 成本控制:**
    - 查看各平台的定价页面了解费用结构
    - 使用免费配额进行初步测试
    - 对比不同模型的性价比
    """
    )


def validate_custom_model_name(model_name: str, provider: str) -> tuple[bool, str]:
    """验证自定义模型名称的格式"""

    if not model_name or not model_name.strip():
        return False, "⚠️ 模型名称不能为空"

    model_name = model_name.strip()

    # 基本格式验证
    if len(model_name) < 3:
        return False, "⚠️ 模型名称过短，请输入完整的模型名称"

    # 特殊字符检查
    invalid_chars = ["<", ">", '"', "'", "&"]
    for char in invalid_chars:
        if char in model_name:
            return False, f"⚠️ 模型名称包含无效字符: {char}"

    # 提供商特定验证
    if provider == "openrouter":
        if "/" not in model_name:
            return (
                False,
                "⚠️ OpenRouter模型名称格式错误，应为 'provider/model' 格式，如 'anthropic/claude-3.5-sonnet'",
            )

    elif provider == "deepseek":
        # DeepSeek模型通常以deepseek开头
        if not model_name.lower().startswith("deepseek"):
            return True, "💡 确保这是有效的DeepSeek模型名称"

    elif provider == "google":
        # Google模型通常以gemini开头
        if not model_name.lower().startswith("gemini"):
            return True, "💡 确保这是有效的Google AI模型名称"

    elif provider == "siliconflow":
        # SiliconFlow模型通常使用 org/model 格式
        if "/" not in model_name:
            return (
                False,
                "⚠️ SiliconFlow模型名称格式错误，应为 'org/model' 格式，如 'deepseek-ai/DeepSeek-V3'",
            )

        # 检查常见的SiliconFlow模型
        known_models = [
            "deepseek-ai/DeepSeek-R1",
            "deepseek-ai/DeepSeek-V3",
            "zai-org/GLM-4.5",
            "Qwen/Qwen3-Coder-480B-A35B-Instruct",
            "moonshotai/Kimi-K2-Instruct",
            "Qwen/Qwen3-235B-A22B-Thinking-2507",
            "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "Qwen/Qwen3-Embedding-8B",
            "Qwen/Qwen3-Reranker-8B",
        ]

        if model_name in known_models:
            return True, f"✅ 已验证的SiliconFlow模型: {model_name}"
        else:
            return True, f"💡 请确保 '{model_name}' 是有效的SiliconFlow模型"

    return True, "✅ 模型名称格式正确"
