"""
历史记录数据服务
聚合和处理分析历史数据
"""

import os
import json
import glob
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.history')


class HistoryService:
    """历史记录数据服务"""
    
    def __init__(self, data_dir: str = None):
        """初始化历史记录服务
        
        Args:
            data_dir: 数据目录路径，默认为项目根目录下的data文件夹
        """
        if data_dir is None:
            # 获取项目根目录
            current_dir = Path(__file__).parent.parent.parent
            data_dir = current_dir / "data"
        
        self.data_dir = Path(data_dir)
        self.results_dir = current_dir / "reports" if (current_dir / "reports").exists() else None
        
        logger.info(f"历史记录服务初始化 - 数据目录: {self.data_dir}")
    
    def get_analysis_history(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """获取分析历史记录
        
        Args:
            limit: 返回记录数量限制
            offset: 偏移量（用于分页）
            
        Returns:
            历史记录列表
        """
        records = []
        
        # 处理多模型协作结果文件
        multi_model_files = self._get_multi_model_files()
        for file_path in multi_model_files:
            try:
                record = self._parse_multi_model_file(file_path)
                if record:
                    records.append(record)
            except Exception as e:
                logger.warning(f"解析多模型文件失败 {file_path}: {e}")
        
        # 处理reports目录下的结果（如果存在）
        if self.results_dir and self.results_dir.exists():
            report_files = self._get_report_files()
            for file_path in report_files:
                try:
                    record = self._parse_report_file(file_path)
                    if record:
                        records.append(record)
                except Exception as e:
                    logger.warning(f"解析报告文件失败 {file_path}: {e}")
        
        # 按时间排序（降序）
        records.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # 分页
        total_count = len(records)
        start_idx = offset
        end_idx = offset + limit
        page_records = records[start_idx:end_idx]
        
        logger.info(f"获取历史记录: 总数={total_count}, 返回={len(page_records)}")
        return page_records
    
    def get_analysis_detail(self, analysis_id: str) -> Optional[Dict]:
        """获取分析详情
        
        Args:
            analysis_id: 分析ID
            
        Returns:
            分析详情数据
        """
        # 先在多模型结果中查找
        multi_model_files = self._get_multi_model_files()
        for file_path in multi_model_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('analysis_id') == analysis_id:
                        return data
            except Exception as e:
                logger.warning(f"读取文件失败 {file_path}: {e}")
        
        # 在报告目录中查找
        if self.results_dir and self.results_dir.exists():
            report_files = self._get_report_files()
            for file_path in report_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('analysis_id') == analysis_id or str(file_path.stem) == analysis_id:
                            return data
                except Exception as e:
                    logger.warning(f"读取报告文件失败 {file_path}: {e}")
        
        return None
    
    def delete_analysis(self, analysis_id: str) -> bool:
        """删除分析记录
        
        Args:
            analysis_id: 分析ID
            
        Returns:
            是否删除成功
        """
        deleted = False
        
        # 删除多模型结果文件
        multi_model_files = self._get_multi_model_files()
        for file_path in multi_model_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get('analysis_id') == analysis_id:
                        os.remove(file_path)
                        deleted = True
                        logger.info(f"删除多模型文件: {file_path}")
                        break
            except Exception as e:
                logger.warning(f"删除文件失败 {file_path}: {e}")
        
        # 删除报告文件（如果存在）
        if self.results_dir and self.results_dir.exists():
            report_files = self._get_report_files()
            for file_path in report_files:
                try:
                    if str(file_path.stem) == analysis_id:
                        os.remove(file_path)
                        deleted = True
                        logger.info(f"删除报告文件: {file_path}")
                        break
                except Exception as e:
                    logger.warning(f"删除报告文件失败 {file_path}: {e}")
        
        return deleted
    
    def get_statistics(self) -> Dict:
        """获取历史统计数据
        
        Returns:
            统计信息字典
        """
        records = self.get_analysis_history(limit=10000)  # 获取所有记录用于统计
        
        total_count = len(records)
        
        # 按市场统计
        market_stats = {}
        mode_stats = {}
        model_stats = {}
        
        for record in records:
            # 市场统计
            market = record.get('market_type', '未知')
            market_stats[market] = market_stats.get(market, 0) + 1
            
            # 模式统计
            mode = record.get('analysis_mode', '未知')
            mode_stats[mode] = mode_stats.get(mode, 0) + 1
            
            # 模型统计
            model = record.get('model_provider', '未知')
            model_stats[model] = model_stats.get(model, 0) + 1
        
        # 时间统计（最近7天、30天）
        now = datetime.now()
        recent_7_days = 0
        recent_30_days = 0
        
        for record in records:
            try:
                record_time = datetime.fromisoformat(record.get('timestamp', '').replace('Z', '+00:00').replace('+00:00', ''))
                days_ago = (now - record_time).days
                
                if days_ago <= 7:
                    recent_7_days += 1
                if days_ago <= 30:
                    recent_30_days += 1
            except:
                pass
        
        return {
            'total_analyses': total_count,
            'recent_7_days': recent_7_days,
            'recent_30_days': recent_30_days,
            'market_distribution': market_stats,
            'mode_distribution': mode_stats,
            'model_distribution': model_stats
        }
    
    def search_analyses(self, **filters) -> List[Dict]:
        """搜索分析记录
        
        Args:
            **filters: 搜索过滤条件
                - stock_symbol: 股票代码
                - market_type: 市场类型
                - analysis_mode: 分析模式
                - start_date: 开始日期
                - end_date: 结束日期
                
        Returns:
            匹配的记录列表
        """
        records = self.get_analysis_history(limit=10000)
        
        filtered_records = []
        
        for record in records:
            # 股票代码过滤
            if filters.get('stock_symbol'):
                if record.get('stock_symbol', '').upper() != filters['stock_symbol'].upper():
                    continue
            
            # 市场类型过滤
            if filters.get('market_type'):
                if record.get('market_type') != filters['market_type']:
                    continue
            
            # 分析模式过滤
            if filters.get('analysis_mode'):
                if record.get('analysis_mode') != filters['analysis_mode']:
                    continue
            
            # 日期范围过滤
            if filters.get('start_date') or filters.get('end_date'):
                try:
                    record_date = datetime.fromisoformat(record.get('timestamp', '').replace('Z', '+00:00').replace('+00:00', '')).date()
                    
                    if filters.get('start_date'):
                        start_date = datetime.strptime(filters['start_date'], '%Y-%m-%d').date()
                        if record_date < start_date:
                            continue
                    
                    if filters.get('end_date'):
                        end_date = datetime.strptime(filters['end_date'], '%Y-%m-%d').date()
                        if record_date > end_date:
                            continue
                except:
                    continue
            
            filtered_records.append(record)
        
        logger.info(f"搜索历史记录: 过滤器={filters}, 结果数量={len(filtered_records)}")
        return filtered_records
    
    def _get_multi_model_files(self) -> List[Path]:
        """获取多模型结果文件列表"""
        pattern = self.data_dir / "multi_model_results_*.json"
        files = list(glob.glob(str(pattern)))
        return [Path(f) for f in files]
    
    def _get_report_files(self) -> List[Path]:
        """获取报告文件列表"""
        if not self.results_dir or not self.results_dir.exists():
            return []
        
        files = []
        # 搜索JSON格式的报告文件
        for pattern in ["*.json", "*/*.json", "*/*/*.json"]:
            found_files = glob.glob(str(self.results_dir / pattern))
            files.extend([Path(f) for f in found_files])
        
        return files
    
    def _parse_multi_model_file(self, file_path: Path) -> Optional[Dict]:
        """解析多模型协作结果文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            analysis_data = data.get('results', {}).get('analysis_data', {})
            results = data.get('results', {}).get('results', {})
            
            # 提取核心信息
            record = {
                'analysis_id': data.get('analysis_id', file_path.stem),
                'timestamp': self._extract_timestamp_from_filename(file_path.name),
                'stock_symbol': analysis_data.get('stock_symbol', '未知'),
                'market_type': analysis_data.get('market_type', '未知'),
                'analysis_mode': '多模型协作',
                'research_depth': analysis_data.get('research_depth', 0),
                'model_provider': 'Mixed',
                'status': data.get('status', 'unknown'),
                'agents_used': data.get('results', {}).get('agents_used', []),
                'file_path': str(file_path)
            }
            
            # 提取投资建议摘要
            summary = self._extract_investment_summary(results)
            if summary:
                record.update(summary)
            
            return record
            
        except Exception as e:
            logger.error(f"解析多模型文件失败 {file_path}: {e}")
            return None
    
    def _parse_report_file(self, file_path: Path) -> Optional[Dict]:
        """解析报告文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 这里需要根据实际报告文件格式来解析
            # 暂时返回基础结构
            record = {
                'analysis_id': file_path.stem,
                'timestamp': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'stock_symbol': data.get('stock_symbol', '未知'),
                'market_type': data.get('market_type', '未知'),
                'analysis_mode': '单模型分析',
                'file_path': str(file_path)
            }
            
            return record
            
        except Exception as e:
            logger.error(f"解析报告文件失败 {file_path}: {e}")
            return None
    
    def _extract_timestamp_from_filename(self, filename: str) -> str:
        """从文件名中提取时间戳"""
        try:
            # 文件名格式: multi_model_results_multi_model_id_20250808_145915.json
            parts = filename.split('_')
            if len(parts) >= 6:
                date_part = parts[-2]  # 20250808
                time_part = parts[-1].replace('.json', '')  # 145915
                
                # 转换为ISO格式
                datetime_str = f"{date_part}T{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                dt = datetime.strptime(datetime_str, "%Y%m%dT%H:%M:%S")
                return dt.isoformat()
        except:
            pass
        
        # 如果解析失败，返回文件修改时间
        try:
            file_path = Path(filename)
            if file_path.exists():
                return datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        except:
            pass
        
        return datetime.now().isoformat()
    
    def _extract_investment_summary(self, results: Dict) -> Dict:
        """从分析结果中提取投资建议摘要"""
        summary = {}
        
        try:
            # 尝试从各个智能体结果中提取关键信息
            for agent_name, agent_result in results.items():
                if isinstance(agent_result, dict):
                    # 提取置信度
                    if 'confidence' in agent_result:
                        summary['confidence'] = agent_result['confidence']
                    
                    # 提取投资建议关键词
                    analysis = agent_result.get('analysis', '')
                    recommendations = agent_result.get('recommendations', '')
                    
                    # 简单的关键词提取逻辑
                    text_to_analyze = f"{analysis} {recommendations}".lower()
                    
                    if '买入' in text_to_analyze or 'buy' in text_to_analyze:
                        summary['action'] = '买入'
                    elif '卖出' in text_to_analyze or 'sell' in text_to_analyze:
                        summary['action'] = '卖出'
                    elif '持有' in text_to_analyze or 'hold' in text_to_analyze:
                        summary['action'] = '持有'
                    
                    # 提取风险评级关键词
                    if '高风险' in text_to_analyze:
                        summary['risk_level'] = '高'
                    elif '中风险' in text_to_analyze:
                        summary['risk_level'] = '中'
                    elif '低风险' in text_to_analyze:
                        summary['risk_level'] = '低'
        except Exception as e:
            logger.warning(f"提取投资建议摘要失败: {e}")
        
        return summary