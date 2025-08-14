"""
Model catalog utilities for UI
Unify model options across panels by reading shared config or backend specs.
"""

from __future__ import annotations

from pathlib import Path
from typing import List


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_models_from_yaml() -> List[str]:
    """Try to load SiliconFlow models from config/multi_model_config.yaml.

    Returns a list of model names (may be empty if file or PyYAML unavailable).
    """
    try:
        import yaml  # type: ignore
    except Exception:
        return []

    cfg_path = _project_root() / "config" / "multi_model_config.yaml"
    if not cfg_path.exists():
        return []

    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        catalog = (raw.get("model_catalog") or {}).get("siliconflow") or []
        names: List[str] = []
        for item in catalog:
            if isinstance(item, dict) and item.get("name"):
                names.append(str(item["name"]))
            elif isinstance(item, str):
                names.append(item)
        return names
    except Exception:
        return []


def _load_models_from_backend() -> List[str]:
    """Fallback: read supported models from backend SiliconFlow client class."""
    try:
        from tradingagents.api.siliconflow_client import SiliconFlowClient  # type: ignore

        return list(SiliconFlowClient.SUPPORTED_MODELS.keys())
    except Exception:
        return []


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def get_siliconflow_models() -> List[str]:
    """Return a unified list of SiliconFlow chat/reasoning models for UI.

    Priority:
    1) config/multi_model_config.yaml -> model_catalog.siliconflow[].name
    2) tradingagents.api.siliconflow_client.SiliconFlowClient.SUPPORTED_MODELS
    3) Minimal hardcoded defaults (as last resort)
    """
    names = _load_models_from_yaml()
    if not names:
        names = _load_models_from_backend()
    if not names:
        names = [
            "deepseek-ai/DeepSeek-R1",
            "deepseek-ai/DeepSeek-V3",
            "zai-org/GLM-4.5",
            "moonshotai/Kimi-K2-Instruct",
        ]
    return _dedupe_preserve_order([str(n) for n in names if isinstance(n, str) and n.strip()])


def get_deepseek_models() -> List[str]:
    """Return DeepSeek models for UI, from backend or minimal defaults."""
    try:
        from tradingagents.api.deepseek_client import DeepSeekClient  # type: ignore

        names = list(DeepSeekClient.SUPPORTED_MODELS.keys())
    except Exception:
        names = ["deepseek-chat", "deepseek-reasoner"]
    return _dedupe_preserve_order([n for n in names if isinstance(n, str) and n.strip()])


def get_google_models() -> List[str]:
    """Return Google Gemini models for UI, from backend or minimal defaults."""
    try:
        from tradingagents.api.google_ai_client import GoogleAIClient  # type: ignore

        names = list(GoogleAIClient.SUPPORTED_MODELS.keys())
    except Exception:
        names = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
    return _dedupe_preserve_order([n for n in names if isinstance(n, str) and n.strip()])


def get_openrouter_models() -> List[str]:
    """Return a curated list of OpenRouter models for UI.

    We do not hit network here; provide a sensible default catalog that
    includes Gemini via OpenRouter plus a few common families. Users can
    always input a custom model id (provider/model) in the UI to override.
    """
    # Preferred Gemini via OpenRouter first
    defaults = [
        # Google Gemini family (via OpenRouter)
        "google/gemini-2.5-pro",
        "google/gemini-2.0-flash",
        "google/gemini-1.5-pro",
        # Anthropic Claude family
        "anthropic/claude-3.5-sonnet",
        "anthropic/claude-3.5-haiku",
        # OpenAI o-series
        "openai/o4-mini-high",
        "openai/o3-pro",
        # Meta Llama
        "meta-llama/llama-3.2-90b-instruct",
        # Mistral
        "mistralai/mistral-large-latest",
    ]
    return _dedupe_preserve_order([n for n in defaults if isinstance(n, str) and n.strip()])
