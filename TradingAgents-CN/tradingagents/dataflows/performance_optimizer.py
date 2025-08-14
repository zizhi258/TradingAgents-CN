"""
Performance Optimization and Resource Management for TradingAgents-CN Data Pipeline

This module implements comprehensive performance optimization including:
- Automatic resource scaling based on demand
- Cost optimization strategies
- Performance monitoring and alerting  
- Resource allocation and tuning
- Load balancing and throughput optimization
"""

import asyncio
import logging
import json
import time
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import psutil
import docker
import threading
from collections import deque, defaultdict
import numpy as np
from concurrent.futures import ThreadPoolExecutor


class ResourceType(Enum):
    """Types of resources to monitor and optimize"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    DATABASE_CONNECTIONS = "db_connections"
    QUEUE_SIZE = "queue_size"
    CACHE_HIT_RATE = "cache_hit_rate"


class OptimizationStrategy(Enum):
    """Performance optimization strategies"""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    LOAD_BALANCE = "load_balance"
    CACHE_OPTIMIZE = "cache_optimize"
    INDEX_OPTIMIZE = "index_optimize"
    QUERY_OPTIMIZE = "query_optimize"


@dataclass
class ResourceMetrics:
    """Resource usage metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_io_mbps: float
    db_connections: int
    queue_size: int
    cache_hit_rate: float
    response_time_ms: float
    throughput_rps: float
    error_rate: float
    timestamp: datetime


@dataclass
class OptimizationRecommendation:
    """Performance optimization recommendation"""
    strategy: OptimizationStrategy
    resource_type: ResourceType
    current_value: float
    recommended_value: float
    expected_improvement: float
    cost_impact: float
    implementation_complexity: str
    priority: str
    description: str


class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("performance_monitor")
        
        # Metrics storage
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.current_metrics = {}
        
        # Thresholds for alerting
        self.thresholds = {
            ResourceType.CPU: {"warning": 70.0, "critical": 85.0},
            ResourceType.MEMORY: {"warning": 75.0, "critical": 90.0},
            ResourceType.DISK: {"warning": 80.0, "critical": 95.0},
            ResourceType.NETWORK: {"warning": 100.0, "critical": 200.0},
            ResourceType.DATABASE_CONNECTIONS: {"warning": 80, "critical": 95},
            ResourceType.QUEUE_SIZE: {"warning": 1000, "critical": 5000},
            ResourceType.CACHE_HIT_RATE: {"warning": 0.85, "critical": 0.70}
        }
        
        # Docker client for container management
        self.docker_client = docker.from_env()
        
        # Performance tracking
        self.performance_stats = {
            'alerts_sent': 0,
            'optimizations_applied': 0,
            'cost_savings': 0.0,
            'last_optimization_time': None
        }
        
        # Monitoring thread
        self.monitoring_thread = None
        self.monitoring_active = False
        
    def start_monitoring(self):
        """Start continuous performance monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        self.logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
        
        self.logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                # Collect system metrics
                metrics = self._collect_system_metrics()
                
                # Collect application metrics
                app_metrics = self._collect_application_metrics()
                metrics.update(app_metrics)
                
                # Store metrics
                self.current_metrics = metrics
                for metric_name, value in metrics.items():
                    self.metrics_history[metric_name].append({
                        'value': value,
                        'timestamp': datetime.now()
                    })
                
                # Check thresholds and send alerts
                self._check_thresholds(metrics)
                
                # Sleep until next collection
                time.sleep(self.config.get('monitoring_interval', 30))
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(5)
    
    def _collect_system_metrics(self) -> Dict[str, float]:
        """Collect system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network I/O
            network = psutil.net_io_counters()
            network_mbps = (network.bytes_sent + network.bytes_recv) / (1024 * 1024)
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'network_mbps': network_mbps
            }
            
        except Exception as e:
            self.logger.error(f"System metrics collection failed: {e}")
            return {}
    
    def _collect_application_metrics(self) -> Dict[str, float]:
        """Collect application-specific metrics"""
        metrics = {}
        
        try:
            # Docker container metrics
            container_metrics = self._collect_container_metrics()
            metrics.update(container_metrics)
            
            # Database connection metrics
            db_metrics = self._collect_database_metrics()
            metrics.update(db_metrics)
            
            # Cache metrics
            cache_metrics = self._collect_cache_metrics()
            metrics.update(cache_metrics)
            
            # Queue metrics
            queue_metrics = self._collect_queue_metrics()
            metrics.update(queue_metrics)
            
        except Exception as e:
            self.logger.error(f"Application metrics collection failed: {e}")
        
        return metrics
    
    def _collect_container_metrics(self) -> Dict[str, float]:
        """Collect Docker container metrics"""
        metrics = {}
        
        try:
            containers = self.docker_client.containers.list()
            
            for container in containers:
                if 'tradingagents' in container.name:
                    try:
                        stats = container.stats(stream=False)
                        
                        # CPU usage
                        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                  stats['precpu_stats']['cpu_usage']['total_usage']
                        system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                     stats['precpu_stats']['system_cpu_usage']
                        
                        if system_delta > 0:
                            cpu_percent = (cpu_delta / system_delta) * 100.0
                            metrics[f'{container.name}_cpu_percent'] = cpu_percent
                        
                        # Memory usage
                        memory_usage = stats['memory_stats']['usage']
                        memory_limit = stats['memory_stats']['limit']
                        memory_percent = (memory_usage / memory_limit) * 100
                        metrics[f'{container.name}_memory_percent'] = memory_percent
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to collect stats for {container.name}: {e}")
            
        except Exception as e:
            self.logger.error(f"Container metrics collection failed: {e}")
        
        return metrics
    
    def _collect_database_metrics(self) -> Dict[str, float]:
        """Collect database performance metrics"""
        metrics = {}
        
        try:
            # MongoDB metrics
            mongodb_metrics = self._get_mongodb_metrics()
            metrics.update(mongodb_metrics)
            
            # Redis metrics
            redis_metrics = self._get_redis_metrics()
            metrics.update(redis_metrics)
            
            # TimescaleDB metrics
            timescale_metrics = self._get_timescale_metrics()
            metrics.update(timescale_metrics)
            
        except Exception as e:
            self.logger.error(f"Database metrics collection failed: {e}")
        
        return metrics
    
    def _get_mongodb_metrics(self) -> Dict[str, float]:
        """Get MongoDB performance metrics"""
        try:
            # This would connect to MongoDB and get stats
            # Implementation depends on MongoDB client setup
            return {
                'mongodb_connections': 0,
                'mongodb_operations_per_sec': 0,
                'mongodb_memory_usage_mb': 0
            }
        except:
            return {}
    
    def _get_redis_metrics(self) -> Dict[str, float]:
        """Get Redis performance metrics"""
        try:
            # This would connect to Redis and get INFO stats
            return {
                'redis_connected_clients': 0,
                'redis_memory_usage_mb': 0,
                'redis_hit_rate': 0.0,
                'redis_ops_per_sec': 0
            }
        except:
            return {}
    
    def _get_timescale_metrics(self) -> Dict[str, float]:
        """Get TimescaleDB performance metrics"""
        try:
            # This would connect to TimescaleDB and get pg_stat stats
            return {
                'timescale_connections': 0,
                'timescale_transactions_per_sec': 0,
                'timescale_cache_hit_ratio': 0.0
            }
        except:
            return {}
    
    def _collect_cache_metrics(self) -> Dict[str, float]:
        """Collect cache performance metrics"""
        # Implementation would depend on cache implementation
        return {
            'cache_hit_rate': 0.85,
            'cache_memory_usage_mb': 500,
            'cache_evictions_per_min': 10
        }
    
    def _collect_queue_metrics(self) -> Dict[str, float]:
        """Collect message queue metrics"""
        # Implementation would depend on queue system (Celery, Kafka, etc.)
        return {
            'queue_size': 100,
            'queue_processing_rate': 50,
            'queue_latency_ms': 100
        }
    
    def _check_thresholds(self, metrics: Dict[str, float]):
        """Check metrics against thresholds and send alerts"""
        try:
            for metric_name, value in metrics.items():
                # Map metric name to resource type
                resource_type = self._map_metric_to_resource_type(metric_name)
                
                if resource_type and resource_type in self.thresholds:
                    thresholds = self.thresholds[resource_type]
                    
                    if value >= thresholds['critical']:
                        self._send_alert('critical', resource_type, metric_name, value, thresholds['critical'])
                    elif value >= thresholds['warning']:
                        self._send_alert('warning', resource_type, metric_name, value, thresholds['warning'])
                        
        except Exception as e:
            self.logger.error(f"Threshold checking failed: {e}")
    
    def _map_metric_to_resource_type(self, metric_name: str) -> Optional[ResourceType]:
        """Map metric name to resource type"""
        if 'cpu' in metric_name.lower():
            return ResourceType.CPU
        elif 'memory' in metric_name.lower():
            return ResourceType.MEMORY
        elif 'disk' in metric_name.lower():
            return ResourceType.DISK
        elif 'network' in metric_name.lower():
            return ResourceType.NETWORK
        elif 'connection' in metric_name.lower():
            return ResourceType.DATABASE_CONNECTIONS
        elif 'queue' in metric_name.lower():
            return ResourceType.QUEUE_SIZE
        elif 'hit_rate' in metric_name.lower():
            return ResourceType.CACHE_HIT_RATE
        else:
            return None
    
    def _send_alert(self, severity: str, resource_type: ResourceType, metric_name: str, 
                   current_value: float, threshold: float):
        """Send performance alert"""
        try:
            alert = {
                'timestamp': datetime.now().isoformat(),
                'severity': severity,
                'resource_type': resource_type.value,
                'metric_name': metric_name,
                'current_value': current_value,
                'threshold': threshold,
                'message': f"{metric_name} is at {current_value:.2f}, exceeding {severity} threshold of {threshold}"
            }
            
            self.logger.warning(f"Performance Alert: {json.dumps(alert)}")
            self.performance_stats['alerts_sent'] += 1
            
            # Here you would integrate with your alerting system
            # (email, Slack, PagerDuty, etc.)
            
        except Exception as e:
            self.logger.error(f"Alert sending failed: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        try:
            summary = {
                'current_metrics': self.current_metrics,
                'performance_stats': self.performance_stats,
                'metric_trends': {},
                'recommendations': self.generate_optimization_recommendations()
            }
            
            # Calculate trends for key metrics
            for metric_name, history in self.metrics_history.items():
                if len(history) >= 10:
                    values = [entry['value'] for entry in list(history)[-10:]]
                    summary['metric_trends'][metric_name] = {
                        'current': values[-1] if values else 0,
                        'average': statistics.mean(values),
                        'trend': 'increasing' if values[-1] > values[0] else 'decreasing',
                        'volatility': statistics.stdev(values) if len(values) > 1 else 0
                    }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Performance summary generation failed: {e}")
            return {'error': str(e)}


class ResourceOptimizer:
    """Automatic resource optimization system"""
    
    def __init__(self, config: Dict[str, Any], monitor: PerformanceMonitor):
        self.config = config
        self.monitor = monitor
        self.logger = logging.getLogger("resource_optimizer")
        
        # Optimization history
        self.optimization_history = []
        
        # Cost tracking
        self.cost_calculator = CostCalculator(config.get('cost_config', {}))
        
    def generate_optimization_recommendations(self) -> List[OptimizationRecommendation]:
        """Generate optimization recommendations based on current metrics"""
        recommendations = []
        
        try:
            current_metrics = self.monitor.current_metrics
            
            # CPU optimization recommendations
            cpu_recommendations = self._analyze_cpu_usage(current_metrics)
            recommendations.extend(cpu_recommendations)
            
            # Memory optimization recommendations
            memory_recommendations = self._analyze_memory_usage(current_metrics)
            recommendations.extend(memory_recommendations)
            
            # Database optimization recommendations
            db_recommendations = self._analyze_database_performance(current_metrics)
            recommendations.extend(db_recommendations)
            
            # Cache optimization recommendations
            cache_recommendations = self._analyze_cache_performance(current_metrics)
            recommendations.extend(cache_recommendations)
            
            # Sort by priority and expected improvement
            recommendations.sort(key=lambda x: (
                {'high': 3, 'medium': 2, 'low': 1}.get(x.priority, 0),
                x.expected_improvement
            ), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Recommendation generation failed: {e}")
        
        return recommendations
    
    def _analyze_cpu_usage(self, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Analyze CPU usage and generate recommendations"""
        recommendations = []
        
        cpu_percent = metrics.get('cpu_percent', 0)
        
        if cpu_percent > 85:
            recommendations.append(OptimizationRecommendation(
                strategy=OptimizationStrategy.SCALE_UP,
                resource_type=ResourceType.CPU,
                current_value=cpu_percent,
                recommended_value=cpu_percent * 0.7,  # Target 70% usage
                expected_improvement=15.0,
                cost_impact=50.0,  # Estimated monthly cost increase
                implementation_complexity="medium",
                priority="high",
                description="Scale up CPU resources to handle high load"
            ))
        elif cpu_percent < 30:
            recommendations.append(OptimizationRecommendation(
                strategy=OptimizationStrategy.SCALE_DOWN,
                resource_type=ResourceType.CPU,
                current_value=cpu_percent,
                recommended_value=cpu_percent * 1.3,  # Target 40% usage
                expected_improvement=10.0,
                cost_impact=-25.0,  # Estimated monthly cost savings
                implementation_complexity="low",
                priority="medium",
                description="Scale down CPU resources to reduce costs"
            ))
        
        return recommendations
    
    def _analyze_memory_usage(self, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Analyze memory usage and generate recommendations"""
        recommendations = []
        
        memory_percent = metrics.get('memory_percent', 0)
        
        if memory_percent > 85:
            recommendations.append(OptimizationRecommendation(
                strategy=OptimizationStrategy.SCALE_UP,
                resource_type=ResourceType.MEMORY,
                current_value=memory_percent,
                recommended_value=memory_percent * 0.8,
                expected_improvement=20.0,
                cost_impact=30.0,
                implementation_complexity="low",
                priority="high",
                description="Increase memory allocation to prevent swapping"
            ))
        
        return recommendations
    
    def _analyze_database_performance(self, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Analyze database performance and generate recommendations"""
        recommendations = []
        
        # MongoDB recommendations
        mongodb_connections = metrics.get('mongodb_connections', 0)
        if mongodb_connections > 80:
            recommendations.append(OptimizationRecommendation(
                strategy=OptimizationStrategy.INDEX_OPTIMIZE,
                resource_type=ResourceType.DATABASE_CONNECTIONS,
                current_value=mongodb_connections,
                recommended_value=60,
                expected_improvement=25.0,
                cost_impact=0,
                implementation_complexity="medium",
                priority="high",
                description="Optimize MongoDB indexes to reduce connection usage"
            ))
        
        # Redis recommendations
        redis_hit_rate = metrics.get('redis_hit_rate', 1.0)
        if redis_hit_rate < 0.8:
            recommendations.append(OptimizationRecommendation(
                strategy=OptimizationStrategy.CACHE_OPTIMIZE,
                resource_type=ResourceType.CACHE_HIT_RATE,
                current_value=redis_hit_rate,
                recommended_value=0.9,
                expected_improvement=30.0,
                cost_impact=10.0,
                implementation_complexity="medium",
                priority="high",
                description="Optimize cache strategy to improve hit rate"
            ))
        
        return recommendations
    
    def _analyze_cache_performance(self, metrics: Dict[str, float]) -> List[OptimizationRecommendation]:
        """Analyze cache performance and generate recommendations"""
        recommendations = []
        
        cache_hit_rate = metrics.get('cache_hit_rate', 1.0)
        cache_evictions = metrics.get('cache_evictions_per_min', 0)
        
        if cache_hit_rate < 0.85 or cache_evictions > 50:
            recommendations.append(OptimizationRecommendation(
                strategy=OptimizationStrategy.CACHE_OPTIMIZE,
                resource_type=ResourceType.CACHE_HIT_RATE,
                current_value=cache_hit_rate,
                recommended_value=0.9,
                expected_improvement=20.0,
                cost_impact=15.0,
                implementation_complexity="medium",
                priority="medium",
                description="Increase cache size or optimize cache eviction policy"
            ))
        
        return recommendations
    
    async def apply_optimization(self, recommendation: OptimizationRecommendation) -> bool:
        """Apply an optimization recommendation"""
        try:
            self.logger.info(f"Applying optimization: {recommendation.description}")
            
            success = False
            
            if recommendation.strategy == OptimizationStrategy.SCALE_UP:
                success = await self._scale_up_resources(recommendation)
            elif recommendation.strategy == OptimizationStrategy.SCALE_DOWN:
                success = await self._scale_down_resources(recommendation)
            elif recommendation.strategy == OptimizationStrategy.CACHE_OPTIMIZE:
                success = await self._optimize_cache(recommendation)
            elif recommendation.strategy == OptimizationStrategy.INDEX_OPTIMIZE:
                success = await self._optimize_indexes(recommendation)
            elif recommendation.strategy == OptimizationStrategy.QUERY_OPTIMIZE:
                success = await self._optimize_queries(recommendation)
            
            if success:
                self.optimization_history.append({
                    'timestamp': datetime.now(),
                    'recommendation': asdict(recommendation),
                    'status': 'applied'
                })
                self.monitor.performance_stats['optimizations_applied'] += 1
                self.monitor.performance_stats['cost_savings'] += recommendation.cost_impact
                self.monitor.performance_stats['last_optimization_time'] = datetime.now()
            
            return success
            
        except Exception as e:
            self.logger.error(f"Optimization application failed: {e}")
            return False
    
    async def _scale_up_resources(self, recommendation: OptimizationRecommendation) -> bool:
        """Scale up resources (CPU/Memory)"""
        try:
            # Implementation would depend on orchestration system
            # (Kubernetes, Docker Swarm, etc.)
            self.logger.info(f"Scaling up {recommendation.resource_type.value}")
            return True
        except Exception as e:
            self.logger.error(f"Scale up failed: {e}")
            return False
    
    async def _scale_down_resources(self, recommendation: OptimizationRecommendation) -> bool:
        """Scale down resources to save costs"""
        try:
            self.logger.info(f"Scaling down {recommendation.resource_type.value}")
            return True
        except Exception as e:
            self.logger.error(f"Scale down failed: {e}")
            return False
    
    async def _optimize_cache(self, recommendation: OptimizationRecommendation) -> bool:
        """Optimize cache configuration"""
        try:
            self.logger.info("Optimizing cache configuration")
            # Implementation would adjust cache settings
            return True
        except Exception as e:
            self.logger.error(f"Cache optimization failed: {e}")
            return False
    
    async def _optimize_indexes(self, recommendation: OptimizationRecommendation) -> bool:
        """Optimize database indexes"""
        try:
            self.logger.info("Optimizing database indexes")
            # Implementation would analyze and create/drop indexes
            return True
        except Exception as e:
            self.logger.error(f"Index optimization failed: {e}")
            return False
    
    async def _optimize_queries(self, recommendation: OptimizationRecommendation) -> bool:
        """Optimize database queries"""
        try:
            self.logger.info("Optimizing database queries")
            # Implementation would rewrite slow queries
            return True
        except Exception as e:
            self.logger.error(f"Query optimization failed: {e}")
            return False


class CostCalculator:
    """Cost calculation and optimization"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("cost_calculator")
        
        # Cost per resource unit (monthly)
        self.cost_per_unit = {
            'cpu_core': config.get('cpu_cost_per_core', 20.0),
            'memory_gb': config.get('memory_cost_per_gb', 5.0),
            'storage_gb': config.get('storage_cost_per_gb', 0.10),
            'network_gb': config.get('network_cost_per_gb', 0.09),
            'database_connection': config.get('db_connection_cost', 0.50)
        }
    
    def calculate_monthly_cost(self, resource_usage: Dict[str, float]) -> float:
        """Calculate estimated monthly cost"""
        try:
            total_cost = 0.0
            
            # CPU cost
            cpu_cores = resource_usage.get('cpu_cores', 0)
            total_cost += cpu_cores * self.cost_per_unit['cpu_core']
            
            # Memory cost
            memory_gb = resource_usage.get('memory_gb', 0)
            total_cost += memory_gb * self.cost_per_unit['memory_gb']
            
            # Storage cost
            storage_gb = resource_usage.get('storage_gb', 0)
            total_cost += storage_gb * self.cost_per_unit['storage_gb']
            
            # Network cost
            network_gb = resource_usage.get('network_gb_per_month', 0)
            total_cost += network_gb * self.cost_per_unit['network_gb']
            
            # Database connections
            db_connections = resource_usage.get('db_connections', 0)
            total_cost += db_connections * self.cost_per_unit['database_connection']
            
            return total_cost
            
        except Exception as e:
            self.logger.error(f"Cost calculation failed: {e}")
            return 0.0
    
    def optimize_cost(self, current_usage: Dict[str, float]) -> Dict[str, Any]:
        """Generate cost optimization recommendations"""
        recommendations = []
        current_cost = self.calculate_monthly_cost(current_usage)
        
        # Analyze each resource type for optimization potential
        for resource, usage in current_usage.items():
            if resource.endswith('_cores') or resource.endswith('_gb'):
                # Check if resource is underutilized
                if usage < current_usage.get(f"{resource}_target", usage * 0.7):
                    potential_savings = (usage - current_usage.get(f"{resource}_target", usage * 0.7)) * \
                                      self.cost_per_unit.get(resource, 0)
                    
                    if potential_savings > 5.0:  # Only recommend if savings > $5/month
                        recommendations.append({
                            'resource': resource,
                            'current_usage': usage,
                            'recommended_usage': current_usage.get(f"{resource}_target", usage * 0.7),
                            'monthly_savings': potential_savings,
                            'optimization_type': 'downsize'
                        })
        
        total_potential_savings = sum(r['monthly_savings'] for r in recommendations)
        
        return {
            'current_monthly_cost': current_cost,
            'potential_monthly_savings': total_potential_savings,
            'optimized_monthly_cost': current_cost - total_potential_savings,
            'recommendations': recommendations
        }


# Factory functions
def create_performance_monitor(config: Dict[str, Any]) -> PerformanceMonitor:
    """Create performance monitor"""
    return PerformanceMonitor(config)


def create_resource_optimizer(config: Dict[str, Any], monitor: PerformanceMonitor) -> ResourceOptimizer:
    """Create resource optimizer"""
    return ResourceOptimizer(config, monitor)


# Example usage
if __name__ == "__main__":
    async def test_performance_optimization():
        config = {
            'monitoring_interval': 10,
            'cost_config': {
                'cpu_cost_per_core': 20.0,
                'memory_cost_per_gb': 5.0,
                'storage_cost_per_gb': 0.10
            }
        }
        
        # Create performance monitor
        monitor = create_performance_monitor(config)
        monitor.start_monitoring()
        
        # Create optimizer
        optimizer = create_resource_optimizer(config, monitor)
        
        # Wait for some metrics to be collected
        await asyncio.sleep(15)
        
        # Generate recommendations
        recommendations = optimizer.generate_optimization_recommendations()
        print(f"Generated {len(recommendations)} optimization recommendations")
        
        for rec in recommendations[:3]:  # Show top 3
            print(f"- {rec.description}")
            print(f"  Priority: {rec.priority}")
            print(f"  Expected improvement: {rec.expected_improvement}%")
            print(f"  Cost impact: ${rec.cost_impact}/month")
        
        # Get performance summary
        summary = monitor.get_performance_summary()
        print(f"\nPerformance Summary:")
        print(f"Current metrics: {len(summary.get('current_metrics', {}))}")
        print(f"Alerts sent: {summary.get('performance_stats', {}).get('alerts_sent', 0)}")
        
        monitor.stop_monitoring()
    
    # Run test
    asyncio.run(test_performance_optimization())