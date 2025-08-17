"""
Enhanced Market Export Utilities
增强版市场分析结果导出工具 - 支持多种格式导出和自定义模板
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("enhanced_market_export_utils")
from utils.market_export_utils import MarketExportManager  # noqa: E402


def render_enhanced_export_interface(scan_id: str, results_data: dict):
    """渲染增强版导出界面"""

    st.markdown("### 📤 结果导出")
    st.caption("将市场分析结果导出为多种格式，便于保存、分享和进一步分析")

    if not results_data:
        st.warning("⚠️ 暂无结果数据可导出")
        return

    # 导出选项
    export_tabs = st.tabs(["📊 数据格式", "📑 报告格式", "🎨 自定义导出"])

    with export_tabs[0]:
        render_data_export_options(scan_id, results_data)

    with export_tabs[1]:
        render_report_export_options(scan_id, results_data)

    with export_tabs[2]:
        render_custom_export_options(scan_id, results_data)


def render_data_export_options(scan_id: str, results_data: dict):
    """渲染数据格式导出选项"""

    st.markdown("#### 📊 数据格式导出")
    st.caption("导出原始分析数据，适合进一步处理和分析")

    data_col1, data_col2, data_col3 = st.columns(3)

    with data_col1:
        st.markdown("**📄 CSV格式**")
        st.caption("适合Excel、数据分析工具")

        if st.button(
            "📥 导出股票排名CSV",
            use_container_width=True,
            key=f"export_rankings_csv_{scan_id}",
        ):
            export_rankings_csv(scan_id, results_data)

        if st.button(
            "📥 导出板块数据CSV",
            use_container_width=True,
            key=f"export_sectors_csv_{scan_id}",
        ):
            export_sectors_csv(scan_id, results_data)

    with data_col2:
        st.markdown("**📋 JSON格式**")
        st.caption("适合程序化处理")

        if st.button(
            "📥 导出完整结果JSON",
            use_container_width=True,
            key=f"export_full_json_{scan_id}",
        ):
            export_full_json(scan_id, results_data)

        if st.button(
            "📥 导出摘要JSON",
            use_container_width=True,
            key=f"export_summary_json_{scan_id}",
        ):
            export_summary_json(scan_id, results_data)

    with data_col3:
        st.markdown("**📊 Excel格式**")
        st.caption("多工作表，包含图表")

        # 使用标准导出管理器生成Excel
        if "export_manager" not in st.session_state:
            st.session_state.export_manager = MarketExportManager()
        export_manager = st.session_state.export_manager
        if st.button(
            "📥 导出完整Excel报告",
            use_container_width=True,
            key=f"export_excel_{scan_id}",
        ):
            with st.spinner("正在生成Excel文件..."):
                path = export_manager.export_scan_results(
                    scan_id, results_data, "excel"
                )
                if path:
                    st.success("✅ Excel文件生成成功")
                    with open(path, "rb") as f:
                        st.download_button(
                            label="📥 下载Excel报告",
                            data=f.read(),
                            file_name=Path(path).name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_excel_{scan_id}",
                        )
                else:
                    st.error("❌ Excel导出失败")


def render_report_export_options(scan_id: str, results_data: dict):
    """渲染报告格式导出选项"""

    st.markdown("#### 📑 报告格式导出")
    st.caption("导出格式化分析报告，适合阅读和分享")

    # 报告模板选择
    report_col1, report_col2 = st.columns(2)

    with report_col1:
        template_options = ["标准模板", "简洁模板", "详细模板", "投资报告模板"]
        selected_template = st.selectbox(
            "选择报告模板", options=template_options, key=f"report_template_{scan_id}"
        )

    with report_col2:
        language_options = ["中文", "英文", "中英双语"]
        selected_language = st.selectbox(
            "报告语言", options=language_options, key=f"report_language_{scan_id}"
        )

    # 报告内容选择
    st.markdown("##### 📋 报告内容")

    content_col1, content_col2, content_col3 = st.columns(3)

    with content_col1:
        include_rankings = st.checkbox(
            "包含股票排名", value=True, key=f"include_rankings_{scan_id}"
        )
        include_sectors = st.checkbox(
            "包含板块分析", value=True, key=f"include_sectors_{scan_id}"
        )
        include_breadth = st.checkbox(
            "包含市场指标", value=True, key=f"include_breadth_{scan_id}"
        )

    with content_col2:
        include_summary = st.checkbox(
            "包含执行摘要", value=True, key=f"include_summary_{scan_id}"
        )
        include_charts = st.checkbox(
            "包含图表", value=True, key=f"include_charts_{scan_id}"
        )
        include_recommendations = st.checkbox(
            "包含投资建议", value=True, key=f"include_recommendations_{scan_id}"
        )

    with content_col3:
        include_risk = st.checkbox(
            "包含风险提示", value=True, key=f"include_risk_{scan_id}"
        )
        include_methodology = st.checkbox(
            "包含分析方法", value=False, key=f"include_methodology_{scan_id}"
        )
        include_appendix = st.checkbox(
            "包含附录", value=False, key=f"include_appendix_{scan_id}"
        )

    # 导出按钮
    st.markdown("---")

    export_options = {
        "template": selected_template,
        "language": selected_language,
        "content": {
            "rankings": include_rankings,
            "sectors": include_sectors,
            "breadth": include_breadth,
            "summary": include_summary,
            "charts": include_charts,
            "recommendations": include_recommendations,
            "risk": include_risk,
            "methodology": include_methodology,
            "appendix": include_appendix,
        },
    }

    report_btn_col1, report_btn_col2, report_btn_col3 = st.columns(3)

    with report_btn_col1:
        if st.button(
            "📄 生成PDF报告", use_container_width=True, key=f"export_pdf_{scan_id}"
        ):
            export_pdf_report(scan_id, results_data, export_options)

    with report_btn_col2:
        if st.button(
            "🌐 生成HTML报告", use_container_width=True, key=f"export_html_{scan_id}"
        ):
            export_html_report(scan_id, results_data, export_options)

    with report_btn_col3:
        if st.button(
            "📝 生成Word报告", use_container_width=True, key=f"export_word_{scan_id}"
        ):
            export_word_report(scan_id, results_data, export_options)


def render_custom_export_options(scan_id: str, results_data: dict):
    """渲染自定义导出选项"""

    st.markdown("#### 🎨 自定义导出")
    st.caption("根据特定需求自定义导出内容和格式")

    # 自定义选项
    custom_col1, custom_col2 = st.columns(2)

    with custom_col1:
        st.markdown("##### 🎯 内容筛选")

        # 股票筛选
        if "rankings" in results_data:
            rankings_data = results_data["rankings"]

            score_threshold = st.slider(
                "最低综合评分",
                min_value=0,
                max_value=100,
                value=60,
                key=f"score_threshold_{scan_id}",
            )

            recommendation_filter = st.multiselect(
                "投资建议筛选",
                options=["买入", "持有", "关注", "卖出"],
                default=["买入", "关注"],
                key=f"rec_filter_{scan_id}",
            )

            max_stocks = st.number_input(
                "最多包含股票数",
                min_value=1,
                max_value=len(rankings_data) if rankings_data else 100,
                value=min(20, len(rankings_data)) if rankings_data else 20,
                key=f"max_stocks_{scan_id}",
            )
        else:
            score_threshold = 60
            recommendation_filter = ["买入", "关注"]
            max_stocks = 20

        # 板块筛选
        if "sectors" in results_data:
            sectors_data = results_data["sectors"]

            selected_sectors = st.multiselect(
                "包含板块",
                options=list(sectors_data.keys()),
                default=list(sectors_data.keys())[:5],
                key=f"selected_sectors_{scan_id}",
            )
        else:
            selected_sectors = []

    with custom_col2:
        st.markdown("##### 🎨 格式设置")

        # 输出格式
        output_format = st.selectbox(
            "输出格式",
            options=["PDF", "HTML", "Markdown", "纯文本"],
            key=f"output_format_{scan_id}",
        )

        # 样式设置
        color_scheme = st.selectbox(
            "配色方案",
            options=["专业蓝", "商务灰", "自然绿", "活力橙"],
            key=f"color_scheme_{scan_id}",
        )

        include_watermark = st.checkbox(
            "包含水印", value=False, key=f"watermark_{scan_id}"
        )

        include_timestamp = st.checkbox(
            "包含时间戳", value=True, key=f"timestamp_{scan_id}"
        )

    # 预览和导出
    st.markdown("---")

    preview_col, export_col = st.columns(2)

    custom_options = {
        "score_threshold": score_threshold,
        "recommendation_filter": recommendation_filter,
        "max_stocks": max_stocks,
        "selected_sectors": selected_sectors,
        "output_format": output_format,
        "color_scheme": color_scheme,
        "include_watermark": include_watermark,
        "include_timestamp": include_timestamp,
    }

    with preview_col:
        if st.button(
            "👀 预览自定义报告",
            use_container_width=True,
            key=f"preview_custom_{scan_id}",
        ):
            preview_custom_report(scan_id, results_data, custom_options)

    with export_col:
        if st.button(
            "📤 导出自定义报告",
            use_container_width=True,
            key=f"export_custom_{scan_id}",
        ):
            export_custom_report(scan_id, results_data, custom_options)


# 导出功能实现


def export_rankings_csv(scan_id: str, results_data: dict):
    """导出股票排名CSV"""

    try:
        rankings = results_data.get("rankings", [])
        if not rankings:
            st.warning("⚠️ 无股票排名数据")
            return

        df = pd.DataFrame(rankings)

        # 重新排列列的顺序
        preferred_columns = [
            "symbol",
            "name",
            "total_score",
            "technical_score",
            "fundamental_score",
            "current_price",
            "change_percent",
            "recommendation",
            "target_price",
            "market_cap",
            "pe_ratio",
            "pb_ratio",
        ]

        # 只选择存在的列
        available_columns = [col for col in preferred_columns if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in preferred_columns]
        final_columns = available_columns + remaining_columns

        if final_columns:
            df = df[final_columns]

        # 添加中文列名
        chinese_columns = {
            "symbol": "股票代码",
            "name": "股票名称",
            "total_score": "综合评分",
            "technical_score": "技术评分",
            "fundamental_score": "基本面评分",
            "current_price": "当前价格",
            "change_percent": "涨跌幅(%)",
            "recommendation": "投资建议",
            "target_price": "目标价",
            "market_cap": "市值(亿)",
            "pe_ratio": "PE倍数",
            "pb_ratio": "PB倍数",
        }

        df.rename(columns=chinese_columns, inplace=True)

        # 生成CSV
        csv_data = df.to_csv(
            index=False, encoding="utf-8-sig"
        )  # 使用utf-8-sig支持Excel打开中文

        filename = f"market_scan_{scan_id}_rankings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        st.download_button(
            label="📥 下载股票排名CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            key=f"download_rankings_csv_{scan_id}",
        )

        st.success(f"✅ 股票排名CSV已准备下载 ({len(df)}条记录)")

    except Exception as e:
        st.error(f"❌ 导出股票排名CSV失败: {e}")
        logger.error(f"导出股票排名CSV失败: {e}")


def export_sectors_csv(scan_id: str, results_data: dict):
    """导出板块数据CSV"""

    try:
        sectors = results_data.get("sectors", {})
        if not sectors:
            st.warning("⚠️ 无板块数据")
            return

        # 转换为DataFrame
        sectors_list = []
        for sector_name, sector_data in sectors.items():
            row = {"板块名称": sector_name}
            row.update(
                {
                    "涨跌幅(%)": sector_data.get("change_percent", 0),
                    "成交额(亿)": sector_data.get("volume", 0),
                    "活跃度": sector_data.get("activity_score", 0),
                    "推荐度": sector_data.get("recommendation_score", 0),
                    "龙头股票": sector_data.get("leading_stock", ""),
                    "推荐股票数": sector_data.get("recommended_count", 0),
                    "市值(亿)": sector_data.get("market_cap", 0),
                }
            )
            sectors_list.append(row)

        df = pd.DataFrame(sectors_list)

        # 生成CSV
        csv_data = df.to_csv(index=False, encoding="utf-8-sig")

        filename = f"market_scan_{scan_id}_sectors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        st.download_button(
            label="📥 下载板块数据CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            key=f"download_sectors_csv_{scan_id}",
        )

        st.success(f"✅ 板块数据CSV已准备下载 ({len(df)}条记录)")

    except Exception as e:
        st.error(f"❌ 导出板块数据CSV失败: {e}")
        logger.error(f"导出板块数据CSV失败: {e}")


def export_full_json(scan_id: str, results_data: dict):
    """导出完整结果JSON"""

    try:
        # 添加元数据
        export_data = {
            "scan_id": scan_id,
            "export_time": datetime.now().isoformat(),
            "data_type": "market_analysis_full_results",
            "version": "1.0",
            "results": results_data,
        }

        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

        filename = f"market_scan_{scan_id}_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        st.download_button(
            label="📥 下载完整结果JSON",
            data=json_str,
            file_name=filename,
            mime="application/json",
            key=f"download_full_json_{scan_id}",
        )

        st.success("✅ 完整结果JSON已准备下载")

        # 显示数据概要
        with st.expander("📊 数据概要", expanded=False):
            st.json(
                {
                    "scan_id": scan_id,
                    "export_time": export_data["export_time"],
                    "data_sections": list(results_data.keys()),
                    "total_size": f"{len(json_str) / 1024:.1f} KB",
                }
            )

    except Exception as e:
        st.error(f"❌ 导出完整JSON失败: {e}")
        logger.error(f"导出完整JSON失败: {e}")


def export_summary_json(scan_id: str, results_data: dict):
    """导出摘要JSON"""

    try:
        # 提取关键摘要信息
        summary_data = {
            "scan_id": scan_id,
            "export_time": datetime.now().isoformat(),
            "data_type": "market_analysis_summary",
            "summary": {
                "total_stocks": results_data.get("total_stocks", 0),
                "recommended_stocks": results_data.get("recommended_stocks", 0),
                "actual_cost": results_data.get("actual_cost", 0),
                "scan_duration": results_data.get("scan_duration", ""),
                "key_insights": results_data.get("summary", {}).get("key_insights", []),
                "investment_recommendations": results_data.get("summary", {}).get(
                    "investment_recommendations", {}
                ),
                "risk_factors": results_data.get("summary", {}).get("risk_factors", []),
                "market_outlook": results_data.get("summary", {}).get(
                    "market_outlook", ""
                ),
            },
        }

        # 添加前10名股票
        if "rankings" in results_data:
            top_stocks = results_data["rankings"][:10]
            summary_data["top_10_stocks"] = [
                {
                    "name": stock.get("name", ""),
                    "symbol": stock.get("symbol", ""),
                    "total_score": stock.get("total_score", 0),
                    "recommendation": stock.get("recommendation", ""),
                }
                for stock in top_stocks
            ]

        # 添加板块摘要
        if "sectors" in results_data:
            sectors = results_data["sectors"]
            summary_data["sector_summary"] = {
                sector: {
                    "change_percent": data.get("change_percent", 0),
                    "recommendation_score": data.get("recommendation_score", 0),
                }
                for sector, data in list(sectors.items())[:5]  # 只取前5个板块
            }

        json_str = json.dumps(summary_data, ensure_ascii=False, indent=2)

        filename = f"market_scan_{scan_id}_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        st.download_button(
            label="📥 下载摘要JSON",
            data=json_str,
            file_name=filename,
            mime="application/json",
            key=f"download_summary_json_{scan_id}",
        )

        st.success("✅ 摘要JSON已准备下载")

    except Exception as e:
        st.error(f"❌ 导出摘要JSON失败: {e}")
        logger.error(f"导出摘要JSON失败: {e}")


def export_excel_report(scan_id: str, results_data: dict):
    """导出Excel报告"""

    st.info("🚧 Excel导出功能正在开发中...")
    st.markdown(
        """
    **Excel报告将包含:**
    - 📊 股票排名工作表
    - 🔥 板块分析工作表  
    - 📈 市场指标工作表
    - 📑 执行摘要工作表
    - 📊 图表和可视化
    """
    )


def export_pdf_report(scan_id: str, results_data: dict, options: dict):
    """导出PDF报告"""

    st.info("🚧 PDF报告导出功能正在开发中...")
    st.markdown(
        f"""
    **PDF报告设置:**
    - 📋 模板: {options['template']}
    - 🌍 语言: {options['language']}
    - 📊 包含图表: {'是' if options['content']['charts'] else '否'}
    - 📑 包含摘要: {'是' if options['content']['summary'] else '否'}
    """
    )


def export_html_report(scan_id: str, results_data: dict, options: dict):
    """导出HTML报告"""

    try:
        # 生成HTML报告内容
        html_content = generate_html_report(scan_id, results_data, options)

        filename = f"market_scan_{scan_id}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        st.download_button(
            label="📥 下载HTML报告",
            data=html_content,
            file_name=filename,
            mime="text/html",
            key=f"download_html_{scan_id}",
        )

        st.success("✅ HTML报告已准备下载")

        # 预览选项
        if st.button("👀 预览HTML报告", key=f"preview_html_{scan_id}"):
            st.components.v1.html(html_content, height=600, scrolling=True)

    except Exception as e:
        st.error(f"❌ 导出HTML报告失败: {e}")
        logger.error(f"导出HTML报告失败: {e}")


def export_word_report(scan_id: str, results_data: dict, options: dict):
    """导出Word报告"""

    st.info("🚧 Word报告导出功能正在开发中...")
    st.markdown(
        f"""
    **Word报告设置:**
    - 📋 模板: {options['template']}
    - 🌍 语言: {options['language']}
    - 📊 内容章节: {sum(options['content'].values())}个
    """
    )


def preview_custom_report(scan_id: str, results_data: dict, custom_options: dict):
    """预览自定义报告"""

    st.markdown("### 👀 自定义报告预览")

    # 显示筛选结果
    st.markdown("#### 📊 筛选结果")

    col1, col2, col3 = st.columns(3)

    with col1:
        if "rankings" in results_data:
            filtered_stocks = filter_stocks_by_criteria(
                results_data["rankings"],
                custom_options["score_threshold"],
                custom_options["recommendation_filter"],
                custom_options["max_stocks"],
            )
            st.metric("筛选后股票数", len(filtered_stocks))

    with col2:
        if "sectors" in results_data:
            filtered_sectors = [
                s
                for s in custom_options["selected_sectors"]
                if s in results_data.get("sectors", {})
            ]
            st.metric("包含板块数", len(filtered_sectors))

    with col3:
        st.metric("输出格式", custom_options["output_format"])

    # 预览内容
    st.markdown("#### 📋 预览内容")

    if "rankings" in results_data:
        filtered_stocks = filter_stocks_by_criteria(
            results_data["rankings"],
            custom_options["score_threshold"],
            custom_options["recommendation_filter"],
            custom_options["max_stocks"],
        )

        if filtered_stocks:
            st.markdown("##### 🔝 筛选后的推荐股票")
            preview_df = pd.DataFrame(filtered_stocks)

            # 选择要显示的列
            display_columns = ["name", "symbol", "total_score", "recommendation"]
            existing_columns = [
                col for col in display_columns if col in preview_df.columns
            ]

            if existing_columns:
                preview_df = preview_df[existing_columns]
                preview_df.columns = ["股票名称", "代码", "综合评分", "建议"][
                    : len(existing_columns)
                ]
                st.dataframe(preview_df, use_container_width=True)


def export_custom_report(scan_id: str, results_data: dict, custom_options: dict):
    """导出自定义报告"""

    try:
        output_format = custom_options["output_format"]

        if output_format == "HTML":
            export_custom_html_report(scan_id, results_data, custom_options)
        elif output_format == "Markdown":
            export_custom_markdown_report(scan_id, results_data, custom_options)
        elif output_format == "纯文本":
            export_custom_text_report(scan_id, results_data, custom_options)
        else:
            st.error(f"❌ 不支持的输出格式: {output_format}")

    except Exception as e:
        st.error(f"❌ 导出自定义报告失败: {e}")
        logger.error(f"导出自定义报告失败: {e}")


def export_custom_html_report(scan_id: str, results_data: dict, custom_options: dict):
    """导出自定义HTML报告"""

    # 生成自定义HTML内容
    html_content = generate_custom_html_report(scan_id, results_data, custom_options)

    filename = (
        f"market_scan_{scan_id}_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    )

    st.download_button(
        label="📥 下载自定义HTML报告",
        data=html_content,
        file_name=filename,
        mime="text/html",
        key=f"download_custom_html_{scan_id}",
    )

    st.success("✅ 自定义HTML报告已准备下载")


def export_custom_markdown_report(
    scan_id: str, results_data: dict, custom_options: dict
):
    """导出自定义Markdown报告"""

    # 生成Markdown内容
    markdown_content = generate_custom_markdown_report(
        scan_id, results_data, custom_options
    )

    filename = (
        f"market_scan_{scan_id}_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )

    st.download_button(
        label="📥 下载Markdown报告",
        data=markdown_content,
        file_name=filename,
        mime="text/markdown",
        key=f"download_custom_md_{scan_id}",
    )

    st.success("✅ Markdown报告已准备下载")


def export_custom_text_report(scan_id: str, results_data: dict, custom_options: dict):
    """导出自定义纯文本报告"""

    # 生成纯文本内容
    text_content = generate_custom_text_report(scan_id, results_data, custom_options)

    filename = (
        f"market_scan_{scan_id}_custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    st.download_button(
        label="📥 下载纯文本报告",
        data=text_content,
        file_name=filename,
        mime="text/plain",
        key=f"download_custom_txt_{scan_id}",
    )

    st.success("✅ 纯文本报告已准备下载")


# 辅助函数


def filter_stocks_by_criteria(
    rankings: list[dict],
    score_threshold: float,
    recommendation_filter: list[str],
    max_stocks: int,
) -> list[dict]:
    """根据条件筛选股票"""

    filtered = []

    for stock in rankings:
        # 评分筛选
        if stock.get("total_score", 0) < score_threshold:
            continue

        # 建议筛选
        if (
            recommendation_filter
            and stock.get("recommendation", "") not in recommendation_filter
        ):
            continue

        filtered.append(stock)

        # 数量限制
        if len(filtered) >= max_stocks:
            break

    return filtered


def generate_html_report(scan_id: str, results_data: dict, options: dict) -> str:
    """生成HTML报告内容"""

    options["template"]
    language = options["language"]
    content = options["content"]

    # 基础HTML模板
    html_template = f"""
    <!DOCTYPE html>
    <html lang="{'zh-CN' if language == '中文' else 'en'}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>市场分析报告 - {scan_id}</title>
        <style>
            body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 40px; line-height: 1.6; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .section {{ margin: 30px 0; }}
            .stock-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .stock-table th, .stock-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            .stock-table th {{ background-color: #f2f2f2; font-weight: bold; }}
            .metric {{ display: inline-block; margin: 10px; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
            .recommendation-buy {{ color: #28a745; font-weight: bold; }}
            .recommendation-hold {{ color: #ffc107; font-weight: bold; }}
            .recommendation-sell {{ color: #dc3545; font-weight: bold; }}
            .footer {{ text-align: center; margin-top: 50px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌍 全球市场分析报告</h1>
            <h2>扫描ID: {scan_id}</h2>
            <p>生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        {generate_html_summary(results_data, content)}
        {generate_html_rankings(results_data, content)}
        {generate_html_sectors(results_data, content)}
        
        <div class="footer">
            <p>本报告由TradingAgents-CN智能分析系统生成</p>
            <p>🤖 Generated with AI | 📊 Data-Driven Analysis</p>
        </div>
    </body>
    </html>
    """

    return html_template


def generate_html_summary(results_data: dict, content: dict) -> str:
    """生成HTML摘要部分"""

    if not content.get("summary", True):
        return ""

    summary = results_data.get("summary", {})

    html = f"""
    <div class="section">
        <h2>📑 执行摘要</h2>
        
        <div class="metrics">
            <div class="metric">
                <h3>扫描股票总数</h3>
                <p>{results_data.get('total_stocks', 0)} 只</p>
            </div>
            <div class="metric">
                <h3>推荐股票数</h3>
                <p>{results_data.get('recommended_stocks', 0)} 只</p>
            </div>
            <div class="metric">
                <h3>实际成本</h3>
                <p>¥{results_data.get('actual_cost', 0):.2f}</p>
            </div>
            <div class="metric">
                <h3>扫描耗时</h3>
                <p>{results_data.get('scan_duration', '未知')}</p>
            </div>
        </div>
    """

    # 核心观点
    if "key_insights" in summary:
        html += "<h3>💡 核心观点</h3><ul>"
        insights = summary["key_insights"]
        if isinstance(insights, list):
            for insight in insights:
                html += f"<li>{insight}</li>"
        else:
            html += f"<li>{insights}</li>"
        html += "</ul>"

    # 投资建议
    if "investment_recommendations" in summary:
        recommendations = summary["investment_recommendations"]
        html += "<h3>🎯 投资建议</h3>"

        if "buy" in recommendations:
            html += "<h4 class='recommendation-buy'>推荐买入</h4><ul>"
            for stock in recommendations["buy"][:5]:
                html += f"<li>{stock.get('name', '')} ({stock.get('symbol', '')}) - {stock.get('reason', '')}</li>"
            html += "</ul>"

        if "watch" in recommendations:
            html += "<h4 class='recommendation-hold'>值得关注</h4><ul>"
            for stock in recommendations["watch"][:5]:
                html += f"<li>{stock.get('name', '')} ({stock.get('symbol', '')}) - {stock.get('reason', '')}</li>"
            html += "</ul>"

    html += "</div>"
    return html


def generate_html_rankings(results_data: dict, content: dict) -> str:
    """生成HTML排名部分"""

    if not content.get("rankings", True):
        return ""

    rankings = results_data.get("rankings", [])
    if not rankings:
        return ""

    html = """
    <div class="section">
        <h2>📊 股票排名 (前20名)</h2>
        <table class="stock-table">
            <tr>
                <th>排名</th>
                <th>股票名称</th>
                <th>代码</th>
                <th>综合评分</th>
                <th>当前价格</th>
                <th>涨跌幅</th>
                <th>投资建议</th>
            </tr>
    """

    for i, stock in enumerate(rankings[:20], 1):
        recommendation_class = (
            f"recommendation-{stock.get('recommendation', 'hold').lower()}"
        )
        html += f"""
            <tr>
                <td>{i}</td>
                <td>{stock.get('name', '')}</td>
                <td>{stock.get('symbol', '')}</td>
                <td>{stock.get('total_score', 0):.1f}</td>
                <td>¥{stock.get('current_price', 0):.2f}</td>
                <td>{stock.get('change_percent', 0):+.2f}%</td>
                <td class="{recommendation_class}">{stock.get('recommendation', '')}</td>
            </tr>
        """

    html += "</table></div>"
    return html


def generate_html_sectors(results_data: dict, content: dict) -> str:
    """生成HTML板块部分"""

    if not content.get("sectors", True):
        return ""

    sectors = results_data.get("sectors", {})
    if not sectors:
        return ""

    html = """
    <div class="section">
        <h2>🔥 板块分析</h2>
        <table class="stock-table">
            <tr>
                <th>板块名称</th>
                <th>涨跌幅</th>
                <th>成交额(亿)</th>
                <th>活跃度</th>
                <th>推荐度</th>
                <th>龙头股票</th>
            </tr>
    """

    for sector_name, sector_data in sectors.items():
        html += f"""
            <tr>
                <td>{sector_name}</td>
                <td>{sector_data.get('change_percent', 0):+.2f}%</td>
                <td>{sector_data.get('volume', 0):.1f}</td>
                <td>{sector_data.get('activity_score', 0):.1f}</td>
                <td>{sector_data.get('recommendation_score', 0):.1f}</td>
                <td>{sector_data.get('leading_stock', '')}</td>
            </tr>
        """

    html += "</table></div>"
    return html


def generate_custom_html_report(
    scan_id: str, results_data: dict, custom_options: dict
) -> str:
    """生成自定义HTML报告"""

    # 根据自定义选项筛选数据
    filtered_stocks = filter_stocks_by_criteria(
        results_data.get("rankings", []),
        custom_options["score_threshold"],
        custom_options["recommendation_filter"],
        custom_options["max_stocks"],
    )

    selected_sectors = {
        sector: data
        for sector, data in results_data.get("sectors", {}).items()
        if sector in custom_options["selected_sectors"]
    }

    # 生成HTML内容
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>自定义市场分析报告 - {scan_id}</title>
        <style>
            body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 40px; }}
            .header {{ text-align: center; margin-bottom: 30px; color: {get_color_scheme(custom_options['color_scheme'])}; }}
            .section {{ margin: 30px 0; }}
            .stock-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            .stock-table th, .stock-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            .stock-table th {{ background-color: {get_color_scheme(custom_options['color_scheme'])}; color: white; }}
            .watermark {{ position: fixed; bottom: 20px; right: 20px; opacity: 0.3; color: #666; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 自定义市场分析报告</h1>
            <h2>扫描ID: {scan_id}</h2>
            {'<p>生成时间: ' + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + '</p>' if custom_options['include_timestamp'] else ''}
        </div>
        
        <div class="section">
            <h2>🎯 筛选条件</h2>
            <p>最低综合评分: {custom_options['score_threshold']}</p>
            <p>投资建议: {', '.join(custom_options['recommendation_filter'])}</p>
            <p>最多股票数: {custom_options['max_stocks']}</p>
            <p>包含板块: {', '.join(custom_options['selected_sectors'])}</p>
        </div>
        
        <div class="section">
            <h2>📊 筛选结果股票 ({len(filtered_stocks)}只)</h2>
            <table class="stock-table">
                <tr><th>排名</th><th>股票名称</th><th>代码</th><th>综合评分</th><th>投资建议</th></tr>
    """

    for i, stock in enumerate(filtered_stocks, 1):
        html_content += f"""
                <tr>
                    <td>{i}</td>
                    <td>{stock.get('name', '')}</td>
                    <td>{stock.get('symbol', '')}</td>
                    <td>{stock.get('total_score', 0):.1f}</td>
                    <td>{stock.get('recommendation', '')}</td>
                </tr>
        """

    html_content += """
            </table>
        </div>
        
        <div class="section">
            <h2>🔥 相关板块</h2>
            <table class="stock-table">
                <tr><th>板块名称</th><th>涨跌幅</th><th>推荐度</th></tr>
    """

    for sector_name, sector_data in selected_sectors.items():
        html_content += f"""
                <tr>
                    <td>{sector_name}</td>
                    <td>{sector_data.get('change_percent', 0):+.2f}%</td>
                    <td>{sector_data.get('recommendation_score', 0):.1f}</td>
                </tr>
        """

    html_content += """
            </table>
        </div>
        
        <div class="footer">
            <p style="text-align: center; margin-top: 50px; color: #666;">
                本报告由TradingAgents-CN智能分析系统生成
            </p>
        </div>
        
    """

    if custom_options["include_watermark"]:
        html_content += """
        <div class="watermark">
            TradingAgents-CN<br>
            Confidential Report
        </div>
        """

    html_content += """
    </body>
    </html>
    """

    return html_content


def generate_custom_markdown_report(
    scan_id: str, results_data: dict, custom_options: dict
) -> str:
    """生成自定义Markdown报告"""

    filtered_stocks = filter_stocks_by_criteria(
        results_data.get("rankings", []),
        custom_options["score_threshold"],
        custom_options["recommendation_filter"],
        custom_options["max_stocks"],
    )

    selected_sectors = {
        sector: data
        for sector, data in results_data.get("sectors", {}).items()
        if sector in custom_options["selected_sectors"]
    }

    markdown_content = f"""# 📊 自定义市场分析报告

## 基本信息
- **扫描ID**: {scan_id}
"""

    if custom_options["include_timestamp"]:
        markdown_content += (
            f"- **生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
        )

    markdown_content += f"""
## 🎯 筛选条件
- **最低综合评分**: {custom_options['score_threshold']}
- **投资建议**: {', '.join(custom_options['recommendation_filter'])}
- **最多股票数**: {custom_options['max_stocks']}
- **包含板块**: {', '.join(custom_options['selected_sectors'])}

## 📊 筛选结果股票 ({len(filtered_stocks)}只)

| 排名 | 股票名称 | 代码 | 综合评分 | 投资建议 |
|------|----------|------|----------|----------|
"""

    for i, stock in enumerate(filtered_stocks, 1):
        markdown_content += f"| {i} | {stock.get('name', '')} | {stock.get('symbol', '')} | {stock.get('total_score', 0):.1f} | {stock.get('recommendation', '')} |\n"

    markdown_content += """
## 🔥 相关板块

| 板块名称 | 涨跌幅 | 推荐度 |
|----------|---------|--------|
"""

    for sector_name, sector_data in selected_sectors.items():
        markdown_content += f"| {sector_name} | {sector_data.get('change_percent', 0):+.2f}% | {sector_data.get('recommendation_score', 0):.1f} |\n"

    markdown_content += "\n---\n\n*本报告由TradingAgents-CN智能分析系统生成*\n"

    if custom_options["include_watermark"]:
        markdown_content += "\n> 🔒 Confidential Report - TradingAgents-CN\n"

    return markdown_content


def generate_custom_text_report(
    scan_id: str, results_data: dict, custom_options: dict
) -> str:
    """生成自定义纯文本报告"""

    filtered_stocks = filter_stocks_by_criteria(
        results_data.get("rankings", []),
        custom_options["score_threshold"],
        custom_options["recommendation_filter"],
        custom_options["max_stocks"],
    )

    selected_sectors = {
        sector: data
        for sector, data in results_data.get("sectors", {}).items()
        if sector in custom_options["selected_sectors"]
    }

    text_content = f"""
{'='*60}
                 自定义市场分析报告
{'='*60}

扫描ID: {scan_id}
"""

    if custom_options["include_timestamp"]:
        text_content += (
            f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n"
        )

    text_content += f"""
{'='*60}
筛选条件
{'='*60}

最低综合评分: {custom_options['score_threshold']}
投资建议: {', '.join(custom_options['recommendation_filter'])}
最多股票数: {custom_options['max_stocks']}
包含板块: {', '.join(custom_options['selected_sectors'])}

{'='*60}
筛选结果股票 ({len(filtered_stocks)}只)
{'='*60}

"""

    for i, stock in enumerate(filtered_stocks, 1):
        text_content += f"{i:2d}. {stock.get('name', ''):15s} ({stock.get('symbol', ''):8s}) 评分:{stock.get('total_score', 0):5.1f} 建议:{stock.get('recommendation', '')}\n"

    text_content += f"""
{'='*60}
相关板块
{'='*60}

"""

    for sector_name, sector_data in selected_sectors.items():
        text_content += f"{sector_name:12s} 涨跌:{sector_data.get('change_percent', 0):+6.2f}% 推荐度:{sector_data.get('recommendation_score', 0):5.1f}\n"

    text_content += f"""
{'='*60}

本报告由TradingAgents-CN智能分析系统生成
"""

    if custom_options["include_watermark"]:
        text_content += "\n[Confidential Report - TradingAgents-CN]\n"

    return text_content


def get_color_scheme(scheme_name: str) -> str:
    """获取配色方案"""

    color_schemes = {
        "专业蓝": "#0066CC",
        "商务灰": "#666666",
        "自然绿": "#28A745",
        "活力橙": "#FF6600",
    }

    return color_schemes.get(scheme_name, "#0066CC")
