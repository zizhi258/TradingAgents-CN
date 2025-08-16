import streamlit as st
from typing import List, Any
import os

def render_button_radio(options: List[str], key: str, default_value: Any = None, horizontal: bool = True):
    """
    使用 st.button 创建一个自定义的、外观更好的单选按钮组。

    Args:
        options (List[str]): 按钮选项列表.
        key (str): 用于 session_state 的唯一键.
        default_value (Any, optional): 默认选中的值. Defaults to None.
        horizontal (bool, optional): 是否水平布局. Defaults to True.

    Returns:
        Any: 当前选中的值.
    """
    # 初始化 session_state
    if key not in st.session_state:
        st.session_state[key] = default_value if default_value is not None else options[0]

    # 定义按钮点击的回调函数
    def on_button_click(option: str):
        st.session_state[key] = option

    # 使用列进行水平布局
    if horizontal:
        # 修复：确保列数与选项数匹配
        cols = st.columns(len(options))
        for i, option in enumerate(options):
            with cols[i]:
                # 判断当前按钮是否被选中
                is_selected = (st.session_state[key] == option)
                st.button(
                    label=option,
                    key=f"{key}_{option}",
                    on_click=on_button_click,
                    args=(option,),
                    type="primary" if is_selected else "secondary",
                    use_container_width=True
                )
    else:  # 垂直布局
        for option in options:
            is_selected = (st.session_state[key] == option)
            st.button(
                label=option,
                key=f"{key}_{option}",
                on_click=on_button_click,
                args=(option,),
                type="primary" if is_selected else "secondary",
                use_container_width=True
            )
    
    # 增加调试输出，检查 session_state 的值
    if os.getenv("DEBUG_MODE", "false").lower() == "true":
        st.markdown(f"<small>调试信息: key=`{key}`, value=`{st.session_state.get(key)}`</small>", unsafe_allow_html=True)
            
    return st.session_state[key]