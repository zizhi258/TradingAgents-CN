#!/usr/bin/env python3
"""
Enrich demo JSON for Changan (000625) with policy/compliance/roadmap snippets.

Usage:
  python scripts/development/enrich_demo_data.py \
      --file TradingAgents-CN/data/demo/changan_000625_demo.json

Notes:
  - Network sources are public pages (Wikipedia, etc.).
  - This script is best-effort; it appends fields only if missing.
  - It does NOT overwrite existing arrays/objects unless the user passes --force.
"""

from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path
from typing import Any

import requests


def fetch_text(url: str, timeout: int = 15) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=timeout)
        if r.ok:
            return r.text
    except Exception:
        pass
    return ""


def strip_html(s: str) -> str:
    s = re.sub(r"<.*?>", " ", s)
    s = unescape(s)
    return " ".join(s.split())


def extract_changan_brands(html: str) -> list[str]:
    # Simple heuristic for known brands on page
    brands = []
    for k in ["Changan", "Deepal", "Avatr", "Kaicene"]:
        if re.search(fr"\b{k}\b", html, re.I):
            brands.append(k)
    return sorted(set(brands))


def ensure_policy_events(data: dict[str, Any]) -> None:
    if "policy_events" in data and data["policy_events"]:
        return
    # Use themes already present in demo news; add best-effort sources
    data["policy_events"] = [
        {
            "date": "2025-07-29",
            "source": "Reuters",
            "title": "Changan restructured as independent state‑owned automaker",
            "summary": "长安汽车从兵装集团剥离为中央控股企业，治理与国际化空间提升。",
            "relevance": "治理与国资属性调整，利好国际化与投融资治理效率",
            "source_url": "https://www.reuters.com/",
        },
        {
            "date": "2025-07-02",
            "source": "Reuters",
            "title": "Changan plans European factory",
            "summary": "计划在欧洲建厂与渠道布局，应对关税与本地化合规需求。",
            "relevance": "欧盟市场本地化，有助于合规与成本控制",
            "source_url": "https://www.reuters.com/",
        },
    ]


def ensure_compliance_risks(data: dict[str, Any]) -> None:
    if "compliance_risks" in data and data["compliance_risks"]:
        return
    data["compliance_risks"] = [
        {
            "risk_type": "贸易与关税",
            "description": "欧盟对中国电动车补贴调查与关税动态，价格体系不确定性高。",
            "severity": "high",
            "mitigation": "欧洲本地化(建厂/供应链)、优化定价与产品结构",
        },
        {
            "risk_type": "数据与隐私(GDPR)",
            "description": "车辆与用户数据的采集/存储/跨境需满足GDPR与本地化合规。",
            "severity": "medium",
            "mitigation": "数据最小化、匿名化、在欧部署与审计",
        },
        {
            "risk_type": "ESG/电池合规",
            "description": "电池碳足迹、回收与溯源(电池护照)要求提升。",
            "severity": "medium",
            "mitigation": "建立碳核算与回收体系、材料可追溯",
        },
    ]


def ensure_tech_roadmap(data: dict[str, Any]) -> None:
    if "tech_roadmap" in data and data["tech_roadmap"]:
        return
    html = fetch_text("https://en.wikipedia.org/wiki/Changan_Automobile")
    brands = extract_changan_brands(html) if html else ["Changan", "Deepal", "Avatr", "Kaicene"]
    data["tech_roadmap"] = {
        "brands": brands,
        "jvs": ["Changan Ford", "Changan Mazda"],
        "focus_areas": ["智能电动平台", "ADAS/NOA", "智能座舱", "出海本地化"],
        "milestones": [
            {"year": 2025, "item": "欧洲市场渠道与本地化能力建设（建厂/CKD）"},
            {"year": 2025, "item": "深蓝/阿维塔车型迭代，城区NOA等功能持续下沉"},
            {"year": 2026, "item": "三电与EEA平台化/降本"},
        ],
        "source_note": "Brands/JVs heuristically derived from Wikipedia: Changan Automobile",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(Path(__file__).resolve().parents[2] / "data/demo/changan_000625_demo.json"))
    ap.add_argument("--force", action="store_true", help="overwrite existing sections if present")
    args = ap.parse_args()

    p = Path(args.file)
    data: dict[str, Any]
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))
    else:
        print(f"File not found: {p}")
        return 1

    if args.force:
        for k in ["policy_events", "compliance_risks", "tech_roadmap"]:
            data.pop(k, None)

    ensure_policy_events(data)
    ensure_compliance_risks(data)
    ensure_tech_roadmap(data)

    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Enriched demo data written: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

