"""API Performance Optimizer

Optimizes API performance through async processing, request batching,
connection pooling, and intelligent load balancing.
"""

import asyncio
import aiohttp
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import queue
import json
import weakref

try:
    from fastapi import FastAPI, BackgroundTasks, Request, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware  
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .cache_optimizer import get_cache_optimizer
from .model_optimizer import get_model_optimizer
from ..utils.logging_init import get_logger

logger = get_logger("api_optimizer")


@dataclass
class APIMetrics:
    """API performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = float('inf')
    max_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    active_connections: int = 0
    peak_connections: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass 
class BatchRequest:
    """Batch request container"""
    request_id: str
    endpoint: str
    data: Any
    headers: Dict = field(default_factory=dict)
    callback: Optional[Callable] = None
    timestamp: float = field(default_factory=time.time)
    future: Optional[asyncio.Future] = None


class RequestBatcher:
    """Intelligent request batching system"""
    
    def __init__(self, max_batch_size: int = 50, batch_timeout_ms: int = 100):
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self.pending_requests = {}  # endpoint -> list of requests
        self.batch_processors = {}  # endpoint -> processor function
        self.is_running = False
        self.processing_thread = None
        self._lock = threading.Lock()
        
        logger.info(f"Request batcher initialized: batch_size={max_batch_size}")
    
    def start(self):
        """Start batch processing"""
        if self.is_running:
            return
            
        self.is_running = True
        self.processing_thread = threading.Thread(target=self._batch_processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("Request batcher started")
    
    def stop(self):
        """Stop batch processing"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        logger.info("Request batcher stopped")
    
    def register_batch_processor(self, endpoint: str, processor: Callable):
        """Register batch processor for endpoint"""
        self.batch_processors[endpoint] = processor
        logger.info(f"Registered batch processor for {endpoint}")
    
    async def submit_request(self, batch_request: BatchRequest) -> Any:
        """Submit request for batching"""
        if not batch_request.future:
            batch_request.future = asyncio.get_event_loop().create_future()
        
        with self._lock:
            if batch_request.endpoint not in self.pending_requests:
                self.pending_requests[batch_request.endpoint] = []
            
            self.pending_requests[batch_request.endpoint].append(batch_request)
        
        return await batch_request.future
    
    def _batch_processing_loop(self):
        """Main batch processing loop"""
        last_process_time = {}
        
        while self.is_running:
            try:
                current_time = time.time()
                
                with self._lock:
                    endpoints_to_process = []
                    
                    for endpoint, requests in self.pending_requests.items():
                        if not requests:
                            continue
                        
                        last_time = last_process_time.get(endpoint, current_time)
                        time_since_last = (current_time - last_time) * 1000
                        
                        should_process = (
                            len(requests) >= self.max_batch_size or
                            time_since_last >= self.batch_timeout_ms
                        )
                        
                        if should_process:
                            endpoints_to_process.append(endpoint)
                
                # Process batches outside of lock
                for endpoint in endpoints_to_process:
                    self._process_endpoint_batch(endpoint)
                    last_process_time[endpoint] = current_time
                
                # Small sleep to prevent busy waiting
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
    
    def _process_endpoint_batch(self, endpoint: str):
        """Process batch for specific endpoint"""
        with self._lock:
            requests = self.pending_requests.get(endpoint, [])
            if not requests:
                return
            
            self.pending_requests[endpoint] = []
        
        if endpoint not in self.batch_processors:
            # No batch processor, handle individually
            for request in requests:
                try:
                    if request.callback:
                        result = request.callback(request.data)
                        request.future.set_result(result)
                    else:
                        request.future.set_result(None)
                except Exception as e:
                    request.future.set_exception(e)
            return
        
        # Use batch processor
        processor = self.batch_processors[endpoint]
        
        try:
            # Extract batch data
            batch_data = [req.data for req in requests]
            
            # Process batch
            results = processor(batch_data)
            
            # Distribute results
            if isinstance(results, list) and len(results) == len(requests):
                for request, result in zip(requests, results):
                    request.future.set_result(result)
            else:
                # Single result for all requests
                for request in requests:
                    request.future.set_result(results)
            
            logger.debug(f"Processed batch of {len(requests)} for {endpoint}")
            
        except Exception as e:
            logger.error(f"Batch processing error for {endpoint}: {e}")
            for request in requests:
                request.future.set_exception(e)


class ConnectionPool:
    """HTTP connection pool for external API calls"""
    
    def __init__(self, max_connections: int = 100, timeout: int = 30):
        self.max_connections = max_connections
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
        self.connector = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.connector = aiohttp.TCPConnector(
            limit=self.max_connections,
            limit_per_host=20,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            timeout=self.timeout
        )
        
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.connector:
            await self.connector.close()


class AsyncAPIOptimizer:
    """Advanced async API performance optimizer"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize components
        self.cache_optimizer = get_cache_optimizer()
        self.model_optimizer = get_model_optimizer()
        
        self.request_batcher = RequestBatcher(
            max_batch_size=self.config.get('batch_size', 50),
            batch_timeout_ms=self.config.get('batch_timeout', 100)
        )
        
        # Metrics tracking
        self.metrics = APIMetrics()
        self._metrics_lock = threading.Lock()
        
        # Rate limiting
        self.rate_limits = {}  # endpoint -> rate limit info
        self.request_counts = {}  # client_ip -> count info
        
        # Connection pooling
        self.connection_pools = {}
        
        # Background task queue
        self.background_tasks = asyncio.Queue()
        self.background_worker = None
        
        # Request/response middleware
        self.request_middleware = []
        self.response_middleware = []
        
        logger.info("Async API optimizer initialized")
    
    def create_optimized_app(self) -> Optional[FastAPI]:
        """Create optimized FastAPI application"""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPI not available")
            return None
        
        app = FastAPI(
            title="Trading Agents API",
            description="Optimized API for trading agents",
            version="1.0.0"
        )
        
        # Add middleware for optimization
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Add custom middleware
        @app.middleware("http")
        async def performance_middleware(request: Request, call_next):
            start_time = time.time()
            
            # Update connection metrics
            with self._metrics_lock:
                self.metrics.active_connections += 1
                self.metrics.peak_connections = max(
                    self.metrics.peak_connections,
                    self.metrics.active_connections
                )
            
            try:
                # Process request middleware
                for middleware in self.request_middleware:
                    request = await middleware(request)
                
                response = await call_next(request)
                
                # Process response middleware
                for middleware in self.response_middleware:
                    response = await middleware(response)
                
                # Update metrics
                response_time = (time.time() - start_time) * 1000
                
                with self._metrics_lock:
                    self.metrics.total_requests += 1
                    self.metrics.successful_requests += 1
                    self.metrics.avg_response_time_ms = (
                        (self.metrics.avg_response_time_ms * (self.metrics.total_requests - 1) + response_time) /
                        self.metrics.total_requests
                    )
                    self.metrics.min_response_time_ms = min(self.metrics.min_response_time_ms, response_time)
                    self.metrics.max_response_time_ms = max(self.metrics.max_response_time_ms, response_time)
                
                return response
                
            except Exception as e:
                with self._metrics_lock:
                    self.metrics.total_requests += 1
                    self.metrics.failed_requests += 1
                raise e
            
            finally:
                with self._metrics_lock:
                    self.metrics.active_connections -= 1
        
        # Add optimized endpoints
        self._register_optimized_endpoints(app)
        
        return app
    
    def _register_optimized_endpoints(self, app: FastAPI):
        """Register optimized API endpoints"""
        
        @app.get("/api/stocks/{symbol}/data")
        async def get_stock_data_optimized(
            symbol: str,
            start_date: str = None,
            end_date: str = None,
            use_cache: bool = True
        ):
            """Optimized stock data endpoint with caching"""
            
            # Generate cache key
            cache_key = f"stock_data:{symbol}:{start_date}:{end_date}"
            
            # Check cache first
            if use_cache:
                cached_data = await self.cache_optimizer.get_async(cache_key)
                if cached_data:
                    with self._metrics_lock:
                        self.metrics.cache_hits += 1
                    return {"data": cached_data, "cached": True}
                
                with self._metrics_lock:
                    self.metrics.cache_misses += 1
            
            # Fetch data (placeholder - integrate with actual data service)
            try:
                # This would integrate with your actual data fetching service
                data = await self._fetch_stock_data_async(symbol, start_date, end_date)
                
                # Cache the result
                if use_cache and data:
                    await self.cache_optimizer.set_async(cache_key, data, ttl=300)
                
                return {"data": data, "cached": False}
                
            except Exception as e:
                logger.error(f"Stock data fetch error: {e}")
                return {"error": str(e)}, 500
        
        @app.post("/api/models/{model_key}/predict")
        async def predict_optimized(
            model_key: str,
            data: Dict[str, Any],
            use_cache: bool = True,
            use_batch: bool = True
        ):
            """Optimized model prediction endpoint"""
            try:
                input_data = data.get("input")
                if input_data is None:
                    return {"error": "No input data provided"}, 400
                
                result = await self.model_optimizer.predict_async(
                    model_key, input_data, use_cache, use_batch
                )
                
                return {"prediction": result, "model": model_key}
                
            except Exception as e:
                logger.error(f"Prediction error: {e}")
                return {"error": str(e)}, 500
        
        @app.post("/api/batch/predict")
        async def batch_predict_optimized(data: Dict[str, Any]):
            """Batch prediction endpoint"""
            try:
                requests = data.get("requests", [])
                if not requests:
                    return {"error": "No requests provided"}, 400
                
                # Submit batch requests
                batch_requests = []
                for req in requests:
                    batch_req = BatchRequest(
                        request_id=req.get("id", ""),
                        endpoint="predict",
                        data=req
                    )
                    batch_requests.append(batch_req)
                
                # Process batch
                results = []
                for batch_req in batch_requests:
                    result = await self.request_batcher.submit_request(batch_req)
                    results.append({
                        "id": batch_req.request_id,
                        "result": result
                    })
                
                return {"results": results}
                
            except Exception as e:
                logger.error(f"Batch prediction error: {e}")
                return {"error": str(e)}, 500
        
        @app.get("/api/metrics")
        async def get_api_metrics():
            """Get API performance metrics"""
            return self.get_performance_metrics()
        
        @app.post("/api/cache/warm")
        async def warm_cache_endpoint(data: Dict[str, Any]):
            """Cache warming endpoint"""
            try:
                await self.warm_cache_predictively()
                return {"message": "Cache warming initiated"}
            except Exception as e:
                return {"error": str(e)}, 500
    
    async def _fetch_stock_data_async(self, symbol: str, start_date: str, end_date: str):
        """Async stock data fetching (placeholder)"""
        # This would integrate with your actual data fetching logic
        await asyncio.sleep(0.1)  # Simulate API call
        return {
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "prices": [100, 101, 99, 102, 104]  # Mock data
        }
    
    def add_request_middleware(self, middleware: Callable):
        """Add request middleware"""
        self.request_middleware.append(middleware)
    
    def add_response_middleware(self, middleware: Callable):
        """Add response middleware"""
        self.response_middleware.append(middleware)
    
    def set_rate_limit(self, endpoint: str, requests_per_minute: int):
        """Set rate limit for endpoint"""
        self.rate_limits[endpoint] = {
            'limit': requests_per_minute,
            'window_ms': 60000,
            'requests': {}
        }
    
    async def check_rate_limit(self, client_ip: str, endpoint: str) -> bool:
        """Check if request is within rate limit"""
        if endpoint not in self.rate_limits:
            return True
        
        rate_limit = self.rate_limits[endpoint]
        current_time = time.time() * 1000
        
        # Clean old requests
        cutoff_time = current_time - rate_limit['window_ms']
        rate_limit['requests'] = {
            ip: times for ip, times in rate_limit['requests'].items()
            if any(t > cutoff_time for t in times)
        }
        
        # Check client rate
        if client_ip not in rate_limit['requests']:
            rate_limit['requests'][client_ip] = []
        
        client_requests = rate_limit['requests'][client_ip]
        recent_requests = [t for t in client_requests if t > cutoff_time]
        
        if len(recent_requests) >= rate_limit['limit']:
            return False
        
        # Add current request
        rate_limit['requests'][client_ip] = recent_requests + [current_time]
        return True
    
    async def warm_cache_predictively(self):
        """Trigger predictive cache warming"""
        try:
            await self.cache_optimizer.warm_cache_predictively()
            logger.info("Predictive cache warming completed")
        except Exception as e:
            logger.error(f"Cache warming error: {e}")
    
    async def start_background_tasks(self):
        """Start background task processing"""
        if self.background_worker:
            return
        
        self.background_worker = asyncio.create_task(self._background_task_worker())
        self.request_batcher.start()
        
        logger.info("Background task processing started")
    
    async def stop_background_tasks(self):
        """Stop background task processing"""
        if self.background_worker:
            self.background_worker.cancel()
            try:
                await self.background_worker
            except asyncio.CancelledError:
                pass
            self.background_worker = None
        
        self.request_batcher.stop()
        
        logger.info("Background task processing stopped")
    
    async def _background_task_worker(self):
        """Background task processing worker"""
        while True:
            try:
                # Get task from queue
                task = await asyncio.wait_for(
                    self.background_tasks.get(),
                    timeout=1.0
                )
                
                # Execute task
                if callable(task):
                    if asyncio.iscoroutinefunction(task):
                        await task()
                    else:
                        task()
                
            except asyncio.TimeoutError:
                # No task available, continue
                continue
            except Exception as e:
                logger.error(f"Background task error: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive API performance metrics"""
        with self._metrics_lock:
            current_metrics = {
                'total_requests': self.metrics.total_requests,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'success_rate': (
                    self.metrics.successful_requests / 
                    max(self.metrics.total_requests, 1) * 100
                ),
                'avg_response_time_ms': self.metrics.avg_response_time_ms,
                'min_response_time_ms': self.metrics.min_response_time_ms,
                'max_response_time_ms': self.metrics.max_response_time_ms,
                'active_connections': self.metrics.active_connections,
                'peak_connections': self.metrics.peak_connections,
                'cache_hit_rate': (
                    self.metrics.cache_hits /
                    max(self.metrics.cache_hits + self.metrics.cache_misses, 1) * 100
                )
            }
        
        return {
            'api_metrics': current_metrics,
            'cache_metrics': self.cache_optimizer.get_cache_metrics(),
            'model_metrics': self.model_optimizer.get_performance_metrics(),
            'timestamp': datetime.now().isoformat()
        }
    
    async def run_server(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        workers: int = 1
    ):
        """Run optimized API server"""
        if not FASTAPI_AVAILABLE:
            logger.error("FastAPI not available for server")
            return
        
        app = self.create_optimized_app()
        if not app:
            return
        
        # Start background tasks
        await self.start_background_tasks()
        
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            workers=workers,
            loop="asyncio",
            access_log=False,  # Use our own logging
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        
        try:
            logger.info(f"Starting optimized API server on {host}:{port}")
            await server.serve()
        finally:
            await self.stop_background_tasks()


# Global API optimizer instance
_api_optimizer = None

def get_api_optimizer() -> AsyncAPIOptimizer:
    """Get global API optimizer instance"""
    global _api_optimizer
    
    if _api_optimizer is None:
        _api_optimizer = AsyncAPIOptimizer()
    
    return _api_optimizer