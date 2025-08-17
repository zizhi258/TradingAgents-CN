#!/usr/bin/env python3
"""
Docker环境中的Gemini 2.5 Pro配置验证脚本
"""

import os


def check_google_genai_sdk():
    """检查Google GenAI SDK"""
    print("🔍 检查Google GenAI SDK...")
    try:
        from google import genai

        print("✅ Google GenAI SDK 已安装")
        try:
            version = getattr(genai, "__version__", "Unknown")
            print(f"   版本: {version}")
        except Exception:
            print("   版本: 无法获取")
        return True
    except ImportError as e:
        print(f"❌ Google GenAI SDK 未安装: {e}")
        return False


def check_api_keys():
    """检查API密钥配置"""
    print("\n🔑 检查API密钥配置...")
    keys = ["GEMINI_API_KEY", "GOOGLE_AI_API_KEY", "GOOGLE_API_KEY"]
    found_keys = []

    for key in keys:
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: {value[:10]}***")
            found_keys.append(key)
        else:
            print(f"❌ {key}: 未设置")

    return len(found_keys) > 0


def check_google_ai_client():
    """检查Google AI客户端是否能正常初始化"""
    print("\n🤖 检查Google AI客户端...")
    try:
        # 尝试导入客户端
        from tradingagents.api.google_ai_client import GoogleAIClient

        print("✅ Google AI客户端模块导入成功")

        # 尝试初始化
        config = {"enabled": True, "default_model": "gemini-2.5-pro", "timeout": 30}

        try:
            client = GoogleAIClient(config)
            print("✅ Google AI客户端初始化成功")

            # 获取支持的模型
            models = client.get_supported_models()
            print(f"✅ 支持的模型数量: {len(models)}")
            for model_name in models.keys():
                if "gemini-2.5" in model_name:
                    print(f"   🎯 {model_name}")

            return True
        except Exception as e:
            print(f"❌ Google AI客户端初始化失败: {e}")
            return False

    except ImportError as e:
        print(f"❌ 无法导入Google AI客户端: {e}")
        return False


def check_multi_model_manager():
    """检查多模型管理器中是否包含Gemini模型"""
    print("\n🎛️  检查多模型管理器...")
    try:
        # 模拟多模型配置
        config = {
            "google_ai": {"enabled": True, "default_model": "gemini-2.5-pro"},
            "siliconflow": {"enabled": True},
            "deepseek": {"enabled": True},
        }

        from tradingagents.core.multi_model_manager import MultiModelManager

        manager = MultiModelManager(config)

        # 获取所有可用模型
        available_models = manager._get_all_available_models()
        print("✅ 多模型管理器初始化成功")
        print(f"   总可用模型数: {len(available_models)}")

        gemini_models = [
            name for name in available_models.keys() if "gemini" in name.lower()
        ]
        if gemini_models:
            print(f"✅ 发现Gemini模型: {len(gemini_models)}个")
            for model in gemini_models:
                print(f"   🎯 {model}")
            return True
        else:
            print("❌ 未发现Gemini模型")
            print("   可用模型列表:")
            for model in list(available_models.keys())[:5]:
                print(f"   - {model}")
            return False

    except Exception as e:
        print(f"❌ 多模型管理器检查失败: {e}")
        return False


def main():
    """主检查函数"""
    print("🐳 Docker环境 - Gemini 2.5 Pro 配置检查")
    print("=" * 50)

    # 检查运行环境
    if os.getenv("DOCKER_CONTAINER"):
        print("✅ 运行在Docker容器中")
    else:
        print("⚠️  未检测到Docker环境")

    checks = [
        ("Google GenAI SDK", check_google_genai_sdk),
        ("API密钥配置", check_api_keys),
        ("Google AI客户端", check_google_ai_client),
        ("多模型管理器", check_multi_model_manager),
    ]

    results = {}
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            print(f"❌ {check_name} 检查时发生错误: {e}")
            results[check_name] = False

    print("\n" + "=" * 50)
    print("📋 检查结果汇总:")

    all_passed = True
    for check_name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 所有检查通过！Gemini 2.5 Pro 应该可以正常使用")
    else:
        print("\n⚠️  存在配置问题，Gemini 2.5 Pro 可能无法使用")
        print("\n🔧 解决建议:")
        print("1. 重新构建Docker镜像: docker-compose build --no-cache")
        print("2. 检查.env文件中的GEMINI_API_KEY配置")
        print("3. 重启Docker服务: docker-compose down && docker-compose up -d")


if __name__ == "__main__":
    main()
