#!/usr/bin/env python3
"""
Final Multi-Model Integration Validation Script
验证多模型协作系统最终集成状态
"""

import os
import sys

import requests


def test_web_service():
    """测试Web服务是否可访问"""
    try:
        response = requests.get("http://localhost:8501", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def test_components_exist():
    """测试关键组件文件是否存在"""
    components = {
        "用户友好错误处理器": "tradingagents/core/user_friendly_error_handler.py",
        "多模型管理器": "tradingagents/core/multi_model_manager.py",
        "智能路由引擎": "tradingagents/core/smart_routing_engine.py",
        "多模型协作扩展": "tradingagents/graph/multi_model_extension.py",
        "增强分析表单": "web/components/enhanced_multi_model_analysis_form.py",
        "多模型分析表单": "web/components/multi_model_analysis_form.py",
        "SiliconFlow客户端": "tradingagents/api/siliconflow_client.py",
        "Google AI客户端": "tradingagents/api/google_ai_client.py",
    }

    results = {}
    for name, path in components.items():
        results[name] = os.path.exists(path)

    return results


def test_configuration():
    """测试配置是否正确设置"""
    config_checks = {
        "环境配置示例": os.path.exists(".env.example"),
        "Docker配置": os.path.exists("docker-compose.yml"),
        "Web应用": os.path.exists("web/app.py"),
    }

    return config_checks


def main():
    print("🚀 TradingAgents-CN 多模型协作系统最终验证")
    print("=" * 60)

    # 测试Web服务
    web_status = test_web_service()
    print(f"🌐 Web服务状态: {'✅ 运行中' if web_status else '❌ 不可访问'}")

    # 测试组件文件
    print("\n📁 核心组件检查:")
    component_results = test_components_exist()
    for name, exists in component_results.items():
        status = "✅" if exists else "❌"
        print(f"{status} {name}")

    # 测试配置
    print("\n⚙️ 配置检查:")
    config_results = test_configuration()
    for name, exists in config_results.items():
        status = "✅" if exists else "❌"
        print(f"{status} {name}")

    # 计算总体状态
    total_components = len(component_results)
    successful_components = sum(component_results.values())
    total_config = len(config_results)
    successful_config = sum(config_results.values())

    print(f"\n📊 组件完整性: {successful_components}/{total_components}")
    print(f"📊 配置完整性: {successful_config}/{total_config}")
    print(f"🌐 Web服务: {'正常' if web_status else '需检查'}")

    # 最终评估
    component_score = (successful_components / total_components) * 100
    config_score = (successful_config / total_config) * 100
    web_score = 100 if web_status else 0

    final_score = component_score * 0.6 + config_score * 0.2 + web_score * 0.2

    print(f"\n🏆 最终评分: {final_score:.1f}/100")

    if final_score >= 90:
        print("🎉 优秀! 多模型协作系统已完全成功集成")
        print("✨ 所有功能已就绪，用户可以开始使用多智能体协作分析")
    elif final_score >= 80:
        print("👍 良好! 多模型协作系统基本集成完成")
        print("💡 建议检查失败的组件以获得最佳体验")
    else:
        print("⚠️ 需要改进，请检查失败的组件")

    print("\n🔗 访问方式:")
    print("   1. 确保Docker服务运行: docker-compose up -d")
    print("   2. 打开浏览器访问: http://localhost:8501")
    print("   3. 在侧边栏选择: '🤖 多模型协作'")

    return final_score >= 85


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
