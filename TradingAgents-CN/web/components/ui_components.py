"""
统一的UI组件库
提供一致的用户界面组件，确保整个应用的视觉统一性
"""

import streamlit as st
from typing import List, Any, Optional, Union, Dict, Callable


def render_unified_css():
    """渲染统一的CSS样式"""
    st.markdown("""
    <style>
    /* 统一的表单控件样式 */
    .unified-form-container {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
    }
    
    /* 统一的选择框样式 */
    .stSelectbox > div > div {
        background-color: white !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 8px !important;
        min-height: 48px !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stSelectbox > div > div:hover {
        border-color: #3b82f6 !important;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* 统一的选择框内容样式 */
    .stSelectbox [data-baseweb="select"] > div {
        min-height: 44px !important;
        display: flex !important;
        align-items: center !important;
        padding: 0 12px !important;
        font-size: 14px !important;
        color: #374151 !important;
    }
    
    /* 统一的选择框值显示 */
    .stSelectbox [data-baseweb="select"] [data-baseweb="select-value"] {
        color: #111827 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
    }
    
    /* 统一的输入框样式 */
    .stTextInput > div > div > input {
        background-color: white !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 12px !important;
        min-height: 48px !important;
        font-size: 14px !important;
        color: #111827 !important;
        transition: border-color 0.2s ease !important;
        box-sizing: border-box !important;
    }
    
    .stTextInput > div > div > input:hover {
        border-color: #3b82f6 !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        outline: none !important;
    }
    
    /* 统一的日期选择器样式 */
    .stDateInput > div > div > input {
        background-color: white !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 12px !important;
        min-height: 48px !important;
        font-size: 14px !important;
        color: #111827 !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stDateInput > div > div > input:hover {
        border-color: #3b82f6 !important;
    }
    
    .stDateInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* 统一的数字输入框样式 */
    .stNumberInput > div > div > input {
        background-color: white !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 12px !important;
        min-height: 48px !important;
        font-size: 14px !important;
        color: #111827 !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stNumberInput > div > div > input:hover {
        border-color: #3b82f6 !important;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* 统一的多选框样式 */
    .stMultiSelect > div > div {
        background-color: white !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 8px !important;
        min-height: 48px !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stMultiSelect > div > div:hover {
        border-color: #3b82f6 !important;
    }
    
    .stMultiSelect > div > div:focus-within {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* 统一的复选框样式 */
    .stCheckbox {
        margin-bottom: 12px !important;
    }
    
    .stCheckbox > label {
        display: flex !important;
        align-items: center !important;
        font-size: 14px !important;
        color: #374151 !important;
        cursor: pointer !important;
        padding: 8px 0 !important;
    }
    
    .stCheckbox > label > div:first-child {
        margin-right: 8px !important;
    }
    
    /* 统一的按钮样式 */
    .stButton > button {
        background-color: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 24px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        min-height: 48px !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    
    .stButton > button:hover {
        background-color: #2563eb !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* 统一的滑块样式 */
    .stSlider > div > div > div {
        background-color: #f3f4f6 !important;
        border-radius: 8px !important;
        height: 8px !important;
    }
    
    .stSlider > div > div > div > div {
        background-color: #3b82f6 !important;
        border-radius: 8px !important;
    }
    
    /* 统一的展开器样式 */
    .streamlit-expanderHeader {
        background-color: #f8fafc !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 12px 16px !important;
        font-weight: 600 !important;
        color: #374151 !important;
        transition: all 0.2s ease !important;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: #f1f5f9 !important;
        border-color: #3b82f6 !important;
    }
    
    .streamlit-expanderContent {
        border: 2px solid #e5e7eb !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        padding: 16px !important;
        background-color: white !important;
    }
    
    /* 统一的下拉选项列表样式 */
    [data-baseweb="popover"] {
        z-index: 999999 !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1) !important;
        border: 2px solid #e5e7eb !important;
    }
    
    [data-baseweb="menu"] {
        border-radius: 8px !important;
        background-color: white !important;
    }
    
    [data-baseweb="menu"] [data-baseweb="menu-item"] {
        padding: 12px 16px !important;
        font-size: 14px !important;
        color: #374151 !important;
        transition: background-color 0.2s ease !important;
    }
    
    [data-baseweb="menu"] [data-baseweb="menu-item"]:hover {
        background-color: #f3f4f6 !important;
        color: #111827 !important;
    }
    
    [data-baseweb="menu"] [data-baseweb="menu-item"][aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    
    /* 统一的标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px !important;
        background-color: #f8fafc !important;
        padding: 4px !important;
        border-radius: 8px !important;
        border: 2px solid #e5e7eb !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 12px 20px !important;
        border-radius: 6px !important;
        border: none !important;
        background-color: transparent !important;
        color: #6b7280 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        transition: all 0.2s ease !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e5e7eb !important;
        color: #374151 !important;
    }
    
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: white !important;
        color: #3b82f6 !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* 统一的表单布局 */
    .stColumns > div {
        padding: 0 8px !important;
    }
    
    .stColumns > div:first-child {
        padding-left: 0 !important;
    }
    
    .stColumns > div:last-child {
        padding-right: 0 !important;
    }
    
    /* 统一的标题样式 */
    .unified-section-title {
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #111827 !important;
        margin-bottom: 16px !important;
        padding-bottom: 8px !important;
        border-bottom: 2px solid #e5e7eb !important;
    }
    
    .unified-subsection-title {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #374151 !important;
        margin-bottom: 12px !important;
    }
    
    /* 统一的信息提示样式 */
    .stAlert {
        border-radius: 8px !important;
        border: 2px solid !important;
        padding: 12px 16px !important;
        margin: 12px 0 !important;
    }
    
    .stAlert[data-baseweb="notification"] {
        font-size: 14px !important;
    }
    
    /* 成功提示 */
    .stAlert[data-baseweb="notification"][kind="success"] {
        background-color: #f0fdf4 !important;
        border-color: #22c55e !important;
        color: #15803d !important;
    }
    
    /* 警告提示 */
    .stAlert[data-baseweb="notification"][kind="warning"] {
        background-color: #fffbeb !important;
        border-color: #f59e0b !important;
        color: #d97706 !important;
    }
    
    /* 错误提示 */
    .stAlert[data-baseweb="notification"][kind="error"] {
        background-color: #fef2f2 !important;
        border-color: #ef4444 !important;
        color: #dc2626 !important;
    }
    
    /* 信息提示 */
    .stAlert[data-baseweb="notification"][kind="info"] {
        background-color: #eff6ff !important;
        border-color: #3b82f6 !important;
        color: #2563eb !important;
    }
    </style>
    """, unsafe_allow_html=True)


def unified_selectbox(
    label: str,
    options: List[Any],
    index: int = 0,
    key: Optional[str] = None,
    help: Optional[str] = None,
    format_func: Optional[Callable] = None,
    placeholder: Optional[str] = None,
    disabled: bool = False
) -> Any:
    """
    统一的选择框组件
    
    Args:
        label: 标签文本
        options: 选项列表
        index: 默认选中的索引
        key: 组件的唯一键
        help: 帮助文本
        format_func: 格式化函数
        placeholder: 占位符文本
        disabled: 是否禁用
    
    Returns:
        选中的值
    """
    return st.selectbox(
        label=label,
        options=options,
        index=index,
        key=key,
        help=help,
        format_func=format_func,
        placeholder=placeholder,
        disabled=disabled
    )


def unified_text_input(
    label: str,
    value: str = "",
    key: Optional[str] = None,
    help: Optional[str] = None,
    placeholder: Optional[str] = None,
    disabled: bool = False,
    type: str = "default",
    max_chars: Optional[int] = None
) -> str:
    """
    统一的文本输入框组件
    
    Args:
        label: 标签文本
        value: 默认值
        key: 组件的唯一键
        help: 帮助文本
        placeholder: 占位符文本
        disabled: 是否禁用
        type: 输入类型
        max_chars: 最大字符数
    
    Returns:
        输入的文本
    """
    return st.text_input(
        label=label,
        value=value,
        key=key,
        help=help,
        placeholder=placeholder,
        disabled=disabled,
        type=type,
        max_chars=max_chars
    )


def unified_multiselect(
    label: str,
    options: List[Any],
    default: Optional[List[Any]] = None,
    key: Optional[str] = None,
    help: Optional[str] = None,
    format_func: Optional[Callable] = None,
    placeholder: Optional[str] = None,
    disabled: bool = False
) -> List[Any]:
    """
    统一的多选框组件
    
    Args:
        label: 标签文本
        options: 选项列表
        default: 默认选中的值列表
        key: 组件的唯一键
        help: 帮助文本
        format_func: 格式化函数
        placeholder: 占位符文本
        disabled: 是否禁用
    
    Returns:
        选中的值列表
    """
    return st.multiselect(
        label=label,
        options=options,
        default=default or [],
        key=key,
        help=help,
        format_func=format_func,
        placeholder=placeholder,
        disabled=disabled
    )


def unified_checkbox(
    label: str,
    value: bool = False,
    key: Optional[str] = None,
    help: Optional[str] = None,
    disabled: bool = False
) -> bool:
    """
    统一的复选框组件
    
    Args:
        label: 标签文本
        value: 默认值
        key: 组件的唯一键
        help: 帮助文本
        disabled: 是否禁用
    
    Returns:
        复选框状态
    """
    return st.checkbox(
        label=label,
        value=value,
        key=key,
        help=help,
        disabled=disabled
    )


def unified_button(
    label: str,
    key: Optional[str] = None,
    help: Optional[str] = None,
    disabled: bool = False,
    type: str = "primary",
    use_container_width: bool = False
) -> bool:
    """
    统一的按钮组件
    
    Args:
        label: 按钮文本
        key: 组件的唯一键
        help: 帮助文本
        disabled: 是否禁用
        type: 按钮类型
        use_container_width: 是否使用容器宽度
    
    Returns:
        是否被点击
    """
    return st.button(
        label=label,
        key=key,
        help=help,
        disabled=disabled,
        type=type,
        use_container_width=use_container_width
    )


def unified_number_input(
    label: str,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    value: Optional[Union[int, float]] = None,
    step: Optional[Union[int, float]] = None,
    key: Optional[str] = None,
    help: Optional[str] = None,
    disabled: bool = False,
    format: Optional[str] = None
) -> Union[int, float]:
    """
    统一的数字输入框组件
    
    Args:
        label: 标签文本
        min_value: 最小值
        max_value: 最大值
        value: 默认值
        step: 步长
        key: 组件的唯一键
        help: 帮助文本
        disabled: 是否禁用
        format: 格式化字符串
    
    Returns:
        输入的数字
    """
    return st.number_input(
        label=label,
        min_value=min_value,
        max_value=max_value,
        value=value,
        step=step,
        key=key,
        help=help,
        disabled=disabled,
        format=format
    )


def unified_date_input(
    label: str,
    value=None,
    min_value=None,
    max_value=None,
    key: Optional[str] = None,
    help: Optional[str] = None,
    disabled: bool = False
):
    """
    统一的日期选择器组件
    
    Args:
        label: 标签文本
        value: 默认值
        min_value: 最小日期
        max_value: 最大日期
        key: 组件的唯一键
        help: 帮助文本
        disabled: 是否禁用
    
    Returns:
        选择的日期
    """
    return st.date_input(
        label=label,
        value=value,
        min_value=min_value,
        max_value=max_value,
        key=key,
        help=help,
        disabled=disabled
    )


def unified_select_slider(
    label: str,
    options: List[Any],
    value: Any = None,
    key: Optional[str] = None,
    help: Optional[str] = None,
    format_func: Optional[Callable] = None,
    disabled: bool = False
) -> Any:
    """
    统一的选择滑块组件
    
    Args:
        label: 标签文本
        options: 选项列表
        value: 默认值
        key: 组件的唯一键
        help: 帮助文本
        format_func: 格式化函数
        disabled: 是否禁用
    
    Returns:
        选中的值
    """
    return st.select_slider(
        label=label,
        options=options,
        value=value,
        key=key,
        help=help,
        format_func=format_func,
        disabled=disabled
    )


def unified_slider(
    label: str,
    min_value: Union[int, float] = 0,
    max_value: Union[int, float] = 100,
    value: Union[int, float] = 50,
    step: Union[int, float] = 1,
    key: Optional[str] = None,
    help: Optional[str] = None,
    disabled: bool = False,
    format: Optional[str] = None
) -> Union[int, float]:
    """
    统一的滑块组件
    
    Args:
        label: 标签文本
        min_value: 最小值
        max_value: 最大值
        value: 默认值
        step: 步长
        key: 组件的唯一键
        help: 帮助文本
        disabled: 是否禁用
        format: 格式化字符串
    
    Returns:
        滑块的值
    """
    return st.slider(
        label=label,
        min_value=min_value,
        max_value=max_value,
        value=value,
        step=step,
        key=key,
        help=help,
        disabled=disabled,
        format=format
    )


def unified_text_area(
    label: str,
    value: str = "",
    height: Optional[int] = None,
    max_chars: Optional[int] = None,
    key: Optional[str] = None,
    help: Optional[str] = None,
    placeholder: Optional[str] = None,
    disabled: bool = False
) -> str:
    """
    统一的文本区域组件
    
    Args:
        label: 标签文本
        value: 默认值
        height: 高度
        max_chars: 最大字符数
        key: 组件的唯一键
        help: 帮助文本
        placeholder: 占位符文本
        disabled: 是否禁用
    
    Returns:
        输入的文本
    """
    return st.text_area(
        label=label,
        value=value,
        height=height,
        max_chars=max_chars,
        key=key,
        help=help,
        placeholder=placeholder,
        disabled=disabled
    )


def unified_form_container(title: str, content_func: Callable):
    """
    统一的表单容器
    
    Args:
        title: 表单标题
        content_func: 内容渲染函数
    """
    st.markdown(f'<div class="unified-form-container">', unsafe_allow_html=True)
    st.markdown(f'<h3 class="unified-section-title">{title}</h3>', unsafe_allow_html=True)
    content_func()
    st.markdown('</div>', unsafe_allow_html=True)


def unified_section_title(title: str):
    """统一的章节标题"""
    st.markdown(f'<h3 class="unified-section-title">{title}</h3>', unsafe_allow_html=True)


def unified_subsection_title(title: str):
    """统一的子章节标题"""
    st.markdown(f'<h4 class="unified-subsection-title">{title}</h4>', unsafe_allow_html=True)