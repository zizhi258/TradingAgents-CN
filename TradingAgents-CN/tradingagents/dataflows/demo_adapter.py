#!/usr/bin/env python3
"""
Demo-mode data adapter

Provides helpers to load a local demo JSON (e.g., 长安汽车 000625) and
format it into strings compatible with the unified China data interface.

Scope:
- Used only when DEMO_MODE=true to simulate input data while keeping the
  rest of the analysis flow unchanged.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from tradingagents.config.env_utils import parse_bool_env, parse_str_env
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


DEFAULT_DEMO_PATH = "data/demo/changan_000625_demo.json"


def is_demo_mode() -> bool:
    """Return True if DEMO_MODE is enabled in environment."""
    return parse_bool_env("DEMO_MODE", False)


def get_demo_file_path() -> str:
    """Get demo file path from env or default."""
    path = parse_str_env("DEMO_DATA_FILE", DEFAULT_DEMO_PATH)
    return path or DEFAULT_DEMO_PATH


def _load_demo_json() -> dict[str, Any]:
    """Load the demo JSON payload from configured path.

    Raises if file cannot be read; caller should handle exceptions.
    """
    path = get_demo_file_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logger.error(f"❌ 演示数据文件读取失败: {path}, 错误: {e}")
        raise


def _filter_ohlcv_range(
    ohlcv: list[dict[str, Any]], start_date: str, end_date: str
) -> list[dict[str, Any]]:
    """Filter ohlcv rows by inclusive date range (YYYY-MM-DD)."""
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.strptime(end_date, "%Y-%m-%d").date()
    except Exception:
        # best-effort if date parsing fails
        return ohlcv
    out: list[dict[str, Any]] = []
    for r in ohlcv:
        try:
            d = datetime.strptime(str(r.get("date")), "%Y-%m-%d").date()
            if sd <= d <= ed:
                out.append(r)
        except Exception:
            continue
    return out


def build_china_stock_data_from_demo(
    symbol: str, start_date: str, end_date: str
) -> str:
    """Build a formatted China stock data report string from demo JSON.

    - Keeps the input `symbol` unchanged in output headers
    - Uses demo OHLCV to compute latest price and basic stats
    - Mirrors the shape used by unified Tushare path to keep downstream compatible
    """
    data = _load_demo_json()
    info = data.get("stock_info", {})
    name = info.get("name", f"股票{symbol}")
    ohlcv = data.get("ohlcv_daily", [])
    rows = _filter_ohlcv_range(ohlcv, start_date, end_date)

    count = len(rows)
    latest_price = 0.0
    change = 0.0
    change_pct = 0.0
    hi = None
    lo = None
    avg_close_acc = 0.0
    vol_sum = 0.0

    if count > 0:
        latest_price = float(rows[-1].get("close", 0.0))
        prev_close = (
            float(rows[-2].get("close", latest_price)) if count > 1 else latest_price
        )
        change = latest_price - prev_close
        change_pct = (change / prev_close * 100.0) if prev_close else 0.0

        hi = max(float(r.get("high", latest_price)) for r in rows)
        lo = min(float(r.get("low", latest_price)) for r in rows)
        avg_close_acc = sum(float(r.get("close", 0.0)) for r in rows) / max(count, 1)
        vol_sum = sum(float(r.get("volume", 0.0)) for r in rows)

    header = f"📊 {name}({symbol}) - 演示数据\n"
    header += f"数据期间: {start_date} 至 {end_date}\n"
    header += f"数据条数: {count}条\n\n"

    stat = f"💰 最新价格: ¥{latest_price:.2f}\n"
    stat += f"📈 涨跌额: {change:+.2f} ({change_pct:+.2f}%)\n\n"
    stat += "📊 价格统计:\n"
    if hi is not None and lo is not None:
        stat += f"   最高价: ¥{hi:.2f}\n"
        stat += f"   最低价: ¥{lo:.2f}\n"
    stat += f"   平均价: ¥{avg_close_acc:.2f}\n"
    stat += f"   成交量: {vol_sum:,.0f} 股\n"

    # Optionally show last up to 3 lines for human readability
    tail_preview = ""
    if count > 0:
        preview = rows[-3:] if count >= 3 else rows
        tail_preview += "\n最新数据 (最多3日):\n"
        tail_preview += (
            "日期        开盘     最高     最低     收盘       成交量       成交额\n"
        )
        for r in preview:
            tail_preview += (
                f"{str(r.get('date')):10s} "
                f"{float(r.get('open', 0.0)):7.2f} "
                f"{float(r.get('high', 0.0)):7.2f} "
                f"{float(r.get('low', 0.0)):7.2f} "
                f"{float(r.get('close', 0.0)):7.2f} "
                f"{int(float(r.get('volume', 0.0))):11d} "
                f"{float(r.get('amount', 0.0)):12.2f}\n"
            )

    note = "\n数据来源: 本地演示JSON (仅替代输入数据)\n"

    return header + stat + tail_preview + note


def build_china_stock_info_from_demo(symbol: str) -> str:
    """Build a formatted China stock info string from demo JSON for unified interface."""
    data = _load_demo_json()
    info = data.get("stock_info", {})
    name = info.get("name", f"股票{symbol}")
    industry = info.get("industry", "未知")
    area = info.get("area", "未知")
    list_date = info.get("list_date", "未知")

    return (
        f"股票代码: {symbol}\n"
        f"股票名称: {name}\n"
        f"所属地区: {area}\n"
        f"所属行业: {industry}\n"
        f"上市市场: A股\n"
        f"上市日期: {list_date}\n"
        f"数据来源: demo\n"
    )


def get_ohlc_json_from_demo(
    symbol: str, start_date: str, end_date: str
) -> dict[str, Any]:
    """Return OHLC structure from demo JSON, aligning with get_stock_ohlc_json."""
    data = _load_demo_json()
    ohlcv = data.get("ohlcv_daily", [])
    rows = _filter_ohlcv_range(ohlcv, start_date, end_date)
    # Normalize fields and types
    records: list[dict[str, Any]] = []
    for r in rows:
        try:
            records.append(
                {
                    "date": str(r.get("date")),
                    "open": float(r.get("open", 0.0)),
                    "high": float(r.get("high", 0.0)),
                    "low": float(r.get("low", 0.0)),
                    "close": float(r.get("close", 0.0)),
                    "volume": float(r.get("volume", 0.0)),
                    "amount": float(r.get("amount", 0.0)),
                }
            )
        except Exception:
            continue

    return {
        "symbol": symbol,
        "market": "A股(演示)",
        "start_date": start_date,
        "end_date": end_date,
        "records": records,
    }


__all__ = [
    "is_demo_mode",
    "get_demo_file_path",
    "build_china_stock_data_from_demo",
    "build_china_stock_info_from_demo",
    "get_ohlc_json_from_demo",
]
