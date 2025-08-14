"""Resource Management and Optimization Module

Advanced resource management for memory, CPU, and I/O optimization
in high-throughput trading scenarios.
"""

import asyncio
import gc
import os
import psutil
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import queue
import weakref

from .database_optimizer import get_pool_manager
from .cache_optimizer import get_cache_optimizer
from ..utils.logging_init import get_logger

logger = get_logger("resource_optimizer")


@dataclass
class ResourceMetrics:
    """System resource metrics"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: float = 0.0
    memory_used_mb: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    network_io_sent_mb: float = 0.0
    network_io_recv_mb: float = 0.0
    open_file_descriptors: int = 0
    thread_count: int = 0
    process_count: int = 0
    swap_percent: float = 0.0
    load_average: List[float] = field(default_factory=list)


class MemoryPoolManager:
    """Advanced memory pool management for object reuse"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.pools = {}
        self.pool_stats = {}
        self._locks = {}
        self.max_pool_size = self.config.get('max_pool_size', 1000)
        self.gc_threshold = self.config.get('gc_threshold', 0.8)
        
        # Monitoring
        self.allocation_count = 0
        self.reuse_count = 0
        self.eviction_count = 0
        
        logger.info("Memory pool manager initialized")
    
    def get_pool(self, pool_name: str, factory_func: Callable = None):
        """Get or create memory pool"""
        if pool_name not in self.pools:
            self.pools[pool_name] = queue.Queue(maxsize=self.max_pool_size)
            self.pool_stats[pool_name] = {
                'size': 0,
                'max_size': self.max_pool_size,
                'allocations': 0,
                'reuses': 0,
                'factory_func': factory_func
            }
            self._locks[pool_name] = threading.Lock()
            
            logger.info(f"Created memory pool: {pool_name}")
        
        return self.pools[pool_name]
    
    def acquire(self, pool_name: str, factory_func: Callable = None):
        """Acquire object from pool or create new one"""
        pool = self.get_pool(pool_name, factory_func)
        
        try:
            # Try to get existing object from pool
            obj = pool.get_nowait()
            self.pool_stats[pool_name]['reuses'] += 1
            self.reuse_count += 1
            return obj
            
        except queue.Empty:
            # Create new object
            if factory_func:
                obj = factory_func()
            elif self.pool_stats[pool_name]['factory_func']:
                obj = self.pool_stats[pool_name]['factory_func']()
            else:
                raise ValueError(f"No factory function for pool {pool_name}")
            
            self.pool_stats[pool_name]['allocations'] += 1
            self.allocation_count += 1
            return obj
    
    def release(self, pool_name: str, obj: Any):
        """Return object to pool"""
        if pool_name not in self.pools:
            return False
        
        pool = self.pools[pool_name]
        
        try:
            # Clean/reset object if it has reset method
            if hasattr(obj, 'reset'):
                obj.reset()
            
            pool.put_nowait(obj)
            return True
            
        except queue.Full:
            # Pool is full, object will be garbage collected
            self.eviction_count += 1
            return False
    
    def get_pool_statistics(self) -> Dict[str, Any]:
        """Get memory pool statistics"""
        pool_info = {}
        
        for pool_name, stats in self.pool_stats.items():
            pool = self.pools[pool_name]
            pool_info[pool_name] = {
                'current_size': pool.qsize(),
                'max_size': stats['max_size'],
                'allocations': stats['allocations'],
                'reuses': stats['reuses'],
                'reuse_ratio': stats['reuses'] / max(stats['allocations'] + stats['reuses'], 1)
            }
        
        return {
            'pools': pool_info,
            'total_allocations': self.allocation_count,
            'total_reuses': self.reuse_count,
            'total_evictions': self.eviction_count,
            'overall_reuse_ratio': self.reuse_count / max(self.allocation_count + self.reuse_count, 1)
        }
    
    def cleanup_pools(self, max_idle_time: int = 3600):
        """Clean up idle objects from pools"""
        cleaned_objects = 0
        
        for pool_name, pool in self.pools.items():
            while not pool.empty():
                try:
                    obj = pool.get_nowait()
                    # Could check object idle time here if tracked
                    pool.put_nowait(obj)  # Put back for now
                    break  # Exit to avoid infinite loop
                except:
                    cleaned_objects += 1
        
        logger.info(f"Cleaned {cleaned_objects} idle objects from memory pools")
        return cleaned_objects


class ResourceMonitor:
    """System resource monitoring and alerting"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.is_monitoring = False
        self.monitor_thread = None
        self.metrics_history = []
        self.max_history = self.config.get('max_history', 1000)
        self.monitor_interval = self.config.get('monitor_interval', 30)  # seconds
        
        # Thresholds for alerts
        self.thresholds = {
            'cpu_critical': self.config.get('cpu_critical', 90),
            'memory_critical': self.config.get('memory_critical', 85),
            'disk_io_critical': self.config.get('disk_io_critical', 100),  # MB/s
            'swap_critical': self.config.get('swap_critical', 50)
        }
        
        # Alert callbacks
        self.alert_callbacks = []
        
        logger.info("Resource monitor initialized")
    
    def start_monitoring(self):
        """Start resource monitoring"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        logger.info("Resource monitoring stopped")
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for resource alerts"""
        self.alert_callbacks.append(callback)
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        last_disk_io = None
        last_network_io = None
        last_time = time.time()
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                metrics = self._collect_metrics(last_disk_io, last_network_io, current_time - last_time)
                
                # Store metrics
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history.pop(0)
                
                # Check thresholds and trigger alerts
                self._check_thresholds(metrics)
                
                # Update for next iteration
                last_disk_io = psutil.disk_io_counters()
                last_network_io = psutil.net_io_counters()
                last_time = current_time
                
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                time.sleep(5)
    
    def _collect_metrics(self, last_disk_io, last_network_io, time_delta) -> ResourceMetrics:
        """Collect system resource metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk I/O rates
            disk_io = psutil.disk_io_counters()
            disk_read_mb = 0
            disk_write_mb = 0
            
            if last_disk_io and time_delta > 0:
                disk_read_mb = (disk_io.read_bytes - last_disk_io.read_bytes) / (1024 * 1024 * time_delta)
                disk_write_mb = (disk_io.write_bytes - last_disk_io.write_bytes) / (1024 * 1024 * time_delta)
            
            # Network I/O rates
            network_io = psutil.net_io_counters()
            network_sent_mb = 0
            network_recv_mb = 0
            
            if last_network_io and time_delta > 0:
                network_sent_mb = (network_io.bytes_sent - last_network_io.bytes_sent) / (1024 * 1024 * time_delta)
                network_recv_mb = (network_io.bytes_recv - last_network_io.bytes_recv) / (1024 * 1024 * time_delta)
            
            # Process information
            process = psutil.Process()
            
            # Load average (Linux/Mac only)
            try:
                load_avg = list(os.getloadavg())
            except (OSError, AttributeError):
                load_avg = []
            
            return ResourceMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available_mb=memory.available / (1024 * 1024),
                memory_used_mb=memory.used / (1024 * 1024),
                disk_io_read_mb=disk_read_mb,
                disk_io_write_mb=disk_write_mb,
                network_io_sent_mb=network_sent_mb,
                network_io_recv_mb=network_recv_mb,
                open_file_descriptors=process.num_fds() if hasattr(process, 'num_fds') else 0,
                thread_count=process.num_threads(),
                process_count=len(psutil.pids()),
                swap_percent=swap.percent,
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error(f"Metrics collection error: {e}")
            return ResourceMetrics()
    
    def _check_thresholds(self, metrics: ResourceMetrics):
        """Check resource thresholds and trigger alerts"""
        alerts = []
        
        if metrics.cpu_percent > self.thresholds['cpu_critical']:
            alerts.append(f"Critical CPU usage: {metrics.cpu_percent:.1f}%")
        
        if metrics.memory_percent > self.thresholds['memory_critical']:
            alerts.append(f"Critical memory usage: {metrics.memory_percent:.1f}%")
        
        if metrics.swap_percent > self.thresholds['swap_critical']:
            alerts.append(f"Critical swap usage: {metrics.swap_percent:.1f}%")
        
        if (metrics.disk_io_read_mb + metrics.disk_io_write_mb) > self.thresholds['disk_io_critical']:
            alerts.append(f"High disk I/O: {metrics.disk_io_read_mb + metrics.disk_io_write_mb:.1f} MB/s")
        
        # Trigger alert callbacks
        for alert in alerts:
            logger.warning(f"Resource alert: {alert}")
            for callback in self.alert_callbacks:
                try:
                    callback(alert, metrics)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")
    
    def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        """Get metrics summary for last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        # Filter recent metrics (would need timestamp in metrics)
        recent_metrics = self.metrics_history[-min(len(self.metrics_history), minutes * 2):]
        
        if not recent_metrics:
            return {'message': 'No metrics available'}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        max_cpu = max(m.cpu_percent for m in recent_metrics)
        max_memory = max(m.memory_percent for m in recent_metrics)
        
        return {
            'time_window_minutes': minutes,
            'sample_count': len(recent_metrics),
            'average_cpu_percent': avg_cpu,
            'average_memory_percent': avg_memory,
            'peak_cpu_percent': max_cpu,
            'peak_memory_percent': max_memory,
            'current_metrics': recent_metrics[-1] if recent_metrics else None
        }


class ResourceOptimizer:
    """Main resource optimization coordinator"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize components
        self.memory_pool_manager = MemoryPoolManager(
            self.config.get('memory_pool', {})
        )
        self.resource_monitor = ResourceMonitor(
            self.config.get('resource_monitor', {})
        )
        
        # Get other optimizers
        self.cache_optimizer = get_cache_optimizer()
        self.pool_manager = get_pool_manager()
        
        # Optimization settings
        self.auto_optimize = self.config.get('auto_optimize', True)
        self.optimization_interval = self.config.get('optimization_interval', 300)  # 5 minutes
        
        # Background optimization
        self.optimization_executor = ThreadPoolExecutor(max_workers=2)
        self._optimization_tasks = []
        
        # Performance tracking
        self.optimization_history = []
        
        logger.info("Resource optimizer initialized")
    
    def start(self):
        """Start resource optimization"""
        # Start monitoring
        self.resource_monitor.start_monitoring()
        
        # Add alert callback for automatic optimization
        if self.auto_optimize:
            self.resource_monitor.add_alert_callback(self._handle_resource_alert)
        
        # Schedule periodic optimization
        self._schedule_periodic_optimization()
        
        logger.info("Resource optimizer started")
    
    def stop(self):
        """Stop resource optimization"""
        self.resource_monitor.stop_monitoring()
        self.optimization_executor.shutdown(wait=True)
        
        logger.info("Resource optimizer stopped")
    
    def _handle_resource_alert(self, alert: str, metrics: ResourceMetrics):
        """Handle resource alerts with automatic optimization"""
        logger.info(f"Handling resource alert: {alert}")
        
        # Submit optimization task
        future = self.optimization_executor.submit(self._run_emergency_optimization, metrics)
        self._optimization_tasks.append(future)
    
    def _run_emergency_optimization(self, metrics: ResourceMetrics):
        """Run emergency optimization when resources are critical"""
        optimization_actions = []
        
        try:
            # Memory optimization
            if metrics.memory_percent > 85:
                # Force garbage collection
                collected = gc.collect()
                optimization_actions.append(f"Garbage collected {collected} objects")
                
                # Clean memory pools
                cleaned = self.memory_pool_manager.cleanup_pools()
                optimization_actions.append(f"Cleaned {cleaned} pooled objects")
                
                # Evict cache entries
                evicted = self.cache_optimizer.evict_cache_entries('l1', 'lru')
                optimization_actions.append(f"Evicted {evicted} cache entries")
            
            # CPU optimization
            if metrics.cpu_percent > 90:
                # Could implement CPU throttling or task deferral here
                optimization_actions.append("CPU optimization triggered")
            
            # Disk I/O optimization
            if (metrics.disk_io_read_mb + metrics.disk_io_write_mb) > 100:
                # Could implement I/O throttling or batching
                optimization_actions.append("I/O optimization triggered")
            
            # Log optimization results
            optimization_result = {
                'timestamp': datetime.now(),
                'trigger': 'emergency',
                'actions': optimization_actions,
                'metrics_before': metrics
            }
            
            self.optimization_history.append(optimization_result)
            logger.info(f"Emergency optimization completed: {optimization_actions}")
            
        except Exception as e:
            logger.error(f"Emergency optimization error: {e}")
    
    def _schedule_periodic_optimization(self):
        """Schedule periodic optimization tasks"""
        def periodic_optimization():
            while True:
                try:
                    time.sleep(self.optimization_interval)
                    
                    # Run regular optimization
                    future = self.optimization_executor.submit(self._run_periodic_optimization)
                    self._optimization_tasks.append(future)
                    
                except Exception as e:
                    logger.error(f"Periodic optimization scheduling error: {e}")
        
        optimization_thread = threading.Thread(target=periodic_optimization)
        optimization_thread.daemon = True
        optimization_thread.start()
    
    def _run_periodic_optimization(self):
        """Run periodic optimization tasks"""
        optimization_actions = []
        
        try:
            current_metrics = self.resource_monitor.get_current_metrics()
            
            # Memory pool maintenance
            pool_stats = self.memory_pool_manager.get_pool_statistics()
            cleaned = self.memory_pool_manager.cleanup_pools()
            if cleaned > 0:
                optimization_actions.append(f"Cleaned {cleaned} pooled objects")
            
            # Cache maintenance
            if current_metrics and current_metrics.memory_percent > 70:
                evicted = self.cache_optimizer.evict_cache_entries('l3', 'size')  # File cache
                if evicted > 0:
                    optimization_actions.append(f"Evicted {evicted} file cache entries")
            
            # Database connection pool optimization
            health = self.pool_manager.health_check()
            if not all(h['healthy'] for h in health.values()):
                optimization_actions.append("Database connection pool health check failed")
            
            # Garbage collection if memory usage is moderate
            if current_metrics and current_metrics.memory_percent > 60:
                collected = gc.collect()
                if collected > 0:
                    optimization_actions.append(f"Garbage collected {collected} objects")
            
            # Log optimization results
            if optimization_actions:
                optimization_result = {
                    'timestamp': datetime.now(),
                    'trigger': 'periodic',
                    'actions': optimization_actions,
                    'metrics': current_metrics
                }
                
                self.optimization_history.append(optimization_result)
                logger.info(f"Periodic optimization completed: {optimization_actions}")
            
        except Exception as e:
            logger.error(f"Periodic optimization error: {e}")
    
    def force_optimization(self) -> Dict[str, Any]:
        """Force immediate optimization"""
        logger.info("Force optimization requested")
        
        current_metrics = self.resource_monitor.get_current_metrics()
        
        # Submit optimization task
        future = self.optimization_executor.submit(self._run_emergency_optimization, current_metrics)
        
        # Wait for completion
        try:
            future.result(timeout=30)
            return {'status': 'completed', 'message': 'Optimization completed successfully'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        return {
            'resource_metrics': self.resource_monitor.get_metrics_summary(),
            'memory_pool_stats': self.memory_pool_manager.get_pool_statistics(),
            'cache_metrics': self.cache_optimizer.get_cache_metrics(),
            'database_pool_stats': self.pool_manager.get_pool_stats(),
            'optimization_history': self.optimization_history[-10:],  # Last 10 optimizations
            'active_optimization_tasks': len([t for t in self._optimization_tasks if not t.done()]),
            'timestamp': datetime.now().isoformat()
        }


# Global resource optimizer instance
_resource_optimizer = None

def get_resource_optimizer() -> ResourceOptimizer:
    """Get global resource optimizer instance"""
    global _resource_optimizer
    
    if _resource_optimizer is None:
        _resource_optimizer = ResourceOptimizer()
    
    return _resource_optimizer