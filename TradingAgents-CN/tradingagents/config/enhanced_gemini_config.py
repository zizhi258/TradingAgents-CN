#!/usr/bin/env python3
"""
Enhanced Gemini Configuration Manager
Provides configurable token limits, cost controls, and monitoring for Gemini models
"""

import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from tradingagents.utils.logging_manager import get_logger
from tradingagents.config.config_manager import config_manager, token_tracker

logger = get_logger('gemini_config')


@dataclass
class TokenLimitConfig:
    """Token limit configuration with cost controls"""
    model_name: str
    base_max_tokens: int
    deep_thinking_max_tokens: int
    quick_thinking_max_tokens: int
    daily_token_limit: Optional[int] = None
    cost_limit_usd: Optional[float] = None
    adaptive_scaling: bool = True


@dataclass
class CostMonitoringConfig:
    """Cost monitoring and alerting configuration"""
    daily_budget_usd: float = 10.0
    weekly_budget_usd: float = 50.0
    monthly_budget_usd: float = 200.0
    alert_threshold_pct: float = 80.0  # Alert at 80% of budget
    emergency_stop_threshold_pct: float = 95.0  # Stop at 95% of budget


class EnhancedGeminiConfigManager:
    """Enhanced configuration manager for Gemini models with cost controls"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or "config")
        self.config_dir.mkdir(exist_ok=True)
        
        self.gemini_config_file = self.config_dir / "gemini_enhanced_config.json"
        self.cost_monitoring_file = self.config_dir / "gemini_cost_monitoring.json"
        
        # Load configurations
        self.token_limits = self._load_token_limits()
        self.cost_monitoring = self._load_cost_monitoring_config()
        
        # Initialize monitoring
        self.usage_history = []
        self._load_usage_history()
    
    def _load_token_limits(self) -> Dict[str, TokenLimitConfig]:
        """Load token limit configurations"""
        default_configs = {
            "gemini-2.5-pro": TokenLimitConfig(
                model_name="gemini-2.5-pro",
                base_max_tokens=32000,  # Increased for 128K context models
                deep_thinking_max_tokens=65536,  # Allow much higher for complex analysis
                quick_thinking_max_tokens=32000,  # Standard for quick tasks
                daily_token_limit=1000000,  # 1M tokens per day - no practical limit
                cost_limit_usd=50.00,  # $50 daily limit
                adaptive_scaling=True
            ),
            "gemini-2.0-flash": TokenLimitConfig(
                model_name="gemini-2.0-flash",
                base_max_tokens=32000,
                deep_thinking_max_tokens=65536,
                quick_thinking_max_tokens=32000,
                daily_token_limit=2000000,  # Flash is cheaper, allow more
                cost_limit_usd=20.00,
                adaptive_scaling=True
            ),
            "gemini-1.5-pro": TokenLimitConfig(
                model_name="gemini-1.5-pro",
                base_max_tokens=32000,
                deep_thinking_max_tokens=65536,
                quick_thinking_max_tokens=32000,
                daily_token_limit=1000000,
                cost_limit_usd=40.00,
                adaptive_scaling=True
            ),
            "gemini-1.5-flash": TokenLimitConfig(
                model_name="gemini-1.5-flash",
                base_max_tokens=32000,
                deep_thinking_max_tokens=65536,
                quick_thinking_max_tokens=32000,
                daily_token_limit=2000000,
                cost_limit_usd=15.00,
                adaptive_scaling=True
            )
        }
        
        if self.gemini_config_file.exists():
            try:
                import json
                with open(self.gemini_config_file, 'r') as f:
                    data = json.load(f)
                    for model_name, config_data in data.items():
                        default_configs[model_name] = TokenLimitConfig(**config_data)
            except Exception as e:
                logger.error(f"Failed to load Gemini config, using defaults: {e}")
        
        return default_configs
    
    def _load_cost_monitoring_config(self) -> CostMonitoringConfig:
        """Load cost monitoring configuration"""
        default_config = CostMonitoringConfig()
        
        if self.cost_monitoring_file.exists():
            try:
                import json
                with open(self.cost_monitoring_file, 'r') as f:
                    data = json.load(f)
                    default_config = CostMonitoringConfig(**data)
            except Exception as e:
                logger.error(f"Failed to load cost monitoring config, using defaults: {e}")
        
        return default_config
    
    def _load_usage_history(self):
        """Load recent usage history for monitoring"""
        try:
            # Get recent usage from the main config manager
            recent_stats = config_manager.get_usage_statistics(days=1)
            self.usage_history = recent_stats.get('provider_stats', {}).get('google', {})
        except Exception as e:
            logger.error(f"Failed to load usage history: {e}")
            self.usage_history = {}
    
    def get_optimal_parameters(
        self, 
        model_name: str, 
        task_type: str,
        complexity_level: str = "medium",
        current_usage: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get optimal parameters for a Gemini model with cost controls
        
        Args:
            model_name: Gemini model name
            task_type: Type of task (e.g., "stock_analysis", "risk_assessment")
            complexity_level: "low", "medium", "high"
            current_usage: Current usage statistics
            
        Returns:
            Optimized parameters with cost controls
        """
        logger.info(f"🔧 Getting optimal parameters for {model_name}, task: {task_type}, complexity: {complexity_level}")
        
        # Get base configuration
        config = self.token_limits.get(model_name)
        if not config:
            logger.warning(f"⚠️ No configuration found for {model_name}, using default")
            config = self._get_default_config(model_name)
        
        # Check cost limits first
        cost_check = self._check_cost_limits(model_name, current_usage)
        if not cost_check['allowed']:
            logger.warning(f"⚠️ Cost limits exceeded for {model_name}: {cost_check['reason']}")
            return self._get_fallback_parameters(model_name, cost_check)
        
        # Get base parameters based on complexity
        if complexity_level == "high":
            max_tokens = config.deep_thinking_max_tokens
            temperature = self._get_optimal_temperature(model_name, "deep")
            top_p = 0.8
        elif complexity_level == "low":
            max_tokens = config.quick_thinking_max_tokens
            temperature = self._get_optimal_temperature(model_name, "quick")
            top_p = 0.7
        else:  # medium
            max_tokens = config.base_max_tokens
            temperature = self._get_optimal_temperature(model_name, "medium")
            top_p = 0.75
        
        # Apply adaptive scaling if enabled
        if config.adaptive_scaling:
            max_tokens = self._apply_adaptive_scaling(
                max_tokens, model_name, task_type, current_usage
            )
        
        # Apply cost-based scaling
        max_tokens = self._apply_cost_scaling(max_tokens, model_name, cost_check['remaining_budget_pct'])
        
        parameters = {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        
        # Add monitoring metadata
        parameters["_cost_monitoring"] = {
            "estimated_cost_usd": self._estimate_request_cost(model_name, max_tokens),
            "remaining_budget_pct": cost_check['remaining_budget_pct'],
            "adaptive_scaling_applied": config.adaptive_scaling,
            "original_max_tokens": config.deep_thinking_max_tokens if complexity_level == "high" else config.base_max_tokens
        }
        
        logger.info(f"✅ Optimal parameters: {parameters}")
        return parameters
    
    def _check_cost_limits(self, model_name: str, current_usage: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Check if request is within cost limits"""
        try:
            # Get current usage statistics
            daily_stats = config_manager.get_usage_statistics(days=1)
            weekly_stats = config_manager.get_usage_statistics(days=7)
            monthly_stats = config_manager.get_usage_statistics(days=30)
            
            # Convert CNY to USD if needed (rough estimate)
            daily_cost = daily_stats.get('total_cost', 0) * 0.14  # CNY to USD rough conversion
            weekly_cost = weekly_stats.get('total_cost', 0) * 0.14
            monthly_cost = monthly_stats.get('total_cost', 0) * 0.14
            
            # Check against limits
            daily_limit_exceeded = daily_cost >= self.cost_monitoring.daily_budget_usd * (self.cost_monitoring.emergency_stop_threshold_pct / 100)
            weekly_limit_exceeded = weekly_cost >= self.cost_monitoring.weekly_budget_usd * (self.cost_monitoring.emergency_stop_threshold_pct / 100)
            monthly_limit_exceeded = monthly_cost >= self.cost_monitoring.monthly_budget_usd * (self.cost_monitoring.emergency_stop_threshold_pct / 100)
            
            if daily_limit_exceeded:
                return {
                    'allowed': False,
                    'reason': f'Daily budget exceeded: ${daily_cost:.2f} >= ${self.cost_monitoring.daily_budget_usd:.2f}',
                    'remaining_budget_pct': 0
                }
            
            if weekly_limit_exceeded:
                return {
                    'allowed': False,
                    'reason': f'Weekly budget exceeded: ${weekly_cost:.2f} >= ${self.cost_monitoring.weekly_budget_usd:.2f}',
                    'remaining_budget_pct': 0
                }
            
            if monthly_limit_exceeded:
                return {
                    'allowed': False,
                    'reason': f'Monthly budget exceeded: ${monthly_cost:.2f} >= ${self.cost_monitoring.monthly_budget_usd:.2f}',
                    'remaining_budget_pct': 0
                }
            
            # Calculate remaining budget percentage (most restrictive)
            daily_remaining = max(0, (self.cost_monitoring.daily_budget_usd - daily_cost) / self.cost_monitoring.daily_budget_usd * 100)
            weekly_remaining = max(0, (self.cost_monitoring.weekly_budget_usd - weekly_cost) / self.cost_monitoring.weekly_budget_usd * 100)
            monthly_remaining = max(0, (self.cost_monitoring.monthly_budget_usd - monthly_cost) / self.cost_monitoring.monthly_budget_usd * 100)
            
            remaining_budget_pct = min(daily_remaining, weekly_remaining, monthly_remaining)
            
            # Check alert thresholds
            if remaining_budget_pct <= (100 - self.cost_monitoring.alert_threshold_pct):
                logger.warning(f"⚠️ Cost alert: {remaining_budget_pct:.1f}% budget remaining")
            
            return {
                'allowed': True,
                'reason': 'Within budget limits',
                'remaining_budget_pct': remaining_budget_pct,
                'daily_cost': daily_cost,
                'weekly_cost': weekly_cost,
                'monthly_cost': monthly_cost
            }
            
        except Exception as e:
            logger.error(f"Cost limit check failed: {e}")
            return {
                'allowed': True,  # Fail open to avoid blocking functionality
                'reason': f'Cost check failed: {e}',
                'remaining_budget_pct': 100
            }
    
    def _get_fallback_parameters(self, model_name: str, cost_check: Dict[str, Any]) -> Dict[str, Any]:
        """Get reduced parameters when cost limits are exceeded"""
        logger.warning(f"🔥 Using fallback parameters for {model_name} due to cost limits")
        
        # Severely reduced parameters to minimize cost
        return {
            "temperature": 0.1,  # Lower temperature for more focused responses
            "max_tokens": 1000,  # Minimum viable token limit
            "top_p": 0.6,  # More focused sampling
            "_cost_monitoring": {
                "fallback_mode": True,
                "reason": cost_check['reason'],
                "estimated_cost_usd": self._estimate_request_cost(model_name, 1000),
                "remaining_budget_pct": cost_check['remaining_budget_pct']
            }
        }
    
    def _apply_adaptive_scaling(
        self, 
        base_max_tokens: int, 
        model_name: str, 
        task_type: str, 
        current_usage: Optional[Dict[str, Any]]
    ) -> int:
        """Apply adaptive scaling based on recent performance and usage patterns"""
        
        # Task-specific scaling factors
        task_scaling = {
            "stock_analysis": 1.2,  # Stock analysis needs more detail
            "risk_assessment": 1.3,  # Risk assessment is complex
            "market_analysis": 1.4,  # Market analysis needs comprehensive coverage
            "news_analysis": 0.9,   # News analysis can be more concise
            "social_sentiment": 0.8, # Sentiment analysis is typically shorter
        }
        
        scale_factor = task_scaling.get(task_type, 1.0)
        
        # Apply time-based scaling (higher limits during market hours)
        if self._is_market_hours():
            scale_factor *= 1.1
        
        # Apply usage-based scaling (reduce if heavy usage recently)
        if current_usage and current_usage.get('requests', 0) > 10:
            scale_factor *= 0.9  # Reduce by 10% if many recent requests
        
        scaled_tokens = int(base_max_tokens * scale_factor)
        
        # Ensure we don't exceed hard limits
        config = self.token_limits.get(model_name)
        if config and config.daily_token_limit:
            daily_usage = self.usage_history.get('input_tokens', 0) + self.usage_history.get('output_tokens', 0)
            remaining_daily_tokens = config.daily_token_limit - daily_usage
            scaled_tokens = min(scaled_tokens, remaining_daily_tokens // 4)  # Reserve 75% for other requests
        
        logger.debug(f"Adaptive scaling: {base_max_tokens} -> {scaled_tokens} (factor: {scale_factor:.2f})")
        return max(1000, scaled_tokens)  # Minimum 1000 tokens
    
    def _apply_cost_scaling(self, max_tokens: int, model_name: str, remaining_budget_pct: float) -> int:
        """Apply cost-based scaling to token limits"""
        if remaining_budget_pct > 50:
            # Plenty of budget remaining, no scaling needed
            return max_tokens
        elif remaining_budget_pct > 20:
            # Moderate budget remaining, scale down slightly
            scale_factor = 0.8
        else:
            # Low budget remaining, significant scaling
            scale_factor = 0.5
        
        scaled_tokens = int(max_tokens * scale_factor)
        logger.debug(f"Cost scaling: {max_tokens} -> {scaled_tokens} (budget: {remaining_budget_pct:.1f}%)")
        return max(500, scaled_tokens)  # Minimum 500 tokens
    
    def _get_optimal_temperature(self, model_name: str, thinking_type: str) -> float:
        """Get optimal temperature based on model and thinking type"""
        base_temps = {
            "gemini-2.5-pro": {"deep": 0.3, "medium": 0.2, "quick": 0.1},
            "gemini-2.0-flash": {"deep": 0.2, "medium": 0.15, "quick": 0.1},
            "gemini-1.5-pro": {"deep": 0.25, "medium": 0.2, "quick": 0.15},
            "gemini-1.5-flash": {"deep": 0.2, "medium": 0.15, "quick": 0.1}
        }
        
        model_temps = base_temps.get(model_name, base_temps["gemini-1.5-pro"])
        return model_temps.get(thinking_type, 0.2)
    
    def _is_market_hours(self) -> bool:
        """Check if it's currently market hours (US Eastern Time)"""
        try:
            from pytz import timezone
            import datetime
            
            eastern = timezone('US/Eastern')
            now = datetime.datetime.now(eastern)
            
            # Market hours: 9:30 AM - 4:00 PM ET, Monday-Friday
            if now.weekday() >= 5:  # Weekend
                return False
            
            market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
            
            return market_open <= now <= market_close
        except:
            # If timezone detection fails, assume it's market hours
            return True
    
    def _estimate_request_cost(self, model_name: str, max_tokens: int) -> float:
        """Estimate the cost of a request"""
        # Rough estimate: assume 50% of max_tokens used for output, rest for input context
        estimated_input_tokens = max_tokens * 0.3  # Context size estimate
        estimated_output_tokens = max_tokens * 0.7  # Output size estimate
        
        return config_manager.calculate_cost("google", model_name, int(estimated_input_tokens), int(estimated_output_tokens))
    
    def _get_default_config(self, model_name: str) -> TokenLimitConfig:
        """Get default configuration for unknown models"""
        return TokenLimitConfig(
            model_name=model_name,
            base_max_tokens=32000,
            deep_thinking_max_tokens=65536,
            quick_thinking_max_tokens=32000,
            daily_token_limit=1000000,
            cost_limit_usd=20.00,
            adaptive_scaling=True
        )
    
    def save_configurations(self):
        """Save current configurations to files"""
        import json
        
        # Save token limits
        token_limits_data = {}
        for model_name, config in self.token_limits.items():
            token_limits_data[model_name] = {
                "model_name": config.model_name,
                "base_max_tokens": config.base_max_tokens,
                "deep_thinking_max_tokens": config.deep_thinking_max_tokens,
                "quick_thinking_max_tokens": config.quick_thinking_max_tokens,
                "daily_token_limit": config.daily_token_limit,
                "cost_limit_usd": config.cost_limit_usd,
                "adaptive_scaling": config.adaptive_scaling
            }
        
        with open(self.gemini_config_file, 'w') as f:
            json.dump(token_limits_data, f, indent=2)
        
        # Save cost monitoring config
        cost_monitoring_data = {
            "daily_budget_usd": self.cost_monitoring.daily_budget_usd,
            "weekly_budget_usd": self.cost_monitoring.weekly_budget_usd,
            "monthly_budget_usd": self.cost_monitoring.monthly_budget_usd,
            "alert_threshold_pct": self.cost_monitoring.alert_threshold_pct,
            "emergency_stop_threshold_pct": self.cost_monitoring.emergency_stop_threshold_pct
        }
        
        with open(self.cost_monitoring_file, 'w') as f:
            json.dump(cost_monitoring_data, f, indent=2)
        
        logger.info("✅ Enhanced Gemini configurations saved")
    
    def get_cost_report(self, days: int = 7) -> Dict[str, Any]:
        """Get detailed cost report for Gemini models"""
        stats = config_manager.get_usage_statistics(days)
        google_stats = stats.get('provider_stats', {}).get('google', {})
        
        # Convert to USD (rough estimate)
        cost_usd = google_stats.get('cost', 0) * 0.14
        
        report = {
            "period_days": days,
            "total_cost_usd": cost_usd,
            "total_requests": google_stats.get('requests', 0),
            "total_tokens": google_stats.get('input_tokens', 0) + google_stats.get('output_tokens', 0),
            "avg_cost_per_request": cost_usd / max(1, google_stats.get('requests', 1)),
            "budget_utilization": {
                "daily": min(100, (cost_usd / days) / self.cost_monitoring.daily_budget_usd * 100),
                "weekly": min(100, cost_usd / self.cost_monitoring.weekly_budget_usd * 100) if days >= 7 else 0,
                "monthly": min(100, cost_usd / self.cost_monitoring.monthly_budget_usd * 100) if days >= 30 else 0
            }
        }
        
        return report


# Global enhanced configuration manager
enhanced_gemini_config = EnhancedGeminiConfigManager()


def get_enhanced_gemini_parameters(
    model_name: str,
    task_type: str = "stock_analysis",
    complexity_level: str = "medium"
) -> Dict[str, Any]:
    """
    Convenience function to get enhanced Gemini parameters
    
    Usage:
        params = get_enhanced_gemini_parameters("gemini-2.5-pro", "stock_analysis", "high")
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", **params)
    """
    return enhanced_gemini_config.get_optimal_parameters(
        model_name=model_name,
        task_type=task_type,
        complexity_level=complexity_level
    )


if __name__ == "__main__":
    # Demo usage
    config_mgr = EnhancedGeminiConfigManager()
    
    print("Enhanced Gemini Configuration Manager Demo")
    print("=" * 50)
    
    # Test different scenarios
    scenarios = [
        ("gemini-2.5-pro", "stock_analysis", "high"),
        ("gemini-2.0-flash", "news_analysis", "medium"),
        ("gemini-1.5-pro", "risk_assessment", "high"),
    ]
    
    for model, task, complexity in scenarios:
        print(f"\nScenario: {model} - {task} - {complexity}")
        params = config_mgr.get_optimal_parameters(model, task, complexity)
        print(f"Parameters: {params}")
    
    # Show cost report
    print(f"\nCost Report:")
    report = config_mgr.get_cost_report()
    print(f"  Total Cost (7 days): ${report['total_cost_usd']:.4f}")
    print(f"  Total Requests: {report['total_requests']}")
    print(f"  Budget Utilization: {report['budget_utilization']}")