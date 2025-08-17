import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel, Field

"""Knowledge base API with safe, lazy imports to avoid heavy package side-effects.

Avoid importing tradingagents.ai package directly to prevent executing its
__init__ (which pulls in ML modules requiring joblib, etc.). Instead, load the
needed classes by file path when required.
"""

from importlib.util import module_from_spec, spec_from_file_location

router = APIRouter(prefix="/api/kb", tags=["knowledge_base"])
from tradingagents.utils.telemetry import telemetry


class ReindexRequest(BaseModel):
    root_dir: str | None = Field(
        default=None, description="Root directory for library ingestion"
    )
    user_id: str | None = None
    symbol: str | None = None
    embedding_dim: int | None = Field(
        default=None, description="Embedding dimensions (32-4096)"
    )
    embedding_model: str | None = Field(default=None, description="Embedding model id")
    embedding_provider: str | None = Field(
        default=None, description="Embedding provider"
    )
    files: list[str] | None = Field(default=None, description="Specific files to ingest under root")
    dry_run: bool = Field(default=False, description="Just simulate ingestion without writing vectors")


class QueryRequest(BaseModel):
    query_text: str
    query_type: str = "general"
    symbols: list[str] | None = None
    user_id: str | None = Field(default=None, description="Filter by user/tenant")
    top_k: int = 5
    relevance_threshold: float = 0.7
    # Multi-turn chat support
    history: list[dict[str, str]] | None = Field(
        default=None,
        description="List of prior messages: {role:'user|assistant', content:str}",
    )
    conversation_id: str | None = None
    agent_role: str | None = Field(
        default=None, description="Agent role for generation (e.g., fundamental_expert)"
    )
    agent_model: str | None = Field(
        default=None, description="Optional: override model for this query"
    )


_rag: Any | None = None
_orc: Any | None = None


def _load_rag_class():
    try:
        from pathlib import Path as _Path

        fr_path = _Path(__file__).resolve().parents[2] / "tradingagents" / "ai" / "financial_rag.py"
        spec = spec_from_file_location("ta_financial_rag", str(fr_path))
        if not spec or not spec.loader:
            raise ImportError("Cannot locate financial_rag module")
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return getattr(mod, "FinancialRAGSystem")
    except Exception as e:
        raise ImportError(f"Load FinancialRAGSystem failed: {e}")


def _load_orchestrator_class():
    try:
        from pathlib import Path as _Path

        orc_path = _Path(__file__).resolve().parents[2] / "tradingagents" / "ai" / "llm_orchestrator.py"
        spec = spec_from_file_location("ta_llm_orchestrator", str(orc_path))
        if not spec or not spec.loader:
            raise ImportError("Cannot locate llm_orchestrator module")
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        return getattr(mod, "AIOrchestrator")
    except Exception as e:
        raise ImportError(f"Load AIOrchestrator failed: {e}")


def _build_mm_config_safe() -> dict[str, Any] | None:
    """Build a minimal, safe Multi-Model config from env or YAML.

    Returns None if no provider is properly configured (to allow graceful fallback).
    """
    # Try YAML config first
    try:
        cfg_path = Path("config/multi_model_config.yaml")
        if cfg_path.exists():
            with open(cfg_path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            providers = raw.get("providers", raw)
            if isinstance(providers, dict) and any(
                isinstance(v, dict) for v in providers.values()
            ):
                return providers
    except Exception:
        pass

    # Env-based assembly (only enable providers with a key)
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


def _get_orchestrator() -> Any | None:
    global _orc
    if _orc is not None:
        return _orc
    try:
        mm_cfg = _build_mm_config_safe()
        if not mm_cfg:
            return None
        AIOrchestrator = _load_orchestrator_class()
        _orc = AIOrchestrator(mm_cfg)
        return _orc
    except Exception:
        return None


def _get_rag() -> Any:
    global _rag
    if _rag is None:
        kb_path = os.getenv("TRADINGAGENTS_DATA_DIR", "./data")
        kb_dir = os.path.join(kb_path, "financial_kb")
        # Ensure the KB directory is usable; if not, fall back to ./data
        try:
            from pathlib import Path as _Path

            p = _Path(kb_dir)
            p.mkdir(parents=True, exist_ok=True)
            # Writeability probe (avoid keeping the file)
            probe = p / ".kb_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except Exception:
            kb_path = "./data"
            kb_dir = os.path.join(kb_path, "financial_kb")
        FinancialRAGSystem = _load_rag_class()
        _rag = FinancialRAGSystem(
            knowledge_base_path=kb_dir, llm_orchestrator=_get_orchestrator()
        )
    return _rag


@router.get("/stats")
async def kb_stats() -> dict[str, Any]:
    rag = _get_rag()
    stats = rag.get_system_stats()
    try:
        telemetry.emit("kb.stats", component="kb", data={"stats": stats})
    except Exception:
        pass
    return stats


@router.post("/reindex")
async def kb_reindex(req: ReindexRequest) -> dict[str, Any]:
    global _rag
    rag = _get_rag()
    root = req.root_dir or os.getenv("LIBRARY_ROOT") or "./data/library"
    path_rewritten = False
    # If the provided path is not accessible inside the container, try to rewrite
    try:
        from pathlib import Path as _Path

        if isinstance(root, str):
            p = _Path(root)
            if not p.exists():
                lib_env = os.getenv("LIBRARY_ROOT") or "/app/data/library"
                # Heuristics: map host paths to container mount when obvious
                patterns = [
                    "TradingAgents-CN/data/library",
                    "\\\"TradingAgents-CN\\data\\library\\\"",
                ]
                if any(seg in root for seg in patterns) or root.startswith("/mnt/") or \
                    (len(root) > 2 and root[1] == ":"):
                    root = lib_env
                    path_rewritten = True
    except Exception:
        pass
    try:
        # Reinitialize RAG with embedding overrides if provided
        embedding_config = None
        if any([req.embedding_dim, req.embedding_model, req.embedding_provider]):
            kb_path = os.getenv("TRADINGAGENTS_DATA_DIR", "./data")
            kb_dir = os.path.join(kb_path, "financial_kb")
            embedding_config = {
                "provider": req.embedding_provider or None,
                "model": req.embedding_model or None,
                "dim": req.embedding_dim or None,
                # Keep API/base from env
            }
            FinancialRAGSystem = _load_rag_class()
            _rag = FinancialRAGSystem(
                knowledge_base_path=kb_dir, embedding_config=embedding_config
            )
            rag = _rag
        # Clean zero-sized KB file to avoid pickle load warnings
        try:
            kb_dir = rag.knowledge_base.storage_path
            kb_file = kb_dir / "knowledge_base.pkl"
            if kb_file.exists():
                size = kb_file.stat().st_size
                if size == 0:
                    kb_file.unlink(missing_ok=True)
        except Exception:
            pass
        telemetry.emit(
            "kb.reindex.start",
            component="kb",
            data={
                "root": root,
                "symbol": req.symbol,
                "files": req.files,
                "dry_run": bool(req.dry_run),
                "path_rewritten": path_rewritten,
            },
        )
        result = rag.ingest_library(
            root,
            user_id=req.user_id,
            symbol=req.symbol,
            files=req.files,
            dry_run=bool(req.dry_run),
        )
        extra: dict[str, Any] = {}
        if path_rewritten:
            extra["path_rewritten"] = True
            extra["effective_root"] = root
        
        # Enhanced logging for debugging
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"Reindexing result: {result}")
        extra["ingestion_log"] = result # Add full result to response

        out = {"success": True, **result, **extra}
        try:
            telemetry.emit("kb.reindex.done", component="kb", data=out)
        except Exception:
            pass
        return out
    except Exception as e:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.error(f"Reindexing failed: {e}", exc_info=True)
        try:
            telemetry.emit(
                "kb.reindex.error", component="kb", level="error", data={"error": str(e)}
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def kb_upload(
    file: UploadFile = File(...),
    user_id: str | None = Form(default=None),
    symbol: str | None = Form(default=None),
    subdir: str | None = Form(default=None),
    ingest: bool = Form(default=True),
) -> dict[str, Any]:
    """Upload a file into the library root and optionally trigger ingestion.

    Saves to LIBRARY_ROOT/(subdir or 'uploads')/YYYY-MM-DD/ and, if ingest=True,
    calls rag.ingest_library on that directory for immediate availability.
    """
    try:
        lib_root = Path(os.getenv("LIBRARY_ROOT") or "./data/library").resolve()
        day = os.getenv("KB_UPLOAD_DATE") or ""
        if not day:
            from datetime import datetime as _dt

            day = _dt.now().strftime("%Y-%m-%d")
        target = lib_root / (subdir or "uploads") / day
        target.mkdir(parents=True, exist_ok=True)

        dest = target / file.filename
        content = await file.read()
        dest.write_bytes(content)

        res: dict[str, Any] = {
            "success": True,
            "saved_path": str(dest),
            "size": len(content),
        }

        if ingest:
            rag = _get_rag()
            idx = rag.ingest_library(str(target), user_id=user_id, symbol=symbol)
            res.update({"ingestion": idx})

        try:
            telemetry.emit(
                "kb.upload", component="kb", data={"path": str(dest), "size": len(content)}
            )
        except Exception:
            pass
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_standalone_query(
    query_text: str, history: list[dict[str, str]] | None
) -> str:
    """Naive query rewrite using recent chat history to make current question standalone.

    Keeps last few turns and truncates overly long context to avoid payload bloat.
    """
    if not history:
        return query_text
    try:
        # Keep last 6 messages max
        recent = history[-6:]
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
        # Hard truncate context to ~1500 chars to keep embeddings efficient
        if len(ctx) > 1500:
            ctx = ctx[-1500:]
        return f"{query_text}\n\n[Conversation context]\n{ctx}"
    except Exception:
        return query_text


@router.post("/query")
async def kb_query(req: QueryRequest, request: Request) -> dict[str, Any]:
    rag = _get_rag()
    try:
        # Build standalone query using history for multi-turn context
        standalone_q = _build_standalone_query(req.query_text, req.history)
        telemetry.emit(
            "kb.query.start",
            component="kb",
            data={
                "len_history": len(req.history) if req.history else 0,
                "top_k": req.top_k,
                "threshold": req.relevance_threshold,
                "agent_role": req.agent_role,
            },
        )
        resp = await rag.query(
            query_text=standalone_q,
            query_type=req.query_type,
            symbols=req.symbols,
            top_k=req.top_k,
            relevance_threshold=req.relevance_threshold,
            user_id=req.user_id,
            agent_role=(
                req.agent_role or os.getenv("RAG_CHAT_AGENT_ROLE") or "fundamental_expert"
            ),
            context={
                "history_len": len(req.history) if req.history else 0,
                "conversation_id": req.conversation_id,
                "model_override": req.agent_model,
            },
        )
        # Build document summaries for UI preview
        base = str(request.base_url).rstrip("/")
        docs = []
        try:
            for d in resp.retrieved_documents or []:
                raw_url = (d.metadata or {}).get("url")
                # Convert relative /library path to absolute API URL for direct clicking
                abs_url = None
                try:
                    if isinstance(raw_url, str) and raw_url.startswith("/"):
                        abs_url = f"{base}{raw_url}"
                except Exception:
                    abs_url = raw_url
                docs.append(
                    {
                        "doc_id": d.doc_id,
                        "title": d.title,
                        "doc_type": d.doc_type,
                        "symbol": d.symbol,
                        "timestamp": d.timestamp.isoformat() if d.timestamp else None,
                        "relevance": d.relevance_score,
                        "preview": (
                            (d.content[:300] + "...")
                            if d.content and len(d.content) > 300
                            else (d.content or "")
                        ),
                        "url": abs_url,
                        "path": (d.metadata or {}).get("path"),
                    }
                )
        except Exception:
            pass
        out = {
            "success": True,
            "answer": resp.generated_response,
            "sources": resp.sources,
            "relevance_score": resp.confidence_score,
            "documents_found": len(resp.retrieved_documents),
            "documents": docs,
            "metadata": resp.metadata,
        }
        try:
            telemetry.emit(
                "kb.query.done",
                component="kb",
                data={
                    "documents_found": out["documents_found"],
                    "relevance": out.get("relevance_score"),
                },
            )
        except Exception:
            pass
        return out
    except Exception as e:
        try:
            telemetry.emit(
                "kb.query.error", component="kb", level="error", data={"error": str(e)}
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
