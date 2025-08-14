"""
Production API Implementation for TradingAgents-CN AI System

This module provides production-ready API endpoints with cost optimization,
monitoring, rate limiting, and comprehensive error handling for AI-powered
financial analysis services.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import threading
from collections import defaultdict, deque
import statistics
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import redis
from contextlib import asynccontextmanager

# TradingAgents imports
from tradingagents.utils.logging_init import get_logger
from tradingagents.config.config_manager import ConfigManager

logger = get_logger("production_api")


class APIErrorCode(Enum):
    """Standardized API error codes"""
    # Client errors
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INSUFFICIENT_CREDITS = "INSUFFICIENT_CREDITS"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    
    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    
    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"


class PriorityLevel(Enum):
    """API request priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    PREMIUM = "premium"


@dataclass
class APIMetrics:
    """API performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    requests_per_minute: float = 0.0
    cost_per_hour: float = 0.0
    cache_hit_rate: float = 0.0
    active_connections: int = 0
    error_rate: float = 0.0
    last_updated: datetime = None


class RequestModels:
    """Pydantic models for API requests"""
    
    class AnalysisRequest(BaseModel):
        """Base analysis request model"""
        symbol: str = Field(..., description="Stock symbol to analyze")
        analysis_type: str = Field(default="comprehensive", description="Type of analysis")
        agent_role: Optional[str] = Field(default=None, description="Specific agent role")
        priority: PriorityLevel = Field(default=PriorityLevel.NORMAL, description="Request priority")
        use_cache: bool = Field(default=True, description="Whether to use cached results")
        max_cost: Optional[float] = Field(default=None, description="Maximum cost limit")
        timeout: Optional[int] = Field(default=30, description="Request timeout in seconds")
        
        @validator('symbol')
        def validate_symbol(cls, v):
            if not v or len(v.strip()) == 0:
                raise ValueError('Symbol cannot be empty')
            return v.strip().upper()
    
    class MultiSymbolAnalysisRequest(BaseModel):
        """Multi-symbol analysis request"""
        symbols: List[str] = Field(..., description="List of symbols to analyze")
        analysis_type: str = Field(default="comprehensive", description="Type of analysis")
        coordination_mode: str = Field(default="parallel", description="Coordination mode")
        max_agents: int = Field(default=5, description="Maximum number of agents")
        priority: PriorityLevel = Field(default=PriorityLevel.NORMAL)
        use_cache: bool = Field(default=True)
        max_cost: Optional[float] = Field(default=None)
        
        @validator('symbols')
        def validate_symbols(cls, v):
            if not v or len(v) == 0:
                raise ValueError('At least one symbol is required')
            return [s.strip().upper() for s in v]
    
    class RAGQueryRequest(BaseModel):
        """RAG query request"""
        query: str = Field(..., description="Query text")
        query_type: str = Field(default="general", description="Type of query")
        symbols: Optional[List[str]] = Field(default=None, description="Related symbols")
        max_documents: int = Field(default=5, description="Maximum documents to retrieve")
        relevance_threshold: float = Field(default=0.7, description="Relevance threshold")
        
        @validator('query')
        def validate_query(cls, v):
            if not v or len(v.strip()) < 5:
                raise ValueError('Query must be at least 5 characters long')
            return v.strip()
    
    class ReportGenerationRequest(BaseModel):
        """Report generation request"""
        report_type: str = Field(..., description="Type of report")
        symbols: List[str] = Field(..., description="Symbols to include")
        template_id: Optional[str] = Field(default=None, description="Custom template ID")
        format: str = Field(default="html", description="Output format")
        priority: PriorityLevel = Field(default=PriorityLevel.NORMAL)
        
        @validator('report_type')
        def validate_report_type(cls, v):
            allowed_types = ['daily_summary', 'risk_assessment', 'market_alert', 'custom_analysis']
            if v not in allowed_types:
                raise ValueError(f'Report type must be one of: {", ".join(allowed_types)}')
            return v
    
    class AlertConditionRequest(BaseModel):
        """Alert condition creation request"""
        name: str = Field(..., description="Alert condition name")
        trigger_type: str = Field(..., description="Type of trigger")
        parameters: Dict[str, Any] = Field(..., description="Trigger parameters")
        symbols: Optional[List[str]] = Field(default=None, description="Related symbols")
        severity: str = Field(default="warning", description="Alert severity")
        enabled: bool = Field(default=True, description="Whether condition is enabled")


class ResponseModels:
    """Pydantic models for API responses"""
    
    class APIResponse(BaseModel):
        """Standard API response wrapper"""
        success: bool
        data: Optional[Any] = None
        error: Optional[Dict[str, Any]] = None
        metadata: Dict[str, Any] = Field(default_factory=dict)
        execution_time: float = 0.0
        cost: float = 0.0
        cached: bool = False
    
    class AnalysisResponse(APIResponse):
        """Analysis response"""
        analysis_result: Optional[str] = None
        confidence: float = 0.0
        model_used: Optional[str] = None
        agent_role: Optional[str] = None
        
    class RAGResponse(APIResponse):
        """RAG query response"""
        answer: Optional[str] = None
        sources: List[str] = Field(default_factory=list)
        relevance_score: float = 0.0
        documents_found: int = 0
        
    class SystemStatusResponse(APIResponse):
        """System status response"""
        status: str = "healthy"
        uptime: float = 0.0
        metrics: Dict[str, Any] = Field(default_factory=dict)
        health_checks: Dict[str, bool] = Field(default_factory=dict)


class RateLimiter:
    """Production-grade rate limiter with Redis backend"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.local_limits = defaultdict(deque)  # Fallback for non-Redis setups
        
        # Rate limiting configurations
        self.limits = {
            PriorityLevel.LOW: {'requests': 10, 'window': 60},       # 10 req/min
            PriorityLevel.NORMAL: {'requests': 30, 'window': 60},    # 30 req/min
            PriorityLevel.HIGH: {'requests': 100, 'window': 60},     # 100 req/min
            PriorityLevel.PREMIUM: {'requests': 500, 'window': 60}   # 500 req/min
        }
    
    async def check_rate_limit(self, client_id: str, priority: PriorityLevel) -> Dict[str, Any]:
        """
        Check if client has exceeded rate limit
        
        Returns:
            Dict with allowed status and metadata
        """
        try:
            limit_config = self.limits[priority]
            window_size = limit_config['window']
            max_requests = limit_config['requests']
            
            current_time = time.time()
            
            if self.redis_client:
                # Redis-based rate limiting
                key = f"rate_limit:{client_id}:{priority.value}"
                
                # Use sliding window log approach
                pipe = self.redis_client.pipeline()
                
                # Remove old entries
                pipe.zremrangebyscore(key, 0, current_time - window_size)
                
                # Count current requests
                pipe.zcard(key)
                
                # Add current request
                pipe.zadd(key, {str(current_time): current_time})
                
                # Set expiry
                pipe.expire(key, window_size + 1)
                
                results = pipe.execute()
                current_requests = results[1]
                
                # Check if limit exceeded
                if current_requests >= max_requests:
                    return {
                        'allowed': False,
                        'current_requests': current_requests,
                        'max_requests': max_requests,
                        'reset_time': current_time + window_size,
                        'retry_after': window_size
                    }
                
                return {
                    'allowed': True,
                    'current_requests': current_requests + 1,
                    'max_requests': max_requests,
                    'reset_time': current_time + window_size,
                    'remaining': max_requests - current_requests - 1
                }
                
            else:
                # Fallback to local rate limiting
                key = f"{client_id}:{priority.value}"
                request_times = self.local_limits[key]
                
                # Clean old requests
                while request_times and request_times[0] < current_time - window_size:
                    request_times.popleft()
                
                # Check limit
                if len(request_times) >= max_requests:
                    return {
                        'allowed': False,
                        'current_requests': len(request_times),
                        'max_requests': max_requests,
                        'retry_after': window_size
                    }
                
                # Add current request
                request_times.append(current_time)
                
                return {
                    'allowed': True,
                    'current_requests': len(request_times),
                    'max_requests': max_requests,
                    'remaining': max_requests - len(request_times)
                }
                
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Allow request on error (fail open)
            return {'allowed': True, 'error': str(e)}


class CostOptimizer:
    """Cost optimization and tracking system"""
    
    def __init__(self):
        self.cost_thresholds = {
            'daily_limit': 100.0,   # $100 per day
            'hourly_limit': 10.0,   # $10 per hour
            'request_limit': 1.0    # $1 per request
        }
        
        self.daily_costs = defaultdict(float)
        self.hourly_costs = defaultdict(float)
        self.cost_history = deque(maxlen=10000)
        
        # Cost reduction strategies
        self.optimization_strategies = {
            'cache_first': True,
            'model_selection': 'cost_optimized',
            'batch_processing': True,
            'smart_fallback': True
        }
    
    def estimate_cost(self, request_type: str, priority: PriorityLevel, 
                     context: Dict[str, Any]) -> float:
        """Estimate cost for a request"""
        
        base_costs = {
            'analysis': 0.10,
            'rag_query': 0.05,
            'report_generation': 0.20,
            'multi_symbol_analysis': 0.30,
            'coordinated_analysis': 0.50
        }
        
        base_cost = base_costs.get(request_type, 0.10)
        
        # Priority multiplier
        priority_multipliers = {
            PriorityLevel.LOW: 0.5,
            PriorityLevel.NORMAL: 1.0,
            PriorityLevel.HIGH: 1.5,
            PriorityLevel.PREMIUM: 2.0
        }
        
        cost_multiplier = priority_multipliers.get(priority, 1.0)
        
        # Context-based adjustments
        if context.get('use_cache', True):
            cost_multiplier *= 0.3  # Significant discount for cached results
        
        if context.get('symbols') and len(context['symbols']) > 1:
            cost_multiplier *= 1 + (len(context['symbols']) - 1) * 0.2
        
        return base_cost * cost_multiplier
    
    def check_cost_limits(self, client_id: str, estimated_cost: float) -> Dict[str, Any]:
        """Check if request would exceed cost limits"""
        
        current_time = datetime.now()
        hour_key = current_time.strftime('%Y-%m-%d-%H')
        day_key = current_time.strftime('%Y-%m-%d')
        
        # Get current costs
        current_hourly = self.hourly_costs.get(f"{client_id}:{hour_key}", 0.0)
        current_daily = self.daily_costs.get(f"{client_id}:{day_key}", 0.0)
        
        # Check limits
        if current_daily + estimated_cost > self.cost_thresholds['daily_limit']:
            return {
                'allowed': False,
                'reason': 'daily_limit_exceeded',
                'current_daily': current_daily,
                'limit': self.cost_thresholds['daily_limit']
            }
        
        if current_hourly + estimated_cost > self.cost_thresholds['hourly_limit']:
            return {
                'allowed': False,
                'reason': 'hourly_limit_exceeded',
                'current_hourly': current_hourly,
                'limit': self.cost_thresholds['hourly_limit']
            }
        
        if estimated_cost > self.cost_thresholds['request_limit']:
            return {
                'allowed': False,
                'reason': 'request_limit_exceeded',
                'estimated_cost': estimated_cost,
                'limit': self.cost_thresholds['request_limit']
            }
        
        return {'allowed': True, 'estimated_cost': estimated_cost}
    
    def record_cost(self, client_id: str, actual_cost: float):
        """Record actual cost after request completion"""
        
        current_time = datetime.now()
        hour_key = current_time.strftime('%Y-%m-%d-%H')
        day_key = current_time.strftime('%Y-%m-%d')
        
        # Update costs
        self.hourly_costs[f"{client_id}:{hour_key}"] += actual_cost
        self.daily_costs[f"{client_id}:{day_key}"] += actual_cost
        
        # Record in history
        self.cost_history.append({
            'client_id': client_id,
            'cost': actual_cost,
            'timestamp': current_time
        })
    
    def get_optimization_recommendations(self, client_id: str) -> List[str]:
        """Get cost optimization recommendations"""
        
        recommendations = []
        
        # Analyze recent costs
        recent_costs = [
            entry for entry in self.cost_history 
            if entry['client_id'] == client_id and 
            entry['timestamp'] > datetime.now() - timedelta(hours=1)
        ]
        
        if recent_costs:
            avg_cost = statistics.mean([entry['cost'] for entry in recent_costs])
            
            if avg_cost > 0.20:
                recommendations.append("Consider using cache to reduce costs")
                recommendations.append("Use 'normal' priority for non-urgent requests")
            
            if len(recent_costs) > 20:
                recommendations.append("Consider batch processing for multiple requests")
            
        return recommendations


class ProductionAPIServer:
    """Production API server with monitoring and optimization"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app = FastAPI(
            title="TradingAgents-CN AI API",
            description="Production AI API for financial analysis",
            version="1.0.0",
            docs_url="/docs" if config.get('enable_docs', True) else None
        )
        
        # Initialize components
        self.ai_orchestrator = None  # Will be injected
        self.rag_system = None      # Will be injected
        self.automation_system = None  # Will be injected
        self.coordinator = None     # Will be injected
        
        # Production components
        self.rate_limiter = RateLimiter()
        self.cost_optimizer = CostOptimizer()
        self.metrics = APIMetrics(last_updated=datetime.now())
        self.response_times = deque(maxlen=1000)
        
        # Security
        self.security = HTTPBearer(auto_error=False)
        
        # Startup time
        self.startup_time = datetime.now()
        
        # Setup middleware and routes
        self._setup_middleware()
        self._setup_routes()
        
        logger.info("Production API Server initialized")
    
    def set_ai_components(self, ai_orchestrator, rag_system, automation_system, coordinator):
        """Inject AI components"""
        self.ai_orchestrator = ai_orchestrator
        self.rag_system = rag_system
        self.automation_system = automation_system
        self.coordinator = coordinator
        logger.info("AI components injected into API server")
    
    def _setup_middleware(self):
        """Setup API middleware"""
        
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get('cors_origins', ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Request/response middleware
        @self.app.middleware("http")
        async def process_request(request: Request, call_next):
            start_time = time.time()
            
            # Add request ID
            request_id = hashlib.md5(f"{time.time()}:{request.url}".encode()).hexdigest()[:16]
            request.state.request_id = request_id
            
            # Track active connections
            self.metrics.active_connections += 1
            
            try:
                response = await call_next(request)
                
                # Calculate response time
                response_time = time.time() - start_time
                self.response_times.append(response_time)
                
                # Update metrics
                self.metrics.total_requests += 1
                if response.status_code < 400:
                    self.metrics.successful_requests += 1
                else:
                    self.metrics.failed_requests += 1
                
                # Add response headers
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time"] = f"{response_time:.3f}s"
                
                return response
                
            except Exception as e:
                self.metrics.failed_requests += 1
                logger.error(f"Request processing error: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error", "request_id": request_id}
                )
            finally:
                self.metrics.active_connections -= 1
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            uptime = (datetime.now() - self.startup_time).total_seconds()
            
            health_status = {
                'status': 'healthy',
                'uptime': uptime,
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            
            # Check AI components
            if self.ai_orchestrator:
                orchestrator_health = self.ai_orchestrator.get_health_status()
                health_status['ai_orchestrator'] = orchestrator_health['overall_health']
            
            return ResponseModels.SystemStatusResponse(
                success=True,
                data=health_status,
                metadata={'uptime': uptime}
            )
        
        @self.app.get("/metrics")
        async def get_metrics():
            """Get API metrics"""
            
            # Update calculated metrics
            if self.response_times:
                self.metrics.avg_response_time = statistics.mean(self.response_times)
                self.metrics.requests_per_minute = len([
                    rt for rt in self.response_times 
                    if time.time() - rt < 60
                ])
            
            self.metrics.error_rate = (
                self.metrics.failed_requests / max(self.metrics.total_requests, 1)
            )
            
            self.metrics.last_updated = datetime.now()
            
            return ResponseModels.APIResponse(
                success=True,
                data=asdict(self.metrics)
            )
        
        @self.app.post("/analysis", response_model=ResponseModels.AnalysisResponse)
        async def analyze_symbol(request: RequestModels.AnalysisRequest,
                                bg_tasks: BackgroundTasks,
                                client_id: str = Depends(self._get_client_id)):
            """Analyze a single symbol"""
            
            start_time = time.time()
            
            try:
                # Rate limiting
                rate_check = await self.rate_limiter.check_rate_limit(client_id, request.priority)
                if not rate_check['allowed']:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            'error': APIErrorCode.RATE_LIMIT_EXCEEDED.value,
                            'message': 'Rate limit exceeded',
                            'retry_after': rate_check.get('retry_after', 60)
                        }
                    )
                
                # Cost optimization
                estimated_cost = self.cost_optimizer.estimate_cost(
                    'analysis', request.priority, {'symbol': request.symbol, 'use_cache': request.use_cache}
                )
                
                cost_check = self.cost_optimizer.check_cost_limits(client_id, estimated_cost)
                if not cost_check['allowed']:
                    raise HTTPException(
                        status_code=402,
                        detail={
                            'error': APIErrorCode.INSUFFICIENT_CREDITS.value,
                            'message': f'Cost limit exceeded: {cost_check["reason"]}',
                            'estimated_cost': estimated_cost
                        }
                    )
                
                # Execute analysis
                if not self.ai_orchestrator:
                    raise HTTPException(500, "AI orchestrator not available")
                
                result = await self.ai_orchestrator.execute_task(
                    agent_role=request.agent_role or "fundamental_expert",
                    task_prompt=f"Please analyze {request.symbol} for {request.analysis_type} analysis",
                    task_type=request.analysis_type,
                    priority=request.priority,
                    context={
                        'symbol': request.symbol,
                        'client_id': client_id,
                        'api_request': True
                    },
                    use_cache=request.use_cache
                )
                
                # Record actual cost
                actual_cost = result.actual_cost if hasattr(result, 'actual_cost') else estimated_cost
                bg_tasks.add_task(self.cost_optimizer.record_cost, client_id, actual_cost)
                
                execution_time = time.time() - start_time
                
                return ResponseModels.AnalysisResponse(
                    success=result.success,
                    analysis_result=result.result if result.success else None,
                    confidence=getattr(result, 'confidence_score', 0.8),
                    model_used=result.model_used.name if result.model_used else None,
                    agent_role=request.agent_role,
                    error={'code': APIErrorCode.AI_SERVICE_ERROR.value, 'message': result.error_message} if not result.success else None,
                    execution_time=execution_time,
                    cost=actual_cost,
                    cached=getattr(result, 'cached', False)
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        'error': APIErrorCode.INTERNAL_ERROR.value,
                        'message': str(e)
                    }
                )
        
        @self.app.post("/rag-query", response_model=ResponseModels.RAGResponse)
        async def rag_query(request: RequestModels.RAGQueryRequest,
                           bg_tasks: BackgroundTasks,
                           client_id: str = Depends(self._get_client_id)):
            """Execute RAG query"""
            
            start_time = time.time()
            
            try:
                # Rate limiting
                rate_check = await self.rate_limiter.check_rate_limit(client_id, PriorityLevel.NORMAL)
                if not rate_check['allowed']:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
                # Cost check
                estimated_cost = self.cost_optimizer.estimate_cost('rag_query', PriorityLevel.NORMAL, {})
                cost_check = self.cost_optimizer.check_cost_limits(client_id, estimated_cost)
                if not cost_check['allowed']:
                    raise HTTPException(status_code=402, detail="Cost limit exceeded")
                
                # Execute RAG query
                if not self.rag_system:
                    raise HTTPException(500, "RAG system not available")
                
                rag_result = await self.rag_system.query(
                    query_text=request.query,
                    query_type=request.query_type,
                    symbols=request.symbols,
                    top_k=request.max_documents,
                    relevance_threshold=request.relevance_threshold
                )
                
                # Record cost
                actual_cost = estimated_cost  # RAG queries have predictable costs
                bg_tasks.add_task(self.cost_optimizer.record_cost, client_id, actual_cost)
                
                execution_time = time.time() - start_time
                
                return ResponseModels.RAGResponse(
                    success=True,
                    answer=rag_result.generated_response,
                    sources=rag_result.sources,
                    relevance_score=rag_result.confidence_score,
                    documents_found=len(rag_result.retrieved_documents),
                    execution_time=execution_time,
                    cost=actual_cost
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"RAG query error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/generate-report")
        async def generate_report(request: RequestModels.ReportGenerationRequest,
                                 bg_tasks: BackgroundTasks,
                                 client_id: str = Depends(self._get_client_id)):
            """Generate automated report"""
            
            try:
                # Rate limiting and cost checks
                rate_check = await self.rate_limiter.check_rate_limit(client_id, request.priority)
                if not rate_check['allowed']:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
                estimated_cost = self.cost_optimizer.estimate_cost(
                    'report_generation', request.priority, {'symbols': request.symbols}
                )
                cost_check = self.cost_optimizer.check_cost_limits(client_id, estimated_cost)
                if not cost_check['allowed']:
                    raise HTTPException(status_code=402, detail="Cost limit exceeded")
                
                # Generate report
                if not self.automation_system:
                    raise HTTPException(500, "Automation system not available")
                
                from tradingagents.ai.intelligent_automation import ReportType
                
                # Map string to enum
                report_type_map = {
                    'daily_summary': ReportType.DAILY_SUMMARY,
                    'risk_assessment': ReportType.RISK_ASSESSMENT,
                    'market_alert': ReportType.MARKET_ALERT,
                    'custom_analysis': ReportType.CUSTOM_ANALYSIS
                }
                
                report_type = report_type_map.get(request.report_type, ReportType.DAILY_SUMMARY)
                
                report_result = await self.automation_system.report_generator.generate_report(
                    report_type=report_type,
                    symbols=request.symbols,
                    template_id=request.template_id
                )
                
                # Record cost
                actual_cost = estimated_cost
                bg_tasks.add_task(self.cost_optimizer.record_cost, client_id, actual_cost)
                
                return ResponseModels.APIResponse(
                    success=True,
                    data=report_result,
                    cost=actual_cost
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Report generation error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/multi-symbol-analysis")
        async def multi_symbol_analysis(request: RequestModels.MultiSymbolAnalysisRequest,
                                      bg_tasks: BackgroundTasks,
                                      client_id: str = Depends(self._get_client_id)):
            """Analyze multiple symbols with coordination"""
            
            try:
                # Enhanced rate limiting for multi-symbol requests
                rate_check = await self.rate_limiter.check_rate_limit(client_id, request.priority)
                if not rate_check['allowed']:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
                # Higher cost for multi-symbol analysis
                estimated_cost = self.cost_optimizer.estimate_cost(
                    'multi_symbol_analysis', request.priority, 
                    {'symbols': request.symbols, 'use_cache': request.use_cache}
                )
                cost_check = self.cost_optimizer.check_cost_limits(client_id, estimated_cost)
                if not cost_check['allowed']:
                    raise HTTPException(status_code=402, detail="Cost limit exceeded")
                
                # Execute coordinated analysis
                if not self.coordinator:
                    raise HTTPException(500, "Coordination system not available")
                
                from tradingagents.ai.enhanced_coordination import CoordinationTask, CoordinationMode
                
                # Create coordination task
                task = CoordinationTask(
                    task_id=f"multi_analysis_{client_id}_{int(time.time())}",
                    task_type="multi_symbol_analysis",
                    description=f"Multi-symbol analysis for {', '.join(request.symbols)}",
                    context={
                        'symbols': request.symbols,
                        'analysis_type': request.analysis_type,
                        'client_id': client_id
                    },
                    complexity_level="high",
                    priority=0.8 if request.priority == PriorityLevel.HIGH else 0.5
                )
                
                # Map coordination mode
                mode_map = {
                    'parallel': CoordinationMode.PARALLEL,
                    'sequential': CoordinationMode.SEQUENTIAL,
                    'consensus': CoordinationMode.CONSENSUS_BUILDING
                }
                coordination_mode = mode_map.get(request.coordination_mode, CoordinationMode.PARALLEL)
                
                result = await self.coordinator.execute_coordinated_analysis(
                    task=task,
                    coordination_mode=coordination_mode,
                    max_agents=request.max_agents
                )
                
                # Record cost
                actual_cost = estimated_cost
                bg_tasks.add_task(self.cost_optimizer.record_cost, client_id, actual_cost)
                
                return ResponseModels.APIResponse(
                    success=result.get('success', False),
                    data=result,
                    cost=actual_cost
                )
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Multi-symbol analysis error: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/cost-optimization")
        async def get_cost_optimization(client_id: str = Depends(self._get_client_id)):
            """Get cost optimization recommendations"""
            
            recommendations = self.cost_optimizer.get_optimization_recommendations(client_id)
            
            return ResponseModels.APIResponse(
                success=True,
                data={
                    'recommendations': recommendations,
                    'current_costs': {
                        'daily': self.cost_optimizer.daily_costs.get(
                            f"{client_id}:{datetime.now().strftime('%Y-%m-%d')}", 0.0
                        ),
                        'hourly': self.cost_optimizer.hourly_costs.get(
                            f"{client_id}:{datetime.now().strftime('%Y-%m-%d-%H')}", 0.0
                        )
                    },
                    'limits': self.cost_optimizer.cost_thresholds
                }
            )
    
    async def _get_client_id(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
        """Extract client ID from request (simplified authentication)"""
        
        if credentials:
            # In production, validate the token and extract client ID
            return hashlib.md5(credentials.credentials.encode()).hexdigest()[:16]
        else:
            # Fallback to IP-based identification
            return "anonymous"
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, workers: int = 1):
        """Run the API server"""
        
        logger.info(f"Starting Production API Server on {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            workers=workers,
            log_level="info",
            access_log=True,
            reload=False  # Disabled for production
        )


# Factory function for creating API server
def create_production_api(config: Dict[str, Any]) -> ProductionAPIServer:
    """
    Factory function to create production API server
    
    Args:
        config: API configuration
        
    Returns:
        Configured ProductionAPIServer instance
    """
    
    # Default configuration
    default_config = {
        'enable_docs': True,
        'cors_origins': ["*"],
        'rate_limiting': True,
        'cost_optimization': True,
        'monitoring': True,
        'cache_backend': 'memory'  # 'redis' for production
    }
    
    # Merge with provided config
    merged_config = {**default_config, **config}
    
    # Create API server
    api_server = ProductionAPIServer(merged_config)
    
    logger.info("Production API server created with configuration")
    
    return api_server


# Example usage and testing utilities
async def test_api_endpoints():
    """Test API endpoints (for development)"""
    
    import httpx
    
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        print(response.json())
        
        # Test analysis endpoint
        analysis_request = {
            "symbol": "AAPL",
            "analysis_type": "comprehensive",
            "priority": "normal"
        }
        
        response = await client.post(
            f"{base_url}/analysis",
            json=analysis_request
        )
        print(f"Analysis: {response.status_code}")
        if response.status_code == 200:
            print("Analysis successful")
        else:
            print(response.json())


if __name__ == "__main__":
    # Example configuration
    config = {
        'enable_docs': True,
        'cors_origins': ["*"],
        'rate_limiting': True,
        'cost_optimization': True
    }
    
    # Create and run API server
    api_server = create_production_api(config)
    api_server.run(host="0.0.0.0", port=8000)