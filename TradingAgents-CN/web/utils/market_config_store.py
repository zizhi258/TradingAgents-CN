"""
全球市场分析配置持久化
提供简单可靠的本地文件方案（按浏览器指纹隔离），用于保存/加载用户的全球市场分析配置预设。

说明：
- 数据存放于 ./data/market_configs/<fingerprint>.json
- 仅保存一份“最近保存配置”（last_saved），并内置若干默认预设
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

from tradingagents.utils.logging_manager import get_logger

# 复用文件会话指纹，按浏览器隔离配置
from .file_session_manager import file_session_manager

logger = get_logger('market_config_store')


class MarketConfigStore:
    """全球市场分析配置存储器（基于文件）"""

    def __init__(self, base_dir: str = "./data/market_configs") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ---------- helpers ----------
    def _get_fingerprint(self) -> str:
        try:
            # 使用 FileSessionManager 的浏览器指纹
            return file_session_manager._get_browser_fingerprint()  # noqa: SLF001
        except Exception:
            return "global"

    def _get_user_file(self) -> Path:
        fingerprint = self._get_fingerprint()
        return self.base_dir / f"{fingerprint}.json"

    def _read_user_data(self) -> Dict[str, Any]:
        file_path = self._get_user_file()
        if not file_path.exists():
            return {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取配置文件失败: {e}")
            return {}

    def _write_user_data(self, data: Dict[str, Any]) -> None:
        file_path = self._get_user_file()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"写入配置文件失败: {e}")

    # ---------- public APIs ----------
    def save_last_config(self, config: Dict[str, Any]) -> None:
        """保存“最近保存配置”。"""
        data = self._read_user_data()
        data['last_saved'] = config
        self._write_user_data(data)
        logger.info("已保存全球市场分析最近配置")

    def load_last_config(self) -> Optional[Dict[str, Any]]:
        """加载“最近保存配置”，不存在返回None。"""
        data = self._read_user_data()
        return data.get('last_saved')

    def get_builtin_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """获取内置预设配置。"""
        presets = self._builtin_presets()
        return presets.get(name)

    def list_builtin_preset_names(self) -> list[str]:
        presets = self._builtin_presets()
        return list(presets.keys())

    # ---------- presets ----------
    def _builtin_presets(self) -> Dict[str, Dict[str, Any]]:
        """内置预设，保持与增强配置面板字段一致。"""
        default = {
            'market_type': 'A股',
            'preset_type': '沪深300',
            'scan_depth': 3,
            'budget_limit': 10.0,
            'stock_limit': 100,
            'time_range': '1月',
            'ai_model_config': {
                'model': 'gemini-2.0-flash',
                'use_ensemble': False,
                'temperature': 0.3,
                'max_tokens': 4000,
            },
            'analysis_focus': {
                'technical': True,
                'fundamental': True,
                'valuation': True,
                'news': False,
                'sentiment': False,
                'social': False,
                'risk': True,
                'liquidity': False,
                'macro': False,
            },
            'advanced_options': {
                'enable_monitoring': True,
                'enable_notification': False,
                'save_intermediate': False,
                'parallel_processing': True,
                'auto_retry': True,
                'cache_results': True,
            },
        }

        fast = dict(default)
        fast.update({'scan_depth': 2, 'budget_limit': 5.0, 'stock_limit': 50})

        deep = dict(default)
        deep.update({'scan_depth': 4, 'budget_limit': 25.0, 'stock_limit': 100, 'time_range': '3月'})

        full = dict(default)
        full.update({'scan_depth': 5, 'budget_limit': 50.0, 'stock_limit': 200, 'time_range': '6月'})

        return {
            '默认配置': default,
            '快速扫描 (成本优先)': fast,
            '深度分析 (质量优先)': deep,
            '全面调研 (完整分析)': full,
        }


_shared_store: Optional[MarketConfigStore] = None


def get_config_store() -> MarketConfigStore:
    global _shared_store
    if _shared_store is None:
        _shared_store = MarketConfigStore()
    return _shared_store


