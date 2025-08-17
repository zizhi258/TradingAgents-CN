"""
Chart Batch Operations Component
图表批量操作组件 - 处理多个图表的批量管理和操作
"""

import datetime
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import streamlit as st

from tradingagents.utils.logging_init import get_logger

from .charting_artist_component import ChartingArtistAPIClient

logger = get_logger("chart_batch_operations")


class ChartBatchManager:
    """图表批量管理器"""

    def __init__(self, api_client: ChartingArtistAPIClient = None):
        self.api_client = api_client or ChartingArtistAPIClient()
        self.batch_operations = []
        self.execution_results = []

    def add_operation(
        self, operation_type: str, chart_id: str = None, **kwargs
    ) -> None:
        """添加批量操作"""
        operation = {
            "type": operation_type,
            "chart_id": chart_id,
            "params": kwargs,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.batch_operations.append(operation)

    def execute_batch(self) -> list[dict[str, Any]]:
        """执行批量操作"""
        results = []

        # 使用线程池并行执行操作
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_operation = {
                executor.submit(self._execute_single_operation, op): op
                for op in self.batch_operations
            }

            for future in as_completed(future_to_operation):
                operation = future_to_operation[future]
                try:
                    result = future.result()
                    results.append(
                        {"operation": operation, "result": result, "status": "success"}
                    )
                except Exception as e:
                    results.append(
                        {"operation": operation, "error": str(e), "status": "failed"}
                    )

        self.execution_results = results
        return results

    def _execute_single_operation(self, operation: dict[str, Any]) -> dict[str, Any]:
        """执行单个操作"""
        op_type = operation["type"]
        chart_id = operation.get("chart_id")
        params = operation.get("params", {})

        if op_type == "delete":
            return self.api_client.delete_chart(chart_id)
        elif op_type == "generate":
            return self.api_client.generate_charts(params)
        elif op_type == "export":
            return self._export_chart_local(chart_id, params)
        elif op_type == "cleanup":
            return self._cleanup_old_charts(params)
        else:
            raise ValueError(f"不支持的操作类型: {op_type}")

    def _export_chart_local(
        self, chart_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """本地导出图表"""
        try:
            # 获取图表数据
            chart_data = self.api_client.get_chart_by_id(chart_id)

            if "error" in chart_data:
                return chart_data

            # 导出到指定格式
            export_format = params.get("format", "html")
            export_path = params.get("path", f"./exports/{chart_id}.{export_format}")

            # 确保导出目录存在
            Path(export_path).parent.mkdir(parents=True, exist_ok=True)

            # 根据格式导出
            if export_format == "json":
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(chart_data, f, ensure_ascii=False, indent=2)
            elif export_format == "html":
                # 假设chart_data包含HTML内容
                html_content = chart_data.get("html_content", "")
                with open(export_path, "w", encoding="utf-8") as f:
                    f.write(html_content)

            return {"success": True, "export_path": export_path}

        except Exception as e:
            return {"error": str(e)}

    def _cleanup_old_charts(self, params: dict[str, Any]) -> dict[str, Any]:
        """清理旧图表"""
        try:
            days_threshold = params.get("days", 7)
            charts_dir = Path("data/attachments/charts")

            if not charts_dir.exists():
                return {"message": "图表目录不存在", "cleaned_count": 0}

            cutoff_date = datetime.datetime.now() - datetime.timedelta(
                days=days_threshold
            )
            cleaned_count = 0

            for chart_file in charts_dir.glob("*"):
                if chart_file.is_file():
                    file_mtime = datetime.datetime.fromtimestamp(
                        chart_file.stat().st_mtime
                    )
                    if file_mtime < cutoff_date:
                        chart_file.unlink()
                        cleaned_count += 1

            return {"success": True, "cleaned_count": cleaned_count}

        except Exception as e:
            return {"error": str(e)}

    def clear_operations(self) -> None:
        """清空操作列表"""
        self.batch_operations = []
        self.execution_results = []


def render_chart_batch_operations_panel() -> None:
    """渲染图表批量操作面板"""

    st.markdown("### 📦 图表批量操作")

    # 初始化批量管理器
    if "batch_manager" not in st.session_state:
        st.session_state.batch_manager = ChartBatchManager()

    batch_manager = st.session_state.batch_manager

    # 操作选择区域
    with st.expander("➕ 添加批量操作", expanded=True):
        operation_tabs = st.tabs(
            ["🗑️ 批量删除", "📊 批量生成", "📤 批量导出", "🧹 定时清理"]
        )

        with operation_tabs[0]:
            render_batch_delete_panel(batch_manager)

        with operation_tabs[1]:
            render_batch_generate_panel(batch_manager)

        with operation_tabs[2]:
            render_batch_export_panel(batch_manager)

        with operation_tabs[3]:
            render_batch_cleanup_panel(batch_manager)

    # 操作队列显示
    render_operation_queue(batch_manager)

    # 执行控制
    render_execution_controls(batch_manager)

    # 执行结果显示
    if batch_manager.execution_results:
        render_execution_results(batch_manager)


def render_batch_delete_panel(batch_manager: ChartBatchManager) -> None:
    """渲染批量删除面板"""

    st.markdown("**批量删除图表**")

    # 获取可删除的图表列表
    charts_list = get_deletable_charts_list()

    if charts_list:
        selected_charts = st.multiselect(
            "选择要删除的图表",
            options=[chart["id"] for chart in charts_list],
            format_func=lambda x: next(
                (c["title"] for c in charts_list if c["id"] == x), x
            ),
        )

        if selected_charts and st.button("➕ 添加删除操作"):
            for chart_id in selected_charts:
                batch_manager.add_operation("delete", chart_id=chart_id)
            st.success(f"已添加 {len(selected_charts)} 个删除操作")
            st.rerun()
    else:
        st.info("暂无可删除的图表")


def render_batch_generate_panel(batch_manager: ChartBatchManager) -> None:
    """渲染批量生成面板"""

    st.markdown("**批量生成图表**")

    # 股票列表输入
    symbols_input = st.text_area(
        "股票代码列表 (每行一个)", placeholder="AAPL\nTSLA\nMSFT", height=100
    )

    # 图表类型选择
    chart_types = st.multiselect(
        "选择图表类型",
        ["candlestick", "bar", "pie", "line", "heatmap", "radar"],
        default=["candlestick", "bar"],
    )

    # 生成配置
    col1, col2 = st.columns(2)
    with col1:
        theme = st.selectbox("主题", ["plotly_dark", "plotly_white"], key="batch_theme")
        interactive = st.checkbox("交互式", value=True, key="batch_interactive")

    with col2:
        include_indicators = st.checkbox("包含指标", value=True, key="batch_indicators")
        add_annotations = st.checkbox("添加标注", value=False, key="batch_annotations")

    if symbols_input and chart_types and st.button("➕ 添加生成操作"):
        symbols = [s.strip() for s in symbols_input.strip().split("\n") if s.strip()]

        for symbol in symbols:
            generation_params = {
                "analysis_id": f"batch_{symbol}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "chart_types": chart_types,
                "config": {
                    "theme": theme,
                    "interactive": interactive,
                    "include_indicators": include_indicators,
                    "add_annotations": add_annotations,
                },
                "data_sources": {"symbol": symbol},
            }
            batch_manager.add_operation("generate", **generation_params)

        st.success(
            f"已添加 {len(symbols)} x {len(chart_types)} = {len(symbols) * len(chart_types)} 个生成操作"
        )
        st.rerun()


def render_batch_export_panel(batch_manager: ChartBatchManager) -> None:
    """渲染批量导出面板"""

    st.markdown("**批量导出图表**")

    # 导出格式选择
    export_format = st.selectbox("导出格式", ["html", "json", "png", "svg"])

    # 导出路径
    export_path = st.text_input("导出路径", value="./exports/")

    # 获取可导出的图表
    charts_list = get_exportable_charts_list()

    if charts_list:
        selected_charts = st.multiselect(
            "选择要导出的图表",
            options=[chart["id"] for chart in charts_list],
            format_func=lambda x: next(
                (c["title"] for c in charts_list if c["id"] == x), x
            ),
        )

        if selected_charts and st.button("➕ 添加导出操作"):
            for chart_id in selected_charts:
                batch_manager.add_operation(
                    "export",
                    chart_id=chart_id,
                    format=export_format,
                    path=f"{export_path}/{chart_id}.{export_format}",
                )
            st.success(f"已添加 {len(selected_charts)} 个导出操作")
            st.rerun()
    else:
        st.info("暂无可导出的图表")


def render_batch_cleanup_panel(batch_manager: ChartBatchManager) -> None:
    """渲染批量清理面板"""

    st.markdown("**定时清理图表**")

    # 清理配置
    col1, col2 = st.columns(2)

    with col1:
        days_threshold = st.number_input(
            "保留天数", min_value=1, max_value=365, value=7
        )

    with col2:
        st.checkbox("启用自动清理", value=False)

    # 清理预览
    charts_dir = Path("data/attachments/charts")
    if charts_dir.exists():
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
        old_files = []

        for chart_file in charts_dir.glob("*"):
            if chart_file.is_file():
                file_mtime = datetime.datetime.fromtimestamp(chart_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    old_files.append(chart_file)

        st.info(f"将清理 {len(old_files)} 个超过 {days_threshold} 天的图表文件")

        if old_files and st.button("➕ 添加清理操作"):
            batch_manager.add_operation("cleanup", days=days_threshold)
            st.success("已添加清理操作")
            st.rerun()
    else:
        st.warning("图表目录不存在")


def render_operation_queue(batch_manager: ChartBatchManager) -> None:
    """渲染操作队列"""

    if not batch_manager.batch_operations:
        return

    st.markdown("### 📋 操作队列")

    # 显示操作列表
    for i, operation in enumerate(batch_manager.batch_operations):
        with st.expander(f"操作 {i+1}: {operation['type']}", expanded=False):
            col1, col2, col3 = st.columns([3, 1, 1])

            with col1:
                st.json(operation)

            with col2:
                if st.button("⬆️", key=f"move_up_{i}", help="上移"):
                    if i > 0:
                        (
                            batch_manager.batch_operations[i],
                            batch_manager.batch_operations[i - 1],
                        ) = (
                            batch_manager.batch_operations[i - 1],
                            batch_manager.batch_operations[i],
                        )
                        st.rerun()

            with col3:
                if st.button("🗑️", key=f"remove_{i}", help="移除"):
                    batch_manager.batch_operations.pop(i)
                    st.rerun()


def render_execution_controls(batch_manager: ChartBatchManager) -> None:
    """渲染执行控制"""

    if not batch_manager.batch_operations:
        return

    st.markdown("### 🚀 执行控制")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ 执行全部", type="primary"):
            with st.spinner("正在执行批量操作..."):
                results = batch_manager.execute_batch()
                st.success(f"批量操作完成，共处理 {len(results)} 个操作")
                st.rerun()

    with col2:
        if st.button("🧹 清空队列"):
            batch_manager.clear_operations()
            st.success("操作队列已清空")
            st.rerun()

    with col3:
        if st.button("💾 保存队列"):
            queue_file = f"batch_operations_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_operation_queue(batch_manager.batch_operations, queue_file)
            st.success(f"操作队列已保存到 {queue_file}")


def render_execution_results(batch_manager: ChartBatchManager) -> None:
    """渲染执行结果"""

    st.markdown("### 📊 执行结果")

    # 统计信息
    results = batch_manager.execution_results
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = len(results) - success_count

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("总操作数", len(results))
    with col2:
        st.metric("成功", success_count, delta=f"{success_count/len(results)*100:.1f}%")
    with col3:
        st.metric(
            "失败",
            failed_count,
            delta=f"{failed_count/len(results)*100:.1f}%" if failed_count > 0 else None,
        )

    # 详细结果
    result_tabs = st.tabs(["✅ 成功", "❌ 失败", "📄 全部"])

    with result_tabs[0]:
        success_results = [r for r in results if r["status"] == "success"]
        for result in success_results:
            st.success(f"操作 {result['operation']['type']} 成功")
            with st.expander("详细信息"):
                st.json(result)

    with result_tabs[1]:
        failed_results = [r for r in results if r["status"] == "failed"]
        for result in failed_results:
            st.error(
                f"操作 {result['operation']['type']} 失败: {result.get('error', 'Unknown error')}"
            )
            with st.expander("详细信息"):
                st.json(result)

    with result_tabs[2]:
        for i, result in enumerate(results):
            status_icon = "✅" if result["status"] == "success" else "❌"
            st.markdown(f"{status_icon} **操作 {i+1}**: {result['operation']['type']}")
            with st.expander("详细信息"):
                st.json(result)


def get_deletable_charts_list() -> list[dict[str, Any]]:
    """获取可删除的图表列表"""
    charts_list = []

    # 从本地文件系统获取
    charts_dir = Path("data/attachments/charts")
    if charts_dir.exists():
        for chart_file in charts_dir.glob("*.html"):
            charts_list.append(
                {
                    "id": chart_file.stem,
                    "title": chart_file.stem.replace("_", " ").title(),
                    "path": str(chart_file),
                    "source": "local",
                }
            )

    return charts_list


def get_exportable_charts_list() -> list[dict[str, Any]]:
    """获取可导出的图表列表"""
    # 复用删除列表的逻辑
    return get_deletable_charts_list()


def save_operation_queue(operations: list[dict[str, Any]], filename: str) -> None:
    """保存操作队列到文件"""
    try:
        queue_dir = Path("data/batch_queues")
        queue_dir.mkdir(parents=True, exist_ok=True)

        queue_file = queue_dir / filename
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(operations, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"保存操作队列失败: {e}")
        raise


# 辅助函数
def show_all_charts_list(
    api_client: ChartingArtistAPIClient, api_available: bool
) -> None:
    """显示所有图表列表"""
    st.session_state.show_all_charts = True


def show_chart_cleanup_dialog() -> None:
    """显示图表清理对话框"""
    st.session_state.show_cleanup_dialog = True


def show_batch_operations_dialog(
    api_client: ChartingArtistAPIClient, api_available: bool
) -> None:
    """显示批量操作对话框"""
    st.session_state.show_batch_operations = True


def show_usage_statistics() -> None:
    """显示使用统计"""
    st.session_state.show_usage_stats = True


def render_all_charts_interface(
    api_client: ChartingArtistAPIClient, api_available: bool
) -> None:
    """渲染所有图表界面"""
    st.markdown("#### 📋 所有图表")

    if api_available:
        # 从API获取图表列表
        result = api_client.list_all_charts(limit=100)
        if "error" not in result:
            charts = result.get("charts", [])
            st.dataframe(
                [
                    {
                        "ID": chart.get("chart_id", "N/A"),
                        "标题": chart.get("title", "N/A"),
                        "类型": chart.get("chart_type", "N/A"),
                        "创建时间": chart.get("created_at", "N/A"),
                    }
                    for chart in charts
                ]
            )
        else:
            st.error(f"获取图表列表失败: {result['error']}")

    # 显示本地图表
    local_charts = get_deletable_charts_list()
    if local_charts:
        st.markdown("**本地图表:**")
        st.dataframe(
            [
                {"ID": chart["id"], "标题": chart["title"], "来源": chart["source"]}
                for chart in local_charts
            ]
        )


def render_cleanup_interface() -> None:
    """渲染清理界面"""
    st.markdown("#### 🧹 清理选项")

    days_to_keep = st.number_input("保留天数", min_value=1, max_value=365, value=7)

    if st.button("执行清理"):
        cleanup_params = {"days": days_to_keep}
        batch_manager = ChartBatchManager()
        result = batch_manager._cleanup_old_charts(cleanup_params)

        if "error" in result:
            st.error(f"清理失败: {result['error']}")
        else:
            st.success(f"清理完成，删除了 {result.get('cleaned_count', 0)} 个文件")


def render_batch_operations_interface(
    api_client: ChartingArtistAPIClient, api_available: bool
) -> None:
    """渲染批量操作界面"""
    render_chart_batch_operations_panel()


def render_usage_statistics_interface() -> None:
    """渲染使用统计界面"""
    st.markdown("#### 📊 使用统计")

    # 统计本地图表
    charts_dir = Path("data/attachments/charts")
    if charts_dir.exists():
        chart_files = list(charts_dir.glob("*"))

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("图表总数", len(chart_files))

        with col2:
            total_size = sum(f.stat().st_size for f in chart_files if f.is_file()) / (
                1024 * 1024
            )  # MB
            st.metric("总大小(MB)", f"{total_size:.2f}")

        with col3:
            if chart_files:
                latest_file = max(chart_files, key=lambda x: x.stat().st_mtime)
                latest_time = datetime.datetime.fromtimestamp(
                    latest_file.stat().st_mtime
                )
                st.metric("最近生成", latest_time.strftime("%Y-%m-%d"))

    else:
        st.info("暂无统计数据")


# 增强函数实现
def download_chart_enhanced(chart: dict[str, Any]) -> None:
    """增强版图表下载"""
    try:
        if "file_path" in chart:
            file_path = Path(chart["file_path"])
            if file_path.exists():
                with open(file_path, "rb") as f:
                    st.download_button(
                        label="下载图表",
                        data=f.read(),
                        file_name=file_path.name,
                        mime="application/octet-stream",
                    )
            else:
                st.error("文件不存在")
        else:
            st.error("无法下载：文件路径未找到")

    except Exception as e:
        st.error(f"下载失败: {e}")


def share_chart_enhanced(chart: dict[str, Any]) -> None:
    """增强版图表分享"""
    chart_url = chart.get("url", "")
    if chart_url:
        st.code(f"图表链接: {chart_url}")
        st.info("复制上面的链接即可分享图表")
    else:
        # 生成临时分享链接
        chart_id = chart.get("chart_id", "unknown")
        temp_url = f"http://localhost:8501/chart/{chart_id}"
        st.code(f"临时链接: {temp_url}")
        st.caption("注意：这是临时链接，仅在应用运行时有效")


def delete_chart_enhanced(
    chart: dict[str, Any], api_client: ChartingArtistAPIClient = None
) -> None:
    """增强版图表删除"""
    if st.button("确认删除", type="secondary"):
        try:
            chart_id = chart.get("chart_id")

            # 尝试通过API删除
            if api_client and chart_id:
                result = api_client.delete_chart(chart_id)
                if "error" not in result:
                    st.success("图表已删除")
                else:
                    st.error(f"API删除失败: {result['error']}")

            # 删除本地文件
            if "file_path" in chart:
                file_path = Path(chart["file_path"])
                if file_path.exists():
                    file_path.unlink()
                    st.success("本地文件已删除")

            st.rerun()

        except Exception as e:
            st.error(f"删除失败: {e}")


def get_local_charts_enhanced(symbol: str = None) -> list[Path]:
    """获取增强的本地图表文件"""
    charts_dir = Path("data/attachments/charts")

    if not charts_dir.exists():
        return []

    chart_files = []

    # 支持多种文件格式
    patterns = ["*.html", "*.json", "*.png", "*.svg"]

    for pattern in patterns:
        for chart_file in charts_dir.glob(pattern):
            if symbol is None or chart_file.name.startswith(f"{symbol}_"):
                chart_files.append(chart_file)

    # 按修改时间排序
    chart_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    return chart_files


def display_local_charts_enhanced(charts: list[Path]) -> None:
    """显示增强的本地图表"""

    for i, chart_path in enumerate(charts[:10]):  # 最多显示10个
        try:
            parts = chart_path.stem.split("_")
            chart_symbol = parts[0] if len(parts) > 0 else "Unknown"
            chart_type = parts[1] if len(parts) > 1 else "unknown"

            with st.expander(
                f"📊 {chart_symbol} - {chart_type.title()}", expanded=(i == 0)
            ):

                if chart_path.exists():
                    # 根据文件类型显示不同内容
                    if chart_path.suffix.lower() == ".html":
                        with open(chart_path, encoding="utf-8") as f:
                            html_content = f.read()
                        st.components.v1.html(html_content, height=500)

                    elif chart_path.suffix.lower() == ".json":
                        with open(chart_path, encoding="utf-8") as f:
                            fig_dict = json.load(f)
                        import plotly.graph_objects as go

                        fig = go.Figure(fig_dict)
                        st.plotly_chart(fig, use_container_width=True)

                    elif chart_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg"]:
                        st.image(str(chart_path), use_column_width=True)

                    else:
                        st.warning(f"不支持的文件格式: {chart_path.suffix}")

                    # 显示文件信息
                    file_stat = chart_path.stat()
                    file_size = file_stat.st_size / 1024  # KB
                    file_mtime = datetime.datetime.fromtimestamp(file_stat.st_mtime)

                    st.caption(
                        f"文件大小: {file_size:.1f} KB | 修改时间: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                else:
                    st.error("图表文件不存在")

        except Exception as e:
            logger.error(f"显示本地图表失败: {e}")
            st.error(f"图表加载失败: {chart_path.name}")


# 导出主要功能函数
__all__ = [
    "ChartBatchManager",
    "render_chart_batch_operations_panel",
    "download_chart_enhanced",
    "share_chart_enhanced",
    "delete_chart_enhanced",
    "get_local_charts_enhanced",
    "display_local_charts_enhanced",
]
