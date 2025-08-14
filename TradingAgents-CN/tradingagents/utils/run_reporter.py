#!/usr/bin/env python3
"""
调度器运行报告工具
用于生成结构化的调度器执行报告和性能指标
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class DigestRunReport:
    """摘要运行报告数据结构"""
    run_id: str
    trigger_type: str
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: str = "running"  # running, completed, failed, cancelled
    subscriptions_processed: int = 0
    symbols_analyzed: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    total_cost: float = 0.0
    attachments_generated: List[str] = None
    errors: List[str] = None
    performance_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attachments_generated is None:
            self.attachments_generated = []
        if self.errors is None:
            self.errors = []
        if self.performance_metrics is None:
            self.performance_metrics = {}

class RunReportManager:
    """运行报告管理器"""
    
    def __init__(self, reports_dir: str = None):
        if reports_dir is None:
            reports_dir = Path(__file__).parent.parent.parent / "data" / "scheduler_runs"
        
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def create_run_report(self, trigger_type: str, trigger_data: Dict = None) -> str:
        """创建新的运行报告"""
        run_id = f"{trigger_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}"
        
        report = DigestRunReport(
            run_id=run_id,
            trigger_type=trigger_type,
            start_time=datetime.now().isoformat(),
            status="running"
        )
        
        # 添加触发器数据到性能指标
        if trigger_data:
            report.performance_metrics['trigger_data'] = trigger_data
        
        self._save_report(report)
        return run_id
    
    def update_run_report(self, run_id: str, **updates) -> bool:
        """更新运行报告"""
        try:
            report = self._load_report(run_id)
            if not report:
                return False
            
            # 更新字段
            for key, value in updates.items():
                if hasattr(report, key):
                    setattr(report, key, value)
            
            # 自动计算持续时间
            if report.end_time and report.start_time:
                start_dt = datetime.fromisoformat(report.start_time)
                end_dt = datetime.fromisoformat(report.end_time)
                report.duration_seconds = (end_dt - start_dt).total_seconds()
            
            self._save_report(report)
            return True
            
        except Exception as e:
            print(f"更新运行报告失败: {e}")
            return False
    
    def complete_run_report(self, run_id: str, status: str = "completed", 
                          subscriptions: int = 0, symbols: int = 0,
                          emails_sent: int = 0, emails_failed: int = 0,
                          total_cost: float = 0.0, attachments: List[str] = None,
                          errors: List[str] = None) -> bool:
        """完成运行报告"""
        updates = {
            'end_time': datetime.now().isoformat(),
            'status': status,
            'subscriptions_processed': subscriptions,
            'symbols_analyzed': symbols,
            'emails_sent': emails_sent,
            'emails_failed': emails_failed,
            'total_cost': total_cost
        }
        
        if attachments:
            updates['attachments_generated'] = attachments
        if errors:
            updates['errors'] = errors
        
        return self.update_run_report(run_id, **updates)
    
    def add_error(self, run_id: str, error: str) -> bool:
        """向运行报告添加错误"""
        try:
            report = self._load_report(run_id)
            if report:
                report.errors.append(f"{datetime.now().isoformat()}: {error}")
                self._save_report(report)
                return True
            return False
        except Exception:
            return False
    
    def add_performance_metric(self, run_id: str, metric_name: str, value: Any) -> bool:
        """添加性能指标"""
        try:
            report = self._load_report(run_id)
            if report:
                report.performance_metrics[metric_name] = value
                self._save_report(report)
                return True
            return False
        except Exception:
            return False
    
    def get_recent_reports(self, limit: int = 10) -> List[Dict]:
        """获取最近的运行报告"""
        try:
            report_files = sorted(
                self.reports_dir.glob("*.json"), 
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )[:limit]
            
            reports = []
            for file_path in report_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reports.append(json.load(f))
                except Exception as e:
                    print(f"读取报告文件失败 {file_path}: {e}")
            
            return reports
            
        except Exception as e:
            print(f"获取最近报告失败: {e}")
            return []
    
    def get_statistics_summary(self, days: int = 7) -> Dict:
        """获取统计摘要"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            recent_reports = []
            for file_path in self.reports_dir.glob("*.json"):
                if file_path.stat().st_mtime >= cutoff_date.timestamp():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            recent_reports.append(json.load(f))
                    except Exception:
                        continue
            
            if not recent_reports:
                return {'total_runs': 0, 'period_days': days}
            
            # 计算统计信息
            stats = {
                'period_days': days,
                'total_runs': len(recent_reports),
                'successful_runs': len([r for r in recent_reports if r.get('status') == 'completed']),
                'failed_runs': len([r for r in recent_reports if r.get('status') == 'failed']),
                'total_emails_sent': sum(r.get('emails_sent', 0) for r in recent_reports),
                'total_emails_failed': sum(r.get('emails_failed', 0) for r in recent_reports),
                'total_subscriptions_processed': sum(r.get('subscriptions_processed', 0) for r in recent_reports),
                'total_symbols_analyzed': sum(r.get('symbols_analyzed', 0) for r in recent_reports),
                'total_cost': sum(r.get('total_cost', 0) for r in recent_reports),
                'average_duration': 0,
                'success_rate': 0
            }
            
            # 计算平均持续时间
            durations = [r.get('duration_seconds', 0) for r in recent_reports if r.get('duration_seconds')]
            if durations:
                stats['average_duration'] = sum(durations) / len(durations)
            
            # 计算成功率
            if stats['total_runs'] > 0:
                stats['success_rate'] = stats['successful_runs'] / stats['total_runs']
            
            return stats
            
        except Exception as e:
            print(f"获取统计摘要失败: {e}")
            return {'error': str(e)}
    
    def cleanup_old_reports(self, days: int = 30) -> int:
        """清理旧的报告文件"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            cleaned_count = 0
            for file_path in self.reports_dir.glob("*.json"):
                if file_path.stat().st_mtime < cutoff_date.timestamp():
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except Exception as e:
                        print(f"删除报告文件失败 {file_path}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            print(f"清理旧报告失败: {e}")
            return 0
    
    def _load_report(self, run_id: str) -> Optional[DigestRunReport]:
        """加载运行报告"""
        try:
            report_file = self.reports_dir / f"{run_id}.json"
            if not report_file.exists():
                return None
            
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return DigestRunReport(**data)
            
        except Exception as e:
            print(f"加载运行报告失败: {e}")
            return None
    
    def _save_report(self, report: DigestRunReport) -> bool:
        """保存运行报告"""
        try:
            report_file = self.reports_dir / f"{report.run_id}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"保存运行报告失败: {e}")
            return False

# 全局实例
_run_report_manager = None

def get_run_report_manager() -> RunReportManager:
    """获取全局运行报告管理器实例"""
    global _run_report_manager
    if _run_report_manager is None:
        _run_report_manager = RunReportManager()
    return _run_report_manager

def create_digest_run_report(trigger_type: str, trigger_data: Dict = None) -> str:
    """便捷函数：创建摘要运行报告"""
    manager = get_run_report_manager()
    return manager.create_run_report(trigger_type, trigger_data)

def complete_digest_run_report(run_id: str, **kwargs) -> bool:
    """便捷函数：完成摘要运行报告"""
    manager = get_run_report_manager()
    return manager.complete_run_report(run_id, **kwargs)

def add_run_error(run_id: str, error: str) -> bool:
    """便捷函数：添加运行错误"""
    manager = get_run_report_manager()
    return manager.add_error(run_id, error)

if __name__ == "__main__":
    # 测试代码
    print("🧪 测试运行报告管理器")
    
    manager = RunReportManager()
    
    # 创建测试报告
    run_id = manager.create_run_report("daily", {"test": True})
    print(f"创建报告: {run_id}")
    
    # 更新报告
    manager.add_performance_metric(run_id, "test_metric", 42)
    manager.add_error(run_id, "测试错误")
    
    # 完成报告
    manager.complete_run_report(
        run_id, "completed",
        subscriptions=5, symbols=10, emails_sent=3,
        total_cost=1.25, attachments=["test.pdf", "test.html"]
    )
    
    # 获取统计信息
    stats = manager.get_statistics_summary()
    print(f"统计信息: {stats}")
    
    # 获取最近报告
    recent = manager.get_recent_reports(5)
    print(f"最近报告数量: {len(recent)}")
    
    print("✅ 测试完成")