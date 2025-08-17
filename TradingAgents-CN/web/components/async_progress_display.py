#!/usr/bin/env python3
"""
异步进度显示组件
支持定时刷新，从Redis或文件获取进度状态
"""

import time
from typing import Any

import streamlit as st

# 统一日志
from tradingagents.utils.logging_manager import get_logger
from web.utils.async_progress_tracker import format_time, get_progress_by_id

logger = get_logger("async_display")


class AsyncProgressDisplay:
    """异步进度显示组件"""

    def __init__(self, container, analysis_id: str, refresh_interval: float = 1.0):
        self.container = container
        self.analysis_id = analysis_id
        self.refresh_interval = refresh_interval

        with self.container:
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
            self.step_info = st.empty()
            self.time_info = st.empty()
            self.refresh_button = st.empty()

        self.last_update = 0.0
        self.is_completed = False

        logger.info(
            f"📊 [异步显示] 初始化: {analysis_id}, 刷新间隔: {refresh_interval}s"
        )

    @staticmethod
    def _should_bind_mm_results() -> bool:
        """仅在多模型个股分析页面下，才写入多模型结果到 session_state。

        目的：避免其它页面（单模型、市场分析等）完成后把结果注入到多模型页面的
        占位变量，造成跨页面信息串场。
        """
        try:
            return (
                st.session_state.get("analysis_mode") == "多模型"
                and bool(st.session_state.get("multi_model_current_analysis_id"))
            )
        except Exception:
            return False

    def update_display(self) -> bool:
        """更新显示，返回是否需要继续刷新"""
        now = time.time()

        if now - self.last_update < self.refresh_interval and not self.is_completed:
            return not self.is_completed

        progress_data = get_progress_by_id(self.analysis_id)

        if not progress_data:
            self.status_text.error("❌ 无法获取分析进度，请检查分析是否正在运行")
            return False

        self._render_progress(progress_data)
        self.last_update = now

        status = progress_data.get("status", "running")
        self.is_completed = status in ["completed", "failed"]
        return not self.is_completed

    def _render_progress(self, progress_data: dict[str, Any]) -> None:
        """渲染进度显示"""
        try:
            current_step = progress_data.get("current_step", 0)
            total_steps = progress_data.get("total_steps", 8)
            progress_percentage = progress_data.get("progress_percentage", 0.0)
            status = progress_data.get("status", "running")

            # 进度条（封顶余量：未完成前不显示超过95%）
            display_pct = progress_percentage
            if status != "completed" and display_pct > 95:
                display_pct = 95.0
            self.progress_bar.progress(min(display_pct / 100.0, 1.0))

            # 文本信息
            step_name = progress_data.get("current_step_name", "未知")
            step_description = progress_data.get("current_step_description", "")
            last_message = progress_data.get("last_message", "")

            status_icon = {"running": "🔄", "completed": "✅", "failed": "❌"}.get(
                status, "🔄"
            )
            self.status_text.info(f"{status_icon} **当前状态**: {last_message}")

            if status == "failed":
                self.step_info.error(f"❌ **分析失败**: {last_message}")
            elif status == "completed":
                self.step_info.success("🎉 **分析完成**: 所有步骤已完成")
                with self.step_info:
                    if st.button(
                        "📊 查看分析报告",
                        key=f"view_report_{progress_data.get('analysis_id', 'unknown')}",
                        type="primary",
                    ):
                        analysis_id = progress_data.get("analysis_id")
                        if not st.session_state.get("analysis_results"):
                            try:
                                from web.utils.analysis_runner import (
                                    format_analysis_results,
                                )

                                raw_results = progress_data.get("raw_results")
                                if raw_results:
                                    formatted = format_analysis_results(raw_results)
                                    if formatted:
                                        st.session_state.analysis_results = formatted
                                        st.session_state.analysis_running = False
                                    # 仅在多模型上下文中写入对应结果键
                                    if (
                                        AsyncProgressDisplay._should_bind_mm_results()
                                        and isinstance(raw_results, dict)
                                        and (
                                            "results" in raw_results
                                            or "agents_used" in raw_results
                                            or raw_results.get("collaboration_mode")
                                        )
                                    ):
                                        st.session_state.multi_model_analysis_results = raw_results
                                        st.session_state.show_multi_model_results = True
                                        st.session_state.multi_model_current_analysis_id = analysis_id
                            except Exception as e:  # noqa: BLE001
                                st.error(f"恢复分析结果失败: {e}")

                        st.session_state.show_analysis_results = True
                        st.session_state.current_analysis_id = analysis_id
                        st.rerun()
            else:
                self.step_info.info(
                    f"📊 **进度**: 第 {current_step + 1} 步，共 {total_steps} 步 ({progress_percentage:.1f}%)\n\n"
                    f"**当前步骤**: {step_name}\n\n"
                    f"**步骤说明**: {step_description}"
                )

            # 时间信息
            start_time = progress_data.get("start_time", 0.0)
            estimated_total_time = progress_data.get("estimated_total_time", 0.0)
            if status == "completed":
                real_elapsed = progress_data.get("elapsed_time", 0.0)
            elif start_time > 0:
                real_elapsed = time.time() - start_time
            else:
                real_elapsed = progress_data.get("elapsed_time", 0.0)

            remaining = max(estimated_total_time - real_elapsed, 0.0)

            if status == "completed":
                self.time_info.success(
                    f"⏱️ **已用时间**: {format_time(real_elapsed)} | **总耗时**: {format_time(real_elapsed)}"
                )
            elif status == "failed":
                self.time_info.error(
                    f"⏱️ **已用时间**: {format_time(real_elapsed)} | **分析中断**"
                )
            else:
                self.time_info.info(
                    f"⏱️ **已用时间**: {format_time(real_elapsed)} | **预计剩余**: {format_time(remaining)}"
                )

            # 运行时刷新按钮
            if status == "running":
                with self.refresh_button:
                    col1, col2, _ = st.columns([1, 1, 1])
                    with col2:
                        if st.button("🔄 手动刷新", key=f"refresh_{self.analysis_id}"):
                            st.rerun()
            else:
                self.refresh_button.empty()
        except Exception as e:  # noqa: BLE001
            logger.error(f"📊 [异步显示] 渲染失败: {e}")
            self.status_text.error(f"❌ 显示更新失败: {str(e)}")


def create_async_progress_display(
    container, analysis_id: str, refresh_interval: float = 1.0
) -> AsyncProgressDisplay:
    """创建异步进度显示组件"""
    return AsyncProgressDisplay(container, analysis_id, refresh_interval)


def auto_refresh_progress(
    display: AsyncProgressDisplay, max_duration: float = 1800
) -> None:
    """自动刷新进度显示"""
    started = time.time()
    placeholder = st.empty()
    while True:
        if time.time() - started > max_duration:
            with placeholder:
                st.warning(
                    "⚠️ 分析时间过长，已停止自动刷新。请手动刷新页面查看最新状态。"
                )
            break

        if not display.update_display():
            break

        time.sleep(display.refresh_interval)

    logger.info(f"📊 [异步显示] 自动刷新结束: {display.analysis_id}")


def streamlit_auto_refresh_progress(
    analysis_id: str, refresh_interval: int = 2
) -> bool:
    """Streamlit专用的自动刷新进度显示"""
    progress_data = get_progress_by_id(analysis_id)
    if not progress_data:
        st.error("❌ 无法获取分析进度，请检查分析是否正在运行")
        return False

    status = progress_data.get("status", "running")
    current_step = progress_data.get("current_step", 0)
    total_steps = progress_data.get("total_steps", 8)
    progress_percentage = progress_data.get("progress_percentage", 0.0)
    step_name = progress_data.get("current_step_name", "未知")
    step_description = progress_data.get("current_step_description", "")
    last_message = progress_data.get("last_message", "")

    # 未完成前封顶95%
    display_pct = progress_percentage
    if status != "completed" and display_pct > 95:
        display_pct = 95.0
    st.progress(min(display_pct / 100.0, 1.0))

    status_icon = {"running": "🔄", "completed": "✅", "failed": "❌"}.get(status, "🔄")
    st.info(f"{status_icon} **当前状态**: {last_message}")

    if status == "failed":
        st.error(f"❌ **分析失败**: {last_message}")
    elif status == "completed":
        st.success("🎉 **分析完成**: 所有步骤已完成")
        if st.button(
            "📊 查看分析报告",
            key=f"view_report_streamlit_{progress_data.get('analysis_id', 'unknown')}",
            type="primary",
        ):
            analysis_id = progress_data.get("analysis_id")
            if not st.session_state.get("analysis_results"):
                try:
                    from web.utils.analysis_runner import format_analysis_results

                    raw_results = progress_data.get("raw_results")
                    if raw_results:
                        formatted = format_analysis_results(raw_results)
                        if formatted:
                            st.session_state.analysis_results = formatted
                            st.session_state.analysis_running = False
                        # 仅在多模型上下文中写入对应结果键
                        if (
                            AsyncProgressDisplay._should_bind_mm_results()
                            and isinstance(raw_results, dict)
                            and (
                                "results" in raw_results
                                or "agents_used" in raw_results
                                or raw_results.get("collaboration_mode")
                            )
                        ):
                            st.session_state.multi_model_analysis_results = raw_results
                            st.session_state.show_multi_model_results = True
                            st.session_state.multi_model_current_analysis_id = analysis_id
                except Exception as e:  # noqa: BLE001
                    st.error(f"恢复分析结果失败: {e}")
    else:
        st.info(
            f"📊 **进度**: 第 {current_step + 1} 步，共 {total_steps} 步 ({progress_percentage:.1f}%)\n\n"
            f"**当前步骤**: {step_name}\n\n"
            f"**步骤说明**: {step_description}"
        )

    # 刷新控制（运行时显示）
    if status == "running":
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 刷新进度", key=f"refresh_streamlit_{analysis_id}"):
                st.rerun()
        with col2:
            auto_refresh_key = f"auto_refresh_streamlit_{analysis_id}"
            default_value = st.session_state.get(auto_refresh_key, True)
            auto_refresh = st.checkbox(
                "🔄 自动刷新", value=default_value, key=auto_refresh_key
            )
            if auto_refresh:
                last_refresh_key = f"last_refresh_{analysis_id}"
                now = time.time()
                last = st.session_state.get(last_refresh_key, 0.0)
                if now - last >= max(1, int(refresh_interval)):
                    st.session_state[last_refresh_key] = now
                    st.rerun()
    else:
        # 完成后关闭自动刷新
        st.session_state[f"auto_refresh_streamlit_{analysis_id}"] = False

    return status in ["completed", "failed"]


def display_static_progress(analysis_id: str) -> bool:
    """显示静态进度（不自动刷新），返回是否已完成"""
    progress_data = get_progress_by_id(analysis_id)
    if not progress_data:
        st.error("❌ 无法获取分析进度，请检查分析是否正在运行")
        return False

    status = progress_data.get("status", "running")
    progress_percentage = progress_data.get("progress_percentage", 0.0)
    step_name = progress_data.get("current_step_name", "未知")
    step_description = progress_data.get("current_step_description", "正在处理...")
    last_message = progress_data.get("last_message", "")

    # 未完成前封顶95%，与其它进度展示函数保持一致
    display_pct = progress_percentage
    if status != "completed" and display_pct > 95:
        display_pct = 95.0

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.write(f"**当前步骤**: {step_name}")
    with col2:
        st.metric("进度", f"{display_pct:.1f}%")
    with col3:
        start_time = progress_data.get("start_time", 0.0)
        if status == "completed":
            elapsed = progress_data.get("elapsed_time", 0.0)
        elif start_time > 0:
            elapsed = time.time() - start_time
        else:
            elapsed = progress_data.get("elapsed_time", 0.0)
        st.metric("已用时间", format_time(elapsed))
    with col4:
        remaining_time = progress_data.get("remaining_time", 0.0)
        if status == "completed":
            st.metric("预计剩余", "已完成")
        elif status == "failed":
            st.metric("预计剩余", "已中断")
        elif remaining_time > 0 and status == "running":
            st.metric("预计剩余", format_time(remaining_time))
        else:
            st.metric("预计剩余", "计算中...")

    # 进度条亦采用封顶后的百分比，避免未完成态显示 100%
    st.progress(min(display_pct / 100.0, 1.0))
    st.write(f"**当前任务**: {step_description}")

    status_icon = {"running": "🔄", "completed": "✅", "failed": "❌"}.get(status, "🔄")
    if status == "failed":
        st.error(f"❌ **分析失败**: {last_message}")
    elif status == "completed":
        st.success(f"🎉 **分析完成**: {last_message}")
        if st.button(
            "📊 查看分析报告", key=f"view_report_static_{analysis_id}", type="primary"
        ):
            if not st.session_state.get("analysis_results"):
                try:
                    from web.utils.analysis_runner import format_analysis_results

                    raw = progress_data.get("raw_results")
                    if raw:
                        formatted = format_analysis_results(raw)
                        if formatted:
                            st.session_state.analysis_results = formatted
                            st.session_state.analysis_running = False
                        # 仅在多模型上下文中同步写入多模型结果与标记
                        if (
                            AsyncProgressDisplay._should_bind_mm_results()
                            and isinstance(raw, dict)
                            and ("results" in raw or "agents_used" in raw or raw.get("collaboration_mode"))
                        ):
                            st.session_state.multi_model_analysis_results = raw
                            st.session_state.show_multi_model_results = True
                            st.session_state.multi_model_current_analysis_id = analysis_id
                except Exception as e:  # noqa: BLE001
                    st.error(f"恢复分析结果失败: {e}")
            st.session_state.show_analysis_results = True
            st.session_state.current_analysis_id = analysis_id
            st.rerun()
    else:
        st.info(f"{status_icon} **当前状态**: {last_message}")

    # 清理完成态的会话键
    if status in ["completed", "failed"]:
        for key in [
            f"progress_display_{analysis_id}",
            f"refresh_container_{analysis_id}",
        ]:
            if key in st.session_state:
                del st.session_state[key]

    return status in ["completed", "failed"]


def display_unified_progress(
    analysis_id: str, show_refresh_controls: bool = True
) -> bool:
    """统一的进度显示函数，返回是否已完成"""
    completed = display_static_progress(analysis_id)
    if show_refresh_controls and not completed:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🔄 刷新进度", key=f"refresh_unified_{analysis_id}"):
                st.rerun()
        with col2:
            auto_refresh_key = f"auto_refresh_unified_{analysis_id}"
            default_value = st.session_state.get(auto_refresh_key, True)
            auto_refresh = st.checkbox(
                "🔄 自动刷新", value=default_value, key=auto_refresh_key
            )
            if auto_refresh:
                time.sleep(2)
                st.rerun()
    return completed


def display_static_progress_with_controls(
    analysis_id: str, show_refresh_controls: bool = True
) -> bool:
    """显示静态进度，可控制是否显示刷新控件（兼容旧接口）"""
    return display_unified_progress(analysis_id, show_refresh_controls)
