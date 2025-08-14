#!/usr/bin/env python3
"""
TradingAgents-CN 调度器系统完整验证脚本
验证所有增强功能和改进
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_environment_configuration() -> Dict[str, Any]:
    """测试环境配置"""
    print("🔍 测试环境配置")
    results = {"passed": [], "failed": [], "warnings": []}
    
    # 检查.env文件
    env_file = project_root / '.env'
    if env_file.exists():
        results["passed"].append("✅ .env文件存在")
        
        # 检查关键环境变量
        from dotenv import load_dotenv
        load_dotenv(env_file)
        
        required_vars = [
            'SCHEDULER_ENABLED',
            'SCHEDULER_TIMEZONE', 
            'SMTP_HOST',
            'SMTP_PORT',
            'SMTP_USER',
            'SMTP_PASS'
        ]
        
        for var in required_vars:
            if os.getenv(var):
                results["passed"].append(f"✅ 环境变量 {var} 已设置")
            else:
                results["failed"].append(f"❌ 环境变量 {var} 未设置")
    else:
        results["failed"].append("❌ .env文件不存在")
    
    return results

def test_settings_configuration() -> Dict[str, Any]:
    """测试配置文件"""
    print("📋 测试settings.json配置")
    results = {"passed": [], "failed": [], "warnings": []}
    
    settings_file = project_root / 'config' / 'settings.json'
    if settings_file.exists():
        results["passed"].append("✅ settings.json文件存在")
        
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # 检查必要的配置段
            required_sections = [
                'email_schedules',
                'scheduler_settings',
                'digest_performance_tuning',
                'cost_controls', 
                'observability'
            ]
            
            for section in required_sections:
                if section in settings:
                    results["passed"].append(f"✅ 配置段 {section} 存在")
                else:
                    results["failed"].append(f"❌ 配置段 {section} 缺失")
            
            # 检查邮件调度配置
            if 'email_schedules' in settings:
                email_schedules = settings['email_schedules']
                for schedule_type in ['daily', 'weekly']:
                    if schedule_type in email_schedules:
                        schedule = email_schedules[schedule_type]
                        required_fields = ['enabled', 'hour', 'minute']
                        
                        for field in required_fields:
                            if field in schedule:
                                results["passed"].append(f"✅ {schedule_type}调度字段 {field} 存在")
                            else:
                                results["failed"].append(f"❌ {schedule_type}调度字段 {field} 缺失")
                        
        except json.JSONDecodeError as e:
            results["failed"].append(f"❌ settings.json格式错误: {e}")
        except Exception as e:
            results["failed"].append(f"❌ 读取settings.json失败: {e}")
    else:
        results["failed"].append("❌ settings.json文件不存在")
    
    return results

def test_directory_structure() -> Dict[str, Any]:
    """测试目录结构"""
    print("📁 测试目录结构")
    results = {"passed": [], "failed": [], "warnings": []}
    
    required_dirs = [
        'tradingagents/services/scheduler',
        'tradingagents/services/subscription', 
        'tradingagents/utils',
        'web/modules',
        'web/components',
        'data/triggers',
        'config',
        'scripts'
    ]
    
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            results["passed"].append(f"✅ 目录 {dir_path} 存在")
        else:
            # 如果是data/triggers目录不存在，创建它
            if dir_path == 'data/triggers':
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    results["passed"].append(f"✅ 目录 {dir_path} 已创建")
                except Exception as e:
                    results["failed"].append(f"❌ 无法创建目录 {dir_path}: {e}")
            else:
                results["failed"].append(f"❌ 目录 {dir_path} 不存在")
    
    return results

def test_key_files() -> Dict[str, Any]:
    """测试关键文件"""
    print("📄 测试关键文件")
    results = {"passed": [], "failed": [], "warnings": []}
    
    key_files = [
        'tradingagents/services/scheduler/market_scheduler.py',
        'tradingagents/services/subscription/subscription_manager.py',
        'tradingagents/utils/run_reporter.py',
        'web/modules/scheduler_admin.py',
        'web/components/subscription_manager.py',
        'scripts/diagnose_email.py',
        'docker-compose.yml',
        'pyproject.toml'
    ]
    
    for file_path in key_files:
        full_path = project_root / file_path
        if full_path.exists():
            results["passed"].append(f"✅ 文件 {file_path} 存在")
            
            # 对Python文件进行基本语法检查
            if file_path.endswith('.py'):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 基本的语法检查
                    compile(content, file_path, 'exec')
                    results["passed"].append(f"✅ 文件 {file_path} 语法正确")
                except SyntaxError as e:
                    results["failed"].append(f"❌ 文件 {file_path} 语法错误: {e}")
                except Exception as e:
                    results["warnings"].append(f"⚠️ 文件 {file_path} 检查失败: {e}")
        else:
            results["failed"].append(f"❌ 文件 {file_path} 不存在")
    
    return results

def test_manual_trigger_functionality() -> Dict[str, Any]:
    """测试手动触发器功能"""
    print("🚀 测试手动触发器功能")
    results = {"passed": [], "failed": [], "warnings": []}
    
    try:
        # 动态导入避免路径问题
        sys.path.insert(0, str(project_root / 'web'))
        from web.modules.scheduler_admin import create_manual_trigger
        
        # 创建测试触发器
        trigger_file = create_manual_trigger('daily', {
            'test': True,
            'source': 'verification_script'
        })
        
        if trigger_file:
            results["passed"].append("✅ 手动触发器创建成功")
            
            # 验证文件存在
            if Path(trigger_file).exists():
                results["passed"].append("✅ 触发器文件存在")
                
                # 验证文件内容
                try:
                    with open(trigger_file, 'r', encoding='utf-8') as f:
                        trigger_data = json.load(f)
                    
                    if 'type' in trigger_data and 'created_at' in trigger_data:
                        results["passed"].append("✅ 触发器文件格式正确")
                    else:
                        results["failed"].append("❌ 触发器文件格式不正确")
                        
                    # 清理测试文件
                    Path(trigger_file).unlink()
                    results["passed"].append("✅ 测试触发器文件已清理")
                    
                except Exception as e:
                    results["failed"].append(f"❌ 触发器文件验证失败: {e}")
            else:
                results["failed"].append("❌ 触发器文件不存在")
        else:
            results["failed"].append("❌ 手动触发器创建失败")
            
    except Exception as e:
        results["failed"].append(f"❌ 触发器功能测试失败: {e}")
    
    return results

def test_run_reporter() -> Dict[str, Any]:
    """测试运行报告功能"""
    print("📊 测试运行报告功能")
    results = {"passed": [], "failed": [], "warnings": []}
    
    try:
        from tradingagents.utils.run_reporter import RunReportManager
        
        # 创建测试实例
        manager = RunReportManager(str(project_root / 'data' / 'test_reports'))
        results["passed"].append("✅ 运行报告管理器初始化成功")
        
        # 测试创建报告
        run_id = manager.create_run_report('test', {'verification': True})
        if run_id:
            results["passed"].append("✅ 运行报告创建成功")
            
            # 测试更新报告
            success = manager.update_run_report(run_id, status='running', test_field='test_value')
            if success:
                results["passed"].append("✅ 运行报告更新成功")
            else:
                results["failed"].append("❌ 运行报告更新失败")
            
            # 测试完成报告
            success = manager.complete_run_report(
                run_id, 'completed', 
                subscriptions=1, symbols=2, emails_sent=1,
                total_cost=0.5
            )
            if success:
                results["passed"].append("✅ 运行报告完成成功")
            else:
                results["failed"].append("❌ 运行报告完成失败")
            
            # 测试获取报告
            recent_reports = manager.get_recent_reports(5)
            if recent_reports:
                results["passed"].append("✅ 获取最近报告成功")
            else:
                results["warnings"].append("⚠️ 没有找到最近的报告")
            
            # 测试统计功能
            stats = manager.get_statistics_summary(1)
            if stats and 'total_runs' in stats:
                results["passed"].append("✅ 统计功能正常")
            else:
                results["warnings"].append("⚠️ 统计功能异常")
            
            # 清理测试数据
            try:
                import shutil
                test_dir = project_root / 'data' / 'test_reports'
                if test_dir.exists():
                    shutil.rmtree(test_dir)
                results["passed"].append("✅ 测试报告数据已清理")
            except Exception as e:
                results["warnings"].append(f"⚠️ 清理测试数据失败: {e}")
                
        else:
            results["failed"].append("❌ 运行报告创建失败")
            
    except Exception as e:
        results["failed"].append(f"❌ 运行报告功能测试失败: {e}")
    
    return results

def test_email_diagnosis() -> Dict[str, Any]:
    """测试邮件诊断功能"""
    print("📧 测试邮件诊断功能")
    results = {"passed": [], "failed": [], "warnings": []}
    
    try:
        # 检查诊断脚本是否存在且可执行
        script_path = project_root / 'scripts' / 'diagnose_email.py'
        if script_path.exists():
            results["passed"].append("✅ 邮件诊断脚本存在")
            
            # 尝试导入主要函数
            try:
                sys.path.insert(0, str(script_path.parent))
                import diagnose_email
                
                if hasattr(diagnose_email, 'diagnose_email_config'):
                    results["passed"].append("✅ 邮件配置诊断函数存在")
                else:
                    results["failed"].append("❌ 邮件配置诊断函数缺失")
                
                if hasattr(diagnose_email, 'test_smtp_connection'):
                    results["passed"].append("✅ SMTP连接测试函数存在")
                else:
                    results["failed"].append("❌ SMTP连接测试函数缺失")
                
                if hasattr(diagnose_email, 'send_test_email'):
                    results["passed"].append("✅ 测试邮件发送函数存在")
                else:
                    results["failed"].append("❌ 测试邮件发送函数缺失")
                    
            except Exception as e:
                results["failed"].append(f"❌ 邮件诊断脚本导入失败: {e}")
        else:
            results["failed"].append("❌ 邮件诊断脚本不存在")
            
    except Exception as e:
        results["failed"].append(f"❌ 邮件诊断功能测试失败: {e}")
    
    return results

def test_dependencies() -> Dict[str, Any]:
    """测试依赖项"""
    print("📦 测试Python依赖项")
    results = {"passed": [], "failed": [], "warnings": []}
    
    # 检查pyproject.toml中的关键依赖
    required_packages = [
        'streamlit',
        'apscheduler',
        'pymongo', 
        'python-dotenv',
        'jinja2',
        'pytz'
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            results["passed"].append(f"✅ 依赖包 {package} 可用")
        except ImportError:
            results["failed"].append(f"❌ 依赖包 {package} 不可用")
    
    return results

def print_results(test_name: str, results: Dict[str, Any]):
    """打印测试结果"""
    print(f"\n{test_name} 结果:")
    print("-" * 50)
    
    for passed in results.get("passed", []):
        print(f"  {passed}")
    
    for warning in results.get("warnings", []):
        print(f"  {warning}")
        
    for failed in results.get("failed", []):
        print(f"  {failed}")
    
    passed_count = len(results.get("passed", []))
    failed_count = len(results.get("failed", []))
    warning_count = len(results.get("warnings", []))
    
    print(f"\n总结: {passed_count} 通过, {failed_count} 失败, {warning_count} 警告")
    return failed_count == 0

def main():
    """主验证函数"""
    print("🔍 TradingAgents-CN 调度器系统增强验证")
    print("=" * 60)
    print(f"验证时间: {datetime.now()}")
    print(f"项目路径: {project_root}")
    print()
    
    test_functions = [
        ("环境配置", test_environment_configuration),
        ("配置文件", test_settings_configuration), 
        ("目录结构", test_directory_structure),
        ("关键文件", test_key_files),
        ("手动触发器", test_manual_trigger_functionality),
        ("运行报告", test_run_reporter),
        ("邮件诊断", test_email_diagnosis),
        ("依赖项", test_dependencies)
    ]
    
    all_passed = True
    total_passed = 0
    total_failed = 0
    total_warnings = 0
    
    for test_name, test_func in test_functions:
        try:
            results = test_func()
            success = print_results(test_name, results)
            
            if not success:
                all_passed = False
            
            total_passed += len(results.get("passed", []))
            total_failed += len(results.get("failed", []))
            total_warnings += len(results.get("warnings", []))
            
        except Exception as e:
            print(f"\n❌ {test_name} 测试异常: {e}")
            all_passed = False
            total_failed += 1
    
    # 最终结果
    print("\n" + "=" * 60)
    print("🎯 最终验证结果")
    print("=" * 60)
    
    if all_passed and total_failed == 0:
        print("🎉 所有测试通过！调度器系统增强完成。")
        status = "✅ PASSED"
    elif total_failed > 0:
        print("⚠️ 部分测试失败，需要修复。")
        status = "❌ FAILED"
    else:
        print("✅ 测试基本通过，有一些警告项目。")
        status = "⚠️ PASSED_WITH_WARNINGS"
    
    print(f"\n总计: {total_passed} 通过, {total_failed} 失败, {total_warnings} 警告")
    print(f"状态: {status}")
    print()
    
    if total_failed > 0:
        print("请根据上述失败项目进行修复，然后重新运行验证。")
    else:
        print("系统已准备就绪，可以进行生产部署。")
    
    return total_failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)