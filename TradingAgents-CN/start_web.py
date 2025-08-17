#!/usr/bin/env python3
"""
TradingAgents-CN 简化启动脚本
解决模块导入问题的最简单方案
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    """主函数"""
    print("🚀 TradingAgents-CN Web应用启动器")
    print("=" * 50)

    # 获取项目根目录
    project_root = Path(__file__).parent
    web_dir = project_root / "web"
    app_file = web_dir / "app.py"

    # 检查文件是否存在
    if not app_file.exists():
        print(f"❌ 找不到应用文件: {app_file}")
        return

    # 检查虚拟环境
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if not in_venv:
        print("⚠️ 建议在虚拟环境中运行:")
        print("   Windows: .\\env\\Scripts\\activate")
        print("   Linux/macOS: source env/bin/activate")
        print()

    # 检查streamlit是否安装
    try:
        import streamlit  # noqa: F401

        print("✅ Streamlit已安装")
    except ImportError:
        print("❌ Streamlit未安装")
        print()
        print("请先安装项目依赖:")
        print("   pip install -e .")
        print()
        print("或单独安装Streamlit:")
        print("   pip install streamlit plotly")
        return

    # 设置环境变量，添加项目根目录到Python路径
    env = os.environ.copy()
    current_path = env.get("PYTHONPATH", "")
    if current_path:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{current_path}"
    else:
        env["PYTHONPATH"] = str(project_root)

    # 若本地API未启动，则尝试在后台启动（提供 /api/kb 等端点）
    try:
        import socket

        def _is_port_open(host: str, port: int) -> bool:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                try:
                    return s.connect_ex((host, port)) == 0
                except Exception:
                    return False

        api_host = os.getenv("MARKET_API_HOST", "127.0.0.1")
        api_port = int(os.getenv("MARKET_API_PORT", "8000"))
        if not _is_port_open(api_host, api_port):
            print(f"🛠️ 未检测到本地API({api_host}:{api_port})，尝试后台启动…")
            api_cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "tradingagents.api.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(api_port),
                "--log-level",
                "warning",
            ]
            # 最小化依赖：失败时不阻断Web启动
            try:
                subprocess.Popen(api_cmd, cwd=project_root, env=env)
                # 提前设置供前端/客户端发现
                env.setdefault("MARKET_API_BASE_URL", f"http://localhost:{api_port}")
                print("✅ 已尝试启动本地API (后台进程)")
            except Exception as e:
                print(f"⚠️ 启动本地API失败（继续启动Web）：{e}")
        else:
            env.setdefault("MARKET_API_BASE_URL", f"http://localhost:{api_port}")
    except Exception as e:
        print(f"⚠️ API探测步骤跳过：{e}")

    # 构建启动命令
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_file),
        "--server.port",
        "8501",
        "--server.address",
        "localhost",
        "--browser.gatherUsageStats",
        "false",
        "--server.fileWatcherType",
        "none",
        "--server.runOnSave",
        "false",
    ]

    print("🌐 启动Web应用...")
    print("📱 浏览器将自动打开 http://localhost:8501")
    print("⏹️  按 Ctrl+C 停止应用")
    print("=" * 50)

    try:
        # 启动应用，传递修改后的环境变量
        subprocess.run(cmd, cwd=project_root, env=env)
    except KeyboardInterrupt:
        print("\n⏹️ Web应用已停止")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        print("\n💡 如果遇到模块导入问题，请尝试:")
        print("   1. 激活虚拟环境")
        print("   2. 运行: pip install -e .")
        print("   3. 再次启动Web应用")


if __name__ == "__main__":
    main()
