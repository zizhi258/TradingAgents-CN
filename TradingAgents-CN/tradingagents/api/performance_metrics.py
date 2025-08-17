from fastapi import APIRouter

from tradingagents.monitoring.debate_metrics import get_metrics

router = APIRouter(prefix="/api/v2/performance", tags=["performance"])


@router.get("/metrics")
async def metrics():
    """Return aggregated debate-related metrics (read-only)."""
    return get_metrics()
