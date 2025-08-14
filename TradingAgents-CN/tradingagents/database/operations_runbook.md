# TradingAgents-CN Database Operations Runbook

## Overview

This runbook provides comprehensive operational procedures for managing the TradingAgents-CN database infrastructure. It serves as the definitive guide for database administrators, DevOps engineers, and developers working with the system.

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Daily Operations](#2-daily-operations)
3. [Monitoring & Alerting](#3-monitoring--alerting)
4. [Performance Optimization](#4-performance-optimization)
5. [Backup & Recovery](#5-backup--recovery)
6. [Troubleshooting Guide](#6-troubleshooting-guide)
7. [Emergency Procedures](#7-emergency-procedures)
8. [Maintenance Windows](#8-maintenance-windows)
9. [Security Operations](#9-security-operations)
10. [Capacity Planning](#10-capacity-planning)

## 1. System Architecture Overview

### 1.1 Database Infrastructure Components

```yaml
# Production Database Infrastructure
production_infrastructure:
  # Primary Databases
  postgresql_primary:
    host: "pg-primary.tradingagents.com"
    port: 5432
    version: "15.4"
    extensions: ["timescaledb", "pg_stat_statements", "pg_repack"]
    role: "Primary (Read/Write)"
    
  postgresql_replicas:
    api_replica:
      host: "pg-api.tradingagents.com"
      purpose: "Real-time API queries"
      lag_threshold: "1s"
    
    analytics_replica:
      host: "pg-analytics.tradingagents.com"
      purpose: "Complex analytics queries"
      lag_threshold: "30s"
    
    reporting_replica:
      host: "pg-reporting.tradingagents.com"
      purpose: "Batch reporting workloads"
      lag_threshold: "5m"
  
  # MongoDB Cluster
  mongodb_cluster:
    config_servers: 3
    mongos_routers: 3
    shard_replica_sets: 3
    purpose: "Document storage (news, analysis, social media)"
  
  # Redis Cluster
  redis_cluster:
    master_nodes: 3
    replica_nodes: 3
    purpose: "High-speed caching and real-time data"
  
  # Object Storage
  object_storage:
    provider: "AWS S3 / MinIO"
    purpose: "Archival data and backups"
    tiers: ["hot", "warm", "cold"]
```

### 1.2 Connection Strings & Endpoints

```bash
# PostgreSQL Connections
export PG_PRIMARY="postgresql://username:password@pg-primary.tradingagents.com:5432/tradingagents"
export PG_API_REPLICA="postgresql://username:password@pg-api.tradingagents.com:5432/tradingagents"
export PG_ANALYTICS_REPLICA="postgresql://username:password@pg-analytics.tradingagents.com:5432/tradingagents"

# MongoDB Connections
export MONGO_URI="mongodb://username:password@mongos-1.tradingagents.com:27017,mongos-2.tradingagents.com:27017,mongos-3.tradingagents.com:27017/tradingagents?authSource=admin"

# Redis Connections
export REDIS_CLUSTER="redis://redis-m1.tradingagents.com:7000,redis-m2.tradingagents.com:7001,redis-m3.tradingagents.com:7002"
```

## 2. Daily Operations

### 2.1 Daily Health Check Checklist

```bash
#!/bin/bash
# Daily Database Health Check Script

echo "=== TradingAgents-CN Database Health Check ==="
echo "Date: $(date)"
echo "Operator: $USER"
echo

# PostgreSQL Health Check
echo "1. PostgreSQL Primary Health:"
psql $PG_PRIMARY -c "
    SELECT 
        version() as version,
        current_timestamp as current_time,
        pg_is_in_recovery() as is_replica,
        pg_database_size('tradingagents')/1024/1024/1024 as db_size_gb;
"

echo "2. PostgreSQL Replication Status:"
psql $PG_PRIMARY -c "
    SELECT 
        client_addr,
        application_name,
        state,
        sent_lsn,
        write_lsn,
        flush_lsn,
        replay_lsn,
        sync_state
    FROM pg_stat_replication;
"

# Check slow queries
echo "3. Slow Queries (>1s in last 24 hours):"
psql $PG_PRIMARY -c "
    SELECT 
        query,
        calls,
        total_time,
        mean_time,
        rows
    FROM pg_stat_statements 
    WHERE mean_time > 1000 
    ORDER BY mean_time DESC 
    LIMIT 10;
"

# MongoDB Health Check
echo "4. MongoDB Cluster Status:"
mongosh $MONGO_URI --eval "
    db.adminCommand('ismaster');
    sh.status();
"

# Redis Cluster Health Check  
echo "5. Redis Cluster Status:"
redis-cli -c -h redis-m1.tradingagents.com -p 7000 cluster info
redis-cli -c -h redis-m1.tradingagents.com -p 7000 cluster nodes

# Check disk space
echo "6. Disk Space Status:"
df -h

# Check system load
echo "7. System Load:"
uptime

echo "=== Health Check Complete ==="
```

### 2.2 Performance Metrics Collection

```python
#!/usr/bin/env python3
# Daily Performance Metrics Collection

import psycopg2
import pymongo
import redis
import json
from datetime import datetime, timedelta

class DailyMetricsCollector:
    def __init__(self):
        self.metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'postgresql': {},
            'mongodb': {},
            'redis': {},
            'system': {}
        }
    
    def collect_postgresql_metrics(self):
        """Collect PostgreSQL performance metrics"""
        with psycopg2.connect(os.getenv('PG_PRIMARY')) as conn:
            with conn.cursor() as cur:
                # Connection stats
                cur.execute("""
                    SELECT 
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections,
                        count(*) FILTER (WHERE state = 'idle') as idle_connections
                    FROM pg_stat_activity;
                """)
                self.metrics['postgresql']['connections'] = dict(zip(
                    ['total', 'active', 'idle'], cur.fetchone()
                ))
                
                # Query performance
                cur.execute("""
                    SELECT 
                        count(*) as total_queries,
                        avg(total_time) as avg_execution_time,
                        sum(calls) as total_calls
                    FROM pg_stat_statements
                    WHERE last_exec > NOW() - INTERVAL '24 hours';
                """)
                result = cur.fetchone()
                if result:
                    self.metrics['postgresql']['query_performance'] = {
                        'total_queries': result[0],
                        'avg_execution_time_ms': float(result[1]) if result[1] else 0,
                        'total_calls': result[2]
                    }
                
                # Database size
                cur.execute("""
                    SELECT 
                        pg_database_size('tradingagents')/1024/1024/1024 as size_gb,
                        (SELECT count(*) FROM market_data) as market_data_rows,
                        (SELECT count(*) FROM technical_indicators) as indicator_rows
                """)
                result = cur.fetchone()
                self.metrics['postgresql']['database_size'] = {
                    'total_size_gb': float(result[0]),
                    'market_data_rows': result[1],
                    'technical_indicators_rows': result[2]
                }
    
    def collect_mongodb_metrics(self):
        """Collect MongoDB performance metrics"""
        client = pymongo.MongoClient(os.getenv('MONGO_URI'))
        db = client.tradingagents
        
        # Database stats
        stats = db.command('dbstats')
        self.metrics['mongodb']['database_stats'] = {
            'collections': stats['collections'],
            'objects': stats['objects'],
            'data_size_mb': stats['dataSize'] / 1024 / 1024,
            'storage_size_mb': stats['storageSize'] / 1024 / 1024,
            'index_size_mb': stats['indexSize'] / 1024 / 1024
        }
        
        # Collection stats
        collection_stats = {}
        for collection_name in ['news_articles', 'agent_analysis_results', 'trading_signals']:
            try:
                coll_stats = db.command('collstats', collection_name)
                collection_stats[collection_name] = {
                    'count': coll_stats['count'],
                    'size_mb': coll_stats['size'] / 1024 / 1024,
                    'avg_obj_size': coll_stats['avgObjSize']
                }
            except:
                collection_stats[collection_name] = {'error': 'Collection not found'}
        
        self.metrics['mongodb']['collections'] = collection_stats
    
    def collect_redis_metrics(self):
        """Collect Redis performance metrics"""
        r = redis.RedisCluster.from_url(os.getenv('REDIS_CLUSTER'))
        
        # Get cluster info
        cluster_info = {}
        for node in r.get_nodes():
            node_info = node.redis_connection.info()
            cluster_info[f"{node.host}:{node.port}"] = {
                'used_memory_mb': node_info['used_memory'] / 1024 / 1024,
                'connected_clients': node_info['connected_clients'],
                'total_commands_processed': node_info['total_commands_processed'],
                'keyspace_hits': node_info['keyspace_hits'],
                'keyspace_misses': node_info['keyspace_misses']
            }
        
        self.metrics['redis']['cluster_nodes'] = cluster_info
        
        # Calculate hit ratio
        total_hits = sum(node['keyspace_hits'] for node in cluster_info.values())
        total_misses = sum(node['keyspace_misses'] for node in cluster_info.values())
        hit_ratio = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        
        self.metrics['redis']['performance'] = {
            'cache_hit_ratio': hit_ratio,
            'total_memory_mb': sum(node['used_memory_mb'] for node in cluster_info.values())
        }
    
    def save_metrics(self):
        """Save collected metrics"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'/var/log/tradingagents/daily_metrics_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(self.metrics, f, indent=2, default=str)
        
        print(f"Metrics saved to {filename}")
        return filename

if __name__ == "__main__":
    collector = DailyMetricsCollector()
    collector.collect_postgresql_metrics()
    collector.collect_mongodb_metrics() 
    collector.collect_redis_metrics()
    collector.save_metrics()
```

## 3. Monitoring & Alerting

### 3.1 Critical Alerts Configuration

```yaml
# Prometheus Alert Rules for TradingAgents-CN Databases
alert_rules:
  # PostgreSQL Alerts
  postgresql_alerts:
    - alert: PostgreSQLDown
      expr: pg_up == 0
      for: 1m
      severity: critical
      description: "PostgreSQL instance {{ $labels.instance }} is down"
      
    - alert: PostgreSQLReplicationLag
      expr: pg_replication_lag_seconds > 60
      for: 5m  
      severity: warning
      description: "PostgreSQL replica lag is {{ $value }}s on {{ $labels.instance }}"
      
    - alert: PostgreSQLSlowQueries
      expr: rate(pg_stat_statements_mean_time_ms[5m]) > 1000
      for: 10m
      severity: warning
      description: "PostgreSQL has slow queries averaging {{ $value }}ms"
      
    - alert: PostgreSQLConnectionsHigh
      expr: pg_stat_activity_count / pg_settings_max_connections > 0.8
      for: 5m
      severity: warning
      description: "PostgreSQL connections at {{ $value }}% of max"
  
  # MongoDB Alerts
  mongodb_alerts:
    - alert: MongoDBDown
      expr: mongodb_up == 0
      for: 1m
      severity: critical
      description: "MongoDB instance {{ $labels.instance }} is down"
      
    - alert: MongoDBReplicationLag
      expr: mongodb_replica_lag_seconds > 30
      for: 5m
      severity: warning
      description: "MongoDB replica lag is {{ $value }}s"
      
    - alert: MongoDBMemoryUsageHigh
      expr: mongodb_memory_resident_mb / mongodb_memory_available_mb > 0.9
      for: 10m
      severity: warning
      description: "MongoDB memory usage at {{ $value }}%"
  
  # Redis Alerts
  redis_alerts:
    - alert: RedisDown
      expr: redis_up == 0
      for: 1m
      severity: critical
      description: "Redis instance {{ $labels.instance }} is down"
      
    - alert: RedisCacheHitRateLow
      expr: redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) < 0.8
      for: 10m
      severity: warning
      description: "Redis cache hit rate is {{ $value }}%"
      
    - alert: RedisMemoryUsageHigh
      expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
      for: 5m
      severity: warning
      description: "Redis memory usage at {{ $value }}%"

# Grafana Dashboard Configuration
grafana_dashboards:
  - name: "TradingAgents PostgreSQL Overview"
    panels:
      - "Connection count over time"
      - "Query execution time percentiles"
      - "Database size growth"
      - "Replication lag"
      - "Lock waits and deadlocks"
      
  - name: "TradingAgents MongoDB Overview"
    panels:
      - "Operations per second"
      - "Document counts by collection"
      - "Memory usage by node"
      - "Shard distribution"
      - "Index efficiency"
      
  - name: "TradingAgents Redis Overview"
    panels:
      - "Cache hit/miss ratio"
      - "Memory usage by node"
      - "Commands per second"
      - "Key expiration rate"
      - "Cluster health status"
```

### 3.2 Health Check Endpoints

```python
# Health Check API Endpoints
from flask import Flask, jsonify
import psycopg2
import pymongo
import redis
import time

app = Flask(__name__)

class HealthChecker:
    def __init__(self):
        self.checks = {
            'postgresql': self.check_postgresql,
            'mongodb': self.check_mongodb,
            'redis': self.check_redis
        }
    
    def check_postgresql(self):
        """Check PostgreSQL health"""
        try:
            start_time = time.time()
            with psycopg2.connect(os.getenv('PG_PRIMARY')) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'connection': 'successful'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'connection': 'failed'
            }
    
    def check_mongodb(self):
        """Check MongoDB health"""
        try:
            start_time = time.time()
            client = pymongo.MongoClient(os.getenv('MONGO_URI'))
            client.admin.command('ping')
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'connection': 'successful'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'connection': 'failed'
            }
    
    def check_redis(self):
        """Check Redis health"""
        try:
            start_time = time.time()
            r = redis.RedisCluster.from_url(os.getenv('REDIS_CLUSTER'))
            r.ping()
            
            response_time = (time.time() - start_time) * 1000  # ms
            
            return {
                'status': 'healthy',
                'response_time_ms': round(response_time, 2),
                'cluster_status': 'connected'
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'cluster_status': 'disconnected'
            }

health_checker = HealthChecker()

@app.route('/health')
def health_check():
    """Overall health check endpoint"""
    results = {}
    overall_status = 'healthy'
    
    for service_name, check_func in health_checker.checks.items():
        results[service_name] = check_func()
        if results[service_name]['status'] == 'unhealthy':
            overall_status = 'unhealthy'
    
    return jsonify({
        'overall_status': overall_status,
        'timestamp': time.time(),
        'services': results
    })

@app.route('/health/<service>')
def service_health_check(service):
    """Individual service health check"""
    if service not in health_checker.checks:
        return jsonify({'error': f'Service {service} not found'}), 404
    
    result = health_checker.checks[service]()
    return jsonify(result)
```

## 4. Performance Optimization

### 4.1 Query Optimization Procedures

```sql
-- PostgreSQL Query Optimization Toolkit

-- 1. Identify slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
WHERE mean_time > 100  -- Queries slower than 100ms
ORDER BY mean_time DESC
LIMIT 20;

-- 2. Analyze table bloat
SELECT 
    schemaname,
    tablename,
    n_tup_ins as inserts,
    n_tup_upd as updates,
    n_tup_del as deletes,
    n_live_tup as live_tuples,
    n_dead_tup as dead_tuples,
    round(100 * n_dead_tup / (n_live_tup + n_dead_tup + 1), 2) as dead_tuple_percent
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY dead_tuple_percent DESC;

-- 3. Index usage analysis
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE idx_tup_read = 0  -- Unused indexes
ORDER BY pg_relation_size(indexrelid) DESC;

-- 4. Lock analysis
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.DATABASE IS NOT DISTINCT FROM blocked_locks.DATABASE
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

### 4.2 Index Maintenance Scripts

```bash
#!/bin/bash
# PostgreSQL Index Maintenance Script

echo "=== PostgreSQL Index Maintenance ==="
echo "Started at: $(date)"

# Function to run maintenance on a specific table
maintain_table() {
    local table_name=$1
    local schema_name=${2:-public}
    
    echo "Maintaining table: $schema_name.$table_name"
    
    # Get table size before maintenance
    size_before=$(psql $PG_PRIMARY -t -c "SELECT pg_size_pretty(pg_total_relation_size('$schema_name.$table_name'));")
    echo "Table size before: $size_before"
    
    # Analyze table
    echo "Running ANALYZE..."
    psql $PG_PRIMARY -c "ANALYZE $schema_name.$table_name;"
    
    # Check if vacuum is needed
    dead_tuples=$(psql $PG_PRIMARY -t -c "SELECT n_dead_tup FROM pg_stat_user_tables WHERE schemaname='$schema_name' AND relname='$table_name';")
    live_tuples=$(psql $PG_PRIMARY -t -c "SELECT n_live_tup FROM pg_stat_user_tables WHERE schemaname='$schema_name' AND relname='$table_name';")
    
    if [ $dead_tuples -gt 0 ] && [ $live_tuples -gt 0 ]; then
        dead_ratio=$(echo "scale=2; $dead_tuples * 100 / ($dead_tuples + $live_tuples)" | bc)
        echo "Dead tuple ratio: $dead_ratio%"
        
        if (( $(echo "$dead_ratio > 10" | bc -l) )); then
            echo "Running VACUUM..."
            psql $PG_PRIMARY -c "VACUUM $schema_name.$table_name;"
        fi
    fi
    
    # Get table size after maintenance
    size_after=$(psql $PG_PRIMARY -t -c "SELECT pg_size_pretty(pg_total_relation_size('$schema_name.$table_name'));")
    echo "Table size after: $size_after"
    echo "---"
}

# Maintain critical tables
maintain_table "market_data"
maintain_table "technical_indicators" 
maintain_table "api_usage"
maintain_table "audit_logs"

# Reindex if needed (during maintenance window only)
if [ "$1" == "--full-maintenance" ]; then
    echo "Running REINDEX on critical tables..."
    psql $PG_PRIMARY -c "REINDEX TABLE market_data;"
    psql $PG_PRIMARY -c "REINDEX TABLE technical_indicators;"
fi

echo "Index maintenance completed at: $(date)"
```

## 5. Backup & Recovery

### 5.1 Automated Backup Scripts

```bash
#!/bin/bash
# Comprehensive Database Backup Script

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/tradingagents"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR/{postgresql,mongodb,redis}

echo "=== TradingAgents Database Backup Started ==="
echo "Backup Date: $BACKUP_DATE"

# PostgreSQL Backup
echo "1. PostgreSQL Backup..."
export PGPASSWORD="$POSTGRES_PASSWORD"

# Full database dump
pg_dump -h pg-primary.tradingagents.com -U postgres -d tradingagents \
    --verbose --format=custom --compress=9 \
    --file="$BACKUP_DIR/postgresql/tradingagents_full_$BACKUP_DATE.dump"

# Schema-only backup for quick recovery testing
pg_dump -h pg-primary.tradingagents.com -U postgres -d tradingagents \
    --schema-only --verbose \
    --file="$BACKUP_DIR/postgresql/tradingagents_schema_$BACKUP_DATE.sql"

# Globals (roles, tablespaces, etc.)
pg_dumpall -h pg-primary.tradingagents.com -U postgres \
    --globals-only --verbose \
    --file="$BACKUP_DIR/postgresql/globals_$BACKUP_DATE.sql"

echo "PostgreSQL backup completed."

# MongoDB Backup
echo "2. MongoDB Backup..."
mongodump --uri="$MONGO_URI" \
    --out="$BACKUP_DIR/mongodb/dump_$BACKUP_DATE" \
    --gzip

echo "MongoDB backup completed."

# Redis Backup
echo "3. Redis Backup..."
for node in redis-m1.tradingagents.com:7000 redis-m2.tradingagents.com:7001 redis-m3.tradingagents.com:7002; do
    host=$(echo $node | cut -d: -f1)
    port=$(echo $node | cut -d: -f2)
    
    # Create RDB snapshot
    redis-cli -h $host -p $port BGSAVE
    
    # Wait for background save to complete
    while [ $(redis-cli -h $host -p $port LASTSAVE) -eq $(redis-cli -h $host -p $port LASTSAVE) ]; do
        sleep 1
    done
    
    # Copy RDB file
    scp $host:/var/lib/redis/dump.rdb "$BACKUP_DIR/redis/redis_${host}_${port}_$BACKUP_DATE.rdb"
done

echo "Redis backup completed."

# Create backup manifest
cat > "$BACKUP_DIR/backup_manifest_$BACKUP_DATE.json" << EOF
{
    "backup_date": "$BACKUP_DATE",
    "backup_type": "full",
    "components": {
        "postgresql": {
            "full_dump": "postgresql/tradingagents_full_$BACKUP_DATE.dump",
            "schema_only": "postgresql/tradingagents_schema_$BACKUP_DATE.sql",
            "globals": "postgresql/globals_$BACKUP_DATE.sql"
        },
        "mongodb": {
            "dump_directory": "mongodb/dump_$BACKUP_DATE"
        },
        "redis": {
            "master_nodes": [
                "redis/redis_redis-m1.tradingagents.com_7000_$BACKUP_DATE.rdb",
                "redis/redis_redis-m2.tradingagents.com_7001_$BACKUP_DATE.rdb",
                "redis/redis_redis-m3.tradingagents.com_7002_$BACKUP_DATE.rdb"
            ]
        }
    },
    "sizes": {
        "postgresql_mb": $(du -m $BACKUP_DIR/postgresql/ | tail -1 | cut -f1),
        "mongodb_mb": $(du -m $BACKUP_DIR/mongodb/ | tail -1 | cut -f1),
        "redis_mb": $(du -m $BACKUP_DIR/redis/ | tail -1 | cut -f1)
    }
}
EOF

# Compress backup directory
tar -czf "$BACKUP_DIR/tradingagents_backup_$BACKUP_DATE.tar.gz" -C "$BACKUP_DIR" \
    postgresql mongodb redis backup_manifest_$BACKUP_DATE.json

# Upload to object storage (if configured)
if [ -n "$S3_BACKUP_BUCKET" ]; then
    echo "4. Uploading to S3..."
    aws s3 cp "$BACKUP_DIR/tradingagents_backup_$BACKUP_DATE.tar.gz" \
        "s3://$S3_BACKUP_BUCKET/daily/"
fi

# Cleanup old backups
echo "5. Cleaning up old backups..."
find $BACKUP_DIR -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.dump" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.rdb" -mtime +$RETENTION_DAYS -delete

echo "=== Backup Completed Successfully ==="
echo "Backup size: $(du -h $BACKUP_DIR/tradingagents_backup_$BACKUP_DATE.tar.gz | cut -f1)"
echo "Backup location: $BACKUP_DIR/tradingagents_backup_$BACKUP_DATE.tar.gz"
```

### 5.2 Point-in-Time Recovery Procedures

```bash
#!/bin/bash
# Point-in-Time Recovery (PITR) Script for PostgreSQL

RECOVERY_TARGET_TIME=$1
BACKUP_FILE=$2

if [ -z "$RECOVERY_TARGET_TIME" ] || [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 'YYYY-MM-DD HH:MI:SS' /path/to/backup.dump"
    echo "Example: $0 '2024-01-15 14:30:00' /var/backups/tradingagents_full_20240115_120000.dump"
    exit 1
fi

echo "=== PostgreSQL Point-in-Time Recovery ==="
echo "Recovery target time: $RECOVERY_TARGET_TIME"
echo "Backup file: $BACKUP_FILE"

# Confirm recovery
read -p "This will replace the current database. Continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Stop application services
echo "1. Stopping application services..."
systemctl stop tradingagents-web
systemctl stop tradingagents-api
systemctl stop tradingagents-scheduler

# Stop PostgreSQL
echo "2. Stopping PostgreSQL..."
systemctl stop postgresql

# Backup current data (safety measure)
echo "3. Creating safety backup..."
mv /var/lib/postgresql/15/main /var/lib/postgresql/15/main.recovery_backup_$(date +%s)

# Initialize new data directory
echo "4. Initializing new data directory..."
sudo -u postgres /usr/lib/postgresql/15/bin/initdb -D /var/lib/postgresql/15/main

# Configure recovery
echo "5. Configuring recovery..."
sudo -u postgres cat > /var/lib/postgresql/15/main/postgresql.conf << EOF
# Recovery configuration
restore_command = 'cp /var/lib/postgresql/15/archive/%f %p'
recovery_target_time = '$RECOVERY_TARGET_TIME'
recovery_target_action = 'promote'
EOF

# Create recovery signal file
sudo -u postgres touch /var/lib/postgresql/15/main/recovery.signal

# Start PostgreSQL in recovery mode
echo "6. Starting PostgreSQL for recovery..."
systemctl start postgresql

# Wait for recovery to complete
echo "7. Waiting for recovery to complete..."
while [ -f /var/lib/postgresql/15/main/recovery.signal ]; do
    echo "Recovery in progress..."
    sleep 5
done

# Restore database from backup
echo "8. Restoring database from backup..."
export PGPASSWORD="$POSTGRES_PASSWORD"
pg_restore -h localhost -U postgres -d tradingagents --verbose --clean --if-exists "$BACKUP_FILE"

echo "9. Recovery completed successfully!"
echo "Please verify data integrity before restarting application services."
```

## 6. Troubleshooting Guide

### 6.1 Common Issues & Solutions

```yaml
troubleshooting_guide:
  # PostgreSQL Issues
  postgresql_issues:
    connection_refused:
      symptoms: ["Connection refused", "Could not connect to server"]
      diagnosis: |
        1. Check if PostgreSQL service is running
        2. Verify port configuration
        3. Check firewall rules
        4. Review pg_hba.conf authentication settings
      solutions: |
        systemctl status postgresql
        netstat -tlnp | grep 5432
        tail -f /var/log/postgresql/postgresql.log
    
    high_cpu_usage:
      symptoms: ["CPU usage >80%", "Slow query performance"]
      diagnosis: |
        1. Identify expensive queries using pg_stat_statements
        2. Check for missing indexes
        3. Look for lock contention
        4. Review autovacuum activity
      solutions: |
        # Find expensive queries
        SELECT query, calls, total_time, mean_time 
        FROM pg_stat_statements 
        ORDER BY mean_time DESC LIMIT 10;
        
        # Check missing indexes
        SELECT schemaname, tablename, attname, n_distinct, correlation
        FROM pg_stats
        WHERE n_distinct > 100 AND correlation < 0.1;
    
    replication_lag:
      symptoms: ["Replica lag >30s", "Read queries returning stale data"]
      diagnosis: |
        1. Check network connectivity between primary and replica
        2. Review WAL shipping configuration
        3. Monitor replica apply rates
        4. Check for long-running transactions on primary
      solutions: |
        # Check replication status
        SELECT * FROM pg_stat_replication;
        
        # Check WAL lag
        SELECT pg_current_wal_lsn(), pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn();
        
        # Identify blocking transactions
        SELECT pid, usename, application_name, state, query_start, query
        FROM pg_stat_activity
        WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';

  # MongoDB Issues
  mongodb_issues:
    election_timeout:
      symptoms: ["Primary election failed", "No primary in replica set"]
      diagnosis: |
        1. Check network connectivity between replica set members
        2. Review replica set configuration
        3. Check for insufficient voting members
        4. Monitor oplog size and sync status
      solutions: |
        # Check replica set status
        rs.status()
        
        # Force election (if safe)
        rs.stepDown()
        
        # Reconfigure replica set if needed
        cfg = rs.conf()
        rs.reconfig(cfg)
    
    balancer_issues:
      symptoms: ["Uneven chunk distribution", "Migration failures"]
      diagnosis: |
        1. Check balancer status and settings
        2. Review chunk size configuration
        3. Monitor failed migrations
        4. Check shard connectivity
      solutions: |
        # Check balancer status
        sh.getBalancerState()
        sh.status()
        
        # Enable/disable balancer
        sh.setBalancerState(true)
        
        # Manual chunk migration if needed
        sh.moveChunk("db.collection", {shard_key: value}, "target_shard")

  # Redis Issues  
  redis_cluster_issues:
    cluster_down:
      symptoms: ["CLUSTERDOWN hash slot not served", "Connection timeouts"]
      diagnosis: |
        1. Check cluster node status
        2. Verify hash slot coverage
        3. Review network partitions
        4. Check master/slave relationships
      solutions: |
        # Check cluster status
        redis-cli cluster info
        redis-cli cluster nodes
        
        # Fix slot coverage
        redis-cli --cluster fix 127.0.0.1:7000
        
        # Manual failover if needed
        redis-cli -p 7001 cluster failover
    
    memory_issues:
      symptoms: ["OOM errors", "High memory usage", "Evictions"]
      diagnosis: |
        1. Check memory usage per node
        2. Review eviction policy settings
        3. Analyze key distribution
        4. Check for memory leaks
      solutions: |
        # Check memory usage
        redis-cli info memory
        
        # Analyze key patterns
        redis-cli --bigkeys
        
        # Adjust memory policy
        CONFIG SET maxmemory-policy allkeys-lru
```

### 6.2 Emergency Response Procedures

```bash
#!/bin/bash
# Emergency Response Script

EMERGENCY_TYPE=$1
SEVERITY=${2:-high}

case $EMERGENCY_TYPE in
    "database-down")
        echo "=== DATABASE DOWN EMERGENCY ==="
        
        # Attempt automatic recovery
        echo "1. Attempting automatic recovery..."
        systemctl restart postgresql
        systemctl restart mongod
        
        # Check services
        sleep 10
        if systemctl is-active postgresql && systemctl is-active mongod; then
            echo "Services recovered successfully"
            # Notify team
            curl -X POST "$SLACK_WEBHOOK" -d '{"text":"Database services recovered automatically"}'
        else
            echo "Automatic recovery failed - manual intervention required"
            # Page on-call engineer
            curl -X POST "$PAGERDUTY_WEBHOOK" -d '{"incident_key":"db-down","description":"Database down - auto recovery failed"}'
        fi
        ;;
        
    "performance-degradation")
        echo "=== PERFORMANCE DEGRADATION ==="
        
        # Identify slow queries
        echo "1. Identifying slow queries..."
        psql $PG_PRIMARY -c "
            SELECT query, calls, total_time, mean_time 
            FROM pg_stat_statements 
            WHERE mean_time > 1000 
            ORDER BY mean_time DESC 
            LIMIT 5;
        " > /tmp/slow_queries.log
        
        # Check system resources
        echo "2. Checking system resources..."
        echo "CPU Usage:" >> /tmp/performance_check.log
        top -bn1 | grep "Cpu(s)" >> /tmp/performance_check.log
        echo "Memory Usage:" >> /tmp/performance_check.log
        free -h >> /tmp/performance_check.log
        echo "Disk I/O:" >> /tmp/performance_check.log
        iostat -x 1 3 >> /tmp/performance_check.log
        
        # Send performance report
        cat /tmp/slow_queries.log /tmp/performance_check.log | \
        curl -X POST "$SLACK_WEBHOOK" -d @- 
        ;;
        
    "data-corruption")
        echo "=== DATA CORRUPTION EMERGENCY ==="
        
        # Stop writes immediately
        echo "1. Stopping write operations..."
        # Implementation depends on application architecture
        
        # Assess corruption extent
        echo "2. Assessing corruption extent..."
        
        # Initiate recovery procedure
        echo "3. Initiating recovery from backup..."
        # This would call the PITR script
        
        ;;
esac
```

This comprehensive runbook provides the essential operational procedures for managing the TradingAgents-CN database infrastructure effectively. Regular review and updates of these procedures ensure optimal system performance and reliability.