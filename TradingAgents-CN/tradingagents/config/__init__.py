"""
配置管理模块（懒加载）

为避免导入副作用（例如在导入任意子模块时就初始化全局配置并触发依赖），
此处不在模块导入时立即导入 `config_manager`，而是通过 __getattr__ 懒加载。

注意：在 __getattr__ 内部使用 importlib.import_module 加载子模块，
避免使用 "from . import config_manager" 造成递归触发 __getattr__。
"""

from typing import TYPE_CHECKING, Any
import importlib
import sys

__all__ = [
    "config_manager",
    "token_tracker",
    "ModelConfig",
    "PricingConfig",
    "UsageRecord",
]

if TYPE_CHECKING:  # 供类型检查工具使用，不在运行时执行重载
    from .config_manager import (  # noqa: F401
        ModelConfig,
        PricingConfig,
        UsageRecord,
        config_manager,
        token_tracker,
    )


def __getattr__(name: str) -> Any:
    """在首次访问时再加载 `config_manager` 模块中的对象。"""
    if name in __all__:
        # 使用 importlib 避免递归触发 __getattr__
        _cfg_module = importlib.import_module('.config_manager', __name__)
        value = getattr(_cfg_module, name)
        # 缓存到当前包的全局命名空间，后续访问不再触发 __getattr__
        globals()[name] = value
        return value
    raise AttributeError(f"module 'tradingagents.config' has no attribute {name!r}")


def __dir__():
    # 便于交互式探索
    return sorted(list(globals().keys()) + __all__)
