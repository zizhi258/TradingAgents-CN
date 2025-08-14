# TradingAgents-CN Sharding & Replication Strategy

## Overview

This document outlines the comprehensive sharding and replication strategies for TradingAgents-CN, ensuring high availability, horizontal scalability, and optimal performance for both transactional and analytical workloads.

## 1. PostgreSQL Sharding Strategy

### 1.1 Sharding Architecture

```yaml
# PostgreSQL Sharding Configuration
postgresql_sharding:
  coordinator_nodes: 3           # Citus coordinator nodes
  worker_nodes: 6               # Initial worker nodes (horizontally scalable)
  replication_factor: 2         # Each shard has 2 replicas
  
  shard_distribution:
    market_data:
      shard_key: "symbol"       # Shard by stock symbol
      shard_count: 16           # 16 shards across 6 worker nodes
      replication: 2            # Each shard replicated twice
    
    technical_indicators:
      shard_key: "symbol"       # Co-located with market_data
      shard_count: 16
      replication: 2
    
    financial_statements:
      shard_key: "symbol"       # Co-located with market_data  
      shard_count: 8            # Less volume than market data
      replication: 2
    
    users:
      shard_key: "user_id"      # Shard by user ID
      shard_count: 4            # Lower volume, fewer shards
      replication: 2
    
    api_usage:
      shard_key: "timestamp"    # Time-based sharding
      shard_count: 12           # Monthly shards
      replication: 2
```

### 1.2 Citus-based Distributed PostgreSQL Setup

```sql
-- Enable Citus extension on coordinator
CREATE EXTENSION citus;

-- Add worker nodes to the cluster
SELECT citus_add_node('worker-1.tradingagents.com', 5432);
SELECT citus_add_node('worker-2.tradingagents.com', 5432);
SELECT citus_add_node('worker-3.tradingagents.com', 5432);
SELECT citus_add_node('worker-4.tradingagents.com', 5432);
SELECT citus_add_node('worker-5.tradingagents.com', 5432);
SELECT citus_add_node('worker-6.tradingagents.com', 5432);

-- Create distributed tables
SELECT create_distributed_table('market_data', 'symbol');
SELECT create_distributed_table('technical_indicators', 'symbol'); 
SELECT create_distributed_table('financial_statements', 'symbol');
SELECT create_distributed_table('financial_metrics', 'symbol');

-- Create reference tables (replicated to all nodes)
SELECT create_reference_table('companies');
SELECT create_reference_table('ml_models');
SELECT create_reference_table('feature_pipelines');

-- User data with different shard key
SELECT create_distributed_table('users', 'id');
SELECT create_distributed_table('user_configs', 'user_id');
SELECT create_distributed_table('api_usage', 'user_id');

-- Time-series tables with time-based sharding
SELECT create_distributed_table('audit_logs', 'timestamp');
SELECT create_distributed_table('performance_logs', 'timestamp');
```

### 1.3 Shard Key Selection Logic

```python
class ShardKeySelector:
    def __init__(self):
        self.shard_strategies = {
            'market_data': {
                'key': 'symbol',
                'algorithm': 'hash',
                'rationale': 'Even distribution, symbol-based queries',
                'co_location': ['technical_indicators', 'financial_data']
            },
            'user_data': {
                'key': 'user_id', 
                'algorithm': 'hash',
                'rationale': 'User isolation, privacy compliance',
                'co_location': ['user_configs', 'user_sessions']
            },
            'time_series': {
                'key': 'timestamp',
                'algorithm': 'range',
                'rationale': 'Time-based queries, efficient pruning',
                'partition_interval': 'monthly'
            }
        }
    
    def get_shard_key(self, table_name, query_patterns):
        """Determine optimal shard key based on access patterns"""
        if 'symbol' in query_patterns['most_frequent_filters']:
            return self.shard_strategies['market_data']
        elif 'user_id' in query_patterns['most_frequent_filters']:
            return self.shard_strategies['user_data']
        elif 'timestamp' in query_patterns['most_frequent_filters']:
            return self.shard_strategies['time_series']
        else:
            return self.analyze_custom_pattern(query_patterns)
```

### 1.4 Query Routing & Optimization

```python
class QueryRouter:
    def __init__(self):
        self.routing_rules = {
            'single_shard_queries': {
                'pattern': 'WHERE symbol = ?',
                'execution': 'single_node',
                'performance': 'optimal'
            },
            'multi_shard_queries': {
                'pattern': 'GROUP BY, ORDER BY without shard key',
                'execution': 'parallel_aggregation',
                'performance': 'good'
            },
            'cross_shard_joins': {
                'pattern': 'JOIN across different shard keys',
                'execution': 'repartition_join',
                'performance': 'expensive'
            }
        }
    
    def optimize_query(self, sql_query):
        """Optimize query for distributed execution"""
        analysis = self.analyze_query(sql_query)
        
        if analysis['type'] == 'single_shard':
            return self.optimize_single_shard(sql_query)
        elif analysis['type'] == 'multi_shard':
            return self.optimize_multi_shard(sql_query)
        else:
            return self.optimize_cross_shard(sql_query)
    
    def optimize_single_shard(self, query):
        """Optimize queries that can run on single shard"""
        # Add shard key filters
        # Use local indexes
        # Minimize coordinator involvement
        return optimized_query
    
    def optimize_multi_shard(self, query):
        """Optimize queries requiring multiple shards"""
        # Parallel execution planning
        # Efficient aggregation strategies  
        # Result set combination
        return optimized_query
```

## 2. MongoDB Sharding Strategy

### 2.1 MongoDB Cluster Architecture

```yaml
# MongoDB Sharded Cluster Configuration
mongodb_cluster:
  config_servers: 3             # Config server replica set
  mongos_routers: 3            # Query router instances
  shard_clusters: 3            # Number of shard replica sets
  
  shard_replica_sets:
    shard01:
      primary: "shard01-primary.tradingagents.com:27018"
      secondaries: 
        - "shard01-secondary1.tradingagents.com:27018"
        - "shard01-secondary2.tradingagents.com:27018"
      arbiter: "shard01-arbiter.tradingagents.com:27018"
    
    shard02:
      primary: "shard02-primary.tradingagents.com:27018" 
      secondaries:
        - "shard02-secondary1.tradingagents.com:27018"
        - "shard02-secondary2.tradingagents.com:27018"
      arbiter: "shard02-arbiter.tradingagents.com:27018"
    
    shard03:
      primary: "shard03-primary.tradingagents.com:27018"
      secondaries:
        - "shard03-secondary1.tradingagents.com:27018" 
        - "shard03-secondary2.tradingagents.com:27018"
      arbiter: "shard03-arbiter.tradingagents.com:27018"

  sharding_strategy:
    news_articles:
      shard_key: { "symbols.symbol": 1, "published_at": 1 }
      shard_distribution: "compound_hashed"
      
    social_media_posts: 
      shard_key: { "symbols.symbol": 1, "posted_at": 1 }
      shard_distribution: "compound_hashed"
      
    agent_analysis_results:
      shard_key: { "symbol": 1, "analysis_timestamp": 1 }
      shard_distribution: "compound_hashed"
      
    multi_agent_sessions:
      shard_key: { "user_id": 1 }
      shard_distribution: "hashed"
      
    trading_signals:
      shard_key: { "symbol": 1, "generated_at": 1 }
      shard_distribution: "compound_hashed"
```

### 2.2 MongoDB Sharding Setup Commands

```javascript
// Initialize Config Server Replica Set
rs.initiate({
  _id: "configReplSet",
  configsvr: true,
  members: [
    { _id: 0, host: "config01.tradingagents.com:27019" },
    { _id: 1, host: "config02.tradingagents.com:27019" },
    { _id: 2, host: "config03.tradingagents.com:27019" }
  ]
});

// Add Shard Replica Sets to Cluster
sh.addShard("shard01/shard01-primary.tradingagents.com:27018,shard01-secondary1.tradingagents.com:27018,shard01-secondary2.tradingagents.com:27018");
sh.addShard("shard02/shard02-primary.tradingagents.com:27018,shard02-secondary1.tradingagents.com:27018,shard02-secondary2.tradingagents.com:27018");
sh.addShard("shard03/shard03-primary.tradingagents.com:27018,shard03-secondary1.tradingagents.com:27018,shard03-secondary2.tradingagents.com:27018");

// Enable Sharding on Database
sh.enableSharding("tradingagents");

// Shard Collections with Optimal Keys
sh.shardCollection("tradingagents.news_articles", { "symbols.symbol": 1, "published_at": 1 });
sh.shardCollection("tradingagents.social_media_posts", { "symbols.symbol": 1, "posted_at": 1 });
sh.shardCollection("tradingagents.agent_analysis_results", { "symbol": 1, "analysis_timestamp": 1 });
sh.shardCollection("tradingagents.multi_agent_sessions", { "user_id": "hashed" });
sh.shardCollection("tradingagents.trading_signals", { "symbol": 1, "generated_at": 1 });

// Configure Balancer Settings
sh.setBalancerState(true);
sh.configureBalancer({
  mode: "full",
  window: {
    start: "02:00",  // Maintenance window
    stop: "06:00"
  }
});
```

### 2.3 Chunk Distribution & Balancing

```javascript
// Custom Balancer Configuration
class MongoBalancerManager {
    constructor() {
        this.balancing_policies = {
            'aggressive': {
                'chunk_size': 64,      // MB
                'migration_threshold': 8,
                'parallel_migrations': 4
            },
            'conservative': {
                'chunk_size': 128,     // MB  
                'migration_threshold': 16,
                'parallel_migrations': 2
            }
        };
    }
    
    optimizeChunkDistribution() {
        // Monitor chunk distribution
        const stats = sh.status();
        
        // Identify hotspots
        const hotShards = this.identifyHotShards(stats);
        
        // Trigger manual splits if needed
        hotShards.forEach(shard => {
            if (shard.chunkSize > this.balancing_policies.aggressive.chunk_size) {
                sh.splitAt(shard.namespace, shard.splitPoint);
            }
        });
    }
}
```

## 3. Redis Cluster Sharding

### 3.1 Redis Cluster Configuration

```yaml
# Redis Cluster Setup
redis_cluster:
  nodes: 6                      # 3 masters + 3 replicas
  slots: 16384                  # Total hash slots
  
  master_nodes:
    redis-master-1:
      host: "redis-m1.tradingagents.com"
      port: 7000
      slots: "0-5460"           # ~5461 slots
      
    redis-master-2:
      host: "redis-m2.tradingagents.com"
      port: 7001  
      slots: "5461-10922"       # ~5461 slots
      
    redis-master-3:
      host: "redis-m3.tradingagents.com"
      port: 7002
      slots: "10923-16383"      # ~5460 slots
  
  replica_nodes:
    redis-replica-1:
      host: "redis-r1.tradingagents.com"
      port: 7003
      replicates: "redis-master-1"
      
    redis-replica-2:
      host: "redis-r2.tradingagents.com"
      port: 7004
      replicates: "redis-master-2"
      
    redis-replica-3:
      host: "redis-r3.tradingagents.com"
      port: 7005
      replicates: "redis-master-3"

# Hash Tag Strategy for Related Keys
key_distribution:
  market_data: 
    pattern: "market:{symbol}:*"
    hash_tag: "{symbol}"        # Ensures co-location
    
  user_sessions:
    pattern: "session:{user_id}:*"
    hash_tag: "{user_id}"       # User data co-location
    
  analysis_cache:
    pattern: "analysis:{symbol}:{type}:*"
    hash_tag: "{symbol}"        # Analysis co-location
```

### 3.2 Redis Cluster Operations

```python
class RedisClusterManager:
    def __init__(self):
        self.cluster = redis.RedisCluster(
            startup_nodes=[
                {"host": "redis-m1.tradingagents.com", "port": "7000"},
                {"host": "redis-m2.tradingagents.com", "port": "7001"},
                {"host": "redis-m3.tradingagents.com", "port": "7002"},
            ],
            decode_responses=True,
            skip_full_coverage_check=True
        )
    
    def get_cluster_info(self):
        """Get cluster topology and health information"""
        nodes = self.cluster.cluster_nodes()
        slots = self.cluster.cluster_slots()
        
        return {
            'nodes': len(nodes),
            'masters': len([n for n in nodes.values() if 'master' in n['flags']]),
            'replicas': len([n for n in nodes.values() if 'slave' in n['flags']]),
            'slot_distribution': self.analyze_slot_distribution(slots)
        }
    
    def rebalance_cluster(self):
        """Rebalance slots across cluster nodes"""
        current_distribution = self.get_slot_distribution()
        target_distribution = self.calculate_optimal_distribution()
        
        migrations = self.plan_slot_migrations(current_distribution, target_distribution)
        
        for migration in migrations:
            self.migrate_slot(migration['slot'], migration['source'], migration['target'])
    
    def ensure_key_co_location(self, key_pattern):
        """Ensure related keys are co-located using hash tags"""
        keys = self.cluster.keys(key_pattern)
        
        for key in keys:
            # Check if key has proper hash tag
            if not self.has_hash_tag(key):
                # Migrate key to proper hash tag format
                new_key = self.add_hash_tag(key)
                self.cluster.rename(key, new_key)
```

## 4. Read Replica Strategy

### 4.1 PostgreSQL Read Replicas

```yaml
# PostgreSQL Read Replica Configuration
postgresql_replicas:
  primary_cluster:
    host: "pg-primary.tradingagents.com"
    port: 5432
    role: "primary"
    
  read_replicas:
    analytics_replica:
      host: "pg-analytics.tradingagents.com"
      port: 5432
      role: "analytics"
      workload: "long_running_queries"
      lag_threshold: "30s"
      
    api_replica:
      host: "pg-api.tradingagents.com"
      port: 5432
      role: "api_queries"
      workload: "short_oltp_queries" 
      lag_threshold: "1s"
      
    reporting_replica:
      host: "pg-reporting.tradingagents.com"
      port: 5432
      role: "reporting"
      workload: "batch_reporting"
      lag_threshold: "5m"

# Connection Routing Rules
connection_routing:
  write_operations: "primary"
  
  read_operations:
    real_time_quotes: "api_replica"        # Low latency required
    user_dashboards: "api_replica"         # Interactive queries
    analytics_queries: "analytics_replica" # Complex aggregations
    batch_reports: "reporting_replica"     # Heavy workloads
```

### 4.2 Intelligent Read/Write Splitting

```python
class DatabaseRouter:
    def __init__(self):
        self.connection_pools = {
            'primary': self.create_primary_pool(),
            'api_replica': self.create_replica_pool('api'),
            'analytics_replica': self.create_replica_pool('analytics'),
            'reporting_replica': self.create_replica_pool('reporting')
        }
        
        self.routing_rules = {
            'write_operations': ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER'],
            'read_operations': ['SELECT'],
            'workload_routing': {
                'real_time': 'api_replica',
                'analytics': 'analytics_replica', 
                'reporting': 'reporting_replica'
            }
        }
    
    def route_query(self, query, workload_type='real_time', read_preference='replica'):
        """Route queries to appropriate database instance"""
        operation = self.detect_operation(query)
        
        if operation in self.routing_rules['write_operations']:
            return self.connection_pools['primary']
        
        elif operation in self.routing_rules['read_operations']:
            if read_preference == 'primary' or self.requires_read_after_write(query):
                return self.connection_pools['primary']
            else:
                target_replica = self.routing_rules['workload_routing'][workload_type]
                
                # Check replica lag before routing
                if self.check_replica_lag(target_replica) < self.get_lag_threshold(workload_type):
                    return self.connection_pools[target_replica]
                else:
                    # Fallback to primary if replica lag is too high
                    return self.connection_pools['primary']
        
        else:
            # DDL operations go to primary
            return self.connection_pools['primary']
    
    def check_replica_lag(self, replica_name):
        """Check replication lag for a specific replica"""
        with self.connection_pools[replica_name].get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT CASE 
                    WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() 
                    THEN 0 
                    ELSE EXTRACT(EPOCH FROM now() - pg_last_xact_replay_timestamp()) 
                END as lag_seconds
            """)
            return cursor.fetchone()[0] or 0
```

### 4.3 MongoDB Read Preference Strategy

```javascript
// MongoDB Read Preference Configuration
const readPreferences = {
    // Real-time data - prefer primary for consistency
    realTimeQuotes: {
        mode: "primaryPreferred",
        maxStalenessSeconds: 30,
        tags: [{ "workload": "realtime" }]
    },
    
    // Analytics queries - can use secondaries
    analyticsQueries: {
        mode: "secondaryPreferred", 
        maxStalenessSeconds: 300,
        tags: [{ "workload": "analytics" }]
    },
    
    // Reporting - dedicated secondary
    reportingQueries: {
        mode: "secondary",
        maxStalenessSeconds: 600,
        tags: [{ "workload": "reporting" }]
    },
    
    // User interface - balance load
    userInterface: {
        mode: "nearest",
        maxStalenessSeconds: 90,
        tags: [{ "datacenter": "local" }]
    }
};

// Connection Examples
const analyticsCollection = db.news_articles.withReadPreference(
    readPreferences.analyticsQueries.mode,
    [readPreferences.analyticsQueries.tags],
    { maxStalenessSeconds: readPreferences.analyticsQueries.maxStalenessSeconds }
);

const realtimeCollection = db.trading_signals.withReadPreference(
    readPreferences.realTimeQuotes.mode,
    [readPreferences.realTimeQuotes.tags],
    { maxStalenessSeconds: readPreferences.realTimeQuotes.maxStalenessSeconds }
);
```

## 5. Failover & High Availability

### 5.1 Automatic Failover Configuration

```yaml
# Failover Configuration
failover_policies:
  postgresql:
    primary_failure_detection: "5s"      # Health check interval
    failover_timeout: "30s"              # Max time for failover
    automatic_failover: true
    failover_priority: 
      - "pg-api.tradingagents.com"       # Promote API replica first
      - "pg-analytics.tradingagents.com" # Fallback option
    
  mongodb:
    election_timeout: "10s"              # Replica set election timeout
    heartbeat_interval: "2s"             # Member heartbeat interval
    priority_members:                    # Election priority
      - { host: "primary", priority: 2 }
      - { host: "secondary1", priority: 1 }
      - { host: "secondary2", priority: 1 }
    
  redis:
    sentinel_quorum: 2                   # Minimum sentinels for failover
    failover_timeout: "60s"              # Redis failover timeout
    down_after_milliseconds: "5000"     # Node failure detection
    parallel_syncs: 1                    # Parallel replica sync during failover
```

### 5.2 Automated Failover Scripts

```python
class FailoverManager:
    def __init__(self):
        self.health_checks = {
            'postgresql': self.check_postgresql_health,
            'mongodb': self.check_mongodb_health,
            'redis': self.check_redis_health
        }
        
        self.failover_procedures = {
            'postgresql': self.postgresql_failover,
            'mongodb': self.mongodb_failover,
            'redis': self.redis_failover
        }
    
    async def monitor_cluster_health(self):
        """Continuous health monitoring with automatic failover"""
        while True:
            for service, health_check in self.health_checks.items():
                try:
                    health_status = await health_check()
                    
                    if not health_status['healthy']:
                        logger.critical(f"{service} primary node failure detected")
                        await self.initiate_failover(service, health_status)
                        
                except Exception as e:
                    logger.error(f"Health check failed for {service}: {e}")
            
            await asyncio.sleep(5)  # 5-second health check interval
    
    async def postgresql_failover(self, failed_node, health_status):
        """Execute PostgreSQL failover procedure"""
        # 1. Identify best replica for promotion
        best_replica = await self.select_promotion_candidate('postgresql')
        
        # 2. Stop accepting writes to failed primary
        await self.isolate_failed_primary(failed_node)
        
        # 3. Promote replica to primary
        await self.promote_replica(best_replica)
        
        # 4. Update connection strings and DNS
        await self.update_connection_routing('postgresql', best_replica)
        
        # 5. Reconfigure remaining replicas
        await self.reconfigure_replicas('postgresql', best_replica)
        
        # 6. Notify applications and operators
        await self.send_failover_notifications('postgresql', failed_node, best_replica)
    
    async def test_failover_procedures(self):
        """Regular failover testing (chaos engineering)"""
        # Scheduled failover tests
        test_schedule = {
            'postgresql': 'monthly',
            'mongodb': 'monthly', 
            'redis': 'bi-weekly'
        }
        
        for service, frequency in test_schedule.items():
            if self.should_run_test(service, frequency):
                await self.execute_controlled_failover_test(service)
```

## 6. Performance Monitoring & Optimization

### 6.1 Shard Performance Metrics

```python
class ShardPerformanceMonitor:
    def __init__(self):
        self.metrics_collectors = {
            'postgresql_shards': self.collect_pg_shard_metrics,
            'mongodb_shards': self.collect_mongo_shard_metrics,
            'redis_cluster': self.collect_redis_cluster_metrics
        }
    
    def collect_pg_shard_metrics(self):
        """Collect PostgreSQL shard performance metrics"""
        metrics = {}
        
        for shard in self.get_pg_shards():
            metrics[shard['name']] = {
                'query_throughput': self.get_queries_per_second(shard),
                'avg_query_time': self.get_avg_query_time(shard),
                'active_connections': self.get_active_connections(shard),
                'replication_lag': self.get_replication_lag(shard),
                'disk_usage': self.get_disk_usage(shard),
                'cpu_utilization': self.get_cpu_utilization(shard),
                'memory_utilization': self.get_memory_utilization(shard)
            }
        
        return metrics
    
    def detect_hot_shards(self, metrics):
        """Identify shards with disproportionately high load"""
        hot_shards = []
        
        avg_throughput = np.mean([m['query_throughput'] for m in metrics.values()])
        std_throughput = np.std([m['query_throughput'] for m in metrics.values()])
        
        threshold = avg_throughput + (2 * std_throughput)  # 2 standard deviations
        
        for shard_name, shard_metrics in metrics.items():
            if shard_metrics['query_throughput'] > threshold:
                hot_shards.append({
                    'name': shard_name,
                    'throughput': shard_metrics['query_throughput'],
                    'avg_query_time': shard_metrics['avg_query_time'],
                    'load_ratio': shard_metrics['query_throughput'] / avg_throughput
                })
        
        return hot_shards
    
    def recommend_rebalancing(self, hot_shards, metrics):
        """Recommend shard rebalancing actions"""
        recommendations = []
        
        for hot_shard in hot_shards:
            if hot_shard['load_ratio'] > 3.0:  # 3x average load
                recommendations.append({
                    'action': 'split_shard',
                    'shard': hot_shard['name'],
                    'reason': f"Load {hot_shard['load_ratio']:.1f}x higher than average",
                    'urgency': 'high'
                })
            elif hot_shard['load_ratio'] > 2.0:  # 2x average load
                recommendations.append({
                    'action': 'migrate_chunks',
                    'shard': hot_shard['name'],
                    'reason': f"Load {hot_shard['load_ratio']:.1f}x higher than average",
                    'urgency': 'medium'
                })
        
        return recommendations
```

### 6.2 Automated Rebalancing

```python
class AutoRebalancer:
    def __init__(self):
        self.rebalancing_policies = {
            'postgresql': {
                'load_threshold': 2.0,      # 2x average load
                'rebalance_window': '02:00-06:00',  # Maintenance window
                'max_concurrent_operations': 2
            },
            'mongodb': {
                'chunk_size_threshold': 128,  # MB
                'imbalance_threshold': 3,     # 3x difference in chunk count
                'balancer_window': '02:00-06:00'
            },
            'redis': {
                'memory_threshold': 0.8,      # 80% memory utilization
                'slot_migration_limit': 100,  # Max slots to migrate at once
                'migration_timeout': '5m'
            }
        }
    
    async def auto_rebalance_postgresql(self):
        """Automatic PostgreSQL shard rebalancing"""
        metrics = await self.collect_pg_shard_metrics()
        hot_shards = self.detect_hot_shards(metrics)
        
        if hot_shards and self.in_maintenance_window():
            recommendations = self.recommend_rebalancing(hot_shards, metrics)
            
            for rec in recommendations:
                if rec['urgency'] == 'high':
                    await self.execute_rebalancing_action(rec)
                elif rec['urgency'] == 'medium' and len(recommendations) <= 2:
                    await self.execute_rebalancing_action(rec)
    
    async def auto_rebalance_mongodb(self):
        """Automatic MongoDB chunk balancing"""
        balancer_stats = await self.get_mongodb_balancer_stats()
        
        if balancer_stats['chunks_imbalanced'] > self.rebalancing_policies['mongodb']['imbalance_threshold']:
            await self.enable_mongodb_balancer()
            
            # Monitor balancing progress
            while await self.is_balancing_active():
                await asyncio.sleep(30)  # Check every 30 seconds
                
            await self.disable_mongodb_balancer()
```

This comprehensive sharding and replication strategy ensures TradingAgents-CN can scale horizontally while maintaining high availability and optimal performance across all data tiers.