#!/usr/bin/env python3
"""
角色库管理页面

提供角色的增删改查、模型限制与提示词模板（system/analysis）编辑，持久化到 config/role_library.json。
编辑保存后会即时调用 ModelProviderManager.reload_role_library() 生效。
"""

from __future__ import annotations

import streamlit as st
from typing import Dict, Any, List

from tradingagents.config.provider_models import (
    model_provider_manager,
    ROLE_DEFINITIONS,
)
from tradingagents.config.role_library import (
    load_role_library,
    upsert_role,
    delete_role,
    save_role_library,
    fill_missing_prompts_in_library,
    overwrite_prompts_with_defaults,
)


def _all_model_names() -> List[str]:
    return list(model_provider_manager.model_catalog.keys())


def _load_all_roles() -> Dict[str, Any]:
    # 基于当前管理器视图（合并内置与自定义）
    merged: Dict[str, Any] = {}
    for k, v in model_provider_manager.role_definitions.items():
        merged[k] = {
            'name': v.name,
            'description': v.description,
            'allowed_models': list(v.allowed_models),
            'preferred_model': v.preferred_model,
            'locked_model': v.locked_model,
            'enabled': getattr(v, 'enabled', True),
        }
    # 合并库中的 prompts 与 task_type
    lib = load_role_library()
    for k, cfg in lib.get('roles', {}).items():
        merged.setdefault(k, {})
        merged[k].update({
            'name': cfg.get('name') or merged[k].get('name') or k,
            'description': cfg.get('description') or merged[k].get('description') or '',
            'allowed_models': cfg.get('allowed_models') or merged[k].get('allowed_models') or [],
            'preferred_model': cfg.get('preferred_model') or merged[k].get('preferred_model'),
            'locked_model': cfg.get('locked_model') or merged[k].get('locked_model'),
            'enabled': cfg.get('enabled') if cfg.get('enabled') is not None else merged[k].get('enabled', True),
            'prompts': cfg.get('prompts') or {},
            'task_type': cfg.get('task_type') or '',
        })
    return merged


def render_role_library():
    st.title("🧰 角色库")
    st.caption("管理内置与自定义角色：模型限制、默认模型、锁定模型、提示词模板等")

    # 快捷刷新（强制从磁盘重载角色库与覆盖）
    col_top1, col_top2 = st.columns([1, 6])
    with col_top1:
        if st.button("🔄 重新加载角色库"):
            try:
                model_provider_manager.reload_role_library()
                st.success("已从磁盘重新加载角色库与覆盖项。")
                try:
                    st.rerun()
                except Exception:
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"重载失败: {e}")

    roles = _load_all_roles()
    all_role_keys = sorted(roles.keys())

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("### 角色列表")
        builtin_keys = set(ROLE_DEFINITIONS.keys())
        # 使用中文显示名称作为展示，但内部值仍为角色key，避免歧义
        selected_key = st.selectbox(
            "选择角色",
            all_role_keys,
            key="role_lib_select",
            format_func=lambda k: (roles.get(k, {}).get('name') or k)
        )
        # 内置角色标识与提示
        if selected_key in builtin_keys:
            st.markdown(
                "<div style='color:#c92a2a; font-weight:600;'>内置角色（谨慎处理）</div>",
                unsafe_allow_html=True,
            )
        new_role = st.text_input("新建角色key", value="", placeholder="如: sector_specialist")
        if st.button("➕ 新建"):
            if new_role and new_role not in roles:
                upsert_role(new_role, {
                    'name': new_role,
                    'description': '',
                    'allowed_models': [],
                    'preferred_model': None,
                    'locked_model': None,
                    'enabled': True,
                    'prompts': {},
                    'task_type': '',
                })
                model_provider_manager.reload_role_library()
                st.success(f"已创建角色: {new_role}")
                try:
                    st.rerun()
                except Exception:
                    st.experimental_rerun()
            else:
                st.warning("请输入唯一的新角色key")

        # 删除/清除按钮（区分内置与自定义）
        lib = load_role_library()
        lib_roles = lib.get('roles', {}) if isinstance(lib.get('roles'), dict) else {}
        if selected_key in builtin_keys:
            # 内置角色：仅允许清除自定义覆盖
            if st.button("🧹 清除自定义覆盖"):
                if selected_key in lib_roles:
                    delete_role(selected_key)
                    model_provider_manager.reload_role_library()
                    st.success(f"已清除覆盖: {selected_key}")
                    try:
                        st.rerun()
                    except Exception:
                        st.experimental_rerun()
                else:
                    st.info("该内置角色未被覆盖，无需清除。")
        else:
            if st.button("🗑️ 删除所选"):
                if selected_key in roles:
                    delete_role(selected_key)
                    model_provider_manager.reload_role_library()
                    st.success(f"已删除角色: {selected_key}")
                    try:
                        st.rerun()
                    except Exception:
                        st.experimental_rerun()

    with c2:
        st.markdown("### 编辑角色")
        if not all_role_keys:
            st.info("暂无角色")
            return

        rk = selected_key
        cfg = roles.get(rk, {})

        # 若为内置角色，给出显著提示（标红）
        if rk in set(ROLE_DEFINITIONS.keys()):
            st.markdown(
                "<div style='padding:6px 10px;border:1px solid #ffe3e3;background:#fff5f5;color:#c92a2a;border-radius:8px;'>"
                "⚠️ 内置角色：删除仅会清除自定义覆盖，无法移除内置定义；如需停用，请取消勾选“启用该角色”。"
                "</div>",
                unsafe_allow_html=True,
            )
            st.write("")

        with st.form("role_edit_form", clear_on_submit=False):
            name = st.text_input("显示名称", value=cfg.get('name') or rk)
            desc = st.text_area("描述", value=cfg.get('description') or '')
            task_type = st.selectbox(
                "任务类型",
                ["", "fundamental_analysis", "technical_analysis", "news_analysis", "sentiment_analysis", "policy_analysis", "risk_assessment", "compliance_check", "decision_making", "general"],
                index=0 if not cfg.get('task_type') else ["", "fundamental_analysis", "technical_analysis", "news_analysis", "sentiment_analysis", "policy_analysis", "risk_assessment", "compliance_check", "decision_making", "general"].index(cfg.get('task_type'))
            )

            models_all = _all_model_names()
            allowed = st.multiselect("允许模型", models_all, default=cfg.get('allowed_models') or [])
            preferred = st.selectbox("首选模型", ["(无)"] + allowed, index= ( ["(无)"] + allowed ).index(cfg.get('preferred_model')) if cfg.get('preferred_model') in allowed else 0 )
            locked = st.selectbox("锁定模型", ["(无)"] + allowed, index= ( ["(无)"] + allowed ).index(cfg.get('locked_model')) if cfg.get('locked_model') in allowed else 0 )

            enabled = st.checkbox("启用该角色", value=bool(cfg.get('enabled', True)))

            prompts = cfg.get('prompts') or {}
            sys_prompt = st.text_area("System Prompt（系统提示）", value=prompts.get('system_prompt') or '', height=180)
            analysis_prompt = st.text_area("Analysis Prompt 模板（可选）", value=prompts.get('analysis_prompt_template') or '', height=160)

            save = st.form_submit_button("💾 保存")
            if save:
                data = load_role_library()
                roles_lib = data.get('roles', {})
                roles_lib[rk] = {
                    'name': name,
                    'description': desc,
                    'task_type': task_type or '',
                    'allowed_models': allowed,
                    'preferred_model': (None if preferred == "(无)" else preferred),
                    'locked_model': (None if locked == "(无)" else locked),
                    'enabled': bool(enabled),
                    'prompts': {
                        'system_prompt': sys_prompt,
                        'analysis_prompt_template': analysis_prompt,
                    }
                }
                data['roles'] = roles_lib
                upsert_role(rk, roles_lib[rk])
                model_provider_manager.reload_role_library()
                st.success("已保存并应用。")

        # 单个角色的“恢复为推荐模板”按钮
        col_r1, _ = st.columns([1, 3])
        with col_r1:
            if st.button("🧭 用推荐模板覆盖该角色"):
                try:
                    from tradingagents.config.role_library import overwrite_prompts_with_defaults
                    cnt = overwrite_prompts_with_defaults([rk])
                    model_provider_manager.reload_role_library()
                    if cnt:
                        st.success("已使用推荐模板覆盖该角色提示词。")
                    else:
                        st.info("没有可覆盖的目标（该角色未在角色库中或无默认模板）。")
                except Exception as e:
                    st.error(f"操作失败: {e}")

    # ===== 导入 / 导出 =====
    with st.expander("📦 导入 / 导出", expanded=False):
        sub_c1, sub_c2 = st.columns(2)
        with sub_c1:
            st.markdown("**导出角色库**")
            lib = load_role_library()
            import json as _json
            json_bytes = _json.dumps(lib, ensure_ascii=False, indent=2).encode('utf-8')
            st.download_button(
                label="⬇️ 导出为 JSON",
                data=json_bytes,
                file_name="role_library.json",
                mime="application/json",
            )
            try:
                import yaml as _yaml  # type: ignore
                yaml_str = _yaml.safe_dump(lib, allow_unicode=True, sort_keys=False)
                st.download_button(
                    label="⬇️ 导出为 YAML",
                    data=yaml_str.encode('utf-8'),
                    file_name="role_library.yaml",
                    mime="text/yaml",
                )
            except Exception:
                st.info("未安装 PyYAML，暂不提供 YAML 导出。")

        with sub_c2:
            st.markdown("**导入角色库**")
            uploaded = st.file_uploader("上传 JSON 或 YAML 文件", type=["json", "yaml", "yml"], key="role_lib_uploader")
            merge_strategy = st.radio("合并策略", ["合并（同名覆盖）", "替换全部"], horizontal=True)
            if st.button("📤 导入并应用", type="primary"):
                if not uploaded:
                    st.warning("请先选择文件")
                else:
                    try:
                        content = uploaded.read().decode('utf-8')
                        data = None
                        import json as _json
                        try:
                            data = _json.loads(content)
                        except Exception:
                            try:
                                import yaml as _yaml  # type: ignore
                                data = _yaml.safe_load(content)
                            except Exception:
                                data = None
                        if not isinstance(data, dict):
                            st.error("文件格式不正确")
                        else:
                            current = load_role_library()
                            if merge_strategy == "替换全部":
                                save_role_library(data)
                            else:
                                roles_cur = current.get('roles', {}) if isinstance(current.get('roles'), dict) else {}
                                roles_new = data.get('roles', {}) if isinstance(data.get('roles'), dict) else {}
                                merged = roles_cur.copy()
                                merged.update(roles_new)
                                save_role_library({'roles': merged})
                            model_provider_manager.reload_role_library()
                            st.success("导入完成并已应用。")
                    except Exception as e:
                        st.error(f"导入失败: {e}")

    # ===== 默认模板工具 =====
    with st.expander("🧩 默认模板工具", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔧 补齐缺失模板（不覆盖）"):
                try:
                    changed = fill_missing_prompts_in_library()
                    model_provider_manager.reload_role_library()
                    if changed:
                        st.success("已为缺失的角色模板补齐默认值。")
                    else:
                        st.info("无需更改，模板已完整。")
                except Exception as e:
                    st.error(f"操作失败: {e}")
        with col_b:
            if st.button("⚠️ 用默认模板覆盖（危险）"):
                try:
                    count = overwrite_prompts_with_defaults()
                    model_provider_manager.reload_role_library()
                    st.success(f"已覆盖 {count} 个角色的模板。")
                except Exception as e:
                    st.error(f"操作失败: {e}")
