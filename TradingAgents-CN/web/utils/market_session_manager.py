"""
Market Session Manager
市场分析会话管理器 - 管理分析状态、历史记录和实时更新
"""

import json
import os
import time
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import streamlit as st

from tradingagents.utils.logging_manager import get_logger
from utils.market_api_client import MarketAnalysisAPIClient, MarketScanConfig, ScanStatus, get_api_client

logger = get_logger('market_session_manager')


@dataclass
class ScanSession:
    """分析会话信息"""
    scan_id: str
    config: Dict[str, Any]
    status: str
    created_at: str
    updated_at: str
    progress: int = 0
    error_message: Optional[str] = None
    results_available: bool = False
    results_summary: Optional[Dict] = None


class MarketSessionManager:
    """市场分析会话管理器"""
    
    def __init__(self, data_dir: str = "./data/market_sessions", use_mock_api: bool = True):
        """
        初始化会话管理器
        
        Args:
            data_dir: 数据存储目录
            use_mock_api: 是否使用模拟API
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions_file = self.data_dir / "sessions.json"
        self.results_dir = self.data_dir / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # 标记是否使用模拟API（影响恢复策略）
        self.use_mock_api = use_mock_api

        # API客户端
        self.api_client = get_api_client(use_mock=use_mock_api)
        
        # 活跃会话缓存
        self._active_sessions: Dict[str, ScanSession] = {}
        self._update_threads: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event] = {}
        
        # 加载历史会话
        self._load_sessions()

        # 若为模拟API，避免恢复不可复原的“运行中”会话，防止进度轮询报错
        if self.use_mock_api:
            self._sanitize_sessions_on_mock()
        
        logger.info(f"初始化市场会话管理器，数据目录: {data_dir}")
    
    def create_scan_session(self, config: Dict[str, Any]) -> str:
        """
        创建新的扫描会话
        
        Args:
            config: 扫描配置
            
        Returns:
            str: 扫描会话ID
            
        Raises:
            Exception: 创建失败
        """
        
        try:
            # 构建API配置对象
            scan_config = MarketScanConfig(
                market_type=config['market_type'],
                preset_type=config['preset_type'],
                scan_depth=config['scan_depth'],
                budget_limit=config['budget_limit'],
                stock_limit=config['stock_limit'],
                time_range=config['time_range'],
                custom_filters=config.get('custom_filters'),
                analysis_focus=config.get('analysis_focus'),
                ai_model_config=config.get('ai_model_config'),
                advanced_options=config.get('advanced_options')
            )
            
            # 调用API创建扫描
            api_result = self.api_client.create_scan(scan_config)
            scan_id = api_result['scan_id']
            
            # 创建会话记录
            session = ScanSession(
                scan_id=scan_id,
                config=config,
                status=ScanStatus.RUNNING.value,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                progress=0
            )
            
            # 缓存会话
            self._active_sessions[scan_id] = session
            
            # 启动进度更新线程
            self._start_progress_update_thread(scan_id)
            
            # 保存到文件
            self._save_sessions()
            
            logger.info(f"创建扫描会话成功: {scan_id}")
            return scan_id
            
        except Exception as e:
            logger.error(f"创建扫描会话失败: {e}")
            raise
    
    def get_session_progress(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话进度信息
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            Optional[Dict]: 进度信息，不存在返回None
        """
        
        if scan_id not in self._active_sessions:
            return None
        
        session = self._active_sessions[scan_id]
        
        try:
            # 从API获取最新进度
            progress = self.api_client.get_scan_status(scan_id)
            
            # 更新会话信息
            session.status = progress.status.value
            session.progress = progress.overall_progress
            session.updated_at = datetime.now().isoformat()
            
            if progress.status == ScanStatus.COMPLETED:
                session.results_available = True
                # 获取结果摘要
                try:
                    summary = self.api_client.get_executive_summary(scan_id)
                    session.results_summary = summary
                except Exception as e:
                    logger.warning(f"获取结果摘要失败: {e}")
            elif progress.status == ScanStatus.FAILED:
                session.error_message = progress.error_message
            
            # 持久化会话变更，确保历史列表可显示结果/状态
            try:
                self._save_sessions()
            except Exception as _e:
                logger.debug(f"保存会话数据失败（忽略）：{_e}")
            
            # 返回进度信息
            return {
                'scan_id': scan_id,
                'status': session.status,
                'overall_progress': progress.overall_progress,
                'current_stage': progress.current_stage,
                'stages': progress.stages,
                'stats': progress.stats,
                'latest_message': progress.latest_message,
                'preview_results': progress.preview_results,
                'error_message': progress.error_message,
                'estimated_completion': progress.estimated_completion,
                'session_info': {
                    'created_at': session.created_at,
                    'updated_at': session.updated_at,
                    'config': session.config
                }
            }
            
        except Exception as e:
            msg = str(e)
            # 对于“未找到”类错误降低噪声级别
            if '扫描不存在' in msg or 'not found' in msg.lower():
                logger.warning(f"获取扫描进度失败: {msg}")
            else:
                logger.error(f"获取扫描进度失败: {msg}")

            # 如果是模拟API下的“扫描不存在”，视为过期/失联的扫描ID，做优雅清理
            if '扫描不存在' in msg or 'not found' in msg.lower():
                # 停止更新线程并从活跃列表移除
                try:
                    self._stop_progress_update_thread(scan_id)
                except Exception:
                    pass
                if scan_id in self._active_sessions:
                    del self._active_sessions[scan_id]
                    self._save_sessions()
                    # 同步从历史记录移除，避免下次重载再次恢复为“running”
                    try:
                        self._remove_session_from_history(scan_id)
                    except Exception:
                        pass

                # 同步清理 Streamlit 会话状态（若引用的是该ID）
                try:
                    if st.session_state.get('current_market_scan_id') == scan_id:
                        st.session_state.current_market_scan_id = None
                        st.session_state.market_scan_running = False
                except Exception:
                    pass

                return {
                    'scan_id': scan_id,
                    'status': 'not_found',
                    'error_message': msg
                }

            return {
                'scan_id': scan_id,
                'status': 'error',
                'error_message': msg
            }
    
    def get_session_results(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话的完整结果
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            Optional[Dict]: 扫描结果，不存在或未完成返回None
        """
        
        if scan_id not in self._active_sessions:
            return None
        
        session = self._active_sessions[scan_id]
        
        if not session.results_available:
            return None
        
        try:
            # 检查本地缓存的结果
            results_file = self.results_dir / f"{scan_id}_results.json"
            
            if results_file.exists():
                # 从本地文件加载结果
                with open(results_file, 'r', encoding='utf-8') as f:
                    cached_results = json.load(f)
                
                # 检查缓存是否过期（1小时）
                cached_time = datetime.fromisoformat(cached_results.get('cached_at', ''))
                if datetime.now() - cached_time < timedelta(hours=1):
                    logger.info(f"使用缓存的扫描结果: {scan_id}")
                    return cached_results.get('results')
            
            # 从API获取完整结果
            complete_results = self.api_client.get_complete_results(scan_id)
            
            # 转换为字典格式
            results_dict = {
                'scan_id': complete_results.scan_id,
                'total_stocks': complete_results.total_stocks,
                'recommended_stocks': complete_results.recommended_stocks,
                'actual_cost': complete_results.actual_cost,
                'scan_duration': complete_results.scan_duration,
                'rankings': complete_results.rankings,
                'sectors': complete_results.sectors,
                'breadth': complete_results.breadth,
                'summary': complete_results.summary,
                'created_at': complete_results.created_at
            }
            
            # 缓存结果到本地
            cache_data = {
                'results': results_dict,
                'cached_at': datetime.now().isoformat()
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"获取并缓存扫描结果: {scan_id}")
            return results_dict
            
        except Exception as e:
            logger.error(f"获取扫描结果失败: {e}")
            return None
    
    def pause_scan(self, scan_id: str) -> bool:
        """暂停扫描"""
        
        try:
            success = self.api_client.pause_scan(scan_id)
            
            if success and scan_id in self._active_sessions:
                self._active_sessions[scan_id].status = ScanStatus.PAUSED.value
                self._active_sessions[scan_id].updated_at = datetime.now().isoformat()
                self._save_sessions()
            
            return success
            
        except Exception as e:
            logger.error(f"暂停扫描失败: {e}")
            return False
    
    def resume_scan(self, scan_id: str) -> bool:
        """继续扫描"""
        
        try:
            success = self.api_client.resume_scan(scan_id)
            
            if success and scan_id in self._active_sessions:
                self._active_sessions[scan_id].status = ScanStatus.RUNNING.value
                self._active_sessions[scan_id].updated_at = datetime.now().isoformat()
                self._save_sessions()
                
                # 重新启动进度更新线程
                self._start_progress_update_thread(scan_id)
            
            return success
            
        except Exception as e:
            logger.error(f"继续扫描失败: {e}")
            return False
    
    def cancel_scan(self, scan_id: str) -> bool:
        """取消扫描"""
        
        try:
            success = self.api_client.cancel_scan(scan_id)
            
            if success and scan_id in self._active_sessions:
                self._active_sessions[scan_id].status = ScanStatus.CANCELLED.value
                self._active_sessions[scan_id].updated_at = datetime.now().isoformat()
                self._save_sessions()
                
                # 停止进度更新线程
                self._stop_progress_update_thread(scan_id)
            
            return success
            
        except Exception as e:
            logger.error(f"取消扫描失败: {e}")
            return False
    
    def get_active_sessions(self) -> List[ScanSession]:
        """获取所有活跃会话"""
        return list(self._active_sessions.values())
    
    def get_session_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取会话历史记录
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 历史记录列表
        """
        
        try:
            if not self.sessions_file.exists():
                return []
            
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                all_sessions = json.load(f)
            
            # 按创建时间排序
            sorted_sessions = sorted(
                all_sessions,
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            return sorted_sessions[:limit]
            
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            return []
    
    def delete_session(self, scan_id: str) -> bool:
        """
        删除会话及其结果
        
        Args:
            scan_id: 扫描ID
            
        Returns:
            bool: 是否删除成功
        """
        
        try:
            # 停止相关线程
            self._stop_progress_update_thread(scan_id)
            
            # 从活跃会话中移除
            if scan_id in self._active_sessions:
                del self._active_sessions[scan_id]
            
            # 删除结果文件
            results_file = self.results_dir / f"{scan_id}_results.json"
            if results_file.exists():
                results_file.unlink()
            
            # 从历史记录中删除
            self._remove_session_from_history(scan_id)
            
            logger.info(f"删除扫描会话成功: {scan_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除扫描会话失败: {e}")
            return False
    
    def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        清理过期会话
        
        Args:
            days: 保留天数
            
        Returns:
            int: 清理的会话数量
        """
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cleaned_count = 0
            
            # 获取所有历史会话
            history = self.get_session_history(limit=1000)
            
            for session_data in history:
                try:
                    created_at = datetime.fromisoformat(session_data['created_at'])
                    if created_at < cutoff_date:
                        scan_id = session_data['scan_id']
                        self.delete_session(scan_id)
                        cleaned_count += 1
                except Exception as e:
                    logger.warning(f"清理会话时出错: {e}")
                    continue
            
            logger.info(f"清理过期会话完成，清理数量: {cleaned_count}")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理过期会话失败: {e}")
            return 0
    
    def export_session_data(self, scan_id: str, format_type: str = "json") -> Optional[str]:
        """
        导出会话数据
        
        Args:
            scan_id: 扫描ID
            format_type: 导出格式
            
        Returns:
            Optional[str]: 导出文件路径
        """
        
        try:
            session_data = self.get_session_results(scan_id)
            if not session_data:
                return None
            
            export_dir = self.data_dir / "exports"
            export_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{scan_id}_{timestamp}.{format_type}"
            export_file = export_dir / filename
            
            if format_type.lower() == "json":
                with open(export_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
            else:
                # 其他格式可以后续扩展
                raise ValueError(f"不支持的导出格式: {format_type}")
            
            logger.info(f"导出会话数据成功: {export_file}")
            return str(export_file)
            
        except Exception as e:
            logger.error(f"导出会话数据失败: {e}")
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态信息"""
        
        return {
            'active_sessions_count': len(self._active_sessions),
            'running_threads_count': len(self._update_threads),
            'api_health': self.api_client.health_check() if hasattr(self.api_client, 'health_check') else True,
            'data_dir': str(self.data_dir),
            'last_cleanup': self._get_last_cleanup_time()
        }
    
    def close(self):
        """关闭会话管理器"""
        
        try:
            # 停止所有更新线程
            for scan_id in list(self._stop_flags.keys()):
                self._stop_progress_update_thread(scan_id)
            
            # 保存会话状态
            self._save_sessions()
            
            # 关闭API客户端
            if hasattr(self.api_client, 'close'):
                self.api_client.close()
            
            logger.info("市场会话管理器已关闭")
            
        except Exception as e:
            logger.error(f"关闭会话管理器时出错: {e}")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
    
    # 私有方法
    def _load_sessions(self):
        """从文件加载会话数据"""
        
        try:
            if not self.sessions_file.exists():
                return
            
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
            
            for session_data in sessions_data:
                scan_id = session_data['scan_id']
                status = session_data.get('status', 'unknown')

                # 只加载未完成的会话到活跃列表
                if status in ['running', 'paused']:
                    session = ScanSession(**session_data)
                    # 对于模拟API，跳过“running”会话的恢复（mock状态不可持久化）
                    if self.use_mock_api and status == 'running':
                        continue
                    self._active_sessions[scan_id] = session
                    
                    # 如果是运行状态，启动进度更新线程
                    if status == 'running':
                        self._start_progress_update_thread(scan_id)
            
            logger.info(f"加载会话数据完成，活跃会话数: {len(self._active_sessions)}")
            
        except Exception as e:
            logger.error(f"加载会话数据失败: {e}")

    def _sanitize_sessions_on_mock(self) -> None:
        """模拟API下的会话恢复策略：
        - 跳过恢复运行中的会话，避免因Mock客户端无历史而报“扫描不存在”。
        - 将持久化文件中处于running的会话标记为cancelled，写回文件。
        """
        try:
            if not self.sessions_file.exists():
                return
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions = json.load(f)

            changed = False
            for s in sessions:
                if s.get('status') == 'running':
                    s['status'] = 'cancelled'
                    s['updated_at'] = datetime.now().isoformat()
                    s['error_message'] = (
                        s.get('error_message') or '模拟API会话在应用重启后不可恢复，已标记为已取消'
                    )
                    changed = True

            if changed:
                with open(self.sessions_file, 'w', encoding='utf-8') as f:
                    json.dump(sessions, f, ensure_ascii=False, indent=2)
                logger.info('已在模拟API模式下清理无法恢复的运行中会话')
        except Exception as e:
            logger.warning(f"模拟API会话清理失败: {e}")
    
    def _save_sessions(self):
        """保存会话数据到文件"""
        
        try:
            # 获取所有历史会话
            existing_sessions = []
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    existing_sessions = json.load(f)
            
            # 更新活跃会话的数据
            existing_sessions_dict = {s['scan_id']: s for s in existing_sessions}
            
            for scan_id, session in self._active_sessions.items():
                existing_sessions_dict[scan_id] = asdict(session)
            
            # 保存到文件
            updated_sessions = list(existing_sessions_dict.values())
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(updated_sessions, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"保存会话数据失败: {e}")
    
    def _start_progress_update_thread(self, scan_id: str):
        """启动进度更新线程"""
        
        if scan_id in self._update_threads:
            # 如果线程已存在，先停止
            self._stop_progress_update_thread(scan_id)
        
        # 创建停止事件
        stop_flag = threading.Event()
        self._stop_flags[scan_id] = stop_flag
        
        # 创建并启动线程
        thread = threading.Thread(
            target=self._progress_update_worker,
            args=(scan_id, stop_flag),
            daemon=True
        )
        
        self._update_threads[scan_id] = thread
        thread.start()
        
        logger.info(f"启动进度更新线程: {scan_id}")
    
    def _stop_progress_update_thread(self, scan_id: str):
        """停止进度更新线程"""
        
        if scan_id in self._stop_flags:
            self._stop_flags[scan_id].set()
            del self._stop_flags[scan_id]
        
        if scan_id in self._update_threads:
            thread = self._update_threads[scan_id]
            # 等待线程结束（最多5秒）
            thread.join(timeout=5)
            del self._update_threads[scan_id]
        
        logger.info(f"停止进度更新线程: {scan_id}")
    
    def _progress_update_worker(self, scan_id: str, stop_flag: threading.Event):
        """进度更新工作线程"""
        
        try:
            while not stop_flag.is_set():
                try:
                    # 获取最新进度
                    progress_info = self.get_session_progress(scan_id)
                    
                    if not progress_info:
                        break
                    
                    status = progress_info.get('status', '')
                    
                    # 如果扫描完成/失败/取消/不存在，停止线程
                    if status in ['completed', 'failed', 'cancelled', 'not_found']:
                        break
                    
                    # 更新会话状态
                    if scan_id in self._active_sessions:
                        session = self._active_sessions[scan_id]
                        session.status = status
                        session.progress = progress_info.get('overall_progress', 0)
                        session.updated_at = datetime.now().isoformat()
                        
                        if status == 'failed':
                            session.error_message = progress_info.get('error_message')
                        elif status == 'completed':
                            session.results_available = True
                    
                    # 等待5秒后再次检查
                    if stop_flag.wait(5):
                        break
                        
                except Exception as e:
                    logger.error(f"进度更新线程出错: {e}")
                    time.sleep(5)  # 出错时等待更长时间
            
            logger.info(f"进度更新线程结束: {scan_id}")
            
        except Exception as e:
            logger.error(f"进度更新线程异常退出: {e}")
    
    def _remove_session_from_history(self, scan_id: str):
        """从历史记录中移除会话"""
        
        try:
            if not self.sessions_file.exists():
                return
            
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                sessions = json.load(f)
            
            # 过滤掉要删除的会话
            updated_sessions = [s for s in sessions if s.get('scan_id') != scan_id]
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(updated_sessions, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logger.error(f"从历史记录移除会话失败: {e}")
    
    def _get_last_cleanup_time(self) -> Optional[str]:
        """获取最后清理时间"""
        
        try:
            cleanup_file = self.data_dir / "last_cleanup.txt"
            if cleanup_file.exists():
                return cleanup_file.read_text().strip()
        except Exception:
            pass
        return None


# Streamlit 集成辅助函数
def init_market_session_state():
    """初始化Streamlit会话状态"""
    
    if 'market_session_manager' not in st.session_state:
        # 允许通过环境变量切换是否使用模拟API（默认True以便开发演示）
        use_mock = os.getenv('MARKET_SCAN_USE_MOCK', 'true').lower() in ['1', 'true', 'yes', 'on']
        st.session_state.market_session_manager = MarketSessionManager(use_mock_api=use_mock)
    
    if 'current_market_scan_id' not in st.session_state:
        st.session_state.current_market_scan_id = None
    
    if 'market_scan_results' not in st.session_state:
        st.session_state.market_scan_results = None
    
    if 'market_scan_running' not in st.session_state:
        st.session_state.market_scan_running = False
    
    if 'auto_refresh_enabled' not in st.session_state:
        st.session_state.auto_refresh_enabled = False


def get_market_session_manager() -> MarketSessionManager:
    """获取市场会话管理器实例"""
    
    init_market_session_state()
    return st.session_state.market_session_manager


def cleanup_market_session_state():
    """清理Streamlit会话状态"""
    
    if 'market_session_manager' in st.session_state:
        try:
            st.session_state.market_session_manager.close()
        except Exception as e:
            logger.error(f"关闭会话管理器时出错: {e}")
        
        del st.session_state.market_session_manager


# 示例用法
if __name__ == "__main__":
    # 测试会话管理器
    with MarketSessionManager(use_mock_api=True) as manager:
        
        # 创建测试配置
        test_config = {
            'market_type': 'A股',
            'preset_type': '大盘蓝筹',
            'scan_depth': 3,
            'budget_limit': 10.0,
            'stock_limit': 100,
            'time_range': '1月'
        }
        
        # 创建扫描会话
        scan_id = manager.create_scan_session(test_config)
        print(f"创建扫描会话: {scan_id}")
        
        # 监控进度
        for i in range(10):
            progress = manager.get_session_progress(scan_id)
            if progress:
                print(f"进度: {progress['overall_progress']}% - {progress['latest_message']}")
                
                if progress['status'] == 'completed':
                    results = manager.get_session_results(scan_id)
                    if results:
                        print(f"扫描完成，发现{len(results['rankings'])}只股票")
                    break
                elif progress['status'] in ['failed', 'cancelled']:
                    print(f"扫描{progress['status']}: {progress.get('error_message', '')}")
                    break
            
            time.sleep(2)
        
        # 显示系统状态
        status = manager.get_system_status()
        print(f"系统状态: {status}")
