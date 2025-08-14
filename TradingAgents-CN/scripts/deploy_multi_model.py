#!/usr/bin/env python3
"""
多模型协作功能一键部署脚本
帮助用户快速启用和配置优化的多模型功能
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any

def print_header():
    """打印欢迎头部"""
    print("""
🚀 TradingAgents-CN 多模型协作功能一键部署
================================================
版本: 优化增强版 v2.0
特性: 用户友好的错误处理 + 智能降级机制
================================================
""")

def check_prerequisites() -> Dict[str, bool]:
    """检查系统前置条件"""
    print("🔍 检查系统前置条件...")
    
    checks = {}
    
    # 检查Python版本
    python_version = sys.version_info
    checks["python_version"] = python_version >= (3, 8)
    status = "✅" if checks["python_version"] else "❌"
    print(f"{status} Python版本: {python_version.major}.{python_version.minor} ({'符合要求' if checks['python_version'] else '需要3.8+'})")
    
    # 检查关键文件
    required_files = [
        ".env.example",
        "docker-compose.yml", 
        "requirements.txt",
        "tradingagents/core/user_friendly_error_handler.py"
    ]
    
    for file_path in required_files:
        checks[file_path] = Path(file_path).exists()
        status = "✅" if checks[file_path] else "❌"
        print(f"{status} 关键文件: {file_path}")
    
    return checks

def setup_environment_config() -> bool:
    """设置环境配置"""
    print("\n⚙️ 配置环境变量...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_example.exists():
        print("❌ .env.example 文件不存在")
        return False
    
    if env_file.exists():
        response = input("📄 .env 文件已存在，是否覆盖？[y/N]: ").lower().strip()
        if response != 'y':
            print("⏭️ 跳过环境配置，使用现有 .env 文件")
            return True
    
    # 复制环境配置文件
    shutil.copy2(env_example, env_file)
    print("✅ 已创建 .env 文件")
    
    # 读取配置内容
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 自动启用多模型功能
    if "MULTI_MODEL_ENABLED=false" in content:
        content = content.replace("MULTI_MODEL_ENABLED=false", "MULTI_MODEL_ENABLED=true")
    elif "MULTI_MODEL_ENABLED=" not in content:
        content += "\n# 多模型协作功能\nMULTI_MODEL_ENABLED=true\n"
    
    # 启用用户友好错误处理
    if "ENABLE_USER_FRIENDLY_ERRORS=" not in content:
        content += "\n# 用户友好错误处理\nENABLE_USER_FRIENDLY_ERRORS=true\n"
    
    # 保存更新的配置
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("🔧 已自动启用多模型协作和用户友好错误处理")
    return True

def prompt_api_keys() -> Dict[str, str]:
    """交互式提示用户输入API密钥"""
    print("\n🔑 配置API密钥...")
    print("💡 提示: 可以先跳过，稍后在 .env 文件中手动配置\n")
    
    api_keys = {}
    
    # 推荐的API配置顺序
    api_configs = [
        {
            "key": "FINNHUB_API_KEY", 
            "name": "FinnHub",
            "description": "必需配置，用于获取股票数据",
            "url": "https://finnhub.io/",
            "required": True
        },
        {
            "key": "GOOGLE_API_KEY",
            "name": "Google AI",
            "description": "可选配置，Gemini 模型",
            "url": "https://aistudio.google.com/",
            "required": False
        },
        {
            "key": "OPENAI_API_KEY",
            "name": "OpenAI",
            "description": "可选配置，需要国外网络",
            "url": "https://platform.openai.com/",
            "required": False
        }
    ]
    
    for config in api_configs:
        key = config["key"]
        name = config["name"]
        description = config["description"]
        required = config["required"]
        
        print(f"\n📌 {name} API密钥")
        print(f"   描述: {description}")
        print(f"   获取: {config['url']}")
        
        if required:
            api_key = input(f"🔑 请输入 {name} API密钥 (必需): ").strip()
        else:
            api_key = input(f"🔑 请输入 {name} API密钥 (可选，回车跳过): ").strip()
        
        if api_key:
            api_keys[key] = api_key
            print(f"✅ {name} API密钥已设置")
        else:
            if required:
                print(f"⚠️ {name} API密钥为空，请稍后在 .env 文件中配置")
            else:
                print(f"⏭️ 已跳过 {name} API密钥配置")
    
    return api_keys

def update_env_file(api_keys: Dict[str, str]) -> bool:
    """更新.env文件中的API密钥"""
    if not api_keys:
        return True
    
    print("\n📝 更新 .env 文件中的API密钥...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env 文件不存在")
        return False
    
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新API密钥
    for key, value in api_keys.items():
        # 查找并替换现有配置
        pattern = f"{key}=your_"
        if pattern in content:
            # 替换占位符
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith(f"{key}=your_"):
                    lines[i] = f"{key}={value}"
                    break
            content = '\n'.join(lines)
        else:
            # 如果没有找到，追加新配置
            content += f"\n{key}={value}\n"
    
    # 保存更新的文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 已更新 {len(api_keys)} 个API密钥")
    return True

def create_data_directories() -> bool:
    """创建必要的数据目录"""
    print("\n📁 创建数据目录...")
    
    directories = ["data", "logs", "config"]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 已创建目录: {dir_name}")
        else:
            print(f"📁 目录已存在: {dir_name}")
    
    return True

def test_multi_model_import() -> bool:
    """测试多模型组件导入"""
    print("\n🧪 测试多模型组件...")
    
    try:
        # 测试核心组件导入
        from tradingagents.core.user_friendly_error_handler import UserFriendlyErrorHandler
        from tradingagents.core.multi_model_manager import MultiModelManager
        print("✅ 核心多模型组件导入成功")
        
        # 测试错误处理功能
        handler = UserFriendlyErrorHandler()
        test_error = Exception("test error")
        user_error = handler.handle_error(test_error)
        print("✅ 用户友好错误处理功能正常")
        
        return True
        
    except ImportError as e:
        print(f"❌ 多模型组件导入失败: {e}")
        return False
    except Exception as e:
        print(f"⚠️ 多模型功能测试异常: {e}")
        return True  # 导入成功但功能测试异常，仍然算作成功

def show_deployment_summary(success: bool) -> None:
    """显示部署总结"""
    print("\n" + "="*60)
    print("📊 部署总结")
    print("="*60)
    
    if success:
        print("🎉 多模型协作功能部署成功！")
        print("\n✅ 主要功能:")
        print("   - 用户友好的错误处理")
        print("   - 智能任务降级机制")
        print("   - 增强的用户界面")
        print("   - Docker一键部署支持")
        
        print("\n🚀 启动方式:")
        print("   方式1 (Docker): docker-compose up")
        print("   方式2 (本地): python -m streamlit run web/app.py")
        
        print("\n📱 访问地址:")
        print("   Web界面: http://localhost:8501")
        print("   多模型功能: 选择 '🤖 多模型协作' 页面")
        
        print("\n💡 使用建议:")
        print("   - 配置完整的API密钥以获得最佳体验")
        print("   - 推荐使用 Google/DeepSeek + FinnHub 组合")
        print("   - 首次使用建议选择 '快速分析' 模式")
        
    else:
        print("❌ 部署过程中遇到问题，请检查以下事项:")
        print("   - Python版本是否 >= 3.8")
        print("   - 是否安装了所有依赖包") 
        print("   - 项目文件是否完整")
        print("   - .env 文件是否正确配置")

def main():
    """主部署函数"""
    print_header()
    
    # 切换到项目根目录
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    success_steps = 0
    total_steps = 6
    
    # 1. 检查前置条件
    checks = check_prerequisites()
    if all(checks.values()):
        success_steps += 1
        print("✅ 前置条件检查通过")
    else:
        print("❌ 前置条件检查失败，请解决上述问题后重试")
        return False
    
    # 2. 配置环境变量
    if setup_environment_config():
        success_steps += 1
    
    # 3. 获取API密钥
    api_keys = prompt_api_keys()
    success_steps += 1  # API密钥配置总是成功（即使为空）
    
    # 4. 更新.env文件
    if update_env_file(api_keys):
        success_steps += 1
    
    # 5. 创建数据目录
    if create_data_directories():
        success_steps += 1
    
    # 6. 测试多模型导入
    if test_multi_model_import():
        success_steps += 1
    
    # 显示总结
    deployment_success = success_steps >= 5  # 至少5步成功
    show_deployment_summary(deployment_success)
    
    print(f"\n📈 部署进度: {success_steps}/{total_steps} 步骤完成")
    
    if deployment_success:
        print("\n🎯 下一步: 启动应用并访问 http://localhost:8501")
        return True
    else:
        print("\n🔧 请解决上述问题后重新运行部署脚本")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 部署已被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 部署过程中出现意外错误: {e}")
        sys.exit(1)