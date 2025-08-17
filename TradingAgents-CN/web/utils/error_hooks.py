#!/usr/bin/env python3
"""
Global Python-side error hooks for Streamlit runtime.

Installs:
  - sys.excepthook -> logger.exception
  - asyncio loop exception handler
  - warnings.showwarning -> logger.warning
"""

from __future__ import annotations

import asyncio
import sys
import traceback
import warnings
from logging import Logger


def install_global_error_hooks(logger: Logger) -> None:
    # sys.excepthook
    def _excepthook(exc_type, exc, tb):
        try:
            logger.exception("Uncaught exception", exc_info=(exc_type, exc, tb))
        except Exception:
            traceback.print_exception(exc_type, exc, tb)

    sys.excepthook = _excepthook

    # asyncio loop exceptions
    try:
        loop = asyncio.get_event_loop()

        def _async_handler(loop, context):  # type: ignore[override]
            msg = context.get("message") or str(context.get("exception"))
            logger.error(f"Async exception: {msg}", exc_info=context.get("exception"))

        loop.set_exception_handler(_async_handler)
    except Exception:
        pass

    # warnings -> logger.warning
    _orig_showwarning = warnings.showwarning

    def _showwarning(message, category, filename, lineno, file=None, line=None):
        try:
            logger.warning(f"{category.__name__}: {message} @ {filename}:{lineno}")
        finally:
            _orig_showwarning(message, category, filename, lineno, file=file, line=line)

    warnings.showwarning = _showwarning

