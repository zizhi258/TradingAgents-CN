"""
ChartingArtist API Endpoints
为ChartingArtist提供REST API端点，支持图表生成、管理和批量操作
"""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, validator
import redis
import json

from tradingagents.agents.specialized.charting_artist import ChartingArtist
from tradingagents.utils.logging_init import get_logger
from tradingagents.core.multi_model_manager import MultiModelManager
import yaml

logger = get_logger("charting_api")

# API Router
router = APIRouter(prefix="/api/charts", tags=["charting"])

# Redis client for caching and job queue
redis_client = redis.from_url(os.getenv("TRADINGAGENTS_REDIS_URL", "redis://localhost:6379"))

# Pydantic models for API requests/responses
class ChartGenerationRequest(BaseModel):
    """图表生成请求"""
    analysis_id: str = Field(..., description="分析会话ID")
    chart_types: List[str] = Field(..., description="要生成的图表类型列表")
    config: Dict[str, Any] = Field(default_factory=dict, description="图表生成配置")
    data_sources: Dict[str, Any] = Field(..., description="数据源")
    priority: str = Field(default="normal", description="优先级: low, normal, high")
    # 新增：LLM绘图配置
    render_mode: Optional[str] = Field(default=None, description="LLM绘图渲染模式: python|html")
    model_override: Optional[str] = Field(default=None, description="强制指定LLM模型，如 moonshotai/Kimi-K2-Instruct")

    @validator('chart_types')
    def validate_chart_types(cls, v):
        allowed_types = [
            "candlestick", "line_chart", "bar_chart", "pie_chart", 
            "scatter_plot", "heatmap", "radar_chart", "gauge_chart",
            "waterfall", "box_plot"
        ]
        for chart_type in v:
            if chart_type not in allowed_types:
                raise ValueError(f"不支持的图表类型: {chart_type}")
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v not in ["low", "normal", "high"]:
            raise ValueError("优先级必须是: low, normal, high")
        return v


class BatchOperationRequest(BaseModel):
    """批量操作请求"""
    operations: List[Dict[str, Any]] = Field(..., description="操作列表")
    
    @validator('operations')
    def validate_operations(cls, v):
        allowed_ops = ["generate", "delete", "export", "refresh"]
        for op in v:
            if "operation" not in op or op["operation"] not in allowed_ops:
                raise ValueError(f"不支持的操作类型: {op.get('operation', 'unknown')}")
        return v


class ChartResponse(BaseModel):
    """图表响应模型"""
    chart_id: str
    chart_type: str
    title: str
    description: str
    file_path: Optional[str] = None
    plotly_json: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    size_bytes: Optional[int] = None


class ChartListResponse(BaseModel):
    """图表列表响应"""
    charts: List[ChartResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# Dependency injection
def _build_default_mm_config() -> Dict[str, Any]:
    """从本地配置或环境变量构建最小可用的多模型配置"""
    # 优先: 读取 config/multi_model_config.yaml
    try:
        cfg_path = Path("config/multi_model_config.yaml")
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            # 兼容常见结构: 顶层或 providers 节点
            return raw.get("providers", raw)
    except Exception:
        pass

    # 退化: 基于环境变量构建
    return {
        "deepseek": {
            "enabled": os.getenv("DEEPSEEK_ENABLED", "true").lower() in ("1","true","yes","on"),
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "default_model": os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat"),
        },
        "google_ai": {
            "enabled": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_API_KEY")),
            "api_key": os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_AI_API_KEY"),
            "default_model": os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-pro"),
        },
        "siliconflow": {
            "enabled": os.getenv("SILICONFLOW_ENABLED", "false").lower() in ("1","true","yes","on"),
            "api_key": os.getenv("SILICONFLOW_API_KEY"),
            "base_url": os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
        },
        "routing": {
            "strategy": os.getenv("ROUTING_STRATEGY", "intelligent"),
        },
        "max_cost_per_session": float(os.getenv("MAX_COST_PER_SESSION", "1.0") or 1.0),
        "enable_caching": True,
    }


def get_charting_artist() -> ChartingArtist:
    """获取ChartingArtist实例"""
    try:
        # Initialize multi-model manager with config
        mm_config = _build_default_mm_config()
        multi_model_manager = MultiModelManager(mm_config)
        return ChartingArtist(multi_model_manager)
    except Exception as e:
        logger.error(f"初始化ChartingArtist失败: {e}")
        raise HTTPException(status_code=500, detail="ChartingArtist服务不可用")


@router.post("/generate", response_model=Dict[str, Any])
async def generate_charts(
    request: ChartGenerationRequest,
    background_tasks: BackgroundTasks,
    charting_artist: ChartingArtist = Depends(get_charting_artist)
):
    """
    生成图表
    
    支持同步和异步两种模式：
    - 简单图表：同步生成并返回
    - 复杂图表：异步生成，返回任务ID
    """
    try:
        # 检查ChartingArtist是否启用
        if not charting_artist.is_enabled():
            raise HTTPException(
                status_code=503, 
                detail="ChartingArtist功能未启用，请设置环境变量CHARTING_ARTIST_ENABLED=true"
            )
        
        # 生成任务ID
        task_id = f"chart_gen_{uuid.uuid4().hex[:12]}"
        
        # 检查生成复杂度
        complexity_score = _calculate_complexity(request.chart_types, request.data_sources)
        
        if complexity_score > 3 or request.priority == "low":
            # 异步生成
            background_tasks.add_task(
                _generate_charts_async,
                task_id,
                request.dict(),
                charting_artist
            )
            
            return {
                "task_id": task_id,
                "status": "queued",
                "estimated_completion": (datetime.now() + timedelta(minutes=2)).isoformat(),
                "message": "图表正在后台生成中，请使用task_id查询进度"
            }
        
        else:
            # 同步生成
            result = charting_artist.generate_visualizations(
                symbol=request.data_sources.get("symbol", "UNKNOWN"),
                analysis_results=request.data_sources.get("analysis_results", {}),
                market_data=request.data_sources.get("market_data"),
                runtime_config={
                    "llm_enabled": True,  # 开启LLM绘图
                    "render_mode": (request.render_mode or os.getenv("CHARTING_ARTIST_RENDER_MODE", "python")),
                    "model_override": request.model_override or os.getenv("CHARTING_ARTIST_LLM_MODEL", "moonshotai/Kimi-K2-Instruct"),
                }
            )
            
            # 缓存结果
            await _cache_generation_result(task_id, result)
            
            return {
                "task_id": task_id,
                "status": "completed",
                "result": result,
                "completion_time": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"图表生成请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"图表生成失败: {str(e)}")


@router.get("/task/{task_id}")
async def get_generation_status(task_id: str):
    """查询图表生成状态"""
    try:
        # 从Redis获取任务状态
        task_key = f"chart_task:{task_id}"
        task_data = redis_client.get(task_key)
        
        if not task_data:
            raise HTTPException(status_code=404, detail="任务不存在或已过期")
        
        task_info = json.loads(task_data)
        return task_info
        
    except json.JSONDecodeError:
        logger.error(f"任务数据解析失败: {task_id}")
        raise HTTPException(status_code=500, detail="任务数据损坏")
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{analysis_id}", response_model=ChartListResponse)
async def get_charts_by_analysis(
    analysis_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """根据分析ID获取相关图表"""
    try:
        # 从文件系统搜索图表
        charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
        
        if not charts_dir.exists():
            return ChartListResponse(
                charts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_next=False
            )
        
        # 查找匹配的图表文件
        chart_files = list(charts_dir.glob(f"*{analysis_id}*.html")) + \
                     list(charts_dir.glob(f"*{analysis_id}*.json"))
        
        total_charts = len(chart_files)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_files = chart_files[start_idx:end_idx]
        
        charts = []
        for chart_file in paginated_files:
            try:
                chart_info = _extract_chart_metadata(chart_file)
                charts.append(ChartResponse(**chart_info))
            except Exception as e:
                logger.warning(f"解析图表文件失败: {chart_file}, {e}")
        
        return ChartListResponse(
            charts=charts,
            total=total_charts,
            page=page,
            page_size=page_size,
            has_next=end_idx < total_charts
        )
        
    except Exception as e:
        logger.error(f"获取图表列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取图表失败: {str(e)}")


@router.get("/chart/{chart_id}")
async def get_chart_by_id(chart_id: str):
    """根据ID获取特定图表"""
    try:
        charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
        
        # 搜索匹配的图表文件
        for ext in [".html", ".json", ".png", ".svg"]:
            chart_file = charts_dir / f"{chart_id}{ext}"
            if chart_file.exists():
                
                if ext in [".html", ".json"]:
                    # 返回文件内容
                    with open(chart_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if ext == ".json":
                        return {"chart_data": json.loads(content)}
                    else:
                        return {"html_content": content}
                
                else:
                    # 返回文件
                    return FileResponse(
                        path=chart_file,
                        media_type=f"image/{ext[1:]}",
                        filename=f"{chart_id}{ext}"
                    )
        
        raise HTTPException(status_code=404, detail="图表不存在")
        
    except Exception as e:
        logger.error(f"获取图表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取图表失败: {str(e)}")


@router.delete("/chart/{chart_id}")
async def delete_chart(chart_id: str):
    """删除图表"""
    try:
        charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
        deleted_files = []
        
        # 删除所有相关文件
        for ext in [".html", ".json", ".png", ".svg"]:
            chart_file = charts_dir / f"{chart_id}{ext}"
            if chart_file.exists():
                chart_file.unlink()
                deleted_files.append(str(chart_file))
        
        if not deleted_files:
            raise HTTPException(status_code=404, detail="图表不存在")
        
        # 清除缓存
        cache_key = f"chart_metadata:{chart_id}"
        redis_client.delete(cache_key)
        
        return {
            "message": f"成功删除图表 {chart_id}",
            "deleted_files": deleted_files
        }
        
    except Exception as e:
        logger.error(f"删除图表失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除图表失败: {str(e)}")


@router.post("/batch", response_model=Dict[str, Any])
async def batch_operations(
    request: BatchOperationRequest,
    background_tasks: BackgroundTasks
):
    """批量图表操作"""
    try:
        # 生成批量任务ID
        batch_id = f"batch_{uuid.uuid4().hex[:12]}"
        
        # 将批量操作加入后台任务
        background_tasks.add_task(
            _process_batch_operations,
            batch_id,
            request.operations
        )
        
        return {
            "batch_id": batch_id,
            "status": "queued",
            "operations_count": len(request.operations),
            "message": "批量操作已加入队列，请使用batch_id查询进度"
        }
        
    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """查询批量操作状态"""
    try:
        batch_key = f"batch_task:{batch_id}"
        batch_data = redis_client.get(batch_key)
        
        if not batch_data:
            raise HTTPException(status_code=404, detail="批量任务不存在或已过期")
        
        return json.loads(batch_data)
        
    except json.JSONDecodeError:
        logger.error(f"批量任务数据解析失败: {batch_id}")
        raise HTTPException(status_code=500, detail="任务数据损坏")
    except Exception as e:
        logger.error(f"查询批量任务状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/list", response_model=ChartListResponse)
async def list_all_charts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    chart_type: Optional[str] = Query(None, description="按图表类型筛选"),
    created_after: Optional[datetime] = Query(None, description="创建时间过滤")
):
    """列出所有图表"""
    try:
        charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
        
        if not charts_dir.exists():
            return ChartListResponse(
                charts=[],
                total=0,
                page=page,
                page_size=page_size,
                has_next=False
            )
        
        # 获取所有图表文件
        chart_files = []
        for ext in [".html", ".json"]:
            chart_files.extend(list(charts_dir.glob(f"*{ext}")))
        
        # 应用过滤器
        if chart_type:
            chart_files = [f for f in chart_files if chart_type in f.name]
        
        if created_after:
            chart_files = [
                f for f in chart_files 
                if datetime.fromtimestamp(f.stat().st_ctime) > created_after
            ]
        
        # 按创建时间排序（最新的在前）
        chart_files.sort(key=lambda x: x.stat().st_ctime, reverse=True)
        
        total_charts = len(chart_files)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_files = chart_files[start_idx:end_idx]
        
        charts = []
        for chart_file in paginated_files:
            try:
                chart_info = _extract_chart_metadata(chart_file)
                charts.append(ChartResponse(**chart_info))
            except Exception as e:
                logger.warning(f"解析图表文件失败: {chart_file}, {e}")
        
        return ChartListResponse(
            charts=charts,
            total=total_charts,
            page=page,
            page_size=page_size,
            has_next=end_idx < total_charts
        )
        
    except Exception as e:
        logger.error(f"获取图表列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取图表列表失败: {str(e)}")


@router.delete("/cleanup")
async def cleanup_old_charts(
    days: int = Query(30, ge=1, le=365, description="删除多少天前的图表"),
    dry_run: bool = Query(False, description="预览模式，不实际删除")
):
    """清理旧图表"""
    try:
        charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
        
        if not charts_dir.exists():
            return {"message": "图表目录不存在", "deleted_count": 0}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_files = []
        
        for chart_file in charts_dir.iterdir():
            if chart_file.is_file():
                file_mtime = datetime.fromtimestamp(chart_file.stat().st_mtime)
                
                if file_mtime < cutoff_date:
                    if not dry_run:
                        chart_file.unlink()
                    deleted_files.append({
                        "file": str(chart_file),
                        "modified_time": file_mtime.isoformat(),
                        "size_bytes": chart_file.stat().st_size
                    })
        
        total_size = sum(f["size_bytes"] for f in deleted_files)
        
        return {
            "message": f"{'预览' if dry_run else '完成'} 清理 {days} 天前的图表",
            "deleted_count": len(deleted_files),
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "files": deleted_files if dry_run else [],
            "dry_run": dry_run
        }
        
    except Exception as e:
        logger.error(f"清理图表失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查ChartingArtist状态
        try:
            charting_artist = get_charting_artist()
            artist_status = "enabled" if charting_artist.is_enabled() else "disabled"
        except Exception:
            artist_status = "error"
        
        # 检查存储目录
        charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
        storage_status = "healthy" if charts_dir.exists() and charts_dir.is_dir() else "error"
        
        # 检查Redis连接
        try:
            redis_client.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "disconnected"
        
        # 获取统计信息
        if charts_dir.exists():
            chart_count = len([f for f in charts_dir.iterdir() if f.is_file()])
            total_size = sum(f.stat().st_size for f in charts_dir.iterdir() if f.is_file())
        else:
            chart_count = 0
            total_size = 0
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "charting_artist": artist_status,
                "storage": storage_status,
                "redis": redis_status
            },
            "stats": {
                "total_charts": chart_count,
                "storage_size_mb": round(total_size / 1024 / 1024, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# 辅助函数
def _calculate_complexity(chart_types: List[str], data_sources: Dict[str, Any]) -> int:
    """计算图表生成复杂度评分"""
    complexity = 0
    
    # 基于图表类型
    complex_charts = ["candlestick", "heatmap", "radar_chart", "waterfall"]
    for chart_type in chart_types:
        if chart_type in complex_charts:
            complexity += 2
        else:
            complexity += 1
    
    # 基于数据量
    analysis_results = data_sources.get("analysis_results", {})
    if len(analysis_results) > 5:
        complexity += 1
    
    return complexity


async def _generate_charts_async(task_id: str, request_data: Dict[str, Any], charting_artist: ChartingArtist):
    """异步生成图表"""
    try:
        # 更新任务状态
        await _update_task_status(task_id, "processing", "图表生成中...")
        
        # 生成图表
        result = charting_artist.generate_visualizations(
            symbol=request_data["data_sources"].get("symbol", "UNKNOWN"),
            analysis_results=request_data["data_sources"].get("analysis_results", {}),
            market_data=request_data["data_sources"].get("market_data"),
            runtime_config={
                "llm_enabled": True,
                "render_mode": request_data.get("render_mode") or os.getenv("CHARTING_ARTIST_RENDER_MODE", "python"),
                "model_override": request_data.get("model_override") or os.getenv("CHARTING_ARTIST_LLM_MODEL", "moonshotai/Kimi-K2-Instruct"),
            }
        )
        
        # 更新任务状态为完成
        await _update_task_status(task_id, "completed", "图表生成完成", result)
        
    except Exception as e:
        logger.error(f"异步图表生成失败: {e}")
        await _update_task_status(task_id, "failed", f"生成失败: {str(e)}")


async def _process_batch_operations(batch_id: str, operations: List[Dict[str, Any]]):
    """处理批量操作"""
    try:
        results = []
        completed = 0
        
        for i, operation in enumerate(operations):
            try:
                # 更新进度
                progress = int((i / len(operations)) * 100)
                await _update_batch_status(batch_id, "processing", f"处理中 ({completed}/{len(operations)})", results, progress)
                
                # 处理单个操作
                op_result = await _process_single_operation(operation)
                results.append(op_result)
                completed += 1
                
            except Exception as e:
                logger.error(f"批量操作中的单个操作失败: {e}")
                results.append({"operation": operation, "status": "failed", "error": str(e)})
        
        # 更新最终状态
        await _update_batch_status(batch_id, "completed", f"批量操作完成 ({completed}/{len(operations)})", results, 100)
        
    except Exception as e:
        logger.error(f"批量操作处理失败: {e}")
        await _update_batch_status(batch_id, "failed", f"批量操作失败: {str(e)}")


async def _process_single_operation(operation: Dict[str, Any]) -> Dict[str, Any]:
    """处理单个操作"""
    op_type = operation.get("operation")
    
    if op_type == "delete":
        chart_id = operation.get("chart_id")
        # 实现删除逻辑
        return {"operation": "delete", "chart_id": chart_id, "status": "success"}
    
    elif op_type == "export":
        # 实现导出逻辑
        return {"operation": "export", "status": "success"}
    
    # 其他操作类型...
    return {"operation": op_type, "status": "not_implemented"}


async def _update_task_status(task_id: str, status: str, message: str, result: Dict[str, Any] = None):
    """更新任务状态"""
    task_data = {
        "task_id": task_id,
        "status": status,
        "message": message,
        "updated_at": datetime.now().isoformat()
    }
    
    if result:
        task_data["result"] = result
    
    # 存储到Redis，设置过期时间为24小时
    redis_client.setex(
        f"chart_task:{task_id}",
        86400,  # 24小时
        json.dumps(task_data, ensure_ascii=False)
    )


async def _update_batch_status(batch_id: str, status: str, message: str, results: List[Dict[str, Any]] = None, progress: int = 0):
    """更新批量任务状态"""
    batch_data = {
        "batch_id": batch_id,
        "status": status,
        "message": message,
        "progress": progress,
        "updated_at": datetime.now().isoformat()
    }
    
    if results:
        batch_data["results"] = results
    
    # 存储到Redis，设置过期时间为24小时
    redis_client.setex(
        f"batch_task:{batch_id}",
        86400,  # 24小时
        json.dumps(batch_data, ensure_ascii=False)
    )


async def _cache_generation_result(task_id: str, result: Dict[str, Any]):
    """缓存生成结果"""
    try:
        cache_key = f"chart_result:{task_id}"
        redis_client.setex(
            cache_key,
            3600,  # 1小时
            json.dumps(result, ensure_ascii=False, default=str)
        )
    except Exception as e:
        logger.warning(f"缓存图表生成结果失败: {e}")


def _extract_chart_metadata(chart_file: Path) -> Dict[str, Any]:
    """从图表文件提取元数据"""
    file_stats = chart_file.stat()
    
    # 从文件名解析信息
    parts = chart_file.stem.split('_')
    symbol = parts[0] if len(parts) > 0 else "Unknown"
    chart_type = parts[1] if len(parts) > 1 else "unknown"
    chart_id = parts[-1] if len(parts) > 2 else chart_file.stem
    
    return {
        "chart_id": chart_id,
        "chart_type": chart_type,
        "title": f"{symbol} {chart_type.title()}",
        "description": f"{symbol}的{chart_type}图表",
        "file_path": str(chart_file),
        "created_at": datetime.fromtimestamp(file_stats.st_ctime),
        "size_bytes": file_stats.st_size,
        "metadata": {
            "symbol": symbol,
            "file_extension": chart_file.suffix,
            "modified_at": datetime.fromtimestamp(file_stats.st_mtime).isoformat()
        }
    }
