"""
Comprehensive Data Quality Monitoring System for TradingAgents-CN

This module implements advanced data quality monitoring with:
- Real-time data validation and cleansing
- Automated anomaly detection
- Data freshness and completeness monitoring
- Quality scoring and reporting
- Alert system for data quality issues
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np
from collections import defaultdict, deque
import statistics
from pathlib import Path
import pickle
from concurrent.futures import ThreadPoolExecutor

# Statistical libraries for advanced analysis
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class DataQualitySeverity(Enum):
    """Data quality issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class QualityMetricType(Enum):
    """Types of data quality metrics"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"


@dataclass
class QualityMetric:
    """Data quality metric definition"""
    name: str
    metric_type: QualityMetricType
    description: str
    threshold: float
    severity: DataQualitySeverity
    enabled: bool = True
    alert_frequency: int = 3600  # seconds


@dataclass
class QualityResult:
    """Result of a quality check"""
    metric_name: str
    value: float
    threshold: float
    passed: bool
    severity: DataQualitySeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    affected_records: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['severity'] = self.severity.value
        return result


@dataclass
class DataQualityReport:
    """Comprehensive data quality report"""
    report_id: str
    dataset_name: str
    start_time: datetime
    end_time: datetime
    total_records: int
    overall_score: float
    metrics: List[QualityResult]
    summary: Dict[str, Any]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'report_id': self.report_id,
            'dataset_name': self.dataset_name,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'total_records': self.total_records,
            'overall_score': self.overall_score,
            'metrics': [metric.to_dict() for metric in self.metrics],
            'summary': self.summary,
            'recommendations': self.recommendations
        }


class AnomalyDetector:
    """Advanced anomaly detection for market data"""
    
    def __init__(self, contamination: float = 0.1):
        self.contamination = contamination
        self.models = {}
        self.scalers = {}
        self.baseline_stats = {}
        self.window_size = 100
        self.min_samples = 20
        
    def fit_symbol_model(self, symbol: str, historical_data: List[Dict[str, Any]]):
        """Fit anomaly detection model for a specific symbol"""
        try:
            if len(historical_data) < self.min_samples:
                logging.warning(f"Insufficient data for {symbol} anomaly model: {len(historical_data)} samples")
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(historical_data)
            
            # Select numerical features
            numerical_cols = ['open', 'high', 'low', 'close', 'volume']
            feature_cols = [col for col in numerical_cols if col in df.columns]
            
            if not feature_cols:
                logging.warning(f"No numerical features found for {symbol}")
                return
            
            # Prepare features
            features = df[feature_cols].values
            
            # Handle missing values
            mask = ~np.isnan(features).any(axis=1)
            features = features[mask]
            
            if len(features) < self.min_samples:
                logging.warning(f"Insufficient clean data for {symbol}: {len(features)} samples")
                return
            
            # Scale features
            scaler = StandardScaler()
            scaled_features = scaler.fit_transform(features)
            
            # Fit isolation forest
            model = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
            model.fit(scaled_features)
            
            # Calculate baseline statistics
            baseline_stats = {}
            for i, col in enumerate(feature_cols):
                col_data = features[:, i]
                baseline_stats[col] = {
                    'mean': float(np.mean(col_data)),
                    'std': float(np.std(col_data)),
                    'min': float(np.min(col_data)),
                    'max': float(np.max(col_data)),
                    'p25': float(np.percentile(col_data, 25)),
                    'p75': float(np.percentile(col_data, 75))
                }
            
            # Store models and metadata
            self.models[symbol] = {
                'model': model,
                'features': feature_cols,
                'trained_samples': len(features),
                'trained_at': datetime.now()
            }
            self.scalers[symbol] = scaler
            self.baseline_stats[symbol] = baseline_stats
            
            logging.info(f"Anomaly model trained for {symbol} with {len(features)} samples")
            
        except Exception as e:
            logging.error(f"Failed to fit anomaly model for {symbol}: {e}")
    
    def detect_anomalies(self, symbol: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect anomalies in new data"""
        try:
            if symbol not in self.models:
                return []
            
            model_info = self.models[symbol]
            model = model_info['model']
            feature_cols = model_info['features']
            scaler = self.scalers[symbol]
            baseline = self.baseline_stats[symbol]
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Check if required features exist
            missing_features = [col for col in feature_cols if col not in df.columns]
            if missing_features:
                logging.warning(f"Missing features for {symbol}: {missing_features}")
                return []
            
            # Prepare features
            features = df[feature_cols].values
            
            # Handle missing values
            mask = ~np.isnan(features).any(axis=1)
            clean_features = features[mask]
            clean_indices = np.where(mask)[0]
            
            if len(clean_features) == 0:
                return []
            
            # Scale features
            scaled_features = scaler.transform(clean_features)
            
            # Predict anomalies
            anomaly_scores = model.decision_function(scaled_features)
            predictions = model.predict(scaled_features)
            
            # Generate anomaly reports
            anomalies = []
            for i, (idx, score, pred) in enumerate(zip(clean_indices, anomaly_scores, predictions)):
                if pred == -1:  # Anomaly detected
                    record = data[idx]
                    
                    # Calculate feature deviations from baseline
                    deviations = {}
                    for j, col in enumerate(feature_cols):
                        value = clean_features[i, j]
                        base_stats = baseline[col]
                        
                        # Calculate z-score
                        z_score = (value - base_stats['mean']) / base_stats['std'] if base_stats['std'] > 0 else 0
                        
                        # Calculate percentile deviation
                        if value < base_stats['p25']:
                            percentile_dev = (base_stats['p25'] - value) / (base_stats['p25'] - base_stats['min']) if base_stats['p25'] != base_stats['min'] else 0
                        elif value > base_stats['p75']:
                            percentile_dev = (value - base_stats['p75']) / (base_stats['max'] - base_stats['p75']) if base_stats['max'] != base_stats['p75'] else 0
                        else:
                            percentile_dev = 0
                        
                        deviations[col] = {
                            'value': float(value),
                            'baseline_mean': base_stats['mean'],
                            'z_score': float(z_score),
                            'percentile_deviation': float(percentile_dev)
                        }
                    
                    anomaly = {
                        'symbol': symbol,
                        'record_index': int(idx),
                        'anomaly_score': float(score),
                        'timestamp': record.get('timestamp', datetime.now().isoformat()),
                        'record_data': record,
                        'feature_deviations': deviations,
                        'detected_at': datetime.now().isoformat()
                    }
                    
                    anomalies.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logging.error(f"Anomaly detection failed for {symbol}: {e}")
            return []
    
    def update_model(self, symbol: str, new_data: List[Dict[str, Any]]):
        """Update anomaly model with new data (incremental learning)"""
        try:
            if symbol not in self.models or len(new_data) < 10:
                return
            
            model_info = self.models[symbol]
            last_update = model_info.get('last_update', model_info['trained_at'])
            
            # Only update if enough time has passed and enough new data
            if (datetime.now() - last_update).seconds < 3600 or len(new_data) < 20:
                return
            
            # Retrain model with recent data
            # In production, you might want to use online learning techniques
            recent_data = new_data[-self.window_size:]
            self.fit_symbol_model(symbol, recent_data)
            
            if symbol in self.models:
                self.models[symbol]['last_update'] = datetime.now()
                logging.info(f"Updated anomaly model for {symbol} with {len(new_data)} new samples")
                
        except Exception as e:
            logging.error(f"Model update failed for {symbol}: {e}")


class DataQualityMonitor:
    """Comprehensive data quality monitoring system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("data_quality_monitor")
        
        # Initialize components
        self.anomaly_detector = AnomalyDetector(
            contamination=config.get('anomaly_contamination', 0.05)
        )
        
        # Quality metrics configuration
        self.quality_metrics = self._load_quality_metrics()
        
        # Alert system
        self.alert_history = defaultdict(deque)
        self.alert_cooldown = {}
        
        # Quality history for trending
        self.quality_history = defaultdict(lambda: deque(maxlen=1000))
        
        # Statistical models for trend analysis
        self.trend_models = {}
        
        # Performance tracking
        self.performance_stats = {
            'checks_performed': 0,
            'anomalies_detected': 0,
            'quality_score_trend': deque(maxlen=100),
            'last_check_time': None
        }
    
    def _load_quality_metrics(self) -> List[QualityMetric]:
        """Load quality metrics configuration"""
        return [
            # Completeness metrics
            QualityMetric(
                name="data_completeness_required_fields",
                metric_type=QualityMetricType.COMPLETENESS,
                description="Percentage of records with all required fields",
                threshold=0.95,
                severity=DataQualitySeverity.ERROR
            ),
            QualityMetric(
                name="data_completeness_optional_fields",
                metric_type=QualityMetricType.COMPLETENESS,
                description="Percentage of records with optional fields",
                threshold=0.80,
                severity=DataQualitySeverity.WARNING
            ),
            
            # Accuracy metrics
            QualityMetric(
                name="price_range_validity",
                metric_type=QualityMetricType.ACCURACY,
                description="Percentage of prices within expected ranges",
                threshold=0.99,
                severity=DataQualitySeverity.ERROR
            ),
            QualityMetric(
                name="ohlc_consistency",
                metric_type=QualityMetricType.CONSISTENCY,
                description="Percentage of OHLC records with consistent values",
                threshold=0.98,
                severity=DataQualitySeverity.ERROR
            ),
            
            # Timeliness metrics
            QualityMetric(
                name="data_freshness",
                metric_type=QualityMetricType.TIMELINESS,
                description="Data freshness score (0-1)",
                threshold=0.90,
                severity=DataQualitySeverity.WARNING
            ),
            QualityMetric(
                name="update_frequency",
                metric_type=QualityMetricType.TIMELINESS,
                description="Update frequency consistency score",
                threshold=0.85,
                severity=DataQualitySeverity.WARNING
            ),
            
            # Uniqueness metrics
            QualityMetric(
                name="duplicate_records",
                metric_type=QualityMetricType.UNIQUENESS,
                description="Percentage of unique records",
                threshold=0.99,
                severity=DataQualitySeverity.WARNING
            ),
            
            # Validity metrics
            QualityMetric(
                name="data_type_validity",
                metric_type=QualityMetricType.VALIDITY,
                description="Percentage of fields with correct data types",
                threshold=0.99,
                severity=DataQualitySeverity.ERROR
            ),
            QualityMetric(
                name="business_rule_validity",
                metric_type=QualityMetricType.VALIDITY,
                description="Percentage of records passing business rules",
                threshold=0.95,
                severity=DataQualitySeverity.ERROR
            )
        ]
    
    async def monitor_data_quality(self, dataset_name: str, data: List[Dict[str, Any]], 
                                 metadata: Dict[str, Any] = None) -> DataQualityReport:
        """Perform comprehensive data quality monitoring"""
        start_time = datetime.now()
        report_id = f"dq_{dataset_name}_{int(start_time.timestamp())}"
        
        if not data:
            return DataQualityReport(
                report_id=report_id,
                dataset_name=dataset_name,
                start_time=start_time,
                end_time=datetime.now(),
                total_records=0,
                overall_score=0.0,
                metrics=[],
                summary={'error': 'No data provided'},
                recommendations=['Ensure data is available before quality checks']
            )
        
        try:
            self.logger.info(f"Starting data quality monitoring for {dataset_name} with {len(data)} records")
            
            # Run quality checks
            quality_results = []
            
            # Execute quality metrics
            for metric in self.quality_metrics:
                if metric.enabled:
                    try:
                        result = await self._execute_quality_metric(metric, data, metadata)
                        quality_results.append(result)
                        
                        # Update quality history
                        self.quality_history[f"{dataset_name}_{metric.name}"].append(result.value)
                        
                    except Exception as e:
                        self.logger.error(f"Quality metric {metric.name} failed: {e}")
                        
                        error_result = QualityResult(
                            metric_name=metric.name,
                            value=0.0,
                            threshold=metric.threshold,
                            passed=False,
                            severity=DataQualitySeverity.CRITICAL,
                            message=f"Metric execution failed: {str(e)}",
                            details={'error': str(e)},
                            timestamp=datetime.now(),
                            affected_records=len(data)
                        )
                        quality_results.append(error_result)
            
            # Detect anomalies
            anomalies = await self._detect_data_anomalies(dataset_name, data)
            
            # Calculate overall quality score
            overall_score = self._calculate_overall_score(quality_results)
            
            # Update performance stats
            self.performance_stats['checks_performed'] += 1
            self.performance_stats['anomalies_detected'] += len(anomalies)
            self.performance_stats['quality_score_trend'].append(overall_score)
            self.performance_stats['last_check_time'] = datetime.now()
            
            # Generate summary and recommendations
            summary = self._generate_summary(quality_results, anomalies)
            recommendations = self._generate_recommendations(quality_results, anomalies)
            
            # Create report
            end_time = datetime.now()
            report = DataQualityReport(
                report_id=report_id,
                dataset_name=dataset_name,
                start_time=start_time,
                end_time=end_time,
                total_records=len(data),
                overall_score=overall_score,
                metrics=quality_results,
                summary=summary,
                recommendations=recommendations
            )
            
            # Check for alerts
            await self._check_and_send_alerts(report)
            
            # Store report
            await self._store_quality_report(report)
            
            self.logger.info(f"Data quality monitoring completed for {dataset_name}. Score: {overall_score:.2f}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Data quality monitoring failed for {dataset_name}: {e}")
            
            error_report = DataQualityReport(
                report_id=report_id,
                dataset_name=dataset_name,
                start_time=start_time,
                end_time=datetime.now(),
                total_records=len(data) if data else 0,
                overall_score=0.0,
                metrics=[],
                summary={'error': str(e)},
                recommendations=['Review data quality monitoring system configuration']
            )
            
            return error_report
    
    async def _execute_quality_metric(self, metric: QualityMetric, data: List[Dict[str, Any]], 
                                    metadata: Dict[str, Any]) -> QualityResult:
        """Execute a specific quality metric"""
        start_time = datetime.now()
        
        try:
            if metric.metric_type == QualityMetricType.COMPLETENESS:
                result = self._check_completeness(metric, data)
            elif metric.metric_type == QualityMetricType.ACCURACY:
                result = self._check_accuracy(metric, data)
            elif metric.metric_type == QualityMetricType.CONSISTENCY:
                result = self._check_consistency(metric, data)
            elif metric.metric_type == QualityMetricType.TIMELINESS:
                result = self._check_timeliness(metric, data, metadata)
            elif metric.metric_type == QualityMetricType.VALIDITY:
                result = self._check_validity(metric, data)
            elif metric.metric_type == QualityMetricType.UNIQUENESS:
                result = self._check_uniqueness(metric, data)
            else:
                raise ValueError(f"Unknown metric type: {metric.metric_type}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            result.details['execution_time_ms'] = execution_time * 1000
            
            return result
            
        except Exception as e:
            return QualityResult(
                metric_name=metric.name,
                value=0.0,
                threshold=metric.threshold,
                passed=False,
                severity=DataQualitySeverity.CRITICAL,
                message=f"Metric execution error: {str(e)}",
                details={'error': str(e)},
                timestamp=datetime.now(),
                affected_records=len(data)
            )
    
    def _check_completeness(self, metric: QualityMetric, data: List[Dict[str, Any]]) -> QualityResult:
        """Check data completeness"""
        total_records = len(data)
        
        if metric.name == "data_completeness_required_fields":
            required_fields = ['symbol', 'timestamp', 'open', 'high', 'low', 'close']
            complete_records = 0
            
            for record in data:
                if all(field in record and record[field] is not None for field in required_fields):
                    complete_records += 1
            
            completeness_score = complete_records / total_records if total_records > 0 else 0
            
            return QualityResult(
                metric_name=metric.name,
                value=completeness_score,
                threshold=metric.threshold,
                passed=completeness_score >= metric.threshold,
                severity=metric.severity,
                message=f"Required fields completeness: {completeness_score:.2%}",
                details={
                    'complete_records': complete_records,
                    'total_records': total_records,
                    'required_fields': required_fields
                },
                timestamp=datetime.now(),
                affected_records=total_records - complete_records
            )
        
        elif metric.name == "data_completeness_optional_fields":
            optional_fields = ['volume', 'amount', 'turnover']
            field_completeness = {}
            
            for field in optional_fields:
                complete_count = sum(1 for record in data if field in record and record[field] is not None)
                field_completeness[field] = complete_count / total_records if total_records > 0 else 0
            
            avg_completeness = statistics.mean(field_completeness.values()) if field_completeness else 0
            
            return QualityResult(
                metric_name=metric.name,
                value=avg_completeness,
                threshold=metric.threshold,
                passed=avg_completeness >= metric.threshold,
                severity=metric.severity,
                message=f"Optional fields completeness: {avg_completeness:.2%}",
                details={
                    'field_completeness': field_completeness,
                    'average_completeness': avg_completeness
                },
                timestamp=datetime.now(),
                affected_records=0
            )
        
        return QualityResult(
            metric_name=metric.name,
            value=0.0,
            threshold=metric.threshold,
            passed=False,
            severity=DataQualitySeverity.ERROR,
            message="Unknown completeness metric",
            details={},
            timestamp=datetime.now()
        )
    
    def _check_accuracy(self, metric: QualityMetric, data: List[Dict[str, Any]]) -> QualityResult:
        """Check data accuracy"""
        total_records = len(data)
        
        if metric.name == "price_range_validity":
            valid_records = 0
            price_fields = ['open', 'high', 'low', 'close']
            
            for record in data:
                valid_prices = 0
                total_prices = 0
                
                for field in price_fields:
                    if field in record and record[field] is not None:
                        total_prices += 1
                        price = float(record[field])
                        
                        # Basic price validation (adjust ranges as needed)
                        if 0.01 <= price <= 10000:  # Reasonable price range
                            valid_prices += 1
                
                if total_prices > 0 and valid_prices / total_prices >= 1.0:
                    valid_records += 1
            
            accuracy_score = valid_records / total_records if total_records > 0 else 0
            
            return QualityResult(
                metric_name=metric.name,
                value=accuracy_score,
                threshold=metric.threshold,
                passed=accuracy_score >= metric.threshold,
                severity=metric.severity,
                message=f"Price range validity: {accuracy_score:.2%}",
                details={
                    'valid_records': valid_records,
                    'total_records': total_records,
                    'price_fields': price_fields
                },
                timestamp=datetime.now(),
                affected_records=total_records - valid_records
            )
        
        return QualityResult(
            metric_name=metric.name,
            value=1.0,
            threshold=metric.threshold,
            passed=True,
            severity=metric.severity,
            message="Accuracy check passed",
            details={},
            timestamp=datetime.now()
        )
    
    def _check_consistency(self, metric: QualityMetric, data: List[Dict[str, Any]]) -> QualityResult:
        """Check data consistency"""
        total_records = len(data)
        
        if metric.name == "ohlc_consistency":
            consistent_records = 0
            
            for record in data:
                ohlc_fields = ['open', 'high', 'low', 'close']
                
                if all(field in record and record[field] is not None for field in ohlc_fields):
                    try:
                        open_price = float(record['open'])
                        high_price = float(record['high'])
                        low_price = float(record['low'])
                        close_price = float(record['close'])
                        
                        # Check OHLC consistency
                        if (high_price >= max(open_price, low_price, close_price) and
                            low_price <= min(open_price, high_price, close_price) and
                            high_price >= low_price):
                            consistent_records += 1
                    except (ValueError, TypeError):
                        continue
            
            consistency_score = consistent_records / total_records if total_records > 0 else 0
            
            return QualityResult(
                metric_name=metric.name,
                value=consistency_score,
                threshold=metric.threshold,
                passed=consistency_score >= metric.threshold,
                severity=metric.severity,
                message=f"OHLC consistency: {consistency_score:.2%}",
                details={
                    'consistent_records': consistent_records,
                    'total_records': total_records
                },
                timestamp=datetime.now(),
                affected_records=total_records - consistent_records
            )
        
        return QualityResult(
            metric_name=metric.name,
            value=1.0,
            threshold=metric.threshold,
            passed=True,
            severity=metric.severity,
            message="Consistency check passed",
            details={},
            timestamp=datetime.now()
        )
    
    def _check_timeliness(self, metric: QualityMetric, data: List[Dict[str, Any]], 
                         metadata: Dict[str, Any]) -> QualityResult:
        """Check data timeliness"""
        if metric.name == "data_freshness":
            current_time = datetime.now()
            fresh_records = 0
            total_records = len(data)
            
            # Define freshness threshold (e.g., data should be no older than 1 day)
            freshness_threshold = timedelta(days=1)
            
            for record in data:
                if 'timestamp' in record:
                    try:
                        record_time = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                        if current_time - record_time <= freshness_threshold:
                            fresh_records += 1
                    except:
                        continue
            
            freshness_score = fresh_records / total_records if total_records > 0 else 0
            
            return QualityResult(
                metric_name=metric.name,
                value=freshness_score,
                threshold=metric.threshold,
                passed=freshness_score >= metric.threshold,
                severity=metric.severity,
                message=f"Data freshness: {freshness_score:.2%}",
                details={
                    'fresh_records': fresh_records,
                    'total_records': total_records,
                    'freshness_threshold_hours': freshness_threshold.total_seconds() / 3600
                },
                timestamp=datetime.now(),
                affected_records=total_records - fresh_records
            )
        
        return QualityResult(
            metric_name=metric.name,
            value=1.0,
            threshold=metric.threshold,
            passed=True,
            severity=metric.severity,
            message="Timeliness check passed",
            details={},
            timestamp=datetime.now()
        )
    
    def _check_validity(self, metric: QualityMetric, data: List[Dict[str, Any]]) -> QualityResult:
        """Check data validity"""
        total_records = len(data)
        
        if metric.name == "data_type_validity":
            valid_records = 0
            
            for record in data:
                valid_fields = 0
                total_fields = 0
                
                # Check numeric fields
                numeric_fields = ['open', 'high', 'low', 'close', 'volume']
                for field in numeric_fields:
                    if field in record and record[field] is not None:
                        total_fields += 1
                        try:
                            float(record[field])
                            valid_fields += 1
                        except (ValueError, TypeError):
                            continue
                
                # Check string fields
                string_fields = ['symbol']
                for field in string_fields:
                    if field in record and record[field] is not None:
                        total_fields += 1
                        if isinstance(record[field], str) and len(record[field]) > 0:
                            valid_fields += 1
                
                if total_fields > 0 and valid_fields / total_fields >= 0.9:  # 90% of fields valid
                    valid_records += 1
            
            validity_score = valid_records / total_records if total_records > 0 else 0
            
            return QualityResult(
                metric_name=metric.name,
                value=validity_score,
                threshold=metric.threshold,
                passed=validity_score >= metric.threshold,
                severity=metric.severity,
                message=f"Data type validity: {validity_score:.2%}",
                details={
                    'valid_records': valid_records,
                    'total_records': total_records
                },
                timestamp=datetime.now(),
                affected_records=total_records - valid_records
            )
        
        return QualityResult(
            metric_name=metric.name,
            value=1.0,
            threshold=metric.threshold,
            passed=True,
            severity=metric.severity,
            message="Validity check passed",
            details={},
            timestamp=datetime.now()
        )
    
    def _check_uniqueness(self, metric: QualityMetric, data: List[Dict[str, Any]]) -> QualityResult:
        """Check data uniqueness"""
        total_records = len(data)
        
        if metric.name == "duplicate_records":
            # Create composite key for duplicate detection
            seen_keys = set()
            unique_records = 0
            
            for record in data:
                # Create key from symbol and timestamp
                key = (record.get('symbol', ''), record.get('timestamp', ''))
                
                if key not in seen_keys:
                    seen_keys.add(key)
                    unique_records += 1
            
            uniqueness_score = unique_records / total_records if total_records > 0 else 0
            
            return QualityResult(
                metric_name=metric.name,
                value=uniqueness_score,
                threshold=metric.threshold,
                passed=uniqueness_score >= metric.threshold,
                severity=metric.severity,
                message=f"Record uniqueness: {uniqueness_score:.2%}",
                details={
                    'unique_records': unique_records,
                    'total_records': total_records,
                    'duplicates': total_records - unique_records
                },
                timestamp=datetime.now(),
                affected_records=total_records - unique_records
            )
        
        return QualityResult(
            metric_name=metric.name,
            value=1.0,
            threshold=metric.threshold,
            passed=True,
            severity=metric.severity,
            message="Uniqueness check passed",
            details={},
            timestamp=datetime.now()
        )
    
    async def _detect_data_anomalies(self, dataset_name: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect data anomalies using ML models"""
        try:
            # Group data by symbol
            symbol_data = defaultdict(list)
            for record in data:
                symbol = record.get('symbol', 'UNKNOWN')
                symbol_data[symbol].append(record)
            
            all_anomalies = []
            
            # Detect anomalies for each symbol
            for symbol, records in symbol_data.items():
                if len(records) >= 5:  # Need minimum data for anomaly detection
                    anomalies = self.anomaly_detector.detect_anomalies(symbol, records)
                    all_anomalies.extend(anomalies)
            
            self.logger.info(f"Detected {len(all_anomalies)} anomalies in {dataset_name}")
            
            return all_anomalies
            
        except Exception as e:
            self.logger.error(f"Anomaly detection failed for {dataset_name}: {e}")
            return []
    
    def _calculate_overall_score(self, quality_results: List[QualityResult]) -> float:
        """Calculate overall data quality score"""
        if not quality_results:
            return 0.0
        
        # Weight scores by severity
        total_weight = 0
        weighted_sum = 0
        
        severity_weights = {
            DataQualitySeverity.CRITICAL: 5,
            DataQualitySeverity.ERROR: 3,
            DataQualitySeverity.WARNING: 2,
            DataQualitySeverity.INFO: 1
        }
        
        for result in quality_results:
            weight = severity_weights.get(result.severity, 1)
            score = result.value if result.passed else 0
            
            weighted_sum += score * weight
            total_weight += weight
        
        return (weighted_sum / total_weight) if total_weight > 0 else 0.0
    
    def _generate_summary(self, quality_results: List[QualityResult], 
                         anomalies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate quality report summary"""
        summary = {
            'total_metrics': len(quality_results),
            'passed_metrics': sum(1 for r in quality_results if r.passed),
            'failed_metrics': sum(1 for r in quality_results if not r.passed),
            'anomalies_detected': len(anomalies),
            'severity_breakdown': defaultdict(int),
            'metric_type_breakdown': defaultdict(int)
        }
        
        for result in quality_results:
            summary['severity_breakdown'][result.severity.value] += 1
            
            # Infer metric type from name
            if 'completeness' in result.metric_name:
                summary['metric_type_breakdown']['completeness'] += 1
            elif 'accuracy' in result.metric_name or 'validity' in result.metric_name:
                summary['metric_type_breakdown']['accuracy'] += 1
            elif 'consistency' in result.metric_name:
                summary['metric_type_breakdown']['consistency'] += 1
            elif 'timeliness' in result.metric_name or 'freshness' in result.metric_name:
                summary['metric_type_breakdown']['timeliness'] += 1
            else:
                summary['metric_type_breakdown']['other'] += 1
        
        return dict(summary)
    
    def _generate_recommendations(self, quality_results: List[QualityResult], 
                                anomalies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on quality results"""
        recommendations = []
        
        # Analyze failed metrics
        failed_metrics = [r for r in quality_results if not r.passed]
        
        if any('completeness' in r.metric_name for r in failed_metrics):
            recommendations.append("Improve data collection processes to reduce missing values")
        
        if any('accuracy' in r.metric_name for r in failed_metrics):
            recommendations.append("Implement stricter data validation at ingestion point")
        
        if any('consistency' in r.metric_name for r in failed_metrics):
            recommendations.append("Add business rule validation to ensure data consistency")
        
        if any('timeliness' in r.metric_name for r in failed_metrics):
            recommendations.append("Optimize data processing pipelines to improve freshness")
        
        if len(anomalies) > 0:
            recommendations.append(f"Investigate {len(anomalies)} detected anomalies for potential data quality issues")
        
        # Performance recommendations
        overall_score = self._calculate_overall_score(quality_results)
        if overall_score < 0.8:
            recommendations.append("Consider implementing automated data cleansing procedures")
            recommendations.append("Set up real-time data quality monitoring and alerting")
        
        if not recommendations:
            recommendations.append("Data quality is good. Continue current monitoring practices.")
        
        return recommendations
    
    async def _check_and_send_alerts(self, report: DataQualityReport):
        """Check quality report and send alerts if needed"""
        try:
            current_time = datetime.now()
            
            # Check for critical/error severity issues
            critical_issues = [m for m in report.metrics if not m.passed and m.severity in [
                DataQualitySeverity.CRITICAL, DataQualitySeverity.ERROR
            ]]
            
            if critical_issues:
                alert_key = f"{report.dataset_name}_critical_quality_issues"
                
                # Check alert cooldown
                last_alert_time = self.alert_cooldown.get(alert_key)
                if last_alert_time and (current_time - last_alert_time).seconds < 1800:  # 30 minutes cooldown
                    return
                
                # Send alert
                alert_message = {
                    'type': 'data_quality_alert',
                    'dataset': report.dataset_name,
                    'severity': 'high',
                    'message': f"Critical data quality issues detected in {report.dataset_name}",
                    'issues': [
                        f"{issue.metric_name}: {issue.message}" for issue in critical_issues
                    ],
                    'overall_score': report.overall_score,
                    'timestamp': current_time.isoformat()
                }
                
                # Store alert in history
                self.alert_history[alert_key].append(alert_message)
                self.alert_cooldown[alert_key] = current_time
                
                # Send alert (implement based on your alerting system)
                self.logger.warning(f"Data quality alert: {json.dumps(alert_message, indent=2)}")
        
        except Exception as e:
            self.logger.error(f"Alert checking failed: {e}")
    
    async def _store_quality_report(self, report: DataQualityReport):
        """Store quality report for historical analysis"""
        try:
            # Store in file system (in production, use database)
            reports_dir = Path(self.config.get('reports_dir', '/tmp/quality_reports'))
            reports_dir.mkdir(exist_ok=True)
            
            report_file = reports_dir / f"{report.report_id}.json"
            with open(report_file, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
            
            self.logger.debug(f"Quality report stored: {report_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to store quality report: {e}")
    
    def get_quality_trends(self, dataset_name: str, metric_name: str, 
                          days: int = 30) -> Dict[str, Any]:
        """Get quality trends for a specific metric"""
        try:
            history_key = f"{dataset_name}_{metric_name}"
            history = list(self.quality_history.get(history_key, []))
            
            if len(history) < 2:
                return {'error': 'Insufficient historical data'}
            
            # Calculate trend statistics
            recent_values = history[-days:] if len(history) > days else history
            trend_slope, _, _, p_value, _ = stats.linregress(range(len(recent_values)), recent_values)
            
            trend_analysis = {
                'metric_name': metric_name,
                'dataset_name': dataset_name,
                'current_value': history[-1] if history else 0,
                'average_value': statistics.mean(recent_values),
                'trend_slope': float(trend_slope),
                'trend_direction': 'improving' if trend_slope > 0 else 'declining' if trend_slope < 0 else 'stable',
                'trend_significance': 'significant' if p_value < 0.05 else 'not_significant',
                'data_points': len(recent_values),
                'time_period_days': days
            }
            
            return trend_analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get monitoring system statistics"""
        return {
            'performance_stats': self.performance_stats.copy(),
            'active_metrics': len([m for m in self.quality_metrics if m.enabled]),
            'total_metrics': len(self.quality_metrics),
            'anomaly_models': len(self.anomaly_detector.models),
            'alert_history_size': sum(len(alerts) for alerts in self.alert_history.values()),
            'quality_history_size': sum(len(history) for history in self.quality_history.values())
        }


# Factory function for creating quality monitor
def create_quality_monitor(config: Dict[str, Any]) -> DataQualityMonitor:
    """Create and configure data quality monitor"""
    return DataQualityMonitor(config)


# Example usage and testing
if __name__ == "__main__":
    async def test_quality_monitor():
        config = {
            'anomaly_contamination': 0.05,
            'reports_dir': '/tmp/quality_reports'
        }
        
        monitor = create_quality_monitor(config)
        
        # Test data with quality issues
        test_data = [
            {
                'symbol': 'AAPL',
                'timestamp': datetime.now().isoformat(),
                'open': 150.0,
                'high': 155.0,
                'low': 148.0,
                'close': 152.0,
                'volume': 1000000
            },
            {
                'symbol': 'AAPL',
                'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
                'open': 149.0,
                'high': 151.0,
                'low': 147.0,
                'close': 150.0,
                'volume': 900000
            },
            # Anomalous record
            {
                'symbol': 'AAPL',
                'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
                'open': 148.0,
                'high': 500.0,  # Anomalous high price
                'low': 1.0,     # Anomalous low price
                'close': 149.0,
                'volume': 50000000  # Anomalous volume
            }
        ]
        
        # Run quality monitoring
        report = await monitor.monitor_data_quality('test_market_data', test_data)
        
        print("Data Quality Report:")
        print(json.dumps(report.to_dict(), indent=2, default=str))
        
        # Get statistics
        stats = monitor.get_monitoring_statistics()
        print(f"\nMonitoring Statistics:")
        print(json.dumps(stats, indent=2, default=str))
    
    # Run test
    asyncio.run(test_quality_monitor())