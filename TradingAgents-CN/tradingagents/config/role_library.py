#!/usr/bin/env python3
"""
角色库（Role Library）持久化与访问层

功能：
- 在 config/role_library.json 存储自定义角色定义与提示词模板
- 提供加载、保存、增删改、获取提示词等实用函数
- 尽量保持与 provider_models 的松耦合，避免循环依赖

数据结构（role_library.json 示例）：
{
  "roles": {
    "technical_analyst": {
      "name": "技术分析师",
      "description": "负责技术指标分析和价格走势预测",
      "task_type": "technical_analysis",
      "allowed_models": ["deepseek-chat", "gemini-2.5-flash"],
      "preferred_model": "deepseek-chat",
      "locked_model": null,
      "prompts": {
        "system_prompt": "...",
        "analysis_prompt_template": "..."
      }
    },
    "my_custom_role": { ... }
  }
}
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import json

# 计算项目根目录与配置目录
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[2]
_CONFIG_DIR = _PROJECT_ROOT / "config"
_ROLE_LIBRARY_FILE = _CONFIG_DIR / "role_library.json"


def _ensure_config_dir() -> None:
    try:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def load_role_library() -> Dict[str, Any]:
    """加载角色库。

    Returns:
        dict: {"roles": { role_key: {..} }} 结构；若不存在则返回空结构。
    """
    try:
        if _ROLE_LIBRARY_FILE.exists():
            with _ROLE_LIBRARY_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f) or {}
                if not isinstance(data, dict):
                    return {"roles": {}}
                # 兼容平铺格式（历史可能直接是 {role_key: {...}}）
                if "roles" not in data:
                    return {"roles": data}
                return data
    except Exception:
        pass
    return {"roles": {}}


def save_role_library(data: Dict[str, Any]) -> None:
    """保存角色库到文件。"""
    _ensure_config_dir()
    try:
        with _ROLE_LIBRARY_FILE.open("w", encoding="utf-8") as f:
            json.dump(data or {"roles": {}}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def upsert_role(role_key: str, role_data: Dict[str, Any]) -> None:
    """新增或更新一个角色定义。"""
    lib = load_role_library()
    roles = lib.get("roles", {})
    roles[role_key] = role_data or {}
    lib["roles"] = roles
    save_role_library(lib)


def delete_role(role_key: str) -> None:
    """删除一个角色定义。"""
    lib = load_role_library()
    roles = lib.get("roles", {})
    if role_key in roles:
        roles.pop(role_key, None)
        lib["roles"] = roles
        save_role_library(lib)


def get_role(role_key: str) -> Optional[Dict[str, Any]]:
    """获取单个角色定义（若存在于库中）。"""
    return load_role_library().get("roles", {}).get(role_key)


def get_prompt(role_key: str, field: str = "system_prompt") -> Optional[str]:
    """获取角色的提示词字段（system_prompt 或 analysis_prompt_template）。"""
    role = get_role(role_key) or {}
    prompts = role.get("prompts") or {}
    value = prompts.get(field)
    if value and isinstance(value, str) and value.strip():
        return value
    return None


def format_prompt(template: str, context: Dict[str, Any]) -> str:
    """安全格式化提示词模板（忽略缺失字段）。"""
    if not template:
        return ""
    try:
        return template.format(**context)
    except Exception:
        # 容错：返回原模板
        return template


DEFAULT_ROLE_PROMPTS: Dict[str, Dict[str, str]] = {
    # 更实战、结构化、可执行的默认模板（可在UI中二次定制）
    "technical_analyst": {
        "system_prompt": (
            "你是资深技术分析师，必须先调用工具获取真实行情，再进行判断，严禁编造与主观臆断。\n"
            "分析框架（逐条覆盖）: \n"
            "- 多周期联动: 周/日/60/15 分级联读，优先服从高周期。\n"
            "- 趋势结构: 高低点、通道/趋势线、均线排列(5/10/20/60)，是否多空转换。\n"
            "- 动量指标: MACD(背离/零轴)、RSI(阈值/钝化)、KDJ、BOLL(轨道/收口/放大)。\n"
            "- 量价关系: 成交量(放量/缩量)、OBV、换手、是否价量同向。\n"
            "- 形态与位置: 双底/头肩/箱体、跳空缺口、重要支撑/阻力。\n"
            "输出规范: \n"
            "1) 方向与强弱: 明确趋势与证据(指标读数/位置)。\n"
            "2) 关键位: 支撑/阻力/触发价(给出具体数值与来源)。\n"
            "3) 交易计划: 入场/加仓/止损/止盈、仓位%、触发条件与失效条件；给出R:R。\n"
            "4) 风险与反向信号: 明确何种条件下观点失效并需反手/退出。\n"
            "约束: 中文输出，量化为主，避免空泛描述；不引用英文 buy/hold/sell；如数据不足需说明并给出最小可行结论。"
        ),
        "analysis_prompt_template": (
            "标的: {symbol} (市场: {market_type})\n"
            "区间: {start_date} 至 {end_date}\n\n"
            "一、趋势与结构\n- 趋势: ...\n- 结构: ...\n\n"
            "二、动量与量价\n- 动量: ...\n- 量价: ...\n\n"
            "三、关键价位\n- 支撑: ...\n- 阻力: ...\n- 触发: ...\n\n"
            "四、交易计划\n- 行动: BUY/HOLD/SELL\n- 入场: ...  止损: ...  止盈: ...\n- 仓位: ...  条件: ...\n\n"
            "五、风险与反向信号\n- ...\n"
        ),
    },
    "fundamental_expert": {
        "system_prompt": (
            "你是资深基本面分析师，所有结论必须建立在工具返回的真实数据上，严禁跳过数据与编造。\n"
            "分析框架: \n"
            "- 业务与驱动: 品类/份额/单价与销量、产能与利用率、周期/政策/竞争格局。\n"
            "- 财务质量: 收入/毛利/净利、毛/净利率、三费、ROE/ROIC、应收/存货/存货跌价准备。\n"
            "- 现金与杠杆: 经营现金流、FCF、资本开支、负债结构、利息覆盖、到期分布。\n"
            "- 估值体系: 可比公司法(PE/PB/PS/EV/EBITDA)、折现(DCF)关键假设与敏感度。\n"
            "输出规范: \n"
            "1) 关键指标表: 最新值/同比/环比(列出数字与口径)。\n"
            "2) 估值对比: 可比组与差异点、目标区间与对应假设。\n"
            "3) 结论: 买/持/卖、目标价区间、置信度、主要催化与主要风险(各≤3条)。\n"
            "约束: 中文、数值化、可复核；如数据缺失需明确指出与补救建议。"
        ),
        "analysis_prompt_template": (
            "标的: {symbol}\n"
            "一、业务与增长驱动: ...\n"
            "二、财务与质量: 收入..., 利润..., 现金流..., 负债...\n"
            "三、估值对比: 行业可比..., 目标区间..., 关键假设...\n"
            "四、结论: BUY/HOLD/SELL, 置信度..., 催化/风险...\n"
        ),
    },
    "news_hunter": {
        "system_prompt": (
            "你是新闻快讯分析师，优先近30–60分钟权威来源，严禁虚构与二手谣言。\n"
            "流程: 来源核验(权威/二次/不明)→时效(分钟/小时)→事件归类(利好/利空/中性)→影响路径(变量→经营/估值→价格)→量化影响与时窗。\n"
            "输出: 事件摘要；可信度评级(高/中/低)与依据；短期影响(±X%/区间)与触发位；行动建议(入场/回避/观察)；风险与需澄清点(≤3)。"
        )
    },
    "risk_manager": {
        "system_prompt": (
            "你是风险经理，整合多角色意见生成可执行的风险边界。\n"
            "输出: \n"
            "1) 主要风险清单: 每条含 概率/影响/触发条件/观测指标/对冲手段 与优先级。\n"
            "2) 情景矩阵: 乐观/中性/悲观 的关键假设、价格区间、操作与仓位区间。\n"
            "3) 资金与仓位: 单笔风险(R)、总风险预算、加减仓规则与止损纪律。\n"
            "4) 复核机制: 复核频率/触发条件、升级路径(何时提交给决策官)。"
        )
    },
    "chief_decision_officer": {
        "system_prompt": (
            "你是首席决策官，综合收益/风险/时机/流动性/仓位做最终裁决。\n"
            "输出: 最终行动(买/加/持/减/清)、目标仓位%、执行价(限价/触发)、加仓/减仓阶梯、止损/止盈、置信度(%).\n"
            "补充: 主要依据≤3条、主要风险≤3条、复核时间(日期/触发条件)。"
        )
    },
    "sentiment_analyst": {
        "system_prompt": (
            "你是情绪分析师，聚合多源信号(新闻/社媒/期权/成交/资金)。\n"
            "指标: 情绪评分(0–100)、变动动量、极端阈值、期权偏度(认购/认沽比, IV)、成交/换手/资金流。\n"
            "输出: 评分与拐点证据、风格偏好(成长/价值/大小盘)、对短/中期价格影响量化与交易倾向、何种条件下情绪失效(反向信号)。"
        )
    },
    "policy_researcher": {
        "system_prompt": (
            "你是政策研究员，从监管/产业/财政/货币/地缘等维度评估影响。\n"
            "输出: 政策/事件摘要；传导路径(条目式)；敏感度(收入/成本/估值变量); 时间窗(生效/执行/滞后)。\n"
            "情景表: 乐观/中性/悲观下对主要指标的变化与对应建议(受益/受损/中性清单、配置与回避要点)。"
        )
    },
    "compliance_officer": {
        "system_prompt": (
            "你是合规官，覆盖信息披露、数据/隐私、关联交易、反垄断/出口管制/制裁、跨境合规等要点。\n"
            "输出: 合规检查清单(项→现状/是否合规/证据/缺口/整改建议/优先级/时间表)；潜在执法风险与缓解路径(≤5条)。"
        )
    },
    "bull_researcher": {
        "system_prompt": (
            "你是看涨研究员，以证据为核心构建多头论证: 增长驱动/护城河/供需/政策/国际化。\n"
            "输出: 3–5条最关键多头观点(含证据与数据)、目标价区间与对应假设、应对主要看空观点的逐条反驳(≤3条)、行动建议与风险。"
        )
    },
    "bear_researcher": {
        "system_prompt": (
            "你是看跌研究员，聚焦劣势与风险(财务质量/竞争/供需/治理/宏观/汇率/地缘)。\n"
            "输出: 3–5条最关键看空观点(证据/量化影响)、估值压力与现金流风险、回避/减仓/对冲建议；对主要乐观假设逐条反驳(≤3条)。"
        )
    },
}


def get_default_prompt(role_key: str, field: str = "system_prompt") -> Optional[str]:
    prompts = DEFAULT_ROLE_PROMPTS.get(role_key) or {}
    val = prompts.get(field)
    if val and isinstance(val, str) and val.strip():
        return val
    return None


# 默认任务类型映射（供种子数据使用）
DEFAULT_TASK_TYPES: Dict[str, str] = {
    "news_hunter": "news_analysis",
    "fundamental_expert": "fundamental_analysis",
    "technical_analyst": "technical_analysis",
    "sentiment_analyst": "sentiment_analysis",
    "policy_researcher": "policy_analysis",
    "tool_engineer": "tool_development",
    "risk_manager": "risk_assessment",
    "compliance_officer": "compliance_check",
    "chief_decision_officer": "decision_making",
    "bull_researcher": "general",
    "bear_researcher": "general",
}


def seed_role_library_if_absent(base_roles: Dict[str, Any], task_type_map: Optional[Dict[str, str]] = None) -> None:
    """如果角色库文件不存在或为空，则用内置与默认提示词进行初始化。

    Args:
        base_roles: 由调用方提供的角色基本配置，结构示例：
            { role_key: { name, description, allowed_models, preferred_model, locked_model } }
        task_type_map: 覆盖用的任务类型映射（可为空，默认使用 DEFAULT_TASK_TYPES）
    """
    _ensure_config_dir()
    ttm = task_type_map or DEFAULT_TASK_TYPES

    # 若文件存在且包含roles，跳过
    if _ROLE_LIBRARY_FILE.exists():
        try:
            with _ROLE_LIBRARY_FILE.open("r", encoding="utf-8") as f:
                existing = json.load(f) or {}
            if isinstance(existing, dict) and isinstance(existing.get("roles"), dict) and existing["roles"]:
                return
        except Exception:
            pass

    # 生成种子数据
    roles_out: Dict[str, Any] = {}
    for rk, cfg in (base_roles or {}).items():
        if not isinstance(cfg, dict):
            continue
        roles_out[rk] = {
            'name': cfg.get('name') or rk,
            'description': cfg.get('description') or '',
            'allowed_models': cfg.get('allowed_models') or [],
            'preferred_model': cfg.get('preferred_model'),
            'locked_model': cfg.get('locked_model'),
            'enabled': cfg.get('enabled', True),
            'task_type': ttm.get(rk, ''),
            'prompts': {}
        }
        # 填充默认Prompt（若有）
        sys_p = get_default_prompt(rk, 'system_prompt')
        if sys_p:
            roles_out[rk]['prompts']['system_prompt'] = sys_p
        ana_p = get_default_prompt(rk, 'analysis_prompt_template')
        if ana_p:
            roles_out[rk]['prompts']['analysis_prompt_template'] = ana_p

    save_role_library({'roles': roles_out})


def fill_missing_prompts_in_library() -> bool:
    """为现有角色补齐缺失的默认Prompt字段（不覆盖已有内容）。

    Returns:
        bool: 是否发生变更
    """
    lib = load_role_library()
    roles = lib.get('roles', {}) if isinstance(lib.get('roles'), dict) else {}
    changed = False
    for rk, cfg in roles.items():
        if not isinstance(cfg, dict):
            continue
        prompts = cfg.get('prompts') or {}
        sys_p = prompts.get('system_prompt')
        ana_p = prompts.get('analysis_prompt_template')
        if not sys_p:
            d = get_default_prompt(rk, 'system_prompt')
            if d:
                prompts['system_prompt'] = d
                changed = True
        if not ana_p:
            d2 = get_default_prompt(rk, 'analysis_prompt_template')
            if d2:
                prompts['analysis_prompt_template'] = d2
                changed = True
        cfg['prompts'] = prompts
    if changed:
        save_role_library({'roles': roles})
    return changed


def overwrite_prompts_with_defaults(role_keys: Optional[list[str]] = None) -> int:
    """用默认Prompt覆盖指定角色（或全部已知角色）的模板。

    Args:
        role_keys: 需要覆盖的角色列表；为空则覆盖 DEFAULT_ROLE_PROMPTS 中的全部键

    Returns:
        int: 实际覆盖的数量
    """
    lib = load_role_library()
    roles = lib.get('roles', {}) if isinstance(lib.get('roles'), dict) else {}
    targets = role_keys or list(DEFAULT_ROLE_PROMPTS.keys())
    count = 0
    for rk in targets:
        if rk not in roles:
            continue
        role_cfg = roles[rk] or {}
        role_cfg.setdefault('prompts', {})
        d_sys = get_default_prompt(rk, 'system_prompt')
        d_ana = get_default_prompt(rk, 'analysis_prompt_template')
        if d_sys:
            role_cfg['prompts']['system_prompt'] = d_sys
        if d_ana:
            role_cfg['prompts']['analysis_prompt_template'] = d_ana
        roles[rk] = role_cfg
        count += 1
    if count:
        save_role_library({'roles': roles})
    return count
