#!/usr/bin/env python3
"""
Demo data utilities
提供“演示模式”所需的数据加载与报告拼装工具。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


def _project_root() -> Path:
    return Path(__file__).parent.parent.parent


def get_demo_file_path() -> Path:
    """获取演示数据文件路径（支持环境变量覆盖）。"""
    default_rel = Path("data/demo/changan_000625_demo.json")
    env_path = os.getenv("DEMO_DATA_FILE", "").strip()
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = _project_root() / p
        return p
    return _project_root() / default_rel


def load_demo_json() -> Dict[str, Any]:
    """加载演示数据JSON，若不存在则返回空结构。"""
    demo_path = get_demo_file_path()
    try:
        with open(demo_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def build_markdown_sections_from_demo(data: Dict[str, Any]) -> Dict[str, str]:
    """根据演示JSON构建各模块Markdown文本。"""
    meta = data.get("meta", {})
    info = data.get("stock_info", {})
    fundamentals = data.get("fundamentals_snapshot", {})
    ohlcv = data.get("ohlcv_daily", [])
    tech = data.get("technical_indicators_snapshot", {})
    news = data.get("news_recent", [])
    senti = data.get("sentiment_agg_7d", {})

    name = info.get("name") or meta.get("ticker") or "演示标的"
    ts_code = meta.get("ts_code", "")

    # 市场技术分析
    last = ohlcv[-1] if ohlcv else {}
    market_md = [f"## 📈 {name} 技术面分析"]
    if last:
        market_md.append(
            f"- 最新收盘: {last.get('close', 'N/A')} (开 {last.get('open','N/A')} 高 {last.get('high','N/A')} 低 {last.get('low','N/A')})"
        )
        market_md.append(f"- 成交量: {last.get('volume','N/A')}  成交额: {last.get('amount','N/A')}")
    if tech:
        market_md.append("- 技术指标概览：")
        ma5 = tech.get("ma5"); ma10 = tech.get("ma10"); ma20 = tech.get("ma20")
        market_md.append(f"  - MA: 5={ma5} / 10={ma10} / 20={ma20}")
        rsi14 = tech.get("rsi14"); macd = tech.get("macd", {})
        market_md.append(f"  - RSI(14)={rsi14}  MACD: dif={macd.get('dif')} dea={macd.get('dea')} hist={macd.get('hist')}")
    market_report = "\n".join(market_md)

    # 基本面分析
    fund_md = [f"## 💰 {name} 基本面快照"]
    if ts_code:
        fund_md.append(f"- 代码: {ts_code}")
    if fundamentals:
        fund_md.append("- 关键指标 (TTM/近四季)：")
        fund_md.append(
            "  - 收入: {0:,} 元  净利润: {1:,} 元".format(
                int(fundamentals.get("revenue", 0) or 0), int(fundamentals.get("net_profit", 0) or 0)
            )
        )
        fund_md.append(
            f"  - EPS: {fundamentals.get('eps_ttm','N/A')}  ROE: {fundamentals.get('roe','N/A')}%  毛利率: {fundamentals.get('gross_margin','N/A')}%"
        )
        fund_md.append(
            f"  - 估值: PE(TTM)={fundamentals.get('pe_ttm','N/A')}  PB={fundamentals.get('pb','N/A')}  资产负债率={fundamentals.get('debt_to_asset','N/A')}%"
        )
    fundamentals_report = "\n".join(fund_md)

    # 新闻事件
    news_md = [f"## 📰 {name} 近期新闻事件"]
    if news:
        for item in news[:3]:
            news_md.append(
                f"- {item.get('date','')} | {item.get('source','')} | {item.get('title','')} ({item.get('sentiment','')})\n  {item.get('summary','')}"
            )
    else:
        news_md.append("- 暂无新闻摘要")
    news_report = "\n".join(news_md)

    # 情绪分析
    sent_md = [f"## 💭 {name} 市场情绪概览(7日)"]
    if senti:
        pos = senti.get('pos', 0); neu = senti.get('neu', 0); neg = senti.get('neg', 0)
        total = (pos or 0) + (neu or 0) + (neg or 0)
        sent_md.append(f"- 情绪计数：正面 {pos} / 中性 {neu} / 负面 {neg} (共 {total})")
        if total:
            bias = '偏正面' if pos > neg else '偏负面' if neg > pos else '中性'
            sent_md.append(f"- 情绪偏向：{bias}")
    else:
        sent_md.append("- 暂无近7日情绪汇总")
    sentiment_report = "\n".join(sent_md)

    # 风险评估（简化）
    risk_md = ["## ⚠️ 风险评估", "- 市场波动与政策变化可能影响需求与估值", "- 海外扩张执行与汇率波动风险", "- 行业竞争与价格战压力"]
    risk_report = "\n".join(risk_md)

    # 投资建议（示例）
    invest_md = ["## 📋 投资建议(演示)", "- 策略: 以演示数据生成的参考结论，非投资建议", "- 建议: 观察关键均线与RSI拐点，分批操作"]
    invest_report = "\n".join(invest_md)

    return {
        "market_report": market_report,
        "fundamentals_report": fundamentals_report,
        "sentiment_report": sentiment_report,
        "news_report": news_report,
        "risk_assessment": risk_report,
        "investment_plan": invest_report,
    }


def build_decision_from_demo(data: Dict[str, Any]) -> Dict[str, Any]:
    """根据演示数据生成一个简要的决策摘要。"""
    # 简单规则：RSI>50 偏多，<35 偏空，否则持有
    tech = data.get("technical_indicators_snapshot", {})
    rsi = tech.get("rsi14")
    action = "持有"; risk = 0.3; conf = 0.6
    if isinstance(rsi, (int, float)):
        if rsi >= 55:
            action, conf, risk = "买入", 0.7, 0.35
        elif rsi <= 35:
            action, conf, risk = "卖出", 0.65, 0.45
    return {
        "action": action,
        "confidence": conf,
        "risk_score": risk,
        "target_price": None,
        "reasoning": "本结论基于演示数据的技术与基本面快照自动生成，供界面演示使用。"
    }


def build_final_article_from_sections(name: str, sections: Dict[str, str]) -> Tuple[str, Dict[str, Any]]:
    content = [f"# {name} 多维度演示分析报告", sections.get("fundamentals_report", ""), sections.get("market_report", ""), sections.get("news_report", ""), sections.get("risk_assessment", ""), sections.get("investment_plan", "")]
    article = "\n\n".join([c for c in content if c])
    metrics = {"word_count": len(article), "sections_covered": sum(1 for k in ["fundamentals_report","market_report","news_report","risk_assessment","investment_plan"] if sections.get(k))}
    return article, metrics


def build_single_result_from_demo() -> Dict[str, Any]:
    data = load_demo_json()
    meta = data.get("meta", {})
    info = data.get("stock_info", {})
    symbol = meta.get("ticker") or "000000"
    name = info.get("name") or symbol
    sections = build_markdown_sections_from_demo(data)
    decision = build_decision_from_demo(data)
    return {
        "stock_symbol": symbol,
        "analysis_date": meta.get("trade_date") or datetime.now().strftime('%Y-%m-%d'),
        "analysts": ["market", "fundamentals", "news"],
        "research_depth": 3,
        "llm_provider": "demo",
        "llm_model": "demo",
        "state": sections,
        "decision": decision,
        "success": True,
        "is_demo": True,
        "demo_reason": "演示模式已启用：使用本地示例数据"
    }


def build_multi_model_results_from_demo(selected_agents: List[str] | None = None) -> Dict[str, Any]:
    data = load_demo_json()
    meta = data.get("meta", {})
    info = data.get("stock_info", {})
    symbol = meta.get("ticker") or "000000"
    name = info.get("name") or symbol
    sections = build_markdown_sections_from_demo(data)

    # 组装智能体结果（简化文本）
    agents = list(selected_agents or ["news_hunter", "fundamental_expert", "risk_manager"])
    results: Dict[str, Any] = {}
    now_iso = datetime.now().isoformat()
    # 为所有被选中的智能体生成内容（映射或占位）
    for agent in agents:
        if agent == "fundamental_expert":
            analysis = sections.get("fundamentals_report", "")
            rec = "请参考基本面快照与估值指标"
        elif agent == "news_hunter":
            analysis = sections.get("news_report", "")
            rec = "根据事件时效与影响路径做短线观察"
        elif agent == "risk_manager":
            analysis = sections.get("risk_assessment", "")
            rec = "控制仓位与波动率，关注政策与汇率"
        elif agent == "technical_analyst":
            analysis = sections.get("market_report", "")
            rec = "关注关键均线/RSI/MACD拐点，分批操作"
        elif agent == "sentiment_analyst":
            analysis = sections.get("sentiment_report", "")
            rec = "情绪偏向作为风险调节因子，不单独做决策"
        elif agent == "policy_researcher":
            analysis = ("## 政策/产业环境(演示)\n- 结合新闻与行业景气，评估对公司收入/成本/估值的影响\n"
                        "- 给出乐观/中性/悲观三情景及触发条件")
            rec = "跟踪产业政策与出口限制的边际变化"
        elif agent == "compliance_officer":
            analysis = ("## 合规检查清单(演示)\n- 信息披露/数据隐私/关联交易/反垄断/出口管制\n"
                        "- 每项：现状/缺口/整改建议/优先级/时间表")
            rec = "完善披露与隐私合规，降低执法风险"
        elif agent == "tool_engineer":
            analysis = ("## 工具/量化视角(演示)\n- 构建基础回测与指标组合，形成观察列表\n- 建议将技术/情绪/新闻信号做多指标打分")
            rec = "用多指标打分过滤交易信号，控制过拟合"
        elif agent == "chief_decision_officer":
            analysis = ("## 综合裁决(演示)\n- 汇总各角色要点，给出行动/仓位/触发价/止损止盈\n- 设定复核时间与触发条件")
            rec = "按‘仓位-触发-止损’三要素落地执行"
        else:
            analysis = f"## {agent} 演示占位\n- 暂无定制模板，建议参考基本面/技术/新闻/风控模块"
            rec = "结合已知模块，形成可执行要点"

        results[agent] = {
            "agent_type": agent,
            "analysis": analysis,
            "confidence": 0.8,
            "recommendations": rec,
            "timestamp": now_iso,
            "model_used": "demo"
        }

    final_article, metrics = build_final_article_from_sections(name, sections)

    return {
        "status": "success",
        "collaboration_mode": "sequential",
        "agents_used": agents,
        "analysis_data": {
            "stock_symbol": symbol,
            "market_type": meta.get("market", "A股"),
            "analysis_date": meta.get("trade_date") or datetime.now().strftime('%Y-%m-%d'),
            "research_depth": 3,
            "custom_requirements": ""
        },
        "results": results,
        "final_article": final_article,
        "final_article_metrics": metrics,
        "timestamp": now_iso
    }
