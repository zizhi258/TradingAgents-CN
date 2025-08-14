"""
AI-Powered Multi-LLM Orchestrator for TradingAgents-CN

This module provides advanced LLM integration with intelligent routing, failover,
and production-ready features for financial analysis workflows.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import logging
from pathlib import Path
import threading
from collections import defaultdict, deque
import statistics

# Core TradingAgents imports
from tradingagents.core.multi_model_manager import MultiModelManager, TaskResult, CollaborationResult
from tradingagents.core.base_multi_model_adapter import TaskSpec, ModelSelection, TaskComplexity
from tradingagents.utils.logging_init import get_logger
from tradingagents.config.config_manager import ConfigManager

logger = get_logger("ai_orchestrator")


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OrchestratorStatus(Enum):
    """Orchestrator status"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class AITask:
    """AI task definition with enhanced metadata"""
    task_id: str
    agent_role: str
    task_prompt: str
    task_type: str = "general"
    priority: TaskPriority = TaskPriority.MEDIUM
    complexity_level: str = "medium"
    context: Dict[str, Any] = field(default_factory=dict)
    timeout: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    callback: Optional[Callable] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass 
class OrchestratorMetrics:
    """Performance metrics for the orchestrator"""
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    average_response_time: float = 0.0
    tasks_per_minute: float = 0.0
    current_load: int = 0
    cache_hit_rate: float = 0.0
    model_usage_stats: Dict[str, int] = field(default_factory=dict)
    error_rates: Dict[str, float] = field(default_factory=dict)
    cost_tracking: Dict[str, float] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.now)


class IntelligentCache:
    """Smart caching system with financial domain awareness"""
    
    def __init__(self, max_size: int = 10000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.hit_count = 0
        self.miss_count = 0
        self._lock = threading.RLock()
    
    def _generate_key(self, agent_role: str, prompt: str, context: Dict[str, Any]) -> str:
        """Generate cache key with financial context awareness"""
        # Include financial context in key generation
        financial_context = {
            'symbol': context.get('symbol'),
            'market': context.get('market_type'),
            'date': context.get('date', datetime.now().date().isoformat()),
            'analysis_type': context.get('analysis_type')
        }
        
        key_data = f"{agent_role}:{prompt[:200]}:{json.dumps(financial_context, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, agent_role: str, prompt: str, context: Dict[str, Any]) -> Optional[TaskResult]:
        """Get cached result if available and fresh"""
        with self._lock:
            key = self._generate_key(agent_role, prompt, context)
            
            if key not in self.cache:
                self.miss_count += 1
                return None
            
            cache_entry = self.cache[key]
            
            # Check TTL
            if time.time() - cache_entry['timestamp'] > self.ttl:
                del self.cache[key]
                del self.access_times[key]
                self.miss_count += 1
                return None
            
            # Check financial data freshness
            if self._is_stale_financial_data(context, cache_entry):
                del self.cache[key]
                del self.access_times[key]
                self.miss_count += 1
                return None
            
            self.access_times[key] = time.time()
            self.hit_count += 1
            
            logger.debug(f"Cache hit for key: {key[:16]}...")
            return cache_entry['result']
    
    def put(self, agent_role: str, prompt: str, context: Dict[str, Any], result: TaskResult):
        """Cache result with intelligent eviction"""
        with self._lock:
            key = self._generate_key(agent_role, prompt, context)
            
            # Evict old entries if cache is full
            if len(self.cache) >= self.max_size:
                self._evict_lru()
            
            self.cache[key] = {
                'result': result,
                'timestamp': time.time(),
                'context': context.copy(),
                'agent_role': agent_role
            }
            self.access_times[key] = time.time()
            
            logger.debug(f"Cached result for key: {key[:16]}...")
    
    def _is_stale_financial_data(self, current_context: Dict[str, Any], 
                                cache_entry: Dict[str, Any]) -> bool:
        """Check if financial data in cache is stale"""
        # Market data is considered stale if it's from a different trading day
        current_date = current_context.get('date')
        cached_date = cache_entry['context'].get('date')
        
        if current_date and cached_date and current_date != cached_date:
            return True
        
        # Real-time analysis requires fresh data
        if current_context.get('real_time', False):
            return True
        
        # News analysis is stale after 30 minutes
        if cache_entry['agent_role'] == 'news_hunter':
            return time.time() - cache_entry['timestamp'] > 1800
        
        return False
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[lru_key]
        del self.access_times[lru_key]
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    def clear(self):
        """Clear all cache entries"""
        with self._lock:
            self.cache.clear()
            self.access_times.clear()
            self.hit_count = 0
            self.miss_count = 0


class AIOrchestrator:
    """
    Advanced AI Orchestrator with production-ready features:
    - Intelligent routing and failover
    - Smart caching with financial context
    - Cost optimization and monitoring
    - Real-time performance metrics
    - Task prioritization and queuing
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.status = OrchestratorStatus.INITIALIZING
        
        # Initialize multi-model manager
        self.mm_manager = MultiModelManager(config)
        
        # Initialize intelligent cache
        cache_config = config.get('caching', {})
        self.cache = IntelligentCache(
            max_size=cache_config.get('max_cache_size', 10000),
            ttl=cache_config.get('ttl', 3600)
        )
        
        # Task management
        self.task_queues = {
            TaskPriority.CRITICAL: deque(),
            TaskPriority.HIGH: deque(),
            TaskPriority.MEDIUM: deque(),
            TaskPriority.LOW: deque()
        }
        self.active_tasks: Dict[str, AITask] = {}
        self.task_results: Dict[str, TaskResult] = {}
        
        # Performance tracking
        self.metrics = OrchestratorMetrics()
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.error_history = deque(maxlen=100)     # Keep last 100 errors
        
        # Concurrency control
        self.max_concurrent = config.get('performance', {}).get('concurrency', {}).get('max_concurrent_requests', 5)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Cost optimization
        self.cost_thresholds = config.get('cost_management', {}).get('limits', {})
        self.daily_cost = 0.0
        self.session_cost = 0.0
        self.cost_reset_time = datetime.now().date()
        
        # Circuit breaker pattern
        self.circuit_breaker_config = config.get('routing', {}).get('circuit_breaker', {})
        self.model_failure_counts = defaultdict(int)
        self.model_last_failure = defaultdict(datetime)
        
        self.status = OrchestratorStatus.READY
        logger.info("AI Orchestrator initialized successfully")
    
    async def execute_task(self, 
                          agent_role: str,
                          task_prompt: str,
                          task_type: str = "general",
                          priority: TaskPriority = TaskPriority.MEDIUM,
                          context: Dict[str, Any] = None,
                          use_cache: bool = True,
                          callback: Optional[Callable] = None) -> TaskResult:
        """
        Execute AI task with intelligent orchestration
        
        Args:
            agent_role: Role of the agent
            task_prompt: Task prompt/instruction
            task_type: Type of task
            priority: Task priority level
            context: Additional context
            use_cache: Whether to use caching
            callback: Optional callback function
            
        Returns:
            TaskResult: Task execution result
        """
        context = context or {}
        task_id = self._generate_task_id(agent_role, task_type)
        
        # Create AI task
        ai_task = AITask(
            task_id=task_id,
            agent_role=agent_role,
            task_prompt=task_prompt,
            task_type=task_type,
            priority=priority,
            context=context,
            callback=callback
        )
        
        try:
            # Check cache first
            if use_cache:
                cached_result = self.cache.get(agent_role, task_prompt, context)
                if cached_result:
                    logger.debug(f"Returning cached result for task: {task_id}")
                    self._update_metrics(True, 0, True)
                    return cached_result
            
            # Check cost limits
            if not self._check_cost_limits():
                raise ValueError("Cost limits exceeded")
            
            # Execute with concurrency control
            async with self.semaphore:
                result = await self._execute_with_intelligence(ai_task)
            
            # Cache successful results
            if use_cache and result.success:
                self.cache.put(agent_role, task_prompt, context, result)
            
            # Update cost tracking
            self._update_cost_tracking(result)
            
            # Execute callback if provided
            if callback:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(result)
                    else:
                        callback(result)
                except Exception as e:
                    logger.warning(f"Callback execution failed: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            error_result = TaskResult(
                result=f"Task execution failed: {str(e)}",
                model_used=None,
                execution_time=0,
                actual_cost=0.0,
                token_usage={},
                success=False,
                error_message=str(e)
            )
            
            self._update_metrics(False, 0, False)
            self.error_history.append({
                'timestamp': datetime.now(),
                'error': str(e),
                'task_id': task_id,
                'agent_role': agent_role
            })
            
            return error_result
    
    async def execute_collaborative_task(self,
                                       task_description: str,
                                       participating_agents: List[str],
                                       collaboration_mode: str = "sequential",
                                       priority: TaskPriority = TaskPriority.MEDIUM,
                                       context: Dict[str, Any] = None) -> CollaborationResult:
        """
        Execute collaborative AI task with enhanced coordination
        
        Args:
            task_description: Description of the task
            participating_agents: List of participating agents
            collaboration_mode: Mode of collaboration
            priority: Task priority level
            context: Additional context
            
        Returns:
            CollaborationResult: Collaboration result
        """
        context = context or {}
        session_id = context.get('session_id', f"collab_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        logger.info(f"Starting collaborative task: {collaboration_mode} with {len(participating_agents)} agents")
        
        try:
            # Enhanced context with orchestrator intelligence
            enhanced_context = context.copy()
            enhanced_context.update({
                'orchestrator_session_id': session_id,
                'task_priority': priority.value,
                'collaboration_enhanced': True,
                'intelligent_routing': True
            })
            
            # Execute with multi-model manager
            result = self.mm_manager.execute_collaborative_analysis(
                task_description=task_description,
                participating_agents=participating_agents,
                collaboration_mode=collaboration_mode,
                context=enhanced_context
            )
            
            # Update metrics
            self._update_collaboration_metrics(result)
            
            logger.info(f"Collaborative task completed: {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Collaborative task failed: {e}")
            return CollaborationResult(
                final_result=f"Collaborative analysis failed: {str(e)}",
                participating_models=[],
                individual_results=[],
                collaboration_metadata={
                    "error": str(e),
                    "orchestrator_enhanced": True,
                    "session_id": session_id
                },
                total_cost=0.0,
                total_time=0,
                success=False,
                error_message=str(e)
            )
    
    async def _execute_with_intelligence(self, task: AITask) -> TaskResult:
        """Execute task with intelligent routing and monitoring"""
        start_time = time.time()
        task.started_at = datetime.now()
        
        try:
            # Check circuit breaker
            selected_model = await self._intelligent_model_selection(task)
            if self._is_circuit_open(selected_model):
                # Try fallback model
                fallback_models = self._get_fallback_models(task.agent_role, task.task_type)
                for fallback_model in fallback_models:
                    if not self._is_circuit_open(fallback_model):
                        selected_model = fallback_model
                        break
                else:
                    raise ValueError("All models are circuit-broken")
            
            # Execute with selected model
            result = self.mm_manager.execute_task(
                agent_role=task.agent_role,
                task_prompt=task.task_prompt,
                task_type=task.task_type,
                complexity_level=task.complexity_level,
                context=task.context,
                model_override=selected_model if selected_model else None
            )
            
            execution_time = time.time() - start_time
            task.completed_at = datetime.now()
            
            # Update circuit breaker on success
            if result.success:
                self._record_success(selected_model)
            else:
                self._record_failure(selected_model)
            
            # Update metrics
            self._update_metrics(result.success, execution_time, False)
            self.response_times.append(execution_time)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self._record_failure(selected_model if 'selected_model' in locals() else 'unknown')
            
            # Try automatic fallback
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(f"Retrying task {task.task_id} (attempt {task.retry_count})")
                return await self._execute_with_intelligence(task)
            
            raise e
    
    async def _intelligent_model_selection(self, task: AITask) -> Optional[str]:
        """Intelligently select model based on task characteristics"""
        try:
            # Use existing model selection logic with enhancements
            selection = self.mm_manager.select_optimal_model(
                agent_role=task.agent_role,
                task_type=task.task_type,
                task_description=task.task_prompt,
                complexity_level=task.complexity_level,
                context=task.context
            )
            
            # Apply orchestrator intelligence
            if task.priority == TaskPriority.CRITICAL:
                # For critical tasks, prefer highest quality models
                quality_models = ['gemini-2.5-pro', 'deepseek-ai/DeepSeek-R1']
                for model in quality_models:
                    if not self._is_circuit_open(model):
                        return model
            
            return selection.model_spec.name if selection.model_spec else None
            
        except Exception as e:
            logger.warning(f"Model selection failed: {e}")
            return None
    
    def _generate_task_id(self, agent_role: str, task_type: str) -> str:
        """Generate unique task ID"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
        return f"{agent_role}_{task_type}_{timestamp}"
    
    def _check_cost_limits(self) -> bool:
        """Check if cost limits are exceeded"""
        # Reset daily cost if new day
        current_date = datetime.now().date()
        if current_date > self.cost_reset_time:
            self.daily_cost = 0.0
            self.cost_reset_time = current_date
        
        # Check limits
        daily_max = self.cost_thresholds.get('daily_max', 10.0)
        session_max = self.cost_thresholds.get('session_max', 1.0)
        
        if self.daily_cost >= daily_max:
            logger.warning(f"Daily cost limit exceeded: ${self.daily_cost:.2f} >= ${daily_max:.2f}")
            return False
        
        if self.session_cost >= session_max:
            logger.warning(f"Session cost limit exceeded: ${self.session_cost:.2f} >= ${session_max:.2f}")
            return False
        
        return True
    
    def _update_cost_tracking(self, result: TaskResult):
        """Update cost tracking metrics"""
        if result.actual_cost > 0:
            self.daily_cost += result.actual_cost
            self.session_cost += result.actual_cost
            
            # Track by model
            model_name = result.model_used.name if result.model_used else 'unknown'
            if model_name not in self.metrics.cost_tracking:
                self.metrics.cost_tracking[model_name] = 0.0
            self.metrics.cost_tracking[model_name] += result.actual_cost
    
    def _is_circuit_open(self, model_name: str) -> bool:
        """Check if circuit breaker is open for a model"""
        if not model_name:
            return True
        
        failure_threshold = self.circuit_breaker_config.get('failure_threshold', 5)
        recovery_timeout = self.circuit_breaker_config.get('recovery_timeout', 300)
        
        failure_count = self.model_failure_counts.get(model_name, 0)
        last_failure = self.model_last_failure.get(model_name)
        
        if failure_count >= failure_threshold:
            if last_failure and (datetime.now() - last_failure).seconds < recovery_timeout:
                return True
            else:
                # Reset circuit breaker after recovery timeout
                self.model_failure_counts[model_name] = 0
                return False
        
        return False
    
    def _record_success(self, model_name: str):
        """Record successful model execution"""
        if model_name:
            self.model_failure_counts[model_name] = 0
    
    def _record_failure(self, model_name: str):
        """Record failed model execution"""
        if model_name:
            self.model_failure_counts[model_name] += 1
            self.model_last_failure[model_name] = datetime.now()
    
    def _get_fallback_models(self, agent_role: str, task_type: str) -> List[str]:
        """Get fallback models for agent and task"""
        # Use configuration-based fallback chains
        agent_config = self.config.get('agent_bindings', {}).get(agent_role, {})
        fallback_chain = agent_config.get('fallback_chain', [])
        
        if fallback_chain:
            return fallback_chain
        
        # Default fallback models
        return ['gemini-2.5-pro', 'deepseek-ai/DeepSeek-V3', 'zai-org/GLM-4.5']
    
    def _update_metrics(self, success: bool, execution_time: float, cache_hit: bool):
        """Update performance metrics"""
        self.metrics.total_tasks += 1
        
        if success:
            self.metrics.successful_tasks += 1
        else:
            self.metrics.failed_tasks += 1
        
        # Update average response time
        if self.response_times:
            self.metrics.average_response_time = statistics.mean(self.response_times)
        
        # Update tasks per minute
        current_time = time.time()
        recent_tasks = [t for t in self.response_times if current_time - t < 60]
        self.metrics.tasks_per_minute = len(recent_tasks)
        
        # Update cache hit rate
        self.metrics.cache_hit_rate = self.cache.hit_rate
        
        self.metrics.last_updated = datetime.now()
    
    def _update_collaboration_metrics(self, result: CollaborationResult):
        """Update metrics for collaborative tasks"""
        if result.success:
            self.metrics.successful_tasks += 1
        else:
            self.metrics.failed_tasks += 1
        
        # Track model usage in collaboration
        for model in result.participating_models:
            if model not in self.metrics.model_usage_stats:
                self.metrics.model_usage_stats[model] = 0
            self.metrics.model_usage_stats[model] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current orchestrator metrics"""
        return {
            'performance': {
                'total_tasks': self.metrics.total_tasks,
                'successful_tasks': self.metrics.successful_tasks,
                'failed_tasks': self.metrics.failed_tasks,
                'success_rate': self.metrics.successful_tasks / max(1, self.metrics.total_tasks),
                'average_response_time': self.metrics.average_response_time,
                'tasks_per_minute': self.metrics.tasks_per_minute,
                'cache_hit_rate': self.metrics.cache_hit_rate
            },
            'cost': {
                'daily_cost': self.daily_cost,
                'session_cost': self.session_cost,
                'cost_by_model': dict(self.metrics.cost_tracking),
                'cost_limits': self.cost_thresholds
            },
            'models': {
                'usage_stats': dict(self.metrics.model_usage_stats),
                'failure_counts': dict(self.model_failure_counts),
                'circuit_breaker_status': {
                    model: self._is_circuit_open(model) 
                    for model in self.model_failure_counts.keys()
                }
            },
            'system': {
                'status': self.status.value,
                'active_tasks': len(self.active_tasks),
                'queue_lengths': {
                    priority.value: len(queue) 
                    for priority, queue in self.task_queues.items()
                },
                'cache_size': len(self.cache.cache),
                'last_updated': self.metrics.last_updated.isoformat()
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get orchestrator health status"""
        # Get underlying system health
        system_health = self.mm_manager.get_system_health_status()
        
        # Add orchestrator-specific health checks
        orchestrator_health = {
            'orchestrator_status': self.status.value,
            'cache_health': {
                'size': len(self.cache.cache),
                'hit_rate': self.cache.hit_rate,
                'memory_usage': 'normal'  # Could add actual memory monitoring
            },
            'cost_status': {
                'daily_usage_pct': (self.daily_cost / self.cost_thresholds.get('daily_max', 10.0)) * 100,
                'session_usage_pct': (self.session_cost / self.cost_thresholds.get('session_max', 1.0)) * 100,
                'within_limits': self._check_cost_limits()
            },
            'circuit_breaker_status': {
                'open_circuits': sum(1 for model in self.model_failure_counts.keys() 
                                   if self._is_circuit_open(model)),
                'total_models': len(self.model_failure_counts)
            }
        }
        
        # Combine health statuses
        combined_health = {
            'overall_health': system_health.get('overall_health', 'unknown'),
            'system': system_health,
            'orchestrator': orchestrator_health,
            'recommendations': self._get_health_recommendations()
        }
        
        return combined_health
    
    def _get_health_recommendations(self) -> List[str]:
        """Get health recommendations based on current status"""
        recommendations = []
        
        # Cost recommendations
        if self.daily_cost > self.cost_thresholds.get('daily_max', 10.0) * 0.8:
            recommendations.append("Daily cost approaching limit - consider optimizing model selection")
        
        # Cache recommendations
        if self.cache.hit_rate < 0.3:
            recommendations.append("Low cache hit rate - consider adjusting cache TTL or task patterns")
        
        # Circuit breaker recommendations
        open_circuits = sum(1 for model in self.model_failure_counts.keys() 
                          if self._is_circuit_open(model))
        if open_circuits > 0:
            recommendations.append(f"{open_circuits} models are circuit-broken - check model health")
        
        # Performance recommendations
        if self.metrics.average_response_time > 30:
            recommendations.append("High response times detected - consider increasing concurrency")
        
        return recommendations
    
    def reset_session_costs(self):
        """Reset session costs (useful for new analysis sessions)"""
        self.session_cost = 0.0
        logger.info("Session costs reset")
    
    def clear_cache(self):
        """Clear orchestrator cache"""
        self.cache.clear()
        logger.info("Orchestrator cache cleared")