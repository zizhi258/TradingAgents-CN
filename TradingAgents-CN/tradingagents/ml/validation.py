"""Model Validation Framework for Stock Market Analysis

This module provides comprehensive validation capabilities for ML models
including time-series cross-validation, backtesting, performance metrics,
and model drift detection.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns

# Statistical libraries
try:
    from scipy import stats
    from scipy.stats import jarque_bera, normaltest
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    
try:
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import (
        mean_squared_error, mean_absolute_error, r2_score,
        accuracy_score, precision_score, recall_score, f1_score,
        classification_report, confusion_matrix
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# Import logging system
from tradingagents.utils.logging_init import get_logger
logger = get_logger("model_validation")


@dataclass
class ValidationConfig:
    """Configuration for model validation"""
    n_splits: int = 5
    test_size: float = 0.2
    gap: int = 0  # Gap between train and test in time series split
    max_train_size: Optional[int] = None
    
    # Backtesting parameters
    initial_capital: float = 100000.0
    transaction_cost: float = 0.001  # 0.1%
    position_size_method: str = "fixed"  # "fixed", "kelly", "risk_parity"
    max_position_size: float = 0.2  # Maximum position size as fraction of capital
    
    # Performance thresholds
    min_sharpe_ratio: float = 1.0
    max_drawdown_threshold: float = 0.2
    min_accuracy: float = 0.6
    
    # Drift detection parameters
    drift_detection_window: int = 100
    drift_threshold: float = 0.05
    

class BaseValidator(ABC):
    """Base class for model validators"""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.validation_results = {}
        
    @abstractmethod
    def validate(self, model: Any, X: np.ndarray, y: np.ndarray) -> Dict:
        """Validate model performance"""
        pass
    
    def _calculate_basic_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, task_type: str) -> Dict:
        """Calculate basic performance metrics"""
        metrics = {}
        
        if task_type == "regression":
            metrics['mse'] = mean_squared_error(y_true, y_pred)
            metrics['rmse'] = np.sqrt(metrics['mse'])
            metrics['mae'] = mean_absolute_error(y_true, y_pred)
            metrics['r2'] = r2_score(y_true, y_pred)
            
            # Additional regression metrics
            metrics['mape'] = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
            metrics['directional_accuracy'] = self._directional_accuracy(y_true, y_pred)
            
        elif task_type == "classification":
            metrics['accuracy'] = accuracy_score(y_true, y_pred)
            metrics['precision'] = precision_score(y_true, y_pred, average='weighted', zero_division=0)
            metrics['recall'] = recall_score(y_true, y_pred, average='weighted', zero_division=0)
            metrics['f1'] = f1_score(y_true, y_pred, average='weighted', zero_division=0)
            
        return metrics
    
    def _directional_accuracy(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """Calculate directional accuracy (same direction of change)"""
        true_direction = np.sign(np.diff(y_true))
        pred_direction = np.sign(np.diff(y_pred))
        
        return np.mean(true_direction == pred_direction)


class TimeSeriesValidator(BaseValidator):
    """Time-series specific cross-validation"""
    
    def validate(self, model: Any, X: np.ndarray, y: np.ndarray, task_type: str = "regression") -> Dict:
        """Perform time-series cross-validation"""
        logger.info("Performing time-series cross-validation")
        
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for time-series validation")
        
        # Initialize time series split
        tscv = TimeSeriesSplit(
            n_splits=self.config.n_splits,
            gap=self.config.gap,
            max_train_size=self.config.max_train_size,
            test_size=int(len(X) * self.config.test_size / self.config.n_splits)
        )
        
        fold_results = []
        
        for fold, (train_idx, test_idx) in enumerate(tscv.split(X)):
            logger.info(f"Processing fold {fold + 1}/{self.config.n_splits}")
            
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Train model on fold
            fold_model = self._clone_model(model)
            fold_model.train(X_train, y_train)
            
            # Make predictions
            y_pred = fold_model.predict(X_test)
            
            # Calculate metrics
            fold_metrics = self._calculate_basic_metrics(y_test, y_pred, task_type)
            fold_metrics['fold'] = fold + 1
            fold_metrics['train_size'] = len(X_train)
            fold_metrics['test_size'] = len(X_test)
            
            fold_results.append(fold_metrics)
        
        # Aggregate results
        validation_results = self._aggregate_fold_results(fold_results)
        
        self.validation_results = validation_results
        logger.info(f"Time-series validation completed. Average score: {validation_results.get('mean_score', 'N/A')}")
        
        return validation_results
    
    def _clone_model(self, model: Any) -> Any:
        """Clone model for fold validation"""
        # This is a simplified clone - in practice, you'd need model-specific cloning
        try:
            # Try scikit-learn style cloning
            from sklearn.base import clone
            return clone(model)
        except:
            # Fallback: return the same model (not ideal for cross-validation)
            logger.warning("Model cloning not supported, using same model instance")
            return model
    
    def _aggregate_fold_results(self, fold_results: List[Dict]) -> Dict:
        """Aggregate results across folds"""
        aggregated = {}
        
        # Get all metric names (excluding non-numeric fields)
        metric_names = [k for k in fold_results[0].keys() if isinstance(fold_results[0][k], (int, float))]
        
        for metric in metric_names:
            values = [fold[metric] for fold in fold_results]
            aggregated[f'mean_{metric}'] = np.mean(values)
            aggregated[f'std_{metric}'] = np.std(values)
            aggregated[f'min_{metric}'] = np.min(values)
            aggregated[f'max_{metric}'] = np.max(values)
        
        # Overall score (using first available score metric)
        score_metrics = ['r2', 'accuracy', 'f1']
        for metric in score_metrics:
            if f'mean_{metric}' in aggregated:
                aggregated['mean_score'] = aggregated[f'mean_{metric}']
                aggregated['std_score'] = aggregated[f'std_{metric}']
                break
        
        aggregated['fold_results'] = fold_results
        
        return aggregated


class BacktestingFramework(BaseValidator):
    """Comprehensive backtesting framework for trading strategies"""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.portfolio_history = []
        
    def validate(self, model: Any, features: pd.DataFrame, prices: pd.DataFrame, 
                returns: pd.Series, task_type: str = "regression") -> Dict:
        """Perform comprehensive backtesting validation"""
        logger.info("Performing backtesting validation")
        
        # Generate predictions
        if task_type == "regression":
            predictions = model.predict(features.values)
            signals = self._convert_predictions_to_signals(predictions, returns)
        else:
            # For classification, predictions are already signals
            signals = model.predict(features)
            
        # Run backtest
        backtest_results = self._run_backtest(signals, prices, returns)
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(backtest_results)
        
        # Risk analysis
        risk_metrics = self._calculate_risk_metrics(backtest_results, returns)
        
        # Combine all results
        validation_results = {
            'backtest_results': backtest_results,
            'performance_metrics': performance_metrics,
            'risk_metrics': risk_metrics,
            'portfolio_history': self.portfolio_history
        }
        
        self.validation_results = validation_results
        logger.info(f"Backtesting completed. Total return: {performance_metrics.get('total_return', 'N/A'):.2%}")
        
        return validation_results
    
    def _convert_predictions_to_signals(self, predictions: np.ndarray, returns: pd.Series, 
                                      threshold: float = 0.01) -> pd.Series:
        """Convert regression predictions to trading signals"""
        signals = pd.Series(index=returns.index[:len(predictions)], dtype=str)
        
        signals[predictions > threshold] = 'BUY'
        signals[predictions < -threshold] = 'SELL'
        signals[(predictions >= -threshold) & (predictions <= threshold)] = 'HOLD'
        
        return signals
    
    def _run_backtest(self, signals: pd.Series, prices: pd.DataFrame, 
                     returns: pd.Series) -> Dict:
        """Run backtesting simulation"""
        
        # Initialize portfolio
        portfolio = {
            'cash': self.config.initial_capital,
            'positions': 0,
            'portfolio_value': self.config.initial_capital,
            'trades': [],
            'daily_returns': [],
            'daily_values': []
        }
        
        self.portfolio_history = []
        
        # Align signals with prices
        aligned_signals, aligned_prices = signals.align(prices['Close'], join='inner')
        
        for date, signal in aligned_signals.items():
            if date not in aligned_prices.index:
                continue
                
            current_price = aligned_prices[date]
            
            # Calculate current portfolio value
            portfolio_value = portfolio['cash'] + (portfolio['positions'] * current_price)
            
            # Execute trading logic
            if signal == 'BUY' and portfolio['positions'] <= 0:
                # Calculate position size
                position_size = self._calculate_position_size(
                    portfolio_value, current_price, signal, returns.get(date, 0)
                )
                
                if position_size > 0:
                    # Buy
                    cost = position_size * current_price * (1 + self.config.transaction_cost)
                    if cost <= portfolio['cash']:
                        portfolio['cash'] -= cost
                        portfolio['positions'] += position_size
                        
                        portfolio['trades'].append({
                            'date': date,
                            'action': 'BUY',
                            'quantity': position_size,
                            'price': current_price,
                            'cost': cost
                        })
                        
            elif signal == 'SELL' and portfolio['positions'] > 0:
                # Sell all positions
                proceeds = portfolio['positions'] * current_price * (1 - self.config.transaction_cost)
                portfolio['cash'] += proceeds
                
                portfolio['trades'].append({
                    'date': date,
                    'action': 'SELL',
                    'quantity': portfolio['positions'],
                    'price': current_price,
                    'proceeds': proceeds
                })
                
                portfolio['positions'] = 0
            
            # Update portfolio tracking
            portfolio_value = portfolio['cash'] + (portfolio['positions'] * current_price)
            portfolio['portfolio_value'] = portfolio_value
            portfolio['daily_values'].append(portfolio_value)
            
            # Calculate daily return
            if len(portfolio['daily_values']) > 1:
                daily_return = (portfolio_value - portfolio['daily_values'][-2]) / portfolio['daily_values'][-2]
                portfolio['daily_returns'].append(daily_return)
            else:
                portfolio['daily_returns'].append(0)
            
            # Store history
            self.portfolio_history.append({
                'date': date,
                'cash': portfolio['cash'],
                'positions': portfolio['positions'],
                'portfolio_value': portfolio_value,
                'signal': signal,
                'price': current_price
            })
        
        return portfolio
    
    def _calculate_position_size(self, portfolio_value: float, price: float, 
                               signal: str, expected_return: float) -> float:
        """Calculate optimal position size"""
        
        if self.config.position_size_method == "fixed":
            # Fixed fraction of portfolio
            max_investment = portfolio_value * self.config.max_position_size
            return max_investment / price
            
        elif self.config.position_size_method == "kelly":
            # Kelly Criterion (simplified)
            if expected_return > 0:
                # Assume 60% win rate and 1:1 risk-reward for simplicity
                kelly_fraction = (0.6 * 1 - 0.4 * 1) / 1  # Kelly = (bp - q) / b
                kelly_fraction = min(kelly_fraction, self.config.max_position_size)
                max_investment = portfolio_value * max(kelly_fraction, 0)
                return max_investment / price
            else:
                return 0
                
        elif self.config.position_size_method == "risk_parity":
            # Risk parity (simplified - equal risk contribution)
            max_investment = portfolio_value * self.config.max_position_size
            return max_investment / price
        
        return 0
    
    def _calculate_performance_metrics(self, backtest_results: Dict) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        daily_returns = np.array(backtest_results['daily_returns'])
        daily_values = np.array(backtest_results['daily_values'])
        
        if len(daily_values) == 0:
            return {}
        
        metrics = {}
        
        # Basic performance
        initial_value = self.config.initial_capital
        final_value = daily_values[-1] if len(daily_values) > 0 else initial_value
        
        metrics['total_return'] = (final_value - initial_value) / initial_value
        
        # Annualized return
        if len(daily_values) > 1:
            days = len(daily_values)
            metrics['annualized_return'] = (final_value / initial_value) ** (252 / days) - 1
        else:
            metrics['annualized_return'] = 0
        
        # Volatility
        if len(daily_returns) > 1:
            metrics['volatility'] = np.std(daily_returns) * np.sqrt(252)
        else:
            metrics['volatility'] = 0
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        if metrics['volatility'] > 0:
            metrics['sharpe_ratio'] = (metrics['annualized_return'] - risk_free_rate) / metrics['volatility']
        else:
            metrics['sharpe_ratio'] = 0
        
        # Maximum drawdown
        if len(daily_values) > 1:
            peak = np.maximum.accumulate(daily_values)
            drawdown = (daily_values - peak) / peak
            metrics['max_drawdown'] = np.min(drawdown)
        else:
            metrics['max_drawdown'] = 0
        
        # Win rate
        if len(daily_returns) > 0:
            winning_days = np.sum(np.array(daily_returns) > 0)
            metrics['win_rate'] = winning_days / len(daily_returns)
        else:
            metrics['win_rate'] = 0
        
        # Calmar ratio
        if metrics['max_drawdown'] < 0:
            metrics['calmar_ratio'] = metrics['annualized_return'] / abs(metrics['max_drawdown'])
        else:
            metrics['calmar_ratio'] = 0
        
        # Number of trades
        metrics['num_trades'] = len(backtest_results['trades'])
        
        return metrics
    
    def _calculate_risk_metrics(self, backtest_results: Dict, market_returns: pd.Series) -> Dict:
        """Calculate risk-specific metrics"""
        
        daily_returns = np.array(backtest_results['daily_returns'])
        
        if len(daily_returns) == 0:
            return {}
        
        risk_metrics = {}
        
        # Value at Risk (VaR)
        risk_metrics['var_95'] = np.percentile(daily_returns, 5)
        risk_metrics['var_99'] = np.percentile(daily_returns, 1)
        
        # Conditional Value at Risk (CVaR)
        var_95 = risk_metrics['var_95']
        risk_metrics['cvar_95'] = np.mean(daily_returns[daily_returns <= var_95])
        
        # Skewness and Kurtosis
        if SCIPY_AVAILABLE and len(daily_returns) > 3:
            risk_metrics['skewness'] = stats.skew(daily_returns)
            risk_metrics['kurtosis'] = stats.kurtosis(daily_returns)
            
            # Jarque-Bera test for normality
            jb_stat, jb_pvalue = jarque_bera(daily_returns)
            risk_metrics['jarque_bera_stat'] = jb_stat
            risk_metrics['jarque_bera_pvalue'] = jb_pvalue
            risk_metrics['is_normal_distribution'] = jb_pvalue > 0.05
        
        # Beta calculation (if market returns available)
        if len(market_returns) > 0 and len(daily_returns) > 1:
            # Align portfolio and market returns
            portfolio_dates = [entry['date'] for entry in self.portfolio_history if 'date' in entry]
            if len(portfolio_dates) == len(daily_returns):
                aligned_market_returns = []
                for date in portfolio_dates:
                    if date in market_returns.index:
                        aligned_market_returns.append(market_returns[date])
                    else:
                        aligned_market_returns.append(0)
                
                if len(aligned_market_returns) == len(daily_returns):
                    market_var = np.var(aligned_market_returns)
                    if market_var > 0:
                        covariance = np.cov(daily_returns, aligned_market_returns)[0, 1]
                        risk_metrics['beta'] = covariance / market_var
                    else:
                        risk_metrics['beta'] = 0
        
        return risk_metrics


class PerformanceMetrics:
    """Comprehensive performance metrics calculator"""
    
    def __init__(self):
        self.metrics = {}
        
    def calculate_all_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, 
                            task_type: str, returns: Optional[pd.Series] = None) -> Dict:
        """Calculate all relevant performance metrics"""
        
        metrics = {}
        
        # Basic metrics
        if task_type == "regression":
            metrics.update(self._regression_metrics(y_true, y_pred))
        elif task_type == "classification":
            metrics.update(self._classification_metrics(y_true, y_pred))
        
        # Financial metrics (if returns provided)
        if returns is not None:
            metrics.update(self._financial_metrics(y_true, y_pred, returns))
        
        # Statistical significance tests
        if SCIPY_AVAILABLE:
            metrics.update(self._statistical_tests(y_true, y_pred))
        
        self.metrics = metrics
        return metrics
    
    def _regression_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Calculate regression-specific metrics"""
        
        metrics = {
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'mae': mean_absolute_error(y_true, y_pred),
            'r2': r2_score(y_true, y_pred)
        }
        
        # Mean Absolute Percentage Error
        non_zero_mask = y_true != 0
        if np.any(non_zero_mask):
            metrics['mape'] = np.mean(np.abs((y_true[non_zero_mask] - y_pred[non_zero_mask]) / y_true[non_zero_mask])) * 100
        else:
            metrics['mape'] = np.inf
        
        # Directional accuracy
        if len(y_true) > 1:
            true_direction = np.sign(np.diff(y_true))
            pred_direction = np.sign(np.diff(y_pred))
            metrics['directional_accuracy'] = np.mean(true_direction == pred_direction)
        
        # Hit rate (for financial predictions)
        threshold = np.std(y_true) * 0.1  # 10% of standard deviation
        hits = np.abs(y_pred - y_true) <= threshold
        metrics['hit_rate'] = np.mean(hits)
        
        return metrics
    
    def _classification_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Calculate classification-specific metrics"""
        
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
            'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
            'f1': f1_score(y_true, y_pred, average='weighted', zero_division=0)
        }
        
        # Per-class metrics
        unique_labels = np.unique(np.concatenate([y_true, y_pred]))
        for label in unique_labels:
            label_mask_true = y_true == label
            label_mask_pred = y_pred == label
            
            if np.any(label_mask_true) and np.any(label_mask_pred):
                metrics[f'precision_{label}'] = precision_score(y_true, y_pred, labels=[label], average=None, zero_division=0)[0]
                metrics[f'recall_{label}'] = recall_score(y_true, y_pred, labels=[label], average=None, zero_division=0)[0]
                metrics[f'f1_{label}'] = f1_score(y_true, y_pred, labels=[label], average=None, zero_division=0)[0]
        
        return metrics
    
    def _financial_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, returns: pd.Series) -> Dict:
        """Calculate finance-specific metrics"""
        
        metrics = {}
        
        # Information Ratio
        if len(returns) > 1:
            benchmark_return = returns.mean()
            excess_returns = y_pred - benchmark_return
            tracking_error = np.std(excess_returns)
            
            if tracking_error > 0:
                metrics['information_ratio'] = np.mean(excess_returns) / tracking_error
            else:
                metrics['information_ratio'] = 0
        
        # Profit factor (for trading signals)
        if np.any(y_pred > 0) and np.any(y_pred < 0):
            gross_profit = np.sum(y_pred[y_pred > 0])
            gross_loss = np.abs(np.sum(y_pred[y_pred < 0]))
            
            if gross_loss > 0:
                metrics['profit_factor'] = gross_profit / gross_loss
            else:
                metrics['profit_factor'] = np.inf
        
        return metrics
    
    def _statistical_tests(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Perform statistical significance tests"""
        
        metrics = {}
        
        # Residuals analysis
        residuals = y_true - y_pred
        
        # Normality tests
        if len(residuals) > 8:  # Minimum sample size for tests
            # Shapiro-Wilk test (for smaller samples)
            if len(residuals) <= 5000:
                shapiro_stat, shapiro_p = stats.shapiro(residuals)
                metrics['shapiro_stat'] = shapiro_stat
                metrics['shapiro_pvalue'] = shapiro_p
            
            # Jarque-Bera test
            jb_stat, jb_p = jarque_bera(residuals)
            metrics['jarque_bera_stat'] = jb_stat
            metrics['jarque_bera_pvalue'] = jb_p
            
            # Anderson-Darling test
            ad_stat, ad_critical, ad_significance = stats.anderson(residuals, dist='norm')
            metrics['anderson_darling_stat'] = ad_stat
            metrics['anderson_darling_critical'] = ad_critical[2]  # 5% significance level
            
            # Ljung-Box test for autocorrelation
            if len(residuals) > 20:
                lb_stat, lb_p = stats.boxljung(residuals, lags=10, return_df=False)
                metrics['ljung_box_stat'] = lb_stat
                metrics['ljung_box_pvalue'] = lb_p
        
        return metrics


class ModelDriftDetector:
    """Detect model drift and performance degradation"""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.baseline_metrics = {}
        self.drift_history = []
        
    def set_baseline(self, y_true: np.ndarray, y_pred: np.ndarray, task_type: str) -> None:
        """Set baseline performance metrics for drift detection"""
        
        metrics_calculator = PerformanceMetrics()
        self.baseline_metrics = metrics_calculator.calculate_all_metrics(y_true, y_pred, task_type)
        
        logger.info(f"Baseline metrics set: {list(self.baseline_metrics.keys())}")
    
    def detect_drift(self, y_true: np.ndarray, y_pred: np.ndarray, task_type: str, 
                    timestamp: Optional[datetime] = None) -> Dict:
        """Detect model drift by comparing current performance to baseline"""
        
        if not self.baseline_metrics:
            raise ValueError("Baseline metrics not set. Call set_baseline() first.")
        
        # Calculate current metrics
        metrics_calculator = PerformanceMetrics()
        current_metrics = metrics_calculator.calculate_all_metrics(y_true, y_pred, task_type)
        
        # Compare with baseline
        drift_results = self._compare_metrics(current_metrics, self.baseline_metrics)
        
        # Statistical tests for drift detection
        statistical_drift = self._statistical_drift_tests(y_true, y_pred)
        
        drift_summary = {
            'timestamp': timestamp or datetime.now(),
            'drift_detected': drift_results['significant_drift'],
            'drift_score': drift_results['overall_drift_score'],
            'metric_changes': drift_results['metric_changes'],
            'statistical_drift': statistical_drift,
            'current_metrics': current_metrics,
            'baseline_metrics': self.baseline_metrics
        }
        
        self.drift_history.append(drift_summary)
        
        if drift_summary['drift_detected']:
            logger.warning(f"Model drift detected! Drift score: {drift_summary['drift_score']:.4f}")
        
        return drift_summary
    
    def _compare_metrics(self, current: Dict, baseline: Dict) -> Dict:
        """Compare current metrics with baseline to detect drift"""
        
        metric_changes = {}
        drift_scores = []
        
        # Key metrics for drift detection
        key_metrics = ['accuracy', 'r2', 'f1', 'mse', 'mae']
        
        for metric in key_metrics:
            if metric in current and metric in baseline:
                current_value = current[metric]
                baseline_value = baseline[metric]
                
                if baseline_value != 0:
                    relative_change = (current_value - baseline_value) / abs(baseline_value)
                else:
                    relative_change = 0 if current_value == 0 else 1
                
                metric_changes[metric] = {
                    'current': current_value,
                    'baseline': baseline_value,
                    'relative_change': relative_change,
                    'absolute_change': current_value - baseline_value
                }
                
                # Calculate drift score for this metric
                drift_score = abs(relative_change)
                drift_scores.append(drift_score)
        
        # Overall drift score
        overall_drift_score = np.mean(drift_scores) if drift_scores else 0
        
        # Determine if significant drift occurred
        significant_drift = overall_drift_score > self.config.drift_threshold
        
        return {
            'metric_changes': metric_changes,
            'overall_drift_score': overall_drift_score,
            'significant_drift': significant_drift
        }
    
    def _statistical_drift_tests(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
        """Perform statistical tests for drift detection"""
        
        statistical_tests = {}
        
        if not SCIPY_AVAILABLE or len(y_true) < 30:
            return statistical_tests
        
        # Kolmogorov-Smirnov test for distribution change
        residuals = y_true - y_pred
        
        # Compare with historical residuals if available
        if len(self.drift_history) > 0:
            # Get historical residuals from baseline
            historical_residuals = np.array([])  # This would come from stored baseline data
            
            if len(historical_residuals) > 0:
                ks_stat, ks_p = stats.ks_2samp(residuals, historical_residuals)
                statistical_tests['ks_test'] = {
                    'statistic': ks_stat,
                    'pvalue': ks_p,
                    'drift_detected': ks_p < 0.05
                }
        
        # Mann-Whitney U test for distribution shift
        if len(residuals) >= 20:
            # Split residuals into two halves
            mid_point = len(residuals) // 2
            first_half = residuals[:mid_point]
            second_half = residuals[mid_point:]
            
            mw_stat, mw_p = stats.mannwhitneyu(first_half, second_half, alternative='two-sided')
            statistical_tests['mann_whitney'] = {
                'statistic': mw_stat,
                'pvalue': mw_p,
                'drift_detected': mw_p < 0.05
            }
        
        return statistical_tests
    
    def get_drift_report(self) -> Dict:
        """Generate comprehensive drift report"""
        
        if not self.drift_history:
            return {"message": "No drift detection history available"}
        
        # Count drift occurrences
        drift_occurrences = sum(1 for entry in self.drift_history if entry['drift_detected'])
        
        # Average drift score
        avg_drift_score = np.mean([entry['drift_score'] for entry in self.drift_history])
        
        # Most recent drift status
        latest_drift = self.drift_history[-1]
        
        return {
            'total_evaluations': len(self.drift_history),
            'drift_occurrences': drift_occurrences,
            'drift_rate': drift_occurrences / len(self.drift_history),
            'average_drift_score': avg_drift_score,
            'latest_drift_status': latest_drift['drift_detected'],
            'latest_drift_score': latest_drift['drift_score'],
            'drift_history': self.drift_history
        }


def run_comprehensive_validation(model: Any, X: np.ndarray, y: np.ndarray, 
                               prices: Optional[pd.DataFrame] = None,
                               returns: Optional[pd.Series] = None,
                               task_type: str = "regression",
                               config: Optional[ValidationConfig] = None) -> Dict:
    """Run comprehensive model validation including all validation methods"""
    
    if config is None:
        config = ValidationConfig()
    
    logger.info("Starting comprehensive model validation")
    
    validation_results = {}
    
    # Time-series cross-validation
    ts_validator = TimeSeriesValidator(config)
    cv_results = ts_validator.validate(model, X, y, task_type)
    validation_results['cross_validation'] = cv_results
    
    # Performance metrics
    y_pred = model.predict(X)
    metrics_calculator = PerformanceMetrics()
    performance_metrics = metrics_calculator.calculate_all_metrics(y_pred, y, task_type, returns)
    validation_results['performance_metrics'] = performance_metrics
    
    # Backtesting (if price data available)
    if prices is not None and returns is not None:
        features_df = pd.DataFrame(X, index=prices.index[:len(X)])
        backtesting_framework = BacktestingFramework(config)
        backtest_results = backtesting_framework.validate(model, features_df, prices, returns, task_type)
        validation_results['backtesting'] = backtest_results
    
    # Model drift detection setup
    drift_detector = ModelDriftDetector(config)
    drift_detector.set_baseline(y, y_pred, task_type)
    validation_results['drift_detector'] = drift_detector
    
    logger.info("Comprehensive validation completed")
    
    return validation_results