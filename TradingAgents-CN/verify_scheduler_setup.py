#!/usr/bin/env python3
"""
调度器功能验证脚本
验证调度器系统的各个组件是否正常工作
"""

import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def load_env_file():
    """加载 .env 文件中的环境变量"""
    env_file = project_root / ".env"
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# 加载环境变量
load_env_file()

def check_environment_variables() -> Tuple[bool, List[str]]:
    """检查环境变量配置"""
    errors = []
    success = True
    
    print("🔧 检查环境变量配置...")
    
    required_vars = [
        'SCHEDULER_ENABLED',
        'SCHEDULER_TIMEZONE', 
        'SMTP_HOST',
        'SMTP_PORT',
        'SMTP_USER',
        'SMTP_PASS'
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            errors.append(f"环境变量 {var} 未设置")
            success = False
        else:
            print(f"  ✅ {var}: {'***' if 'PASS' in var or 'KEY' in var else value}")
    
    # 检查 SCHEDULER_ENABLED 是否为 true
    scheduler_enabled = os.getenv('SCHEDULER_ENABLED', '').lower()
    if scheduler_enabled != 'true':
        errors.append("SCHEDULER_ENABLED 必须设置为 'true'")
        success = False
    
    return success, errors


def check_settings_json() -> Tuple[bool, List[str]]:
    """检查 settings.json 配置文件"""
    errors = []
    success = True
    
    print("📁 检查 settings.json 配置...")
    
    settings_file = project_root / "config" / "settings.json"
    
    if not settings_file.exists():
        errors.append(f"配置文件不存在: {settings_file}")
        return False, errors
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        # 检查必需的配置项
        required_sections = ['email_schedules', 'email_settings', 'scheduler_settings']
        
        for section in required_sections:
            if section not in settings:
                errors.append(f"配置文件缺少必需段落: {section}")
                success = False
            else:
                print(f"  ✅ 找到配置段: {section}")
        
        # 检查邮件调度配置
        if 'email_schedules' in settings:
            email_schedules = settings['email_schedules']
            for schedule_type in ['daily', 'weekly']:
                if schedule_type not in email_schedules:
                    errors.append(f"email_schedules 缺少 {schedule_type} 配置")
                    success = False
                else:
                    schedule_config = email_schedules[schedule_type]
                    required_keys = ['enabled', 'hour', 'minute']
                    if schedule_type == 'weekly':
                        required_keys.append('weekday')
                    
                    for key in required_keys:
                        if key not in schedule_config:
                            errors.append(f"{schedule_type} 调度配置缺少字段: {key}")
                            success = False
    
    except json.JSONDecodeError as e:
        errors.append(f"settings.json 格式错误: {e}")
        success = False
    except Exception as e:
        errors.append(f"读取 settings.json 失败: {e}")
        success = False
    
    return success, errors


def check_directory_structure() -> Tuple[bool, List[str]]:
    """检查目录结构"""
    errors = []
    success = True
    
    print("📂 检查目录结构...")
    
    required_dirs = [
        project_root / "data",
        project_root / "data" / "triggers",
        project_root / "config",
        project_root / "web" / "modules"
    ]
    
    for dir_path in required_dirs:
        if not dir_path.exists():
            errors.append(f"必需目录不存在: {dir_path}")
            success = False
        else:
            print(f"  ✅ 目录存在: {dir_path.name}")
    
    # 检查重要文件
    important_files = [
        project_root / "web" / "modules" / "scheduler_admin.py",
        project_root / "data" / "triggers" / "README.md"
    ]
    
    for file_path in important_files:
        if not file_path.exists():
            errors.append(f"重要文件不存在: {file_path}")
            success = False
        else:
            print(f"  ✅ 文件存在: {file_path.name}")
    
    return success, errors


def test_manual_trigger_creation() -> Tuple[bool, List[str]]:
    """测试手动触发器创建功能"""
    errors = []
    success = True
    
    print("⚡ 测试手动触发器创建...")
    
    try:
        # 模拟创建触发器
        trigger_dir = project_root / "data" / "triggers"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 测试每日触发器
        daily_trigger_file = trigger_dir / f"test_trigger_daily_{timestamp}.json"
        trigger_data = {
            'type': 'daily',
            'created_at': datetime.now().isoformat(),
            'source': 'verification_script'
        }
        
        with open(daily_trigger_file, 'w', encoding='utf-8') as f:
            json.dump(trigger_data, f, ensure_ascii=False, indent=2)
        
        if daily_trigger_file.exists():
            print(f"  ✅ 成功创建测试触发器: {daily_trigger_file.name}")
            # 清理测试文件
            daily_trigger_file.unlink()
        else:
            errors.append("创建触发器文件失败")
            success = False
    
    except Exception as e:
        errors.append(f"触发器创建测试失败: {e}")
        success = False
    
    return success, errors


def test_scheduler_admin_import() -> Tuple[bool, List[str]]:
    """测试调度器管理模块导入"""
    errors = []
    success = True
    
    print("📦 测试调度器管理模块导入...")
    
    try:
        # 检查调度器管理模块文件是否存在
        scheduler_admin_path = project_root / "web" / "modules" / "scheduler_admin.py"
        if not scheduler_admin_path.exists():
            errors.append("调度器管理模块文件不存在")
            return False, errors
        
        # 读取文件内容检查关键函数
        with open(scheduler_admin_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_functions = [
            'render_scheduler_admin',
            'render_scheduler_overview', 
            'render_schedule_editor',
            'render_manual_triggers',
            'create_manual_trigger',
            'get_scheduler_status'
        ]
        
        missing_functions = []
        for func_name in required_functions:
            if f"def {func_name}" in content:
                print(f"  ✅ 找到函数: {func_name}")
            else:
                missing_functions.append(func_name)
        
        if missing_functions:
            errors.extend([f"调度器管理模块缺少函数: {func}" for func in missing_functions])
            success = False
        
        # 尝试导入（如果streamlit可用）
        try:
            sys.path.insert(0, str(project_root / "web" / "modules"))
            import scheduler_admin
            print("  ✅ 调度器管理模块导入成功")
        except ImportError as e:
            if 'streamlit' in str(e):
                print("  ⚠️  Streamlit未安装，但模块文件结构正确")
                # 这不算错误，只是警告
            else:
                errors.append(f"无法导入调度器管理模块: {e}")
                success = False
    
    except Exception as e:
        errors.append(f"调度器管理模块测试失败: {e}")
        success = False
    
    return success, errors


def test_docker_compatibility() -> Tuple[bool, List[str]]:
    """测试Docker兼容性"""
    errors = []
    success = True
    
    print("🐳 检查Docker兼容性...")
    
    # 检查docker-compose.yml文件
    docker_compose_file = project_root / "docker-compose.yml"
    
    if docker_compose_file.exists():
        print("  ✅ 找到 docker-compose.yml")
        
        try:
            with open(docker_compose_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否包含调度器相关配置
            scheduler_indicators = ['scheduler', 'SCHEDULER_ENABLED', 'SMTP_']
            found_indicators = []
            
            for indicator in scheduler_indicators:
                if indicator in content:
                    found_indicators.append(indicator)
            
            if found_indicators:
                print(f"  ✅ Docker配置包含调度器相关设置: {', '.join(found_indicators)}")
            else:
                errors.append("Docker配置可能缺少调度器相关设置")
                success = False
                
        except Exception as e:
            errors.append(f"读取 docker-compose.yml 失败: {e}")
            success = False
    else:
        errors.append("未找到 docker-compose.yml 文件")
        success = False
    
    return success, errors


def run_verification() -> bool:
    """运行完整的验证流程"""
    print("="*60)
    print("🔍 TradingAgents-CN 调度器功能验证")
    print("="*60)
    print()
    
    all_tests = [
        ("环境变量配置", check_environment_variables),
        ("settings.json 配置", check_settings_json),
        ("目录结构", check_directory_structure),
        ("手动触发器创建", test_manual_trigger_creation),
        ("调度器管理模块", test_scheduler_admin_import),
        ("Docker兼容性", test_docker_compatibility)
    ]
    
    overall_success = True
    all_errors = []
    
    for test_name, test_func in all_tests:
        print(f"📋 执行测试: {test_name}")
        try:
            success, errors = test_func()
            if success:
                print(f"  ✅ {test_name} 测试通过")
            else:
                print(f"  ❌ {test_name} 测试失败")
                overall_success = False
                all_errors.extend(errors)
        except Exception as e:
            print(f"  💥 {test_name} 测试异常: {e}")
            traceback.print_exc()
            overall_success = False
            all_errors.append(f"{test_name} 测试异常: {e}")
        print()
    
    print("="*60)
    print("📊 验证结果总结")
    print("="*60)
    
    if overall_success:
        print("🎉 所有验证测试通过！调度器系统配置正确。")
        print()
        print("✨ 下一步操作建议：")
        print("1. 启动Docker服务: docker compose up -d")
        print("2. 访问Web界面的调度管理页面")
        print("3. 配置邮件调度并测试手动触发功能")
        print("4. 检查日志文件确保调度器正常运行")
        return True
    else:
        print("❌ 发现以下问题需要修复：")
        print()
        for i, error in enumerate(all_errors, 1):
            print(f"{i:2d}. {error}")
        print()
        print("🔧 修复建议：")
        print("1. 检查并修复上述配置问题")
        print("2. 重新运行此验证脚本")
        print("3. 确保所有依赖已正确安装")
        return False


if __name__ == "__main__":
    try:
        success = run_verification()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  验证被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 验证脚本发生未预期错误: {e}")
        traceback.print_exc()
        sys.exit(1)