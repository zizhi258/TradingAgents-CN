#!/usr/bin/env python3
"""
Google GenAI SDK 测试脚本
验证新版google-genai SDK是否能正确连接和工作
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_new_google_genai_sdk():
    """测试新版Google GenAI SDK"""
    print("=== 测试新版Google GenAI SDK ===")

    try:
        # 测试导入新版SDK
        from google import genai
        from google.genai import types

        print("✅ 新版SDK导入成功")
    except ImportError as e:
        print(f"❌ 新版SDK导入失败: {e}")
        print("请运行: pip install google-genai")
        return False

    # 检查环境变量
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_AI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:
        print("❌ API密钥未配置，请设置环境变量: GEMINI_API_KEY")
        return False

    print(f"✅ API密钥已配置: {api_key[:10]}...")

    # 初始化客户端
    try:
        if not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = api_key

        client = genai.Client()
        print("✅ 客户端初始化成功")
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        return False

    # 测试API调用
    try:
        print("🔄 测试API调用...")

        response = client.models.generate_content(
            model="gemini-1.5-flash",  # 使用轻量级模型测试
            contents="请用中文回答：你好，请回复'测试成功'",
            config=types.GenerateContentConfig(max_output_tokens=50, temperature=0.1),
        )

        if response.text:
            print("✅ API调用成功")
            print(f"📄 响应内容: {response.text.strip()}")

            # 检查使用量信息
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = response.usage_metadata
                print(f"📊 Token使用量: {usage}")

            return True
        else:
            print("❌ API调用失败: 无响应内容")
            return False

    except Exception as e:
        print(f"❌ API调用异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_flagship_models():
    """测试旗舰模型可用性"""
    print("\n=== 测试旗舰模型可用性 ===")

    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            print("❌ API密钥未配置")
            return False

        if not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = api_key

        client = genai.Client()

        # 测试旗舰模型
        flagship_models = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"]

        for model in flagship_models:
            try:
                print(f"🔄 测试模型: {model}")

                response = client.models.generate_content(
                    model=model,
                    contents="Hello, please respond with 'OK'",
                    config=types.GenerateContentConfig(
                        max_output_tokens=10, temperature=0.1
                    ),
                )

                if response.text and "OK" in response.text:
                    print(f"✅ {model}: 可用")
                else:
                    print(f"⚠️ {model}: 响应异常 - {response.text}")

            except Exception as e:
                print(f"❌ {model}: 不可用 - {e}")

        return True

    except Exception as e:
        print(f"❌ 旗舰模型测试失败: {e}")
        return False


def test_thinking_mode():
    """测试Gemini 2.5的思考模式"""
    print("\n=== 测试Gemini 2.5思考模式 ===")

    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            print("❌ API密钥未配置")
            return False

        if not os.getenv("GEMINI_API_KEY"):
            os.environ["GEMINI_API_KEY"] = api_key

        client = genai.Client()

        # 测试带思考模式的调用
        print("🔄 测试思考模式（启用）...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="简单解释一下股票投资的基本原理",
            config=types.GenerateContentConfig(
                max_output_tokens=200,
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=1000),
            ),
        )

        if response.text:
            print("✅ 思考模式调用成功")
            print(f"📄 响应长度: {len(response.text)} 字符")

        # 测试禁用思考模式
        print("🔄 测试思考模式（禁用）...")
        response2 = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="简单解释一下股票投资的基本原理",
            config=types.GenerateContentConfig(
                max_output_tokens=200,
                temperature=0.3,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )

        if response2.text:
            print("✅ 禁用思考模式调用成功")
            print(f"📄 响应长度: {len(response2.text)} 字符")

        return True

    except Exception as e:
        print(f"❌ 思考模式测试失败: {e}")
        return False


def main():
    """主函数"""
    print("🚀 Google GenAI SDK 兼容性测试\n")

    # 加载环境变量
    try:
        from dotenv import load_dotenv

        load_dotenv()
        print("✅ 环境变量加载成功")
    except ImportError:
        print("⚠️ python-dotenv未安装，跳过.env文件加载")
    except Exception as e:
        print(f"⚠️ 环境变量加载失败: {e}")

    results = []

    # 测试新版SDK
    results.append(("新版SDK基础测试", test_new_google_genai_sdk()))

    # 测试旗舰模型
    results.append(("旗舰模型可用性测试", test_flagship_models()))

    # 测试思考模式
    results.append(("思考模式测试", test_thinking_mode()))

    # 输出结果摘要
    print("\n" + "=" * 50)
    print("🎯 测试结果摘要:")
    print("=" * 50)

    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 所有测试通过！新版Google GenAI SDK可以正常使用")
    else:
        print("⚠️ 部分测试失败，请检查配置和网络连接")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
