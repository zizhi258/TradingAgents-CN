#!/usr/bin/env python3
"""
Inject a lightweight browser-side debug helper for Streamlit pages.

When enabled, it:
  - Opens an EventSource to the API log SSE endpoint and logs incoming lines.
  - Optionally wraps window.fetch to log request/response failures.

Usage (in Streamlit):
    from web.utils.browser_debug import inject_browser_debug
    inject_browser_debug(api_base_url)
"""

from __future__ import annotations

import os
from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components


def inject_browser_debug(api_base_url: str | None = None, intercept_fetch: bool = True) -> None:
    """Inject small JS snippet into the Streamlit app to surface errors in F12.

    Controlled by env var WEB_DEBUG_CONSOLE=true to avoid noise in prod.
    """
    flag = os.getenv("WEB_DEBUG_CONSOLE", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not flag:
        return
    # Prefer a public/base URL suitable for browser access
    if not api_base_url:
        api_base_url = (
            os.getenv("MARKET_API_PUBLIC_BASE_URL")
            or os.getenv("MARKET_API_BASE_URL")
            or "http://localhost:8000"
        )

    # Very small, sandboxed iframe that runs JS for console instrumentation.
    # In browser, 'api' (Docker DNS) is not resolvable. Best-effort rewrite if needed.
    # JS code will still just use the provided base.
    js = dedent(
        f"""
        <script>
        (function() {{
          try {{
            let base = {api_base_url!r};
            try {{
              const u = new URL(base);
              if (u.hostname === 'api') {{
                // Map Docker DNS 'api' to current host with published port 8000
                u.hostname = window.location.hostname;
                u.port = u.port || '8000';
                base = u.toString();
              }}
            }} catch(e) {{}}
            const url = base.replace(/\/$/, '') + "/api/debug/logs/stream";
            const es = new EventSource(url, {{ withCredentials: false }});
            console.log('[TA] Debug log stream connecting to', url);
            es.onmessage = (evt) => {{
              try {{
                const obj = JSON.parse(evt.data);
                const lvl = (obj.level || 'INFO').toUpperCase();
                const tag = `[TA][{api_base_url!r}]`;
                if (lvl === 'ERROR' || lvl === 'CRITICAL') console.error(tag, obj);
                else if (lvl === 'WARNING' || lvl === 'WARN') console.warn(tag, obj);
                else console.log(tag, obj);
              }} catch (e) {{ console.warn('[TA] Bad log event', evt.data); }}
            }};
            es.onerror = (e) => {{ console.warn('[TA] Log stream error', e); }};
          }} catch (e) {{ console.warn('[TA] Debug injector failed', e); }}

          if ({str(bool(intercept_fetch)).lower()}) {{
            const _fetch = window.fetch;
            window.fetch = async function() {{
              const rid = Math.random().toString(16).slice(2,10);
              try {{
                const resp = await _fetch.apply(this, arguments);
                if (!resp.ok) {{
                  console.error('[TA][fetch]', rid, resp.status, resp.url, resp.headers.get('X-Request-ID'));
                }} else {{
                  const r = resp.headers.get('X-Request-ID');
                  if (r) console.debug('[TA][fetch]', rid, 'ok', resp.status, resp.url, r);
                }
                return resp;
              }} catch (err) {{
                console.error('[TA][fetch]', rid, 'network_error', err);
                throw err;
              }}
            }}
          }}

          // Global JS error surface to Console
          window.addEventListener('error', function (event) {{
            try {{
              console.error('[TA][window.onerror]', event.message, event.filename + ':' + event.lineno + ':' + event.colno, event.error && event.error.stack);
            }} catch (e) {{}}
          }});
          window.addEventListener('unhandledrejection', function (event) {{
            try {{
              console.error('[TA][unhandledrejection]', event.reason);
            }} catch (e) {{}}
          }});
        }})();
        </script>
        """
    )
    components.html(js, height=0)
