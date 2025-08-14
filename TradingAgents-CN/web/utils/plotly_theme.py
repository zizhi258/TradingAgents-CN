#!/usr/bin/env python3
"""
Plotly 主题与字体统一设置
 - 统一中文字体（优先 Windows 字体，如 Microsoft YaHei / SimHei）
 - 统一配色与网格线
 - 透明背景以融入 Streamlit 主题
"""

from __future__ import annotations

from typing import List

import plotly.io as pio


def apply_plotly_theme(
    default_font_family: str = "Microsoft YaHei, SimHei, 'Noto Sans CJK SC', 'Segoe UI', Arial, sans-serif",
    colorway: List[str] | None = None,
) -> None:
    """应用全局 Plotly 主题。

    参数:
        default_font_family: 全局字体族，优先 Windows 中文字体
        colorway: 自定义颜色序列
    """
    try:
        import plotly.graph_objects as go

        if colorway is None:
            colorway = [
                "#0EA5A4",  # 青绿（主题主色）
                "#2563EB",  # 蓝
                "#F59E0B",  # 橙
                "#10B981",  # 绿
                "#EF4444",  # 红
                "#8B5CF6",  # 紫
                "#14B8A6",  # 青
            ]

        template = go.layout.Template()
        template.layout = go.Layout(
            font=dict(family=default_font_family, size=13),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                gridcolor="#E5E7EB",
                zerolinecolor="#E5E7EB",
                linecolor="#CBD5E1",
                ticks="outside",
                title_font=dict(size=12),
            ),
            yaxis=dict(
                gridcolor="#E5E7EB",
                zerolinecolor="#E5E7EB",
                linecolor="#CBD5E1",
                ticks="outside",
                title_font=dict(size=12),
            ),
            legend=dict(borderwidth=0, bgcolor="rgba(255,255,255,0)"),
            margin=dict(t=40, r=20, b=40, l=50),
            colorway=colorway,
        )

        pio.templates["ta_zen"] = template
        pio.templates.default = "ta_zen"
    except Exception:
        # 非致命，静默失败
        pass


