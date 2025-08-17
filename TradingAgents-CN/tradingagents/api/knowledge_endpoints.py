import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tradingagents.ai.financial_rag import FinancialRAGSystem
from tradingagents.ai.llm_orchestrator import AIOrchestrator

router = APIRouter(prefix="/api/kb", tags=["knowledge_base"])


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


class QueryRequest(BaseModel):
    query_text: str
    query_type: str = "general"
    symbols: list[str] | None = None
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


_rag: FinancialRAGSystem | None = None
_orc: AIOrchestrator | None = None


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


def _get_orchestrator() -> AIOrchestrator | None:
    global _orc
    if _orc is not None:
        return _orc
    try:
        mm_cfg = _build_mm_config_safe()
        if not mm_cfg:
            return None
        _orc = AIOrchestrator(mm_cfg)
        return _orc
    except Exception:
        return None


def _get_rag() -> FinancialRAGSystem:
    global _rag
    if _rag is None:
        kb_path = os.getenv("TRADINGAGENTS_DATA_DIR", "./data")
        kb_dir = os.path.join(kb_path, "financial_kb")
        _rag = FinancialRAGSystem(
            knowledge_base_path=kb_dir, llm_orchestrator=_get_orchestrator()
        )
    return _rag


@router.get("/stats")
async def kb_stats() -> dict[str, Any]:
    rag = _get_rag()
    return rag.get_system_stats()


@router.post("/reindex")
async def kb_reindex(req: ReindexRequest) -> dict[str, Any]:
    global _rag
    rag = _get_rag()
    root = req.root_dir or os.getenv("LIBRARY_ROOT") or "./data/library"
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
            _rag = FinancialRAGSystem(
                knowledge_base_path=kb_dir, embedding_config=embedding_config
            )
            rag = _rag
        result = rag.ingest_library(root, user_id=req.user_id, symbol=req.symbol)
        return {"success": True, **result}
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
async def kb_query(req: QueryRequest) -> dict[str, Any]:
    rag = _get_rag()
    try:
        # Build standalone query using history for multi-turn context
        standalone_q = _build_standalone_query(req.query_text, req.history)
        resp = await rag.query(
            query_text=standalone_q,
            query_type=req.query_type,
            symbols=req.symbols,
            top_k=req.top_k,
            relevance_threshold=req.relevance_threshold,
            agent_role=(
                req.agent_role or os.getenv("RAG_CHAT_AGENT_ROLE") or "fundamental_expert"
            ),
            context={
                "history_len": len(req.history) if req.history else 0,
                "conversation_id": req.conversation_id,
            },
        )
        # Build document summaries for UI preview
        docs = []
        try:
            for d in resp.retrieved_documents or []:
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
                        "url": (d.metadata or {}).get("url"),
                    }
                )
        except Exception:
            pass
        return {
            "success": True,
            "answer": resp.generated_response,
            "sources": resp.sources,
            "relevance_score": resp.confidence_score,
            "documents_found": len(resp.retrieved_documents),
            "documents": docs,
            "metadata": resp.metadata,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
