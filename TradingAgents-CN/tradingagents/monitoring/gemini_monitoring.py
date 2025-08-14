#!/usr/bin/env python3
"""
Gemini Analysis Monitoring Script
Real-time monitoring of Gemini model performance, cost effectiveness, and parameter optimization
"""

import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict, deque

from tradingagents.utils.logging_manager import get_logger
from tradingagents.config.config_manager import config_manager, token_tracker
from tradingagents.config.enhanced_gemini_config import enhanced_gemini_config

logger = get_logger('gemini_monitor')


class ParameterEffectivenessTracker:
    """Track the effectiveness of different parameter sets over time"""
    
    def __init__(self):
        self.effectiveness_data = defaultdict(lambda: {
            'usage_count': 0,
            'total_cost': 0.0,
            'avg_response_length': 0,
            'success_indicators': 0,
            'failure_indicators': 0,
            'response_times': deque(maxlen=100),
            'quality_scores': deque(maxlen=100),
            'last_updated': None
        })
        
    def record_usage(
        self,
        parameter_set_id: str,
        cost: float,
        response_length: int,
        response_time: float,
        success_indicators: List[str],
        failure_indicators: List[str],
        quality_score: Optional[float] = None
    ):
        """Record usage of a specific parameter set"""
        data = self.effectiveness_data[parameter_set_id]
        
        data['usage_count'] += 1
        data['total_cost'] += cost
        
        # Update running average for response length
        prev_avg = data['avg_response_length']
        data['avg_response_length'] = (
            (prev_avg * (data['usage_count'] - 1) + response_length) / data['usage_count']
        )
        
        data['success_indicators'] += len(success_indicators)
        data['failure_indicators'] += len(failure_indicators)
        data['response_times'].append(response_time)
        
        if quality_score is not None:
            data['quality_scores'].append(quality_score)
            
        data['last_updated'] = datetime.now().isoformat()
        
        logger.debug(f"📊 Updated effectiveness data for {parameter_set_id}")
    
    def get_effectiveness_report(self, parameter_set_id: str) -> Dict[str, Any]:
        """Get effectiveness report for a parameter set"""
        data = self.effectiveness_data[parameter_set_id]
        
        if data['usage_count'] == 0:
            return {"error": "No usage data available"}
        
        avg_response_time = sum(data['response_times']) / len(data['response_times']) if data['response_times'] else 0
        avg_quality_score = sum(data['quality_scores']) / len(data['quality_scores']) if data['quality_scores'] else None
        
        success_rate = data['success_indicators'] / max(1, data['success_indicators'] + data['failure_indicators'])
        avg_cost_per_use = data['total_cost'] / data['usage_count']
        
        return {
            'parameter_set_id': parameter_set_id,
            'usage_count': data['usage_count'],
            'avg_cost_per_use': avg_cost_per_use,
            'total_cost': data['total_cost'],
            'avg_response_length': data['avg_response_length'],
            'avg_response_time': avg_response_time,
            'success_rate': success_rate,
            'avg_quality_score': avg_quality_score,
            'cost_per_quality_point': avg_cost_per_use / max(0.1, avg_quality_score or 0.1),
            'last_updated': data['last_updated']
        }
    
    def compare_parameter_sets(self) -> Dict[str, Any]:
        """Compare all parameter sets and identify the most effective"""
        reports = {}
        for param_set_id in self.effectiveness_data:
            reports[param_set_id] = self.get_effectiveness_report(param_set_id)
        
        # Rank by cost-effectiveness (quality per dollar)
        ranked = []
        for param_set_id, report in reports.items():
            if 'error' not in report and report['avg_quality_score']:
                efficiency = report['avg_quality_score'] / max(0.001, report['avg_cost_per_use'])
                ranked.append((param_set_id, efficiency, report))
        
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'all_reports': reports,
            'ranking': [(param_id, efficiency) for param_id, efficiency, _ in ranked],
            'most_effective': ranked[0] if ranked else None,
            'least_effective': ranked[-1] if ranked else None
        }


class AnalysisQualityMonitor:
    """Monitor analysis quality metrics in real-time"""
    
    def __init__(self):
        self.quality_history = deque(maxlen=1000)
        self.quality_thresholds = {
            'completeness_min': 0.7,
            'depth_min': 0.6,
            'coherence_min': 0.8,
            'length_min': 1000
        }
        
    def assess_response_quality(self, response: str, expected_elements: List[str] = None) -> Dict[str, Any]:
        """Assess the quality of a model response"""
        quality_score = {
            'timestamp': datetime.now().isoformat(),
            'response_length': len(response),
            'sentence_count': len([s for s in response.split('.') if s.strip()]),
            'paragraph_count': len([p for p in response.split('\n\n') if p.strip()]),
            'numeric_mentions': len([w for w in response.split() if any(c.isdigit() for c in w)]),
            'structured_content': self._check_structured_content(response),
            'completeness_score': 0.0,
            'depth_score': 0.0,
            'coherence_score': 0.0,
            'overall_quality': 0.0
        }
        
        # Calculate completeness score
        if expected_elements:
            found_elements = sum(1 for elem in expected_elements if elem.lower() in response.lower())
            quality_score['completeness_score'] = found_elements / len(expected_elements)
        
        # Calculate depth score based on analysis characteristics
        depth_indicators = 0
        if quality_score['sentence_count'] >= 15:
            depth_indicators += 1
        if quality_score['numeric_mentions'] >= 5:
            depth_indicators += 1
        if quality_score['paragraph_count'] >= 4:
            depth_indicators += 1
        if len(response) >= 1500:
            depth_indicators += 1
        
        quality_score['depth_score'] = depth_indicators / 4
        
        # Calculate coherence score
        coherence_indicators = 0
        if quality_score['structured_content']['has_headers']:
            coherence_indicators += 1
        if quality_score['structured_content']['has_lists']:
            coherence_indicators += 1
        if quality_score['paragraph_count'] >= 3:
            coherence_indicators += 1
        
        quality_score['coherence_score'] = coherence_indicators / 3
        
        # Calculate overall quality (weighted average)
        quality_score['overall_quality'] = (
            quality_score['completeness_score'] * 0.4 +
            quality_score['depth_score'] * 0.35 +
            quality_score['coherence_score'] * 0.25
        )
        
        # Record in history
        self.quality_history.append(quality_score)
        
        return quality_score
    
    def _check_structured_content(self, response: str) -> Dict[str, bool]:
        """Check for structured content indicators"""
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        return {
            'has_headers': any(line.startswith('#') or line.endswith(':') for line in lines),
            'has_lists': any(line.startswith(('-', '*', '•')) for line in lines),
            'has_numbered_lists': any(line[0].isdigit() and '.' in line[:3] for line in lines),
            'has_sections': len([l for l in lines if l.endswith(':')]) >= 2
        }
    
    def get_quality_trend(self, hours: int = 24) -> Dict[str, Any]:
        """Get quality trend for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_scores = [
            score for score in self.quality_history
            if datetime.fromisoformat(score['timestamp']) >= cutoff_time
        ]
        
        if not recent_scores:
            return {"error": "No recent quality data"}
        
        # Calculate trends
        completeness_scores = [s['completeness_score'] for s in recent_scores if s['completeness_score'] > 0]
        depth_scores = [s['depth_score'] for s in recent_scores]
        coherence_scores = [s['coherence_score'] for s in recent_scores]
        overall_scores = [s['overall_quality'] for s in recent_scores]
        
        return {
            'period_hours': hours,
            'sample_count': len(recent_scores),
            'averages': {
                'completeness': sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0,
                'depth': sum(depth_scores) / len(depth_scores),
                'coherence': sum(coherence_scores) / len(coherence_scores),
                'overall': sum(overall_scores) / len(overall_scores)
            },
            'trends': {
                'improving': self._calculate_trend(overall_scores),
                'quality_degradation': sum(overall_scores) / len(overall_scores) < 0.6,
                'consistency': self._calculate_consistency(overall_scores)
            },
            'threshold_violations': self._check_threshold_violations(recent_scores)
        }
    
    def _calculate_trend(self, scores: List[float]) -> bool:
        """Calculate if scores are trending upward"""
        if len(scores) < 5:
            return False
        
        # Simple trend calculation: compare first half to second half
        mid_point = len(scores) // 2
        first_half_avg = sum(scores[:mid_point]) / mid_point
        second_half_avg = sum(scores[mid_point:]) / (len(scores) - mid_point)
        
        return second_half_avg > first_half_avg
    
    def _calculate_consistency(self, scores: List[float]) -> float:
        """Calculate consistency score (inverse of coefficient of variation)"""
        if len(scores) < 2:
            return 1.0
        
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5
        
        if mean_score == 0:
            return 0.0
        
        cv = std_dev / mean_score  # Coefficient of variation
        return max(0, 1 - cv)  # Consistency score (0-1, higher is more consistent)
    
    def _check_threshold_violations(self, scores: List[Dict[str, Any]]) -> Dict[str, int]:
        """Check for threshold violations"""
        violations = defaultdict(int)
        
        for score in scores:
            if score['completeness_score'] > 0 and score['completeness_score'] < self.quality_thresholds['completeness_min']:
                violations['completeness_violations'] += 1
            if score['depth_score'] < self.quality_thresholds['depth_min']:
                violations['depth_violations'] += 1
            if score['coherence_score'] < self.quality_thresholds['coherence_min']:
                violations['coherence_violations'] += 1
            if score['response_length'] < self.quality_thresholds['length_min']:
                violations['length_violations'] += 1
        
        return dict(violations)


class CostEffectivenessMonitor:
    """Monitor cost effectiveness of different configurations"""
    
    def __init__(self):
        self.cost_history = deque(maxlen=1000)
        self.budget_alerts = {
            'daily_budget': 10.0,  # $10/day
            'weekly_budget': 50.0,  # $50/week
            'monthly_budget': 200.0  # $200/month
        }
        
    def record_cost_data(
        self,
        model_name: str,
        parameter_set: Dict[str, Any],
        actual_cost: float,
        quality_score: float,
        response_length: int,
        task_type: str
    ):
        """Record cost and effectiveness data"""
        cost_record = {
            'timestamp': datetime.now().isoformat(),
            'model_name': model_name,
            'parameter_set_hash': self._hash_parameters(parameter_set),
            'parameters': parameter_set,
            'actual_cost': actual_cost,
            'quality_score': quality_score,
            'response_length': response_length,
            'task_type': task_type,
            'cost_per_quality_point': actual_cost / max(0.1, quality_score),
            'cost_per_char': actual_cost / max(1, response_length)
        }
        
        self.cost_history.append(cost_record)
        
        # Check for budget alerts
        self._check_budget_alerts()
    
    def _hash_parameters(self, params: Dict[str, Any]) -> str:
        """Create a hash of parameters for identification"""
        # Clean parameters (remove monitoring metadata)
        clean_params = {k: v for k, v in params.items() if not k.startswith('_')}
        params_str = json.dumps(clean_params, sort_keys=True)
        return str(hash(params_str))
    
    def _check_budget_alerts(self):
        """Check if we're approaching budget limits"""
        now = datetime.now()
        
        # Daily budget check
        daily_cost = sum(
            record['actual_cost'] for record in self.cost_history
            if datetime.fromisoformat(record['timestamp']) > now - timedelta(days=1)
        )
        
        if daily_cost > self.budget_alerts['daily_budget'] * 0.8:  # 80% threshold
            logger.warning(f"⚠️ Daily budget alert: ${daily_cost:.2f} / ${self.budget_alerts['daily_budget']:.2f}")
        
        # Weekly budget check
        weekly_cost = sum(
            record['actual_cost'] for record in self.cost_history
            if datetime.fromisoformat(record['timestamp']) > now - timedelta(days=7)
        )
        
        if weekly_cost > self.budget_alerts['weekly_budget'] * 0.8:
            logger.warning(f"⚠️ Weekly budget alert: ${weekly_cost:.2f} / ${self.budget_alerts['weekly_budget']:.2f}")
    
    def get_cost_effectiveness_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get cost effectiveness report"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_records = [
            record for record in self.cost_history
            if datetime.fromisoformat(record['timestamp']) >= cutoff_time
        ]
        
        if not recent_records:
            return {"error": "No recent cost data"}
        
        # Group by parameter sets
        param_groups = defaultdict(list)
        for record in recent_records:
            param_groups[record['parameter_set_hash']].append(record)
        
        # Analyze each parameter group
        parameter_analysis = {}
        for param_hash, records in param_groups.items():
            avg_cost = sum(r['actual_cost'] for r in records) / len(records)
            avg_quality = sum(r['quality_score'] for r in records) / len(records)
            avg_cost_per_quality = sum(r['cost_per_quality_point'] for r in records) / len(records)
            
            parameter_analysis[param_hash] = {
                'sample_params': records[0]['parameters'],  # Representative parameters
                'usage_count': len(records),
                'avg_cost': avg_cost,
                'total_cost': sum(r['actual_cost'] for r in records),
                'avg_quality_score': avg_quality,
                'avg_cost_per_quality_point': avg_cost_per_quality,
                'efficiency_rank': 0  # Will be set after sorting
            }
        
        # Rank by efficiency (lower cost per quality point is better)
        ranked_params = sorted(
            parameter_analysis.items(),
            key=lambda x: x[1]['avg_cost_per_quality_point']
        )
        
        for i, (param_hash, data) in enumerate(ranked_params):
            parameter_analysis[param_hash]['efficiency_rank'] = i + 1
        
        total_cost = sum(r['actual_cost'] for r in recent_records)
        avg_quality = sum(r['quality_score'] for r in recent_records) / len(recent_records)
        
        return {
            'period_hours': hours,
            'total_records': len(recent_records),
            'total_cost': total_cost,
            'avg_cost_per_request': total_cost / len(recent_records),
            'avg_quality_score': avg_quality,
            'cost_per_quality_point': total_cost / max(0.1, avg_quality),
            'parameter_efficiency_analysis': parameter_analysis,
            'most_efficient_parameters': ranked_params[0] if ranked_params else None,
            'least_efficient_parameters': ranked_params[-1] if ranked_params else None
        }


class GeminiMonitoringDashboard:
    """Comprehensive monitoring dashboard for Gemini improvements"""
    
    def __init__(self):
        self.parameter_tracker = ParameterEffectivenessTracker()
        self.quality_monitor = AnalysisQualityMonitor()
        self.cost_monitor = CostEffectivenessMonitor()
        self.monitoring_dir = Path("monitoring_data")
        self.monitoring_dir.mkdir(exist_ok=True)
        
        logger.info("🖥️ Gemini Monitoring Dashboard initialized")
    
    def record_analysis_session(
        self,
        model_name: str,
        parameters: Dict[str, Any],
        response: str,
        actual_cost: float,
        response_time: float,
        task_type: str = "stock_analysis",
        expected_elements: List[str] = None
    ) -> Dict[str, Any]:
        """Record a complete analysis session"""
        
        # Assess quality
        quality_assessment = self.quality_monitor.assess_response_quality(
            response, expected_elements
        )
        
        # Record cost effectiveness
        self.cost_monitor.record_cost_data(
            model_name=model_name,
            parameter_set=parameters,
            actual_cost=actual_cost,
            quality_score=quality_assessment['overall_quality'],
            response_length=len(response),
            task_type=task_type
        )
        
        # Record parameter effectiveness
        param_set_id = f"{model_name}_{self._create_param_signature(parameters)}"
        
        success_indicators = self._identify_success_indicators(response, quality_assessment)
        failure_indicators = self._identify_failure_indicators(response, quality_assessment)
        
        self.parameter_tracker.record_usage(
            parameter_set_id=param_set_id,
            cost=actual_cost,
            response_length=len(response),
            response_time=response_time,
            success_indicators=success_indicators,
            failure_indicators=failure_indicators,
            quality_score=quality_assessment['overall_quality']
        )
        
        # Generate session summary
        session_summary = {
            'session_id': f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'model_name': model_name,
            'parameters': parameters,
            'quality_assessment': quality_assessment,
            'cost_data': {
                'actual_cost': actual_cost,
                'cost_per_quality_point': actual_cost / max(0.1, quality_assessment['overall_quality'])
            },
            'performance_indicators': {
                'success_indicators': success_indicators,
                'failure_indicators': failure_indicators,
                'response_time': response_time
            }
        }
        
        logger.info(f"📊 Analysis session recorded: Quality={quality_assessment['overall_quality']:.2f}, Cost=${actual_cost:.4f}")
        
        return session_summary
    
    def _create_param_signature(self, parameters: Dict[str, Any]) -> str:
        """Create a short signature for parameters"""
        clean_params = {k: v for k, v in parameters.items() if not k.startswith('_')}
        temp = clean_params.get('temperature', 0.0)
        max_tokens = clean_params.get('max_tokens', 0)
        top_p = clean_params.get('top_p', 0.0)
        
        return f"t{temp}_m{max_tokens}_p{top_p}".replace('.', '')
    
    def _identify_success_indicators(self, response: str, quality_assessment: Dict[str, Any]) -> List[str]:
        """Identify indicators of successful analysis"""
        indicators = []
        
        if quality_assessment['overall_quality'] >= 0.8:
            indicators.append("high_quality_analysis")
        if quality_assessment['completeness_score'] >= 0.8:
            indicators.append("complete_coverage")
        if quality_assessment['depth_score'] >= 0.7:
            indicators.append("sufficient_depth")
        if quality_assessment['response_length'] >= 1500:
            indicators.append("adequate_length")
        if quality_assessment['numeric_mentions'] >= 5:
            indicators.append("data_rich")
        
        # Content-specific indicators
        if "recommendation" in response.lower():
            indicators.append("includes_recommendation")
        if any(word in response.lower() for word in ["risk", "risks"]):
            indicators.append("includes_risk_analysis")
        if any(word in response.lower() for word in ["price", "target", "valuation"]):
            indicators.append("includes_valuation")
        
        return indicators
    
    def _identify_failure_indicators(self, response: str, quality_assessment: Dict[str, Any]) -> List[str]:
        """Identify indicators of analysis problems"""
        indicators = []
        
        if quality_assessment['overall_quality'] < 0.5:
            indicators.append("low_quality_analysis")
        if quality_assessment['completeness_score'] < 0.6:
            indicators.append("incomplete_coverage")
        if quality_assessment['response_length'] < 800:
            indicators.append("too_short")
        if quality_assessment['numeric_mentions'] < 2:
            indicators.append("lacks_data")
        
        # Content-specific failures
        if "sorry" in response.lower() or "cannot" in response.lower():
            indicators.append("refusal_response")
        if response.lower().count("analysis") < 2:
            indicators.append("lacks_analysis_depth")
        if not any(word in response.lower() for word in ["recommend", "suggest", "advise"]):
            indicators.append("no_clear_recommendation")
        
        return indicators
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        logger.info("📋 Generating comprehensive monitoring report")
        
        # Get individual component reports
        parameter_comparison = self.parameter_tracker.compare_parameter_sets()
        quality_trend = self.quality_monitor.get_quality_trend(hours=24)
        cost_effectiveness = self.cost_monitor.get_cost_effectiveness_report(hours=24)
        
        # Generate overall assessment
        overall_assessment = self._assess_overall_performance(
            parameter_comparison, quality_trend, cost_effectiveness
        )
        
        # Generate recommendations
        recommendations = self._generate_improvement_recommendations(
            parameter_comparison, quality_trend, cost_effectiveness
        )
        
        comprehensive_report = {
            'report_timestamp': datetime.now().isoformat(),
            'parameter_effectiveness': parameter_comparison,
            'quality_trends': quality_trend,
            'cost_effectiveness': cost_effectiveness,
            'overall_assessment': overall_assessment,
            'improvement_recommendations': recommendations,
            'system_health': self._check_system_health()
        }
        
        # Save report
        self._save_monitoring_report(comprehensive_report)
        
        return comprehensive_report
    
    def _assess_overall_performance(
        self, 
        param_comparison: Dict[str, Any],
        quality_trend: Dict[str, Any], 
        cost_effectiveness: Dict[str, Any]
    ) -> str:
        """Assess overall system performance"""
        
        # Check if we have enough data
        if ('error' in quality_trend or 'error' in cost_effectiveness or 
            not param_comparison.get('most_effective')):
            return "INSUFFICIENT_DATA - Not enough data for assessment"
        
        # Check quality trends
        quality_good = quality_trend['averages']['overall'] >= 0.7
        quality_improving = quality_trend['trends']['improving']
        
        # Check cost effectiveness
        cost_reasonable = cost_effectiveness['avg_cost_per_request'] <= 0.50  # $0.50 per request
        cost_efficient = cost_effectiveness['cost_per_quality_point'] <= 1.0  # $1 per quality point
        
        # Check parameter effectiveness
        best_params = param_comparison.get('most_effective')
        param_effective = best_params and best_params[1] > 0.5  # Efficiency score
        
        if quality_good and cost_efficient and param_effective:
            return "EXCELLENT - All metrics performing well"
        elif quality_good and (cost_efficient or param_effective):
            return "GOOD - Strong performance with room for optimization"
        elif quality_improving and cost_reasonable:
            return "IMPROVING - Positive trends but needs monitoring"
        elif not quality_good and not cost_efficient:
            return "POOR - Significant improvement needed"
        else:
            return "MIXED - Some areas performing well, others need attention"
    
    def _generate_improvement_recommendations(
        self,
        param_comparison: Dict[str, Any],
        quality_trend: Dict[str, Any],
        cost_effectiveness: Dict[str, Any]
    ) -> List[str]:
        """Generate specific improvement recommendations"""
        recommendations = []
        
        # Parameter recommendations
        if param_comparison.get('most_effective'):
            best_param_id = param_comparison['most_effective'][0]
            recommendations.append(f"🎯 Use parameter set '{best_param_id}' - most cost-effective")
        
        # Quality recommendations
        if 'error' not in quality_trend:
            if quality_trend['averages']['overall'] < 0.6:
                recommendations.append("📈 Quality below target - consider increasing max_tokens")
            if quality_trend['averages']['completeness'] < 0.7:
                recommendations.append("📝 Improve completeness - review prompt engineering")
            if not quality_trend['trends']['improving']:
                recommendations.append("🔄 Quality not improving - review parameter adjustments")
        
        # Cost recommendations
        if 'error' not in cost_effectiveness:
            if cost_effectiveness['avg_cost_per_request'] > 0.75:
                recommendations.append("💰 High cost per request - consider more efficient parameters")
            if cost_effectiveness['cost_per_quality_point'] > 1.5:
                recommendations.append("⚖️ Poor cost-quality ratio - optimize parameters")
        
        # System recommendations
        if not recommendations:
            recommendations.append("✅ System performing well - continue current configuration")
        
        return recommendations
    
    def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health"""
        health_status = {
            'monitoring_active': True,
            'data_collection_healthy': len(self.quality_monitor.quality_history) > 0,
            'cost_tracking_active': len(self.cost_monitor.cost_history) > 0,
            'parameter_tracking_active': len(self.parameter_tracker.effectiveness_data) > 0,
            'alerts_active': True,
            'last_health_check': datetime.now().isoformat()
        }
        
        overall_health = all(health_status[key] for key in health_status if key != 'last_health_check')
        health_status['overall_health'] = "HEALTHY" if overall_health else "DEGRADED"
        
        return health_status
    
    def _save_monitoring_report(self, report: Dict[str, Any]):
        """Save monitoring report to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gemini_monitoring_report_{timestamp}.json"
        filepath = self.monitoring_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Monitoring report saved to {filepath}")


# Global monitoring dashboard instance
monitoring_dashboard = GeminiMonitoringDashboard()


def record_gemini_analysis(
    model_name: str,
    parameters: Dict[str, Any],
    response: str,
    actual_cost: float,
    response_time: float,
    task_type: str = "stock_analysis"
) -> Dict[str, Any]:
    """
    Convenience function to record a Gemini analysis session
    
    Usage:
        record_gemini_analysis(
            model_name="gemini-2.5-pro",
            parameters={"temperature": 0.3, "max_tokens": 8000},
            response=response_content,
            actual_cost=0.15,
            response_time=3.2
        )
    """
    return monitoring_dashboard.record_analysis_session(
        model_name=model_name,
        parameters=parameters,
        response=response,
        actual_cost=actual_cost,
        response_time=response_time,
        task_type=task_type
    )


if __name__ == "__main__":
    # Demo monitoring functionality
    dashboard = GeminiMonitoringDashboard()
    
    print("Gemini Monitoring Dashboard Demo")
    print("=" * 40)
    
    # Simulate some analysis sessions
    import random
    
    sample_responses = [
        "Comprehensive analysis of AAPL stock shows strong financial performance with revenue growth of 8% YoY. The company maintains healthy profit margins at 25%. Key risks include market saturation and regulatory challenges. Recommendation: BUY with price target of $180.",
        "Brief analysis shows positive trends.",
        "Tesla's position in the EV market remains strong with 20% market share. Financial metrics show improvement in gross margins to 18%. Competitive pressures increasing from traditional automakers. Risk factors include regulatory changes and supply chain disruptions. Investment thesis remains positive with 12-month target of $250."
    ]
    
    for i in range(3):
        response = sample_responses[i]
        cost = random.uniform(0.05, 0.25)
        response_time = random.uniform(2.0, 5.0)
        
        params = {
            "temperature": 0.3,
            "max_tokens": 8000 if i != 1 else 2000,  # Simulate different configs
            "top_p": 0.8
        }
        
        session = dashboard.record_analysis_session(
            model_name="gemini-2.5-pro",
            parameters=params,
            response=response,
            actual_cost=cost,
            response_time=response_time
        )
        
        print(f"Session {i+1}: Quality={session['quality_assessment']['overall_quality']:.2f}, Cost=${cost:.3f}")
    
    # Generate report
    print("\nGenerating comprehensive report...")
    report = dashboard.generate_comprehensive_report()
    
    print(f"\nOverall Assessment: {report['overall_assessment']}")
    print("Recommendations:")
    for rec in report['improvement_recommendations']:
        print(f"  • {rec}")