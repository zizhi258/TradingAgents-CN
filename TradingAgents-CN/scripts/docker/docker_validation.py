#!/usr/bin/env python3
"""
Docker部署验证脚本
验证TradingAgents-CN Docker部署的完整性和功能性
"""

import subprocess
import sys
from typing import Any

import requests


# 颜色定义
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    WHITE = "\033[1;37m"
    NC = "\033[0m"  # No Color


def print_colored(message: str, color: str = Colors.NC):
    """打印彩色文本"""
    print(f"{color}{message}{Colors.NC}")


def run_command(command: str, capture_output: bool = True) -> tuple[bool, str]:
    """运行命令并返回结果"""
    try:
        if capture_output:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=30
            )
            return result.returncode == 0, result.stdout + result.stderr
        else:
            result = subprocess.run(command, shell=True, timeout=30)
            return result.returncode == 0, ""
    except subprocess.TimeoutExpired:
        return False, "命令执行超时"
    except Exception as e:
        return False, str(e)


def check_docker_services() -> list[dict[str, Any]]:
    """检查Docker服务状态"""
    print_colored("🐳 检查Docker服务状态", Colors.BLUE)

    results = []

    # 检查Docker是否运行
    success, output = run_command("docker --version")
    results.append(
        {
            "test": "Docker版本检查",
            "success": success,
            "message": output.strip() if success else "Docker未安装或未运行",
            "category": "docker",
        }
    )

    # 检查Docker Compose是否可用
    success, output = run_command("docker-compose --version")
    results.append(
        {
            "test": "Docker Compose版本检查",
            "success": success,
            "message": output.strip() if success else "Docker Compose未安装",
            "category": "docker",
        }
    )

    # 检查容器状态
    success, output = run_command("docker-compose ps")
    if success:
        containers_running = "Up" in output
        results.append(
            {
                "test": "容器状态检查",
                "success": containers_running,
                "message": (
                    "容器正在运行" if containers_running else f"容器状态异常: {output}"
                ),
                "category": "docker",
            }
        )
    else:
        results.append(
            {
                "test": "容器状态检查",
                "success": False,
                "message": f"无法获取容器状态: {output}",
                "category": "docker",
            }
        )

    return results


def check_web_interface() -> list[dict[str, Any]]:
    """检查Web界面可访问性"""
    print_colored("🌐 检查Web界面可访问性", Colors.BLUE)

    results = []

    # 检查Streamlit健康端点
    try:
        response = requests.get("http://localhost:8501/_stcore/health", timeout=10)
        if response.status_code == 200:
            results.append(
                {
                    "test": "Web界面健康检查",
                    "success": True,
                    "message": "Web界面可正常访问",
                    "category": "web",
                }
            )
        else:
            results.append(
                {
                    "test": "Web界面健康检查",
                    "success": False,
                    "message": f"Web界面返回状态码: {response.status_code}",
                    "category": "web",
                }
            )
    except requests.exceptions.RequestException as e:
        results.append(
            {
                "test": "Web界面健康检查",
                "success": False,
                "message": f"Web界面无法访问: {str(e)}",
                "category": "web",
            }
        )

    # 检查主页面
    try:
        response = requests.get("http://localhost:8501", timeout=15)
        if response.status_code == 200:
            results.append(
                {
                    "test": "Web界面主页面",
                    "success": True,
                    "message": f"主页面加载成功 (大小: {len(response.content)} bytes)",
                    "category": "web",
                }
            )
        else:
            results.append(
                {
                    "test": "Web界面主页面",
                    "success": False,
                    "message": f"主页面返回状态码: {response.status_code}",
                    "category": "web",
                }
            )
    except requests.exceptions.RequestException as e:
        results.append(
            {
                "test": "Web界面主页面",
                "success": False,
                "message": f"主页面无法访问: {str(e)}",
                "category": "web",
            }
        )

    return results


def check_google_genai_sdk() -> list[dict[str, Any]]:
    """检查Google GenAI SDK"""
    print_colored("🧠 检查Google GenAI SDK", Colors.BLUE)

    results = []

    # 检查SDK是否已安装
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"from google import genai; print('Google GenAI SDK imported successfully')\""
    )
    results.append(
        {
            "test": "Google GenAI SDK导入测试",
            "success": success,
            "message": output.strip() if success else f"SDK导入失败: {output}",
            "category": "sdk",
        }
    )

    # 检查类型模块
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"from google.genai import types; print('Types module imported successfully')\""
    )
    results.append(
        {
            "test": "Google GenAI Types模块测试",
            "success": success,
            "message": output.strip() if success else f"Types模块导入失败: {output}",
            "category": "sdk",
        }
    )

    # 检查客户端初始化（需要API密钥）
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"import os; from google import genai; api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_AI_API_KEY'); print('API Key configured:' if api_key else 'No API Key'); client = genai.Client() if api_key else None; print('Client initialized successfully' if client else 'No client (missing API key)')\""
    )
    results.append(
        {
            "test": "Google GenAI客户端初始化",
            "success": success,
            "message": output.strip() if success else f"客户端初始化失败: {output}",
            "category": "sdk",
        }
    )

    return results


def check_database_connections() -> list[dict[str, Any]]:
    """检查数据库连接"""
    print_colored("💾 检查数据库连接", Colors.BLUE)

    results = []

    # 检查MongoDB连接
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"import pymongo; client = pymongo.MongoClient('mongodb://admin:tradingagents123@mongodb:27017/'); client.admin.command('ping'); print('MongoDB connection successful')\""
    )
    results.append(
        {
            "test": "MongoDB连接测试",
            "success": success,
            "message": output.strip() if success else f"MongoDB连接失败: {output}",
            "category": "database",
        }
    )

    # 检查Redis连接
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"import redis; r = redis.Redis(host='redis', port=6379, password='tradingagents123'); r.ping(); print('Redis connection successful')\""
    )
    results.append(
        {
            "test": "Redis连接测试",
            "success": success,
            "message": output.strip() if success else f"Redis连接失败: {output}",
            "category": "database",
        }
    )

    return results


def check_environment_variables() -> list[dict[str, Any]]:
    """检查环境变量配置"""
    print_colored("🔑 检查环境变量配置", Colors.BLUE)

    results = []

    # 检查关键环境变量
    env_vars = [
        "GEMINI_API_KEY",
        "SILICONFLOW_API_KEY",
        "DEEPSEEK_API_KEY",
        "MULTI_MODEL_ENABLED",
    ]

    for var in env_vars:
        success, output = run_command(
            f"docker exec TradingAgents-web python -c \"import os; print('{var}:', 'SET' if os.getenv('{var}') else 'NOT SET')\""
        )
        is_set = "SET" in output
        results.append(
            {
                "test": f"环境变量 {var}",
                "success": is_set,
                "message": output.strip() if success else f"无法检查环境变量: {output}",
                "category": "environment",
            }
        )

    return results


def check_multi_model_system() -> list[dict[str, Any]]:
    """检查多模型系统"""
    print_colored("🤖 检查多模型系统", Colors.BLUE)

    results = []

    # 检查多模型管理器
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"from tradingagents.core.multi_model_manager import MultiModelManager; print('MultiModelManager imported successfully')\""
    )
    results.append(
        {
            "test": "多模型管理器导入",
            "success": success,
            "message": output.strip() if success else f"多模型管理器导入失败: {output}",
            "category": "multi_model",
        }
    )

    # 检查智能路由引擎
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"from tradingagents.core.smart_routing_engine import SmartRoutingEngine; print('SmartRoutingEngine imported successfully')\""
    )
    results.append(
        {
            "test": "智能路由引擎导入",
            "success": success,
            "message": output.strip() if success else f"智能路由引擎导入失败: {output}",
            "category": "multi_model",
        }
    )

    # 尝试初始化多模型系统
    success, output = run_command(
        "docker exec TradingAgents-web python -c \"import yaml; from tradingagents.core.multi_model_manager import MultiModelManager; config = yaml.safe_load(open('/app/config/multi_model_config.yaml', 'r', encoding='utf-8')); manager = MultiModelManager(config.get('providers', {})); print('Multi-model system initialized successfully')\""
    )
    results.append(
        {
            "test": "多模型系统初始化",
            "success": success,
            "message": output.strip() if success else f"多模型系统初始化失败: {output}",
            "category": "multi_model",
        }
    )

    return results


def generate_report(all_results: list[dict[str, Any]]) -> None:
    """生成测试报告"""
    print_colored("\n📊 Docker部署验证报告", Colors.WHITE)
    print_colored("=" * 60, Colors.WHITE)

    # 按类别分组结果
    categories = {}
    for result in all_results:
        category = result.get("category", "other")
        if category not in categories:
            categories[category] = []
        categories[category].append(result)

    # 统计
    total_tests = len(all_results)
    passed_tests = sum(1 for result in all_results if result["success"])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

    # 显示总体统计
    print_colored("\n📈 总体统计:", Colors.CYAN)
    print_colored(f"  总测试数: {total_tests}", Colors.WHITE)
    print_colored(f"  通过: {passed_tests}", Colors.GREEN)
    print_colored(
        f"  失败: {failed_tests}", Colors.RED if failed_tests > 0 else Colors.WHITE
    )
    print_colored(
        f"  成功率: {success_rate:.1f}%",
        (
            Colors.GREEN
            if success_rate >= 80
            else Colors.YELLOW if success_rate >= 60 else Colors.RED
        ),
    )

    # 显示各类别结果
    category_names = {
        "docker": "🐳 Docker服务",
        "web": "🌐 Web界面",
        "sdk": "🧠 Google GenAI SDK",
        "database": "💾 数据库",
        "environment": "🔑 环境变量",
        "multi_model": "🤖 多模型系统",
    }

    for category, tests in categories.items():
        category_passed = sum(1 for test in tests if test["success"])
        category_total = len(tests)
        category_rate = (
            (category_passed / category_total) * 100 if category_total > 0 else 0
        )

        print_colored(f"\n{category_names.get(category, category)}:", Colors.CYAN)
        print_colored(
            f"  状态: {category_passed}/{category_total} ({category_rate:.1f}%)",
            (
                Colors.GREEN
                if category_rate >= 80
                else Colors.YELLOW if category_rate >= 60 else Colors.RED
            ),
        )

        for test in tests:
            status_color = Colors.GREEN if test["success"] else Colors.RED
            status_icon = "✅" if test["success"] else "❌"
            print_colored(
                f"  {status_icon} {test['test']}: {test['message']}", status_color
            )

    # 显示建议
    print_colored("\n💡 建议:", Colors.CYAN)
    if success_rate >= 90:
        print_colored("🎉 Docker部署状态优秀！所有主要功能正常运行。", Colors.GREEN)
    elif success_rate >= 80:
        print_colored("👍 Docker部署状态良好，有少数问题需要注意。", Colors.YELLOW)
        print_colored("建议检查失败的测试项并进行修复。", Colors.YELLOW)
    elif success_rate >= 60:
        print_colored("⚠️ Docker部署有一些问题，建议进行修复。", Colors.YELLOW)
        print_colored("重点关注失败的测试项，可能影响系统功能。", Colors.YELLOW)
    else:
        print_colored("🚨 Docker部署存在严重问题，需要立即修复！", Colors.RED)
        print_colored("建议重新运行部署脚本或检查系统配置。", Colors.RED)

    # 显示后续步骤
    print_colored("\n🔧 后续步骤:", Colors.CYAN)
    if failed_tests > 0:
        print_colored("1. 检查失败项的错误信息", Colors.YELLOW)
        print_colored("2. 运行: docker-compose logs -f web", Colors.YELLOW)
        print_colored("3. 检查.env文件配置", Colors.YELLOW)
        print_colored(
            "4. 重新运行部署脚本: ./scripts/docker/docker_deployment_fix.sh",
            Colors.YELLOW,
        )
    else:
        print_colored("🎉 所有测试通过！可以开始使用系统：", Colors.GREEN)
        print_colored("   Web界面: http://localhost:8501", Colors.GREEN)
        print_colored("   MongoDB管理: http://localhost:8082", Colors.GREEN)


def main():
    """主函数"""
    print_colored("🚀 TradingAgents-CN Docker部署验证", Colors.WHITE)
    print_colored("=" * 50, Colors.WHITE)

    all_results = []

    try:
        # 执行所有检查
        all_results.extend(check_docker_services())
        all_results.extend(check_web_interface())
        all_results.extend(check_google_genai_sdk())
        all_results.extend(check_database_connections())
        all_results.extend(check_environment_variables())
        all_results.extend(check_multi_model_system())

        # 生成报告
        generate_report(all_results)

        # 返回适当的退出代码
        failed_tests = sum(1 for result in all_results if not result["success"])
        return 0 if failed_tests == 0 else 1

    except KeyboardInterrupt:
        print_colored("\n\n⚠️ 验证被用户中断", Colors.YELLOW)
        return 1
    except Exception as e:
        print_colored(f"\n\n🚨 验证过程中出现异常: {str(e)}", Colors.RED)
        return 1


if __name__ == "__main__":
    sys.exit(main())
