"""Performance Optimization Module

Comprehensive performance optimization suite for TradingAgents-CN system.
Provides database optimization, caching strategies, model serving optimization,
API performance improvements, and real-time monitoring.
"""

from .api_optimizer import AsyncAPIOptimizer, RequestBatcher
from .cache_optimizer import MultiLevelCacheOptimizer, PredictiveCacheWarmer
from .database_optimizer import ConnectionPoolManager, DatabaseOptimizer
from .model_optimizer import BatchInferenceEngine, ModelServingOptimizer
from .monitoring import AlertManager, MetricsCollector, PerformanceMonitor
from .pipeline_optimizer import DataPipelineOptimizer, StreamProcessor
from .resource_optimizer import MemoryPoolManager, ResourceManager

__all__ = [
    "DatabaseOptimizer",
    "ConnectionPoolManager",
    "MultiLevelCacheOptimizer",
    "PredictiveCacheWarmer",
    "ModelServingOptimizer",
    "BatchInferenceEngine",
    "AsyncAPIOptimizer",
    "RequestBatcher",
    "DataPipelineOptimizer",
    "StreamProcessor",
    "ResourceManager",
    "MemoryPoolManager",
    "PerformanceMonitor",
    "MetricsCollector",
    "AlertManager",
]

__version__ = "1.0.0"
