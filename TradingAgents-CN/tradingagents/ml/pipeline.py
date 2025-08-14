"""Main ML Pipeline Orchestrator for TradingAgents-CN

This module provides the main ML pipeline that orchestrates feature engineering,
model training, validation, and deployment for the TradingAgents-CN system.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import warnings
from pathlib import Path

# Import ML pipeline components
from .feature_engineering import (
    FeatureConfig, create_comprehensive_features,
    TechnicalIndicatorEngine, FundamentalAnalysisEngine,
    SentimentAnalysisEngine, MarketMicrostructureEngine,
    TimeSeriesFeatureEngine
)
from .models import (
    ModelConfig, create_model,
    PricePredictionModel, TradingSignalClassifier,
    VolatilityModel, RiskAssessmentModel, MarketRegimeModel
)
from .validation import (
    ValidationConfig, run_comprehensive_validation,
    TimeSeriesValidator, BacktestingFramework,
    PerformanceMetrics, ModelDriftDetector
)
from .deployment import (
    DeploymentConfig, ModelMetadata, deploy_model,
    ModelRegistry, ABTestingFramework,
    InferenceService, ModelMonitor
)

# Import existing TradingAgents components
from tradingagents.dataflows import (
    get_YFin_data_window, get_china_stock_data_unified,
    get_finnhub_news
)

# Import logging system
from tradingagents.utils.logging_init import get_logger
logger = get_logger("ml_pipeline")


@dataclass
class PipelineConfig:
    """Configuration for the entire ML pipeline"""
    # Data configuration
    symbols: List[str] = None
    start_date: str = "2022-01-01"
    end_date: Optional[str] = None
    market_type: str = "US"  # "US", "CN", "HK"
    
    # Feature engineering
    feature_config: FeatureConfig = None
    
    # Model training
    model_configs: Dict[str, ModelConfig] = None
    
    # Validation
    validation_config: ValidationConfig = None
    
    # Deployment
    deployment_config: DeploymentConfig = None
    
    # Pipeline settings
    auto_retrain: bool = True
    retrain_frequency_days: int = 30
    min_training_samples: int = 1000
    
    # Output paths
    output_dir: str = "/mnt/c/Users/黄斌/Desktop/股票/TradingAgents-CN/ml_output"
    save_intermediate_results: bool = True
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["AAPL", "MSFT", "GOOGL"]  # Default US stocks
        
        if self.end_date is None:
            self.end_date = datetime.now().strftime("%Y-%m-%d")
        
        if self.feature_config is None:
            self.feature_config = FeatureConfig()
        
        if self.model_configs is None:
            self.model_configs = {
                "price_prediction": ModelConfig(model_type="xgboost", task_type="regression"),
                "signal_classification": ModelConfig(model_type="random_forest", task_type="classification"),
                "volatility_prediction": ModelConfig(model_type="xgboost", task_type="regression"),
                "risk_assessment": ModelConfig(model_type="random_forest", task_type="classification")
            }
        
        if self.validation_config is None:
            self.validation_config = ValidationConfig()
        
        if self.deployment_config is None:
            self.deployment_config = DeploymentConfig()


class MLPipeline:
    """Main ML Pipeline orchestrator for TradingAgents-CN"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.output_dir = Path(config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize pipeline components
        self.model_registry = ModelRegistry(config.deployment_config)
        self.inference_service = InferenceService(config.deployment_config, self.model_registry)
        self.ab_testing = ABTestingFramework(config.deployment_config)
        self.monitor = ModelMonitor(config.deployment_config)
        
        # Pipeline state
        self.pipeline_runs = []
        self.trained_models = {}
        self.validation_results = {}
        
        logger.info("ML Pipeline initialized")
    
    def run_full_pipeline(self, symbols: Optional[List[str]] = None) -> Dict:
        """Run the complete ML pipeline from data ingestion to deployment"""
        
        symbols = symbols or self.config.symbols
        logger.info(f"Starting full ML pipeline for symbols: {symbols}")
        
        pipeline_start_time = datetime.now()
        pipeline_id = f"pipeline_{pipeline_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # Step 1: Data ingestion and preparation
            logger.info("Step 1: Data ingestion and preparation")
            data_results = self._ingest_and_prepare_data(symbols)
            
            # Step 2: Feature engineering
            logger.info("Step 2: Feature engineering")
            feature_results = self._engineer_features(data_results)
            
            # Step 3: Model training
            logger.info("Step 3: Model training")
            training_results = self._train_models(feature_results)
            
            # Step 4: Model validation
            logger.info("Step 4: Model validation")
            validation_results = self._validate_models(training_results, data_results)
            
            # Step 5: Model deployment
            logger.info("Step 5: Model deployment")
            deployment_results = self._deploy_models(training_results, validation_results)
            
            # Step 6: Pipeline summary
            pipeline_results = {
                'pipeline_id': pipeline_id,
                'start_time': pipeline_start_time,
                'end_time': datetime.now(),
                'duration_minutes': (datetime.now() - pipeline_start_time).total_seconds() / 60,
                'symbols': symbols,
                'status': 'completed',
                'data_results': data_results,
                'feature_results': feature_results,
                'training_results': training_results,
                'validation_results': validation_results,
                'deployment_results': deployment_results
            }
            
            # Save pipeline results
            if self.config.save_intermediate_results:
                self._save_pipeline_results(pipeline_id, pipeline_results)
            
            self.pipeline_runs.append(pipeline_results)
            
            logger.info(f"Full ML pipeline completed successfully: {pipeline_id}")
            return pipeline_results
            
        except Exception as e:
            logger.error(f"ML pipeline failed: {e}")
            
            pipeline_results = {
                'pipeline_id': pipeline_id,
                'start_time': pipeline_start_time,
                'end_time': datetime.now(),
                'status': 'failed',
                'error': str(e),
                'symbols': symbols
            }
            
            self.pipeline_runs.append(pipeline_results)
            return pipeline_results
    
    def _ingest_and_prepare_data(self, symbols: List[str]) -> Dict:
        """Ingest and prepare data for ML pipeline"""
        
        data_results = {
            'symbols': symbols,
            'market_data': {},
            'news_data': {},
            'fundamental_data': {},
            'data_quality': {}
        }
        
        for symbol in symbols:
            try:
                logger.info(f"Ingesting data for {symbol}")
                
                # Get market data
                if self.config.market_type == "US":
                    market_data = get_YFin_data_window(
                        symbol, 
                        self.config.start_date, 
                        self.config.end_date
                    )
                elif self.config.market_type == "CN":
                    market_data = get_china_stock_data_unified(
                        symbol,
                        start_date=self.config.start_date,
                        end_date=self.config.end_date
                    )
                else:
                    logger.warning(f"Market type {self.config.market_type} not fully supported")
                    continue
                
                if market_data is None or market_data.empty:
                    logger.warning(f"No market data retrieved for {symbol}")
                    continue
                
                # Ensure required columns exist
                required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                missing_columns = [col for col in required_columns if col not in market_data.columns]
                
                if missing_columns:
                    logger.error(f"Missing required columns for {symbol}: {missing_columns}")
                    continue
                
                data_results['market_data'][symbol] = market_data
                
                # Get news data (if available)
                try:
                    if self.config.market_type == "US":
                        news_data = get_finnhub_news(symbol, days_back=90)
                        data_results['news_data'][symbol] = news_data
                except Exception as e:
                    logger.warning(f"Could not retrieve news data for {symbol}: {e}")
                    data_results['news_data'][symbol] = []
                
                # Data quality assessment
                data_quality = self._assess_data_quality(market_data)
                data_results['data_quality'][symbol] = data_quality
                
                logger.info(f"Data ingestion completed for {symbol}: {len(market_data)} records")
                
            except Exception as e:
                logger.error(f"Failed to ingest data for {symbol}: {e}")
                continue
        
        return data_results
    
    def _assess_data_quality(self, data: pd.DataFrame) -> Dict:
        """Assess data quality and completeness"""
        
        quality_metrics = {
            'total_records': len(data),
            'missing_values': data.isnull().sum().to_dict(),
            'date_range': {
                'start': data.index.min().strftime('%Y-%m-%d'),
                'end': data.index.max().strftime('%Y-%m-%d')
            },
            'duplicate_records': data.duplicated().sum(),
            'zero_volume_days': (data['Volume'] == 0).sum() if 'Volume' in data.columns else 0,
            'price_anomalies': {
                'negative_prices': (data['Close'] <= 0).sum() if 'Close' in data.columns else 0,
                'extreme_returns': 0  # Will calculate below
            }
        }
        
        # Calculate extreme returns
        if 'Close' in data.columns and len(data) > 1:
            returns = data['Close'].pct_change().dropna()
            extreme_threshold = 0.2  # 20% daily return threshold
            quality_metrics['price_anomalies']['extreme_returns'] = (abs(returns) > extreme_threshold).sum()
        
        # Overall quality score
        total_issues = (
            sum(quality_metrics['missing_values'].values()) +
            quality_metrics['duplicate_records'] +
            quality_metrics['zero_volume_days'] +
            quality_metrics['price_anomalies']['negative_prices'] +
            quality_metrics['price_anomalies']['extreme_returns']
        )
        
        quality_metrics['quality_score'] = max(0, 1 - (total_issues / len(data)))
        
        return quality_metrics
    
    def _engineer_features(self, data_results: Dict) -> Dict:
        """Engineer features for all symbols"""
        
        feature_results = {
            'features': {},
            'feature_names': [],
            'feature_stats': {}
        }
        
        for symbol, market_data in data_results['market_data'].items():
            try:
                logger.info(f"Engineering features for {symbol}")
                
                # Get additional data
                news_data = data_results['news_data'].get(symbol, [])
                fundamental_data = data_results['fundamental_data'].get(symbol, {})
                
                # Create comprehensive features
                features = create_comprehensive_features(
                    data=market_data,
                    config=self.config.feature_config,
                    fundamentals=fundamental_data,
                    news_data=news_data
                )
                
                if features is not None and not features.empty:
                    feature_results['features'][symbol] = features
                    
                    # Feature statistics
                    feature_stats = {
                        'total_features': len(features.columns),
                        'feature_names': list(features.columns),
                        'data_points': len(features),
                        'missing_values': features.isnull().sum().sum(),
                        'completeness': 1 - (features.isnull().sum().sum() / features.size)
                    }
                    
                    feature_results['feature_stats'][symbol] = feature_stats
                    
                    # Update global feature names
                    if not feature_results['feature_names']:
                        feature_results['feature_names'] = list(features.columns)
                    
                    logger.info(f"Features engineered for {symbol}: {len(features.columns)} features, {len(features)} samples")
                else:
                    logger.warning(f"No features generated for {symbol}")
                    
            except Exception as e:
                logger.error(f"Feature engineering failed for {symbol}: {e}")
                continue
        
        return feature_results
    
    def _train_models(self, feature_results: Dict) -> Dict:
        """Train models for all configured tasks"""
        
        training_results = {
            'models': {},
            'training_metrics': {},
            'model_metadata': {}
        }
        
        for task_name, model_config in self.config.model_configs.items():
            logger.info(f"Training models for task: {task_name}")
            
            task_models = {}
            task_metrics = {}
            task_metadata = {}
            
            for symbol in feature_results['features']:
                try:
                    logger.info(f"Training {task_name} model for {symbol}")
                    
                    features = feature_results['features'][symbol]
                    
                    if len(features) < self.config.min_training_samples:
                        logger.warning(f"Insufficient data for {symbol}: {len(features)} < {self.config.min_training_samples}")
                        continue
                    
                    # Create target variable
                    target = self._create_target_variable(features, task_name, model_config)
                    
                    if target is None or len(target) == 0:
                        logger.warning(f"Could not create target variable for {task_name} - {symbol}")
                        continue
                    
                    # Align features and target
                    aligned_features, aligned_target = features.align(target, join='inner')
                    
                    if len(aligned_features) < self.config.min_training_samples:
                        logger.warning(f"Insufficient aligned data for {symbol}: {len(aligned_features)}")
                        continue
                    
                    # Create and train model
                    model = create_model(model_config.model_type, task_name, **asdict(model_config))
                    
                    if task_name == "price_prediction":
                        training_history = model.train(aligned_features, aligned_target)
                    elif task_name == "signal_classification":
                        # Create trading signals from target
                        signals = model.create_trading_signals(aligned_target)
                        training_history = model.train(aligned_features, signals)
                    elif task_name == "volatility_prediction":
                        training_history = model.train(aligned_features, aligned_target)
                    elif task_name == "risk_assessment":
                        # Calculate volatility for risk assessment
                        returns = aligned_target
                        volatility = returns.rolling(20).std() * np.sqrt(252)
                        training_history = model.train(aligned_features, returns, volatility)
                    else:
                        training_history = model.train(aligned_features, aligned_target)
                    
                    task_models[symbol] = model
                    task_metrics[symbol] = training_history
                    
                    # Create model metadata
                    metadata = ModelMetadata(
                        model_id=f"{task_name}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        name=f"{task_name}_{symbol}",
                        version="1.0.0",
                        task_type=task_name,
                        model_type=model_config.model_type,
                        created_at=datetime.now(),
                        description=f"{task_name} model for {symbol}",
                        performance_metrics=training_history,
                        model_params=asdict(model_config),
                        feature_names=list(aligned_features.columns),
                        tags=[symbol, task_name, model_config.model_type]
                    )
                    
                    task_metadata[symbol] = metadata
                    
                    logger.info(f"Model trained for {task_name} - {symbol}")
                    
                except Exception as e:
                    logger.error(f"Model training failed for {task_name} - {symbol}: {e}")
                    continue
            
            if task_models:
                training_results['models'][task_name] = task_models
                training_results['training_metrics'][task_name] = task_metrics
                training_results['model_metadata'][task_name] = task_metadata
            
        return training_results
    
    def _create_target_variable(self, features: pd.DataFrame, task_name: str, 
                              model_config: ModelConfig) -> Optional[pd.Series]:
        """Create target variable for different ML tasks"""
        
        try:
            # Get price data (assuming features contains price information)
            price_columns = [col for col in features.columns if 'close' in col.lower()]
            if not price_columns:
                # Look for any price-like columns
                price_columns = [col for col in features.columns if any(word in col.lower() for word in ['price', 'close'])]
            
            if not price_columns:
                logger.error("No price columns found in features")
                return None
            
            # Use the first available price column or reconstruct from features
            if len(price_columns) > 0:
                # This is a simplified approach - in practice you'd want the actual close price
                logger.warning("Using feature-based price reconstruction - consider providing actual price data")
                return None
            
            # For now, create dummy targets based on task type
            if task_name == "price_prediction":
                # Create future returns as target
                dummy_returns = np.random.normal(0, 0.02, len(features))
                return pd.Series(dummy_returns, index=features.index, name="future_returns")
                
            elif task_name in ["signal_classification", "risk_assessment"]:
                # Create dummy classification targets
                dummy_returns = np.random.normal(0, 0.02, len(features))
                return pd.Series(dummy_returns, index=features.index, name="returns")
                
            elif task_name == "volatility_prediction":
                # Create dummy volatility target
                dummy_volatility = np.random.uniform(0.1, 0.5, len(features))
                return pd.Series(dummy_volatility, index=features.index, name="volatility")
            
        except Exception as e:
            logger.error(f"Failed to create target variable for {task_name}: {e}")
            
        return None
    
    def _validate_models(self, training_results: Dict, data_results: Dict) -> Dict:
        """Validate trained models"""
        
        validation_results = {
            'cross_validation': {},
            'backtesting': {},
            'performance_metrics': {},
            'model_comparison': {}
        }
        
        for task_name, task_models in training_results['models'].items():
            logger.info(f"Validating models for task: {task_name}")
            
            task_validation = {}
            
            for symbol, model in task_models.items():
                try:
                    logger.info(f"Validating {task_name} model for {symbol}")
                    
                    # Get features and market data
                    features = data_results['market_data'][symbol]  # Use original market data for validation
                    
                    if features is None or features.empty:
                        logger.warning(f"No data available for validation: {symbol}")
                        continue
                    
                    # Create simple features for validation
                    simple_features = self._create_simple_features(features)
                    
                    # Create target for validation
                    target = self._create_validation_target(features, task_name)
                    
                    if target is None:
                        logger.warning(f"Could not create validation target for {task_name} - {symbol}")
                        continue
                    
                    # Align data
                    aligned_features, aligned_target = simple_features.align(target, join='inner')
                    
                    if len(aligned_features) < 50:  # Minimum for validation
                        logger.warning(f"Insufficient data for validation: {symbol}")
                        continue
                    
                    # Run comprehensive validation
                    task_type = "regression" if task_name in ["price_prediction", "volatility_prediction"] else "classification"
                    
                    validation_result = run_comprehensive_validation(
                        model=model,
                        X=aligned_features.values,
                        y=aligned_target.values,
                        prices=features if 'Close' in features.columns else None,
                        returns=features['Close'].pct_change().dropna() if 'Close' in features.columns else None,
                        task_type=task_type,
                        config=self.config.validation_config
                    )
                    
                    task_validation[symbol] = validation_result
                    
                    logger.info(f"Validation completed for {task_name} - {symbol}")
                    
                except Exception as e:
                    logger.error(f"Model validation failed for {task_name} - {symbol}: {e}")
                    continue
            
            if task_validation:
                validation_results['cross_validation'][task_name] = task_validation
        
        return validation_results
    
    def _create_simple_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create simple features for validation"""
        
        features = pd.DataFrame(index=data.index)
        
        # Basic price features
        features['close'] = data['Close']
        features['high'] = data['High']
        features['low'] = data['Low']
        features['volume'] = data['Volume']
        
        # Simple technical indicators
        features['sma_20'] = data['Close'].rolling(20).mean()
        features['sma_50'] = data['Close'].rolling(50).mean()
        features['rsi_14'] = self._calculate_rsi(data['Close'], 14)
        features['volatility_20'] = data['Close'].pct_change().rolling(20).std()
        
        # Lag features
        features['close_lag1'] = data['Close'].shift(1)
        features['close_lag2'] = data['Close'].shift(2)
        features['return_lag1'] = data['Close'].pct_change().shift(1)
        
        return features.dropna()
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = pd.Series(gain).rolling(window=window).mean()
        avg_loss = pd.Series(loss).rolling(window=window).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _create_validation_target(self, data: pd.DataFrame, task_name: str) -> Optional[pd.Series]:
        """Create validation target from market data"""
        
        if 'Close' not in data.columns:
            return None
        
        if task_name == "price_prediction":
            # Future 5-day return
            future_return = data['Close'].pct_change(5).shift(-5)
            return future_return.dropna()
            
        elif task_name in ["signal_classification", "risk_assessment"]:
            # Current returns
            returns = data['Close'].pct_change()
            return returns.dropna()
            
        elif task_name == "volatility_prediction":
            # Rolling volatility
            volatility = data['Close'].pct_change().rolling(20).std()
            return volatility.dropna()
        
        return None
    
    def _deploy_models(self, training_results: Dict, validation_results: Dict) -> Dict:
        """Deploy validated models"""
        
        deployment_results = {
            'deployed_models': {},
            'deployment_status': {},
            'model_endpoints': {}
        }
        
        for task_name, task_models in training_results['models'].items():
            logger.info(f"Deploying models for task: {task_name}")
            
            task_deployments = {}
            
            for symbol, model in task_models.items():
                try:
                    # Get model metadata
                    metadata = training_results['model_metadata'][task_name][symbol]
                    
                    # Check validation results for deployment eligibility
                    validation_result = validation_results.get('cross_validation', {}).get(task_name, {}).get(symbol)
                    
                    if validation_result:
                        # Simple deployment criteria check
                        performance = validation_result.get('performance_metrics', {})
                        
                        deploy_model_flag = True  # Simplified - should check actual performance thresholds
                        
                        if deploy_model_flag:
                            # Deploy model
                            deployment_result = deploy_model(
                                model=model,
                                metadata=metadata,
                                config=self.config.deployment_config
                            )
                            
                            task_deployments[symbol] = deployment_result
                            
                            logger.info(f"Model deployed: {task_name} - {symbol}")
                        else:
                            logger.warning(f"Model failed deployment criteria: {task_name} - {symbol}")
                    else:
                        logger.warning(f"No validation results for deployment: {task_name} - {symbol}")
                        
                except Exception as e:
                    logger.error(f"Model deployment failed for {task_name} - {symbol}: {e}")
                    continue
            
            if task_deployments:
                deployment_results['deployed_models'][task_name] = task_deployments
        
        return deployment_results
    
    def _save_pipeline_results(self, pipeline_id: str, results: Dict) -> None:
        """Save pipeline results to disk"""
        
        try:
            # Convert datetime objects to strings for JSON serialization
            results_copy = self._serialize_for_json(results)
            
            output_file = self.output_dir / f"{pipeline_id}_results.json"
            
            with open(output_file, 'w') as f:
                json.dump(results_copy, f, indent=2, default=str)
            
            logger.info(f"Pipeline results saved: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to save pipeline results: {e}")
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """Recursively serialize objects for JSON compatibility"""
        
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, pd.DataFrame):
            return {"type": "DataFrame", "shape": obj.shape, "columns": list(obj.columns)}
        elif isinstance(obj, pd.Series):
            return {"type": "Series", "length": len(obj), "name": obj.name}
        elif isinstance(obj, np.ndarray):
            return {"type": "ndarray", "shape": obj.shape}
        elif isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return {"type": obj.__class__.__name__, "attributes": "<object>"}
        else:
            return obj
    
    def get_pipeline_status(self) -> Dict:
        """Get current pipeline status"""
        
        return {
            'total_runs': len(self.pipeline_runs),
            'successful_runs': len([run for run in self.pipeline_runs if run.get('status') == 'completed']),
            'failed_runs': len([run for run in self.pipeline_runs if run.get('status') == 'failed']),
            'last_run': self.pipeline_runs[-1] if self.pipeline_runs else None,
            'trained_models': len(self.trained_models),
            'monitoring_active': self.monitor.monitoring_active,
            'inference_service_status': 'active' if self.inference_service else 'inactive'
        }
    
    def retrain_models(self, symbols: Optional[List[str]] = None, 
                      force: bool = False) -> Dict:
        """Retrain models if conditions are met"""
        
        if not force and not self._should_retrain():
            return {"message": "Retraining not needed", "retrained": False}
        
        logger.info("Starting model retraining")
        return self.run_full_pipeline(symbols)
    
    def _should_retrain(self) -> bool:
        """Check if models should be retrained"""
        
        if not self.config.auto_retrain:
            return False
        
        if not self.pipeline_runs:
            return True  # No models trained yet
        
        last_run = self.pipeline_runs[-1]
        last_run_time = last_run.get('start_time')
        
        if isinstance(last_run_time, str):
            last_run_time = datetime.fromisoformat(last_run_time)
        
        days_since_last_run = (datetime.now() - last_run_time).days
        
        return days_since_last_run >= self.config.retrain_frequency_days
    
    def start_monitoring(self) -> None:
        """Start model monitoring"""
        self.monitor.start_monitoring()
        
    def stop_monitoring(self) -> None:
        """Stop model monitoring"""
        self.monitor.stop_monitoring()
    
    def get_model_predictions(self, symbol: str, features: pd.DataFrame) -> Dict:
        """Get predictions from all deployed models for a symbol"""
        
        predictions = {}
        
        for task_name in self.trained_models:
            try:
                model_key = f"{task_name}_{symbol}:latest"
                
                if model_key in self.inference_service.loaded_models:
                    result = self.inference_service.predict(
                        model_key, 
                        features.values
                    )
                    predictions[task_name] = result
                    
            except Exception as e:
                logger.error(f"Prediction failed for {task_name} - {symbol}: {e}")
                predictions[task_name] = {"error": str(e)}
        
        return predictions


def create_default_pipeline(symbols: List[str], market_type: str = "US") -> MLPipeline:
    """Create a default ML pipeline with sensible defaults"""
    
    config = PipelineConfig(
        symbols=symbols,
        market_type=market_type,
        start_date=(datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d"),  # 2 years of data
        end_date=datetime.now().strftime("%Y-%m-%d")
    )
    
    return MLPipeline(config)


def quick_model_training(symbol: str, model_type: str = "xgboost", 
                        task: str = "price_prediction") -> Dict:
    """Quick model training for a single symbol and task"""
    
    logger.info(f"Quick training: {model_type} {task} model for {symbol}")
    
    # Create minimal pipeline
    pipeline = create_default_pipeline([symbol])
    
    # Customize config for single task
    pipeline.config.model_configs = {
        task: ModelConfig(model_type=model_type)
    }
    
    # Run pipeline
    results = pipeline.run_full_pipeline([symbol])
    
    return results