"""
Market Data API Endpoints (A股/通用)

Exposes commonly needed market-data endpoints backed by the project's
dataflows and (optionally) Tushare SDK when available.

All endpoints are read-only and return JSON-serializable payloads.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from tradingagents.utils.logging_init import get_logger

logger = get_logger("market_api")
router = APIRouter(prefix="/api/v1/market", tags=["market"])


# Pydantic models
class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0


class StockInfo(BaseModel):
    code: str
    name: Optional[str] = None
    market: Optional[str] = None
    category: Optional[str] = None
    ts_code: Optional[str] = None
    source: Optional[str] = None
    updated_at: Optional[str] = None


class StockInfoPage(BaseModel):
    items: List[StockInfo]
    pagination: Pagination


# ------------------------------
# Cross-market OHLC (CN/HK/US)
# ------------------------------

class OHLCRecord(BaseModel):
    date: str
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[float] = None
    amount: Optional[float] = None


class OHLCResult(BaseModel):
    symbol: str
    market: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    records: List[OHLCRecord]


@router.get("/stocks/{code}/info", response_model=StockInfo)
def get_stock_info(code: str) -> StockInfo:
    """Get basic stock info (with internal fallback)."""
    try:
        from .stock_api import get_stock_info as _get

        data = _get(code)
        if isinstance(data, dict) and data.get("error"):
            raise HTTPException(status_code=503, detail=data.get("error"))
        return StockInfo(**data)  # type: ignore[arg-type]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_stock_info failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stock info")


@router.get("/stocks", response_model=StockInfoPage)
def list_stocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> StockInfoPage:
    """List stocks with simple pagination."""
    try:
        from .stock_api import get_all_stocks as _list

        items = _list()
        # Convert list[dict] -> list[StockInfo]
        rows: List[StockInfo] = []
        for it in items:
            if isinstance(it, dict) and it.get("error"):
                continue
            try:
                rows.append(StockInfo(**it))  # type: ignore[arg-type]
            except Exception:
                # skip malformed row
                continue

        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        return StockInfoPage(
            items=rows[start:end],
            pagination=Pagination(page=page, page_size=page_size, total=total),
        )
    except Exception as e:
        logger.error(f"list_stocks failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list stocks")


@router.get("/stocks/search", response_model=StockInfoPage)
def search_stocks(
    q: str = Query(..., min_length=1, description="keyword (code or name)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
) -> StockInfoPage:
    """Search stocks by code/name substring."""
    try:
        from .stock_api import search_stocks as _search

        items = _search(q)
        rows: List[StockInfo] = []
        for it in items:
            if isinstance(it, dict) and it.get("error"):
                continue
            try:
                rows.append(StockInfo(**it))  # type: ignore[arg-type]
            except Exception:
                continue
        total = len(rows)
        start = (page - 1) * page_size
        end = start + page_size
        return StockInfoPage(
            items=rows[start:end],
            pagination=Pagination(page=page, page_size=page_size, total=total),
        )
    except Exception as e:
        logger.error(f"search_stocks failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to search stocks")


@router.get("/stocks/{code}/daily")
def get_daily(
    code: str,
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    adj: Optional[str] = Query("qfq", pattern="^(|qfq|hfq)$", description="pro_bar adj: '', qfq, hfq"),
) -> Dict[str, Any]:
    """Daily bars with optional pro_bar adj (requires Tushare token; 2000+ 积分)."""
    try:
        # Prefer pro_bar when adj provided; otherwise fallback to provider.daily
        from tradingagents.dataflows.tushare_utils import get_tushare_provider

        prov = get_tushare_provider()
        if adj is not None and hasattr(prov, "get_stock_daily_probar"):
            df = prov.get_stock_daily_probar(code, start_date, end_date, adj=adj or "")
            # 安全回退：pro_bar 返回空时，尝试 daily
            if df is None or getattr(df, "empty", True):
                df = prov.get_stock_daily(code, start_date, end_date)
        else:
            df = prov.get_stock_daily(code, start_date, end_date)

        if df is None or getattr(df, "empty", True):
            return {"code": code, "rows": 0, "data": []}

        # Convert DataFrame -> records
        data = df.to_dict(orient="records")
        return {"code": code, "rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"get_daily failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch daily data")


@router.get("/summary")
def market_summary() -> Dict[str, Any]:
    """Market-wide summary derived from current stock list."""
    try:
        from .stock_api import get_market_summary as _summary

        return _summary()
    except Exception as e:
        logger.error(f"market_summary failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch market summary")


@router.get("/stocks/{code}/ohlc", response_model=OHLCResult)
def get_stock_ohlc(
    code: str,
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
) -> OHLCResult:
    """Unified OHLC endpoint for CN/HK/US using internal dataflows.

    - CN: Tushare adapter
    - HK: AKShare (fallback: Yahoo/Finnhub)
    - US: yfinance online data
    """
    try:
        from tradingagents.dataflows.interface import get_stock_ohlc_json as _ohlc
        payload = _ohlc(code, start_date or "2000-01-01", end_date or datetime.now().strftime("%Y-%m-%d"))
        if not isinstance(payload, dict) or "records" not in payload:
            raise ValueError("Invalid OHLC payload")
        recs = payload.get("records", [])
        out = [
            OHLCRecord(
                date=str(r.get("date")),
                open=r.get("open"),
                high=r.get("high"),
                low=r.get("low"),
                close=r.get("close"),
                volume=r.get("volume"),
                amount=r.get("amount"),
            ) for r in recs
        ]
        return OHLCResult(
            symbol=payload.get("symbol", code),
            market=payload.get("market", "unknown"),
            start_date=payload.get("start_date", start_date),
            end_date=payload.get("end_date", end_date),
            records=out,
        )
    except Exception as e:
        logger.error(f"get_stock_ohlc failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch OHLC data")


# Optional: expose a small set of 2000+ 积分 Tushare endpoints

def _tushare_api_or_raise():
    try:
        import tushare as ts  # type: ignore
        return ts.pro_api()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Tushare SDK/token not available: {e}",
        )


class DividendQuery(BaseModel):
    ts_code: Optional[str] = Field(None, description="e.g., 600519.SH")
    ann_date: Optional[str] = Field(None, description="YYYYMMDD")
    record_date: Optional[str] = None
    ex_date: Optional[str] = None


@router.get("/tushare/dividend")
def tushare_dividend(
    ts_code: Optional[str] = None,
    ann_date: Optional[str] = None,
    record_date: Optional[str] = None,
    ex_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Tushare dividend (2000+) — mirrors doc index_105.md."""
    api = _tushare_api_or_raise()
    try:
        df = api.dividend(
            ts_code=ts_code,
            ann_date=ann_date,
            record_date=record_date,
            ex_date=ex_date,
        )
        rows = 0 if df is None else len(df)
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": rows, "data": data}
    except Exception as e:
        logger.error(f"tushare.dividend failed: {e}")
        raise HTTPException(status_code=500, detail="dividend query failed")


@router.get("/tushare/pledge_stat")
def tushare_pledge_stat(ts_code: Optional[str] = None) -> Dict[str, Any]:
    """Tushare pledge_stat (2000+) — mirrors doc index_112.md."""
    api = _tushare_api_or_raise()
    try:
        df = api.pledge_stat(ts_code=ts_code)
        rows = 0 if df is None else len(df)
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": rows, "data": data}
    except Exception as e:
        logger.error(f"tushare.pledge_stat failed: {e}")
        raise HTTPException(status_code=500, detail="pledge_stat query failed")


@router.get("/tushare/pledge_detail")
def tushare_pledge_detail(ts_code: Optional[str] = None) -> Dict[str, Any]:
    """Tushare pledge_detail (2000+) — mirrors doc index_113.md."""
    api = _tushare_api_or_raise()
    try:
        df = api.pledge_detail(ts_code=ts_code)
        rows = 0 if df is None else len(df)
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": rows, "data": data}
    except Exception as e:
        logger.error(f"tushare.pledge_detail failed: {e}")
        raise HTTPException(status_code=500, detail="pledge_detail query failed")


@router.get("/tushare/top_list")
def tushare_top_list(trade_date: Optional[str] = None) -> Dict[str, Any]:
    """Tushare top_list (2000+) — mirrors doc index_108.md."""
    api = _tushare_api_or_raise()
    try:
        df = api.top_list(trade_date=trade_date)
        rows = 0 if df is None else len(df)
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": rows, "data": data}
    except Exception as e:
        logger.error(f"tushare.top_list failed: {e}")
        raise HTTPException(status_code=500, detail="top_list query failed")


@router.get("/tushare/top_inst")
def tushare_top_inst(trade_date: Optional[str] = None) -> Dict[str, Any]:
    """Tushare top_inst (2000+) — mirrors doc index_109.md."""
    api = _tushare_api_or_raise()
    try:
        df = api.top_inst(trade_date=trade_date)
        rows = 0 if df is None else len(df)
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": rows, "data": data}
    except Exception as e:
        logger.error(f"tushare.top_inst failed: {e}")
        raise HTTPException(status_code=500, detail="top_inst query failed")


# ------------------------------
# Additional Tushare endpoints (2000 积分档内常用)
# ------------------------------

@router.get("/tushare/daily_basic")
def tushare_daily_basic(
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Tushare daily_basic (2000+) — common daily indicators."""
    api = _tushare_api_or_raise()
    try:
        df = api.daily_basic(
            ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date
        )
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"tushare.daily_basic failed: {e}")
        raise HTTPException(status_code=500, detail="daily_basic query failed")


@router.get("/tushare/moneyflow")
def tushare_moneyflow(
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Tushare moneyflow (2000+) — 个股资金流向。"""
    api = _tushare_api_or_raise()
    try:
        df = api.moneyflow(
            ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date
        )
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"tushare.moneyflow failed: {e}")
        raise HTTPException(status_code=500, detail="moneyflow query failed")


@router.get("/tushare/block_trade")
def tushare_block_trade(
    ts_code: Optional[str] = None,
    trade_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Tushare block_trade (2000+) — 大宗交易。"""
    api = _tushare_api_or_raise()
    try:
        df = api.block_trade(
            ts_code=ts_code, trade_date=trade_date, start_date=start_date, end_date=end_date
        )
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"tushare.block_trade failed: {e}")
        raise HTTPException(status_code=500, detail="block_trade query failed")


@router.get("/tushare/stk_limit")
def tushare_stk_limit(ts_code: Optional[str] = None, trade_date: Optional[str] = None) -> Dict[str, Any]:
    """Tushare stk_limit (2000+) — 涨跌停价格。"""
    api = _tushare_api_or_raise()
    try:
        df = api.stk_limit(ts_code=ts_code, trade_date=trade_date)
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"tushare.stk_limit failed: {e}")
        raise HTTPException(status_code=500, detail="stk_limit query failed")


@router.get("/tushare/hk_hold")
def tushare_hk_hold(ts_code: Optional[str] = None, trade_date: Optional[str] = None) -> Dict[str, Any]:
    """Tushare hk_hold (2000+) — 沪深股通持股明细。"""
    api = _tushare_api_or_raise()
    try:
        df = api.hk_hold(ts_code=ts_code, trade_date=trade_date)
        data = [] if df is None else df.to_dict(orient="records")
        return {"rows": len(data), "data": data}
    except Exception as e:
        logger.error(f"tushare.hk_hold failed: {e}")
        raise HTTPException(status_code=500, detail="hk_hold query failed")


"""
# ------------------------------
# Group/custom filters for A股清单（指数预设相关接口已移除）
# ------------------------------
"""
    


class GroupResult(BaseModel):
    group: str
    items: List[StockInfo]
    pagination: Pagination


def _load_all_stock_infos() -> List[StockInfo]:
    from .stock_api import get_all_stocks as _list
    items = _list()
    rows: List[StockInfo] = []
    for it in items:
        if isinstance(it, dict) and it.get("error"):
            continue
        try:
            rows.append(StockInfo(**it))  # type: ignore[arg-type]
        except Exception:
            continue
    return rows


@router.get("/filters/group/{group}", response_model=GroupResult)
def filter_by_group(
    group: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> GroupResult:
    group = group.lower()
    rows = _load_all_stock_infos()
    if group == "sme":
        filtered = [r for r in rows if r.code.startswith("002")]  # 中小板常见代码前缀
    elif group == "st":
        def _is_st(name: Optional[str]) -> bool:
            if not name:
                return False
            n = name.upper()
            return ("ST" in n) or ("*ST" in n) or ("退" in n)
        filtered = [r for r in rows if _is_st(r.name)]
    else:
        raise HTTPException(status_code=404, detail="Unknown group")

    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return GroupResult(
        group=group,
        items=filtered[start:end],
        pagination=Pagination(page=page, page_size=page_size, total=total),
    )


class CustomFilter(BaseModel):
    markets: Optional[List[str]] = Field(None, description="e.g., ['上海','深圳']")
    code_prefixes: Optional[List[str]] = None
    name_contains: Optional[str] = None
    include_st: Optional[bool] = None
    exclude_st: Optional[bool] = None
    category_in: Optional[List[str]] = None
    industry_in: Optional[List[str]] = None
    limit: int = 200
    offset: int = 0


class CustomFilterResponse(BaseModel):
    total: int
    items: List[StockInfo]


@router.post("/filters/custom", response_model=CustomFilterResponse)
def custom_filter(payload: CustomFilter) -> CustomFilterResponse:
    rows = _load_all_stock_infos()

    def is_st(name: Optional[str]) -> bool:
        if not name:
            return False
        n = name.upper()
        return ("ST" in n) or ("*ST" in n) or ("退" in n)

    q = []
    for r in rows:
        ok = True
        if payload.markets and r.market not in payload.markets:
            ok = False
        if ok and payload.code_prefixes and not any(r.code.startswith(p) for p in payload.code_prefixes):
            ok = False
        if ok and payload.name_contains and (not r.name or payload.name_contains not in r.name):
            ok = False
        if ok and payload.category_in and (not r.category or r.category not in payload.category_in):
            ok = False
        if ok and payload.industry_in:
            # StockInfo currently doesn't expose industry; treat as not match
            ok = False
        if ok and payload.include_st is True and not is_st(r.name):
            ok = False
        if ok and payload.exclude_st is True and is_st(r.name):
            ok = False
        if ok:
            q.append(r)

    total = len(q)
    start = max(0, payload.offset)
    end = start + max(1, payload.limit)
    return CustomFilterResponse(total=total, items=q[start:end])
