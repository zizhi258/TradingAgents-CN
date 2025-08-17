"""
Debate metrics collection (lightweight, optional).

Records simple counts for evidence usage and judge flip rate.
Safe to import; if disabled, calls are no-ops.
"""

from __future__ import annotations

import os
import threading
from typing import Any

_lock = threading.Lock()
_store: dict[str, Any] = {
    "citations": {
        "bull": {"with": 0, "without": 0},
        "bear": {"with": 0, "without": 0},
        "risky": {"with": 0, "without": 0},
        "safe": {"with": 0, "without": 0},
        "neutral": {"with": 0, "without": 0},
    },
    "judge": {
        "position_flip_count": 0,
        "position_checks": 0,
    },
}


def _enabled() -> bool:
    v = os.getenv(
        "ENABLE_DEBATE_METRICS", os.getenv("ENABLE_PERFORMANCE_MONITORING", "true")
    )
    return str(v).strip().lower() in {"1", "true", "yes", "on"}


def record_citation(agent: str, has_citation: bool) -> None:
    if not _enabled():
        return
    agent = agent.lower()
    key = "with" if has_citation else "without"
    with _lock:
        if agent not in _store["citations"]:
            _store["citations"][agent] = {"with": 0, "without": 0}
        _store["citations"][agent][key] += 1


def record_judge_flip(flip: bool) -> None:
    if not _enabled():
        return
    with _lock:
        _store["judge"]["position_checks"] += 1
        if flip:
            _store["judge"]["position_flip_count"] += 1


def get_metrics() -> dict[str, Any]:
    with _lock:
        data = {"citations": {}, "judge": dict(_store["judge"])}
        # compute ratios
        for agent, rec in _store["citations"].items():
            total = rec["with"] + rec["without"]
            ratio = (rec["with"] / total) if total > 0 else 0.0
            data["citations"][agent] = {
                "with": rec["with"],
                "without": rec["without"],
                "evidence_ratio": ratio,
            }
        checks = data["judge"].get("position_checks", 0)
        flips = data["judge"].get("position_flip_count", 0)
        data["judge"]["position_flip_rate"] = (flips / checks) if checks > 0 else 0.0
        return data
