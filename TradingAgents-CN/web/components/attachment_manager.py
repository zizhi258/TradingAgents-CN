"""
附件管理Web组件
提供文件上传和管理的Streamlit界面
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict

from tradingagents.services.file_manager import FileManager
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.attachment')


def render_attachment_manager(embedded: bool = False):
    """渲染附件管理界面

    embedded: 当作为“图书馆”子页嵌入时，避免重复标题
    """
    if not embedded:
        # 页面主标题已由上层页面渲染，这里仅给出简短说明，避免标题重复
        st.markdown("管理邮件附件文件的上传、存储和配置")
    
    # 初始化文件管理器
    try:
        file_manager = FileManager()
    except Exception as e:
        st.error(f"❌ 初始化文件管理器失败: {e}")
        return
    
    # 标签页
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 上传文件",
        "📋 我的文件", 
        "📊 存储统计",
        "⚙️ 文件设置"
    ])
    
    # 上传文件标签页
    with tab1:
        render_file_upload(file_manager)
        
    # 我的文件标签页
    with tab2:
        render_file_list(file_manager)
        
    # 存储统计标签页
    with tab3:
        render_storage_stats(file_manager)
        
    # 文件设置标签页
    with tab4:
        render_file_settings(file_manager)


def render_file_upload(file_manager: FileManager):
    """渲染文件上传界面"""
    
    st.markdown("### 上传附件文件")
    
    # 文件上传组件
    uploaded_files = st.file_uploader(
        "选择要上传的文件",
        type=['pdf', 'docx', 'doc', 'xlsx', 'xls', 'png', 'jpg', 'jpeg', 'gif', 'txt', 'md', 'csv'],
        accept_multiple_files=True,
        help="支持PDF、Word、Excel、图片、文本等格式"
    )
    
    if uploaded_files:
        st.markdown("#### 上传配置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            file_category = st.selectbox(
                "文件分类",
                ["upload", "report", "chart", "temp"],
                format_func=lambda x: {
                    "upload": "📁 用户上传",
                    "report": "📄 分析报告",
                    "chart": "📊 图表文件",
                    "temp": "🗂️ 临时文件"
                }.get(x, x),
                help="选择文件的用途分类"
            )
            
        with col2:
            auto_rename = st.checkbox(
                "自动重命名",
                value=True,
                help="为文件添加时间戳前缀避免重名"
            )
        
        # 文件描述
        file_description = st.text_area(
            "文件描述（可选）",
            placeholder="描述这些文件的用途和内容...",
            height=100
        )
        
        # 批量上传按钮
        if st.button("📤 开始上传", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            uploaded_count = 0
            total_files = len(uploaded_files)
            
            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    # 更新进度
                    progress = (i + 1) / total_files
                    progress_bar.progress(progress)
                    status_text.text(f"正在上传: {uploaded_file.name} ({i+1}/{total_files})")
                    
                    # 读取文件内容
                    file_content = uploaded_file.read()
                    
                    # 处理文件名
                    filename = uploaded_file.name
                    if auto_rename:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name_parts = filename.rsplit('.', 1)
                        if len(name_parts) == 2:
                            filename = f"{timestamp}_{name_parts[0]}.{name_parts[1]}"
                        else:
                            filename = f"{timestamp}_{filename}"
                    
                    # 准备元数据
                    metadata = {
                        'original_name': uploaded_file.name,
                        'size': uploaded_file.size,
                        'type': uploaded_file.type,
                        'description': file_description,
                        'uploaded_via': 'web_interface'
                    }
                    
                    # 保存文件
                    file_id = file_manager.save_file(
                        content=file_content,
                        filename=filename,
                        category=file_category,
                        metadata=metadata
                    )
                    
                    uploaded_count += 1
                    logger.info(f"✅ 文件上传成功: {filename} -> {file_id}")
                    
                except Exception as e:
                    st.error(f"❌ 上传文件失败 {uploaded_file.name}: {e}")
                    logger.error(f"文件上传失败: {e}")
            
            progress_bar.progress(1.0)
            status_text.text("上传完成！")
            
            if uploaded_count > 0:
                st.success(f"✅ 成功上传 {uploaded_count} 个文件！")
                st.rerun()
            else:
                st.error("❌ 没有文件上传成功")


def render_file_list(file_manager: FileManager):
    """渲染文件列表界面"""
    
    st.markdown("### 文件管理")
    
    # 筛选选项
    col1, col2, col3 = st.columns(3)
    
    with col1:
        category_filter = st.selectbox(
            "按分类筛选",
            ["全部", "upload", "report", "chart", "temp"],
            format_func=lambda x: {
                "全部": "📁 全部文件",
                "upload": "📁 用户上传",
                "report": "📄 分析报告", 
                "chart": "📊 图表文件",
                "temp": "🗂️ 临时文件"
            }.get(x, x)
        )
        
    with col2:
        sort_by = st.selectbox(
            "排序方式",
            ["created_at", "size", "filename"],
            format_func=lambda x: {
                "created_at": "⏰ 创建时间",
                "size": "📏 文件大小",
                "filename": "📝 文件名"
            }.get(x, x)
        )
        
    with col3:
        items_per_page = st.selectbox(
            "每页显示",
            [10, 20, 50, 100],
            index=1
        )
    
    # 获取文件列表
    category = None if category_filter == "全部" else category_filter
    files = file_manager.list_files(category)
    
    if not files:
        st.info("📭 暂无文件")
        return
    
    # 排序
    if sort_by == "created_at":
        files.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    elif sort_by == "size":
        files.sort(key=lambda x: x.get('size', 0), reverse=True)
    elif sort_by == "filename":
        files.sort(key=lambda x: x.get('filename', ''))
    
    # 分页
    total_files = len(files)
    total_pages = (total_files + items_per_page - 1) // items_per_page
    
    if total_pages > 1:
        page = st.selectbox(f"页面 (共{total_pages}页)", range(1, total_pages + 1))
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_files = files[start_idx:end_idx]
    else:
        page_files = files
    
    # 显示文件表格
    if page_files:
        # 转换为DataFrame
        df_data = []
        for file_info in page_files:
            df_data.append({
                "文件名": file_info['filename'],
                "分类": {
                    "upload": "📁 用户上传",
                    "report": "📄 分析报告",
                    "chart": "📊 图表文件", 
                    "temp": "🗂️ 临时文件"
                }.get(file_info.get('category'), file_info.get('category')),
                "大小": _format_file_size(file_info.get('size', 0)),
                "创建时间": file_info['created_at'].strftime("%Y-%m-%d %H:%M") if isinstance(file_info.get('created_at'), datetime) else str(file_info.get('created_at', '')),
                "文件ID": file_info['id']
            })
        
        df = pd.DataFrame(df_data)
        
        # 显示表格
        selected_rows = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row"
        )
        
        # 批量操作
        st.markdown("#### 批量操作")
        col4, col5, col6, col7 = st.columns(4)
        
        with col4:
            if st.button("🗑️ 删除选中文件"):
                if hasattr(selected_rows, 'selection') and selected_rows.selection.get('rows'):
                    selected_indices = selected_rows.selection['rows']
                    deleted_count = 0
                    
                    for idx in selected_indices:
                        if idx < len(page_files):
                            file_id = page_files[idx]['id']
                            if file_manager.delete_file(file_id):
                                deleted_count += 1
                    
                    if deleted_count > 0:
                        st.success(f"✅ 成功删除 {deleted_count} 个文件")
                        st.rerun()
                else:
                    st.warning("请先选择要删除的文件")
        
        with col5:
            if st.button("📧 添加到邮件模板"):
                if hasattr(selected_rows, 'selection') and selected_rows.selection.get('rows'):
                    selected_indices = selected_rows.selection['rows']
                    st.info(f"已选中 {len(selected_indices)} 个文件，功能开发中...")
                else:
                    st.warning("请先选择文件")

        with col6:
            if st.button("📊 查看详情"):
                if hasattr(selected_rows, 'selection') and selected_rows.selection.get('rows'):
                    selected_indices = selected_rows.selection['rows']
                    if len(selected_indices) == 1:
                        file_info = page_files[selected_indices[0]]
                        _show_file_details(file_info)
                    else:
                        st.warning("请选择单个文件查看详情")
                else:
                    st.warning("请先选择文件")

        with col7:
            if st.button("📧 发送到订阅邮箱"):
                if hasattr(selected_rows, 'selection') and selected_rows.selection.get('rows'):
                    try:
                        from tradingagents.services.subscription.subscription_manager import SubscriptionManager
                        from tradingagents.services.mailer.email_sender import EmailSender
                        sm = SubscriptionManager()
                        es = EmailSender()
                        sent_total = 0
                        for idx in selected_rows.selection['rows']:
                            if idx >= len(page_files):
                                continue
                            fi = page_files[idx]
                            meta = fi.get('metadata') or {}
                            symbol = (meta.get('stock_symbol') or '').upper()
                            # 仅当有股票代码时，向个股订阅发送；否则跳过
                            if not symbol:
                                continue
                            subs = [s for s in sm.get_active_subscriptions(subscription_type='stock') if s.get('symbol') == symbol]
                            recipients = sorted(list({s.get('email') for s in subs if s.get('email')}))
                            if not recipients:
                                continue
                            # 作为附件发送该文件
                            attachments = [{
                                'type': 'file',
                                'path': fi.get('path'),
                                'filename': fi.get('filename')
                            }]
                            # 简要正文
                            analysis_result = {
                                'analysis_date': fi.get('created_at').strftime('%Y-%m-%d') if fi.get('created_at') else '',
                                'decision': {'action': '报告', 'confidence': 0.0, 'risk_score': 0.0, 'reasoning': ''},
                                'full_analysis': f"来自图书馆的报告附件：{fi.get('filename')}"
                            }
                            if es.send_analysis_report(recipients=recipients, stock_symbol=symbol or 'REPORT', analysis_result=analysis_result, attachments=attachments):
                                sent_total += len(recipients)
                        if sent_total:
                            st.success(f"✅ 已向订阅邮箱发送，共 {sent_total} 封")
                        else:
                            st.warning("未找到可发送的订阅或所选文件缺少股票代码元数据")
                    except Exception as e:
                        st.error(f"发送失败: {e}")
                else:
                    st.warning("请先选择文件")


def render_storage_stats(file_manager: FileManager):
    """渲染存储统计界面"""
    
    st.markdown("### 存储统计")
    
    try:
        stats = file_manager.get_storage_stats()
        
        # 总体统计
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 总文件数", stats['total_files'])
            
        with col2:
            st.metric("💾 总存储空间", _format_file_size(stats['total_size']))
            
        with col3:
            st.metric("📁 存储路径", "已设置")
            st.caption(stats['storage_path'])
        
        # 按分类统计
        st.markdown("#### 按分类统计")
        if stats['categories']:
            categories_data = []
            for category, info in stats['categories'].items():
                category_name = {
                    "upload": "📁 用户上传",
                    "report": "📄 分析报告",
                    "chart": "📊 图表文件",
                    "temp": "🗂️ 临时文件"
                }.get(category, category)
                
                categories_data.append({
                    "分类": category_name,
                    "文件数量": info['count'],
                    "存储空间": _format_file_size(info['size'])
                })
            
            df_categories = pd.DataFrame(categories_data)
            st.dataframe(df_categories, use_container_width=True, hide_index=True)
            
            # 可视化图表
            st.markdown("#### 存储空间分布")
            chart_data = pd.DataFrame({
                '分类': [item['分类'] for item in categories_data],
                '大小': [info['size'] for info in stats['categories'].values()]
            })
            st.bar_chart(chart_data.set_index('分类'))
        else:
            st.info("暂无文件统计数据")
            
    except Exception as e:
        st.error(f"❌ 获取统计信息失败: {e}")


def render_file_settings(file_manager: FileManager):
    """渲染文件设置界面"""
    
    st.markdown("### 文件设置")
    
    # 存储设置
    st.markdown("#### 💾 存储设置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        max_file_size = st.number_input(
            "最大文件大小 (MB)",
            min_value=1,
            max_value=100,
            value=10,
            help="单个文件的最大上传大小"
        )
        
        auto_cleanup = st.checkbox(
            "自动清理临时文件",
            value=True,
            help="自动删除过期的临时文件"
        )
        
    with col2:
        cleanup_days = st.number_input(
            "临时文件保留天数",
            min_value=1,
            max_value=30,
            value=7,
            help="临时文件的保留时间"
        )
        
        allowed_types = st.multiselect(
            "允许的文件类型",
            ['pdf', 'docx', 'xlsx', 'png', 'jpg', 'txt', 'md', 'csv'],
            default=['pdf', 'docx', 'xlsx', 'png', 'jpg', 'txt'],
            help="允许上传的文件格式"
        )
    
    # 清理操作
    st.markdown("#### 🧹 存储清理")
    
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("🗑️ 清理临时文件"):
            try:
                deleted_count = file_manager.cleanup_temp_files(cleanup_days * 24)
                st.success(f"✅ 清理了 {deleted_count} 个临时文件")
            except Exception as e:
                st.error(f"❌ 清理失败: {e}")
    
    with col4:
        if st.button("📊 重新计算统计"):
            try:
                # 强制重新加载元数据
                file_manager._load_metadata()
                st.success("✅ 统计信息已更新")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 更新失败: {e}")
    
    # 保存设置
    if st.button("💾 保存设置", type="primary"):
        st.success("✅ 设置已保存")


def _format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    
    return f"{size_bytes:.1f} TB"


def _show_file_details(file_info: Dict):
    """显示文件详情"""
    with st.expander(f"📄 文件详情: {file_info['filename']}", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**文件ID**: `{file_info['id']}`")
            st.write(f"**原始名称**: {file_info.get('original_name', file_info['filename'])}")
            st.write(f"**文件大小**: {_format_file_size(file_info.get('size', 0))}")
            st.write(f"**MIME类型**: {file_info.get('mime_type', '未知')}")
            
        with col2:
            st.write(f"**分类**: {file_info.get('category', '未分类')}")
            st.write(f"**创建时间**: {file_info.get('created_at', '未知')}")
            st.write(f"**文件路径**: `{file_info.get('path', '未知')}`")
            
        # 元数据
        metadata = file_info.get('metadata', {})
        if metadata:
            st.markdown("**元数据**:")
            st.json(metadata)
