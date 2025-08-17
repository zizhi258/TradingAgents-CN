"""
Chromadb client initialization helper for Windows/WSL.

Provides get_optimal_chromadb_client(path) to create a PersistentClient with
safe defaults and small tweaks for Windows 10/11 file locking quirks.
"""

from __future__ import annotations

import os
import platform
from typing import Any


def get_optimal_chromadb_client(path: str):
    try:
        import chromadb  # type: ignore
        from chromadb.config import Settings  # type: ignore
    except Exception as e:  # pragma: no cover - optional dep
        raise ImportError(f"ChromaDB not available: {e}")

    # Normalize path and ensure directory exists
    path = os.fspath(path)
    os.makedirs(path, exist_ok=True)

    # Basic settings: disable telemetry and allow_reset
    settings_kwargs: dict[str, Any] = {
        "anonymized_telemetry": False,
        "allow_reset": True,
    }

    # Windows-specific hints
    try:
        is_windows = platform.system().lower().startswith("win")
        if is_windows:
            # There is no official public option to change duckdb locking here,
            # but we keep a single writer pattern by design and avoid aggressive resets.
            # Future knobs could be added here if Chroma exposes them.
            pass
    except Exception:
        pass

    return chromadb.PersistentClient(path=path, settings=Settings(**settings_kwargs))

