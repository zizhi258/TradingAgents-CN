"""Performance Optimization Module

Comprehensive performance optimization suite for TradingAgents-CN system.
Provides database optimization, caching strategies, model serving optimization,
API performance improvements, and real-time monitoring.
"""

from .database_optimizer import DatabaseOptimizer, ConnectionPoolManager
from .cache_optimizer import MultiLevelCacheOptimizer, PredictiveCacheWarmer
from .model_optimizer import ModelServingOptimizer, BatchInferenceEngine
from .api_optimizer import AsyncAPIOptimizer, RequestBatcher
from .pipeline_optimizer import DataPipelineOptimizer, StreamProcessor
from .resource_optimizer import ResourceManager, MemoryPoolManager
from .monitoring import PerformanceMonitor, MetricsCollector, AlertManager

__all__ = [
    'DatabaseOptimizer',
    'ConnectionPoolManager', 
    'MultiLevelCacheOptimizer',
    'PredictiveCacheWarmer',
    'ModelServingOptimizer',
    'BatchInferenceEngine',
    'AsyncAPIOptimizer',
    'RequestBatcher',
    'DataPipelineOptimizer',
    'StreamProcessor',
    'ResourceManager',
    'MemoryPoolManager',
    'PerformanceMonitor',
    'MetricsCollector',
    'AlertManager'
]

__version__ = "1.0.0"