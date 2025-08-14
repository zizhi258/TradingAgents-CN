"""Multi-Level Cache Optimizer

Advanced caching system with Redis L1, MongoDB L2, and File L3 caching.
Includes predictive cache warming, intelligent eviction policies, and
performance analytics.
"""

import asyncio
import hashlib
import json
import pickle
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import weakref

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

from .database_optimizer import get_pool_manager
from ..utils.logging_init import get_logger

logger = get_logger("cache_optimizer")


@dataclass
class CacheMetrics:
    """Cache performance metrics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    writes: int = 0
    read_time_ms: float = 0.0
    write_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    hit_rate: float = 0.0


class CacheKeyGenerator:
    """Intelligent cache key generation with conflict prevention"""
    
    @staticmethod
    def generate_key(
        prefix: str,
        symbol: str,
        data_type: str = "stock_data",
        start_date: str = "",
        end_date: str = "",
        parameters: Dict = None,
        version: str = "v1"
    ) -> str:
        """Generate optimized cache key"""
        key_components = [
            prefix,
            symbol.upper(),
            data_type,
            start_date,
            end_date,
            version
        ]
        
        # Add parameters hash if provided
        if parameters:
            param_hash = hashlib.md5(
                json.dumps(parameters, sort_keys=True).encode()
            ).hexdigest()[:8]
            key_components.append(param_hash)
        
        base_key = ":".join(filter(None, key_components))
        
        # Create short hash for very long keys
        if len(base_key) > 200:
            key_hash = hashlib.sha256(base_key.encode()).hexdigest()[:16]
            return f"{prefix}:{symbol}:hash:{key_hash}"
        
        return base_key
    
    @staticmethod
    def generate_pattern(prefix: str, symbol: str = "*", data_type: str = "*") -> str:
        """Generate cache key pattern for bulk operations"""
        return f"{prefix}:{symbol}:{data_type}:*"


class CacheEvictionPolicy:
    """Advanced cache eviction policies"""
    
    def __init__(self, max_memory_mb: float = 1024):
        self.max_memory_mb = max_memory_mb
        self.access_times = {}
        self.access_counts = {}
        self.cache_sizes = {}
        self._lock = threading.Lock()
    
    def record_access(self, key: str, size_bytes: int = 0):
        """Record cache key access for LRU/LFU tracking"""
        current_time = time.time()
        
        with self._lock:
            self.access_times[key] = current_time
            self.access_counts[key] = self.access_counts.get(key, 0) + 1
            if size_bytes > 0:
                self.cache_sizes[key] = size_bytes
    
    def get_eviction_candidates(
        self,
        current_memory_mb: float,
        policy: str = "lru"
    ) -> List[str]:
        """Get keys to evict based on policy"""
        if current_memory_mb < self.max_memory_mb:
            return []
        
        with self._lock:
            if policy == "lru":
                # Least Recently Used
                sorted_keys = sorted(
                    self.access_times.items(),
                    key=lambda x: x[1]
                )
            elif policy == "lfu":
                # Least Frequently Used
                sorted_keys = sorted(
                    self.access_counts.items(),
                    key=lambda x: x[1]
                )
            elif policy == "size":
                # Largest items first
                sorted_keys = sorted(
                    self.cache_sizes.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            else:
                return []
        
        # Calculate eviction candidates
        candidates = []
        memory_to_free = current_memory_mb - (self.max_memory_mb * 0.8)
        freed_memory = 0
        
        for key, _ in sorted_keys:
            candidates.append(key)
            key_size = self.cache_sizes.get(key, 1024) / (1024 * 1024)  # MB
            freed_memory += key_size
            
            if freed_memory >= memory_to_free:
                break
        
        return candidates
    
    def cleanup_tracking(self, removed_keys: List[str]):
        """Clean up tracking data for removed keys"""
        with self._lock:
            for key in removed_keys:
                self.access_times.pop(key, None)
                self.access_counts.pop(key, None)
                self.cache_sizes.pop(key, None)


class PredictiveCacheWarmer:
    """Machine learning-based cache warming system"""
    
    def __init__(self, cache_optimizer):
        self.cache_optimizer = cache_optimizer
        self.access_patterns = {}
        self.prediction_model = None
        self.training_data = []
        self.warmup_executor = ThreadPoolExecutor(max_workers=3)
        self._lock = threading.Lock()
        
        logger.info("Predictive cache warmer initialized")
    
    def record_access_pattern(
        self,
        symbol: str,
        data_type: str,
        access_time: datetime = None
    ):
        """Record access pattern for ML training"""
        access_time = access_time or datetime.now()
        
        pattern_key = f"{symbol}:{data_type}"
        
        with self._lock:
            if pattern_key not in self.access_patterns:
                self.access_patterns[pattern_key] = []
            
            self.access_patterns[pattern_key].append(access_time)
            
            # Keep only recent patterns (last 30 days)
            cutoff_time = datetime.now() - timedelta(days=30)
            self.access_patterns[pattern_key] = [
                t for t in self.access_patterns[pattern_key]
                if t > cutoff_time
            ]
    
    def train_prediction_model(self):
        """Train ML model for access pattern prediction"""
        training_features = []
        training_targets = []
        
        for pattern_key, access_times in self.access_patterns.items():
            if len(access_times) < 5:  # Need minimum data points
                continue
            
            # Create features: hour, day_of_week, is_weekend, etc.
            for i in range(len(access_times) - 1):
                current_time = access_times[i]
                next_time = access_times[i + 1]
                
                features = [
                    current_time.hour,
                    current_time.weekday(),
                    1 if current_time.weekday() >= 5 else 0,  # weekend
                    current_time.day,
                    (next_time - current_time).total_seconds() / 3600  # hours until next
                ]
                
                training_features.append(features)
                training_targets.append(1)  # Will be accessed
        
        if len(training_features) > 10:
            try:
                self.prediction_model = LinearRegression()
                self.prediction_model.fit(training_features, training_targets)
                logger.info(f"Trained prediction model with {len(training_features)} samples")
            except Exception as e:
                logger.error(f"Failed to train prediction model: {e}")
    
    def predict_cache_needs(self, hours_ahead: int = 2) -> List[Tuple[str, str, float]]:
        """Predict which cache entries will be needed"""
        if not self.prediction_model:
            return []
        
        predictions = []
        current_time = datetime.now()
        future_time = current_time + timedelta(hours=hours_ahead)
        
        for pattern_key in self.access_patterns:
            symbol, data_type = pattern_key.split(":", 1)
            
            # Create prediction features
            features = [[
                future_time.hour,
                future_time.weekday(),
                1 if future_time.weekday() >= 5 else 0,
                future_time.day,
                hours_ahead
            ]]
            
            try:
                probability = self.prediction_model.predict(features)[0]
                if probability > 0.5:  # Threshold for warming
                    predictions.append((symbol, data_type, probability))
            except Exception as e:
                logger.debug(f"Prediction error for {pattern_key}: {e}")
        
        # Sort by probability
        predictions.sort(key=lambda x: x[2], reverse=True)
        return predictions[:20]  # Top 20 predictions
    
    async def warm_predicted_data(self, data_fetcher: Callable = None):
        """Warm cache with predicted data needs"""
        if not data_fetcher:
            return
        
        predictions = self.predict_cache_needs()
        if not predictions:
            logger.info("No cache warming predictions available")
            return
        
        warmed_count = 0
        
        for symbol, data_type, probability in predictions:
            try:
                # Check if already cached
                cache_key = CacheKeyGenerator.generate_key(
                    "warmup", symbol, data_type
                )
                
                if await self.cache_optimizer.get_async(cache_key):
                    continue  # Already cached
                
                # Fetch and cache data
                data = await data_fetcher(symbol, data_type)
                if data is not None:
                    await self.cache_optimizer.set_async(
                        cache_key, data, ttl=3600
                    )
                    warmed_count += 1
                    
                    logger.info(
                        f"Warmed cache for {symbol}:{data_type} "
                        f"(probability: {probability:.2f})"
                    )
                
            except Exception as e:
                logger.error(f"Cache warming error for {symbol}:{data_type}: {e}")
        
        logger.info(f"Cache warming completed: {warmed_count} entries warmed")


class MultiLevelCacheOptimizer:
    """Advanced multi-level caching system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.pool_manager = get_pool_manager()
        
        # Cache level configurations
        self.l1_redis_config = {
            'default_ttl': self.config.get('l1_ttl', 300),  # 5 minutes
            'max_memory_mb': self.config.get('l1_max_memory', 512),
        }
        
        self.l2_mongodb_config = {
            'default_ttl': self.config.get('l2_ttl', 3600),  # 1 hour
            'collection': self.config.get('l2_collection', 'cache_l2'),
        }
        
        self.l3_file_config = {
            'default_ttl': self.config.get('l3_ttl', 86400),  # 24 hours
            'cache_dir': Path(self.config.get('l3_cache_dir', 'data/cache/l3')),
        }
        
        # Initialize file cache directory
        self.l3_file_config['cache_dir'].mkdir(parents=True, exist_ok=True)
        
        # Cache metrics
        self.metrics = {
            'l1_redis': CacheMetrics(),
            'l2_mongodb': CacheMetrics(),
            'l3_file': CacheMetrics()
        }
        
        # Eviction policy
        self.eviction_policy = CacheEvictionPolicy(
            self.l1_redis_config['max_memory_mb']
        )
        
        # Predictive warming
        self.cache_warmer = PredictiveCacheWarmer(self)
        
        # Thread safety
        self._locks = {
            'l1': threading.Lock(),
            'l2': threading.Lock(),
            'l3': threading.Lock()
        }
        
        logger.info("Multi-level cache optimizer initialized")
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data for caching"""
        if isinstance(data, pd.DataFrame):
            return data.to_json().encode('utf-8')
        elif isinstance(data, np.ndarray):
            return pickle.dumps(data)
        elif isinstance(data, (dict, list, str, int, float)):
            return json.dumps(data).encode('utf-8')
        else:
            return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes, data_type: str = None) -> Any:
        """Deserialize cached data"""
        try:
            if data_type == 'dataframe':
                return pd.read_json(data.decode('utf-8'))
            elif data_type == 'json':
                return json.loads(data.decode('utf-8'))
            else:
                return pickle.loads(data)
        except:
            # Fallback to pickle
            return pickle.loads(data)
    
    async def get_async(self, key: str) -> Optional[Any]:
        """Async get with multi-level fallback"""
        start_time = time.time()
        
        # L1: Redis cache
        result = await self._get_l1_redis(key)
        if result is not None:
            self.metrics['l1_redis'].hits += 1
            self.metrics['l1_redis'].read_time_ms = (time.time() - start_time) * 1000
            self.eviction_policy.record_access(key)
            return result
        
        self.metrics['l1_redis'].misses += 1
        
        # L2: MongoDB cache
        result = await self._get_l2_mongodb(key)
        if result is not None:
            self.metrics['l2_mongodb'].hits += 1
            self.metrics['l2_mongodb'].read_time_ms = (time.time() - start_time) * 1000
            
            # Promote to L1
            await self._set_l1_redis(key, result, self.l1_redis_config['default_ttl'])
            return result
        
        self.metrics['l2_mongodb'].misses += 1
        
        # L3: File cache
        result = await self._get_l3_file(key)
        if result is not None:
            self.metrics['l3_file'].hits += 1
            self.metrics['l3_file'].read_time_ms = (time.time() - start_time) * 1000
            
            # Promote to L1 and L2
            await self._set_l1_redis(key, result, self.l1_redis_config['default_ttl'])
            await self._set_l2_mongodb(key, result, self.l2_mongodb_config['default_ttl'])
            return result
        
        self.metrics['l3_file'].misses += 1
        return None
    
    async def set_async(
        self,
        key: str,
        value: Any,
        ttl: int = None,
        levels: List[str] = None
    ) -> bool:
        """Async set to specified cache levels"""
        if levels is None:
            levels = ['l1', 'l2', 'l3']
        
        success = True
        
        if 'l1' in levels:
            success &= await self._set_l1_redis(
                key, value, ttl or self.l1_redis_config['default_ttl']
            )
        
        if 'l2' in levels:
            success &= await self._set_l2_mongodb(
                key, value, ttl or self.l2_mongodb_config['default_ttl']
            )
        
        if 'l3' in levels:
            success &= await self._set_l3_file(
                key, value, ttl or self.l3_file_config['default_ttl']
            )
        
        return success
    
    async def _get_l1_redis(self, key: str) -> Optional[Any]:
        """Get from Redis L1 cache"""
        client = self.pool_manager.get_redis_client()
        if not client:
            return None
        
        try:
            with self._locks['l1']:
                data = client.get(key)
                if data:
                    return self._deserialize_data(data)
        except Exception as e:
            logger.error(f"Redis L1 get error: {e}")
        
        return None
    
    async def _set_l1_redis(self, key: str, value: Any, ttl: int) -> bool:
        """Set to Redis L1 cache"""
        client = self.pool_manager.get_redis_client()
        if not client:
            return False
        
        try:
            serialized_data = self._serialize_data(value)
            
            with self._locks['l1']:
                client.setex(key, ttl, serialized_data)
                self.metrics['l1_redis'].writes += 1
                self.eviction_policy.record_access(key, len(serialized_data))
            
            return True
            
        except Exception as e:
            logger.error(f"Redis L1 set error: {e}")
            return False
    
    async def _get_l2_mongodb(self, key: str) -> Optional[Any]:
        """Get from MongoDB L2 cache"""
        client = self.pool_manager.get_mongo_client()
        if not client:
            return None
        
        try:
            with self._locks['l2']:
                db = client.tradingagents
                collection = db[self.l2_mongodb_config['collection']]
                
                doc = collection.find_one({
                    '_id': key,
                    'expires_at': {'$gt': datetime.now()}
                })
                
                if doc:
                    data_type = doc.get('data_type', 'pickle')
                    return self._deserialize_data(doc['data'], data_type)
                    
        except Exception as e:
            logger.error(f"MongoDB L2 get error: {e}")
        
        return None
    
    async def _set_l2_mongodb(self, key: str, value: Any, ttl: int) -> bool:
        """Set to MongoDB L2 cache"""
        client = self.pool_manager.get_mongo_client()
        if not client:
            return False
        
        try:
            serialized_data = self._serialize_data(value)
            data_type = 'dataframe' if isinstance(value, pd.DataFrame) else 'pickle'
            
            doc = {
                '_id': key,
                'data': serialized_data,
                'data_type': data_type,
                'created_at': datetime.now(),
                'expires_at': datetime.now() + timedelta(seconds=ttl),
                'size_bytes': len(serialized_data)
            }
            
            with self._locks['l2']:
                db = client.tradingagents
                collection = db[self.l2_mongodb_config['collection']]
                collection.replace_one({'_id': key}, doc, upsert=True)
                self.metrics['l2_mongodb'].writes += 1
            
            return True
            
        except Exception as e:
            logger.error(f"MongoDB L2 set error: {e}")
            return False
    
    async def _get_l3_file(self, key: str) -> Optional[Any]:
        """Get from file L3 cache"""
        try:
            file_path = self.l3_file_config['cache_dir'] / f"{key}.pkl"
            
            if not file_path.exists():
                return None
            
            # Check TTL
            file_age = time.time() - file_path.stat().st_mtime
            if file_age > self.l3_file_config['default_ttl']:
                file_path.unlink()  # Remove expired file
                return None
            
            with self._locks['l3']:
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
                    
        except Exception as e:
            logger.error(f"File L3 get error: {e}")
            return None
    
    async def _set_l3_file(self, key: str, value: Any, ttl: int) -> bool:
        """Set to file L3 cache"""
        try:
            file_path = self.l3_file_config['cache_dir'] / f"{key}.pkl"
            
            with self._locks['l3']:
                with open(file_path, 'wb') as f:
                    pickle.dump(value, f)
                self.metrics['l3_file'].writes += 1
            
            return True
            
        except Exception as e:
            logger.error(f"File L3 set error: {e}")
            return False
    
    def evict_cache_entries(self, level: str = 'l1', policy: str = 'lru') -> int:
        """Evict cache entries based on policy"""
        evicted_count = 0
        
        if level == 'l1':
            # Redis eviction
            client = self.pool_manager.get_redis_client()
            if client:
                try:
                    info = client.info('memory')
                    current_memory_mb = info['used_memory'] / (1024 * 1024)
                    
                    candidates = self.eviction_policy.get_eviction_candidates(
                        current_memory_mb, policy
                    )
                    
                    for key in candidates:
                        try:
                            client.delete(key)
                            evicted_count += 1
                        except:
                            pass
                    
                    self.eviction_policy.cleanup_tracking(candidates)
                    self.metrics['l1_redis'].evictions += evicted_count
                    
                except Exception as e:
                    logger.error(f"Redis eviction error: {e}")
        
        elif level == 'l3':
            # File cache cleanup
            try:
                cache_dir = self.l3_file_config['cache_dir']
                current_time = time.time()
                
                for file_path in cache_dir.glob("*.pkl"):
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > self.l3_file_config['default_ttl']:
                        file_path.unlink()
                        evicted_count += 1
                
                self.metrics['l3_file'].evictions += evicted_count
                
            except Exception as e:
                logger.error(f"File cache cleanup error: {e}")
        
        logger.info(f"Evicted {evicted_count} entries from {level} cache")
        return evicted_count
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Get comprehensive cache metrics"""
        metrics_summary = {}
        
        for level, metrics in self.metrics.items():
            total_operations = metrics.hits + metrics.misses
            hit_rate = metrics.hits / max(total_operations, 1) * 100
            
            metrics_summary[level] = {
                'hits': metrics.hits,
                'misses': metrics.misses,
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': metrics.evictions,
                'writes': metrics.writes,
                'avg_read_time_ms': metrics.read_time_ms,
                'avg_write_time_ms': metrics.write_time_ms,
            }
        
        return {
            'levels': metrics_summary,
            'pool_stats': self.pool_manager.get_pool_stats(),
            'timestamp': datetime.now().isoformat()
        }
    
    async def warm_cache_predictively(self, data_fetcher: Callable = None):
        """Trigger predictive cache warming"""
        await self.cache_warmer.warm_predicted_data(data_fetcher)
    
    def train_warming_model(self):
        """Train the cache warming ML model"""
        self.cache_warmer.train_prediction_model()


# Global cache optimizer instance
_cache_optimizer = None

def get_cache_optimizer() -> MultiLevelCacheOptimizer:
    """Get global cache optimizer instance"""
    global _cache_optimizer
    
    if _cache_optimizer is None:
        _cache_optimizer = MultiLevelCacheOptimizer()
    
    return _cache_optimizer