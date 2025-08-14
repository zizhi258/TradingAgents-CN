"""Database Performance Optimizer

Optimizes MongoDB and Redis performance through connection pooling,
query optimization, indexing strategies, and intelligent failover.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from concurrent.futures import ThreadPoolExecutor
import threading
from contextlib import contextmanager
import weakref

import pymongo
import redis
from pymongo import MongoClient
from redis.connection import ConnectionPool
from redis.retry import Retry
from redis.backoff import ExponentialBackoff

from ..config.database_manager import get_database_manager
from ..utils.logging_init import get_logger

logger = get_logger("database_optimizer")


class ConnectionPoolManager:
    """Advanced connection pool manager for MongoDB and Redis"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.mongo_pools = {}
        self.redis_pools = {}
        self.pool_stats = {
            'mongo': {'connections': 0, 'active': 0, 'peak': 0},
            'redis': {'connections': 0, 'active': 0, 'peak': 0}
        }
        self._lock = threading.Lock()
        self.db_manager = get_database_manager()
        
        # Pool configuration
        self.mongo_pool_config = {
            'maxPoolSize': self.config.get('mongo_max_pool_size', 50),
            'minPoolSize': self.config.get('mongo_min_pool_size', 5),
            'maxIdleTimeMS': self.config.get('mongo_idle_timeout', 30000),
            'waitQueueTimeoutMS': self.config.get('mongo_queue_timeout', 5000),
            'serverSelectionTimeoutMS': self.config.get('mongo_server_timeout', 3000),
        }
        
        self.redis_pool_config = {
            'max_connections': self.config.get('redis_max_connections', 50),
            'retry_on_timeout': True,
            'retry': Retry(ExponentialBackoff(), 3),
            'socket_keepalive': True,
            'socket_keepalive_options': {},
            'health_check_interval': 30,
        }
        
        logger.info("Connection pool manager initialized")
    
    def get_mongo_client(self, database: str = None) -> Optional[MongoClient]:
        """Get optimized MongoDB client with connection pooling"""
        if not self.db_manager.is_mongodb_available():
            return None
            
        db_key = database or 'default'
        
        with self._lock:
            if db_key not in self.mongo_pools:
                try:
                    mongo_config = self.db_manager.mongodb_config.copy()
                    mongo_config.update(self.mongo_pool_config)
                    
                    # Build connection string with pool settings
                    connect_kwargs = {
                        'host': mongo_config['host'],
                        'port': mongo_config['port'],
                        **self.mongo_pool_config
                    }
                    
                    if mongo_config.get('username') and mongo_config.get('password'):
                        connect_kwargs.update({
                            'username': mongo_config['username'],
                            'password': mongo_config['password'],
                            'authSource': mongo_config.get('auth_source', 'admin')
                        })
                    
                    client = MongoClient(**connect_kwargs)
                    self.mongo_pools[db_key] = client
                    self.pool_stats['mongo']['connections'] += 1
                    
                    logger.info(f"MongoDB connection pool created for {db_key}")
                    
                except Exception as e:
                    logger.error(f"Failed to create MongoDB pool: {e}")
                    return None
            
            return self.mongo_pools.get(db_key)
    
    def get_redis_client(self, db: int = None) -> Optional[redis.Redis]:
        """Get optimized Redis client with connection pooling"""
        if not self.db_manager.is_redis_available():
            return None
            
        db_key = db if db is not None else self.db_manager.redis_config.get('db', 0)
        
        with self._lock:
            if db_key not in self.redis_pools:
                try:
                    redis_config = self.db_manager.redis_config.copy()
                    
                    # Create connection pool
                    pool = ConnectionPool(
                        host=redis_config['host'],
                        port=redis_config['port'],
                        db=db_key,
                        password=redis_config.get('password'),
                        **self.redis_pool_config
                    )
                    
                    client = redis.Redis(connection_pool=pool)
                    self.redis_pools[db_key] = client
                    self.pool_stats['redis']['connections'] += 1
                    
                    logger.info(f"Redis connection pool created for db {db_key}")
                    
                except Exception as e:
                    logger.error(f"Failed to create Redis pool: {e}")
                    return None
            
            return self.redis_pools.get(db_key)
    
    @contextmanager
    def mongo_session(self, database: str = None):
        """Context manager for MongoDB sessions with automatic cleanup"""
        client = self.get_mongo_client(database)
        if not client:
            yield None
            return
            
        session = None
        try:
            session = client.start_session()
            self.pool_stats['mongo']['active'] += 1
            self.pool_stats['mongo']['peak'] = max(
                self.pool_stats['mongo']['peak'],
                self.pool_stats['mongo']['active']
            )
            yield session
        finally:
            if session:
                session.end_session()
                self.pool_stats['mongo']['active'] -= 1
    
    @contextmanager 
    def redis_pipeline(self, db: int = None):
        """Context manager for Redis pipeline operations"""
        client = self.get_redis_client(db)
        if not client:
            yield None
            return
            
        pipeline = None
        try:
            pipeline = client.pipeline()
            self.pool_stats['redis']['active'] += 1
            self.pool_stats['redis']['peak'] = max(
                self.pool_stats['redis']['peak'],
                self.pool_stats['redis']['active']
            )
            yield pipeline
        finally:
            if pipeline:
                self.pool_stats['redis']['active'] -= 1
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all connection pools"""
        health_status = {
            'mongo': {'healthy': False, 'latency': None, 'error': None},
            'redis': {'healthy': False, 'latency': None, 'error': None}
        }
        
        # MongoDB health check
        if self.db_manager.is_mongodb_available():
            try:
                start_time = time.time()
                client = self.get_mongo_client()
                if client:
                    client.admin.command('ping')
                    latency = (time.time() - start_time) * 1000
                    health_status['mongo'] = {
                        'healthy': True, 
                        'latency': f"{latency:.2f}ms",
                        'error': None
                    }
            except Exception as e:
                health_status['mongo']['error'] = str(e)
        
        # Redis health check
        if self.db_manager.is_redis_available():
            try:
                start_time = time.time()
                client = self.get_redis_client()
                if client:
                    client.ping()
                    latency = (time.time() - start_time) * 1000
                    health_status['redis'] = {
                        'healthy': True,
                        'latency': f"{latency:.2f}ms", 
                        'error': None
                    }
            except Exception as e:
                health_status['redis']['error'] = str(e)
        
        return health_status
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get detailed pool statistics"""
        return {
            'pools': self.pool_stats.copy(),
            'mongo_pools': len(self.mongo_pools),
            'redis_pools': len(self.redis_pools),
            'timestamp': datetime.now().isoformat()
        }
    
    def close_all_pools(self):
        """Close all connection pools and cleanup resources"""
        logger.info("Closing all connection pools")
        
        # Close MongoDB pools
        for db_key, client in self.mongo_pools.items():
            try:
                client.close()
                logger.info(f"Closed MongoDB pool for {db_key}")
            except Exception as e:
                logger.error(f"Error closing MongoDB pool {db_key}: {e}")
        
        # Close Redis pools
        for db_key, client in self.redis_pools.items():
            try:
                client.connection_pool.disconnect()
                logger.info(f"Closed Redis pool for db {db_key}")
            except Exception as e:
                logger.error(f"Error closing Redis pool {db_key}: {e}")
        
        self.mongo_pools.clear()
        self.redis_pools.clear()


class DatabaseOptimizer:
    """Advanced database performance optimizer"""
    
    def __init__(self, pool_manager: ConnectionPoolManager = None):
        self.pool_manager = pool_manager or ConnectionPoolManager()
        self.query_cache = {}
        self.query_stats = {}
        self._cache_lock = threading.Lock()
        
        # Query optimization settings
        self.cache_ttl = 300  # 5 minutes default
        self.slow_query_threshold = 1.0  # 1 second
        self.batch_size = 100
        
        logger.info("Database optimizer initialized")
    
    def optimize_mongodb_indexes(self, database: str = 'tradingagents'):
        """Create optimized indexes for MongoDB collections with advanced strategies"""
        client = self.pool_manager.get_mongo_client(database)
        if not client:
            logger.warning("MongoDB not available for index optimization")
            return
        
        db = client[database]
        
        # Advanced index optimization strategies
        index_strategies = {
            'stock_data': [
                # Compound indexes for time-series queries
                [('symbol', 1), ('date', -1)],
                [('date', -1), ('symbol', 1)],
                [('symbol', 1), ('data_source', 1), ('date', -1)],
                # Partial indexes for recent data (last 30 days)
                [('updated_at', -1)],
                [('volume', -1)],  # High volume queries
                # Text index for symbol search
                [('symbol', 'text')],
                # Sparse indexes for optional fields
                [('market_cap', 1)],
                [('pe_ratio', 1)],
            ],
            'cache': [
                [('_id', 1)],  # Primary key optimization
                [('expires_at', 1)],  # TTL index
                [('timestamp', -1)],  # Recent data queries
                [('metadata.symbol', 1), ('metadata.data_type', 1)],
                [('size_bytes', -1)],  # Cache size queries
                [('hit_count', -1)],  # Popular cache entries
            ],
            'analysis_results': [
                [('symbol', 1), ('analysis_type', 1), ('timestamp', -1)],
                [('timestamp', -1)],  # Time-based queries
                [('status', 1), ('timestamp', -1)],
                [('confidence_score', -1)],  # High confidence results
                [('processing_time_ms', 1)],  # Performance analysis
            ],
            'market_data': [
                [('symbol', 1), ('market', 1), ('timestamp', -1)],
                [('timestamp', -1)],
                [('price', 1), ('volume', -1)],  # Price-volume queries
                [('market_session', 1), ('timestamp', -1)],
            ],
            'user_sessions': [
                [('user_id', 1), ('created_at', -1)],
                [('expires_at', 1)],  # Session cleanup
                [('last_activity', -1)],  # Active sessions
            ],
            'performance_metrics': [
                [('service_name', 1), ('timestamp', -1)],
                [('timestamp', -1)],
                [('metric_type', 1), ('value', -1)],
            ]
        }
        
        for collection_name, indexes in index_strategies.items():
            try:
                collection = db[collection_name]
                
                # Create indexes with advanced options
                for index_spec in indexes:
                    try:
                        # Handle different index types
                        if isinstance(index_spec[0], tuple) and index_spec[0][1] == 'text':
                            # Text index
                            collection.create_index(
                                index_spec,
                                background=True,
                                name=f"text_{collection_name}_{index_spec[0][0]}"
                            )
                            logger.info(f"Created text index on {collection_name}.{index_spec[0][0]}")
                            continue
                        
                        # Regular compound index
                        index_name = f"opt_{'_'.join([f'{k}_{v}' for k, v in index_spec])}"
                        
                        # Add partial filter for recent data on stock_data
                        partial_filter = None
                        if collection_name == 'stock_data' and 'updated_at' in [k for k, v in index_spec]:
                            # Only index recent data (last 90 days)
                            recent_date = datetime.now() - timedelta(days=90)
                            partial_filter = {'updated_at': {'$gte': recent_date}}
                        
                        collection.create_index(
                            index_spec,
                            background=True,
                            name=index_name,
                            partialFilterExpression=partial_filter
                        )
                        logger.info(f"Created index {index_name} on {collection_name}")
                        
                    except pymongo.errors.OperationFailure as e:
                        if "already exists" not in str(e):
                            logger.warning(f"Failed to create index on {collection_name}: {e}")
                
                # Create specialized TTL indexes
                if collection_name == 'cache':
                    try:
                        collection.create_index(
                            "expires_at",
                            expireAfterSeconds=0,
                            background=True,
                            name="ttl_cache_expires"
                        )
                        logger.info("Created TTL index on cache collection")
                    except pymongo.errors.OperationFailure:
                        pass
                
                if collection_name == 'user_sessions':
                    try:
                        collection.create_index(
                            "expires_at",
                            expireAfterSeconds=0,
                            background=True,
                            name="ttl_session_expires"
                        )
                        logger.info("Created TTL index on user_sessions")
                    except pymongo.errors.OperationFailure:
                        pass
                        
            except Exception as e:
                logger.error(f"Error optimizing indexes for {collection_name}: {e}")
    
    async def batch_insert_mongodb(
        self, 
        collection_name: str, 
        documents: List[Dict],
        database: str = 'tradingagents'
    ) -> int:
        """Optimized batch insert for MongoDB"""
        if not documents:
            return 0
            
        client = self.pool_manager.get_mongo_client(database)
        if not client:
            return 0
        
        db = client[database]
        collection = db[collection_name]
        
        inserted_count = 0
        
        # Process in batches to avoid memory issues
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            
            try:
                result = collection.insert_many(
                    batch,
                    ordered=False,  # Continue on errors
                    bypass_document_validation=False
                )
                inserted_count += len(result.inserted_ids)
                
            except pymongo.errors.BulkWriteError as e:
                # Count successful inserts even with some failures
                inserted_count += e.details['nInserted']
                logger.warning(f"Bulk insert partial failure: {e.details}")
            
            except Exception as e:
                logger.error(f"Batch insert error: {e}")
        
        logger.info(f"Batch inserted {inserted_count}/{len(documents)} documents to {collection_name}")
        return inserted_count
    
    def batch_set_redis(
        self,
        data: Dict[str, Any],
        ttl: int = None,
        db: int = None
    ) -> int:
        """Optimized batch set for Redis"""
        if not data:
            return 0
            
        client = self.pool_manager.get_redis_client(db)
        if not client:
            return 0
        
        set_count = 0
        
        try:
            with self.pool_manager.redis_pipeline(db) as pipe:
                if not pipe:
                    return 0
                
                for key, value in data.items():
                    if ttl:
                        pipe.setex(key, ttl, value)
                    else:
                        pipe.set(key, value)
                    set_count += 1
                
                pipe.execute()
                logger.info(f"Batch set {set_count} keys to Redis")
                
        except Exception as e:
            logger.error(f"Batch Redis set error: {e}")
            set_count = 0
        
        return set_count
    
    def execute_optimized_query(
        self,
        query_func: callable,
        cache_key: str = None,
        ttl: int = None
    ) -> Any:
        """Execute database query with caching and performance monitoring"""
        if cache_key and cache_key in self.query_cache:
            cached_result, cache_time = self.query_cache[cache_key]
            if time.time() - cache_time < (ttl or self.cache_ttl):
                return cached_result
        
        # Execute query with timing
        start_time = time.time()
        
        try:
            result = query_func()
            execution_time = time.time() - start_time
            
            # Track query performance
            if cache_key:
                self.query_stats[cache_key] = {
                    'execution_time': execution_time,
                    'timestamp': datetime.now(),
                    'slow_query': execution_time > self.slow_query_threshold
                }
            
            # Cache result if specified
            if cache_key and result is not None:
                with self._cache_lock:
                    self.query_cache[cache_key] = (result, time.time())
            
            if execution_time > self.slow_query_threshold:
                logger.warning(f"Slow query detected: {cache_key} took {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Query execution error for {cache_key}: {e}")
            return None
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query performance statistics"""
        if not self.query_stats:
            return {'message': 'No query statistics available'}
        
        slow_queries = [
            key for key, stats in self.query_stats.items() 
            if stats.get('slow_query', False)
        ]
        
        avg_execution_time = sum(
            stats['execution_time'] for stats in self.query_stats.values()
        ) / len(self.query_stats)
        
        # Calculate percentiles
        execution_times = [stats['execution_time'] for stats in self.query_stats.values()]
        execution_times.sort()
        
        def percentile(data, p):
            if not data:
                return 0
            index = int(len(data) * p / 100)
            return data[min(index, len(data) - 1)]
        
        p95_time = percentile(execution_times, 95)
        p99_time = percentile(execution_times, 99)
        
        # Recent query performance (last hour)
        recent_cutoff = datetime.now() - timedelta(hours=1)
        recent_queries = [
            stats for stats in self.query_stats.values()
            if stats['timestamp'] > recent_cutoff
        ]
        
        return {
            'total_queries': len(self.query_stats),
            'slow_queries': len(slow_queries),
            'slow_query_list': slow_queries[:10],  # Top 10 slow queries
            'average_execution_time': avg_execution_time,
            'p95_execution_time': p95_time,
            'p99_execution_time': p99_time,
            'recent_queries_count': len(recent_queries),
            'recent_avg_time': sum(s['execution_time'] for s in recent_queries) / max(len(recent_queries), 1),
            'cache_hit_ratio': len(self.query_cache) / max(len(self.query_stats), 1),
            'pool_stats': self.pool_manager.get_pool_stats(),
            'query_types': self._analyze_query_types()
        }
    
    def _analyze_query_types(self) -> Dict[str, Any]:
        """Analyze query patterns by type"""
        query_types = {}
        
        for query_key, stats in self.query_stats.items():
            # Extract query type from key pattern
            parts = query_key.split(':')
            query_type = parts[0] if parts else 'unknown'
            
            if query_type not in query_types:
                query_types[query_type] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'slow_count': 0
                }
            
            query_types[query_type]['count'] += 1
            query_types[query_type]['total_time'] += stats['execution_time']
            if stats.get('slow_query', False):
                query_types[query_type]['slow_count'] += 1
        
        # Calculate averages
        for query_type, data in query_types.items():
            data['avg_time'] = data['total_time'] / data['count']
        
        return query_types
    
    def cleanup_query_cache(self, max_age: int = 3600):
        """Clean up old cached queries with intelligent eviction"""
        current_time = time.time()
        
        with self._cache_lock:
            # Find expired entries
            expired_keys = [
                key for key, (_, cache_time) in self.query_cache.items()
                if current_time - cache_time > max_age
            ]
            
            # Also evict if cache is too large (keep most recent)
            if len(self.query_cache) > 1000:  # Max cache size
                # Sort by access time and keep most recent 800
                sorted_entries = sorted(
                    self.query_cache.items(),
                    key=lambda x: x[1][1],  # Sort by cache_time
                    reverse=True
                )
                
                keys_to_keep = {entry[0] for entry in sorted_entries[:800]}
                additional_expired = [
                    key for key in self.query_cache.keys()
                    if key not in keys_to_keep and key not in expired_keys
                ]
                expired_keys.extend(additional_expired)
            
            # Remove expired entries
            for key in expired_keys:
                del self.query_cache[key]
        
        logger.info(f"Cleaned up {len(expired_keys)} expired/excess query cache entries")
        return len(expired_keys)
    
    def analyze_index_usage(self, database: str = 'tradingagents') -> Dict[str, Any]:
        """Analyze MongoDB index usage for optimization"""
        client = self.pool_manager.get_mongo_client(database)
        if not client:
            return {'error': 'MongoDB not available'}
        
        db = client[database]
        index_stats = {}
        
        try:
            # Get collection list
            collections = db.list_collection_names()
            
            for collection_name in collections:
                collection = db[collection_name]
                
                # Get index stats
                try:
                    stats = list(collection.aggregate([
                        {'$indexStats': {}}
                    ]))
                    
                    collection_stats = []
                    for stat in stats:
                        collection_stats.append({
                            'name': stat.get('name'),
                            'accesses': stat.get('accesses', {}),
                            'spec': stat.get('spec', {})
                        })
                    
                    index_stats[collection_name] = collection_stats
                    
                except Exception as e:
                    logger.warning(f"Could not get index stats for {collection_name}: {e}")
            
            return {
                'collections': len(collections),
                'index_usage': index_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Index analysis error: {e}")
            return {'error': str(e)}
    
    def create_query_plan_cache(self, database: str = 'tradingagents'):
        """Create optimized query plan cache for frequent queries"""
        client = self.pool_manager.get_mongo_client(database)
        if not client:
            return
        
        db = client[database]
        
        # Common query patterns to optimize
        common_queries = [
            {
                'collection': 'stock_data',
                'query': {'symbol': 1, 'date': {'$gte': datetime.now() - timedelta(days=30)}},
                'sort': [('date', -1)]
            },
            {
                'collection': 'analysis_results',
                'query': {'status': 'completed', 'timestamp': {'$gte': datetime.now() - timedelta(hours=24)}},
                'sort': [('timestamp', -1)]
            },
            {
                'collection': 'market_data',
                'query': {'market_session': 'regular', 'timestamp': {'$gte': datetime.now() - timedelta(hours=1)}},
                'sort': [('timestamp', -1)]
            }
        ]
        
        plan_cache_count = 0
        
        for query_spec in common_queries:
            try:
                collection = db[query_spec['collection']]
                
                # Execute query to warm up plan cache
                cursor = collection.find(query_spec['query'])
                if 'sort' in query_spec:
                    cursor = cursor.sort(query_spec['sort'])
                
                # Limit to small result set for plan caching
                list(cursor.limit(1))
                plan_cache_count += 1
                
                logger.debug(f"Warmed query plan for {query_spec['collection']}")
                
            except Exception as e:
                logger.warning(f"Query plan warming error for {query_spec['collection']}: {e}")
        
        logger.info(f"Warmed {plan_cache_count} query plans")


class QueryOptimizationScheduler:
    """Automated query optimization scheduler"""
    
    def __init__(self, database_optimizer: DatabaseOptimizer):
        self.database_optimizer = database_optimizer
        self.is_running = False
        self.scheduler_thread = None
        self.optimization_interval = 3600  # 1 hour
        
    def start(self):
        """Start automated optimization scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._optimization_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Query optimization scheduler started")
    
    def stop(self):
        """Stop optimization scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        logger.info("Query optimization scheduler stopped")
    
    def _optimization_loop(self):
        """Main optimization loop"""
        while self.is_running:
            try:
                # Run optimizations
                self.database_optimizer.optimize_mongodb_indexes()
                self.database_optimizer.create_query_plan_cache()
                self.database_optimizer.cleanup_query_cache()
                
                # Analyze performance
                stats = self.database_optimizer.get_query_statistics()
                slow_query_count = stats.get('slow_queries', 0)
                
                if slow_query_count > 10:
                    logger.warning(f"High number of slow queries detected: {slow_query_count}")
                    # Could trigger additional optimizations here
                
                # Sleep until next optimization cycle
                time.sleep(self.optimization_interval)
                
            except Exception as e:
                logger.error(f"Optimization scheduler error: {e}")
                time.sleep(60)  # Short sleep on error


# Global optimizer instances
_database_optimizer = None
_pool_manager = None
_optimization_scheduler = None

def get_database_optimizer() -> DatabaseOptimizer:
    """Get global database optimizer instance"""
    global _database_optimizer, _pool_manager, _optimization_scheduler
    
    if _database_optimizer is None:
        _pool_manager = ConnectionPoolManager()
        _database_optimizer = DatabaseOptimizer(_pool_manager)
        _optimization_scheduler = QueryOptimizationScheduler(_database_optimizer)
    
    return _database_optimizer

def get_pool_manager() -> ConnectionPoolManager:
    """Get global connection pool manager instance"""
    global _pool_manager
    
    if _pool_manager is None:
        _pool_manager = ConnectionPoolManager()
    
    return _pool_manager

def get_optimization_scheduler() -> QueryOptimizationScheduler:
    """Get global optimization scheduler instance"""
    global _optimization_scheduler, _database_optimizer
    
    if _optimization_scheduler is None:
        if _database_optimizer is None:
            get_database_optimizer()  # Initialize all components
        else:
            _optimization_scheduler = QueryOptimizationScheduler(_database_optimizer)
    
    return _optimization_scheduler