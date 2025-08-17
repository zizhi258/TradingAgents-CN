#!/usr/bin/env python3
"""
Lightweight HTTP client instrumentation for requests.

Enable via env var HTTP_DEBUG=true to log outgoing requests/responses
with URL, method, status, duration, and selected headers.
"""

from __future__ import annotations

import os
import time
from typing import Any

from .logging_manager import get_logger


def install_requests_debug_logging() -> None:
    try:
        import requests  # type: ignore
    except Exception:
        return

    if os.getenv("HTTP_DEBUG", "false").strip().lower() not in {"1", "true", "yes", "on"}:
        return

    log = get_logger("http.requests")

    # Monkeypatch Session.request once
    orig_request = requests.sessions.Session.request

    def _wrapped(self, method: str, url: str, *args: Any, **kwargs: Any):  # type: ignore[override]
        start = time.perf_counter()
        rid = kwargs.get("headers", {}).get("X-Request-ID") if isinstance(kwargs.get("headers"), dict) else None
        log.info(f"HTTP -> {method} {url}", extra={"request_id": rid})
        try:
            resp = orig_request(self, method, url, *args, **kwargs)
        except Exception as e:
            dur = int((time.perf_counter() - start) * 1000)
            log.error(f"HTTP !! {method} {url} failed after {dur}ms: {e}", extra={"request_id": rid})
            raise
        dur = int((time.perf_counter() - start) * 1000)
        rid_resp = resp.headers.get("X-Request-ID")
        log.info(
            f"HTTP <- {method} {url} {resp.status_code} {dur}ms",
            extra={"request_id": rid or rid_resp},
        )
        return resp

    if getattr(install_requests_debug_logging, "_patched", False):
        return
    requests.sessions.Session.request = _wrapped  # type: ignore[assignment]
    install_requests_debug_logging._patched = True  # type: ignore[attr-defined]

