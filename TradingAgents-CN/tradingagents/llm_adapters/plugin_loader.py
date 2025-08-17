#!/usr/bin/env python3
"""
LLM适配器插件加载器
支持动态加载和注册自定义LLM适配器
"""

import importlib
import pkgutil
from abc import ABC, abstractmethod
from pathlib import Path

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("llm_adapters")


class BaseLLMAdapter(ABC):
    """LLM适配器基类

    所有自定义LLM适配器必须继承此类并实现相应方法
    """

    # 适配器元数据（子类必须定义）
    name: str = None  # 适配器唯一标识
    provider: str = None  # 提供商名称
    supported_models: list[str] = []  # 支持的模型列表

    def __init__(self, model: str = None, api_key: str = None, **kwargs):
        """初始化适配器

        Args:
            model: 模型名称
            api_key: API密钥
            **kwargs: 其他配置参数
        """
        self.model = model
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    def invoke(self, messages: list[dict], **kwargs) -> str:
        """同步调用模型

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 额外参数（temperature, max_tokens等）

        Returns:
            模型响应文本
        """
        pass

    @abstractmethod
    async def ainvoke(self, messages: list[dict], **kwargs) -> str:
        """异步调用模型

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            模型响应文本
        """
        pass

    def stream(self, messages: list[dict], **kwargs):
        """流式调用模型

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            响应片段
        """
        # 默认实现：调用invoke并返回完整结果
        result = self.invoke(messages, **kwargs)
        yield result

    @classmethod
    def get_required_env_vars(cls) -> list[str]:
        """获取必需的环境变量列表

        Returns:
            环境变量名称列表
        """
        return []

    @classmethod
    def validate_config(cls, config: dict) -> bool:
        """验证配置是否有效

        Args:
            config: 配置字典

        Returns:
            配置是否有效
        """
        return True

    def get_usage_stats(self) -> dict:
        """获取使用统计信息

        Returns:
            包含token使用量、成本等信息的字典
        """
        return {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}


class LLMAdapterRegistry:
    """LLM适配器注册表

    管理所有可用的LLM适配器
    """

    _adapters: dict[str, type[BaseLLMAdapter]] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, adapter_class: type[BaseLLMAdapter]):
        """注册适配器

        Args:
            adapter_class: 适配器类
        """
        if not issubclass(adapter_class, BaseLLMAdapter):
            raise ValueError(f"{adapter_class} 必须继承自 BaseLLMAdapter")

        if not adapter_class.name:
            raise ValueError(f"{adapter_class} 必须定义 name 属性")

        cls._adapters[adapter_class.name] = adapter_class
        logger.info(
            f"✅ 注册LLM适配器: {adapter_class.name} ({adapter_class.provider})"
        )

    @classmethod
    def unregister(cls, name: str):
        """注销适配器

        Args:
            name: 适配器名称
        """
        if name in cls._adapters:
            del cls._adapters[name]
            logger.info(f"❌ 注销LLM适配器: {name}")

    @classmethod
    def get_adapter(cls, name: str) -> type[BaseLLMAdapter] | None:
        """获取适配器类

        Args:
            name: 适配器名称

        Returns:
            适配器类，如果不存在返回None
        """
        # 确保已初始化
        cls.ensure_initialized()

        return cls._adapters.get(name)

    @classmethod
    def create_adapter(cls, name: str, **kwargs) -> BaseLLMAdapter:
        """创建适配器实例

        Args:
            name: 适配器名称
            **kwargs: 初始化参数

        Returns:
            适配器实例
        """
        adapter_class = cls.get_adapter(name)
        if not adapter_class:
            raise ValueError(f"未找到适配器: {name}")

        return adapter_class(**kwargs)

    @classmethod
    def list_adapters(cls) -> list[dict]:
        """列出所有已注册的适配器

        Returns:
            适配器信息列表
        """
        cls.ensure_initialized()

        adapters = []
        for name, adapter_class in cls._adapters.items():
            adapters.append(
                {
                    "name": name,
                    "provider": adapter_class.provider,
                    "supported_models": adapter_class.supported_models,
                    "required_env_vars": adapter_class.get_required_env_vars(),
                }
            )
        return adapters

    @classmethod
    def auto_discover(cls):
        """自动发现并注册适配器

        扫描llm_adapters目录和custom子目录，自动加载所有适配器
        """
        if cls._initialized:
            return

        logger.info("🔍 开始自动发现LLM适配器...")

        # 获取llm_adapters目录路径
        adapters_dir = Path(__file__).parent

        # 扫描主目录
        cls._scan_directory(adapters_dir)

        # 扫描custom子目录
        custom_dir = adapters_dir / "custom"
        if custom_dir.exists():
            cls._scan_directory(custom_dir, prefix="custom.")

        cls._initialized = True
        logger.info(f"✅ 发现并注册了 {len(cls._adapters)} 个LLM适配器")

    @classmethod
    def _scan_directory(cls, directory: Path, prefix: str = ""):
        """扫描目录查找适配器

        Args:
            directory: 要扫描的目录
            prefix: 模块名前缀
        """
        for finder, name, ispkg in pkgutil.iter_modules([str(directory)]):
            # 跳过特殊文件和本模块
            if name.startswith("_") or name == "plugin_loader":
                continue

            try:
                # 构建完整模块名
                if prefix:
                    module_name = f"tradingagents.llm_adapters.{prefix}{name}"
                else:
                    module_name = f"tradingagents.llm_adapters.{name}"

                # 导入模块
                module = importlib.import_module(module_name)

                # 查找适配器类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # 检查是否是适配器类
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseLLMAdapter)
                        and attr != BaseLLMAdapter
                        and hasattr(attr, "name")
                        and attr.name
                    ):

                        cls.register(attr)

            except Exception as e:
                logger.warning(f"加载适配器模块 {name} 失败: {e}")

    @classmethod
    def ensure_initialized(cls):
        """确保注册表已初始化"""
        if not cls._initialized:
            cls.auto_discover()

    @classmethod
    def reload(cls):
        """重新加载所有适配器"""
        cls._adapters.clear()
        cls._initialized = False
        cls.auto_discover()


# 便捷函数
def get_llm_adapter(name: str, **kwargs) -> BaseLLMAdapter:
    """获取LLM适配器实例

    Args:
        name: 适配器名称
        **kwargs: 初始化参数

    Returns:
        适配器实例
    """
    return LLMAdapterRegistry.create_adapter(name, **kwargs)


def list_available_adapters() -> list[dict]:
    """列出所有可用的适配器

    Returns:
        适配器信息列表
    """
    return LLMAdapterRegistry.list_adapters()


# 模块初始化时自动发现适配器
LLMAdapterRegistry.auto_discover()
