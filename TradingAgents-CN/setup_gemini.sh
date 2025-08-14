#!/bin/bash
# Gemini 2.5 Pro 设置脚本
# 用于配置 Google GenAI SDK 和 API 密钥

echo "🔧 Gemini 2.5 Pro 配置向导"
echo "================================"

# 检查当前状态
echo "📋 检查当前状态..."

# 检查 Google GenAI SDK
python3 -c "
try:
    from google import genai
    print('✅ Google GenAI SDK 已安装')
except ImportError:
    print('❌ Google GenAI SDK 未安装')
    print('   请运行: pip install google-genai')
"

# 检查环境变量
echo ""
echo "🔑 检查 API 密钥配置..."
if [ -n "$GEMINI_API_KEY" ]; then
    echo "✅ GEMINI_API_KEY 已配置"
elif [ -n "$GOOGLE_AI_API_KEY" ]; then
    echo "✅ GOOGLE_AI_API_KEY 已配置"  
elif [ -n "$GOOGLE_API_KEY" ]; then
    echo "✅ GOOGLE_API_KEY 已配置"
else
    echo "❌ 未配置 Google AI API 密钥"
    echo "   需要设置以下环境变量之一："
    echo "   - GEMINI_API_KEY"
    echo "   - GOOGLE_AI_API_KEY"
    echo "   - GOOGLE_API_KEY"
    echo ""
    echo "📝 配置方法："
    echo "   1. 获取API密钥: https://makersuite.google.com/app/apikey"
    echo "   2. 添加到 .env 文件:"
    echo "      GEMINI_API_KEY=your_api_key_here"
    echo "   3. 或临时设置:"
    echo "      export GEMINI_API_KEY=your_api_key_here"
fi

echo ""
echo "🔧 修复建议："
echo "1. 安装依赖: pip install google-genai"
echo "2. 配置API密钥到 .env 文件"
echo "3. 重启应用以使配置生效"

echo ""
echo "📱 获取免费API密钥:"
echo "   https://makersuite.google.com/app/apikey"
echo "   (Google AI Studio 提供免费配额)"