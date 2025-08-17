"""
分析表单组件
"""

import datetime
import os

import streamlit as st

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("web")


def render_analysis_form(simple_mode: bool | None = None):
    """渲染个股分析表单

    Args:
        simple_mode: 若为True则隐藏大部分高级选项，仅保留必要输入。
    """

    st.subheader("📋 分析配置")
    st.caption("选择市场与股票，设定研究深度与分析师团队。")

    # 获取缓存的表单配置（确保不为None）
    cached_config = st.session_state.get("form_config") or {}

    # 调试信息（只在没有分析运行时记录，避免重复）
    if not st.session_state.get("analysis_running", False):
        if cached_config:
            logger.debug(f"📊 [配置恢复] 使用缓存配置: {cached_config}")
        else:
            logger.debug("📊 [配置恢复] 使用默认配置")

    # 创建表单
    with st.form("analysis_form", clear_on_submit=False):

        # 在表单开始时保存当前配置（用于检测变化）
        initial_config = cached_config.copy() if cached_config else {}
        col1, col2 = st.columns(2)

        with col1:
            # 市场选择（使用缓存的值）
            market_options = ["美股", "A股", "港股"]
            cached_market = (
                cached_config.get("market_type", "A股") if cached_config else "A股"
            )
            try:
                market_index = market_options.index(cached_market)
            except (ValueError, TypeError):
                market_index = 1  # 默认A股

            market_type = st.selectbox(
                "选择市场",
                options=market_options,
                index=market_index,
                help="选择要分析的股票市场",
                placeholder="请选择",
            )

            # 根据市场类型显示不同的输入提示
            cached_stock = (
                cached_config.get("stock_symbol", "") if cached_config else ""
            )

            if market_type == "美股":
                stock_symbol = (
                    st.text_input(
                        "股票代码",
                        value=(
                            cached_stock
                            if (
                                cached_config
                                and cached_config.get("market_type") == "美股"
                            )
                            else ""
                        ),
                        placeholder="输入美股代码，如 AAPL, TSLA, MSFT，然后按回车确认",
                        help="输入要分析的美股代码，输入完成后请按回车键确认",
                        key="us_stock_input",
                        autocomplete="off",  # 修复autocomplete警告
                    )
                    .upper()
                    .strip()
                )

                logger.debug(f"🔍 [FORM DEBUG] 美股text_input返回值: '{stock_symbol}'")

            elif market_type == "港股":
                stock_symbol = (
                    st.text_input(
                        "股票代码",
                        value=(
                            cached_stock
                            if (
                                cached_config
                                and cached_config.get("market_type") == "港股"
                            )
                            else ""
                        ),
                        placeholder="输入港股代码，如 0700.HK, 9988.HK, 3690.HK，然后按回车确认",
                        help="输入要分析的港股代码，如 0700.HK(腾讯控股), 9988.HK(阿里巴巴), 3690.HK(美团)，输入完成后请按回车键确认",
                        key="hk_stock_input",
                        autocomplete="off",  # 修复autocomplete警告
                    )
                    .upper()
                    .strip()
                )

                logger.debug(f"🔍 [FORM DEBUG] 港股text_input返回值: '{stock_symbol}'")

            else:  # A股
                stock_symbol = st.text_input(
                    "股票代码",
                    value=(
                        cached_stock
                        if (cached_config and cached_config.get("market_type") == "A股")
                        else ""
                    ),
                    placeholder="输入A股代码，如 000001, 600519，然后按回车确认",
                    help="输入要分析的A股代码，如 000001(平安银行), 600519(贵州茅台)，输入完成后请按回车键确认",
                    key="cn_stock_input",
                    autocomplete="off",  # 修复autocomplete警告
                ).strip()

                logger.debug(f"🔍 [FORM DEBUG] A股text_input返回值: '{stock_symbol}'")

            # 分析日期
            analysis_date = st.date_input(
                "分析日期", value=datetime.date.today(), help="选择分析的基准日期"
            )

        with col2:
            # 研究深度（使用缓存的值）
            cached_depth = (
                cached_config.get("research_depth", 3) if cached_config else 3
            )
            research_depth = st.select_slider(
                "研究深度",
                options=[1, 2, 3, 4, 5],
                value=cached_depth,
                format_func=lambda x: {
                    1: "1级 - 快速分析",
                    2: "2级 - 基础分析",
                    3: "3级 - 标准分析",
                    4: "4级 - 深度分析",
                    5: "5级 - 全面分析",
                }[x],
                help="选择分析的深度级别，级别越高分析越详细但耗时更长",
            )

        # 统一：单模型页与多模型/市场分析使用同一套专业智能体角色
        # 选择角色 → 自动映射为单模型可识别的基础分析师键，并记录扩展角色用于结果展示
        selected_agents: list[str] = []
        chosen_ext: list[str] = []
        try:
            # 动态加载角色定义（优先后端定义）
            try:
                from tradingagents.config.provider_models import model_provider_manager

                _defs = model_provider_manager.role_definitions
                roles_config = []
                for rk, rc in _defs.items():
                    if getattr(rc, "enabled", True):
                        roles_config.append(
                            (rk, rc.name or rk, rc.description or rc.name or rk)
                        )
                roles_config.sort(key=lambda x: x[1])
            except Exception:
                # 回退：静态角色定义；按环境变量控制“绘图师”是否展示
                roles_config = [
                    ("news_hunter", "📰 快讯猎手", "实时新闻收集与分析"),
                    ("fundamental_expert", "💰 基本面专家", "财务数据与估值分析"),
                    ("technical_analyst", "📈 技术分析师", "技术指标与图表分析"),
                    ("sentiment_analyst", "💭 情绪分析师", "市场情绪与社媒分析"),
                    ("risk_manager", "⚠️ 风控经理", "风险评估与管理"),
                    ("compliance_officer", "📋 合规官", "合规性检查"),
                    ("policy_researcher", "📋 政策研究员", "政策法规解读分析"),
                    ("tool_engineer", "🔧 工具工程师", "量化工具与代码生成"),
                    ("chief_decision_officer", "👔 首席决策官", "最终决策仲裁"),
                ]
                try:
                    if os.getenv("CHARTING_ARTIST_ENABLED", "false").lower() in (
                        "1",
                        "true",
                        "yes",
                        "on",
                    ):
                        roles_config.append(
                            ("charting_artist", "🎨 绘图师", "生成可交互金融图表")
                        )
                except Exception:
                    pass

            st.markdown("### 👥 专业智能体团队")
            st.caption("单模型/多模型/市场分析统一使用同一套角色标签。")

            cached_agents = (
                cached_config.get("selected_agents", []) if cached_config else []
            )
            if (
                (simple_mode is None and st.session_state.get("SIMPLE_MODE_DEFAULT"))
                or simple_mode is True
            ) and not cached_agents:
                cached_agents = ["news_hunter", "fundamental_expert", "risk_manager"]
                st.info("已按简化模式预选：快讯猎手/基本面专家/风控经理。")

            col1, col2, col3 = st.columns(3)
            roles_per_col = len(roles_config) // 3 + (1 if len(roles_config) % 3 else 0)
            for col_idx, col in enumerate([col1, col2, col3]):
                start_idx = col_idx * roles_per_col
                end_idx = min(start_idx + roles_per_col, len(roles_config))
                with col:
                    for role_key, role_label, role_desc in roles_config[start_idx:end_idx]:
                        checked = st.checkbox(
                            role_label,
                            value=(role_key in cached_agents),
                            key=f"single_role_{role_key}",
                            help=role_desc,
                        )
                        if checked:
                            selected_agents.append(role_key)

            # 将选择的专业角色映射为单模型可识别分析师键
            from web.utils.roles_registry import map_role_to_single_model_key

            mapped_needed: set[str] = set()
            mapping_origins: dict[str, set[str]] = {
                "market": set(),
                "fundamentals": set(),
                "news": set(),
                "social": set(),
            }
            for r in selected_agents:
                mapped = map_role_to_single_model_key(r)
                if mapped in {"market", "fundamentals", "news", "social"}:
                    mapped_needed.add(mapped)
                    try:
                        mapping_origins[mapped].add(r)
                    except Exception:
                        pass
                else:
                    pass

            # 构造用于后端的分析师键+显示名称
            key_to_label = {
                "market": "市场分析师",
                "fundamentals": "基本面分析师",
                "news": "新闻分析师",
                "social": "社交媒体分析师",
            }
            # 标注“（兼容）”：当基础分析师键仅因扩展角色映射而被加入时
            base_direct_role_for = {
                "market": "technical_analyst",
                "fundamentals": "fundamental_expert",
                "news": "news_hunter",
                "social": "sentiment_analyst",
            }
            compat_added: set[str] = set()
            try:
                for k in list(mapped_needed):
                    direct_role = base_direct_role_for.get(k)
                    # 若未直接勾选对应基础角色，但存在其它角色映射到该基础键，则标记为兼容
                    if direct_role and (direct_role not in selected_agents):
                        origins = mapping_origins.get(k) or set()
                        # origins 中若存在非 direct_role 的来源，则认为是兼容映射加入
                        if any(o != direct_role for o in origins):
                            compat_added.add(k)
            except Exception:
                pass

            selected_analysts = []
            for k in sorted(mapped_needed):
                label = key_to_label[k] + ("（兼容）" if k in compat_added else "")
                selected_analysts.append((k, label))

            # 统一记录扩展角色（含会映射到基础分析师的角色如政策/工具），用于展示与后处理
            try:
                base_role_keys = {
                    "news_hunter",
                    "fundamental_expert",
                    "technical_analyst",
                    "sentiment_analyst",
                }
                chosen_ext = [r for r in selected_agents if r not in base_role_keys]
            except Exception:
                pass

            if selected_agents:
                st.success(
                    f"✅ 已选择 {len(selected_agents)} 个专业智能体: {', '.join(selected_agents)}"
                )
                try:
                    if compat_added:
                        _auto = ", ".join(
                            [key_to_label[k] + "（兼容）" for k in sorted(compat_added)]
                        )
                        st.info(f"已自动包含基础分析师用于兼容展示：{_auto}")
                except Exception:
                    pass
            else:
                st.warning("请至少选择一个角色")
        except Exception:
            # 降级为原始四类
            selected_analysts = [
                ("market", "市场分析师"),
                ("fundamentals", "基本面分析师"),
                ("news", "新闻分析师"),
            ]
            chosen_ext = []

        # 高级选项
        with st.expander("🔧 高级选项（可选）"):
            include_sentiment = st.checkbox(
                "包含社交媒体情绪分析",
                value=True,
                help="与勾选‘社交媒体分析师’等效：开启将自动包含‘社交’分析维度；关闭将移除",
            )

            include_risk_assessment = st.checkbox(
                "显示风险评估分区",
                value=True,
                help="控制结果页是否显示‘风险评估’分区（不影响后端执行，仅影响展示）",
            )

            custom_prompt = st.text_area(
                "自定义分析要求",
                placeholder="输入特定的分析要求或关注点...",
                help="提示模型关注特定要点（单模型路径下作为上下文参考）",
            )

        # 显示输入状态提示
        if not stock_symbol:
            st.info("💡 请在上方输入股票代码，输入完成后按回车键确认")
        else:
            st.success(f"✅ 已输入股票代码: {stock_symbol}")

        # 添加JavaScript来改善用户体验
        st.markdown(
            """
        <script>
        // 监听输入框的变化，提供更好的用户反馈（使用主题主色）
        document.addEventListener('DOMContentLoaded', function() {
            const inputs = document.querySelectorAll('input[type="text"]');
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    const accent = getComputedStyle(document.body).getPropertyValue('--zen-accent') || '#0EA5A4';
                    if (this.value.trim()) {
                        this.style.borderColor = accent.trim();
                        this.title = '按回车键确认输入';
                    } else {
                        this.style.borderColor = '';
                        this.title = '';
                    }
                });
            });
        });
        </script>
        """,
            unsafe_allow_html=True,
        )

        # 在提交按钮前检测配置变化并保存
        # 将‘包含社交媒体情绪分析’与分析师选择对齐
        try:
            if include_sentiment and (
                "social" not in [a[0] for a in selected_analysts]
            ):
                selected_analysts.append(("social", "社交媒体分析师"))
            if (not include_sentiment) and selected_analysts:
                selected_analysts = [a for a in selected_analysts if a[0] != "social"]
        except Exception:
            pass

        # 记录展示偏好：风险评估是否显示
        try:
            st.session_state["ui_show_risk_assessment"] = bool(include_risk_assessment)
        except Exception:
            pass

        current_config = {
            "stock_symbol": stock_symbol,
            "market_type": market_type,
            "research_depth": research_depth,
            "selected_analysts": [a[0] for a in selected_analysts],
            # 统一角色选择（用于跨页面共享与展示）
            "selected_agents": selected_agents,
            "include_sentiment": include_sentiment,
            "include_risk_assessment": include_risk_assessment,
            "custom_prompt": custom_prompt,
            # 额外：扩展角色（用于结果展示与轻量补齐）
            "extended_roles": chosen_ext,
        }

        # 如果配置发生变化，立即保存（即使没有提交）
        if current_config != initial_config:
            st.session_state.form_config = current_config
            try:
                from utils.smart_session_manager import smart_session_manager

                current_analysis_id = st.session_state.get(
                    "current_analysis_id", "form_config_only"
                )
                smart_session_manager.save_analysis_state(
                    analysis_id=current_analysis_id,
                    status=st.session_state.get("analysis_running", False)
                    and "running"
                    or "idle",
                    stock_symbol=stock_symbol,
                    market_type=market_type,
                    form_config=current_config,
                )
                logger.debug("📊 [配置自动保存] 表单配置已更新")
            except Exception as e:
                logger.warning(f"⚠️ [配置自动保存] 保存失败: {e}")

        # 提交按钮（不禁用，让用户可以点击）
        cols_btn = st.columns([3, 1])
        with cols_btn[0]:
            submitted = st.form_submit_button(
                "🚀 开始分析", type="primary", use_container_width=True
            )
        with cols_btn[1]:
            st.form_submit_button("重置", type="secondary")

    # 只有在提交时才返回数据
    if submitted and stock_symbol:  # 确保有股票代码才提交
        # 添加详细日志
        logger.debug("🔍 [FORM DEBUG] ===== 分析表单提交 =====")
        logger.debug(f"🔍 [FORM DEBUG] 用户输入的股票代码: '{stock_symbol}'")
        logger.debug(f"🔍 [FORM DEBUG] 市场类型: '{market_type}'")
        logger.debug(f"🔍 [FORM DEBUG] 分析日期: '{analysis_date}'")
        logger.debug(
            f"🔍 [FORM DEBUG] 选择的分析师: {[a[0] for a in selected_analysts]}"
        )
        logger.debug(f"🔍 [FORM DEBUG] 研究深度: {research_depth}")

        form_data = {
            "submitted": True,
            "stock_symbol": stock_symbol,
            "market_type": market_type,
            "analysis_date": str(analysis_date),
            "analysts": [a[0] for a in selected_analysts],
            "selected_agents": selected_agents,
            "research_depth": research_depth,
            "include_sentiment": include_sentiment,
            "include_risk_assessment": include_risk_assessment,
            "custom_prompt": custom_prompt,
            "extended_roles": chosen_ext,
        }

        # 保存表单配置到缓存和持久化存储
        form_config = {
            "stock_symbol": stock_symbol,
            "market_type": market_type,
            "research_depth": research_depth,
            "selected_analysts": [a[0] for a in selected_analysts],
            "selected_agents": selected_agents,
            "include_sentiment": include_sentiment,
            "include_risk_assessment": include_risk_assessment,
            "custom_prompt": custom_prompt,
            "extended_roles": chosen_ext,
        }
        st.session_state.form_config = form_config

        # 保存到持久化存储
        try:
            from utils.smart_session_manager import smart_session_manager

            # 获取当前分析ID（如果有的话）
            current_analysis_id = st.session_state.get(
                "current_analysis_id", "form_config_only"
            )
            smart_session_manager.save_analysis_state(
                analysis_id=current_analysis_id,
                status=st.session_state.get("analysis_running", False)
                and "running"
                or "idle",
                stock_symbol=stock_symbol,
                market_type=market_type,
                form_config=form_config,
            )
        except Exception as e:
            logger.warning(f"⚠️ [配置持久化] 保存失败: {e}")

        logger.info(f"📊 [配置缓存] 表单配置已保存: {form_config}")

        logger.debug(f"🔍 [FORM DEBUG] 返回的表单数据: {form_data}")
        logger.debug("🔍 [FORM DEBUG] ===== 表单提交结束 =====")

        return form_data
    elif submitted and not stock_symbol:
        # 用户点击了提交但没有输入股票代码
        logger.error("🔍 [FORM DEBUG] 提交失败：股票代码为空")
        st.error("❌ 请输入股票代码后再提交")
        return {"submitted": False}
    else:
        return {"submitted": False}
