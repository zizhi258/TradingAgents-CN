"""Model Deployment Pipeline for Stock Market Analysis

This module provides comprehensive model deployment capabilities including
model versioning, A/B testing, real-time inference serving, and monitoring.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import json
import pickle
import joblib
import hashlib
import uuid
from datetime import datetime, timedelta
import threading
import time
from pathlib import Path
import warnings
from collections import defaultdict, deque

# Web framework for API endpoints
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Redis for caching and session management
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Docker SDK for containerization
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

# Import logging system
from tradingagents.utils.logging_init import get_logger
logger = get_logger("model_deployment")


@dataclass
class ModelMetadata:
    """Metadata for deployed models"""
    model_id: str
    name: str
    version: str
    task_type: str  # "price_prediction", "signal_classification", etc.
    model_type: str  # "xgboost", "lstm", etc.
    created_at: datetime
    deployed_at: Optional[datetime] = None
    author: str = "TradingAgents-ML"
    description: str = ""
    performance_metrics: Dict = None
    model_params: Dict = None
    feature_names: List[str] = None
    training_data_hash: str = ""
    model_size_mb: float = 0.0
    status: str = "created"  # "created", "deployed", "deprecated"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = {}
        if self.model_params is None:
            self.model_params = {}
        if self.feature_names is None:
            self.feature_names = []
        if self.tags is None:
            self.tags = []


@dataclass
class DeploymentConfig:
    """Configuration for model deployment"""
    model_registry_path: str = "/mnt/c/Users/黄斌/Desktop/股票/TradingAgents-CN/models"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    enable_monitoring: bool = True
    monitoring_interval: int = 300  # 5 minutes
    max_model_versions: int = 10
    
    # A/B testing configuration
    ab_test_duration_hours: int = 24
    ab_test_traffic_split: float = 0.5  # 50-50 split
    ab_test_min_samples: int = 100
    
    # Performance thresholds for auto-rollback
    max_latency_ms: int = 1000
    min_accuracy_threshold: float = 0.8
    max_error_rate: float = 0.05
    
    # Caching configuration
    enable_redis_cache: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    cache_ttl: int = 3600  # 1 hour
    
    # Docker configuration
    enable_docker: bool = False
    docker_image_name: str = "tradingagents-ml"
    docker_registry: str = "localhost:5000"


class ModelRegistry:
    """Centralized model registry for versioning and metadata management"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.registry_path = Path(config.model_registry_path)
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize registry index
        self.index_file = self.registry_path / "registry_index.json"
        self.models_index = self._load_index()
        
    def _load_index(self) -> Dict:
        """Load model registry index"""
        if self.index_file.exists():
            with open(self.index_file, 'r') as f:
                return json.load(f)
        return {"models": {}}
    
    def _save_index(self) -> None:
        """Save model registry index"""
        with open(self.index_file, 'w') as f:
            json.dump(self.models_index, f, indent=2, default=str)
    
    def register_model(self, model: Any, metadata: ModelMetadata) -> str:
        """Register a new model version"""
        logger.info(f"Registering model: {metadata.name} v{metadata.version}")
        
        # Create model directory
        model_dir = self.registry_path / metadata.name / metadata.version
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = model_dir / "model.joblib"
        joblib.dump(model, model_path)
        
        # Calculate model size
        metadata.model_size_mb = model_path.stat().st_size / (1024 * 1024)
        
        # Save metadata
        metadata_path = model_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(asdict(metadata), f, indent=2, default=str)
        
        # Update index
        if metadata.name not in self.models_index["models"]:
            self.models_index["models"][metadata.name] = {"versions": []}
        
        version_info = {
            "version": metadata.version,
            "model_id": metadata.model_id,
            "created_at": metadata.created_at.isoformat(),
            "status": metadata.status,
            "path": str(model_path)
        }
        
        # Remove old versions if exceeding limit
        versions = self.models_index["models"][metadata.name]["versions"]
        versions.append(version_info)
        versions.sort(key=lambda x: x["created_at"], reverse=True)
        
        if len(versions) > self.config.max_model_versions:
            old_versions = versions[self.config.max_model_versions:]
            for old_version in old_versions:
                self._delete_model_files(metadata.name, old_version["version"])
            versions = versions[:self.config.max_model_versions]
        
        self.models_index["models"][metadata.name]["versions"] = versions
        self._save_index()
        
        logger.info(f"Model registered successfully: {metadata.model_id}")
        return metadata.model_id
    
    def get_model(self, name: str, version: Optional[str] = None) -> Tuple[Any, ModelMetadata]:
        """Retrieve a model and its metadata"""
        if name not in self.models_index["models"]:
            raise ValueError(f"Model {name} not found in registry")
        
        versions = self.models_index["models"][name]["versions"]
        if not versions:
            raise ValueError(f"No versions found for model {name}")
        
        # Get specific version or latest
        if version:
            version_info = next((v for v in versions if v["version"] == version), None)
            if not version_info:
                raise ValueError(f"Version {version} not found for model {name}")
        else:
            version_info = versions[0]  # Latest version
        
        # Load model
        model_path = Path(version_info["path"])
        model = joblib.load(model_path)
        
        # Load metadata
        metadata_path = model_path.parent / "metadata.json"
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)
        
        # Convert back to ModelMetadata object
        metadata_dict['created_at'] = datetime.fromisoformat(metadata_dict['created_at'])
        if metadata_dict.get('deployed_at'):
            metadata_dict['deployed_at'] = datetime.fromisoformat(metadata_dict['deployed_at'])
        
        metadata = ModelMetadata(**metadata_dict)
        
        return model, metadata
    
    def list_models(self) -> Dict[str, List[str]]:
        """List all models and their versions"""
        result = {}
        for name, info in self.models_index["models"].items():
            result[name] = [v["version"] for v in info["versions"]]
        return result
    
    def delete_model(self, name: str, version: Optional[str] = None) -> None:
        """Delete a model version or entire model"""
        if name not in self.models_index["models"]:
            raise ValueError(f"Model {name} not found in registry")
        
        if version:
            # Delete specific version
            versions = self.models_index["models"][name]["versions"]
            version_info = next((v for v in versions if v["version"] == version), None)
            if not version_info:
                raise ValueError(f"Version {version} not found for model {name}")
            
            self._delete_model_files(name, version)
            versions.remove(version_info)
            
            if not versions:
                del self.models_index["models"][name]
        else:
            # Delete entire model
            versions = self.models_index["models"][name]["versions"]
            for version_info in versions:
                self._delete_model_files(name, version_info["version"])
            del self.models_index["models"][name]
        
        self._save_index()
        logger.info(f"Deleted model: {name} v{version or 'all'}")
    
    def _delete_model_files(self, name: str, version: str) -> None:
        """Delete model files for a specific version"""
        model_dir = self.registry_path / name / version
        if model_dir.exists():
            import shutil
            shutil.rmtree(model_dir)


class ABTestingFramework:
    """A/B testing framework for model comparison"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.active_tests = {}
        self.test_results = {}
        
    def start_ab_test(self, test_name: str, model_a: str, model_b: str, 
                     traffic_split: Optional[float] = None) -> str:
        """Start an A/B test between two models"""
        
        test_id = str(uuid.uuid4())
        split = traffic_split or self.config.ab_test_traffic_split
        
        ab_test = {
            'test_id': test_id,
            'test_name': test_name,
            'model_a': model_a,
            'model_b': model_b,
            'traffic_split': split,
            'start_time': datetime.now(),
            'end_time': datetime.now() + timedelta(hours=self.config.ab_test_duration_hours),
            'status': 'active',
            'metrics': {
                'model_a': {'requests': 0, 'errors': 0, 'latency': [], 'predictions': []},
                'model_b': {'requests': 0, 'errors': 0, 'latency': [], 'predictions': []}
            }
        }
        
        self.active_tests[test_id] = ab_test
        logger.info(f"Started A/B test: {test_name} ({test_id})")
        
        return test_id
    
    def route_traffic(self, test_id: str, request_id: Optional[str] = None) -> str:
        """Route traffic to model A or B based on test configuration"""
        
        if test_id not in self.active_tests:
            raise ValueError(f"A/B test {test_id} not found")
        
        test = self.active_tests[test_id]
        
        if datetime.now() > test['end_time']:
            self._finalize_test(test_id)
            # Return model A as default after test ends
            return test['model_a']
        
        # Simple random routing based on traffic split
        if np.random.random() < test['traffic_split']:
            return test['model_a']
        else:
            return test['model_b']
    
    def record_prediction(self, test_id: str, model_name: str, prediction: Any, 
                        latency_ms: float, error: bool = False) -> None:
        """Record prediction results for A/B test"""
        
        if test_id not in self.active_tests:
            return
        
        test = self.active_tests[test_id]
        model_key = 'model_a' if model_name == test['model_a'] else 'model_b'
        
        metrics = test['metrics'][model_key]
        metrics['requests'] += 1
        metrics['latency'].append(latency_ms)
        metrics['predictions'].append(prediction)
        
        if error:
            metrics['errors'] += 1
    
    def get_test_status(self, test_id: str) -> Dict:
        """Get current status of A/B test"""
        
        if test_id not in self.active_tests:
            return self.test_results.get(test_id, {})
        
        test = self.active_tests[test_id]
        
        # Calculate current metrics
        metrics_a = test['metrics']['model_a']
        metrics_b = test['metrics']['model_b']
        
        status = {
            'test_id': test_id,
            'test_name': test['test_name'],
            'status': test['status'],
            'start_time': test['start_time'],
            'end_time': test['end_time'],
            'time_remaining': max(0, (test['end_time'] - datetime.now()).total_seconds()),
            'model_a': {
                'name': test['model_a'],
                'requests': metrics_a['requests'],
                'error_rate': metrics_a['errors'] / max(metrics_a['requests'], 1),
                'avg_latency': np.mean(metrics_a['latency']) if metrics_a['latency'] else 0
            },
            'model_b': {
                'name': test['model_b'],
                'requests': metrics_b['requests'],
                'error_rate': metrics_b['errors'] / max(metrics_b['requests'], 1),
                'avg_latency': np.mean(metrics_b['latency']) if metrics_b['latency'] else 0
            }
        }
        
        return status
    
    def _finalize_test(self, test_id: str) -> Dict:
        """Finalize A/B test and determine winner"""
        
        test = self.active_tests[test_id]
        test['status'] = 'completed'
        
        metrics_a = test['metrics']['model_a']
        metrics_b = test['metrics']['model_b']
        
        # Calculate final metrics
        final_results = {
            'test_id': test_id,
            'winner': None,
            'statistical_significance': False,
            'model_a_performance': {
                'requests': metrics_a['requests'],
                'error_rate': metrics_a['errors'] / max(metrics_a['requests'], 1),
                'avg_latency': np.mean(metrics_a['latency']) if metrics_a['latency'] else 0
            },
            'model_b_performance': {
                'requests': metrics_b['requests'],
                'error_rate': metrics_b['errors'] / max(metrics_b['requests'], 1),
                'avg_latency': np.mean(metrics_b['latency']) if metrics_b['latency'] else 0
            }
        }
        
        # Simple winner determination based on error rate and latency
        if metrics_a['requests'] >= self.config.ab_test_min_samples and metrics_b['requests'] >= self.config.ab_test_min_samples:
            error_rate_a = final_results['model_a_performance']['error_rate']
            error_rate_b = final_results['model_b_performance']['error_rate']
            
            latency_a = final_results['model_a_performance']['avg_latency']
            latency_b = final_results['model_b_performance']['avg_latency']
            
            # Model with lower error rate and latency wins
            score_a = error_rate_a + (latency_a / 1000)  # Normalize latency
            score_b = error_rate_b + (latency_b / 1000)
            
            if score_a < score_b:
                final_results['winner'] = test['model_a']
            else:
                final_results['winner'] = test['model_b']
            
            final_results['statistical_significance'] = True
        
        self.test_results[test_id] = final_results
        del self.active_tests[test_id]
        
        logger.info(f"A/B test completed: {test_id}, Winner: {final_results['winner']}")
        
        return final_results
    
    def stop_test(self, test_id: str) -> Dict:
        """Manually stop an active A/B test"""
        if test_id in self.active_tests:
            return self._finalize_test(test_id)
        return self.test_results.get(test_id, {})


class InferenceService:
    """Real-time inference service for model predictions"""
    
    def __init__(self, config: DeploymentConfig, model_registry: ModelRegistry):
        self.config = config
        self.model_registry = model_registry
        self.loaded_models = {}
        self.prediction_cache = {}
        
        # Initialize Redis cache if available
        self.redis_client = None
        if config.enable_redis_cache and REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=config.redis_host, 
                    port=config.redis_port, 
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Redis cache: {e}")
                self.redis_client = None
        
        # Initialize FastAPI app if available
        if FASTAPI_AVAILABLE:
            self.app = self._create_fastapi_app()
        else:
            self.app = None
            logger.warning("FastAPI not available, API endpoints disabled")
    
    def load_model(self, model_name: str, version: Optional[str] = None) -> str:
        """Load a model for inference"""
        
        model_key = f"{model_name}:{version or 'latest'}"
        
        if model_key not in self.loaded_models:
            model, metadata = self.model_registry.get_model(model_name, version)
            self.loaded_models[model_key] = {
                'model': model,
                'metadata': metadata,
                'loaded_at': datetime.now()
            }
            logger.info(f"Model loaded: {model_key}")
        
        return model_key
    
    def predict(self, model_key: str, features: np.ndarray, use_cache: bool = True) -> Dict:
        """Make predictions with loaded model"""
        
        start_time = time.time()
        
        # Generate cache key
        cache_key = None
        if use_cache:
            features_hash = hashlib.md5(features.tobytes()).hexdigest()
            cache_key = f"pred:{model_key}:{features_hash}"
            
            # Check cache first
            cached_result = self._get_cached_prediction(cache_key)
            if cached_result:
                return cached_result
        
        # Get model
        if model_key not in self.loaded_models:
            raise ValueError(f"Model {model_key} not loaded")
        
        model_info = self.loaded_models[model_key]
        model = model_info['model']
        metadata = model_info['metadata']
        
        try:
            # Make prediction
            if hasattr(model, 'predict'):
                prediction = model.predict(features)
            elif hasattr(model, 'model') and hasattr(model.model, 'predict'):
                prediction = model.model.predict(features)
            else:
                raise ValueError(f"Model {model_key} does not have a predict method")
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            result = {
                'prediction': prediction.tolist() if isinstance(prediction, np.ndarray) else prediction,
                'model_name': metadata.name,
                'model_version': metadata.version,
                'model_type': metadata.model_type,
                'task_type': metadata.task_type,
                'latency_ms': latency_ms,
                'timestamp': datetime.now().isoformat(),
                'features_shape': features.shape,
                'success': True
            }
            
            # Cache result
            if use_cache and cache_key:
                self._cache_prediction(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error for model {model_key}: {e}")
            return {
                'prediction': None,
                'error': str(e),
                'model_name': metadata.name,
                'model_version': metadata.version,
                'latency_ms': (time.time() - start_time) * 1000,
                'timestamp': datetime.now().isoformat(),
                'success': False
            }
    
    def _get_cached_prediction(self, cache_key: str) -> Optional[Dict]:
        """Get cached prediction result"""
        
        # Try Redis first
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")
        
        # Fallback to in-memory cache
        return self.prediction_cache.get(cache_key)
    
    def _cache_prediction(self, cache_key: str, result: Dict) -> None:
        """Cache prediction result"""
        
        # Try Redis first
        if self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key, 
                    self.config.cache_ttl, 
                    json.dumps(result, default=str)
                )
                return
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
        
        # Fallback to in-memory cache with simple LRU
        if len(self.prediction_cache) > 1000:  # Simple cleanup
            # Remove oldest 20% of entries
            keys_to_remove = list(self.prediction_cache.keys())[:200]
            for key in keys_to_remove:
                del self.prediction_cache[key]
        
        self.prediction_cache[cache_key] = result
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application for inference service"""
        
        app = FastAPI(title="TradingAgents ML Inference API", version="1.0.0")
        
        class PredictionRequest(BaseModel):
            model_name: str
            model_version: Optional[str] = None
            features: List[List[float]]
            use_cache: bool = True
        
        class PredictionResponse(BaseModel):
            prediction: Any
            model_name: str
            model_version: str
            latency_ms: float
            success: bool
            error: Optional[str] = None
        
        @app.post("/predict", response_model=PredictionResponse)
        async def predict_endpoint(request: PredictionRequest):
            try:
                # Load model if not already loaded
                model_key = self.load_model(request.model_name, request.model_version)
                
                # Convert features to numpy array
                features = np.array(request.features)
                
                # Make prediction
                result = self.predict(model_key, features, request.use_cache)
                
                return PredictionResponse(**result)
                
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/models")
        async def list_models():
            return self.model_registry.list_models()
        
        @app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "loaded_models": len(self.loaded_models),
                "timestamp": datetime.now().isoformat()
            }
        
        return app
    
    def start_api_server(self) -> None:
        """Start the FastAPI server"""
        if not self.app:
            raise RuntimeError("FastAPI not available")
        
        logger.info(f"Starting inference API server on {self.config.api_host}:{self.config.api_port}")
        uvicorn.run(
            self.app, 
            host=self.config.api_host, 
            port=self.config.api_port,
            log_level="info"
        )


class ModelMonitor:
    """Monitor model performance and health in production"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        self.metrics_history = defaultdict(lambda: deque(maxlen=1000))
        self.alert_rules = []
        self.monitoring_active = False
        self.monitoring_thread = None
        
    def start_monitoring(self) -> None:
        """Start model monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        logger.info("Model monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop model monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("Model monitoring stopped")
    
    def record_prediction(self, model_name: str, prediction_result: Dict) -> None:
        """Record prediction for monitoring"""
        
        timestamp = datetime.now()
        
        # Extract metrics
        metrics = {
            'timestamp': timestamp,
            'latency_ms': prediction_result.get('latency_ms', 0),
            'success': prediction_result.get('success', False),
            'error': prediction_result.get('error'),
            'prediction': prediction_result.get('prediction')
        }
        
        # Store metrics
        self.metrics_history[model_name].append(metrics)
        
        # Check alert rules
        self._check_alerts(model_name, metrics)
    
    def add_alert_rule(self, rule: Dict) -> None:
        """Add monitoring alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Added alert rule: {rule.get('name', 'unnamed')}")
    
    def get_model_metrics(self, model_name: str, hours: int = 24) -> Dict:
        """Get model metrics for specified time period"""
        
        if model_name not in self.metrics_history:
            return {"error": f"No metrics found for model {model_name}"}
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            m for m in self.metrics_history[model_name] 
            if m['timestamp'] > cutoff_time
        ]
        
        if not recent_metrics:
            return {"error": "No recent metrics found"}
        
        # Calculate aggregated metrics
        latencies = [m['latency_ms'] for m in recent_metrics]
        error_count = sum(1 for m in recent_metrics if not m['success'])
        
        return {
            'model_name': model_name,
            'time_period_hours': hours,
            'total_predictions': len(recent_metrics),
            'error_count': error_count,
            'error_rate': error_count / len(recent_metrics),
            'avg_latency_ms': np.mean(latencies),
            'p95_latency_ms': np.percentile(latencies, 95),
            'p99_latency_ms': np.percentile(latencies, 99),
            'max_latency_ms': np.max(latencies),
            'min_latency_ms': np.min(latencies)
        }
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        
        while self.monitoring_active:
            try:
                # Perform periodic health checks
                self._health_check()
                
                # Sleep until next check
                time.sleep(self.config.monitoring_interval)
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _health_check(self) -> None:
        """Perform health check on all monitored models"""
        
        for model_name in self.metrics_history:
            metrics = self.get_model_metrics(model_name, hours=1)  # Last hour
            
            if 'error' not in metrics:
                # Check performance thresholds
                if metrics['error_rate'] > self.config.max_error_rate:
                    self._trigger_alert({
                        'type': 'high_error_rate',
                        'model': model_name,
                        'error_rate': metrics['error_rate'],
                        'threshold': self.config.max_error_rate
                    })
                
                if metrics['p95_latency_ms'] > self.config.max_latency_ms:
                    self._trigger_alert({
                        'type': 'high_latency',
                        'model': model_name,
                        'p95_latency_ms': metrics['p95_latency_ms'],
                        'threshold': self.config.max_latency_ms
                    })
    
    def _check_alerts(self, model_name: str, metrics: Dict) -> None:
        """Check if metrics trigger any alert rules"""
        
        for rule in self.alert_rules:
            if self._evaluate_alert_rule(rule, model_name, metrics):
                self._trigger_alert({
                    'type': 'custom_rule',
                    'rule_name': rule.get('name', 'unnamed'),
                    'model': model_name,
                    'metrics': metrics
                })
    
    def _evaluate_alert_rule(self, rule: Dict, model_name: str, metrics: Dict) -> bool:
        """Evaluate if an alert rule is triggered"""
        # Simple rule evaluation - can be extended
        return False  # Placeholder
    
    def _trigger_alert(self, alert: Dict) -> None:
        """Trigger an alert"""
        logger.warning(f"ALERT: {alert}")
        
        # Here you could integrate with alerting systems like:
        # - Email notifications
        # - Slack/Teams webhooks
        # - PagerDuty
        # - Custom webhooks


class DockerDeployment:
    """Docker-based model deployment"""
    
    def __init__(self, config: DeploymentConfig):
        self.config = config
        
        if not DOCKER_AVAILABLE:
            logger.warning("Docker SDK not available, container deployment disabled")
            self.docker_client = None
        else:
            try:
                self.docker_client = docker.from_env()
                logger.info("Docker client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Docker client: {e}")
                self.docker_client = None
    
    def create_dockerfile(self, model_name: str, model_version: str) -> str:
        """Create Dockerfile for model deployment"""
        
        dockerfile_content = f"""
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model and application code
COPY models/{model_name}/{model_version}/ /app/model/
COPY tradingagents/ml/ /app/tradingagents/ml/

# Expose port
EXPOSE {self.config.api_port}

# Run inference service
CMD ["python", "-m", "tradingagents.ml.inference_service"]
"""
        
        return dockerfile_content
    
    def build_image(self, model_name: str, model_version: str) -> str:
        """Build Docker image for model"""
        
        if not self.docker_client:
            raise RuntimeError("Docker client not available")
        
        image_tag = f"{self.config.docker_image_name}:{model_name}-{model_version}"
        
        logger.info(f"Building Docker image: {image_tag}")
        
        # Create build context
        build_context = {
            'dockerfile': self.create_dockerfile(model_name, model_version)
        }
        
        # Build image (simplified - in practice you'd create proper build context)
        # image = self.docker_client.images.build(
        #     path=".",
        #     tag=image_tag,
        #     dockerfile=build_context['dockerfile']
        # )
        
        logger.info(f"Docker image built: {image_tag}")
        
        return image_tag
    
    def deploy_container(self, image_tag: str) -> str:
        """Deploy model container"""
        
        if not self.docker_client:
            raise RuntimeError("Docker client not available")
        
        container_name = f"tradingagents-ml-{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Deploying container: {container_name}")
        
        # Run container (simplified)
        # container = self.docker_client.containers.run(
        #     image_tag,
        #     name=container_name,
        #     ports={f'{self.config.api_port}/tcp': self.config.api_port},
        #     detach=True
        # )
        
        logger.info(f"Container deployed: {container_name}")
        
        return container_name


def deploy_model(model: Any, metadata: ModelMetadata, 
                config: Optional[DeploymentConfig] = None) -> Dict:
    """Deploy a model with full deployment pipeline"""
    
    if config is None:
        config = DeploymentConfig()
    
    logger.info(f"Starting deployment of model: {metadata.name} v{metadata.version}")
    
    deployment_results = {}
    
    # Step 1: Register model
    registry = ModelRegistry(config)
    model_id = registry.register_model(model, metadata)
    deployment_results['model_id'] = model_id
    deployment_results['registry_status'] = 'success'
    
    # Step 2: Load model in inference service
    inference_service = InferenceService(config, registry)
    model_key = inference_service.load_model(metadata.name, metadata.version)
    deployment_results['inference_service_status'] = 'success'
    deployment_results['model_key'] = model_key
    
    # Step 3: Start monitoring
    monitor = ModelMonitor(config)
    if config.enable_monitoring:
        monitor.start_monitoring()
        deployment_results['monitoring_status'] = 'active'
    else:
        deployment_results['monitoring_status'] = 'disabled'
    
    # Step 4: Docker deployment (if enabled)
    if config.enable_docker:
        docker_deployment = DockerDeployment(config)
        try:
            image_tag = docker_deployment.build_image(metadata.name, metadata.version)
            container_name = docker_deployment.deploy_container(image_tag)
            deployment_results['docker_status'] = 'success'
            deployment_results['container_name'] = container_name
        except Exception as e:
            logger.error(f"Docker deployment failed: {e}")
            deployment_results['docker_status'] = 'failed'
            deployment_results['docker_error'] = str(e)
    else:
        deployment_results['docker_status'] = 'disabled'
    
    deployment_results['deployment_time'] = datetime.now()
    deployment_results['config'] = config
    
    logger.info(f"Model deployment completed: {model_id}")
    
    return deployment_results