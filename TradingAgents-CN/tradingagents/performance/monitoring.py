"""Comprehensive Performance Monitoring and Alerting System

Advanced monitoring system with real-time metrics collection,
alerting, and performance analytics for trading systems.
"""

import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import statistics
import weakref

try:
    import prometheus_client
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

from .database_optimizer import get_database_optimizer
from .cache_optimizer import get_cache_optimizer
from .model_optimizer import get_model_optimizer
from .api_optimizer import get_api_optimizer
from .resource_optimizer import get_resource_optimizer
from ..utils.logging_init import get_logger

logger = get_logger("performance_monitor")


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class Alert:
    """Performance alert"""
    id: str
    timestamp: datetime
    severity: AlertSeverity
    category: str
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricPoint:
    """Individual metric data point"""
    timestamp: datetime
    value: float
    tags: Dict[str, str] = field(default_factory=dict)


class MetricsBuffer:
    """Ring buffer for storing metric time series data"""
    
    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self.data = deque(maxlen=max_points)
        self._lock = threading.Lock()
    
    def add_point(self, value: float, tags: Dict[str, str] = None):
        """Add metric point"""
        with self._lock:
            point = MetricPoint(
                timestamp=datetime.now(),
                value=value,
                tags=tags or {}
            )
            self.data.append(point)
    
    def get_points(self, minutes: int = 60) -> List[MetricPoint]:
        """Get points from last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            return [
                point for point in self.data 
                if point.timestamp > cutoff_time
            ]
    
    def get_latest(self) -> Optional[MetricPoint]:
        """Get latest metric point"""
        with self._lock:
            return self.data[-1] if self.data else None
    
    def calculate_stats(self, minutes: int = 60) -> Dict[str, float]:
        """Calculate statistics for time window"""
        points = self.get_points(minutes)
        if not points:
            return {}
        
        values = [p.value for p in points]
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'min': min(values),
            'max': max(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0,
            'p95': statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            'p99': statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
        }


class MetricsCollector:
    """Advanced metrics collection and aggregation"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.metrics = defaultdict(lambda: MetricsBuffer())
        self.is_collecting = False
        self.collection_thread = None
        self.collection_interval = self.config.get('collection_interval', 30)  # seconds
        
        # Component references
        self.db_optimizer = None
        self.cache_optimizer = None
        self.model_optimizer = None
        self.api_optimizer = None
        self.resource_optimizer = None
        
        # Prometheus metrics if available
        self.prometheus_metrics = {}
        self._setup_prometheus_metrics()
        
        logger.info("Metrics collector initialized")
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics if available"""
        if not PROMETHEUS_AVAILABLE:
            return
        
        self.prometheus_metrics = {
            'api_requests_total': Counter('trading_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status']),
            'api_request_duration': Histogram('trading_api_request_duration_seconds', 'API request duration'),
            'cache_hits_total': Counter('trading_cache_hits_total', 'Cache hits', ['level']),
            'cache_misses_total': Counter('trading_cache_misses_total', 'Cache misses', ['level']),
            'db_query_duration': Histogram('trading_db_query_duration_seconds', 'Database query duration', ['collection']),
            'model_inference_duration': Histogram('trading_model_inference_duration_seconds', 'Model inference duration', ['model']),
            'memory_usage_bytes': Gauge('trading_memory_usage_bytes', 'Memory usage in bytes'),
            'cpu_usage_percent': Gauge('trading_cpu_usage_percent', 'CPU usage percentage'),
            'active_connections': Gauge('trading_active_connections', 'Active connections', ['type']),
        }
    
    def start_collection(self):
        """Start metrics collection"""
        if self.is_collecting:
            return
        
        # Initialize component references
        self.db_optimizer = get_database_optimizer()
        self.cache_optimizer = get_cache_optimizer()
        self.model_optimizer = get_model_optimizer()
        self.api_optimizer = get_api_optimizer()
        self.resource_optimizer = get_resource_optimizer()
        
        self.is_collecting = True
        self.collection_thread = threading.Thread(target=self._collection_loop)
        self.collection_thread.daemon = True
        self.collection_thread.start()
        
        logger.info("Metrics collection started")
    
    def stop_collection(self):
        """Stop metrics collection"""
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=10)
        
        logger.info("Metrics collection stopped")
    
    def _collection_loop(self):
        """Main metrics collection loop"""
        while self.is_collecting:
            try:
                self._collect_all_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(5)
    
    def _collect_all_metrics(self):
        """Collect metrics from all components"""
        try:
            # Database metrics
            db_stats = self.db_optimizer.get_query_statistics()
            if 'average_execution_time' in db_stats:
                self.record_metric('db.avg_query_time', db_stats['average_execution_time'] * 1000)  # ms
            if 'total_queries' in db_stats:
                self.record_metric('db.total_queries', db_stats['total_queries'])
            
            # Cache metrics
            cache_stats = self.cache_optimizer.get_cache_metrics()
            if 'levels' in cache_stats:
                for level, stats in cache_stats['levels'].items():
                    if 'hits' in stats:
                        self.record_metric(f'cache.{level}.hits', stats['hits'])
                    if 'misses' in stats:
                        self.record_metric(f'cache.{level}.misses', stats['misses'])
            
            # Model serving metrics
            model_stats = self.model_optimizer.get_performance_metrics()
            if 'serving_metrics' in model_stats:
                serving = model_stats['serving_metrics']
                if 'avg_inference_time_ms' in serving:
                    self.record_metric('model.avg_inference_time', serving['avg_inference_time_ms'])
                if 'cache_hit_rate' in serving:
                    self.record_metric('model.cache_hit_rate', serving['cache_hit_rate'])
            
            # API metrics
            api_stats = self.api_optimizer.get_performance_metrics()
            if 'api_metrics' in api_stats:
                api = api_stats['api_metrics']
                if 'avg_response_time_ms' in api:
                    self.record_metric('api.avg_response_time', api['avg_response_time_ms'])
                if 'success_rate' in api:
                    self.record_metric('api.success_rate', api['success_rate'])
                if 'active_connections' in api:
                    self.record_metric('api.active_connections', api['active_connections'])
            
            # Resource metrics
            resource_stats = self.resource_optimizer.get_optimization_report()
            if 'resource_metrics' in resource_stats:
                if 'current_metrics' in resource_stats['resource_metrics']:
                    current = resource_stats['resource_metrics']['current_metrics']
                    if current:
                        self.record_metric('system.cpu_percent', current.cpu_percent)
                        self.record_metric('system.memory_percent', current.memory_percent)
            
            # Update Prometheus metrics
            self._update_prometheus_metrics()
            
        except Exception as e:
            logger.error(f"Metric collection error: {e}")
    
    def record_metric(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Record a metric value"""
        self.metrics[metric_name].add_point(value, tags)
    
    def get_metric_stats(self, metric_name: str, minutes: int = 60) -> Dict[str, Any]:
        """Get statistics for a metric"""
        if metric_name not in self.metrics:
            return {'error': f'Metric {metric_name} not found'}
        
        stats = self.metrics[metric_name].calculate_stats(minutes)
        latest = self.metrics[metric_name].get_latest()
        
        return {
            'metric_name': metric_name,
            'time_window_minutes': minutes,
            'statistics': stats,
            'latest_value': latest.value if latest else None,
            'latest_timestamp': latest.timestamp.isoformat() if latest else None
        }
    
    def get_all_metrics_summary(self, minutes: int = 60) -> Dict[str, Any]:
        \"\"\"Get summary of all collected metrics\"\"\"
        summary = {}
        
        for metric_name in self.metrics.keys():
            try:
                summary[metric_name] = self.get_metric_stats(metric_name, minutes)
            except Exception as e:
                summary[metric_name] = {'error': str(e)}
        
        return {
            'summary': summary,
            'collection_time_window_minutes': minutes,
            'total_metrics': len(self.metrics),
            'timestamp': datetime.now().isoformat()
        }
    
    def _update_prometheus_metrics(self):
        \"\"\"Update Prometheus metrics\"\"\"
        if not PROMETHEUS_AVAILABLE or not self.prometheus_metrics:
            return
        
        try:
            # Update Prometheus gauges with latest values
            for metric_name, buffer in self.metrics.items():
                latest = buffer.get_latest()
                if not latest:
                    continue
                
                # Map internal metrics to Prometheus metrics
                if 'cpu_percent' in metric_name and 'cpu_usage_percent' in self.prometheus_metrics:
                    self.prometheus_metrics['cpu_usage_percent'].set(latest.value)
                elif 'memory_percent' in metric_name and 'memory_usage_bytes' in self.prometheus_metrics:
                    # Convert percentage to bytes (approximate)
                    self.prometheus_metrics['memory_usage_bytes'].set(latest.value * 1024 * 1024 * 100)  # Rough estimate
                elif 'active_connections' in metric_name:
                    self.prometheus_metrics['active_connections'].labels(type='api').set(latest.value)
        
        except Exception as e:
            logger.error(f\"Prometheus metrics update error: {e}\")


class AlertManager:
    \"\"\"Advanced alerting system with smart thresholds\"\"\"
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.alert_rules = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_callbacks = []
        self.is_monitoring = False
        self.monitoring_thread = None
        self.check_interval = self.config.get('check_interval', 30)  # seconds
        
        # Alert aggregation to prevent spam
        self.alert_cooldowns = {}
        self.default_cooldown = self.config.get('default_cooldown', 300)  # 5 minutes
        
        # Initialize default alert rules
        self._setup_default_alert_rules()
        
        logger.info(\"Alert manager initialized\")
    
    def _setup_default_alert_rules(self):
        \"\"\"Setup default alert rules for common scenarios\"\"\"
        
        # API performance alerts
        self.add_alert_rule(
            'api_high_response_time',
            metric='api.avg_response_time',
            threshold=2000,  # 2 seconds
            severity=AlertSeverity.WARNING,
            condition='greater',
            message='API response time is high: {value}ms (threshold: {threshold}ms)'
        )
        
        self.add_alert_rule(
            'api_critical_response_time',
            metric='api.avg_response_time',
            threshold=5000,  # 5 seconds
            severity=AlertSeverity.CRITICAL,
            condition='greater',
            message='API response time is critical: {value}ms (threshold: {threshold}ms)'
        )
        
        # Database performance alerts
        self.add_alert_rule(
            'db_slow_queries',
            metric='db.avg_query_time',
            threshold=1000,  # 1 second
            severity=AlertSeverity.WARNING,
            condition='greater',
            message='Database queries are slow: {value}ms (threshold: {threshold}ms)'
        )
        
        # Cache performance alerts  
        self.add_alert_rule(
            'cache_low_hit_rate',
            metric='model.cache_hit_rate',
            threshold=70,  # 70%
            severity=AlertSeverity.WARNING,
            condition='less',
            message='Cache hit rate is low: {value}% (threshold: {threshold}%)'
        )
        
        # System resource alerts
        self.add_alert_rule(
            'high_cpu_usage',
            metric='system.cpu_percent',
            threshold=85,
            severity=AlertSeverity.WARNING,
            condition='greater',
            message='CPU usage is high: {value}% (threshold: {threshold}%)'
        )
        
        self.add_alert_rule(
            'critical_cpu_usage',
            metric='system.cpu_percent',
            threshold=95,
            severity=AlertSeverity.CRITICAL,
            condition='greater',
            message='CPU usage is critical: {value}% (threshold: {threshold}%)'
        )
        
        self.add_alert_rule(
            'high_memory_usage',
            metric='system.memory_percent',
            threshold=80,
            severity=AlertSeverity.WARNING,
            condition='greater',
            message='Memory usage is high: {value}% (threshold: {threshold}%)'
        )
        
        self.add_alert_rule(
            'critical_memory_usage',
            metric='system.memory_percent',
            threshold=90,
            severity=AlertSeverity.CRITICAL,
            condition='greater',
            message='Memory usage is critical: {value}% (threshold: {threshold}%)'
        )
    
    def add_alert_rule(
        self,
        rule_id: str,
        metric: str,
        threshold: float,
        severity: AlertSeverity,
        condition: str = 'greater',
        message: str = '',
        cooldown: int = None
    ):
        \"\"\"Add alert rule\"\"\"
        self.alert_rules[rule_id] = {
            'metric': metric,
            'threshold': threshold,
            'severity': severity,
            'condition': condition,
            'message': message or f'{metric} {condition} {threshold}',
            'cooldown': cooldown or self.default_cooldown,
            'enabled': True
        }
        
        logger.info(f\"Added alert rule: {rule_id}\")
    
    def remove_alert_rule(self, rule_id: str):
        \"\"\"Remove alert rule\"\"\"
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            logger.info(f\"Removed alert rule: {rule_id}\")
    
    def start_monitoring(self, metrics_collector: MetricsCollector):
        \"\"\"Start alert monitoring\"\"\"
        if self.is_monitoring:
            return
        
        self.metrics_collector = metrics_collector
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info(\"Alert monitoring started\")
    
    def stop_monitoring(self):
        \"\"\"Stop alert monitoring\"\"\"
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        logger.info(\"Alert monitoring stopped\")
    
    def _monitoring_loop(self):
        \"\"\"Main alert monitoring loop\"\"\"
        while self.is_monitoring:
            try:
                self._check_all_rules()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f\"Alert monitoring error: {e}\")
                time.sleep(5)
    
    def _check_all_rules(self):
        \"\"\"Check all alert rules against current metrics\"\"\"
        for rule_id, rule in self.alert_rules.items():
            if not rule['enabled']:
                continue
            
            try:
                self._check_rule(rule_id, rule)
            except Exception as e:
                logger.error(f\"Error checking rule {rule_id}: {e}\")
    
    def _check_rule(self, rule_id: str, rule: Dict[str, Any]):
        \"\"\"Check individual alert rule\"\"\"
        metric_name = rule['metric']
        
        # Get current metric value
        if metric_name not in self.metrics_collector.metrics:
            return
        
        latest = self.metrics_collector.metrics[metric_name].get_latest()
        if not latest:
            return
        
        current_value = latest.value
        threshold = rule['threshold']
        condition = rule['condition']
        
        # Check condition
        triggered = False
        if condition == 'greater':
            triggered = current_value > threshold
        elif condition == 'less':
            triggered = current_value < threshold
        elif condition == 'equal':
            triggered = abs(current_value - threshold) < 0.001
        
        if triggered:
            # Check cooldown
            if rule_id in self.alert_cooldowns:
                last_alert_time = self.alert_cooldowns[rule_id]
                if (datetime.now() - last_alert_time).total_seconds() < rule['cooldown']:
                    return
            
            # Create alert
            alert = Alert(
                id=f\"{rule_id}_{int(time.time())}\",
                timestamp=datetime.now(),
                severity=rule['severity'],
                category=metric_name.split('.')[0],
                message=rule['message'].format(
                    value=current_value,
                    threshold=threshold,
                    metric=metric_name
                ),
                metric_name=metric_name,
                metric_value=current_value,
                threshold=threshold,
                metadata={'rule_id': rule_id}
            )
            
            self._trigger_alert(alert)
            self.alert_cooldowns[rule_id] = datetime.now()
        
        else:
            # Check if we need to resolve an active alert
            if rule_id in self.active_alerts:
                alert = self.active_alerts[rule_id]
                alert.resolved = True
                alert.resolved_at = datetime.now()
                
                logger.info(f\"Alert resolved: {alert.message}\")
                del self.active_alerts[rule_id]
    
    def _trigger_alert(self, alert: Alert):
        \"\"\"Trigger an alert\"\"\"
        # Store alert
        self.active_alerts[alert.metadata['rule_id']] = alert
        self.alert_history.append(alert)
        
        # Log alert
        logger.log(
            50 if alert.severity == AlertSeverity.CRITICAL else 40,  # ERROR or WARNING level
            f\"ALERT [{alert.severity.value.upper()}]: {alert.message}\"
        )
        
        # Trigger callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f\"Alert callback error: {e}\")
    
    def add_alert_callback(self, callback: Callable[[Alert], None]):
        \"\"\"Add alert callback\"\"\"
        self.alert_callbacks.append(callback)
    
    def get_active_alerts(self) -> List[Alert]:
        \"\"\"Get all active alerts\"\"\"
        return list(self.active_alerts.values())
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        \"\"\"Get alert summary for time period\"\"\"
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_alerts = [
            alert for alert in self.alert_history
            if alert.timestamp > cutoff_time
        ]
        
        # Group by severity
        severity_counts = defaultdict(int)
        category_counts = defaultdict(int)
        
        for alert in recent_alerts:
            severity_counts[alert.severity.value] += 1
            category_counts[alert.category] += 1
        
        return {
            'time_period_hours': hours,
            'total_alerts': len(recent_alerts),
            'active_alerts': len(self.active_alerts),
            'severity_breakdown': dict(severity_counts),
            'category_breakdown': dict(category_counts),
            'recent_alerts': [
                {
                    'id': alert.id,
                    'timestamp': alert.timestamp.isoformat(),
                    'severity': alert.severity.value,
                    'message': alert.message,
                    'resolved': alert.resolved
                }
                for alert in recent_alerts[-20:]  # Last 20 alerts
            ]
        }


class PerformanceMonitor:
    \"\"\"Main performance monitoring coordinator\"\"\"
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize components
        self.metrics_collector = MetricsCollector(
            self.config.get('metrics', {})
        )
        self.alert_manager = AlertManager(
            self.config.get('alerts', {})
        )
        
        # Prometheus server
        self.prometheus_port = self.config.get('prometheus_port', 9090)
        self.prometheus_server = None
        
        logger.info(\"Performance monitor initialized\")
    
    def start(self):
        \"\"\"Start performance monitoring\"\"\"
        # Start metrics collection
        self.metrics_collector.start_collection()
        
        # Start alert monitoring
        self.alert_manager.start_monitoring(self.metrics_collector)
        
        # Start Prometheus server if available
        if PROMETHEUS_AVAILABLE and self.config.get('enable_prometheus', True):
            try:
                self.prometheus_server = start_http_server(self.prometheus_port)
                logger.info(f\"Prometheus metrics server started on port {self.prometheus_port}\")
            except Exception as e:
                logger.error(f\"Failed to start Prometheus server: {e}\")
        
        logger.info(\"Performance monitoring started\")
    
    def stop(self):
        \"\"\"Stop performance monitoring\"\"\"
        self.metrics_collector.stop_collection()
        self.alert_manager.stop_monitoring()
        
        logger.info(\"Performance monitoring stopped\")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        \"\"\"Get comprehensive dashboard data\"\"\"
        return {
            'metrics': self.metrics_collector.get_all_metrics_summary(),
            'alerts': self.alert_manager.get_alert_summary(),
            'system_health': self._get_system_health(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_system_health(self) -> Dict[str, Any]:
        \"\"\"Get overall system health status\"\"\"
        # Get latest metrics for key indicators
        key_metrics = [
            'api.avg_response_time',
            'system.cpu_percent',
            'system.memory_percent',
            'model.cache_hit_rate'
        ]
        
        health_status = {}
        overall_health = 'good'  # good, warning, critical
        
        for metric_name in key_metrics:
            if metric_name in self.metrics_collector.metrics:
                latest = self.metrics_collector.metrics[metric_name].get_latest()
                if latest:
                    health_status[metric_name] = latest.value
                    
                    # Simple health assessment
                    if metric_name == 'api.avg_response_time' and latest.value > 2000:
                        overall_health = 'warning' if overall_health == 'good' else overall_health
                    elif metric_name == 'system.cpu_percent' and latest.value > 85:
                        overall_health = 'critical' if latest.value > 95 else 'warning'
                    elif metric_name == 'system.memory_percent' and latest.value > 85:
                        overall_health = 'critical' if latest.value > 95 else 'warning'
        
        active_alerts = len(self.alert_manager.get_active_alerts())
        critical_alerts = len([
            a for a in self.alert_manager.get_active_alerts()
            if a.severity == AlertSeverity.CRITICAL
        ])
        
        if critical_alerts > 0:
            overall_health = 'critical'
        elif active_alerts > 5:
            overall_health = 'warning' if overall_health == 'good' else overall_health
        
        return {
            'overall_status': overall_health,
            'key_metrics': health_status,
            'active_alerts': active_alerts,
            'critical_alerts': critical_alerts
        }


# Global performance monitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    \"\"\"Get global performance monitor instance\"\"\"
    global _performance_monitor
    
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    
    return _performance_monitor