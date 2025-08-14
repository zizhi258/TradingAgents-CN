"""
Market Analysis API Client
市场分析API客户端 - 与后端Market-Wide Analysis API进行通信
"""

import requests
import json
import time
import os
import threading
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from tradingagents.utils.logging_manager import get_logger
logger = get_logger('market_api_client')


class ScanStatus(Enum):
    """扫描状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MarketScanConfig:
    """市场扫描配置"""
    market_type: str  # A股, 美股, 港股
    preset_type: str  # 预设筛选类型
    scan_depth: int   # 扫描深度 1-5
    budget_limit: float  # 预算上限
    stock_limit: int  # 股票数量限制
    time_range: str   # 时间范围
    custom_filters: Optional[Dict] = None  # 自定义筛选条件
    analysis_focus: Optional[Dict] = None  # 分析重点
    ai_model_config: Optional[Dict] = None  # AI模型配置
    advanced_options: Optional[Dict] = None  # 高级选项


@dataclass
class ScanProgress:
    """扫描进度"""
    scan_id: str
    status: ScanStatus
    overall_progress: int  # 0-100
    current_stage: str
    stages: List[Dict]
    stats: Dict
    latest_message: str
    preview_results: Optional[Dict] = None
    error_message: Optional[str] = None
    estimated_completion: Optional[str] = None


@dataclass
class ScanResults:
    """扫描结果"""
    scan_id: str
    total_stocks: int
    recommended_stocks: int
    actual_cost: float
    scan_duration: str
    rankings: List[Dict]
    sectors: Dict
    breadth: Dict
    summary: Dict
    created_at: str


class MarketAnalysisAPIClient:
    """市场分析API客户端"""
    
    def __init__(self, base_url: str = None, timeout: int = 30):
        """
        初始化API客户端
        
        Args:
            base_url: API服务器基础URL
            timeout: 请求超时时间（秒）
        """
        # Base URL resolution: env -> argument -> default
        env_base = os.getenv('MARKET_API_BASE_URL') or os.getenv('API_BASE_URL')
        base = base_url or env_base or 'http://localhost:8000'
        self.base_url = base.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # 设置默认请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # 尝试自动探测可用的 API 基址（多路径探测）
        self._auto_detect_base_url()

        # API端点
        self.endpoints = {
            'create_scan': '/api/v1/market/scans',
            'scan_status': '/api/v1/market/scans/{run_id}/status',
            'scan_rankings': '/api/v1/market/scans/{run_id}/rankings',
            'scan_sectors': '/api/v1/market/scans/{run_id}/sectors',
            'scan_breadth': '/api/v1/market/scans/{run_id}/breadth',
            'scan_summary': '/api/v1/market/scans/{run_id}/summary',
            'scan_export': '/api/v1/market/scans/{run_id}/export',
            'pause_scan': '/api/v1/market/scans/{run_id}/pause',
            'resume_scan': '/api/v1/market/scans/{run_id}/resume',
            'cancel_scan': '/api/v1/market/scans/{run_id}/cancel',

            # New market data endpoints (harmonized with backend)
            'stock_info': '/api/v1/market/stocks/{code}/info',
            'stock_list': '/api/v1/market/stocks',
            'stock_search': '/api/v1/market/stocks/search',
            'stock_daily': '/api/v1/market/stocks/{code}/daily',
            'market_summary': '/api/v1/market/summary',

            'tushare_daily_basic': '/api/v1/market/tushare/daily_basic',
            'tushare_moneyflow': '/api/v1/market/tushare/moneyflow',
            'tushare_block_trade': '/api/v1/market/tushare/block_trade',
            'tushare_stk_limit': '/api/v1/market/tushare/stk_limit',
            'tushare_hk_hold': '/api/v1/market/tushare/hk_hold',
            'group_filter': '/api/v1/market/filters/group/{group}',
            'custom_filter': '/api/v1/market/filters/custom',
        }
        
        logger.info(f"初始化市场分析API客户端，服务器地址: {self.base_url}")

    def _auto_detect_base_url(self):
        """Detect a reachable base URL by probing several known paths quickly.

        Order:
          1) current base_url
          2) docker->local fallbacks (localhost, 127.0.0.1, host.docker.internal)
          3) optional candidates from MARKET_API_CANDIDATES (comma-separated)

        A URL is considered reachable if any probe returns status < 500.
        """
        import re

        def _with_host(url: str, host: str) -> str:
            try:
                m = re.match(r"^(https?://)([^/:]+)(?::(\d+))?", url)
                if not m:
                    return url
                scheme = m.group(1)
                port = m.group(3) or '8000'
                return f"{scheme}{host}:{port}"
            except Exception:
                return url

        candidates = [self.base_url]
        # Common docker->local fallbacks based on current scheme/port
        if '://api:' in self.base_url or '://localhost' in self.base_url:
            for host in ('localhost', '127.0.0.1', 'host.docker.internal'):
                candidates.append(_with_host(self.base_url, host))
        # Optional extra candidates
        extra = os.getenv('MARKET_API_CANDIDATES')
        if extra:
            for x in extra.split(','):
                x = x.strip()
                if x:
                    candidates.append(x)
        else:
            # Sensible defaults if none provided
            candidates.extend(['http://localhost:8000', 'http://127.0.0.1:8000', 'http://host.docker.internal:8000'])

        # Deduplicate while preserving order
        seen = set()
        uniq = []
        for u in candidates:
            v = u.rstrip('/')
            if v not in seen:
                seen.add(v)
                uniq.append(v)

        probe_paths = ['/health', '/api/info']
        for base in uniq:
            for path in probe_paths:
                try:
                    r = self.session.get(f"{base}{path}", timeout=1.5)
                    # treat any non-5xx as reachable (2xx, 3xx, 401/403/404)
                    if r.status_code < 500:
                        self.base_url = base
                        return
                except requests.exceptions.RequestException:
                    continue
        # If the current base is a docker alias and nothing worked, bias to localhost
        if '://api:' in self.base_url:
            self.base_url = 'http://localhost:8000'
        # keep original if none reachable; actual calls will raise accordingly
    
    def create_scan(self, config: MarketScanConfig) -> Dict[str, Any]:
        """
        创建新的市场扫描
        
        Args:
            config: 扫描配置
            
        Returns:
            Dict: 包含scan_id和创建信息的响应
            
        Raises:
            APIError: API调用失败
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['create_scan']}"
            
            # 构建请求数据
            request_data = {
                'market_type': config.market_type,
                'preset_type': config.preset_type,
                'scan_depth': config.scan_depth,
                'budget_limit': config.budget_limit,
                'stock_limit': config.stock_limit,
                'time_range': config.time_range,
                'custom_filters': config.custom_filters or {},
                'analysis_focus': config.analysis_focus or {},
                'ai_model_config': config.ai_model_config or {},
                'advanced_options': config.advanced_options or {}
            }
            
            logger.info(f"创建市场扫描请求: {config.market_type}, 深度: {config.scan_depth}, 预算: {config.budget_limit}")
            
            response = self.session.post(
                url, 
                json=request_data, 
                timeout=self.timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"市场扫描创建成功: {result.get('scan_id', 'unknown')}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"创建市场扫描失败: {e}")
            raise APIError(f"创建扫描失败: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"解析响应JSON失败: {e}")
            raise APIError(f"响应格式错误: {e}")
    
    def get_scan_status(self, scan_id: str) -> ScanProgress:
        """
        获取扫描状态和进度
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            ScanProgress: 扫描进度信息
            
        Raises:
            APIError: API调用失败
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['scan_status'].format(run_id=scan_id)}"
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            
            # 解析响应数据
            return ScanProgress(
                scan_id=scan_id,
                status=ScanStatus(data.get('status', 'unknown')),
                overall_progress=data.get('overall_progress', 0),
                current_stage=data.get('current_stage', ''),
                stages=data.get('stages', []),
                stats=data.get('stats', {}),
                latest_message=data.get('latest_message', ''),
                preview_results=data.get('preview_results'),
                error_message=data.get('error_message'),
                estimated_completion=data.get('estimated_completion')
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取扫描状态失败: {e}")
            raise APIError(f"获取扫描状态失败: {e}")
    
    def get_scan_rankings(self, scan_id: str, 
                         sort_by: str = "total_score",
                         order: str = "desc",
                         limit: int = 100,
                         filters: Optional[Dict] = None) -> List[Dict]:
        """
        获取股票排名结果
        
        Args:
            scan_id: 扫描ID
            sort_by: 排序字段
            order: 排序方向 (asc/desc)
            limit: 返回数量限制
            filters: 筛选条件
            
        Returns:
            List[Dict]: 股票排名列表
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['scan_rankings'].format(run_id=scan_id)}"
            
            params = {
                'sort_by': sort_by,
                'order': order,
                'limit': limit
            }
            
            if filters:
                params.update(filters)
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json().get('rankings', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取股票排名失败: {e}")
            raise APIError(f"获取股票排名失败: {e}")

    # -----------------------------
    # New: thin wrappers for market data
    # -----------------------------

    def get_stock_info(self, code: str) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['stock_info'].format(code=code)}"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_stocks(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['stock_list']}"
        r = self.session.get(url, params={'page': page, 'page_size': page_size}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def search_stocks(self, keyword: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['stock_search']}"
        r = self.session.get(url, params={'q': keyword, 'page': page, 'page_size': page_size}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_daily(self, code: str, start_date: str = None, end_date: str = None, adj: str = 'qfq') -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['stock_daily'].format(code=code)}"
        params = {'adj': adj}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def market_summary(self) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['market_summary']}"
        r = self.session.get(url, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # Tushare mirrors
    def ts_daily_basic(self, **params) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['tushare_daily_basic']}"
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def ts_moneyflow(self, **params) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['tushare_moneyflow']}"
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def ts_block_trade(self, **params) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['tushare_block_trade']}"
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def ts_stk_limit(self, **params) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['tushare_stk_limit']}"
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def ts_hk_hold(self, **params) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['tushare_hk_hold']}"
        r = self.session.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # Index presets/constituents/ohlc endpoints have been removed from backend.

    def filter_group(self, group: str, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['group_filter'].format(group=group)}"
        r = self.session.get(url, params={'page': page, 'page_size': page_size}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def filter_custom(self, **conditions) -> Dict[str, Any]:
        url = f"{self.base_url}{self.endpoints['custom_filter']}"
        r = self.session.post(url, json=conditions, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
    
    def get_sector_analysis(self, scan_id: str) -> Dict[str, Any]:
        """
        获取板块分析结果
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            Dict: 板块分析数据
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['scan_sectors'].format(run_id=scan_id)}"
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json().get('sectors', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取板块分析失败: {e}")
            raise APIError(f"获取板块分析失败: {e}")
    
    def get_market_breadth(self, scan_id: str) -> Dict[str, Any]:
        """
        获取市场广度指标
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            Dict: 市场广度数据
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['scan_breadth'].format(run_id=scan_id)}"
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json().get('breadth', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取市场广度失败: {e}")
            raise APIError(f"获取市场广度失败: {e}")
    
    def get_executive_summary(self, scan_id: str) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            Dict: 执行摘要数据
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['scan_summary'].format(run_id=scan_id)}"
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json().get('summary', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取执行摘要失败: {e}")
            raise APIError(f"获取执行摘要失败: {e}")
    
    def get_complete_results(self, scan_id: str) -> ScanResults:
        """
        获取完整的扫描结果
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            ScanResults: 完整扫描结果
        """
        
        try:
            # 并行获取各部分结果
            rankings = self.get_scan_rankings(scan_id)
            sectors = self.get_sector_analysis(scan_id)
            breadth = self.get_market_breadth(scan_id)
            summary = self.get_executive_summary(scan_id)
            
            # 获取基本信息
            progress = self.get_scan_status(scan_id)
            stats = progress.stats
            
            return ScanResults(
                scan_id=scan_id,
                total_stocks=stats.get('total_stocks', 0),
                recommended_stocks=stats.get('recommended_stocks', 0),
                actual_cost=stats.get('actual_cost', 0.0),
                scan_duration=stats.get('scan_duration', '未知'),
                rankings=rankings,
                sectors=sectors,
                breadth=breadth,
                summary=summary,
                created_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"获取完整结果失败: {e}")
            raise APIError(f"获取完整结果失败: {e}")
    
    def export_results(self, scan_id: str, export_format: str = "excel", 
                      options: Optional[Dict] = None) -> Union[bytes, str]:
        """
        导出扫描结果
        
        Args:
            scan_id: 扫描ID
            export_format: 导出格式 (excel, pdf, html, csv)
            options: 导出选项
            
        Returns:
            Union[bytes, str]: 导出的文件内容或下载链接
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['scan_export'].format(run_id=scan_id)}"
            
            params = {'format': export_format}
            if options:
                params.update(options)
            
            response = self.session.get(url, params=params, timeout=60)  # 导出可能需要更长时间
            response.raise_for_status()
            
            # 根据响应类型返回不同格式
            content_type = response.headers.get('content-type', '')
            
            if 'application/json' in content_type:
                # 返回下载链接
                return response.json().get('download_url', '')
            else:
                # 返回文件内容
                return response.content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"导出结果失败: {e}")
            raise APIError(f"导出结果失败: {e}")
    
    def pause_scan(self, scan_id: str) -> bool:
        """
        暂停扫描
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            bool: 是否暂停成功
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['pause_scan'].format(run_id=scan_id)}"
            
            response = self.session.post(url, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            success = result.get('success', False)
            
            if success:
                logger.info(f"扫描暂停成功: {scan_id}")
            else:
                logger.warning(f"扫描暂停失败: {scan_id}, 原因: {result.get('message', 'unknown')}")
            
            return success
            
        except requests.exceptions.RequestException as e:
            logger.error(f"暂停扫描失败: {e}")
            return False
    
    def resume_scan(self, scan_id: str) -> bool:
        """
        继续扫描
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            bool: 是否继续成功
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['resume_scan'].format(run_id=scan_id)}"
            
            response = self.session.post(url, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            success = result.get('success', False)
            
            if success:
                logger.info(f"扫描继续成功: {scan_id}")
            else:
                logger.warning(f"扫描继续失败: {scan_id}, 原因: {result.get('message', 'unknown')}")
            
            return success
            
        except requests.exceptions.RequestException as e:
            logger.error(f"继续扫描失败: {e}")
            return False
    
    def cancel_scan(self, scan_id: str) -> bool:
        """
        取消扫描
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            bool: 是否取消成功
        """
        
        try:
            url = f"{self.base_url}{self.endpoints['cancel_scan'].format(run_id=scan_id)}"
            
            response = self.session.post(url, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            success = result.get('success', False)
            
            if success:
                logger.info(f"扫描取消成功: {scan_id}")
            else:
                logger.warning(f"扫描取消失败: {scan_id}, 原因: {result.get('message', 'unknown')}")
            
            return success
            
        except requests.exceptions.RequestException as e:
            logger.error(f"取消扫描失败: {e}")
            return False
    
    def health_check(self) -> bool:
        """
        检查API服务健康状态
        
        Returns:
            bool: 服务是否正常
        """
        
        try:
            url = f"{self.base_url}/health"
            response = self.session.get(url, timeout=5)
            
            return response.status_code == 200
            
        except Exception:
            return False
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        获取API信息
        
        Returns:
            Dict: API信息
        """
        
        try:
            url = f"{self.base_url}/api/info"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取API信息失败: {e}")
            return {}
    
    def close(self):
        """关闭HTTP会话"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()


class APIError(Exception):
    """API调用异常"""
    pass


class MockMarketAnalysisAPIClient(MarketAnalysisAPIClient):
    """模拟API客户端，用于开发和测试"""
    
    def __init__(self):
        """初始化模拟客户端"""
        # 不调用父类初始化，避免网络连接
        self.mock_data = {}
        self.scan_counter = 0
        logger.info("初始化模拟市场分析API客户端")
    
    def create_scan(self, config: MarketScanConfig) -> Dict[str, Any]:
        """模拟创建扫描"""
        
        import uuid
        import datetime
        
        self.scan_counter += 1
        scan_id = f"mock_scan_{uuid.uuid4().hex[:8]}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 存储扫描配置
        self.mock_data[scan_id] = {
            'config': config,
            'status': ScanStatus.RUNNING,
            'created_at': datetime.datetime.now(),
            'progress': 0,
            'results': None
        }
        
        logger.info(f"模拟创建扫描成功: {scan_id}")
        
        return {
            'success': True,
            'scan_id': scan_id,
            'message': '扫描创建成功',
            'estimated_cost': config.stock_limit * 0.05,
            'estimated_duration': f"{config.scan_depth * 5}分钟"
        }
    
    def get_scan_status(self, scan_id: str) -> ScanProgress:
        """模拟获取扫描状态"""
        
        if scan_id not in self.mock_data:
            raise APIError(f"扫描不存在: {scan_id}")
        
        scan_data = self.mock_data[scan_id]
        
        # 模拟进度递增
        current_progress = scan_data.get('progress', 0)
        if scan_data['status'] == ScanStatus.RUNNING and current_progress < 100:
            import random
            scan_data['progress'] = min(100, current_progress + random.randint(5, 15))
        
        # 进度完成后更新状态
        if scan_data['progress'] >= 100 and scan_data['status'] == ScanStatus.RUNNING:
            scan_data['status'] = ScanStatus.COMPLETED
            scan_data['results'] = self._generate_mock_results(scan_data['config'])
        
        progress = scan_data['progress']
        
        # 生成模拟阶段信息
        stages = [
            {'name': '数据准备', 'completed': progress > 10, 'current': progress <= 10},
            {'name': '股票筛选', 'completed': progress > 30, 'current': 10 < progress <= 30},
            {'name': '技术分析', 'completed': progress > 60, 'current': 30 < progress <= 60},
            {'name': '基本面分析', 'completed': progress > 80, 'current': 60 < progress <= 80},
            {'name': '生成报告', 'completed': progress > 95, 'current': 80 < progress <= 95}
        ]
        
        # 统计信息
        config = scan_data['config']
        stats = {
            'processed_stocks': int(progress * config.stock_limit / 100),
            'total_stocks': config.stock_limit,
            'cost_used': progress * config.budget_limit / 100,
            'scan_duration': f"{int(progress / 5)}分钟" if progress >= 100 else None,
            'actual_cost': config.budget_limit * 0.8 if progress >= 100 else None,
            'recommended_stocks': int(progress * config.stock_limit / 500) if progress >= 100 else 0
        }
        
        return ScanProgress(
            scan_id=scan_id,
            status=scan_data['status'],
            overall_progress=progress,
            current_stage=next((s['name'] for s in stages if s['current']), '已完成'),
            stages=stages,
            stats=stats,
            latest_message=f"正在处理第{progress}%阶段...",
            preview_results=self._generate_preview_results(progress) if progress < 100 else None,
            estimated_completion=f"{max(1, int((100 - progress) / 10))}分钟" if progress < 100 else "已完成"
        )
    
    def get_scan_rankings(self, scan_id: str, **kwargs) -> List[Dict]:
        """模拟获取股票排名"""
        
        if scan_id not in self.mock_data:
            return []
        
        scan_data = self.mock_data[scan_id]
        if scan_data['status'] != ScanStatus.COMPLETED or not scan_data['results']:
            return []
        
        return scan_data['results']['rankings']
    
    def get_sector_analysis(self, scan_id: str) -> Dict[str, Any]:
        """模拟获取板块分析"""
        
        if scan_id not in self.mock_data:
            return {}
        
        scan_data = self.mock_data[scan_id]
        if scan_data['status'] != ScanStatus.COMPLETED or not scan_data['results']:
            return {}
        
        return scan_data['results']['sectors']
    
    def get_market_breadth(self, scan_id: str) -> Dict[str, Any]:
        """模拟获取市场广度"""
        
        if scan_id not in self.mock_data:
            return {}
        
        scan_data = self.mock_data[scan_id]
        if scan_data['status'] != ScanStatus.COMPLETED or not scan_data['results']:
            return {}
        
        return scan_data['results']['breadth']
    
    def get_executive_summary(self, scan_id: str) -> Dict[str, Any]:
        """模拟获取执行摘要"""
        
        if scan_id not in self.mock_data:
            return {}
        
        scan_data = self.mock_data[scan_id]
        if scan_data['status'] != ScanStatus.COMPLETED or not scan_data['results']:
            return {}
        
        return scan_data['results']['summary']
    
    def pause_scan(self, scan_id: str) -> bool:
        """模拟暂停扫描"""
        
        if scan_id in self.mock_data:
            self.mock_data[scan_id]['status'] = ScanStatus.PAUSED
            return True
        return False
    
    def resume_scan(self, scan_id: str) -> bool:
        """模拟继续扫描"""
        
        if scan_id in self.mock_data and self.mock_data[scan_id]['status'] == ScanStatus.PAUSED:
            self.mock_data[scan_id]['status'] = ScanStatus.RUNNING
            return True
        return False
    
    def cancel_scan(self, scan_id: str) -> bool:
        """模拟取消扫描"""
        
        if scan_id in self.mock_data:
            self.mock_data[scan_id]['status'] = ScanStatus.CANCELLED
            return True
        return False
    
    def health_check(self) -> bool:
        """模拟健康检查"""
        return True
    
    def _generate_mock_results(self, config: MarketScanConfig) -> Dict:
        """生成模拟结果数据"""
        
        import random
        
        # 生成模拟股票排名
        rankings = []
        for i in range(min(config.stock_limit, 100)):
            rankings.append({
                'symbol': f"{1000000 + i:06d}",
                'name': f"模拟股票{i:03d}",
                'total_score': random.uniform(60, 95),
                'technical_score': random.uniform(50, 100),
                'fundamental_score': random.uniform(50, 100),
                'current_price': random.uniform(10, 200),
                'change_percent': random.uniform(-8, 12),
                'recommendation': random.choice(['买入', '持有', '关注', '卖出']),
                'target_price': random.uniform(15, 250),
                'market_cap': random.uniform(50, 5000),
                'pe_ratio': random.uniform(8, 50),
                'pb_ratio': random.uniform(0.5, 8)
            })
        
        # 按综合评分排序
        rankings.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 生成板块数据
        sector_names = ['科技', '金融', '消费', '医药', '能源', '制造', '地产', '材料']
        sectors = {}
        for sector in sector_names:
            sectors[sector] = {
                'change_percent': random.uniform(-5, 10),
                'volume': random.uniform(100, 1000),
                'activity_score': random.uniform(30, 90),
                'recommendation_score': random.uniform(40, 85),
                'leading_stock': f"{sector}龙头股",
                'recommended_count': random.randint(3, 15),
                'market_cap': random.uniform(1000, 50000),
                'recommended_stocks': rankings[:random.randint(3, 8)]
            }
        
        # 生成市场广度数据
        breadth = {
            'up_ratio': random.uniform(30, 70),
            'up_ratio_change': random.uniform(-5, 5),
            'activity_index': random.uniform(40, 80),
            'activity_change': random.uniform(-10, 10),
            'net_inflow': random.uniform(-100, 200),
            'net_inflow_change': random.uniform(-50, 50),
            'sentiment_index': random.uniform(30, 80),
            'sentiment_change': random.uniform(-5, 5),
            'market_strength': random.uniform(30, 85),
            'limit_up_count': random.randint(0, 50),
            'limit_down_count': random.randint(0, 20),
            'new_high_count': random.randint(10, 100),
            'new_low_count': random.randint(5, 50),
            'high_volume_count': random.randint(50, 200)
        }
        
        # 生成执行摘要
        summary = {
            'key_insights': [
                f"{config.market_type}市场整体表现{'强劲' if breadth['market_strength'] > 60 else '一般'}",
                f"共发现{len([r for r in rankings if r['recommendation'] == '买入'])}只值得买入的股票",
                f"科技板块表现{'突出' if sectors['科技']['change_percent'] > 0 else '疲软'}"
            ],
            'investment_recommendations': {
                'buy': [r for r in rankings if r['recommendation'] == '买入'][:5],
                'watch': [r for r in rankings if r['recommendation'] == '关注'][:5]
            },
            'risk_factors': [
                '市场波动性较高，注意风险控制',
                '部分板块存在估值过高风险'
            ],
            'market_outlook': f"{config.market_type}市场短期内可能继续{'上涨' if breadth['sentiment_index'] > 50 else '震荡'}，建议{'积极' if breadth['market_strength'] > 60 else '谨慎'}参与。",
            'scan_statistics': {
                'completion_rate': 100,
                'data_quality': '良好',
                'confidence_level': random.randint(75, 95)
            }
        }
        
        return {
            'rankings': rankings,
            'sectors': sectors,
            'breadth': breadth,
            'summary': summary
        }
    
    def _generate_preview_results(self, progress: int) -> Dict:
        """生成预览结果"""
        
        import random
        
        if progress < 30:
            return {}
        
        return {
            'top_stocks': [
                {'name': f'股票{i}', 'symbol': f'00000{i}', 'score': random.uniform(80, 95)}
                for i in range(5)
            ],
            'sector_performance': {
                '科技': {'change_percent': random.uniform(-2, 5)},
                '金融': {'change_percent': random.uniform(-3, 2)},
                '消费': {'change_percent': random.uniform(-1, 4)}
            },
            'market_sentiment': random.uniform(40, 70)
        }


class LocalMarketAnalysisClient(MarketAnalysisAPIClient):
    """本地编排客户端：不经HTTP，直接在进程内调用 Orchestrator"""

    def __init__(self):
        # 不调用父类初始化，避免HTTP会话
        from tradingagents.core.market_scan_orchestrator import MarketScanOrchestrator, OrchestratorConfig
        self._Orchestrator = MarketScanOrchestrator
        self._Cfg = OrchestratorConfig
        self._runs: Dict[str, Dict[str, Any]] = {}
        logger.info('初始化本地市场分析客户端（Local backend）')

    def create_scan(self, config: MarketScanConfig) -> Dict[str, Any]:
        import uuid
        run_id = f"local_scan_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 预设运行态
        self._runs[run_id] = {
            'status': ScanStatus.RUNNING,
            'progress': 0,
            'current_stage': '初始化',
            'stages': [],
            'stats': {
                'processed_stocks': 0,
                'total_stocks': config.stock_limit,
                'cost_used': 0.0,
                'scan_duration': None,
                'actual_cost': None,
                'recommended_stocks': 0,
            },
            'latest_message': '开始',
            'preview_results': None,
            'error_message': None,
            'estimated_completion': None,
            'results': None,
            'config': config,
            'created_at': datetime.now().isoformat(),
        }

        def _progress_cb(msg: str, cur: int, total: int):
            try:
                st = self._runs.get(run_id)
                if not st:
                    return
                st['progress'] = int(max(0, min(100, cur)))
                st['latest_message'] = msg
                st['current_stage'] = msg
                st['stages'] = [
                    {'name': '准备环境', 'completed': st['progress'] > 5, 'current': st['progress'] <= 5},
                    {'name': '股票池', 'completed': st['progress'] > 10, 'current': 5 < st['progress'] <= 10},
                    {'name': '并发评估', 'completed': st['progress'] > 85, 'current': 10 < st['progress'] <= 85},
                    {'name': '聚合统计', 'completed': st['progress'] > 95, 'current': 85 < st['progress'] <= 95},
                    {'name': '生成摘要', 'completed': st['progress'] >= 100, 'current': 95 < st['progress'] < 100},
                ]
                st['estimated_completion'] = None
                if st['progress'] >= 30 and not st['results']:
                    st['preview_results'] = {
                        'top_stocks': [
                            {'name': '预览A', 'symbol': 'PREV.A', 'score': 88.0},
                            {'name': '预览B', 'symbol': 'PREV.B', 'score': 85.5},
                        ]
                    }
            except Exception:
                pass

        def _runner():
            t0 = time.time()
            try:
                orch = self._Orchestrator(progress_cb=_progress_cb)
                ocfg = self._Cfg(
                    market_type=config.market_type,
                    preset_type=config.preset_type,
                    scan_depth=config.scan_depth,
                    budget_limit=config.budget_limit,
                    stock_limit=config.stock_limit,
                    time_range=config.time_range,
                    custom_filters=config.custom_filters,
                    analysis_focus=config.analysis_focus,
                    ai_model_config=config.ai_model_config,
                    advanced_options=config.advanced_options,
                )
                result = orch.run(ocfg)
                st = self._runs.get(run_id)
                if st is None:
                    return
                st['results'] = result
                st['status'] = ScanStatus.COMPLETED
                st['progress'] = 100
                st['latest_message'] = '完成'
                stats = result.get('stats', {})
                st['stats'].update(stats)
                st['stats']['scan_duration'] = stats.get('scan_duration') or f"{int(time.time()-t0)}秒"
                st['preview_results'] = None
            except Exception as e:
                st = self._runs.get(run_id)
                if st is None:
                    return
                st['status'] = ScanStatus.FAILED
                st['error_message'] = str(e)
                logger.error(f'本地扫描失败: {e}')

        th = threading.Thread(target=_runner, daemon=True)
        th.start()

        return {
            'success': True,
            'scan_id': run_id,
            'message': '扫描创建成功',
            'estimated_cost': config.stock_limit * 0.002,
            'estimated_duration': f"{max(1, int(config.stock_limit/10))}分钟",
        }

    def get_scan_status(self, scan_id: str) -> ScanProgress:
        st = self._runs.get(scan_id)
        if not st:
            raise APIError(f"扫描不存在: {scan_id}")
        return ScanProgress(
            scan_id=scan_id,
            status=st['status'],
            overall_progress=int(st.get('progress', 0)),
            current_stage=st.get('current_stage', ''),
            stages=st.get('stages', []),
            stats=st.get('stats', {}),
            latest_message=st.get('latest_message', ''),
            preview_results=st.get('preview_results'),
            error_message=st.get('error_message'),
            estimated_completion=st.get('estimated_completion'),
        )

    def get_scan_rankings(self, scan_id: str, **kwargs) -> List[Dict]:
        st = self._runs.get(scan_id)
        if not st or st['status'] != ScanStatus.COMPLETED or not st.get('results'):
            return []
        return st['results'].get('rankings', [])

    def get_sector_analysis(self, scan_id: str) -> Dict[str, Any]:
        st = self._runs.get(scan_id)
        if not st or st['status'] != ScanStatus.COMPLETED or not st.get('results'):
            return {}
        return st['results'].get('sectors', {})

    def get_market_breadth(self, scan_id: str) -> Dict[str, Any]:
        st = self._runs.get(scan_id)
        if not st or st['status'] != ScanStatus.COMPLETED or not st.get('results'):
            return {}
        return st['results'].get('breadth', {})

    def get_executive_summary(self, scan_id: str) -> Dict[str, Any]:
        st = self._runs.get(scan_id)
        if not st or st['status'] != ScanStatus.COMPLETED or not st.get('results'):
            return {}
        return st['results'].get('summary', {})

    def get_complete_results(self, scan_id: str) -> ScanResults:
        st = self._runs.get(scan_id)
        if not st or st['status'] != ScanStatus.COMPLETED or not st.get('results'):
            raise APIError('结果尚未准备好')
        res = st['results']
        stats = res.get('stats', {})
        return ScanResults(
            scan_id=scan_id,
            total_stocks=stats.get('total_stocks', 0),
            recommended_stocks=stats.get('recommended_stocks', 0),
            actual_cost=stats.get('actual_cost', 0.0),
            scan_duration=stats.get('scan_duration', '未知'),
            rankings=res.get('rankings', []),
            sectors=res.get('sectors', {}),
            breadth=res.get('breadth', {}),
            summary=res.get('summary', {}),
            created_at=datetime.now().isoformat()
        )

    def pause_scan(self, scan_id: str) -> bool:
        st = self._runs.get(scan_id)
        if not st:
            return False
        st['status'] = ScanStatus.PAUSED
        return True

    def resume_scan(self, scan_id: str) -> bool:
        st = self._runs.get(scan_id)
        if not st:
            return False
        if st['status'] == ScanStatus.PAUSED:
            st['status'] = ScanStatus.RUNNING
            return True
        return False

    def cancel_scan(self, scan_id: str) -> bool:
        st = self._runs.get(scan_id)
        if not st:
            return False
        st['status'] = ScanStatus.CANCELLED
        return True

    def health_check(self) -> bool:
        return True

def get_api_client(use_mock: bool = False, **kwargs) -> MarketAnalysisAPIClient:
    """
    获取API客户端实例
    - 当 use_mock=True 时，使用内置 Mock 客户端。
    - 当后端选择为 local（默认）时，使用本地编排客户端。
    - 否则回退到 HTTP 客户端（需要独立后端服务）。
    """

    if use_mock:
        return MockMarketAnalysisAPIClient()

    backend = os.getenv('MARKET_SCAN_BACKEND', 'local').lower()
    if backend == 'local':
        try:
            return LocalMarketAnalysisClient()
        except Exception as e:
            logger.warning(f"Local 后端初始化失败，回退HTTP: {e}")
            return MarketAnalysisAPIClient(**kwargs)

    return MarketAnalysisAPIClient(**kwargs)


# 示例用法
if __name__ == "__main__":
    # 使用模拟客户端测试
    with get_api_client(use_mock=True) as client:
        
        # 创建扫描配置
        config = MarketScanConfig(
            market_type="A股",
            preset_type="大盘蓝筹",
            scan_depth=3,
            budget_limit=10.0,
            stock_limit=100,
            time_range="1月"
        )
        
        # 创建扫描
        result = client.create_scan(config)
        print(f"创建扫描结果: {result}")
        
        scan_id = result['scan_id']
        
        # 检查进度
        while True:
            progress = client.get_scan_status(scan_id)
            print(f"扫描进度: {progress.overall_progress}%")
            
            if progress.status == ScanStatus.COMPLETED:
                break
            elif progress.status in [ScanStatus.FAILED, ScanStatus.CANCELLED]:
                print(f"扫描失败: {progress.error_message}")
                break
            
            time.sleep(2)
        
        # 获取结果
        if progress.status == ScanStatus.COMPLETED:
            results = client.get_complete_results(scan_id)
            print(f"扫描结果: {len(results.rankings)}只股票")
