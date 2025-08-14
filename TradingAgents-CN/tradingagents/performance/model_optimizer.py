"""ML Model Serving Optimizer

Optimizes machine learning model serving through model caching,
batch inference, async processing, and GPU utilization optimization.
"""

import asyncio
import json
import pickle
import time
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import weakref

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator

try:
    import torch
    import torch.nn as nn
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False

try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

from .cache_optimizer import get_cache_optimizer
from ..ml.models import BaseModel, ModelConfig
from ..utils.logging_init import get_logger

logger = get_logger("model_optimizer")


@dataclass
class ModelPerformanceMetrics:
    """Model serving performance metrics"""
    inference_count: int = 0
    batch_inference_count: int = 0
    total_inference_time_ms: float = 0.0
    avg_inference_time_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    memory_usage_mb: float = 0.0
    gpu_usage_percent: float = 0.0
    error_count: int = 0


class ModelCache:
    """Intelligent model caching system"""
    
    def __init__(self, max_models: int = 10, max_memory_mb: float = 2048):
        self.max_models = max_models
        self.max_memory_mb = max_memory_mb
        self.models = {}
        self.access_times = {}
        self.model_sizes = {}
        self.load_times = {}
        self._lock = threading.Lock()
        
        logger.info(f"Model cache initialized: max_models={max_models}, max_memory={max_memory_mb}MB")
    
    def get_model(self, model_key: str) -> Optional[Any]:
        """Get cached model with LRU tracking"""
        with self._lock:
            if model_key in self.models:
                self.access_times[model_key] = time.time()
                return self.models[model_key]
        return None
    
    def cache_model(self, model_key: str, model: Any, size_mb: float = None):
        """Cache model with intelligent eviction"""
        current_time = time.time()
        
        with self._lock:
            # Calculate model size if not provided
            if size_mb is None:
                try:
                    if hasattr(model, 'state_dict'):  # PyTorch model
                        size_mb = sum(p.numel() * 4 for p in model.parameters()) / (1024 * 1024)  # Assume float32
                    else:
                        # Estimate size for sklearn models
                        size_mb = 10  # Default estimate
                except:
                    size_mb = 10
            
            # Check if eviction needed
            current_memory = sum(self.model_sizes.values())
            
            while (len(self.models) >= self.max_models or 
                   current_memory + size_mb > self.max_memory_mb):
                
                if not self.models:
                    break
                
                # Find LRU model
                lru_key = min(self.access_times, key=self.access_times.get)
                self._evict_model(lru_key)
                current_memory = sum(self.model_sizes.values())
            
            # Cache the model
            self.models[model_key] = model
            self.access_times[model_key] = current_time
            self.model_sizes[model_key] = size_mb
            
            logger.info(f"Cached model {model_key}: {size_mb:.1f}MB")
    
    def _evict_model(self, model_key: str):
        """Evict model from cache"""
        if model_key in self.models:
            size_mb = self.model_sizes.get(model_key, 0)
            
            del self.models[model_key]
            self.access_times.pop(model_key, None)
            self.model_sizes.pop(model_key, None)
            self.load_times.pop(model_key, None)
            
            logger.info(f"Evicted model {model_key}: {size_mb:.1f}MB freed")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'cached_models': len(self.models),
                'max_models': self.max_models,
                'memory_usage_mb': sum(self.model_sizes.values()),
                'max_memory_mb': self.max_memory_mb,
                'model_keys': list(self.models.keys()),
                'average_model_size_mb': np.mean(list(self.model_sizes.values())) if self.model_sizes else 0
            }


class BatchInferenceEngine:
    """High-performance batch inference engine"""
    
    def __init__(self, max_batch_size: int = 64, batch_timeout_ms: int = 100):
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.pending_requests = queue.Queue()
        self.batch_processor = None
        self.processing_thread = None
        self.is_running = False
        self._start_batch_processor()
        
        logger.info(f"Batch inference engine initialized: batch_size={max_batch_size}")
    
    def _start_batch_processor(self):
        """Start batch processing thread"""
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._batch_processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _batch_processing_loop(self):
        """Main batch processing loop"""
        batch_requests = []
        last_batch_time = time.time()
        
        while self.is_running:
            try:
                # Collect requests for batching
                timeout = self.batch_timeout_ms / 1000.0
                
                try:
                    request = self.pending_requests.get(timeout=timeout)
                    batch_requests.append(request)
                except queue.Empty:
                    pass
                
                current_time = time.time()
                
                # Process batch if conditions met
                should_process = (
                    len(batch_requests) >= self.max_batch_size or
                    (batch_requests and 
                     (current_time - last_batch_time) * 1000 >= self.batch_timeout_ms)
                )
                
                if should_process and batch_requests:
                    self._process_batch(batch_requests)
                    batch_requests = []
                    last_batch_time = current_time
                
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                # Clear problematic requests
                for request in batch_requests:
                    try:
                        request['future'].set_exception(e)
                    except:
                        pass
                batch_requests = []
    
    def _process_batch(self, batch_requests: List[Dict]):
        """Process a batch of inference requests"""
        if not batch_requests:
            return
        
        try:
            # Group by model
            model_groups = {}
            for request in batch_requests:
                model_key = request['model_key']
                if model_key not in model_groups:
                    model_groups[model_key] = []
                model_groups[model_key].append(request)
            
            # Process each model group
            for model_key, requests in model_groups.items():
                self._process_model_batch(model_key, requests)
                
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # Set exception for all requests
            for request in batch_requests:
                try:
                    request['future'].set_exception(e)
                except:
                    pass
    
    def _process_model_batch(self, model_key: str, requests: List[Dict]):
        """Process batch for a specific model"""
        try:
            # Extract model and data
            model = requests[0]['model']
            input_data = [req['input_data'] for req in requests]
            
            # Stack inputs for batch processing
            if isinstance(input_data[0], np.ndarray):
                batch_input = np.vstack(input_data)
            else:
                batch_input = input_data
            
            # Perform batch inference
            start_time = time.time()
            
            if hasattr(model, 'predict_batch'):
                batch_output = model.predict_batch(batch_input)
            else:
                batch_output = model.predict(batch_input)
            
            inference_time = time.time() - start_time
            
            # Distribute results
            if isinstance(batch_output, np.ndarray) and len(batch_output.shape) > 1:
                # Multiple outputs
                for i, request in enumerate(requests):
                    request['future'].set_result(batch_output[i])
            else:
                # Single output or list of outputs
                for i, request in enumerate(requests):
                    result = batch_output[i] if hasattr(batch_output, '__getitem__') else batch_output
                    request['future'].set_result(result)
            
            logger.debug(f"Processed batch of {len(requests)} for {model_key} in {inference_time*1000:.1f}ms")
            
        except Exception as e:
            logger.error(f"Model batch processing error for {model_key}: {e}")
            for request in requests:
                try:
                    request['future'].set_exception(e)
                except:
                    pass
    
    async def infer_async(self, model_key: str, model: Any, input_data: Any) -> Any:
        """Submit async inference request"""
        future = asyncio.get_event_loop().create_future()
        
        request = {
            'model_key': model_key,
            'model': model,
            'input_data': input_data,
            'future': future,
            'timestamp': time.time()
        }
        
        self.pending_requests.put(request)
        return await future
    
    def stop(self):
        """Stop batch processing"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)


class ModelServingOptimizer:
    """Advanced model serving optimization system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize components
        self.model_cache = ModelCache(
            max_models=self.config.get('max_cached_models', 10),
            max_memory_mb=self.config.get('cache_memory_limit_mb', 2048)
        )
        
        self.batch_engine = BatchInferenceEngine(
            max_batch_size=self.config.get('max_batch_size', 64),
            batch_timeout_ms=self.config.get('batch_timeout_ms', 100)
        )
        
        self.cache_optimizer = get_cache_optimizer()
        
        # Performance tracking
        self.metrics = ModelPerformanceMetrics()
        self._metrics_lock = threading.Lock()
        
        # Async executor for non-batch operations
        self.async_executor = ThreadPoolExecutor(
            max_workers=self.config.get('async_workers', 4)
        )
        
        # Model registry
        self.model_registry = {}
        self.model_metadata = {}
        
        logger.info("Model serving optimizer initialized")
    
    def register_model(
        self,
        model_key: str,
        model_path: str,
        model_type: str,
        config: Dict = None,
        preload: bool = False
    ):
        """Register a model for serving"""
        self.model_registry[model_key] = {
            'path': model_path,
            'type': model_type,
            'config': config or {},
            'registered_at': datetime.now(),
            'access_count': 0
        }
        
        if preload:
            self._load_model(model_key)
        
        logger.info(f"Registered model {model_key} from {model_path}")
    
    def _load_model(self, model_key: str) -> Optional[Any]:
        """Load model with caching"""
        # Check cache first
        cached_model = self.model_cache.get_model(model_key)
        if cached_model:
            return cached_model
        
        # Check if model is registered
        if model_key not in self.model_registry:
            logger.error(f"Model {model_key} not registered")
            return None
        
        model_info = self.model_registry[model_key]
        
        try:
            start_time = time.time()
            
            # Load model based on type
            if model_info['type'] == 'joblib':
                if not JOBLIB_AVAILABLE:
                    raise ImportError("joblib not available")
                model = joblib.load(model_info['path'])
                
            elif model_info['type'] == 'pytorch':
                if not PYTORCH_AVAILABLE:
                    raise ImportError("PyTorch not available")
                model = torch.load(model_info['path'])
                if hasattr(model, 'eval'):
                    model.eval()
                    
            elif model_info['type'] == 'pickle':
                with open(model_info['path'], 'rb') as f:
                    model = pickle.load(f)
                    
            else:
                raise ValueError(f"Unsupported model type: {model_info['type']}")
            
            load_time = time.time() - start_time
            
            # Cache the loaded model
            self.model_cache.cache_model(model_key, model)
            
            # Update metadata
            self.model_metadata[model_key] = {
                'load_time_ms': load_time * 1000,
                'loaded_at': datetime.now(),
                'memory_usage_mb': self._estimate_model_size(model)
            }
            
            logger.info(f"Loaded model {model_key} in {load_time*1000:.1f}ms")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model {model_key}: {e}")
            return None
    
    def _estimate_model_size(self, model: Any) -> float:
        """Estimate model memory usage in MB"""
        try:
            if PYTORCH_AVAILABLE and isinstance(model, nn.Module):
                return sum(p.numel() * 4 for p in model.parameters()) / (1024 * 1024)
            elif hasattr(model, '__sizeof__'):
                return model.__sizeof__() / (1024 * 1024)
            else:
                return 10.0  # Default estimate
        except:
            return 10.0
    
    async def predict_async(
        self,
        model_key: str,
        input_data: Any,
        use_cache: bool = True,
        use_batch: bool = True
    ) -> Any:
        """Async model prediction with optimization"""
        start_time = time.time()
        
        try:
            # Check prediction cache first
            if use_cache:
                cache_key = f"prediction:{model_key}:{hash(str(input_data))}"
                cached_result = await self.cache_optimizer.get_async(cache_key)
                if cached_result is not None:
                    with self._metrics_lock:
                        self.metrics.cache_hits += 1
                    return cached_result
                
                with self._metrics_lock:
                    self.metrics.cache_misses += 1
            
            # Load model
            model = self._load_model(model_key)
            if model is None:
                raise ValueError(f"Failed to load model {model_key}")
            
            # Perform prediction
            if use_batch:
                result = await self.batch_engine.infer_async(model_key, model, input_data)
                with self._metrics_lock:
                    self.metrics.batch_inference_count += 1
            else:
                # Direct prediction
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.async_executor,
                    model.predict,
                    input_data
                )
            
            # Cache result
            if use_cache and result is not None:
                cache_key = f"prediction:{model_key}:{hash(str(input_data))}"
                await self.cache_optimizer.set_async(
                    cache_key, result, ttl=300, levels=['l1']  # 5 min cache
                )
            
            # Update metrics
            inference_time = (time.time() - start_time) * 1000
            with self._metrics_lock:
                self.metrics.inference_count += 1
                self.metrics.total_inference_time_ms += inference_time
                self.metrics.avg_inference_time_ms = (
                    self.metrics.total_inference_time_ms / self.metrics.inference_count
                )
            
            # Update model access count
            if model_key in self.model_registry:
                self.model_registry[model_key]['access_count'] += 1
            
            return result
            
        except Exception as e:
            with self._metrics_lock:
                self.metrics.error_count += 1
            logger.error(f"Prediction error for {model_key}: {e}")
            raise
    
    def predict_batch(
        self,
        model_key: str,
        input_batch: List[Any],
        use_cache: bool = True
    ) -> List[Any]:
        """Synchronous batch prediction"""
        try:
            model = self._load_model(model_key)
            if model is None:
                raise ValueError(f"Failed to load model {model_key}")
            
            start_time = time.time()
            
            # Check cache for batch results
            cached_results = []
            uncached_indices = []
            uncached_inputs = []
            
            if use_cache:
                for i, input_data in enumerate(input_batch):
                    cache_key = f"prediction:{model_key}:{hash(str(input_data))}"
                    # Synchronous cache check for batch
                    cached_result = None  # Would need sync cache method
                    
                    if cached_result is not None:
                        cached_results.append((i, cached_result))
                    else:
                        uncached_indices.append(i)
                        uncached_inputs.append(input_data)
            else:
                uncached_indices = list(range(len(input_batch)))
                uncached_inputs = input_batch
            
            # Process uncached inputs
            if uncached_inputs:
                if isinstance(uncached_inputs[0], np.ndarray):
                    batch_input = np.vstack(uncached_inputs)
                else:
                    batch_input = uncached_inputs
                
                batch_results = model.predict(batch_input)
                
                # Cache individual results
                if use_cache:
                    for i, input_data in enumerate(uncached_inputs):
                        cache_key = f"prediction:{model_key}:{hash(str(input_data))}"
                        result = batch_results[i] if hasattr(batch_results, '__getitem__') else batch_results
                        # Would cache result here
            
            # Combine cached and uncached results
            results = [None] * len(input_batch)
            
            # Fill cached results
            for i, result in cached_results:
                results[i] = result
            
            # Fill uncached results
            for i, orig_idx in enumerate(uncached_indices):
                result = batch_results[i] if hasattr(batch_results, '__getitem__') else batch_results
                results[orig_idx] = result
            
            # Update metrics
            inference_time = (time.time() - start_time) * 1000
            with self._metrics_lock:
                self.metrics.batch_inference_count += 1
                self.metrics.total_inference_time_ms += inference_time
            
            return results
            
        except Exception as e:
            with self._metrics_lock:
                self.metrics.error_count += 1
            logger.error(f"Batch prediction error for {model_key}: {e}")
            raise
    
    def preload_models(self, model_keys: List[str] = None):
        """Preload models for faster serving"""
        if model_keys is None:
            model_keys = list(self.model_registry.keys())
        
        logger.info(f"Preloading {len(model_keys)} models")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self._load_model, key): key 
                for key in model_keys
            }
            
            for future in as_completed(futures):
                model_key = futures[future]
                try:
                    model = future.result()
                    if model:
                        logger.info(f"Preloaded model {model_key}")
                    else:
                        logger.error(f"Failed to preload model {model_key}")
                except Exception as e:
                    logger.error(f"Preload error for {model_key}: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        with self._metrics_lock:
            metrics_dict = {
                'inference_count': self.metrics.inference_count,
                'batch_inference_count': self.metrics.batch_inference_count,
                'avg_inference_time_ms': self.metrics.avg_inference_time_ms,
                'cache_hit_rate': (
                    self.metrics.cache_hits / 
                    max(self.metrics.cache_hits + self.metrics.cache_misses, 1) * 100
                ),
                'error_count': self.metrics.error_count,
                'error_rate': (
                    self.metrics.error_count / 
                    max(self.metrics.inference_count + self.metrics.error_count, 1) * 100
                )
            }
        
        return {
            'serving_metrics': metrics_dict,
            'model_cache': self.model_cache.get_cache_stats(),
            'registered_models': len(self.model_registry),
            'cache_metrics': self.cache_optimizer.get_cache_metrics(),
            'timestamp': datetime.now().isoformat()
        }
    
    def optimize_model_serving(self):
        """Run model serving optimizations"""
        logger.info("Running model serving optimizations")
        
        # Cache optimization
        self.cache_optimizer.evict_cache_entries('l1', 'lru')
        
        # Model cache optimization - evict least used models
        cache_stats = self.model_cache.get_cache_stats()
        if cache_stats['cached_models'] >= cache_stats['max_models']:
            # Force eviction of least accessed models
            access_counts = {
                key: info.get('access_count', 0)
                for key, info in self.model_registry.items()
            }
            
            # Evict models with lowest access counts
            sorted_models = sorted(access_counts.items(), key=lambda x: x[1])
            for model_key, _ in sorted_models[:2]:  # Evict bottom 2
                self.model_cache._evict_model(model_key)
        
        # Batch engine optimization
        logger.info("Model serving optimization completed")
    
    def shutdown(self):
        """Shutdown optimizer and cleanup resources"""
        logger.info("Shutting down model serving optimizer")
        
        self.batch_engine.stop()
        self.async_executor.shutdown(wait=True)
        
        logger.info("Model serving optimizer shutdown completed")


# Global optimizer instance
_model_optimizer = None

def get_model_optimizer() -> ModelServingOptimizer:
    """Get global model serving optimizer instance"""
    global _model_optimizer
    
    if _model_optimizer is None:
        _model_optimizer = ModelServingOptimizer()
    
    return _model_optimizer