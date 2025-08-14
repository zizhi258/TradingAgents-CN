import streamlit as st
from pathlib import Path


def _read_markdown(rel_path: str) -> str:
    """读取项目根目录下 `docs/` 的 Markdown 文件。

    返回文件内容；若不存在则返回带有错误提示的占位文本。
    """
    try:
        project_root = Path(__file__).parent.parent.parent
        file_path = project_root / rel_path
        if not file_path.exists():
            return f"> ⚠️ 未找到文档文件: `{rel_path}`\n\n请确认仓库中存在该文件。"
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"> ❌ 读取文档失败: {e}"


def _render_doc_file(rel_path: str):
    """将 Markdown 文件内容渲染到页面。"""
    content = _read_markdown(rel_path)
    st.markdown(content)


def render_docs():
    # 与截图保持一致，但提供真正的“详细版”内容渲染
    st.header("📖 使用文档（详细版）")
    
    # 创建标签页
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🚀 快速开始", 
        "⚙️ 配置参数", 
        "📊 模型选择", 
        "🎯 报告导出",
        "❓ 常见问题",
        "📚 常用外链"
    ])
    
    with tab1:
        st.markdown("### 🚀 快速开始")
        st.caption("内容来自 `docs/overview/quick-start.md`")
        _render_doc_file("docs/overview/quick-start.md")
    
    with tab2:
        st.markdown("### ⚙️ 配置参数")
        st.caption("内容来自 `docs/configuration/config-guide.md`")
        _render_doc_file("docs/configuration/config-guide.md")
    
    with tab3:
        st.markdown("### 📊 Web 界面与模型选择")
        st.caption("内容来自 `docs/usage/web-interface-guide.md`")
        _render_doc_file("docs/usage/web-interface-guide.md")
    
    with tab4:
        st.markdown("### 🎯 报告导出")
        st.caption("内容来自 `docs/guides/report-export-guide.md`（若存在）或 README 段落")
        # 优先尝试专门的导出指南；若没有则提示
        project_root = Path(__file__).parent.parent.parent
        guide = project_root / "docs/guides/report-export-guide.md"
        if guide.exists():
            _render_doc_file("docs/guides/report-export-guide.md")
        else:
            st.info("未找到 `docs/guides/report-export-guide.md`，请参考 README 中的导出说明或右侧导出按钮帮助。")
    
    with tab5:
        st.markdown("### ❓ 常见问题")
        st.caption("内容来自 `docs/faq/faq.md`，若不存在则列出常见问题文档")
        project_root = Path(__file__).parent.parent.parent
        faq = project_root / "docs/faq/faq.md"
        if faq.exists():
            _render_doc_file("docs/faq/faq.md")
        else:
            st.markdown("- `docs/troubleshooting/web-startup-issues.md`\n- `docs/troubleshooting/docker-troubleshooting.md`\n- `docs/troubleshooting/export-issues.md`")
    
    with tab6:
        st.markdown("### 📚 常用外链与快速预览")
        st.markdown("#### 📖 项目文档（点击下拉选择即可预览）")
        choices = {
            "🚀 快速开始": "docs/overview/quick-start.md",
            "📝 配置指南": "docs/configuration/config-guide.md",
            "🌐 Web界面指南": "docs/usage/web-interface-guide.md",
            "🆘 启动问题排查": "docs/troubleshooting/web-startup-issues.md",
        }
        selected = st.selectbox("选择文档进行预览", list(choices.keys()))
        _render_doc_file(choices[selected])

        st.markdown("""
        #### 🔗 外部资源
        - **GitHub项目**: [TradingAgents-CN](https://github.com/hsliuping/TradingAgents-CN)
        - **原版项目**: [TradingAgents](https://github.com/TauricResearch/TradingAgents)
        - **QQ交流群**: 782124367
        
        #### 🛠️ API文档
        - **FinnHub API**: [finnhub.io](https://finnhub.io/)
        - **Google AI**: [aistudio.google.com](https://aistudio.google.com/)
        - **DeepSeek**: [platform.deepseek.com](https://platform.deepseek.com/)
        - **Tushare**: [tushare.pro](https://tushare.pro/)
        """)
    
    # 添加页脚信息
    st.markdown("---")
    st.info(
        """
        💡 **提示**: 
        - 本页已直接渲染 `docs/` 下的原始 Markdown 文件；如未展示，请确认文件存在
        - 遇到问题可以在 GitHub 提交 Issue 或加入 QQ 群交流
        - 本项目持续更新中，欢迎贡献代码和建议
        """
    )
