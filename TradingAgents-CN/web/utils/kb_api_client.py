import asyncio
import os
from typing import Any

import requests


class KBApiClient:
    """Lightweight client for knowledge base RAG endpoints.

    Uses MARKET_API_BASE_URL to locate the API service (same container as market API).
    """

    def __init__(self, base_url: str | None = None, timeout: float = 15.0):
        # 优先使用显式配置；区分本地与Docker场景：
        # - 本地: 允许将 http://api:8000 回退到 localhost:8000 以便直连
        # - Docker: 保留 http://api:8000 以便通过容器网络访问 api 服务
        env_base = os.getenv("MARKET_API_BASE_URL")
        default_base = "http://localhost:8000"
        chosen = base_url or env_base or default_base
        in_docker = os.getenv("DOCKER_CONTAINER", "").lower() == "true"
        if (not in_docker) and isinstance(chosen, str) and (
            "://api:" in chosen or chosen.startswith("http://api:") or chosen.startswith("https://api:")
        ):
            chosen = default_base
        self.base_url = chosen.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self._inproc = None  # fallback in-process KB handler
        self._auto_detect_base_url()

    def _auto_detect_base_url(self) -> None:
        import re

        def _with_host(url: str, host: str) -> str:
            try:
                m = re.match(r"^(https?://)([^/:]+)(?::(\d+))?", url)
                if not m:
                    return url
                scheme = m.group(1)
                port = m.group(3) or "8000"
                return f"{scheme}{host}:{port}"
            except Exception:
                return url

        # Prefer local endpoints first
        candidates: list[str] = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://host.docker.internal:8000",
        ]
        # Base URL from env/config
        if self.base_url not in candidates:
            candidates.append(self.base_url)
        # Add local variants of service hostname forms
        if "://api:" in self.base_url or "://localhost" in self.base_url:
            for host in ("localhost", "127.0.0.1", "host.docker.internal"):
                v = _with_host(self.base_url, host)
                if v not in candidates:
                    candidates.append(v)
        # Extra user-specified candidates
        extra = os.getenv("MARKET_API_CANDIDATES")
        if extra:
            for x in extra.split(","):
                x = x.strip()
                if x and x not in candidates:
                    candidates.append(x)

        # Deduplicate while preserving order
        seen = set()
        uniq: list[str] = []
        for u in candidates:
            v = u.rstrip("/")
            if v not in seen:
                seen.add(v)
                uniq.append(v)

        # Probe for KB endpoints first, then /api/info, then /health
        best = None
        for base in uniq:
            try:
                r = self.session.get(f"{base}/api/kb/stats", timeout=1.5)
                if r.status_code < 400:
                    best = base
                    break
            except requests.exceptions.RequestException:
                pass
        if not best:
            for base in uniq:
                try:
                    r = self.session.get(f"{base}/api/info", timeout=1.5)
                    if r.status_code < 400:
                        best = base
                        break
                except requests.exceptions.RequestException:
                    pass
        if not best:
            for base in uniq:
                try:
                    r = self.session.get(f"{base}/health", timeout=1.5)
                    if r.status_code < 400:
                        best = base
                        break
                except requests.exceptions.RequestException:
                    pass

        if best:
            self.base_url = best
            return
        # No reachable API; enable in-process fallback for local dev, or when explicitly allowed
        fallback_env = os.getenv("KB_INPROC_FALLBACK", "true").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        try:
            in_docker = os.getenv("DOCKER_CONTAINER", "").lower() == "true"
        except Exception:
            in_docker = False
        if (not in_docker) or fallback_env:
            try:
                self._enable_inproc_fallback()
            except Exception:
                self._inproc = None
        # Final fallback to localhost when only service hostname was provided (for logs/visibility)
        if "://api:" in self.base_url:
            self.base_url = "http://localhost:8000"

    # -------- In-process fallback (when API unreachable) --------
    def _enable_inproc_fallback(self) -> None:
        if self._inproc is not None:
            return
        try:
            # Lazy, file-path import to avoid heavy package-level __init__ side effects
            from importlib.util import module_from_spec, spec_from_file_location
            from pathlib import Path as _Path

            fr_path = _Path(__file__).resolve().parents[2] / "tradingagents" / "ai" / "financial_rag.py"
            spec = spec_from_file_location("ta_financial_rag", fr_path)
            if not spec or not spec.loader:
                raise ImportError("Cannot locate financial_rag module")
            _mod = module_from_spec(spec)
            spec.loader.exec_module(_mod)  # type: ignore
            FinancialRAGSystem = getattr(_mod, "FinancialRAGSystem")

            try:
                import yaml  # type: ignore
            except Exception:
                yaml = None  # noqa: F841

            def _build_mm_config_safe() -> dict[str, Any] | None:
                # Try YAML config
                try:
                    from pathlib import Path
                    cfg_path = Path("config/multi_model_config.yaml")
                    if cfg_path.exists() and yaml:
                        with open(cfg_path, encoding="utf-8") as f:
                            raw = yaml.safe_load(f) or {}
                        providers = raw.get("providers", raw)
                        if isinstance(providers, dict) and any(
                            isinstance(v, dict) for v in providers.values()
                        ):
                            return providers
                except Exception:
                    pass
                # Env-based
                deepseek_key = os.getenv("DEEPSEEK_API_KEY")
                gemini_key = (
                    os.getenv("GEMINI_API_KEY")
                    or os.getenv("GOOGLE_AI_API_KEY")
                    or os.getenv("GOOGLE_API_KEY")
                )
                silicon_key = os.getenv("SILICONFLOW_API_KEY")
                cfg: dict[str, Any] = {
                    "routing": {"strategy": os.getenv("ROUTING_STRATEGY", "intelligent")},
                    "max_cost_per_session": float(os.getenv("MAX_COST_PER_SESSION", "1.0") or 1.0),
                    "enable_caching": True,
                }
                if deepseek_key:
                    cfg["deepseek"] = {
                        "enabled": True,
                        "api_key": deepseek_key,
                        "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                        "default_model": os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
                    }
                if gemini_key:
                    cfg["google_ai"] = {
                        "enabled": True,
                        "api_key": gemini_key,
                        "default_model": os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-pro"),
                    }
                if silicon_key:
                    cfg["siliconflow"] = {
                        "enabled": True,
                        "api_key": silicon_key,
                        "base_url": os.getenv(
                            "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
                        ),
                    }
                return cfg if any(k in cfg for k in ("deepseek", "google_ai", "siliconflow")) else None

            class _InProcKB:
                def __init__(self) -> None:
                    kb_path = os.getenv("TRADINGAGENTS_DATA_DIR", "./data")
                    kb_dir = os.path.join(kb_path, "financial_kb")
                    # Try to build a lightweight orchestrator if possible so LLM fallback works
                    orchestrator = None
                    try:
                        mm_cfg = _build_mm_config_safe()
                        if mm_cfg:
                            from importlib.util import module_from_spec, spec_from_file_location
                            # Import orchestrator by file path to avoid package-level side effects
                            _orc_path = _Path(__file__).resolve().parents[2] / "tradingagents" / "ai" / "llm_orchestrator.py"
                            _spec = spec_from_file_location("ta_llm_orchestrator", _orc_path)
                            if _spec and _spec.loader:
                                _mod_orc = module_from_spec(_spec)
                                _spec.loader.exec_module(_mod_orc)  # type: ignore
                                AIOrchestrator = getattr(_mod_orc, "AIOrchestrator")
                                orchestrator = AIOrchestrator(mm_cfg)
                    except Exception:
                        orchestrator = None
                    self.rag = FinancialRAGSystem(
                        knowledge_base_path=kb_dir, llm_orchestrator=orchestrator
                    )

                def kb_stats(self) -> dict[str, Any]:
                    return self.rag.get_system_stats()

                def kb_reindex(
                    self,
                    root_dir: str | None = None,
                    user_id: str | None = None,
                    symbol: str | None = None,
                    embedding_dim: int | None = None,
                    embedding_model: str | None = None,
                    embedding_provider: str | None = None,
                    files: list[str] | None = None,
                    dry_run: bool = False,
                ) -> dict[str, Any]:
                    # Normalize root_dir to a valid local path
                    try:
                        from pathlib import Path as _Path
                        _root = root_dir or os.getenv("LIBRARY_ROOT") or "./data/library"
                        rp = _Path(_root)
                        if not rp.exists():
                            # if container-style absolute path, fallback to local default
                            _root = os.getenv("LIBRARY_ROOT") or "./data/library"
                            rp2 = _Path(_root)
                            if not rp2.exists():
                                _root = "./data/library"
                    except Exception:
                        _root = root_dir or os.getenv("LIBRARY_ROOT") or "./data/library"

                    # Recreate RAG if embedding overrides provided
                    if any([embedding_dim, embedding_model, embedding_provider]):
                        kb_path = os.getenv("TRADINGAGENTS_DATA_DIR", "./data")
                        kb_dir = os.path.join(kb_path, "financial_kb")
                        # Recreate with overrides; keep orchestrator None
                        self.rag = FinancialRAGSystem(
                            knowledge_base_path=kb_dir,
                            llm_orchestrator=None,
                            embedding_config={
                                "provider": embedding_provider or None,
                                "model": embedding_model or None,
                                "dim": embedding_dim or None,
                            },
                        )
                    res = self.rag.ingest_library(
                        _root,
                        user_id=user_id,
                        symbol=symbol,
                        files=files,
                        dry_run=bool(dry_run),
                    )
                    return {"success": True, **res}

                def kb_query(
                    self,
                    query_text: str,
                    query_type: str = "general",
                    symbols: list[str] | None = None,
                    user_id: str | None = None,
                    top_k: int = 5,
                    relevance_threshold: float = 0.7,
                    history: list[dict[str, Any]] | None = None,
                    conversation_id: str | None = None,
                    agent_role: str | None = None,
                    agent_model: str | None = None,
                ) -> dict[str, Any]:
                    # Build standalone query (reuse simple server-side logic)
                    def _rewrite(q: str, hist: list[dict[str, Any]] | None) -> str:
                        if not hist:
                            return q
                        try:
                            recent = hist[-6:]
                            parts: list[str] = []
                            for m in recent:
                                role = (m.get("role") or "").lower()
                                content = (m.get("content") or "").strip()
                                if not content:
                                    continue
                                if role in {"user", "human"}:
                                    parts.append(f"User: {content}")
                                elif role in {"assistant", "ai", "system"}:
                                    parts.append(f"Assistant: {content}")
                            ctx = "\n".join(parts)
                            if len(ctx) > 1500:
                                ctx = ctx[-1500:]
                            return f"{q}\n\n[Conversation context]\n{ctx}"
                        except Exception:
                            return q

                    q2 = _rewrite(query_text, history)
                    # Call async rag.query
                    async def _do():
                        return await self.rag.query(
                            query_text=q2,
                            query_type=query_type,
                            symbols=symbols,
                            user_id=user_id,
                            top_k=top_k,
                            relevance_threshold=relevance_threshold,
                            agent_role=(agent_role or os.getenv('RAG_CHAT_AGENT_ROLE') or 'fundamental_expert'),
                            context={
                                'history_len': len(history) if history else 0,
                                'conversation_id': conversation_id,
                                'model_override': agent_model,
                            }
                        )

                    try:
                        resp = asyncio.run(_do())
                    except RuntimeError:
                        # If an event loop is already running (rare in Streamlit), try get_event_loop
                        loop = asyncio.get_event_loop()
                        resp = loop.run_until_complete(_do())

                    docs = []
                    try:
                        for d in resp.retrieved_documents or []:
                            raw_url = (d.metadata or {}).get('url')
                            if isinstance(raw_url, str) and raw_url.startswith('/'):
                                url = f"{self.base_url}{raw_url}"
                            else:
                                url = raw_url
                            docs.append({
                                'doc_id': d.doc_id,
                                'title': d.title,
                                'doc_type': d.doc_type,
                                'symbol': d.symbol,
                                'timestamp': d.timestamp.isoformat() if d.timestamp else None,
                                'relevance': d.relevance_score,
                                'preview': (d.content[:300] + '...') if d.content and len(d.content) > 300 else (d.content or ''),
                                'url': url,
                            })
                    except Exception:
                        pass
                    return {
                        'success': True,
                        'answer': resp.generated_response,
                        'sources': resp.sources,
                        'relevance_score': resp.confidence_score,
                        'documents_found': len(resp.retrieved_documents),
                        'documents': docs,
                        'metadata': resp.metadata,
                    }

            self._inproc = _InProcKB()
        except Exception:
            self._inproc = None

    def _ensure_inproc_if_down(self) -> None:
        """If remote API is unreachable, enable in-process fallback on demand."""
        if self._inproc is not None:
            return
        try:
            r = self.session.get(f"{self.base_url}/health", timeout=1.0)
            if r.status_code < 400:
                return
        except requests.exceptions.RequestException:
            pass
        # Try to enable fallback
        try:
            self._enable_inproc_fallback()
        except Exception:
            self._inproc = None

    def kb_stats(self) -> dict[str, Any]:
        if self._inproc:
            return self._inproc.kb_stats()
        try:
            r = self.session.get(f"{self.base_url}/api/kb/stats", timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException:
            # On connection issues, switch to in-proc fallback
            self._ensure_inproc_if_down()
            if self._inproc:
                return self._inproc.kb_stats()
            raise

    def kb_reindex(
        self,
        root_dir: str | None = None,
        user_id: str | None = None,
        symbol: str | None = None,
        embedding_dim: int | None = None,
        embedding_model: str | None = None,
        embedding_provider: str | None = None,
        files: list[str] | None = None,
        dry_run: bool | None = None,
        agent_role: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if root_dir:
            payload["root_dir"] = root_dir
        if user_id:
            payload["user_id"] = user_id
        if symbol:
            payload["symbol"] = symbol
        if embedding_dim:
            payload["embedding_dim"] = embedding_dim
        if embedding_model:
            payload["embedding_model"] = embedding_model
        if embedding_provider:
            payload["embedding_provider"] = embedding_provider
        if files:
            payload["files"] = files
        if dry_run is not None:
            payload["dry_run"] = bool(dry_run)
        if self._inproc:
            return self._inproc.kb_reindex(
                root_dir=root_dir,
                user_id=user_id,
                symbol=symbol,
                embedding_dim=embedding_dim,
                embedding_model=embedding_model,
                embedding_provider=embedding_provider,
                files=files,
                dry_run=bool(dry_run) if dry_run is not None else False,
            )
        try:
            r = self.session.post(
                f"{self.base_url}/api/kb/reindex", json=payload, timeout=self.timeout
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException:
            self._ensure_inproc_if_down()
            if self._inproc:
                return self._inproc.kb_reindex(
                    root_dir=root_dir,
                    user_id=user_id,
                    symbol=symbol,
                    embedding_dim=embedding_dim,
                    embedding_model=embedding_model,
                    embedding_provider=embedding_provider,
                    files=files,
                    dry_run=bool(dry_run) if dry_run is not None else False,
                )
            raise

    def kb_query(
        self,
        query_text: str,
        query_type: str = "general",
        symbols: list[str] | None = None,
        user_id: str | None = None,
        top_k: int = 5,
        relevance_threshold: float = 0.7,
        history: list[dict[str, Any]] | None = None,
        conversation_id: str | None = None,
        agent_role: str | None = None,
        agent_model: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query_text": query_text,
            "query_type": query_type,
            "top_k": top_k,
            "relevance_threshold": relevance_threshold,
        }
        if symbols:
            payload["symbols"] = symbols
        if user_id:
            payload["user_id"] = user_id
        if history:
            # Keep only role/content for safety
            safe_hist: list[dict[str, Any]] = []
            for m in history[-10:]:
                safe_hist.append({"role": m.get("role"), "content": m.get("content")})
            payload["history"] = safe_hist
        if conversation_id:
            payload["conversation_id"] = conversation_id
        if agent_role:
            payload["agent_role"] = agent_role
        if agent_model:
            payload["agent_model"] = agent_model
        if self._inproc:
            return self._inproc.kb_query(
                query_text=query_text,
                query_type=query_type,
                symbols=symbols,
                user_id=user_id,
                top_k=top_k,
                relevance_threshold=relevance_threshold,
                history=history,
                conversation_id=conversation_id,
                agent_role=agent_role,
                agent_model=agent_model,
            )
        try:
            r = self.session.post(
                f"{self.base_url}/api/kb/query", json=payload, timeout=self.timeout
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException:
            self._ensure_inproc_if_down()
            if self._inproc:
                return self._inproc.kb_query(
                    query_text=query_text,
                    query_type=query_type,
                    symbols=symbols,
                    user_id=user_id,
                    top_k=top_k,
                    relevance_threshold=relevance_threshold,
                    history=history,
                    conversation_id=conversation_id,
                    agent_role=agent_role,
                    agent_model=agent_model,
                )
            raise
