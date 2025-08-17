#!/usr/bin/env python3
"""
TradingAgents-CN API 主入口

提供统一的 FastAPI 应用，聚合各路由模块：
- /api/charts/*  图表生成与管理（charting_endpoints）
- /api/v1/visualization/* 可视化服务（visualization_api）
- /health 健康检查
"""

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Ensure .env is loaded when running API directly (uvicorn path)
try:
    from pathlib import Path

    from dotenv import load_dotenv

    # project root: .../TradingAgents-CN
    _env_path = Path(__file__).resolve().parents[2] / ".env"
    # In containers, prefer environment provided by Docker over .env file
    load_dotenv(_env_path, override=False)
except Exception:
    # Do not hard-fail if dotenv is missing; many configs also come from real env
    pass


from tradingagents.utils.logging_init import init_logging, get_logger
from tradingagents.utils.http_instrumentation import install_requests_debug_logging
from .instrumentation import setup_instrumentation


def create_app() -> FastAPI:
    # Init logging early once (no-op if already configured)
    try:
        init_logging()
    except Exception:
        pass

    app = FastAPI(title="TradingAgents-CN API", version="0.1.0")

    log = get_logger("api.boot")
    # Optional: outgoing HTTP debug
    try:
        install_requests_debug_logging()
    except Exception:
        pass

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

    # Instrumentation: request IDs, logging, exception handling, debug routes
    setup_instrumentation(app)

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
                "/api/kb",
            ],
            "health": "ok",
        }

    # 路由聚合
    try:
        from .charting_endpoints import router as charting_router

        app.include_router(charting_router)
    except Exception as e:
        # 不中断服务，便于最小可用
        log.warning(f"跳过加载 charting_endpoints: {e}")

    try:
        from .visualization_api import router as visualization_router

        app.include_router(visualization_router)
    except Exception as e:
        log.warning(f"跳过加载 visualization_api: {e}")

    # 市场数据/扫描等统一后端接口
    try:
        from .market_data_endpoints import router as market_router

        app.include_router(market_router)
    except Exception as e:
        log.warning(f"跳过加载 market_data_endpoints: {e}")

    # 只读性能指标（辩论相关）
    try:
        from .performance_metrics import router as perf_router

        app.include_router(perf_router)
    except Exception as e:
        log.warning(f"跳过加载 performance_metrics: {e}")

    # 知识库/KBRAG 端点（供智能对话使用）
    try:
        from .knowledge_endpoints import router as kb_router

        app.include_router(kb_router)
        log.info("已挂载知识库端点 /api/kb/*，用于智能对话的RAG查询")
    except Exception as e:
        log.warning(f"跳过加载 knowledge_endpoints: {e}")

    # 静态挂载：原文跳转（/library/* -> LIBRARY_ROOT）
    try:
        serve_flag = str(os.getenv("SERVE_LIBRARY_STATIC", "true")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if serve_flag:
            from pathlib import Path as _Path

            lib_root = os.getenv("LIBRARY_ROOT", "./data/library")
            p = _Path(lib_root)
            p.mkdir(parents=True, exist_ok=True)
            app.mount("/library", StaticFiles(directory=str(p), html=False), name="library")
            log.info(f"已挂载静态文库: /library -> {p}")
    except Exception as e:
        log.warning(f"静态文库挂载失败: {e}")

    # 可选：挂载多模型协作的 v2 路由（供前端探测可用智能体等）
    # 通过环境变量开启：ENABLE_MULTI_MODEL_API=true 或 MULTI_MODEL_ENABLED=true
    try:
        enable_flag = os.getenv(
            "ENABLE_MULTI_MODEL_API", os.getenv("MULTI_MODEL_ENABLED", "false")
        )
        if str(enable_flag).lower() in {"1", "true", "yes", "on"}:
            try:
                from tradingagents.api.multi_model_api_extension import (
                    extend_stock_api_with_multi_model,
                )
                from tradingagents.graph.trading_graph import TradingAgentsGraph

                # 使用默认配置初始化 TradingAgentsGraph（内部会按环境变量选择可用提供商）
                graph = TradingAgentsGraph(debug=False)
                extend_stock_api_with_multi_model(app, graph)
                log.info("已挂载多模型协作 v2 路由 (/api/v2)")
            except Exception as e:
                log.warning(f"跳过加载 multi_model_api_extension: {e}")
        else:
            log.info(
                "多模型协作 v2 路由未启用 (设置 ENABLE_MULTI_MODEL_API=true 可开启)"
            )
    except Exception as e:
        log.warning(f"检测多模型路由开关失败: {e}")

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
