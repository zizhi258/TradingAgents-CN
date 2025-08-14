"""
Enhanced Redis Integration for TradingAgents-CN Production Pipeline

This module provides high-performance Redis integration with:
- Multi-tier caching strategy
- Real-time data streams
- Message queues with priority handling
- Feature store for ML models
- Rate limiting and circuit breaking
"""

import asyncio
import json
import pickle
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import aioredis
import numpy as np
from contextlib import asynccontextmanager


class CacheTier(Enum):
    """Cache tier levels for different data types"""
    L1_MEMORY = "l1_memory"      # Ultra-fast in-memory cache
    L2_REDIS = "l2_redis"        # Redis cache with TTL
    L3_PERSISTENT = "l3_persistent"  # Long-term storage in Redis


@dataclass
class CacheConfig:
    """Configuration for cache operations"""
    default_ttl: int = 3600
    max_memory_items: int = 1000
    enable_compression: bool = True
    enable_encryption: bool = False
    key_prefix: str = "ta"
    cluster_mode: bool = False


class RedisCircuitBreaker:
    """Circuit breaker for Redis operations"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            
            raise e


class EnhancedRedisManager:
    """Enhanced Redis manager with advanced features"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_config = CacheConfig(**config.get('cache_config', {}))
        self.logger = logging.getLogger("redis_manager")
        
        # Redis connection pools
        self.redis_pools = {}
        self.redis_clients = {}
        
        # Circuit breakers for different operations
        self.circuit_breakers = {
            'read': RedisCircuitBreaker(),
            'write': RedisCircuitBreaker(),
            'stream': RedisCircuitBreaker()
        }
        
        # In-memory L1 cache
        self.l1_cache = {}
        self.l1_cache_timestamps = {}
        
        # Statistics
        self.stats = {
            'operations_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'last_operation_time': None
        }
        
        # Key prefixes for different data types
        self.key_prefixes = {
            'market_data': f"{self.cache_config.key_prefix}:market:",
            'analysis': f"{self.cache_config.key_prefix}:analysis:",
            'features': f"{self.cache_config.key_prefix}:features:",
            'session': f"{self.cache_config.key_prefix}:session:",
            'queue': f"{self.cache_config.key_prefix}:queue:",
            'stream': f"{self.cache_config.key_prefix}:stream:",
            'rate_limit': f"{self.cache_config.key_prefix}:rate:",
            'config': f"{self.cache_config.key_prefix}:config:"
        }
        
        # Initialize connections
        asyncio.create_task(self._initialize_connections())
    
    async def _initialize_connections(self):
        """Initialize Redis connection pools"""
        try:
            redis_configs = self.config.get('redis_clusters', {
                'primary': self.config.get('redis_url', 'redis://localhost:6379')
            })
            
            for cluster_name, redis_url in redis_configs.items():
                # Create connection pool
                pool = aioredis.ConnectionPool.from_url(
                    redis_url,
                    max_connections=20,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                # Create Redis client
                client = aioredis.Redis(
                    connection_pool=pool,
                    decode_responses=False,  # Keep binary for pickle data
                    socket_timeout=10,
                    socket_connect_timeout=10
                )
                
                # Test connection
                await client.ping()
                
                self.redis_pools[cluster_name] = pool
                self.redis_clients[cluster_name] = client
                
                self.logger.info(f"Redis cluster '{cluster_name}' connected successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis connections: {e}")
            raise
    
    def _get_redis_client(self, cluster: str = 'primary') -> aioredis.Redis:
        """Get Redis client for specific cluster"""
        return self.redis_clients.get(cluster, self.redis_clients['primary'])
    
    async def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for Redis storage"""
        try:
            if isinstance(data, (dict, list, tuple)):
                # Use JSON for simple structures
                return json.dumps(data, default=str).encode('utf-8')
            else:
                # Use pickle for complex objects
                return pickle.dumps(data)
        except Exception as e:
            self.logger.error(f"Serialization error: {e}")
            return json.dumps({'error': 'serialization_failed'}).encode('utf-8')
    
    async def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data from Redis"""
        try:
            # Try JSON first
            try:
                return json.loads(data.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                return pickle.loads(data)
        except Exception as e:
            self.logger.error(f"Deserialization error: {e}")
            return None
    
    @asynccontextmanager
    async def _operation_context(self, operation_type: str):
        """Context manager for Redis operations with circuit breaker"""
        self.stats['operations_count'] += 1
        self.stats['last_operation_time'] = datetime.now()
        
        try:
            async with self.circuit_breakers[operation_type]:
                yield
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Redis {operation_type} operation failed: {e}")
            raise
    
    async def set_market_data(self, symbol: str, data: Dict[str, Any], 
                            ttl: int = None, cluster: str = 'primary') -> bool:
        """Cache market data with multi-tier strategy"""
        try:
            if ttl is None:
                ttl = self.cache_config.default_ttl
            
            # Store in L1 cache
            cache_key = f"market_data:{symbol}"
            self.l1_cache[cache_key] = data
            self.l1_cache_timestamps[cache_key] = time.time()
            
            # Limit L1 cache size
            if len(self.l1_cache) > self.cache_config.max_memory_items:
                oldest_key = min(self.l1_cache_timestamps.items(), key=lambda x: x[1])[0]
                del self.l1_cache[oldest_key]
                del self.l1_cache_timestamps[oldest_key]
            
            # Store in Redis L2 cache
            redis_key = f"{self.key_prefixes['market_data']}latest:{symbol}"
            redis_client = self._get_redis_client(cluster)
            
            async with self._operation_context('write'):
                if isinstance(data, dict):
                    # Use hash for structured data
                    await redis_client.hset(redis_key, mapping=data)
                else:
                    # Use string for serialized data
                    serialized_data = await self._serialize_data(data)
                    await redis_client.set(redis_key, serialized_data)
                
                await redis_client.expire(redis_key, ttl)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set market data for {symbol}: {e}")
            return False
    
    async def get_market_data(self, symbol: str, cluster: str = 'primary') -> Optional[Dict[str, Any]]:
        """Get market data from multi-tier cache"""
        try:
            # Try L1 cache first
            cache_key = f"market_data:{symbol}"
            if cache_key in self.l1_cache:
                # Check if data is still fresh (5 seconds)
                if time.time() - self.l1_cache_timestamps[cache_key] < 5:
                    self.stats['cache_hits'] += 1
                    return self.l1_cache[cache_key]
            
            # Try Redis L2 cache
            redis_key = f"{self.key_prefixes['market_data']}latest:{symbol}"
            redis_client = self._get_redis_client(cluster)
            
            async with self._operation_context('read'):
                # Try hash first
                data = await redis_client.hgetall(redis_key)
                if data:
                    # Convert bytes to appropriate types
                    result = {}
                    for k, v in data.items():
                        key = k.decode('utf-8') if isinstance(k, bytes) else k
                        try:
                            # Try to convert to float/int if possible
                            if isinstance(v, bytes):
                                v_str = v.decode('utf-8')
                                if '.' in v_str:
                                    result[key] = float(v_str)
                                elif v_str.isdigit():
                                    result[key] = int(v_str)
                                else:
                                    result[key] = v_str
                            else:
                                result[key] = v
                        except:
                            result[key] = v.decode('utf-8') if isinstance(v, bytes) else v
                    
                    # Update L1 cache
                    self.l1_cache[cache_key] = result
                    self.l1_cache_timestamps[cache_key] = time.time()
                    
                    self.stats['cache_hits'] += 1
                    return result
                
                # Try string data
                string_data = await redis_client.get(redis_key)
                if string_data:
                    result = await self._deserialize_data(string_data)
                    if result:
                        # Update L1 cache
                        self.l1_cache[cache_key] = result
                        self.l1_cache_timestamps[cache_key] = time.time()
                        
                        self.stats['cache_hits'] += 1
                        return result
            
            self.stats['cache_misses'] += 1
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get market data for {symbol}: {e}")
            return None
    
    async def cache_analysis_result(self, symbol: str, analysis_type: str,
                                  result: Dict[str, Any], ttl: int = 3600,
                                  cluster: str = 'primary') -> bool:
        """Cache analysis results with metadata"""
        try:
            cache_data = {
                'result': result,
                'cached_at': datetime.now().isoformat(),
                'analysis_type': analysis_type,
                'symbol': symbol,
                'ttl': ttl
            }
            
            redis_key = f"{self.key_prefixes['analysis']}{symbol}:{analysis_type}"
            redis_client = self._get_redis_client(cluster)
            
            async with self._operation_context('write'):
                serialized_data = await self._serialize_data(cache_data)
                await redis_client.setex(redis_key, ttl, serialized_data)
            
            self.logger.debug(f"Cached analysis result: {symbol}:{analysis_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache analysis result: {e}")
            return False
    
    async def get_cached_analysis(self, symbol: str, analysis_type: str,
                                cluster: str = 'primary') -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        try:
            redis_key = f"{self.key_prefixes['analysis']}{symbol}:{analysis_type}"
            redis_client = self._get_redis_client(cluster)
            
            async with self._operation_context('read'):
                cached_data = await redis_client.get(redis_key)
                
                if cached_data:
                    data = await self._deserialize_data(cached_data)
                    if data and 'result' in data:
                        self.stats['cache_hits'] += 1
                        return data['result']
            
            self.stats['cache_misses'] += 1
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cached analysis: {e}")
            return None
    
    async def store_ml_features(self, symbol: str, features: Dict[str, Any],
                              feature_set: str = 'default', ttl: int = 86400,
                              cluster: str = 'primary') -> bool:
        """Store ML features efficiently"""
        try:
            redis_key = f"{self.key_prefixes['features']}{symbol}:{feature_set}"
            redis_client = self._get_redis_client(cluster)
            
            # Add timestamp and metadata
            feature_data = {
                'features': features,
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'feature_set': feature_set
            }
            
            async with self._operation_context('write'):
                # Use efficient serialization for numerical data
                if all(isinstance(v, (int, float, list)) for v in features.values()):
                    # Use hash for numerical features
                    hash_data = {}
                    for k, v in features.items():
                        if isinstance(v, list):
                            hash_data[k] = json.dumps(v)
                        else:
                            hash_data[k] = str(v)
                    
                    hash_data['_timestamp'] = feature_data['timestamp']
                    hash_data['_symbol'] = symbol
                    hash_data['_feature_set'] = feature_set
                    
                    await redis_client.hset(redis_key, mapping=hash_data)
                else:
                    # Use pickle for complex features
                    serialized_data = await self._serialize_data(feature_data)
                    await redis_client.set(redis_key, serialized_data)
                
                await redis_client.expire(redis_key, ttl)
            
            self.logger.debug(f"Stored ML features: {symbol}:{feature_set}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store ML features: {e}")
            return False
    
    async def get_ml_features(self, symbol: str, feature_set: str = 'default',
                            cluster: str = 'primary') -> Optional[Dict[str, Any]]:
        """Get cached ML features"""
        try:
            redis_key = f"{self.key_prefixes['features']}{symbol}:{feature_set}"
            redis_client = self._get_redis_client(cluster)
            
            async with self._operation_context('read'):
                # Try hash first
                hash_data = await redis_client.hgetall(redis_key)
                if hash_data:
                    features = {}
                    metadata = {}
                    
                    for k, v in hash_data.items():
                        key = k.decode('utf-8') if isinstance(k, bytes) else k
                        val = v.decode('utf-8') if isinstance(v, bytes) else v
                        
                        if key.startswith('_'):
                            metadata[key[1:]] = val
                        else:
                            try:
                                if val.startswith('[') and val.endswith(']'):
                                    features[key] = json.loads(val)
                                elif '.' in val:
                                    features[key] = float(val)
                                else:
                                    features[key] = int(val)
                            except:
                                features[key] = val
                    
                    if features:
                        self.stats['cache_hits'] += 1
                        return features
                
                # Try serialized data
                serialized_data = await redis_client.get(redis_key)
                if serialized_data:
                    data = await self._deserialize_data(serialized_data)
                    if data and 'features' in data:
                        self.stats['cache_hits'] += 1
                        return data['features']
            
            self.stats['cache_misses'] += 1
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get ML features: {e}")
            return None
    
    async def enqueue_task(self, queue_name: str, task_data: Dict[str, Any],
                         priority: float = 0.0, delay: int = 0,
                         cluster: str = 'primary') -> bool:
        """Add task to priority queue with optional delay"""
        try:
            redis_client = self._get_redis_client(cluster)
            queue_key = f"{self.key_prefixes['queue']}{queue_name}"
            
            # Create task payload
            task_payload = {
                'id': f"{int(time.time() * 1000)}_{hash(json.dumps(task_data, sort_keys=True))}",
                'data': task_data,
                'priority': priority,
                'created_at': datetime.now().isoformat(),
                'execute_after': (datetime.now() + timedelta(seconds=delay)).isoformat() if delay > 0 else None
            }
            
            async with self._operation_context('write'):
                if delay > 0:
                    # Use delayed queue
                    delayed_key = f"{queue_key}:delayed"
                    execute_timestamp = time.time() + delay
                    await redis_client.zadd(
                        delayed_key,
                        {json.dumps(task_payload): execute_timestamp}
                    )
                else:
                    # Use immediate priority queue
                    await redis_client.zadd(
                        queue_key,
                        {json.dumps(task_payload): priority}
                    )
            
            self.logger.debug(f"Enqueued task in {queue_name} with priority {priority}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to enqueue task: {e}")
            return False
    
    async def dequeue_tasks(self, queue_name: str, batch_size: int = 1,
                          cluster: str = 'primary') -> List[Dict[str, Any]]:
        """Dequeue tasks from priority queue"""
        try:
            redis_client = self._get_redis_client(cluster)
            queue_key = f"{self.key_prefixes['queue']}{queue_name}"
            delayed_key = f"{queue_key}:delayed"
            
            async with self._operation_context('read'):
                # First, move ready delayed tasks to main queue
                current_time = time.time()
                delayed_tasks = await redis_client.zrangebyscore(
                    delayed_key, 0, current_time, withscores=True
                )
                
                if delayed_tasks:
                    pipe = redis_client.pipeline()
                    for task_data, score in delayed_tasks:
                        task = json.loads(task_data)
                        priority = task.get('priority', 0.0)
                        
                        # Move to main queue
                        pipe.zadd(queue_key, {task_data: priority})
                        pipe.zrem(delayed_key, task_data)
                    
                    await pipe.execute()
                
                # Get tasks from main queue (highest priority first)
                tasks = await redis_client.zrevrange(
                    queue_key, 0, batch_size - 1, withscores=True
                )
                
                if tasks:
                    # Remove from queue
                    task_data_list = [task_data for task_data, _ in tasks]
                    await redis_client.zrem(queue_key, *task_data_list)
                    
                    # Parse and return tasks
                    results = []
                    for task_data, priority in tasks:
                        try:
                            task = json.loads(task_data)
                            results.append(task)
                        except:
                            continue
                    
                    return results
            
            return []
            
        except Exception as e:
            self.logger.error(f"Failed to dequeue tasks: {e}")
            return []
    
    async def add_to_stream(self, stream_name: str, data: Dict[str, Any],
                          max_len: int = 10000, cluster: str = 'primary') -> str:
        """Add data to Redis stream"""
        try:
            redis_client = self._get_redis_client(cluster)
            stream_key = f"{self.key_prefixes['stream']}{stream_name}"
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
            
            async with self._operation_context('stream'):
                message_id = await redis_client.xadd(
                    stream_key,
                    data,
                    maxlen=max_len,
                    approximate=True
                )
            
            return message_id.decode('utf-8') if isinstance(message_id, bytes) else message_id
            
        except Exception as e:
            self.logger.error(f"Failed to add to stream {stream_name}: {e}")
            return ""
    
    async def read_from_stream(self, stream_name: str, consumer_group: str,
                             consumer_name: str, count: int = 10,
                             block: int = 1000, cluster: str = 'primary') -> List[Dict[str, Any]]:
        """Read from Redis stream with consumer group"""
        try:
            redis_client = self._get_redis_client(cluster)
            stream_key = f"{self.key_prefixes['stream']}{stream_name}"
            
            async with self._operation_context('stream'):
                # Create consumer group if it doesn't exist
                try:
                    await redis_client.xgroup_create(
                        stream_key, consumer_group, id='0', mkstream=True
                    )
                except:
                    pass  # Group already exists or other error
                
                # Read messages
                messages = await redis_client.xreadgroup(
                    consumer_group,
                    consumer_name,
                    {stream_key: '>'},
                    count=count,
                    block=block
                )
                
                results = []
                for stream, msgs in messages:
                    for msg_id, fields in msgs:
                        message_data = {
                            'id': msg_id.decode('utf-8') if isinstance(msg_id, bytes) else msg_id,
                            'stream': stream.decode('utf-8') if isinstance(stream, bytes) else stream,
                            'data': {}
                        }
                        
                        # Decode field data
                        for k, v in fields.items():
                            key = k.decode('utf-8') if isinstance(k, bytes) else k
                            val = v.decode('utf-8') if isinstance(v, bytes) else v
                            message_data['data'][key] = val
                        
                        results.append(message_data)
                
                return results
            
        except Exception as e:
            self.logger.error(f"Failed to read from stream {stream_name}: {e}")
            return []
    
    async def ack_stream_message(self, stream_name: str, consumer_group: str,
                               message_id: str, cluster: str = 'primary') -> bool:
        """Acknowledge stream message"""
        try:
            redis_client = self._get_redis_client(cluster)
            stream_key = f"{self.key_prefixes['stream']}{stream_name}"
            
            async with self._operation_context('stream'):
                result = await redis_client.xack(stream_key, consumer_group, message_id)
                return result > 0
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge message {message_id}: {e}")
            return False
    
    async def rate_limit_check(self, identifier: str, limit: int,
                             window_seconds: int, cluster: str = 'primary') -> Tuple[bool, Dict[str, Any]]:
        """Advanced rate limiting with sliding window"""
        try:
            redis_client = self._get_redis_client(cluster)
            rate_key = f"{self.key_prefixes['rate_limit']}{identifier}"
            
            async with self._operation_context('write'):
                current_time = time.time()
                window_start = current_time - window_seconds
                
                # Remove old entries
                await redis_client.zremrangebyscore(rate_key, 0, window_start)
                
                # Count current requests
                current_count = await redis_client.zcard(rate_key)
                
                # Rate limit info
                rate_info = {
                    'allowed': current_count < limit,
                    'current_count': current_count,
                    'limit': limit,
                    'window_seconds': window_seconds,
                    'reset_time': current_time + window_seconds
                }
                
                if current_count < limit:
                    # Add current request
                    await redis_client.zadd(rate_key, {str(current_time): current_time})
                    await redis_client.expire(rate_key, window_seconds * 2)
                    return True, rate_info
                else:
                    return False, rate_info
            
        except Exception as e:
            self.logger.error(f"Rate limit check failed for {identifier}: {e}")
            return True, {'error': str(e)}  # Allow on error
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            stats = {
                'operations': self.stats.copy(),
                'l1_cache_size': len(self.l1_cache),
                'circuit_breakers': {
                    name: {
                        'state': cb.state,
                        'failure_count': cb.failure_count,
                        'last_failure': cb.last_failure_time
                    }
                    for name, cb in self.circuit_breakers.items()
                },
                'redis_clusters': {}
            }
            
            # Get Redis cluster statistics
            for cluster_name, client in self.redis_clients.items():
                try:
                    info = await client.info()
                    cluster_stats = {
                        'connected_clients': info.get('connected_clients', 0),
                        'used_memory_mb': info.get('used_memory', 0) / (1024 * 1024),
                        'total_keys': info.get('db0', {}).get('keys', 0),
                        'hit_rate': self._calculate_hit_rate(info),
                        'ops_per_sec': info.get('instantaneous_ops_per_sec', 0)
                    }
                    stats['redis_clusters'][cluster_name] = cluster_stats
                except Exception as e:
                    stats['redis_clusters'][cluster_name] = {'error': str(e)}
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get cache statistics: {e}")
            return {'error': str(e)}
    
    def _calculate_hit_rate(self, redis_info: Dict[str, Any]) -> float:
        """Calculate cache hit rate from Redis info"""
        try:
            hits = redis_info.get('keyspace_hits', 0)
            misses = redis_info.get('keyspace_misses', 0)
            total = hits + misses
            return (hits / total * 100) if total > 0 else 0.0
        except:
            return 0.0
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired cache entries and optimize memory"""
        cleanup_stats = {
            'l1_cleaned': 0,
            'redis_keys_scanned': 0,
            'redis_keys_cleaned': 0
        }
        
        try:
            # Clean L1 cache
            current_time = time.time()
            expired_keys = [
                key for key, timestamp in self.l1_cache_timestamps.items()
                if current_time - timestamp > 300  # 5 minutes
            ]
            
            for key in expired_keys:
                del self.l1_cache[key]
                del self.l1_cache_timestamps[key]
                cleanup_stats['l1_cleaned'] += 1
            
            # Clean Redis data
            for cluster_name, client in self.redis_clients.items():
                try:
                    # Get keys with our prefixes
                    for prefix in self.key_prefixes.values():
                        async for key in client.scan_iter(match=f"{prefix}*", count=1000):
                            cleanup_stats['redis_keys_scanned'] += 1
                            
                            # Check TTL and remove expired keys without TTL
                            ttl = await client.ttl(key)
                            if ttl == -1:  # No expiration set
                                # Set default expiration for keys without TTL
                                await client.expire(key, self.cache_config.default_ttl)
                                cleanup_stats['redis_keys_cleaned'] += 1
                            
                except Exception as e:
                    self.logger.error(f"Cleanup error for cluster {cluster_name}: {e}")
            
            self.logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return cleanup_stats
    
    async def close(self):
        """Close all Redis connections"""
        try:
            for cluster_name, pool in self.redis_pools.items():
                await pool.disconnect()
                self.logger.info(f"Closed Redis connection pool for {cluster_name}")
            
            self.redis_pools.clear()
            self.redis_clients.clear()
            
        except Exception as e:
            self.logger.error(f"Error closing Redis connections: {e}")


# Factory function
def create_redis_manager(config: Dict[str, Any]) -> EnhancedRedisManager:
    """Create and configure enhanced Redis manager"""
    return EnhancedRedisManager(config)


# Example usage and testing
if __name__ == "__main__":
    async def test_redis_manager():
        config = {
            'redis_url': 'redis://localhost:6379',
            'cache_config': {
                'default_ttl': 3600,
                'max_memory_items': 1000,
                'key_prefix': 'test_ta'
            }
        }
        
        redis_manager = create_redis_manager(config)
        
        # Test market data caching
        test_data = {
            'price': 150.50,
            'volume': 1000000,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store data
        success = await redis_manager.set_market_data('AAPL', test_data, ttl=300)
        print(f"Store result: {success}")
        
        # Retrieve data
        retrieved_data = await redis_manager.get_market_data('AAPL')
        print(f"Retrieved data: {retrieved_data}")
        
        # Test ML features
        features = {
            'sma_20': 148.50,
            'rsi': 65.2,
            'volume_avg': 50000000,
            'price_features': [1.0, 2.0, 3.0, 4.0, 5.0]
        }
        
        await redis_manager.store_ml_features('AAPL', features)
        retrieved_features = await redis_manager.get_ml_features('AAPL')
        print(f"Retrieved features: {retrieved_features}")
        
        # Test rate limiting
        for i in range(6):
            allowed, info = await redis_manager.rate_limit_check('test_user', 5, 60)
            print(f"Request {i+1}: Allowed={allowed}, Info={info}")
        
        # Get statistics
        stats = await redis_manager.get_cache_statistics()
        print(f"Cache statistics: {json.dumps(stats, indent=2, default=str)}")
        
        # Cleanup
        await redis_manager.close()
    
    # Run test
    asyncio.run(test_redis_manager())