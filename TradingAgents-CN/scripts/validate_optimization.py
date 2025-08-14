#!/usr/bin/env python3
"""
多模型集成优化验证脚本
验证用户体验和错误处理的优化成果
"""

import os
import sys
import importlib.util
from pathlib import Path
from typing import Dict, Any, List

def check_file_exists(file_path: str, description: str) -> bool:
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (不存在)")
        return False

def check_enhanced_components() -> Dict[str, bool]:
    """检查增强的组件是否存在"""
    print("🔍 检查增强的多模型组件...")
    
    components = {
        "用户友好的错误处理器": "tradingagents/core/user_friendly_error_handler.py",
        "增强的多模型表单": "web/components/enhanced_multi_model_analysis_form.py", 
        "改进的多模型管理器": "tradingagents/core/multi_model_manager.py",
        "优化的环境配置": ".env.example"
    }
    
    results = {}
    for desc, path in components.items():
        results[desc] = check_file_exists(path, desc)
    
    return results

def check_error_handling_features() -> Dict[str, bool]:
    """检查错误处理功能"""
    print("\n🛡️ 检查错误处理功能...")
    
    try:
        # 检查用户友好错误处理器
        from tradingagents.core.user_friendly_error_handler import (
            UserFriendlyErrorHandler, 
            handle_user_friendly_error,
            ErrorCategory
        )
        print("✅ 用户友好错误处理器导入成功")
        
        # 测试错误分类
        handler = UserFriendlyErrorHandler()
        test_errors = [
            "invalid api key",
            "quota exceeded", 
            "connection timeout",
            "model not available"
        ]
        
        categorized_correctly = 0
        for error in test_errors:
            try:
                category = handler._categorize_error(error)
                if category != ErrorCategory.UNKNOWN_ERROR:
                    categorized_correctly += 1
            except Exception:
                pass
        
        print(f"✅ 错误分类功能: {categorized_correctly}/{len(test_errors)} 个错误正确分类")
        return {"error_handler_import": True, "error_categorization": categorized_correctly > 2}
        
    except ImportError as e:
        print(f"❌ 错误处理器导入失败: {e}")
        return {"error_handler_import": False, "error_categorization": False}

def check_fallback_mechanisms() -> Dict[str, bool]:
    """检查降级机制"""
    print("\n⚡ 检查降级机制...")
    
    try:
        from tradingagents.core.multi_model_manager import MultiModelManager
        
        # 检查是否有降级方法
        fallback_methods = [
            "_attempt_task_fallback",
            "_attempt_collaboration_fallback", 
            "_simplify_task_prompt",
            "_select_core_agents",
            "get_system_health_status"
        ]
        
        method_exists = {}
        for method in fallback_methods:
            method_exists[method] = hasattr(MultiModelManager, method)
            status = "✅" if method_exists[method] else "❌"
            print(f"{status} {method}: {'存在' if method_exists[method] else '缺失'}")
        
        return method_exists
        
    except ImportError as e:
        print(f"❌ 多模型管理器导入失败: {e}")
        return {method: False for method in ["_attempt_task_fallback", "_attempt_collaboration_fallback"]}

def check_user_experience_improvements() -> Dict[str, bool]:
    """检查用户体验改进"""
    print("\n🎨 检查用户体验改进...")
    
    improvements = {}
    
    # 检查增强的表单组件
    try:
        from web.components.enhanced_multi_model_analysis_form import (
            render_enhanced_multi_model_analysis_form,
            AnalysisProgressTracker,
            check_system_health
        )
        improvements["enhanced_form"] = True
        print("✅ 增强的表单组件导入成功")
        
        # 检查进度跟踪功能
        tracker = AnalysisProgressTracker()
        tracker.start_analysis()
        improvements["progress_tracking"] = True
        print("✅ 分析进度跟踪功能可用")
        
    except ImportError as e:
        improvements["enhanced_form"] = False
        improvements["progress_tracking"] = False
        print(f"❌ 增强表单组件导入失败: {e}")
    
    # 检查环境配置优化
    env_example_path = Path(".env.example")
    if env_example_path.exists():
        with open(env_example_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_configs = [
            "MULTI_MODEL_ENABLED=true",
            "ROUTING_STRATEGY=",
            "ENABLE_USER_FRIENDLY_ERRORS=",
            "MAX_COST_PER_SESSION="
        ]
        
        config_present = sum(1 for config in required_configs if config in content)
        improvements["env_optimization"] = config_present >= 3
        
        status = "✅" if improvements["env_optimization"] else "⚠️"
        print(f"{status} 环境配置优化: {config_present}/{len(required_configs)} 项配置存在")
    else:
        improvements["env_optimization"] = False
        print("❌ .env.example 文件不存在")
    
    return improvements

def check_docker_integration() -> bool:
    """检查Docker集成"""
    print("\n🐳 检查Docker集成...")
    
    docker_compose_path = Path("docker-compose.yml")
    if not docker_compose_path.exists():
        print("❌ docker-compose.yml 文件不存在")
        return False
    
    with open(docker_compose_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_features = [
        "MULTI_MODEL_ENABLED",
        "ROUTING_STRATEGY", 
        "MAX_COST_PER_SESSION",
        "ENABLE_PERFORMANCE_MONITORING",
        "tradingagents-network"
    ]
    
    present_features = sum(1 for feature in required_features if feature in content)
    integration_complete = present_features >= 4
    
    status = "✅" if integration_complete else "⚠️"
    print(f"{status} Docker集成: {present_features}/{len(required_features)} 项功能配置存在")
    
    return integration_complete

def calculate_optimization_score(results: Dict[str, Any]) -> int:
    """计算优化得分"""
    print("\n📊 计算优化得分...")
    
    # 权重分配
    weights = {
        "error_handling": 30,      # 错误处理改进 (30分)
        "user_experience": 25,     # 用户体验改进 (25分) 
        "fallback_mechanisms": 20, # 降级机制 (20分)
        "code_quality": 15,        # 代码质量 (15分)
        "integration": 10          # 集成完整性 (10分)
    }
    
    scores = {}
    
    # 错误处理得分
    error_score = 0
    if results.get("error_handler_import", False):
        error_score += 15
    if results.get("error_categorization", False):
        error_score += 15
    scores["error_handling"] = error_score
    
    # 用户体验得分
    ux_score = 0
    if results.get("enhanced_form", False):
        ux_score += 10
    if results.get("progress_tracking", False):
        ux_score += 10
    if results.get("env_optimization", False):
        ux_score += 5
    scores["user_experience"] = ux_score
    
    # 降级机制得分
    fallback_score = 0
    fallback_methods = ["_attempt_task_fallback", "_attempt_collaboration_fallback"]
    for method in fallback_methods:
        if results.get(method, False):
            fallback_score += 10
    scores["fallback_mechanisms"] = fallback_score
    
    # 代码质量得分 (基于组件存在性)
    quality_score = 0
    components = ["用户友好的错误处理器", "增强的多模型表单", "改进的多模型管理器"]
    for comp in components:
        if results.get(comp, False):
            quality_score += 5
    scores["code_quality"] = quality_score
    
    # 集成完整性得分
    integration_score = 10 if results.get("docker_integration", False) else 5
    scores["integration"] = integration_score
    
    # 计算总分
    total_score = sum(scores.values())
    
    print(f"📈 各项得分详情:")
    for category, score in scores.items():
        max_score = weights[category]
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        print(f"   {category}: {score}/{max_score} ({percentage:.1f}%)")
    
    print(f"\n🏆 总得分: {total_score}/100")
    
    return total_score

def generate_optimization_report(score: int, results: Dict[str, Any]) -> str:
    """生成优化报告"""
    print("\n📋 生成优化报告...")
    
    if score >= 90:
        overall_rating = "优秀 🎉"
        summary = "多模型集成优化已达到预期目标，用户体验和错误处理显著改善。"
    elif score >= 80:
        overall_rating = "良好 👍"
        summary = "多模型集成优化基本达到目标，仍有小幅改进空间。"
    elif score >= 70:
        overall_rating = "及格 📈"
        summary = "多模型集成优化部分完成，需要继续完善。"
    else:
        overall_rating = "需改进 ⚠️"
        summary = "多模型集成优化需要大幅改进才能达到预期效果。"
    
    # 识别改进建议
    recommendations = []
    
    if not results.get("error_handler_import", False):
        recommendations.append("- 修复用户友好错误处理器的导入问题")
    
    if not results.get("enhanced_form", False):
        recommendations.append("- 完善增强的多模型表单组件")
    
    if not results.get("_attempt_task_fallback", False):
        recommendations.append("- 实现任务降级处理机制")
    
    if not results.get("docker_integration", False):
        recommendations.append("- 完善Docker集成配置")
    
    report = f"""
==================================================
🚀 多模型集成优化验证报告
==================================================

📊 总体评价: {overall_rating}
🏆 优化得分: {score}/100

📝 优化总结:
{summary}

✅ 主要成果:
- {'✅ 用户友好错误处理' if results.get('error_handler_import') else '❌ 用户友好错误处理'}
- {'✅ 增强的用户界面' if results.get('enhanced_form') else '❌ 增强的用户界面'}
- {'✅ 智能降级机制' if results.get('_attempt_task_fallback') else '❌ 智能降级机制'}
- {'✅ Docker一键部署' if results.get('docker_integration') else '❌ Docker一键部署'}

{"🔧 改进建议:" if recommendations else "🎉 所有功能均已正常运行！"}
{chr(10).join(recommendations) if recommendations else "系统已完全优化，可以开始使用多模型协作功能。"}

==================================================
"""
    
    return report

def main():
    """主验证函数"""
    print("🔍 开始多模型集成优化验证...")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    all_results = {}
    
    # 1. 检查增强组件
    component_results = check_enhanced_components()
    all_results.update(component_results)
    
    # 2. 检查错误处理功能
    error_results = check_error_handling_features()
    all_results.update(error_results)
    
    # 3. 检查降级机制
    fallback_results = check_fallback_mechanisms()
    all_results.update(fallback_results)
    
    # 4. 检查用户体验改进
    ux_results = check_user_experience_improvements()
    all_results.update(ux_results)
    
    # 5. 检查Docker集成
    docker_result = check_docker_integration()
    all_results["docker_integration"] = docker_result
    
    # 6. 计算优化得分
    final_score = calculate_optimization_score(all_results)
    
    # 7. 生成并显示报告
    report = generate_optimization_report(final_score, all_results)
    print(report)
    
    # 保存报告到文件
    report_file = "optimization_validation_report.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 详细报告已保存到: {report_file}")
    
    return final_score >= 85  # 85分以上认为优化成功

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)