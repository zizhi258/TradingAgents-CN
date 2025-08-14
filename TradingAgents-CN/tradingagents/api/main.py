#!/usr/bin/env python3
"""
TradingAgents-CN API 主入口

提供统一的 FastAPI 应用，聚合各路由模块：
- /api/charts/*  图表生成与管理（charting_endpoints）
- /api/v1/visualization/* 可视化服务（visualization_api）
- /health 健康检查
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="TradingAgents-CN API", version="0.1.0")

    # CORS（允许来自本机与常见端口的访问）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "*",  # 如需严格限制来源，可替换为具体域名
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 健康检查
    @app.get("/health")
    async def health():
        return {"status": "ok"}

    # 简要信息（供前端探测与调试）
    @app.get("/api/info")
    async def api_info():
        return {
            "service": "tradingagents-api",
            "version": "0.1.0",
            "routers": [
                "/api/charts",
                "/api/v1/market",
                "/api/v1/visualization",
            ],
            "health": "ok",
        }

    # 路由聚合
    try:
        from .charting_endpoints import router as charting_router
        app.include_router(charting_router)
    except Exception as e:
        # 不中断服务，便于最小可用
        print(f"[API] 跳过加载 charting_endpoints: {e}")

    try:
        from .visualization_api import router as visualization_router
        app.include_router(visualization_router)
    except Exception as e:
        print(f"[API] 跳过加载 visualization_api: {e}")

    # 市场数据/扫描等统一后端接口
    try:
        from .market_data_endpoints import router as market_router
        app.include_router(market_router)
    except Exception as e:
        print(f"[API] 跳过加载 market_data_endpoints: {e}")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
