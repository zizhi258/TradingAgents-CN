"""Machine Learning Pipeline for TradingAgents-CN System

This module provides a comprehensive ML pipeline for stock market analysis,
including feature engineering, model training, validation, and deployment.

Key Components:
- Feature Engineering: Technical indicators, fundamental ratios, sentiment features
- Model Training: Price prediction, signal classification, volatility, risk models
- Validation Framework: Time-series CV, backtesting, performance metrics
- Deployment Pipeline: Model versioning, A/B testing, real-time inference
- Integration: Seamless integration with TradingAgents multi-agent system
"""

from .feature_engineering import (
    TechnicalIndicatorEngine,
    FundamentalAnalysisEngine,
    SentimentAnalysisEngine,
    MarketMicrostructureEngine,
    TimeSeriesFeatureEngine
)

from .models import (
    PricePredictionModel,
    TradingSignalClassifier,
    VolatilityModel,
    RiskAssessmentModel,
    MarketRegimeModel
)

from .validation import (
    TimeSeriesValidator,
    BacktestingFramework,
    PerformanceMetrics,
    ModelDriftDetector
)

from .deployment import (
    ModelRegistry,
    ABTestingFramework,
    InferenceService,
    ModelMonitor
)

from .pipeline import MLPipeline

# Import logging system
from tradingagents.utils.logging_init import get_logger
logger = get_logger("ml_pipeline")

__version__ = "1.0.0"
__author__ = "TradingAgents-CN ML Team"

__all__ = [
    # Feature Engineering
    "TechnicalIndicatorEngine",
    "FundamentalAnalysisEngine", 
    "SentimentAnalysisEngine",
    "MarketMicrostructureEngine",
    "TimeSeriesFeatureEngine",
    
    # Models
    "PricePredictionModel",
    "TradingSignalClassifier",
    "VolatilityModel",
    "RiskAssessmentModel",
    "MarketRegimeModel",
    
    # Validation
    "TimeSeriesValidator",
    "BacktestingFramework",
    "PerformanceMetrics",
    "ModelDriftDetector",
    
    # Deployment
    "ModelRegistry",
    "ABTestingFramework",
    "InferenceService",
    "ModelMonitor",
    
    # Main Pipeline
    "MLPipeline"
]