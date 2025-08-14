# TradingAgents-CN Storage Architecture & Data Tiering Strategy

## Overview

This document outlines the comprehensive storage architecture for TradingAgents-CN, implementing a multi-tier data strategy optimized for real-time trading scenarios while supporting complex analytics queries.

## 1. Storage Architecture Layers

### 1.1 Hot Data Tier (Real-time Access)
**Technology Stack**: Redis Cluster + PostgreSQL Primary
**Data Retention**: Last 7 days
**Access Pattern**: Sub-millisecond reads, frequent writes

```
Hot Tier Components:
├── Redis Cluster (Primary Cache)
│   ├── Real-time quotes (1-minute TTL)
│   ├── Latest market data (1-hour TTL)
│   ├── Active trading signals (4-hour TTL)
│   ├── User sessions (24-hour TTL)
│   └── ML inference cache (30-minute TTL)
├── PostgreSQL Primary
│   ├── Last 7 days market data
│   ├── Active user configurations
│   ├── Current trading positions
│   └── Real-time alert triggers
└── MongoDB Primary
    ├── Latest news (24 hours)
    ├── Recent social sentiment
    ├── Active analysis sessions
    └── Current trading signals
```

### 1.2 Warm Data Tier (Frequent Access)
**Technology Stack**: PostgreSQL + MongoDB + Object Storage
**Data Retention**: 30 days to 2 years
**Access Pattern**: Second-level reads, batch writes

```
Warm Tier Components:
├── PostgreSQL (TimescaleDB)
│   ├── Historical market data (30 days - 2 years)
│   ├── Financial statements (last 10 years)
│   ├── Technical indicators (1 year)
│   └── User activity logs (1 year)
├── MongoDB
│   ├── News archive (6 months)
│   ├── Analysis results (1 year)
│   ├── Social media data (3 months)
│   └── Research reports (2 years)
└── Object Storage (S3/MinIO)
    ├── Chart images and visualizations
    ├── Report exports (PDF/Excel)
    ├── ML model artifacts
    └── Data backups
```

### 1.3 Cold Data Tier (Archival)
**Technology Stack**: Object Storage + Compressed Archives
**Data Retention**: 2+ years (indefinite for compliance)
**Access Pattern**: Rare access, batch processing

```
Cold Tier Components:
├── Object Storage (Glacier/Deep Archive)
│   ├── Historical market data (>2 years)
│   ├── Old news and social media
│   ├── Archived analysis results
│   └── Compliance audit logs
├── Data Lake (Parquet Format)
│   ├── Compressed time-series data
│   ├── Historical ML training datasets
│   ├── Regulatory compliance data
│   └── Historical performance metrics
└── Backup Archives
    ├── Database snapshots
    ├── Configuration backups
    ├── Disaster recovery images
    └── Point-in-time recovery files
```

## 2. Data Movement Policies

### 2.1 Automated Data Lifecycle Management

```yaml
# Data Lifecycle Configuration
lifecycle_policies:
  market_data:
    hot_to_warm: 7d      # Move to warm tier after 7 days
    warm_to_cold: 2y     # Archive after 2 years
    compression: 7d      # Compress after 7 days
    retention: 10y       # Keep for 10 years (regulatory)
  
  news_data:
    hot_to_warm: 1d      # Move to warm after 1 day  
    warm_to_cold: 6m     # Archive after 6 months
    retention: 5y        # Keep for 5 years
  
  social_data:
    hot_to_warm: 4h      # Move to warm after 4 hours
    warm_to_cold: 3m     # Archive after 3 months  
    retention: 2y        # Keep for 2 years
  
  analysis_results:
    hot_to_warm: 7d      # Keep hot for a week
    warm_to_cold: 1y     # Archive after 1 year
    retention: 7y        # Keep for compliance
  
  user_data:
    hot_to_warm: 30d     # Move to warm after 30 days
    warm_to_cold: 2y     # Archive after 2 years
    retention: 7y        # Regulatory compliance
  
  audit_logs:
    hot_to_warm: 1d      # Move to warm daily
    warm_to_cold: 1y     # Archive after 1 year
    retention: 7y        # Regulatory requirement
```

### 2.2 Intelligent Data Placement

```python
# Data Placement Logic
class DataPlacementEngine:
    def __init__(self):
        self.placement_rules = {
            'access_frequency': {
                'high': 'hot',      # >100 requests/day
                'medium': 'warm',   # 10-100 requests/day
                'low': 'cold'       # <10 requests/day
            },
            'data_age': {
                'recent': 'hot',    # <7 days
                'moderate': 'warm', # 7 days - 2 years
                'old': 'cold'       # >2 years
            },
            'importance': {
                'critical': 'hot',  # Real-time trading data
                'important': 'warm', # Analysis results
                'archive': 'cold'   # Historical compliance
            }
        }
    
    def determine_placement(self, data_type, metadata):
        # Intelligent placement based on multiple factors
        score = self.calculate_placement_score(data_type, metadata)
        return self.get_tier_by_score(score)
```

## 3. Redis Caching Strategy (Hot Tier)

### 3.1 Redis Cluster Configuration

```yaml
# Redis Cluster Setup
redis_cluster:
  nodes: 6                    # 3 masters + 3 replicas
  memory_per_node: 8GB
  eviction_policy: allkeys-lru
  persistence: 
    - rdb: enabled           # Point-in-time snapshots
    - aof: everysec         # Append-only file
  
  # Key Partitioning Strategy
  sharding:
    market_data: "consistent_hash"
    user_sessions: "range_based" 
    analysis_cache: "consistent_hash"
```

### 3.2 Cache Key Design & TTL Strategy

```python
# Optimized Cache Key Structure
CACHE_KEYS = {
    # Real-time Data (Short TTL)
    'realtime_quote': 'quote:{symbol}:{market}',           # TTL: 60s
    'latest_price': 'price:{symbol}:latest',               # TTL: 300s
    'volume_spike': 'volume:{symbol}:spike',               # TTL: 600s
    
    # Market Data (Medium TTL)
    'daily_ohlcv': 'ohlcv:{symbol}:{date}',               # TTL: 86400s (1 day)
    'technical_indicators': 'tech:{symbol}:{indicator}',   # TTL: 3600s (1 hour)
    'market_summary': 'summary:{market}:{timeframe}',      # TTL: 1800s (30 min)
    
    # Analysis Data (Long TTL)
    'analysis_result': 'analysis:{symbol}:{session_id}',   # TTL: 7200s (2 hours)
    'sentiment_score': 'sentiment:{symbol}:{timeframe}',   # TTL: 1800s (30 min)
    'news_summary': 'news:{symbol}:{date}',               # TTL: 3600s (1 hour)
    
    # User Data (Variable TTL)
    'user_session': 'session:{user_id}',                  # TTL: 86400s (1 day)
    'user_watchlist': 'watchlist:{user_id}',              # TTL: 3600s (1 hour)
    'user_preferences': 'prefs:{user_id}',                # TTL: 86400s (1 day)
}

# TTL Management
TTL_POLICIES = {
    'market_hours': {
        'trading_hours': 300,      # 5 minutes during market hours
        'after_hours': 1800,       # 30 minutes after market close
        'weekend': 3600            # 1 hour on weekends
    },
    'volatility_based': {
        'high_volatility': 60,     # 1 minute for volatile stocks
        'normal_volatility': 300,  # 5 minutes for normal stocks
        'low_volatility': 900      # 15 minutes for stable stocks
    }
}
```

### 3.3 Cache Warming & Pre-loading Strategy

```python
class CacheWarmingService:
    def __init__(self):
        self.redis_client = redis.RedisCluster(...)
        self.warming_schedule = {
            'pre_market': '08:00',     # Warm cache before market open
            'market_open': '09:30',    # Refresh active symbols
            'mid_session': '12:00',    # Refresh popular symbols
            'post_market': '16:30'     # Cache summary data
        }
    
    async def warm_market_data(self):
        """Pre-load frequently accessed market data"""
        popular_symbols = await self.get_popular_symbols()
        
        tasks = []
        for symbol in popular_symbols:
            tasks.extend([
                self.cache_latest_quote(symbol),
                self.cache_technical_indicators(symbol),
                self.cache_recent_news(symbol)
            ])
        
        await asyncio.gather(*tasks)
    
    async def intelligent_preloading(self):
        """ML-driven cache preloading based on user patterns"""
        predictions = await self.predict_data_access()
        for symbol, probability in predictions.items():
            if probability > 0.7:  # High probability of access
                await self.preload_symbol_data(symbol)
```

## 4. Backup & Disaster Recovery

### 4.1 Backup Strategy

```yaml
backup_strategy:
  # Database Backups
  postgresql:
    full_backup: "daily @ 02:00 UTC"
    incremental: "every 4 hours"
    wal_archiving: "continuous"
    retention: "30 days full, 7 days incremental"
    
  mongodb:
    full_backup: "daily @ 03:00 UTC"  
    oplog_backup: "continuous"
    retention: "30 days full, 7 days oplog"
    
  redis:
    rdb_snapshot: "every 6 hours"
    aof_backup: "daily @ 04:00 UTC"
    retention: "7 days"
  
  # File System Backups  
  application_data:
    backup_frequency: "daily @ 01:00 UTC"
    retention: "90 days"
    compression: "gzip"
    
  configuration:
    backup_frequency: "on change + daily"
    retention: "1 year"
    versioning: "enabled"

# Cross-Region Replication
replication:
  primary_region: "us-east-1"
  backup_regions: ["us-west-2", "eu-west-1"]
  replication_lag: "<30 seconds"
  failover_time: "<5 minutes"
```

### 4.2 Disaster Recovery Procedures

```python
class DisasterRecoveryManager:
    def __init__(self):
        self.recovery_tiers = {
            'tier_1': {  # Critical systems
                'rto': '15 minutes',      # Recovery Time Objective
                'rpo': '1 minute',        # Recovery Point Objective
                'components': ['redis', 'postgresql_primary', 'trading_api']
            },
            'tier_2': {  # Important systems
                'rto': '1 hour',
                'rpo': '15 minutes', 
                'components': ['mongodb', 'analytics_api', 'user_interface']
            },
            'tier_3': {  # Non-critical systems
                'rto': '4 hours',
                'rpo': '1 hour',
                'components': ['reporting', 'batch_jobs', 'archival_data']
            }
        }
    
    async def execute_disaster_recovery(self, incident_type):
        """Execute disaster recovery based on incident severity"""
        if incident_type in ['complete_outage', 'data_corruption']:
            await self.full_system_recovery()
        elif incident_type in ['partial_outage', 'performance_degradation']:
            await self.partial_system_recovery()
        
        # Verify recovery
        await self.verify_system_integrity()
        await self.notify_stakeholders('recovery_complete')
```

## 5. Performance Optimization

### 5.1 Read Optimization Strategies

```python
# Read Optimization Patterns
class ReadOptimizer:
    def __init__(self):
        self.read_patterns = {
            'hot_data': {
                'strategy': 'cache_first',
                'fallback': 'database',
                'timeout': '100ms'
            },
            'warm_data': {
                'strategy': 'database_first', 
                'cache_result': True,
                'timeout': '1s'
            },
            'cold_data': {
                'strategy': 'async_fetch',
                'notification': True,
                'timeout': '30s'
            }
        }
    
    async def optimized_read(self, data_key, tier='auto'):
        """Optimized read with automatic tier detection"""
        if tier == 'auto':
            tier = await self.detect_data_tier(data_key)
        
        strategy = self.read_patterns[f'{tier}_data']['strategy']
        
        if strategy == 'cache_first':
            return await self.cache_first_read(data_key)
        elif strategy == 'database_first':
            return await self.database_first_read(data_key)
        else:
            return await self.async_fetch_read(data_key)
```

### 5.2 Write Optimization Strategies

```python
class WriteOptimizer:
    def __init__(self):
        self.write_patterns = {
            'real_time': {
                'strategy': 'write_through',      # Write to cache + DB
                'consistency': 'strong',
                'batching': False
            },
            'analytical': {
                'strategy': 'write_behind',       # Write to cache, async DB
                'consistency': 'eventual',
                'batching': True,
                'batch_size': 1000
            },
            'archival': {
                'strategy': 'direct_write',       # Skip cache, write to storage
                'consistency': 'eventual',
                'compression': True
            }
        }
    
    async def optimized_write(self, data, data_type='real_time'):
        """Optimized write based on data characteristics"""
        pattern = self.write_patterns[data_type]
        
        if pattern['strategy'] == 'write_through':
            await self.write_through(data)
        elif pattern['strategy'] == 'write_behind':
            await self.write_behind(data, pattern['batch_size'])
        else:
            await self.direct_write(data, pattern['compression'])
```

### 5.3 Query Optimization

```sql
-- Optimized Query Examples

-- 1. Time-series data with proper indexing
EXPLAIN (ANALYZE, BUFFERS) 
SELECT symbol, timestamp, close 
FROM market_data 
WHERE symbol = 'AAPL' 
  AND timestamp >= NOW() - INTERVAL '7 days'
ORDER BY timestamp DESC;

-- 2. Aggregated sentiment analysis
EXPLAIN (ANALYZE, BUFFERS)
SELECT 
    symbol,
    date_trunc('hour', timestamp) as hour,
    avg(sentiment_score) as avg_sentiment,
    count(*) as post_count
FROM social_media_sentiment 
WHERE symbol IN ('AAPL', 'GOOGL', 'MSFT')
  AND timestamp >= NOW() - INTERVAL '1 day'
GROUP BY symbol, date_trunc('hour', timestamp)
ORDER BY hour DESC, symbol;

-- 3. Cross-database correlation query
WITH price_changes AS (
    SELECT symbol, 
           (close - LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp)) / LAG(close) OVER (PARTITION BY symbol ORDER BY timestamp) * 100 as price_change_pct
    FROM market_data 
    WHERE timestamp >= NOW() - INTERVAL '1 day'
),
sentiment_changes AS (
    SELECT symbol,
           avg(sentiment_score) as avg_sentiment
    FROM social_media_sentiment
    WHERE timestamp >= NOW() - INTERVAL '1 day'  
    GROUP BY symbol
)
SELECT p.symbol, p.price_change_pct, s.avg_sentiment,
       corr(p.price_change_pct, s.avg_sentiment) OVER () as correlation
FROM price_changes p
JOIN sentiment_changes s ON p.symbol = s.symbol
WHERE p.price_change_pct IS NOT NULL;
```

## 6. Monitoring & Alerting

### 6.1 Performance Metrics

```yaml
monitoring_metrics:
  # Storage Performance
  storage_metrics:
    - disk_io_utilization
    - storage_latency_p95
    - storage_throughput
    - available_storage_space
    
  # Database Performance  
  database_metrics:
    - connection_pool_utilization
    - query_execution_time_p95
    - slow_query_count
    - replication_lag
    
  # Cache Performance
  cache_metrics:
    - cache_hit_ratio
    - cache_memory_utilization  
    - eviction_rate
    - key_expiration_rate
    
  # Application Performance
  app_metrics:
    - api_response_time
    - throughput_requests_per_second
    - error_rate
    - data_freshness

alert_thresholds:
  critical:
    - cache_hit_ratio < 0.8
    - query_time_p95 > 1000ms
    - replication_lag > 60s
    - error_rate > 5%
    
  warning:
    - storage_utilization > 80%
    - connection_pool_utilization > 70%
    - slow_query_count > 10/min
    - cache_memory_utilization > 85%
```

### 6.2 Automated Scaling & Recovery

```python
class AutoScalingManager:
    def __init__(self):
        self.scaling_policies = {
            'redis_cluster': {
                'scale_out_threshold': 0.8,    # 80% memory utilization
                'scale_in_threshold': 0.3,     # 30% memory utilization  
                'min_nodes': 3,
                'max_nodes': 12
            },
            'postgresql_replicas': {
                'scale_out_threshold': 0.7,    # 70% CPU utilization
                'scale_in_threshold': 0.2,     # 20% CPU utilization
                'min_replicas': 1,
                'max_replicas': 5
            }
        }
    
    async def auto_scale_redis(self, metrics):
        """Automatically scale Redis cluster based on metrics"""
        memory_util = metrics['memory_utilization']
        current_nodes = metrics['node_count']
        
        if memory_util > self.scaling_policies['redis_cluster']['scale_out_threshold']:
            if current_nodes < self.scaling_policies['redis_cluster']['max_nodes']:
                await self.add_redis_node()
                
        elif memory_util < self.scaling_policies['redis_cluster']['scale_in_threshold']:
            if current_nodes > self.scaling_policies['redis_cluster']['min_nodes']:
                await self.remove_redis_node()
```

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up PostgreSQL with TimescaleDB
- [ ] Configure Redis cluster
- [ ] Implement basic data lifecycle policies
- [ ] Set up monitoring infrastructure

### Phase 2: Data Migration (Weeks 3-4)  
- [ ] Create migration scripts from current MongoDB
- [ ] Implement data validation procedures
- [ ] Set up replication and backup systems
- [ ] Test disaster recovery procedures

### Phase 3: Optimization (Weeks 5-6)
- [ ] Implement intelligent caching strategies
- [ ] Set up automated scaling
- [ ] Optimize query performance
- [ ] Fine-tune data tiering policies

### Phase 4: Advanced Features (Weeks 7-8)
- [ ] Implement ML-driven cache warming
- [ ] Set up cross-region replication  
- [ ] Advanced monitoring dashboards
- [ ] Performance testing and tuning

This storage architecture provides a robust, scalable foundation for TradingAgents-CN that can handle both real-time trading requirements and complex analytical workloads while maintaining cost-effectiveness through intelligent data tiering.