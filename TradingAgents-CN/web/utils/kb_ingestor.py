#!/usr/bin/env python3
"""
知识库离线索引管道（Web）

在分析完成后，将结果导出为Markdown并写入文库目录，然后触发RAG索引重建，
确保后续对话基于已向量化的离线索引，而非临时在线索引。
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("kb_ingestor")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _get_library_root() -> Path:
    base = os.getenv("LIBRARY_ROOT") or os.getenv("TRADINGAGENTS_DATA_DIR")
    # Prefer local path if container-style absolute path is not present
    if base:
        p = Path(base)
        if not p.is_absolute():
            p = _project_root() / p
        # If absolute but not exists (likely docker-only path), fall back
        if not p.exists():
            p = _project_root() / "data" / "library"
    else:
        p = _project_root() / "data" / "library"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_full_report_md(results: dict[str, Any], out_dir: Path) -> Path | None:
    try:
        # 使用已有的Markdown生成逻辑，保证结构一致
        from .report_exporter import report_exporter

        md = report_exporter.generate_markdown_report(results)
        dest = out_dir / "00_full_analysis.md"
        dest.write_text(md, encoding="utf-8")
        return dest
    except Exception as e:
        logger.warning(f"生成完整Markdown失败：{e}")
        return None


def export_results_to_library(results: dict[str, Any]) -> dict[str, Any]:
    """将分析结果导出到文库目录（仅写文件，不进行向量化）。

    返回 { 'target_dir': str, 'files': list[str] }
    """
    symbol = str(results.get("stock_symbol") or "UNKNOWN").upper()
    # 尽力获取日期（用于分目录）
    ts = results.get("analysis_date") or datetime.now().isoformat()
    try:
        date_str = str(ts)[:10]
    except Exception:
        date_str = datetime.now().strftime("%Y-%m-%d")

    lib_root = _get_library_root()
    target_dir = _ensure_dir(lib_root / "analyses" / symbol / date_str)
    written: list[str] = []

    # 1) 写主报告
    full = _write_full_report_md(results, target_dir)
    if full:
        written.append(str(full))

    # 2) 写分模块报告（沿用已有的保存逻辑，再复制到文库）
    try:
        from .report_exporter import save_modular_reports_to_results_dir

        modular = save_modular_reports_to_results_dir(results, symbol)
        for _, src in (modular or {}).items():
            try:
                src_p = Path(src)
                dst_p = target_dir / src_p.name
                shutil.copy2(src_p, dst_p)
                written.append(str(dst_p))
            except Exception as ce:
                logger.debug(f"复制模块文件失败 {src}: {ce}")
    except Exception as e:
        logger.debug(f"生成/复制分模块报告失败：{e}")

    logger.info(f"📚 已导出分析到文库: {target_dir}，文件数={len(written)}")
    return {"target_dir": str(target_dir), "files": written}


def trigger_kb_reindex(root_dir: str, symbol: str | None = None) -> dict[str, Any]:
    """调用KB API或进程内后备进行索引重建（仅针对指定目录）。"""
    try:
        from .kb_api_client import KBApiClient

        client = KBApiClient()
        # 默认使用SiliconFlow嵌入配置；允许通过环境变量覆盖
        try:
            emb_dim = int(os.getenv("EMBEDDING_DIM", "4096"))
        except Exception:
            emb_dim = 4096
        emb_model = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
        emb_provider = os.getenv("EMBEDDING_PROVIDER", "siliconflow")

        res = client.kb_reindex(
            root_dir=root_dir,
            user_id=os.getenv("KB_USER_ID") or "web",
            symbol=symbol,
            embedding_dim=emb_dim,
            embedding_model=emb_model,
            embedding_provider=emb_provider,
        )
        logger.info(
            f"✅ KB索引完成: added={res.get('added')} skipped={res.get('skipped')}"
        )
        return {"success": True, **res}
    except Exception as e:
        logger.error(f"❌ 触发KB索引失败: {e}")
        return {"success": False, "error": str(e)}


def ingest_analysis_results(results: dict[str, Any]) -> dict[str, Any]:
    """完整流程：导出 -> 触发KB索引（离线向量化）。"""
    try:
        out = export_results_to_library(results)
        symbol = str(results.get("stock_symbol") or "").upper() or None
        idx = trigger_kb_reindex(out["target_dir"], symbol=symbol)
        return {"export": out, "index": idx}
    except Exception as e:
        logger.error(f"KB离线索引流程失败: {e}")
        return {"export": {"success": False, "error": str(e)}, "index": {"success": False, "error": str(e)}}
