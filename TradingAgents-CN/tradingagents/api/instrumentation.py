#!/usr/bin/env python3
"""
FastAPI instrumentation: request IDs, request/response logging,
global exception handling, and optional SSE log streaming.

Usage:
    from .instrumentation import setup_instrumentation
    setup_instrumentation(app)
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextvars import ContextVar
from typing import Any, AsyncIterator, Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware

from tradingagents.utils.logging_init import get_logger


# Context: request ID available to logging records
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class _RequestContextFilter:
    """Logging filter to always add request_id attribute to records."""

    def filter(self, record):  # type: ignore[override]
        try:
            rid = _request_id_ctx.get()
        except Exception:
            rid = None
        # Always provide the attribute to avoid KeyError in formatters
        setattr(record, "request_id", rid or "-")
        return True


def _install_log_filter_once() -> None:
    """Attach context filter to the root logger once.

    This ensures console/file formatters can safely reference %(request_id)s.
    """
    import logging

    root = logging.getLogger()
    # Avoid duplicate filters
    if not any(isinstance(f, _RequestContextFilter) for f in root.filters):
        root.addFilter(_RequestContextFilter())


class _RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self.logger = get_logger("api.requests")

    async def dispatch(self, request: Request, call_next: Callable):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = _request_id_ctx.set(request_id)
        start = time.perf_counter()

        # Basic request information
        client = request.client.host if request.client else "-"
        ua = request.headers.get("user-agent", "-")[:200]
        self.logger.info(
            f"-> {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "client": client,
                "user_agent": ua,
                "path": request.url.path,
                "query": str(request.url.query)[:500],
            },
        )

        try:
            response = await call_next(request)
        except Exception:
            # Let global handler handle; ensure context restored
            _request_id_ctx.reset(token)
            raise

        # Attach headers for browser visibility and tracing
        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers.setdefault("X-Request-ID", request_id)
        response.headers.setdefault("X-Process-Time", str(duration_ms))

        # Log summary
        self.logger.info(
            f"<- {request.method} {request.url.path} {response.status_code} {duration_ms}ms",
            extra={"request_id": request_id, "status_code": response.status_code},
        )

        _request_id_ctx.reset(token)
        return response


async def _json_error(
    status: int,
    message: str,
    request_id: str | None,
    code: str = "internal_error",
    detail: Any | None = None,
):
    payload = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        },
        "request_id": request_id,
    }
    headers = {"X-Request-ID": request_id or "-", "X-Error-Code": code}
    return JSONResponse(status_code=status, content=payload, headers=headers)


def _install_exception_handlers(app: FastAPI) -> None:
    logger = get_logger("api.errors")

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        rid = _request_id_ctx.get()
        logger.warning(
            f"validation_error: {exc.errors()!r}",
            extra={"request_id": rid, "path": request.url.path},
        )
        return await _json_error(422, "请求参数校验失败", rid, code="validation_error", detail=exc.errors())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        rid = _request_id_ctx.get()
        logger.exception(
            f"unhandled_exception at {request.url.path}: {exc}",
            extra={"request_id": rid},
        )
        return await _json_error(500, "服务器内部错误", rid, code="internal_error")


# --- SSE Log Streaming ---
_log_queue: asyncio.Queue[str] | None = None


class _QueueLogHandler:
    """Lightweight handler-like object to push JSON log entries to an asyncio.Queue.

    We avoid importing logging here to keep dependencies minimal; attach from setup.
    """

    def __init__(self, queue: asyncio.Queue[str]):
        self.queue = queue

    def emit(self, record):  # type: ignore[override]
        try:
            import logging

            logger = logging.getLogger(record.name)
            # Build a small JSON payload for the browser
            data = {
                "ts": getattr(record, "created", time.time()),
                "level": record.levelname,
                "logger": record.name,
                "msg": record.getMessage(),
                "request_id": getattr(record, "request_id", "-"),
            }
            self.queue.put_nowait(json.dumps(data, ensure_ascii=False))
        except Exception:
            # Never raise from emit
            pass


def _attach_queue_handler() -> None:
    global _log_queue
    if _log_queue is not None:
        return
    _log_queue = asyncio.Queue(maxsize=1000)

    import logging

    handler = _QueueLogHandler(_log_queue)

    class _Proxy(logging.Handler):
        def emit(self, record):  # type: ignore[override]
            handler.emit(record)

    proxy = _Proxy()
    proxy.setLevel(logging.INFO)

    root = logging.getLogger()
    root.addHandler(proxy)


async def _sse_event_source() -> AsyncIterator[bytes]:
    """Yield log lines as SSE events."""
    assert _log_queue is not None
    # Send a hello event so the connection appears in Network tab quickly
    hello = json.dumps({"level": "INFO", "logger": "api.sse", "msg": "log stream connected"})
    yield f"data: {hello}\n\n".encode("utf-8")
    while True:
        line = await _log_queue.get()
        yield f"data: {line}\n\n".encode("utf-8")


def _mount_debug_routes(app: FastAPI) -> None:
    logger = get_logger("api.debug")

    @app.get("/api/debug/logs/stream")
    async def sse_logs():
        """Server-Sent Events stream of logs for browser F12 visibility."""
        if _log_queue is None:
            _attach_queue_handler()
        return StreamingResponse(
            _sse_event_source(),
            headers={"Cache-Control": "no-cache"},
            media_type="text/event-stream",
        )

    @app.get("/api/debug/error")
    async def trigger_error():
        """Produce a test error to validate exception handling and request IDs."""
        logger.info("triggering test error…")
        raise RuntimeError("debug: induced failure")


def setup_instrumentation(app: FastAPI) -> None:
    """Install logging filter, middleware, exception handlers, CORS exposure, and debug routes."""
    # Ensure logs can reference %(request_id)s safely
    _install_log_filter_once()

    # Middleware: request/response logging + headers
    app.add_middleware(_RequestLoggingMiddleware)

    # Exception handlers
    _install_exception_handlers(app)

    # Expose tracing headers to browser
    try:
        # If CORS middleware exists, extend its expose headers via response headers in another middleware
        @app.middleware("http")
        async def _expose_headers(request: Request, call_next: Callable):
            response = await call_next(request)
            existing = response.headers.get("Access-Control-Expose-Headers", "")
            expose = {h.strip() for h in existing.split(",") if h.strip()}
            expose.update({"X-Request-ID", "X-Error-Code", "X-Process-Time"})
            response.headers["Access-Control-Expose-Headers"] = ", ".join(sorted(expose))
            return response
    except Exception:
        pass

    # Debug routes (SSE + test)
    _mount_debug_routes(app)

