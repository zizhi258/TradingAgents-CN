"""
Unified Streamlit session state helper with namespace support.

This module provides a minimal, safe API to read/write/clear session state
within logical namespaces, so pages/components avoid key collisions and
"global" clears.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

try:
    import streamlit as st  # type: ignore
except Exception:  # pragma: no cover
    st = None  # Allows non-Streamlit contexts to import safely


NS_PREFIX = "__ns__"


def _ns_key(ns: str) -> str:
    return f"{NS_PREFIX}:{ns}"


def ensure_ns(ns: str) -> Dict[str, Any]:
    """Ensure and return the namespace dict stored in session_state."""
    if st is None:
        # Fallback to a temporary in-memory store if Streamlit not available
        # (kept minimal on purpose)
        raise RuntimeError("Streamlit session_state is not available in this context")
    key = _ns_key(ns)
    if key not in st.session_state or not isinstance(st.session_state.get(key), dict):
        st.session_state[key] = {}
    return st.session_state[key]


def get(ns: str, key: str, default: Any = None) -> Any:
    """Get a value from a namespace, returning default if not present."""
    try:
        return ensure_ns(ns).get(key, default)
    except Exception:
        return default


def set(ns: str, key: str, value: Any) -> None:
    """Set a value into a namespace."""
    ensure_ns(ns)[key] = value


def pop(ns: str, key: str, default: Any = None) -> Any:
    """Pop a value from a namespace, returning default if missing."""
    return ensure_ns(ns).pop(key, default)


def clear(ns: str) -> None:
    """Clear only the given namespace, leaving others intact."""
    key = _ns_key(ns)
    if st is not None and key in st.session_state:
        try:
            st.session_state[key].clear()
        except Exception:
            st.session_state[key] = {}


def as_dict(ns: str) -> Dict[str, Any]:
    """Return a shallow copy of the namespace dict for inspection/logging."""
    return dict(ensure_ns(ns))


def move(ns_from: str, ns_to: str, *, overwrite: bool = False) -> None:
    """Move all keys from one namespace to another."""
    src = ensure_ns(ns_from)
    dst = ensure_ns(ns_to)
    for k, v in src.items():
        if overwrite or k not in dst:
            dst[k] = v
    src.clear()

