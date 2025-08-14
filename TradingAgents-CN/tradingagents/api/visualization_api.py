"""
Visualization API Endpoints
可视化服务API接口定义
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from pathlib import Path
import json
import uuid

from tradingagents.agents.specialized.charting_artist import ChartingArtist
from tradingagents.utils.logging_init import get_logger

logger = get_logger("visualization_api")
router = APIRouter(prefix="/api/v1/visualization", tags=["visualization"])


# Request/Response Models
class ChartGenerationRequest(BaseModel):
    """图表生成请求"""
    symbol: str = Field(..., description="股票代码")
    analysis_results: Dict[str, Any] = Field(..., description="前序分析结果")
    chart_types: Optional[List[str]] = Field(None, description="指定图表类型")
    market_data: Optional[Dict[str, Any]] = Field(None, description="市场数据")
    config: Optional[Dict[str, Any]] = Field(None, description="图表配置")

class ChartResponse(BaseModel):
    """单个图表响应"""
    chart_id: str
    chart_type: str
    title: str
    description: str
    file_path: str
    url: str
    interactive: bool
    created_at: datetime

class VisualizationResponse(BaseModel):
    """可视化响应"""
    request_id: str
    symbol: str
    status: str
    charts: List[ChartResponse]
    total_charts: int
    generation_time: int
    metadata: Dict[str, Any]
    errors: List[Dict[str, Any]] = []

class ChartListResponse(BaseModel):
    """图表列表响应"""
    charts: List[ChartResponse]
    total: int
    page: int
    page_size: int

class ChartConfigResponse(BaseModel):
    """图表配置响应"""
    supported_chart_types: List[str]
    default_config: Dict[str, Any]
    templates: Dict[str, Any]


# API Endpoints

@router.post("/generate", response_model=VisualizationResponse)
async def generate_visualization(
    request: ChartGenerationRequest,
    background_tasks: BackgroundTasks
) -> VisualizationResponse:
    """
    生成可视化图表
    
    根据分析结果和配置生成一组可视化图表
    """
    request_id = str(uuid.uuid4())
    start_time = datetime.now()
    
    try:
        logger.info(f"开始生成可视化图表: {request.symbol}, request_id: {request_id}")
        
        # 初始化绘图师（这里需要依赖注入多模型管理器）
        # 实际应用中应该从依赖注入容器获取
        charting_artist = get_charting_artist_instance()
        
        if not charting_artist.is_enabled():
            raise HTTPException(
                status_code=503,
                detail="绘图师服务未启用，请检查 CHARTING_ARTIST_ENABLED 环境变量"
            )
        
        # 生成可视化
        viz_results = charting_artist.generate_visualizations(
            symbol=request.symbol,
            analysis_results=request.analysis_results,
            market_data=request.market_data
        )
        
        # 构建响应
        charts = []
        for chart_info in viz_results.get("charts_generated", []):
            chart_response = ChartResponse(
                chart_id=str(uuid.uuid4()),
                chart_type=chart_info["chart_type"],
                title=chart_info.get("title", f"{request.symbol} {chart_info['chart_type']}"),
                description=chart_info.get("description", ""),
                file_path=chart_info["path"],
                url=f"/api/v1/visualization/chart/{chart_info['filename']}",
                interactive=True,
                created_at=datetime.now()
            )
            charts.append(chart_response)
        
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        response = VisualizationResponse(
            request_id=request_id,
            symbol=request.symbol,
            status="success",
            charts=charts,
            total_charts=len(charts),
            generation_time=execution_time,
            metadata={
                "charting_artist_enabled": True,
                "generation_strategy": "post_processing",
                "chart_config_used": charting_artist.chart_config
            },
            errors=viz_results.get("errors", [])
        )
        
        logger.info(f"可视化生成完成: {len(charts)} 张图表, 耗时: {execution_time}ms")
        return response
        
    except Exception as e:
        logger.error(f"可视化生成失败: {e}", exc_info=True)
        execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return VisualizationResponse(
            request_id=request_id,
            symbol=request.symbol,
            status="error",
            charts=[],
            total_charts=0,
            generation_time=execution_time,
            metadata={"error": str(e)},
            errors=[{"general_error": str(e)}]
        )


@router.get("/chart/{filename}")
async def get_chart(filename: str) -> FileResponse:
    """
    获取图表文件
    
    返回指定的图表HTML文件
    """
    try:
        chart_path = Path("data/attachments/charts") / filename
        
        if not chart_path.exists():
            raise HTTPException(status_code=404, detail="图表文件不存在")
        
        if not filename.endswith(('.html', '.png', '.svg')):
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        return FileResponse(
            path=str(chart_path),
            filename=filename,
            media_type="text/html" if filename.endswith('.html') else "image/png"
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="图表文件不存在")
    except Exception as e:
        logger.error(f"获取图表文件失败: {e}")
        raise HTTPException(status_code=500, detail="获取图表文件失败")


@router.get("/charts", response_model=ChartListResponse)
async def list_charts(
    symbol: Optional[str] = Query(None, description="股票代码过滤"),
    chart_type: Optional[str] = Query(None, description="图表类型过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
) -> ChartListResponse:
    """
    获取图表列表
    
    支持按股票代码和图表类型过滤
    """
    try:
        charts_dir = Path("data/attachments/charts")
        chart_files = []
        
        if charts_dir.exists():
            for chart_file in charts_dir.glob("*.html"):
                # 解析文件名获取信息
                parts = chart_file.stem.split('_')
                if len(parts) >= 3:
                    file_symbol = parts[0]
                    file_chart_type = parts[1]
                    
                    # 应用过滤器
                    if symbol and file_symbol != symbol:
                        continue
                    if chart_type and file_chart_type != chart_type:
                        continue
                    
                    chart_response = ChartResponse(
                        chart_id=chart_file.stem,
                        chart_type=file_chart_type,
                        title=f"{file_symbol} {file_chart_type}图表",
                        description=f"{file_symbol}的{file_chart_type}可视化分析",
                        file_path=str(chart_file),
                        url=f"/api/v1/visualization/chart/{chart_file.name}",
                        interactive=True,
                        created_at=datetime.fromtimestamp(chart_file.stat().st_mtime)
                    )
                    chart_files.append(chart_response)
        
        # 分页
        total = len(chart_files)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_charts = chart_files[start_idx:end_idx]
        
        return ChartListResponse(
            charts=paginated_charts,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"获取图表列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取图表列表失败")


@router.delete("/chart/{filename}")
async def delete_chart(filename: str) -> Dict[str, Any]:
    """
    删除图表文件
    
    删除指定的图表文件
    """
    try:
        chart_path = Path("data/attachments/charts") / filename
        
        if not chart_path.exists():
            raise HTTPException(status_code=404, detail="图表文件不存在")
        
        chart_path.unlink()
        
        return {
            "status": "success",
            "message": f"图表文件 {filename} 已删除"
        }
        
    except Exception as e:
        logger.error(f"删除图表文件失败: {e}")
        raise HTTPException(status_code=500, detail="删除图表文件失败")


@router.get("/config", response_model=ChartConfigResponse)
async def get_chart_config() -> ChartConfigResponse:
    """
    获取图表配置信息
    
    返回支持的图表类型、默认配置等信息
    """
    try:
        charting_artist = get_charting_artist_instance()
        
        supported_types = list(charting_artist.chart_generators.keys())
        
        return ChartConfigResponse(
            supported_chart_types=supported_types,
            default_config=charting_artist.chart_config,
            templates={
                "price_analysis": {
                    "chart_types": ["candlestick", "line_chart"],
                    "indicators": ["ma", "volume"]
                },
                "technical_analysis": {
                    "chart_types": ["candlestick", "scatter_plot"],
                    "indicators": ["ma", "rsi", "macd"]
                },
                "fundamental_analysis": {
                    "chart_types": ["bar_chart", "waterfall"],
                    "metrics": ["revenue", "profit", "ratios"]
                },
                "risk_analysis": {
                    "chart_types": ["gauge_chart", "radar_chart", "heatmap"],
                    "metrics": ["var", "volatility", "correlation"]
                }
            }
        )
        
    except Exception as e:
        logger.error(f"获取图表配置失败: {e}")
        raise HTTPException(status_code=500, detail="获取图表配置失败")


@router.post("/config/update")
async def update_chart_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新图表配置
    
    动态更新图表生成配置
    """
    try:
        # 这里应该实现配置更新逻辑
        # 实际应用中需要验证配置格式和权限
        
        return {
            "status": "success",
            "message": "图表配置已更新",
            "updated_config": config
        }
        
    except Exception as e:
        logger.error(f"更新图表配置失败: {e}")
        raise HTTPException(status_code=500, detail="更新图表配置失败")


@router.get("/status")
async def get_visualization_status() -> Dict[str, Any]:
    """
    获取可视化服务状态
    
    返回服务启用状态、支持的功能等信息
    """
    try:
        charting_artist = get_charting_artist_instance()
        charts_dir = Path("data/attachments/charts")
        
        # 统计图表文件
        chart_count = len(list(charts_dir.glob("*.html"))) if charts_dir.exists() else 0
        
        return {
            "service_enabled": charting_artist.is_enabled(),
            "supported_chart_types": len(charting_artist.chart_generators),
            "total_charts_generated": chart_count,
            "charts_directory": str(charts_dir),
            "configuration": {
                "charting_artist_enabled": charting_artist.is_enabled(),
                "default_theme": charting_artist.chart_config.get("charting_artist", {}).get("chart_settings", {}).get("default_theme", "plotly_dark")
            },
            "health_status": "healthy" if charting_artist.is_enabled() else "disabled"
        }
        
    except Exception as e:
        logger.error(f"获取服务状态失败: {e}")
        raise HTTPException(status_code=500, detail="获取服务状态失败")


# Batch Operations
@router.post("/batch/generate")
async def batch_generate_charts(
    requests: List[ChartGenerationRequest],
    background_tasks: BackgroundTasks
) -> List[VisualizationResponse]:
    """
    批量生成图表
    
    支持同时为多个股票生成可视化图表
    """
    try:
        batch_id = str(uuid.uuid4())
        logger.info(f"开始批量生成图表，批次ID: {batch_id}, 数量: {len(requests)}")
        
        responses = []
        for req in requests:
            try:
                response = await generate_visualization(req, background_tasks)
                responses.append(response)
            except Exception as e:
                logger.error(f"批量生成中单个请求失败: {req.symbol}, error: {e}")
                responses.append(VisualizationResponse(
                    request_id=str(uuid.uuid4()),
                    symbol=req.symbol,
                    status="error",
                    charts=[],
                    total_charts=0,
                    generation_time=0,
                    metadata={"batch_id": batch_id},
                    errors=[{"error": str(e)}]
                ))
        
        return responses
        
    except Exception as e:
        logger.error(f"批量生成图表失败: {e}")
        raise HTTPException(status_code=500, detail="批量生成图表失败")


@router.delete("/cleanup")
async def cleanup_old_charts(
    days_old: int = Query(7, ge=1, description="清理多少天前的图表")
) -> Dict[str, Any]:
    """
    清理旧图表文件
    
    删除指定天数之前的图表文件
    """
    try:
        charts_dir = Path("data/attachments/charts")
        if not charts_dir.exists():
            return {"cleaned_files": 0, "message": "图表目录不存在"}
        
        cutoff_time = datetime.now().timestamp() - (days_old * 24 * 3600)
        cleaned_count = 0
        
        for chart_file in charts_dir.glob("*.html"):
            if chart_file.stat().st_mtime < cutoff_time:
                chart_file.unlink()
                cleaned_count += 1
        
        return {
            "cleaned_files": cleaned_count,
            "message": f"已清理 {days_old} 天前的 {cleaned_count} 个图表文件"
        }
        
    except Exception as e:
        logger.error(f"清理图表文件失败: {e}")
        raise HTTPException(status_code=500, detail="清理图表文件失败")


# Helper Functions
def get_charting_artist_instance():
    """
    获取绘图师实例
    
    实际应用中应该使用依赖注入容器管理实例
    """
    # 这里需要根据实际的依赖注入方式来实现
    # 临时实现，实际应用中需要从容器获取
    from tradingagents.core.multi_model_manager import MultiModelManager
    
    # 这是一个简化的实现，实际应该从应用上下文获取
    try:
        multi_model_manager = MultiModelManager()
        return ChartingArtist(multi_model_manager=multi_model_manager)
    except Exception as e:
        logger.error(f"创建绘图师实例失败: {e}")
        raise HTTPException(status_code=503, detail="绘图师服务不可用")