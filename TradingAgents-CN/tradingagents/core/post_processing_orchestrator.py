"""
Post-Processing Orchestrator
后处理编排器 - 管理ChartingArtist的触发和执行
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from tradingagents.utils.logging_init import get_logger
from tradingagents.agents.specialized.charting_artist import ChartingArtist
from tradingagents.agents.specialized.base_specialized_agent import AgentAnalysisResult


logger = get_logger("post_processing_orchestrator")


class PostProcessingStage(Enum):
    """后处理阶段枚举"""
    PENDING = "pending"
    ANALYZING = "analyzing" 
    VISUALIZING = "visualizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PostProcessingContext:
    """后处理上下文"""
    session_id: str
    symbol: str
    analysis_results: Dict[str, AgentAnalysisResult]
    market_data: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    stage: PostProcessingStage = PostProcessingStage.PENDING
    start_time: datetime = field(default_factory=datetime.now)
    completion_time: Optional[datetime] = None
    error_message: Optional[str] = None
    visualization_results: Optional[Dict[str, Any]] = None


@dataclass  
class PostProcessingResult:
    """后处理结果"""
    success: bool
    context: PostProcessingContext
    charts_generated: List[Dict[str, Any]] = field(default_factory=list)
    total_execution_time: int = 0  # milliseconds
    error_details: Optional[str] = None


class PostProcessingOrchestrator:
    """
    后处理编排器
    
    负责管理分析完成后的后处理流程，包括ChartingArtist的触发和执行
    """
    
    def __init__(self, multi_model_manager, config: Dict[str, Any] = None):
        """
        初始化后处理编排器
        
        Args:
            multi_model_manager: 多模型管理器实例
            config: 配置参数
        """
        self.multi_model_manager = multi_model_manager
        self.config = config or {}
        
        # 初始化后处理组件
        self.charting_artist = ChartingArtist(
            multi_model_manager=multi_model_manager,
            config=config.get("charting_artist", {})
        )
        
        # 后处理回调函数
        self.completion_callbacks: List[Callable[[PostProcessingResult], None]] = []
        
        # 当前活跃的后处理任务
        self.active_tasks: Dict[str, PostProcessingContext] = {}
        
        self.logger = get_logger("post_processing_orchestrator")
        self.logger.info("后处理编排器初始化完成")
    
    def register_completion_callback(self, callback: Callable[[PostProcessingResult], None]) -> None:
        """注册后处理完成回调函数"""
        self.completion_callbacks.append(callback)
    
    def should_trigger_post_processing(self, analysis_results: Dict[str, AgentAnalysisResult]) -> bool:
        """
        判断是否应该触发后处理
        
        Args:
            analysis_results: 分析结果字典
            
        Returns:
            bool: 是否应该触发后处理
        """
        try:
            # 检查ChartingArtist是否启用
            if not self.charting_artist.is_enabled():
                self.logger.debug("ChartingArtist未启用，跳过后处理")
                return False
            
            # 检查核心分析是否完成
            required_agents = ["fundamental_expert", "technical_analyst", "chief_decision_officer"]
            completed_agents = list(analysis_results.keys())
            
            # 至少需要有基本的分析结果
            if not any(agent in completed_agents for agent in required_agents):
                self.logger.debug("核心分析未完成，跳过后处理")
                return False
            
            # 检查分析结果质量
            avg_confidence = sum(
                result.confidence_score for result in analysis_results.values()
            ) / len(analysis_results)
            
            if avg_confidence < 0.5:  # 置信度过低
                self.logger.debug(f"分析置信度过低 ({avg_confidence:.3f})，跳过后处理")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"判断后处理触发条件失败: {e}")
            return False
    
    async def execute_post_processing(self, 
                                    session_id: str,
                                    symbol: str,
                                    analysis_results: Dict[str, AgentAnalysisResult],
                                    market_data: Dict[str, Any] = None) -> PostProcessingResult:
        """
        执行后处理流程
        
        Args:
            session_id: 会话ID
            symbol: 股票代码
            analysis_results: 分析结果
            market_data: 市场数据
            
        Returns:
            PostProcessingResult: 后处理结果
        """
        context = PostProcessingContext(
            session_id=session_id,
            symbol=symbol,
            analysis_results=analysis_results,
            market_data=market_data or {},
            config=self.config
        )
        
        # 添加到活跃任务列表
        self.active_tasks[session_id] = context
        
        try:
            self.logger.info(f"开始后处理流程: {symbol}, session: {session_id}")
            
            # 阶段1: 分析准备
            context.stage = PostProcessingStage.ANALYZING
            await self._prepare_analysis_data(context)
            
            # 阶段2: 可视化生成
            context.stage = PostProcessingStage.VISUALIZING
            await self._execute_visualization(context)
            
            # 完成后处理
            context.stage = PostProcessingStage.COMPLETED
            context.completion_time = datetime.now()
            
            result = PostProcessingResult(
                success=True,
                context=context,
                charts_generated=context.visualization_results.get("charts_generated", []),
                total_execution_time=int(
                    (context.completion_time - context.start_time).total_seconds() * 1000
                )
            )
            
            self.logger.info(f"后处理完成: {len(result.charts_generated)} 个图表, 耗时: {result.total_execution_time}ms")
            
        except Exception as e:
            self.logger.error(f"后处理执行失败: {e}", exc_info=True)
            
            context.stage = PostProcessingStage.FAILED
            context.error_message = str(e)
            context.completion_time = datetime.now()
            
            result = PostProcessingResult(
                success=False,
                context=context,
                error_details=str(e),
                total_execution_time=int(
                    (context.completion_time - context.start_time).total_seconds() * 1000
                )
            )
        
        finally:
            # 从活跃任务列表移除
            self.active_tasks.pop(session_id, None)
            
            # 触发完成回调
            await self._trigger_completion_callbacks(result)
        
        return result
    
    async def _prepare_analysis_data(self, context: PostProcessingContext) -> None:
        """准备分析数据"""
        try:
            # 合并分析结果
            combined_results = {}
            for agent_role, result in context.analysis_results.items():
                combined_results[agent_role] = {
                    "analysis_content": result.analysis_content,
                    "confidence_score": result.confidence_score,
                    "key_points": result.key_points,
                    "risk_factors": result.risk_factors,
                    "recommendations": result.recommendations,
                    "supporting_data": result.supporting_data
                }
            
            # 提取可视化相关数据
            visualization_data = self._extract_visualization_data(combined_results, context.market_data)
            
            # 更新上下文
            context.market_data.update(visualization_data)
            
        except Exception as e:
            self.logger.error(f"准备分析数据失败: {e}")
            raise
    
    async def _execute_visualization(self, context: PostProcessingContext) -> None:
        """执行可视化生成"""
        try:
            # 转换分析结果格式
            analysis_dict = {
                agent_role: {
                    "analysis_content": result.analysis_content,
                    "key_points": result.key_points,
                    "risk_factors": result.risk_factors,
                    "recommendations": result.recommendations,
                    "supporting_data": result.supporting_data
                }
                for agent_role, result in context.analysis_results.items()
            }
            
            # 生成可视化
            viz_results = self.charting_artist.generate_visualizations(
                symbol=context.symbol,
                analysis_results=analysis_dict,
                market_data=context.market_data
            )
            
            context.visualization_results = viz_results
            
        except Exception as e:
            self.logger.error(f"执行可视化生成失败: {e}")
            raise
    
    def _extract_visualization_data(self, 
                                  analysis_results: Dict[str, Any],
                                  market_data: Dict[str, Any]) -> Dict[str, Any]:
        """从分析结果中提取可视化数据"""
        viz_data = {}
        
        try:
            # 从技术分析中提取价格数据
            if "technical_analyst" in analysis_results:
                tech_data = analysis_results["technical_analyst"].get("supporting_data", {})
                if "price_data" in tech_data:
                    viz_data["price_data"] = tech_data["price_data"]
            
            # 从基本面分析中提取财务数据
            if "fundamental_expert" in analysis_results:
                fund_data = analysis_results["fundamental_expert"].get("supporting_data", {})
                if "financial_metrics" in fund_data:
                    viz_data["financial_data"] = fund_data["financial_metrics"]
            
            # 从风险管理中提取风险数据
            if "risk_manager" in analysis_results:
                risk_data = analysis_results["risk_manager"].get("supporting_data", {})
                if "risk_metrics" in risk_data:
                    viz_data["risk_data"] = risk_data["risk_metrics"]
            
            # 添加市场数据
            viz_data.update(market_data)
            
        except Exception as e:
            self.logger.warning(f"提取可视化数据失败: {e}")
        
        return viz_data
    
    async def _trigger_completion_callbacks(self, result: PostProcessingResult) -> None:
        """触发完成回调函数"""
        try:
            for callback in self.completion_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(result)
                    else:
                        callback(result)
                except Exception as e:
                    self.logger.error(f"后处理回调函数执行失败: {e}")
        except Exception as e:
            self.logger.error(f"触发完成回调失败: {e}")
    
    def get_active_tasks(self) -> Dict[str, PostProcessingContext]:
        """获取活跃的后处理任务"""
        return self.active_tasks.copy()
    
    def get_task_status(self, session_id: str) -> Optional[PostProcessingStage]:
        """获取指定任务的状态"""
        task = self.active_tasks.get(session_id)
        return task.stage if task else None
    
    def cancel_task(self, session_id: str) -> bool:
        """取消后处理任务"""
        try:
            if session_id in self.active_tasks:
                task = self.active_tasks[session_id]
                task.stage = PostProcessingStage.FAILED
                task.error_message = "任务被用户取消"
                self.active_tasks.pop(session_id)
                self.logger.info(f"后处理任务已取消: {session_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"取消任务失败: {e}")
            return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        try:
            charting_stats = self.charting_artist.get_performance_summary()
            
            return {
                "charting_artist": charting_stats,
                "active_tasks": len(self.active_tasks),
                "total_callbacks": len(self.completion_callbacks),
                "orchestrator_enabled": True
            }
        except Exception as e:
            self.logger.error(f"获取性能统计失败: {e}")
            return {
                "error": str(e),
                "orchestrator_enabled": False
            }


# 全局编排器实例管理
_orchestrator_instance: Optional[PostProcessingOrchestrator] = None


def initialize_post_processing_orchestrator(multi_model_manager, config: Dict[str, Any] = None) -> PostProcessingOrchestrator:
    """初始化全局后处理编排器实例"""
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = PostProcessingOrchestrator(
            multi_model_manager=multi_model_manager,
            config=config
        )
        logger.info("全局后处理编排器已初始化")
    
    return _orchestrator_instance


def get_post_processing_orchestrator() -> Optional[PostProcessingOrchestrator]:
    """获取全局后处理编排器实例"""
    return _orchestrator_instance


# 便捷函数
async def execute_post_processing_if_needed(session_id: str,
                                          symbol: str,
                                          analysis_results: Dict[str, AgentAnalysisResult],
                                          market_data: Dict[str, Any] = None) -> Optional[PostProcessingResult]:
    """
    如果需要则执行后处理
    
    Args:
        session_id: 会话ID
        symbol: 股票代码
        analysis_results: 分析结果
        market_data: 市场数据
        
    Returns:
        Optional[PostProcessingResult]: 后处理结果，如果未触发则返回None
    """
    orchestrator = get_post_processing_orchestrator()
    
    if orchestrator is None:
        logger.warning("后处理编排器未初始化")
        return None
    
    if not orchestrator.should_trigger_post_processing(analysis_results):
        logger.debug("不满足后处理触发条件，跳过执行")
        return None
    
    return await orchestrator.execute_post_processing(
        session_id=session_id,
        symbol=symbol,
        analysis_results=analysis_results,
        market_data=market_data
    )