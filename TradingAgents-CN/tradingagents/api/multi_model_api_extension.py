"""
Multi-Model API Endpoints Extension
扩展现有的stock_api.py以支持多模型协作分析
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date
import json
import asyncio

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger('multi_model_api')


class CollaborativeAnalysisRequest(BaseModel):
    """协作分析请求模型"""
    ticker: str = Field(..., description="股票代码")
    trade_date: Optional[str] = Field(None, description="交易日期，格式：YYYY-MM-DD")
    collaboration_mode: str = Field("sequential", description="协作模式：sequential/parallel/debate")
    selected_agents: Optional[List[str]] = Field(None, description="选择的智能体列表")
    context: Optional[Dict[str, Any]] = Field(None, description="额外的上下文信息")
    
    class Config:
        schema_extra = {
            "example": {
                "ticker": "AAPL",
                "trade_date": "2024-12-07",
                "collaboration_mode": "sequential",
                "selected_agents": ["news_hunter", "fundamental_expert", "technical_analyst", "risk_manager"],
                "context": {
                    "urgency": "normal",
                    "complexity": "medium"
                }
            }
        }


class SmartAnalysisRequest(BaseModel):
    """智能分析请求模型"""
    ticker: str = Field(..., description="股票代码")
    trade_date: Optional[str] = Field(None, description="交易日期，格式：YYYY-MM-DD")
    context: Optional[Dict[str, Any]] = Field(None, description="分析上下文")
    
    class Config:
        schema_extra = {
            "example": {
                "ticker": "TSLA",
                "trade_date": "2024-12-07",
                "context": {
                    "urgency": "high",
                    "complexity": "high",
                    "focus_areas": ["news", "risk"]
                }
            }
        }


class ModelSelectionRequest(BaseModel):
    """模型选择请求"""
    agent_role: str = Field(..., description="智能体角色")
    task_type: str = Field("general", description="任务类型")
    task_description: Optional[str] = Field("", description="任务描述")
    complexity_level: str = Field("medium", description="复杂度：low/medium/high")
    
    class Config:
        schema_extra = {
            "example": {
                "agent_role": "fundamental_expert",
                "task_type": "fundamental_analysis",
                "task_description": "分析苹果公司的基本面情况",
                "complexity_level": "high"
            }
        }


class MultiModelAPIExtension:
    """多模型API扩展类"""
    
    def __init__(self, trading_graph_instance):
        """
        初始化API扩展
        
        Args:
            trading_graph_instance: TradingGraph实例
        """
        self.trading_graph = trading_graph_instance
        self.router = APIRouter(prefix="/api/v2", tags=["multi-model"])
        self._setup_routes()
        
        logger.info("多模型API扩展初始化完成")
    
    def _setup_routes(self):
        """设置API路由"""
        
        @self.router.post("/analysis/collaborative")
        async def collaborative_analysis(request: CollaborativeAnalysisRequest):
            """执行协作分析"""
            try:
                # 参数验证
                if not request.ticker:
                    raise HTTPException(status_code=400, detail="股票代码不能为空")
                
                # 默认使用当前日期
                trade_date = request.trade_date or datetime.now().strftime('%Y-%m-%d')
                
                # 验证协作模式
                available_modes = self.trading_graph.get_available_collaboration_modes()
                if request.collaboration_mode not in available_modes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"不支持的协作模式: {request.collaboration_mode}，可用模式: {available_modes}"
                    )
                
                # 验证智能体选择
                if request.selected_agents:
                    available_agents = self.trading_graph.get_available_agents()
                    invalid_agents = [agent for agent in request.selected_agents if agent not in available_agents]
                    if invalid_agents:
                        raise HTTPException(
                            status_code=400,
                            detail=f"不支持的智能体: {invalid_agents}，可用智能体: {available_agents}"
                        )
                
                # 执行协作分析
                logger.info(f"开始协作分析: {request.ticker}, 模式: {request.collaboration_mode}")
                
                result = self.trading_graph.analyze_with_collaboration(
                    company_name=request.ticker,
                    trade_date=trade_date,
                    collaboration_mode=request.collaboration_mode,
                    selected_agents=request.selected_agents
                )
                
                # 添加请求元数据
                result['request_metadata'] = {
                    'timestamp': datetime.now().isoformat(),
                    'collaboration_mode': request.collaboration_mode,
                    'selected_agents': request.selected_agents,
                    'api_version': 'v2'
                }
                
                return {
                    'success': True,
                    'data': result,
                    'message': '协作分析完成'
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"协作分析失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"协作分析执行失败: {str(e)}")
        
        @self.router.post("/analysis/smart")
        async def smart_analysis(request: SmartAnalysisRequest):
            """智能分析（自动选择最佳协作模式）"""
            try:
                if not request.ticker:
                    raise HTTPException(status_code=400, detail="股票代码不能为空")
                
                trade_date = request.trade_date or datetime.now().strftime('%Y-%m-%d')
                
                logger.info(f"开始智能分析: {request.ticker}")
                
                result = self.trading_graph.smart_analyze(
                    company_name=request.ticker,
                    trade_date=trade_date,
                    context=request.context
                )
                
                result['request_metadata'] = {
                    'timestamp': datetime.now().isoformat(),
                    'analysis_type': 'smart',
                    'api_version': 'v2'
                }
                
                return {
                    'success': True,
                    'data': result,
                    'message': '智能分析完成'
                }
                
            except Exception as e:
                logger.error(f"智能分析失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"智能分析执行失败: {str(e)}")
        
        @self.router.post("/routing/select-model")
        async def select_optimal_model(request: ModelSelectionRequest):
            """智能模型选择"""
            try:
                if not self.trading_graph.multi_model_extension:
                    raise HTTPException(status_code=503, detail="多模型功能不可用")
                
                multi_model_manager = self.trading_graph.multi_model_extension.multi_model_manager
                
                # 执行模型选择
                model_selection = multi_model_manager.select_optimal_model(
                    agent_role=request.agent_role,
                    task_type=request.task_type,
                    task_description=request.task_description,
                    complexity_level=request.complexity_level
                )
                
                return {
                    'success': True,
                    'data': {
                        'selected_model': model_selection.model_spec.name,
                        'provider': model_selection.model_spec.provider.value,
                        'confidence': model_selection.confidence_score,
                        'reasoning': model_selection.reasoning,
                        'estimated_cost': model_selection.estimated_cost,
                        'estimated_time': model_selection.estimated_time,
                        'model_details': {
                            'type': model_selection.model_spec.model_type,
                            'max_tokens': model_selection.model_spec.max_tokens,
                            'cost_per_1k_tokens': model_selection.model_spec.cost_per_1k_tokens
                        }
                    },
                    'message': '模型选择完成'
                }
                
            except Exception as e:
                logger.error(f"模型选择失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"模型选择失败: {str(e)}")
        
        @self.router.get("/system/status")
        async def get_system_status():
            """获取多模型系统状态"""
            try:
                status = self.trading_graph.get_multi_model_status()
                
                return {
                    'success': True,
                    'data': status,
                    'message': '系统状态获取成功'
                }
                
            except Exception as e:
                logger.error(f"获取系统状态失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")
        
        @self.router.get("/agents/available")
        async def get_available_agents():
            """获取可用的智能体列表"""
            try:
                agents = self.trading_graph.get_available_agents()
                collaboration_modes = self.trading_graph.get_available_collaboration_modes()
                
                # 获取智能体详细信息
                agent_details = {}
                if self.trading_graph.multi_model_extension:
                    for agent_name in agents:
                        if agent_name in self.trading_graph.multi_model_extension.specialized_agents:
                            agent = self.trading_graph.multi_model_extension.specialized_agents[agent_name]
                            agent_details[agent_name] = {
                                'description': agent.description,
                                'task_type': agent.get_specialized_task_type(),
                                'performance': agent.get_performance_summary()
                            }
                
                return {
                    'success': True,
                    'data': {
                        'available_agents': agents,
                        'collaboration_modes': collaboration_modes,
                        'agent_details': agent_details
                    },
                    'message': '智能体列表获取成功'
                }
                
            except Exception as e:
                logger.error(f"获取智能体列表失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取智能体列表失败: {str(e)}")
        
        @self.router.get("/performance/metrics")
        async def get_performance_metrics(
            time_window_hours: int = Query(24, description="时间窗口（小时）", ge=1, le=720)
        ):
            """获取性能指标"""
            try:
                if not self.trading_graph.multi_model_extension:
                    raise HTTPException(status_code=503, detail="多模型功能不可用")
                
                routing_engine = self.trading_graph.multi_model_extension.multi_model_manager.routing_engine
                
                # 获取路由统计
                routing_stats = routing_engine.get_routing_statistics(time_window_hours)
                
                # 获取智能体性能
                agent_performance = {}
                for agent_name, agent in self.trading_graph.multi_model_extension.specialized_agents.items():
                    agent_performance[agent_name] = agent.get_performance_summary()
                
                return {
                    'success': True,
                    'data': {
                        'routing_statistics': routing_stats,
                        'agent_performance': agent_performance,
                        'time_window_hours': time_window_hours,
                        'timestamp': datetime.now().isoformat()
                    },
                    'message': '性能指标获取成功'
                }
                
            except Exception as e:
                logger.error(f"获取性能指标失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取性能指标失败: {str(e)}")
        
        @self.router.post("/system/enable-smart-analysis")
        async def enable_smart_analysis():
            """启用智能分析模式"""
            try:
                success = self.trading_graph.enable_smart_analysis()
                
                if success:
                    return {
                        'success': True,
                        'data': {'smart_analysis_enabled': True},
                        'message': '智能分析模式已启用'
                    }
                else:
                    raise HTTPException(status_code=503, detail="无法启用智能分析模式")
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"启用智能分析模式失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"启用智能分析模式失败: {str(e)}")
        
        @self.router.get("/models/available")
        async def get_available_models():
            """获取所有可用的模型列表"""
            try:
                if not self.trading_graph.multi_model_extension:
                    raise HTTPException(status_code=503, detail="多模型功能不可用")
                
                multi_model_manager = self.trading_graph.multi_model_extension.multi_model_manager
                
                # 获取所有可用模型
                available_models = multi_model_manager._get_all_available_models()
                
                # 格式化模型信息
                models_by_provider = {}
                for model_name, model_spec in available_models.items():
                    provider = model_spec.provider.value
                    
                    if provider not in models_by_provider:
                        models_by_provider[provider] = []
                    
                    models_by_provider[provider].append({
                        'name': model_spec.name,
                        'type': model_spec.model_type,
                        'cost_per_1k_tokens': model_spec.cost_per_1k_tokens,
                        'max_tokens': model_spec.max_tokens,
                        'context_window': model_spec.context_window,
                        'supports_streaming': model_spec.supports_streaming
                    })
                
                return {
                    'success': True,
                    'data': {
                        'models_by_provider': models_by_provider,
                        'total_models': len(available_models),
                        'providers': list(models_by_provider.keys())
                    },
                    'message': '模型列表获取成功'
                }
                
            except Exception as e:
                logger.error(f"获取模型列表失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")
    
    def get_router(self) -> APIRouter:
        """获取API路由器"""
        return self.router


def extend_stock_api_with_multi_model(app, trading_graph_instance):
    """
    扩展现有的stock_api应用以支持多模型功能
    
    Args:
        app: FastAPI应用实例
        trading_graph_instance: TradingGraph实例
    """
    try:
        # 创建多模型API扩展
        multi_model_extension = MultiModelAPIExtension(trading_graph_instance)
        
        # 添加路由到现有应用
        app.include_router(multi_model_extension.get_router())
        
        logger.info("多模型API扩展已成功添加到现有应用")
        
        return multi_model_extension
        
    except Exception as e:
        logger.error(f"多模型API扩展失败: {e}", exc_info=True)
        return None