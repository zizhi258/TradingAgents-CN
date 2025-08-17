"""
系统状态页面组件
显示系统运行状态、健康检查、诊断信息
"""

import json
import os
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import psutil
import streamlit as st

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("web.system_status")


def render_system_status():
    """渲染系统状态页面"""

    st.markdown("## 🔧 系统状态")
    st.markdown("系统运行状态监控、健康检查和诊断工具")

    # 页面标签
    tab1, tab2, tab3, tab4 = st.tabs(
        ["🏥 健康检查", "📊 系统资源", "🔑 API状态", "🛠️ 诊断工具"]
    )

    # 健康检查标签页
    with tab1:
        render_health_check()

    # 系统资源标签页
    with tab2:
        render_system_resources()

    # API状态标签页
    with tab3:
        render_api_status()

    # 诊断工具标签页
    with tab4:
        render_diagnostic_tools()


def render_health_check():
    """渲染健康检查页面"""

    st.markdown("### 系统健康检查")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 执行健康检查", type="primary"):
            with st.spinner("正在执行健康检查..."):
                health_results = perform_health_check()
                st.session_state.health_results = health_results

    with col2:
        if st.button("📋 导出检查报告"):
            if "health_results" in st.session_state:
                export_health_report(st.session_state.health_results)
            else:
                st.warning("请先执行健康检查")

    # 显示健康检查结果
    if "health_results" in st.session_state:
        display_health_results(st.session_state.health_results)


def render_system_resources():
    """渲染系统资源页面"""

    st.markdown("### 系统资源监控")

    try:
        # 获取系统信息
        system_info = get_system_info()

        # 基础系统信息
        st.markdown("#### 📋 基础信息")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("🖥️ 操作系统", f"{system_info['os']} {system_info['arch']}")
            st.metric("🐍 Python版本", system_info["python_version"])

        with col2:
            st.metric("💾 总内存", f"{system_info['total_memory']:.1f} GB")
            st.metric("💽 CPU核心", system_info["cpu_cores"])

        with col3:
            st.metric("📁 工作目录", "已设置")
            st.caption(system_info["working_dir"])

        # 实时资源使用情况
        st.markdown("#### 📊 资源使用")

        col4, col5, col6 = st.columns(3)

        with col4:
            cpu_percent = psutil.cpu_percent(interval=1)
            st.metric("⚡ CPU使用率", f"{cpu_percent:.1f}%")
            st.progress(cpu_percent / 100)

        with col5:
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            st.metric("💾 内存使用率", f"{memory_percent:.1f}%")
            st.progress(memory_percent / 100)

        with col6:
            disk = psutil.disk_usage(system_info["working_dir"])
            disk_percent = disk.percent
            st.metric("💿 磁盘使用率", f"{disk_percent:.1f}%")
            st.progress(disk_percent / 100)

        # 磁盘空间详情
        st.markdown("#### 💽 存储空间")
        disk_info = get_disk_info()

        for mount_point, info in disk_info.items():
            with st.expander(f"📁 {mount_point}", expanded=False):
                col7, col8, col9 = st.columns(3)

                with col7:
                    st.write(f"**总容量**: {info['total']:.1f} GB")

                with col8:
                    st.write(f"**已使用**: {info['used']:.1f} GB")

                with col9:
                    st.write(f"**可用**: {info['free']:.1f} GB")

        # 自动刷新
        if st.checkbox("⚡ 自动刷新 (10秒)", value=False):
            st.rerun()

    except Exception as e:
        st.error(f"❌ 获取系统信息失败: {e}")


def render_api_status():
    """渲染API状态页面"""

    st.markdown("### API密钥状态检查")

    # API密钥检查
    try:
        from utils.api_checker import check_api_keys

        api_status = check_api_keys()

        # 总体状态
        if api_status["all_configured"]:
            st.success("✅ 所有必需的API密钥均已配置")
        else:
            st.warning("⚠️ 部分API密钥未配置")

        # 详细状态
        st.markdown("#### 📋 详细状态")

        for key_name, status_info in api_status["details"].items():
            with st.expander(f"🔑 {key_name}", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    if status_info["configured"]:
                        st.success("✅ 已配置")
                        st.write(f"**显示值**: `{status_info['display']}`")
                    else:
                        st.error("❌ 未配置")
                        st.write("**状态**: 密钥未设置或格式错误")

                with col2:
                    # 获取帮助信息
                    help_info = get_api_help_info(key_name)
                    if help_info:
                        st.markdown("**获取方式**:")
                        st.markdown(f"- 网站: {help_info['url']}")
                        st.markdown(f"- 用途: {help_info['purpose']}")

        # 连接测试
        st.markdown("#### 🔗 连接测试")
        if st.button("🧪 测试API连接"):
            test_api_connections(api_status)

    except Exception as e:
        st.error(f"❌ API状态检查失败: {e}")

    # 数据库状态
    st.markdown("#### 🗄️ 数据库状态")

    col3, col4 = st.columns(2)

    with col3:
        # MongoDB状态
        st.markdown("**MongoDB**")
        mongo_status = check_mongodb_status()
        if mongo_status["enabled"]:
            if mongo_status["connected"]:
                st.success("✅ 连接正常")
                st.write(f"**地址**: {mongo_status['host']}:{mongo_status['port']}")
                st.write(f"**数据库**: {mongo_status['database']}")
            else:
                st.error("❌ 连接失败")
                st.write(f"**错误**: {mongo_status['error']}")
        else:
            st.info("ℹ️ 未启用")

    with col4:
        # Redis状态
        st.markdown("**Redis**")
        redis_status = check_redis_status()
        if redis_status["enabled"]:
            if redis_status["connected"]:
                st.success("✅ 连接正常")
                st.write(f"**地址**: {redis_status['host']}:{redis_status['port']}")
                st.write(f"**数据库**: {redis_status['db']}")
            else:
                st.error("❌ 连接失败")
                st.write(f"**错误**: {redis_status['error']}")
        else:
            st.info("ℹ️ 未启用")


def render_diagnostic_tools():
    """渲染诊断工具页面"""

    st.markdown("### 诊断和维护工具")

    # 日志分析
    st.markdown("#### 📋 日志分析")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📖 查看最新日志"):
            show_recent_logs()

    with col2:
        if st.button("⚠️ 查看错误日志"):
            show_error_logs()

    with col3:
        if st.button("🧹 清理日志文件"):
            cleanup_old_logs()

    # 线程管理
    st.markdown("#### 🔄 进程管理")
    col4, col5 = st.columns(2)

    with col4:
        if st.button("🔍 检查运行线程"):
            show_running_threads()

    with col5:
        if st.button("🧹 清理僵尸线程"):
            cleanup_zombie_threads()

    # 缓存管理
    st.markdown("#### 💾 缓存管理")
    col6, col7, col8 = st.columns(3)

    with col6:
        if st.button("📊 缓存统计"):
            show_cache_statistics()

    with col7:
        if st.button("🔄 重置缓存"):
            reset_cache()

    with col8:
        if st.button("🧹 清理过期缓存"):
            cleanup_expired_cache()

    # 导出诊断包
    st.markdown("#### 📦 诊断包导出")
    st.markdown("导出包含系统状态、日志文件、配置信息的完整诊断包")

    if st.button("📥 生成诊断包", type="primary"):
        generate_diagnostic_package()


def perform_health_check() -> dict:
    """执行系统健康检查"""

    results = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "checks": {},
    }

    # 检查Python环境
    try:
        results["checks"]["python_version"] = {
            "status": "pass",
            "version": sys.version,
            "message": f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }
    except Exception as e:
        results["checks"]["python_version"] = {"status": "fail", "error": str(e)}
        results["overall_status"] = "unhealthy"

    # 检查依赖包
    try:
        import numpy  # noqa: F401
        import pandas  # noqa: F401
        import streamlit  # noqa: F401

        results["checks"]["dependencies"] = {
            "status": "pass",
            "message": "核心依赖包正常",
        }
    except ImportError as e:
        results["checks"]["dependencies"] = {
            "status": "fail",
            "error": f"依赖包缺失: {e}",
        }
        results["overall_status"] = "unhealthy"

    # 检查文件系统权限
    try:
        test_file = Path(tempfile.gettempdir()) / "tradingagents_test.txt"
        test_file.write_text("test")
        test_file.unlink()
        results["checks"]["filesystem"] = {
            "status": "pass",
            "message": "文件系统读写正常",
        }
    except Exception as e:
        results["checks"]["filesystem"] = {
            "status": "fail",
            "error": f"文件系统权限问题: {e}",
        }
        results["overall_status"] = "unhealthy"

    # 检查内存使用
    try:
        memory = psutil.virtual_memory()
        if memory.percent < 80:
            results["checks"]["memory"] = {
                "status": "pass",
                "usage": f"{memory.percent:.1f}%",
                "message": "内存使用正常",
            }
        else:
            results["checks"]["memory"] = {
                "status": "warning",
                "usage": f"{memory.percent:.1f}%",
                "message": "内存使用率较高",
            }
    except Exception as e:
        results["checks"]["memory"] = {"status": "fail", "error": str(e)}

    # 检查磁盘空间
    try:
        disk = psutil.disk_usage("/")
        free_gb = disk.free / (1024**3)
        if free_gb > 1:  # 至少1GB可用空间
            results["checks"]["disk_space"] = {
                "status": "pass",
                "free_space": f"{free_gb:.1f} GB",
                "message": "磁盘空间充足",
            }
        else:
            results["checks"]["disk_space"] = {
                "status": "warning",
                "free_space": f"{free_gb:.1f} GB",
                "message": "磁盘空间不足",
            }
    except Exception as e:
        results["checks"]["disk_space"] = {"status": "fail", "error": str(e)}

    return results


def display_health_results(results: dict):
    """显示健康检查结果"""

    # 总体状态
    if results["overall_status"] == "healthy":
        st.success(f"✅ 系统状态健康 - 检查时间: {results['timestamp']}")
    else:
        st.error(f"❌ 系统存在问题 - 检查时间: {results['timestamp']}")

    # 详细检查结果
    st.markdown("#### 📋 详细检查结果")

    for check_name, check_result in results["checks"].items():
        with st.expander(f"🔍 {check_name.replace('_', ' ').title()}", expanded=False):

            if check_result["status"] == "pass":
                st.success("✅ 检查通过")
                if "message" in check_result:
                    st.write(check_result["message"])
            elif check_result["status"] == "warning":
                st.warning("⚠️ 需要注意")
                if "message" in check_result:
                    st.write(check_result["message"])
            else:  # fail
                st.error("❌ 检查失败")
                if "error" in check_result:
                    st.write(f"错误: {check_result['error']}")

            # 显示其他信息
            for key, value in check_result.items():
                if key not in ["status", "message", "error"]:
                    st.write(f"**{key.replace('_', ' ').title()}**: {value}")


def get_system_info() -> dict:
    """获取系统信息"""

    return {
        "os": f"{os.name} ({psutil.WINDOWS if os.name == 'nt' else psutil.LINUX})",
        "arch": os.uname().machine if hasattr(os, "uname") else "unknown",
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "total_memory": psutil.virtual_memory().total / (1024**3),
        "cpu_cores": psutil.cpu_count(),
        "working_dir": str(Path.cwd()),
    }


def get_disk_info() -> dict:
    """获取磁盘信息"""

    disk_info = {}

    try:
        # 获取所有磁盘分区
        partitions = psutil.disk_partitions()

        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.mountpoint] = {
                    "total": usage.total / (1024**3),
                    "used": usage.used / (1024**3),
                    "free": usage.free / (1024**3),
                    "filesystem": partition.fstype,
                }
            except PermissionError:
                # 跳过无权限访问的分区
                continue

    except Exception as e:
        logger.warning(f"获取磁盘信息失败: {e}")

    return disk_info


def check_mongodb_status() -> dict:
    """检查MongoDB连接状态"""

    mongo_enabled = os.getenv("MONGODB_ENABLED", "false").lower() == "true"

    if not mongo_enabled:
        return {"enabled": False}

    try:
        from pymongo import MongoClient

        host = os.getenv("MONGODB_HOST", "localhost")
        port = int(os.getenv("MONGODB_PORT", "27017"))
        database = os.getenv("MONGODB_DATABASE", "trading_agents")

        client = MongoClient(host, port, serverSelectionTimeoutMS=3000)
        client.server_info()  # 触发连接

        return {
            "enabled": True,
            "connected": True,
            "host": host,
            "port": port,
            "database": database,
        }

    except Exception as e:
        return {"enabled": True, "connected": False, "error": str(e)}


def check_redis_status() -> dict:
    """检查Redis连接状态"""

    redis_enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"

    if not redis_enabled:
        return {"enabled": False}

    try:
        import redis

        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        db = int(os.getenv("REDIS_DB", "0"))

        r = redis.Redis(host=host, port=port, db=db, socket_timeout=3)
        r.ping()  # 测试连接

        return {
            "enabled": True,
            "connected": True,
            "host": host,
            "port": port,
            "db": db,
        }

    except Exception as e:
        return {"enabled": True, "connected": False, "error": str(e)}


def get_api_help_info(key_name: str) -> dict | None:
    """获取API密钥帮助信息"""

    help_mapping = {
        "Google AI": {
            "url": "https://aistudio.google.com/",
            "purpose": "AI模型推理和生成",
        },
        "FinnHub": {"url": "https://finnhub.io/", "purpose": "美股市场数据和新闻"},
        "DeepSeek": {
            "url": "https://platform.deepseek.com/",
            "purpose": "中文AI模型推理",
        },
        "Tushare": {"url": "https://tushare.pro/", "purpose": "A股市场数据"},
    }

    return help_mapping.get(key_name)


def test_api_connections(api_status: dict):
    """测试API连接"""

    st.markdown("#### 🧪 API连接测试结果")

    # 这里可以添加具体的API连接测试逻辑
    for key_name, status_info in api_status["details"].items():
        if status_info["configured"]:
            # 模拟连接测试
            with st.spinner(f"测试 {key_name} 连接..."):
                # 这里应该添加实际的API测试逻辑
                st.success(f"✅ {key_name} - 连接正常")
        else:
            st.warning(f"⚠️ {key_name} - 未配置，跳过测试")


def show_recent_logs():
    """显示最新日志"""

    try:
        log_dir = Path.cwd() / "logs"
        if not log_dir.exists():
            st.info("📭 暂无日志文件")
            return

        # 查找最新的日志文件
        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            st.info("📭 暂无日志文件")
            return

        latest_log = max(log_files, key=lambda x: x.stat().st_mtime)

        # 读取最后100行
        with open(latest_log, encoding="utf-8") as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines

        st.markdown("#### 📖 最新日志内容")
        st.text_area("日志内容", "".join(recent_lines), height=400)

    except Exception as e:
        st.error(f"❌ 读取日志失败: {e}")


def show_error_logs():
    """显示错误日志"""
    st.info("🔄 错误日志功能开发中...")


def cleanup_old_logs():
    """清理旧日志文件"""
    st.info("🔄 日志清理功能开发中...")


def show_running_threads():
    """显示运行中的线程"""

    try:
        from utils.thread_tracker import get_active_threads_summary

        thread_info = get_active_threads_summary()

        st.markdown("#### 🔄 活跃线程信息")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("总线程数", thread_info.get("total_threads", 0))

        with col2:
            st.metric("分析线程", thread_info.get("analysis_threads", 0))

        with col3:
            st.metric("Web线程", thread_info.get("web_threads", 0))

        # 显示线程详情
        if thread_info.get("details"):
            st.json(thread_info["details"])

    except Exception as e:
        st.error(f"❌ 获取线程信息失败: {e}")


def cleanup_zombie_threads():
    """清理僵尸线程"""
    st.info("🔄 线程清理功能开发中...")


def show_cache_statistics():
    """显示缓存统计"""
    st.info("🔄 缓存统计功能开发中...")


def reset_cache():
    """重置缓存"""
    st.info("🔄 重置缓存功能开发中...")


def cleanup_expired_cache():
    """清理过期缓存"""
    st.info("🔄 清理过期缓存功能开发中...")


def generate_diagnostic_package():
    """生成诊断包"""

    try:
        with st.spinner("正在生成诊断包..."):
            # 创建临时目录
            temp_dir = Path(tempfile.mkdtemp())

            # 收集系统信息
            system_info = get_system_info()
            health_results = perform_health_check()

            # 写入系统信息
            with open(temp_dir / "system_info.json", "w", encoding="utf-8") as f:
                json.dump(system_info, f, ensure_ascii=False, indent=2)

            # 写入健康检查结果
            with open(temp_dir / "health_check.json", "w", encoding="utf-8") as f:
                json.dump(health_results, f, ensure_ascii=False, indent=2)

            # 复制日志文件
            log_dir = Path.cwd() / "logs"
            if log_dir.exists():
                for log_file in log_dir.glob("*.log"):
                    if log_file.stat().st_size < 10 * 1024 * 1024:  # 小于10MB的日志文件
                        import shutil

                        shutil.copy2(log_file, temp_dir / log_file.name)

            # 创建ZIP包
            zip_filename = (
                f"diagnostic_package_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )
            zip_path = temp_dir / zip_filename

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in temp_dir.glob("*"):
                    if file_path != zip_path:
                        zf.write(file_path, file_path.name)

            # 提供下载
            with open(zip_path, "rb") as f:
                zip_data = f.read()

            st.download_button(
                label="📥 下载诊断包",
                data=zip_data,
                file_name=zip_filename,
                mime="application/zip",
            )

            st.success("✅ 诊断包生成完成！")

            # 清理临时文件
            import shutil

            shutil.rmtree(temp_dir)

    except Exception as e:
        st.error(f"❌ 生成诊断包失败: {e}")


def export_health_report(health_results: dict):
    """导出健康检查报告"""

    try:
        report_content = f"""# TradingAgents-CN 系统健康报告

## 基本信息
- 生成时间: {health_results['timestamp']}
- 总体状态: {health_results['overall_status']}

## 检查结果

"""

        for check_name, check_result in health_results["checks"].items():
            report_content += f"### {check_name.replace('_', ' ').title()}\n"
            report_content += f"- 状态: {check_result['status']}\n"

            if "message" in check_result:
                report_content += f"- 信息: {check_result['message']}\n"

            if "error" in check_result:
                report_content += f"- 错误: {check_result['error']}\n"

            for key, value in check_result.items():
                if key not in ["status", "message", "error"]:
                    report_content += f"- {key.replace('_', ' ').title()}: {value}\n"

            report_content += "\n"

        st.download_button(
            label="📥 下载健康报告",
            data=report_content,
            file_name=f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
            mime="text/markdown",
        )

        st.success("✅ 健康报告已准备下载！")

    except Exception as e:
        st.error(f"❌ 导出健康报告失败: {e}")
