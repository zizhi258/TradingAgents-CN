"""
Performance Optimization Module for ChartingArtist
优化图表生成和存储管理的性能
"""

import asyncio
import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import lru_cache, wraps
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from datetime import datetime, timedelta
import psutil
import threading
import queue
from dataclasses import dataclass, field
import redis
import pickle

from tradingagents.utils.logging_init import get_logger

logger = get_logger("charting_performance")


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    generation_time: float = 0.0
    queue_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    concurrent_jobs: int = 0
    total_charts_generated: int = 0
    error_count: int = 0
    avg_file_size_mb: float = 0.0
    storage_usage_mb: float = 0.0


class PerformanceOptimizer:
    """ChartingArtist性能优化器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metrics = PerformanceMetrics()
        self.redis_client = self._init_redis()
        self.cache_enabled = self.config.get("cache_enabled", True)
        self.max_concurrent_jobs = self.config.get("max_concurrent_jobs", 3)
        self.memory_limit_mb = self.config.get("memory_limit_mb", 2048)
        self.storage_limit_mb = self.config.get("storage_limit_mb", 10240)  # 10GB
        
        # 线程池管理
        self.executor = ThreadPoolExecutor(max_workers=self.max_concurrent_jobs)
        self.process_executor = ProcessPoolExecutor(max_workers=2)
        
        # 队列管理
        self.job_queue = asyncio.Queue(maxsize=100)
        self.priority_queue = queue.PriorityQueue()
        
        # 内存缓存
        self.memory_cache = {}
        self.cache_lock = threading.RLock()
        
        # 性能监控
        self.performance_monitor = PerformanceMonitor()
        
        logger.info("Performance optimizer initialized")
    
    def _init_redis(self) -> Optional[redis.Redis]:
        """初始化Redis连接"""
        try:
            redis_url = os.getenv("TRADINGAGENTS_REDIS_URL")
            if redis_url:
                client = redis.from_url(redis_url, decode_responses=True)
                client.ping()
                logger.info("Redis cache connected for performance optimization")
                return client
        except Exception as e:
            logger.warning(f"Redis connection failed, using memory cache only: {e}")
        return None
    
    def performance_monitor_decorator(self, operation_name: str):
        """性能监控装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024
                
                try:
                    result = await func(*args, **kwargs)
                    self.metrics.total_charts_generated += 1
                    return result
                except Exception as e:
                    self.metrics.error_count += 1
                    logger.error(f"Performance monitored operation failed: {e}")
                    raise
                finally:
                    end_time = time.time()
                    memory_after = psutil.Process().memory_info().rss / 1024 / 1024
                    
                    generation_time = end_time - start_time
                    memory_used = memory_after - memory_before
                    
                    self.metrics.generation_time = generation_time
                    self.metrics.memory_usage_mb = memory_after
                    
                    logger.debug(
                        f"Operation '{operation_name}' completed in {generation_time:.2f}s, "
                        f"memory delta: {memory_used:.1f}MB"
                    )
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                memory_before = psutil.Process().memory_info().rss / 1024 / 1024
                
                try:
                    result = func(*args, **kwargs)
                    self.metrics.total_charts_generated += 1
                    return result
                except Exception as e:
                    self.metrics.error_count += 1
                    logger.error(f"Performance monitored operation failed: {e}")
                    raise
                finally:
                    end_time = time.time()
                    memory_after = psutil.Process().memory_info().rss / 1024 / 1024
                    
                    generation_time = end_time - start_time
                    memory_used = memory_after - memory_before
                    
                    self.metrics.generation_time = generation_time
                    self.metrics.memory_usage_mb = memory_after
                    
                    logger.debug(
                        f"Operation '{operation_name}' completed in {generation_time:.2f}s, "
                        f"memory delta: {memory_used:.1f}MB"
                    )
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def intelligent_cache_key(self, data: Dict[str, Any]) -> str:
        """生成智能缓存键"""
        # 提取关键数据用于生成缓存键
        cache_data = {
            "symbol": data.get("symbol"),
            "chart_type": data.get("chart_type"),
            "config": data.get("config", {}),
            "data_hash": self._hash_chart_data(data.get("data", {}))
        }
        
        # 生成稳定的hash
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()[:16]
    
    def _hash_chart_data(self, data: Dict[str, Any]) -> str:
        """为图表数据生成hash"""
        if not data:
            return "empty"
        
        # 只hash关键数据字段，忽略时间戳等变化频繁的字段
        key_fields = ["symbol", "analysis_results", "market_data"]
        filtered_data = {k: v for k, v in data.items() if k in key_fields}
        
        data_string = json.dumps(filtered_data, sort_keys=True, default=str)
        return hashlib.md5(data_string.encode()).hexdigest()[:8]
    
    async def get_cached_chart(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存的图表"""
        if not self.cache_enabled:
            return None
        
        try:
            # 首先检查内存缓存
            with self.cache_lock:
                if cache_key in self.memory_cache:
                    cached_data, expiry = self.memory_cache[cache_key]
                    if datetime.now() < expiry:
                        self.metrics.cache_hits += 1
                        logger.debug(f"Memory cache hit for key: {cache_key}")
                        return cached_data
                    else:
                        del self.memory_cache[cache_key]
            
            # 检查Redis缓存
            if self.redis_client:
                cached_data = self.redis_client.get(f"chart_cache:{cache_key}")
                if cached_data:
                    chart_data = json.loads(cached_data)
                    self.metrics.cache_hits += 1
                    logger.debug(f"Redis cache hit for key: {cache_key}")
                    
                    # 回写到内存缓存
                    self._cache_to_memory(cache_key, chart_data)
                    return chart_data
            
            self.metrics.cache_misses += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            self.metrics.cache_misses += 1
            return None
    
    async def cache_chart(self, cache_key: str, chart_data: Dict[str, Any], 
                         ttl_hours: int = 24) -> bool:
        """缓存图表数据"""
        if not self.cache_enabled:
            return False
        
        try:
            # 缓存到内存
            self._cache_to_memory(cache_key, chart_data, ttl_hours)
            
            # 缓存到Redis
            if self.redis_client:
                ttl_seconds = ttl_hours * 3600
                self.redis_client.setex(
                    f"chart_cache:{cache_key}",
                    ttl_seconds,
                    json.dumps(chart_data, default=str)
                )
            
            logger.debug(f"Chart cached with key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            return False
    
    def _cache_to_memory(self, cache_key: str, data: Dict[str, Any], ttl_hours: int = 1):
        """缓存到内存"""
        try:
            with self.cache_lock:
                # 检查内存缓存大小，清理过期项
                if len(self.memory_cache) > 100:  # 限制内存缓存大小
                    self._cleanup_memory_cache()
                
                expiry = datetime.now() + timedelta(hours=ttl_hours)
                self.memory_cache[cache_key] = (data, expiry)
                
        except Exception as e:
            logger.error(f"Memory cache error: {e}")
    
    def _cleanup_memory_cache(self):
        """清理过期的内存缓存"""
        with self.cache_lock:
            now = datetime.now()
            expired_keys = [
                key for key, (_, expiry) in self.memory_cache.items()
                if expiry < now
            ]
            for key in expired_keys:
                del self.memory_cache[key]
            
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def optimize_chart_generation(self, chart_func: Callable, 
                                      *args, **kwargs) -> Dict[str, Any]:
        """优化的图表生成方法"""
        
        # 生成缓存键
        cache_key = self.intelligent_cache_key(kwargs)
        
        # 检查缓存
        cached_result = await self.get_cached_chart(cache_key)
        if cached_result:
            logger.info(f"Using cached chart for key: {cache_key}")
            return cached_result
        
        # 检查系统资源
        if not self._check_system_resources():
            logger.warning("System resources low, queuing chart generation")
            return await self._queue_chart_generation(chart_func, *args, **kwargs)
        
        # 生成图表
        try:
            start_time = time.time()
            
            # 在线程池中执行图表生成
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor, 
                self._execute_chart_generation,
                chart_func, args, kwargs
            )
            
            generation_time = time.time() - start_time
            
            # 缓存结果
            await self.cache_chart(cache_key, result)
            
            logger.info(f"Chart generated in {generation_time:.2f}s, cached with key: {cache_key}")
            return result
            
        except Exception as e:
            logger.error(f"Optimized chart generation failed: {e}")
            raise
    
    def _execute_chart_generation(self, chart_func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
        """在线程中执行图表生成"""
        try:
            return chart_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Chart generation execution failed: {e}")
            raise
    
    def _check_system_resources(self) -> bool:
        """检查系统资源是否充足"""
        try:
            # 检查内存使用
            memory_info = psutil.virtual_memory()
            memory_usage_mb = (memory_info.total - memory_info.available) / 1024 / 1024
            
            if memory_usage_mb > self.memory_limit_mb:
                logger.warning(f"High memory usage: {memory_usage_mb:.1f}MB")
                return False
            
            # 检查CPU负载
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                logger.warning(f"High CPU usage: {cpu_percent}%")
                return False
            
            # 检查磁盘空间
            charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
            if charts_dir.exists():
                disk_usage = psutil.disk_usage(str(charts_dir))
                disk_usage_mb = (disk_usage.total - disk_usage.free) / 1024 / 1024
                
                if disk_usage_mb > self.storage_limit_mb:
                    logger.warning(f"High disk usage: {disk_usage_mb:.1f}MB")
                    return False
            
            # 检查并发任务数
            if self.metrics.concurrent_jobs >= self.max_concurrent_jobs:
                logger.warning(f"Max concurrent jobs reached: {self.metrics.concurrent_jobs}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Resource check failed: {e}")
            return True  # 在检查失败时默认允许执行
    
    async def _queue_chart_generation(self, chart_func: Callable, *args, **kwargs) -> Dict[str, Any]:
        """将图表生成任务加入队列"""
        try:
            # 创建任务
            task_id = f"chart_task_{int(time.time() * 1000)}"
            task = {
                "id": task_id,
                "func": chart_func,
                "args": args,
                "kwargs": kwargs,
                "created_at": datetime.now(),
                "priority": kwargs.get("priority", 5)  # 默认优先级
            }
            
            # 加入优先级队列
            self.priority_queue.put((task["priority"], task))
            
            logger.info(f"Chart generation task queued: {task_id}")
            
            # 等待任务完成（简化版本，实际应该有更复杂的任务状态管理）
            return await self._wait_for_queued_task(task_id)
            
        except Exception as e:
            logger.error(f"Task queuing failed: {e}")
            raise
    
    async def _wait_for_queued_task(self, task_id: str) -> Dict[str, Any]:
        """等待队列任务完成"""
        # 这里应该实现更完整的任务状态跟踪
        # 简化版本：直接执行任务
        max_wait = 300  # 5分钟超时
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if not self.priority_queue.empty():
                priority, task = self.priority_queue.get()
                if task["id"] == task_id:
                    # 执行任务
                    try:
                        result = self._execute_chart_generation(
                            task["func"], task["args"], task["kwargs"]
                        )
                        return result
                    except Exception as e:
                        logger.error(f"Queued task execution failed: {e}")
                        raise
                else:
                    # 放回队列
                    self.priority_queue.put((priority, task))
            
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Task {task_id} timed out in queue")
    
    async def batch_optimize_charts(self, chart_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量优化图表生成"""
        logger.info(f"Starting batch optimization for {len(chart_requests)} charts")
        
        # 对请求进行分析和优化
        optimized_requests = self._analyze_batch_requests(chart_requests)
        
        # 并发生成图表
        tasks = []
        semaphore = asyncio.Semaphore(self.max_concurrent_jobs)
        
        async def generate_with_semaphore(request):
            async with semaphore:
                return await self.optimize_chart_generation(
                    request["chart_func"],
                    **request["kwargs"]
                )
        
        for request in optimized_requests:
            task = asyncio.create_task(generate_with_semaphore(request))
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        successful_results = []
        failed_count = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch chart generation failed for request {i}: {result}")
                failed_count += 1
            else:
                successful_results.append(result)
        
        logger.info(f"Batch optimization completed: {len(successful_results)} success, {failed_count} failed")
        return successful_results
    
    def _analyze_batch_requests(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析和优化批量请求"""
        # 检查重复请求
        seen_keys = set()
        optimized_requests = []
        
        for request in requests:
            cache_key = self.intelligent_cache_key(request.get("kwargs", {}))
            
            if cache_key not in seen_keys:
                seen_keys.add(cache_key)
                optimized_requests.append(request)
            else:
                logger.debug(f"Skipping duplicate request with cache key: {cache_key}")
        
        # 按优先级排序
        optimized_requests.sort(key=lambda x: x.get("kwargs", {}).get("priority", 5))
        
        logger.info(f"Batch analysis: {len(requests)} -> {len(optimized_requests)} requests (removed {len(requests) - len(optimized_requests)} duplicates)")
        
        return optimized_requests
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            # 更新当前系统指标
            memory_info = psutil.virtual_memory()
            self.metrics.memory_usage_mb = (memory_info.total - memory_info.available) / 1024 / 1024
            self.metrics.cpu_usage_percent = psutil.cpu_percent()
            
            # 计算缓存命中率
            total_cache_requests = self.metrics.cache_hits + self.metrics.cache_misses
            cache_hit_rate = (self.metrics.cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0
            
            # 计算错误率
            total_operations = self.metrics.total_charts_generated + self.metrics.error_count
            error_rate = (self.metrics.error_count / total_operations * 100) if total_operations > 0 else 0
            
            return {
                "generation_time_avg": self.metrics.generation_time,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "cache_hits": self.metrics.cache_hits,
                "cache_misses": self.metrics.cache_misses,
                "memory_usage_mb": round(self.metrics.memory_usage_mb, 1),
                "cpu_usage_percent": round(self.metrics.cpu_usage_percent, 1),
                "concurrent_jobs": self.metrics.concurrent_jobs,
                "total_charts_generated": self.metrics.total_charts_generated,
                "error_count": self.metrics.error_count,
                "error_rate": round(error_rate, 2),
                "storage_usage_mb": round(self.metrics.storage_usage_mb, 1),
                "queue_depth": self.priority_queue.qsize(),
                "memory_cache_size": len(self.memory_cache)
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}
    
    def cleanup_resources(self):
        """清理资源"""
        try:
            # 关闭线程池
            self.executor.shutdown(wait=True)
            self.process_executor.shutdown(wait=True)
            
            # 清理内存缓存
            with self.cache_lock:
                self.memory_cache.clear()
            
            # 关闭Redis连接
            if self.redis_client:
                self.redis_client.close()
            
            logger.info("Performance optimizer resources cleaned up")
            
        except Exception as e:
            logger.error(f"Resource cleanup failed: {e}")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, monitoring_interval: int = 60):
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_thread = None
        self.metrics_history = []
        self.max_history_size = 1440  # 24小时，每分钟一个数据点
    
    def start_monitoring(self):
        """开始性能监控"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """停止性能监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                metrics = self._collect_metrics()
                self._store_metrics(metrics)
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"Performance monitoring error: {e}")
                time.sleep(self.monitoring_interval)
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """收集系统指标"""
        try:
            # 系统资源指标
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # ChartingArtist特定目录的磁盘使用
            charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
            disk_usage = 0
            file_count = 0
            
            if charts_dir.exists():
                for file_path in charts_dir.rglob("*"):
                    if file_path.is_file():
                        disk_usage += file_path.stat().st_size
                        file_count += 1
            
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_used_mb": (memory.total - memory.available) / 1024 / 1024,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_usage_mb": disk_usage / 1024 / 1024,
                "chart_file_count": file_count,
                "load_average": os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
            }
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return {"timestamp": datetime.now().isoformat(), "error": str(e)}
    
    def _store_metrics(self, metrics: Dict[str, Any]):
        """存储指标数据"""
        self.metrics_history.append(metrics)
        
        # 限制历史数据大小
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """获取指标摘要"""
        if not self.metrics_history:
            return {}
        
        # 过滤指定时间范围的数据
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history 
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        # 计算统计值
        cpu_values = [m.get("cpu_percent", 0) for m in recent_metrics]
        memory_values = [m.get("memory_used_mb", 0) for m in recent_metrics]
        
        return {
            "timespan_hours": hours,
            "data_points": len(recent_metrics),
            "cpu_avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "cpu_max": max(cpu_values) if cpu_values else 0,
            "memory_avg_mb": sum(memory_values) / len(memory_values) if memory_values else 0,
            "memory_max_mb": max(memory_values) if memory_values else 0,
            "latest_chart_count": recent_metrics[-1].get("chart_file_count", 0) if recent_metrics else 0,
            "latest_disk_usage_mb": recent_metrics[-1].get("disk_usage_mb", 0) if recent_metrics else 0
        }


# 全局性能优化器实例
_performance_optimizer = None

def get_performance_optimizer(config: Dict[str, Any] = None) -> PerformanceOptimizer:
    """获取性能优化器单例"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer(config)
    return _performance_optimizer


# 装饰器函数
def optimized_chart_generation(operation_name: str = "chart_generation"):
    """图表生成性能优化装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            optimizer = get_performance_optimizer()
            return await optimizer.optimize_chart_generation(func, *args, **kwargs)
        return wrapper
    return decorator


# 导出主要类和函数
__all__ = [
    'PerformanceOptimizer',
    'PerformanceMonitor', 
    'PerformanceMetrics',
    'get_performance_optimizer',
    'optimized_chart_generation'
]