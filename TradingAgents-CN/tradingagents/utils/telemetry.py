#!/usr/bin/env python3
"""
Lightweight telemetry/trace utility.

- Writes JSONL events to logs/telemetry/YYYYMMDD/events.jsonl
- Respects env TELEMETRY_ENABLED (default: true)
 - You can disable by setting TELEMETRY_ENABLED=false
- Designed to be dependency-free and safe in production paths

Usage:
  from tradingagents.utils.telemetry import telemetry
  telemetry.emit(event="multi_model.start", analysis_id="...", component="web", data={...})

  with telemetry.span(event="charting.generate", analysis_id=aid, component="charting") as span:
      ...
      span.update({"charts": 3})
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _is_enabled() -> bool:
    v = str(os.getenv("TELEMETRY_ENABLED", "true")).strip().lower()
    return v in ("1", "true", "yes", "on")


def _event_path() -> Path:
    day = datetime.now().strftime("%Y%m%d")
    p = Path("logs") / "telemetry" / day
    p.mkdir(parents=True, exist_ok=True)
    return p / "events.jsonl"


@dataclass
class Telemetry:
    enabled: bool = field(default_factory=_is_enabled)

    def emit(
        self,
        event: str,
        *,
        analysis_id: Optional[str] = None,
        component: Optional[str] = None,
        level: str = "info",
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            payload = {
                "ts": datetime.now().isoformat(timespec="milliseconds"),
                "event": event,
                "component": component or "general",
                "level": level,
            }
            if analysis_id:
                payload["analysis_id"] = analysis_id
            if data:
                # Ensure JSON-serializable (best-effort)
                try:
                    json.dumps(data)
                    payload["data"] = data
                except Exception:
                    payload["data"] = {"_str": str(data)}
            path = _event_path()
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # Silent fail; telemetry must not break business logic
            pass

    @contextmanager
    def span(
        self,
        event: str,
        *,
        analysis_id: Optional[str] = None,
        component: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        start = datetime.now()
        self.emit(event + ".start", analysis_id=analysis_id, component=component, data=data)
        span_state: Dict[str, Any] = {}
        try:
            yield Span(self, event, analysis_id, component, span_state)
            dur_ms = int((datetime.now() - start).total_seconds() * 1000)
            self.emit(
                event + ".end",
                analysis_id=analysis_id,
                component=component,
                data={"duration_ms": dur_ms, **span_state},
            )
        except Exception as e:
            dur_ms = int((datetime.now() - start).total_seconds() * 1000)
            self.emit(
                event + ".error",
                analysis_id=analysis_id,
                component=component,
                level="error",
                data={"duration_ms": dur_ms, "error": str(e), **span_state},
            )
            raise


@dataclass
class Span:
    telemetry: Telemetry
    event: str
    analysis_id: Optional[str]
    component: Optional[str]
    state: Dict[str, Any]

    def update(self, extra: Dict[str, Any]) -> None:
        try:
            self.state.update(extra or {})
        except Exception:
            pass


telemetry = Telemetry()

