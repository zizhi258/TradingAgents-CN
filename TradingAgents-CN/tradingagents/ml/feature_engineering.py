"""Feature Engineering Pipeline for Stock Market Analysis

This module provides comprehensive feature engineering capabilities for
stock market data, including technical indicators, fundamental analysis,
sentiment analysis, and market microstructure features.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
import warnings
from sklearn.preprocessing import StandardScaler, RobustScaler
from datetime import datetime, timedelta

# Import existing dataflow utilities
from tradingagents.dataflows import (
    get_YFin_data_window,
    get_stockstats_indicator,
    get_china_stock_data_unified,
    get_finnhub_news
)

# Import logging system
from tradingagents.utils.logging_init import get_logger
logger = get_logger("feature_engineering")


@dataclass
class FeatureConfig:
    """Configuration for feature engineering parameters"""
    lookback_window: int = 252  # Trading days for feature calculation
    technical_indicators: bool = True
    fundamental_features: bool = True
    sentiment_features: bool = True
    microstructure_features: bool = True
    time_series_features: bool = True
    normalize_features: bool = True
    scaler_type: str = "robust"  # "standard" or "robust"
    

class BaseFeatureEngine(ABC):
    """Base class for feature engineering engines"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
        self.features_computed = {}
        self.scaler = None
        
        if config.normalize_features:
            if config.scaler_type == "standard":
                self.scaler = StandardScaler()
            elif config.scaler_type == "robust":
                self.scaler = RobustScaler()
    
    @abstractmethod
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features from input data"""
        pass
    
    def normalize_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Normalize features if configured"""
        if self.scaler is not None and len(features) > 0:
            numeric_cols = features.select_dtypes(include=[np.number]).columns
            features[numeric_cols] = self.scaler.fit_transform(features[numeric_cols])
        return features


class TechnicalIndicatorEngine(BaseFeatureEngine):
    """Engine for computing technical indicators"""
    
    def __init__(self, config: FeatureConfig):
        super().__init__(config)
        
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract technical indicator features"""
        logger.info("Extracting technical indicator features")
        
        features = pd.DataFrame(index=data.index)
        
        try:
            # Price-based indicators
            features = self._add_price_indicators(data, features)
            
            # Volume-based indicators  
            features = self._add_volume_indicators(data, features)
            
            # Momentum indicators
            features = self._add_momentum_indicators(data, features)
            
            # Volatility indicators
            features = self._add_volatility_indicators(data, features)
            
            # Trend indicators
            features = self._add_trend_indicators(data, features)
            
            # Support/Resistance indicators
            features = self._add_support_resistance_indicators(data, features)
            
            logger.info(f"Generated {len(features.columns)} technical indicators")
            
        except Exception as e:
            logger.error(f"Error extracting technical features: {e}")
            
        return self.normalize_features(features)
    
    def _add_price_indicators(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add price-based technical indicators"""
        
        # Simple Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            features[f'sma_{period}'] = data['Close'].rolling(window=period).mean()
            features[f'sma_{period}_ratio'] = data['Close'] / features[f'sma_{period}']
            
        # Exponential Moving Averages
        for period in [12, 26, 50, 200]:
            features[f'ema_{period}'] = data['Close'].ewm(span=period).mean()
            features[f'ema_{period}_ratio'] = data['Close'] / features[f'ema_{period}']
            
        # Price position within recent range
        for period in [14, 30, 60]:
            high_roll = data['High'].rolling(window=period).max()
            low_roll = data['Low'].rolling(window=period).min()
            features[f'price_position_{period}'] = (data['Close'] - low_roll) / (high_roll - low_roll)
            
        # Gaps
        features['gap'] = (data['Open'] - data['Close'].shift(1)) / data['Close'].shift(1)
        features['gap_filled'] = np.where(
            features['gap'] > 0,
            (data['Low'] <= data['Close'].shift(1)).astype(int),
            (data['High'] >= data['Close'].shift(1)).astype(int)
        )
        
        return features
    
    def _add_volume_indicators(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based indicators"""
        
        # Volume moving averages
        for period in [10, 20, 50]:
            features[f'volume_ma_{period}'] = data['Volume'].rolling(window=period).mean()
            features[f'volume_ratio_{period}'] = data['Volume'] / features[f'volume_ma_{period}']
            
        # On-Balance Volume (OBV)
        price_change = data['Close'].diff()
        features['obv'] = (np.sign(price_change) * data['Volume']).cumsum()
        features['obv_ma_10'] = features['obv'].rolling(window=10).mean()
        
        # Volume Price Trend (VPT)
        features['vpt'] = (data['Volume'] * (data['Close'].pct_change())).cumsum()
        
        # Accumulation/Distribution Line
        clv = ((data['Close'] - data['Low']) - (data['High'] - data['Close'])) / (data['High'] - data['Low'])
        clv = clv.fillna(0)
        features['ad_line'] = (clv * data['Volume']).cumsum()
        
        # Volume Weighted Average Price (VWAP)
        typical_price = (data['High'] + data['Low'] + data['Close']) / 3
        features['vwap'] = (typical_price * data['Volume']).cumsum() / data['Volume'].cumsum()
        features['vwap_ratio'] = data['Close'] / features['vwap']
        
        return features
        
    def _add_momentum_indicators(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add momentum indicators"""
        
        # RSI (Relative Strength Index)
        for period in [14, 21, 30]:
            delta = data['Close'].diff()
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            avg_gain = pd.Series(gain).rolling(window=period).mean()
            avg_loss = pd.Series(loss).rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            features[f'rsi_{period}'] = 100 - (100 / (1 + rs))
            
        # MACD (Moving Average Convergence Divergence)
        ema12 = data['Close'].ewm(span=12).mean()
        ema26 = data['Close'].ewm(span=26).mean()
        features['macd'] = ema12 - ema26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        # Stochastic Oscillator
        for period in [14, 21]:
            low_min = data['Low'].rolling(window=period).min()
            high_max = data['High'].rolling(window=period).max()
            features[f'stoch_k_{period}'] = 100 * ((data['Close'] - low_min) / (high_max - low_min))
            features[f'stoch_d_{period}'] = features[f'stoch_k_{period}'].rolling(window=3).mean()
            
        # Williams %R
        for period in [14, 21]:
            high_max = data['High'].rolling(window=period).max()
            low_min = data['Low'].rolling(window=period).min()
            features[f'williams_r_{period}'] = -100 * ((high_max - data['Close']) / (high_max - low_min))
            
        # Rate of Change (ROC)
        for period in [10, 20, 30]:
            features[f'roc_{period}'] = data['Close'].pct_change(periods=period) * 100
            
        return features
    
    def _add_volatility_indicators(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add volatility indicators"""
        
        # Bollinger Bands
        for period in [20, 50]:
            sma = data['Close'].rolling(window=period).mean()
            std = data['Close'].rolling(window=period).std()
            
            features[f'bb_upper_{period}'] = sma + (2 * std)
            features[f'bb_lower_{period}'] = sma - (2 * std)
            features[f'bb_width_{period}'] = (features[f'bb_upper_{period}'] - features[f'bb_lower_{period}']) / sma
            features[f'bb_position_{period}'] = (data['Close'] - features[f'bb_lower_{period}']) / (features[f'bb_upper_{period}'] - features[f'bb_lower_{period}'])
            
        # Average True Range (ATR)
        high_low = data['High'] - data['Low']
        high_close_prev = np.abs(data['High'] - data['Close'].shift(1))
        low_close_prev = np.abs(data['Low'] - data['Close'].shift(1))
        
        true_range = np.maximum(high_low, np.maximum(high_close_prev, low_close_prev))
        
        for period in [14, 21]:
            features[f'atr_{period}'] = true_range.rolling(window=period).mean()
            features[f'atr_ratio_{period}'] = features[f'atr_{period}'] / data['Close']
            
        # Historical Volatility
        for period in [10, 20, 30]:
            returns = data['Close'].pct_change()
            features[f'hist_vol_{period}'] = returns.rolling(window=period).std() * np.sqrt(252)
            
        return features
    
    def _add_trend_indicators(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add trend indicators"""
        
        # Average Directional Index (ADX)
        high_diff = data['High'].diff()
        low_diff = data['Low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        # ATR for ADX calculation
        atr_14 = features.get('atr_14', data['Close'].rolling(14).std())  # fallback
        
        plus_di = 100 * (pd.Series(plus_dm).rolling(14).sum() / atr_14)
        minus_di = 100 * (pd.Series(minus_dm).rolling(14).sum() / atr_14)
        
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        features['adx'] = dx.rolling(14).mean()
        features['plus_di'] = plus_di
        features['minus_di'] = minus_di
        
        # Parabolic SAR (simplified)
        features['sar'] = self._calculate_parabolic_sar(data)
        
        # Moving Average Convergence Divergence of different periods
        for short, long_period in [(5, 20), (10, 30), (20, 50)]:
            short_ma = data['Close'].rolling(short).mean()
            long_ma = data['Close'].rolling(long_period).mean()
            features[f'ma_diff_{short}_{long_period}'] = (short_ma - long_ma) / long_ma
            
        return features
    
    def _add_support_resistance_indicators(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add support and resistance level indicators"""
        
        # Pivot Points
        features['pivot_point'] = (data['High'].shift(1) + data['Low'].shift(1) + data['Close'].shift(1)) / 3
        features['resistance_1'] = 2 * features['pivot_point'] - data['Low'].shift(1)
        features['support_1'] = 2 * features['pivot_point'] - data['High'].shift(1)
        features['resistance_2'] = features['pivot_point'] + (data['High'].shift(1) - data['Low'].shift(1))
        features['support_2'] = features['pivot_point'] - (data['High'].shift(1) - data['Low'].shift(1))
        
        # Distance from pivot levels
        features['dist_from_pivot'] = (data['Close'] - features['pivot_point']) / features['pivot_point']
        features['dist_from_r1'] = (data['Close'] - features['resistance_1']) / features['resistance_1']
        features['dist_from_s1'] = (data['Close'] - features['support_1']) / features['support_1']
        
        # Fibonacci Retracements (simplified)
        for period in [20, 50]:
            high_max = data['High'].rolling(period).max()
            low_min = data['Low'].rolling(period).min()
            price_range = high_max - low_min
            
            features[f'fib_23.6_{period}'] = high_max - 0.236 * price_range
            features[f'fib_38.2_{period}'] = high_max - 0.382 * price_range
            features[f'fib_50.0_{period}'] = high_max - 0.500 * price_range
            features[f'fib_61.8_{period}'] = high_max - 0.618 * price_range
            
        return features
    
    def _calculate_parabolic_sar(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Parabolic SAR indicator"""
        # Simplified Parabolic SAR calculation
        sar = pd.Series(index=data.index, dtype=float)
        
        if len(data) < 2:
            return sar
            
        # Initialize
        sar.iloc[0] = data['Low'].iloc[0]
        af = 0.02
        max_af = 0.2
        
        for i in range(1, len(data)):
            if i == 1:
                sar.iloc[i] = data['High'].iloc[0]
            else:
                sar.iloc[i] = sar.iloc[i-1] + af * (data['High'].iloc[i-1] - sar.iloc[i-1])
                
        return sar


class FundamentalAnalysisEngine(BaseFeatureEngine):
    """Engine for fundamental analysis features"""
    
    def extract_features(self, data: pd.DataFrame, fundamentals: Optional[Dict] = None) -> pd.DataFrame:
        """Extract fundamental analysis features"""
        logger.info("Extracting fundamental analysis features")
        
        features = pd.DataFrame(index=data.index)
        
        if fundamentals is None:
            logger.warning("No fundamental data provided, generating placeholder features")
            return self._generate_placeholder_fundamentals(features)
        
        try:
            # Financial ratios
            features = self._add_financial_ratios(fundamentals, features)
            
            # Growth metrics
            features = self._add_growth_metrics(fundamentals, features)
            
            # Profitability metrics
            features = self._add_profitability_metrics(fundamentals, features)
            
            # Leverage metrics
            features = self._add_leverage_metrics(fundamentals, features)
            
            # Efficiency metrics
            features = self._add_efficiency_metrics(fundamentals, features)
            
            logger.info(f"Generated {len(features.columns)} fundamental features")
            
        except Exception as e:
            logger.error(f"Error extracting fundamental features: {e}")
            
        return self.normalize_features(features)
    
    def _add_financial_ratios(self, fundamentals: Dict, features: pd.DataFrame) -> pd.DataFrame:
        """Add financial ratio features"""
        
        # P/E ratios
        if 'eps' in fundamentals and 'price' in fundamentals:
            features['pe_ratio'] = fundamentals['price'] / fundamentals['eps']
            
        # P/B ratio
        if 'book_value_per_share' in fundamentals and 'price' in fundamentals:
            features['pb_ratio'] = fundamentals['price'] / fundamentals['book_value_per_share']
            
        # P/S ratio
        if 'sales_per_share' in fundamentals and 'price' in fundamentals:
            features['ps_ratio'] = fundamentals['price'] / fundamentals['sales_per_share']
            
        # PEG ratio
        if 'pe_ratio' in features and 'earnings_growth' in fundamentals:
            features['peg_ratio'] = features['pe_ratio'] / fundamentals['earnings_growth']
            
        return features
    
    def _add_growth_metrics(self, fundamentals: Dict, features: pd.DataFrame) -> pd.DataFrame:
        """Add growth metric features"""
        
        # Revenue growth
        if 'revenue_growth' in fundamentals:
            features['revenue_growth'] = fundamentals['revenue_growth']
            
        # Earnings growth
        if 'earnings_growth' in fundamentals:
            features['earnings_growth'] = fundamentals['earnings_growth']
            
        # Book value growth
        if 'book_value_growth' in fundamentals:
            features['book_value_growth'] = fundamentals['book_value_growth']
            
        return features
    
    def _add_profitability_metrics(self, fundamentals: Dict, features: pd.DataFrame) -> pd.DataFrame:
        """Add profitability metric features"""
        
        # Return on Equity
        if 'net_income' in fundamentals and 'shareholders_equity' in fundamentals:
            features['roe'] = fundamentals['net_income'] / fundamentals['shareholders_equity']
            
        # Return on Assets
        if 'net_income' in fundamentals and 'total_assets' in fundamentals:
            features['roa'] = fundamentals['net_income'] / fundamentals['total_assets']
            
        # Gross margin
        if 'gross_profit' in fundamentals and 'revenue' in fundamentals:
            features['gross_margin'] = fundamentals['gross_profit'] / fundamentals['revenue']
            
        # Operating margin
        if 'operating_income' in fundamentals and 'revenue' in fundamentals:
            features['operating_margin'] = fundamentals['operating_income'] / fundamentals['revenue']
            
        # Net margin
        if 'net_income' in fundamentals and 'revenue' in fundamentals:
            features['net_margin'] = fundamentals['net_income'] / fundamentals['revenue']
            
        return features
    
    def _add_leverage_metrics(self, fundamentals: Dict, features: pd.DataFrame) -> pd.DataFrame:
        """Add leverage metric features"""
        
        # Debt to Equity
        if 'total_debt' in fundamentals and 'shareholders_equity' in fundamentals:
            features['debt_to_equity'] = fundamentals['total_debt'] / fundamentals['shareholders_equity']
            
        # Debt to Assets
        if 'total_debt' in fundamentals and 'total_assets' in fundamentals:
            features['debt_to_assets'] = fundamentals['total_debt'] / fundamentals['total_assets']
            
        # Interest Coverage
        if 'ebit' in fundamentals and 'interest_expense' in fundamentals:
            features['interest_coverage'] = fundamentals['ebit'] / fundamentals['interest_expense']
            
        return features
    
    def _add_efficiency_metrics(self, fundamentals: Dict, features: pd.DataFrame) -> pd.DataFrame:
        """Add efficiency metric features"""
        
        # Asset Turnover
        if 'revenue' in fundamentals and 'total_assets' in fundamentals:
            features['asset_turnover'] = fundamentals['revenue'] / fundamentals['total_assets']
            
        # Inventory Turnover
        if 'cogs' in fundamentals and 'inventory' in fundamentals:
            features['inventory_turnover'] = fundamentals['cogs'] / fundamentals['inventory']
            
        # Receivables Turnover
        if 'revenue' in fundamentals and 'accounts_receivable' in fundamentals:
            features['receivables_turnover'] = fundamentals['revenue'] / fundamentals['accounts_receivable']
            
        return features
    
    def _generate_placeholder_fundamentals(self, features: pd.DataFrame) -> pd.DataFrame:
        """Generate placeholder fundamental features when data is not available"""
        
        placeholder_features = [
            'pe_ratio', 'pb_ratio', 'ps_ratio', 'peg_ratio',
            'revenue_growth', 'earnings_growth', 'book_value_growth',
            'roe', 'roa', 'gross_margin', 'operating_margin', 'net_margin',
            'debt_to_equity', 'debt_to_assets', 'interest_coverage',
            'asset_turnover', 'inventory_turnover', 'receivables_turnover'
        ]
        
        for feature in placeholder_features:
            features[feature] = np.nan
            
        return features


class SentimentAnalysisEngine(BaseFeatureEngine):
    """Engine for sentiment analysis features"""
    
    def extract_features(self, data: pd.DataFrame, news_data: Optional[List] = None) -> pd.DataFrame:
        """Extract sentiment analysis features"""
        logger.info("Extracting sentiment analysis features")
        
        features = pd.DataFrame(index=data.index)
        
        try:
            if news_data is not None:
                features = self._add_news_sentiment_features(news_data, features)
            else:
                features = self._generate_placeholder_sentiment_features(features)
                
            # Market sentiment indicators
            features = self._add_market_sentiment_features(data, features)
            
            logger.info(f"Generated {len(features.columns)} sentiment features")
            
        except Exception as e:
            logger.error(f"Error extracting sentiment features: {e}")
            
        return self.normalize_features(features)
    
    def _add_news_sentiment_features(self, news_data: List, features: pd.DataFrame) -> pd.DataFrame:
        """Add news sentiment features"""
        
        # Placeholder for actual sentiment analysis implementation
        # This would integrate with NLP models for sentiment scoring
        
        features['news_sentiment_score'] = np.random.uniform(-1, 1, len(features))
        features['news_volume'] = np.random.poisson(5, len(features))
        features['news_sentiment_ma_5'] = features['news_sentiment_score'].rolling(5).mean()
        features['news_sentiment_ma_20'] = features['news_sentiment_score'].rolling(20).mean()
        features['news_sentiment_volatility'] = features['news_sentiment_score'].rolling(10).std()
        
        return features
    
    def _add_market_sentiment_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add market-based sentiment indicators"""
        
        # Price momentum as sentiment proxy
        features['price_momentum_5'] = data['Close'].pct_change(5)
        features['price_momentum_20'] = data['Close'].pct_change(20)
        
        # Volume-price sentiment
        price_change = data['Close'].pct_change()
        volume_change = data['Volume'].pct_change()
        features['volume_price_sentiment'] = price_change * volume_change
        
        # Fear & Greed proxy (simplified VIX-like calculation)
        returns = data['Close'].pct_change()
        features['fear_greed_proxy'] = returns.rolling(20).std() * np.sqrt(252)
        
        return features
    
    def _generate_placeholder_sentiment_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Generate placeholder sentiment features"""
        
        placeholder_features = [
            'news_sentiment_score', 'news_volume', 'news_sentiment_ma_5',
            'news_sentiment_ma_20', 'news_sentiment_volatility'
        ]
        
        for feature in placeholder_features:
            features[feature] = np.nan
            
        return features


class MarketMicrostructureEngine(BaseFeatureEngine):
    """Engine for market microstructure features"""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract market microstructure features"""
        logger.info("Extracting market microstructure features")
        
        features = pd.DataFrame(index=data.index)
        
        try:
            # Volume analysis
            features = self._add_volume_analysis_features(data, features)
            
            # Spread analysis (using High-Low as proxy)
            features = self._add_spread_features(data, features)
            
            # Depth analysis
            features = self._add_depth_features(data, features)
            
            # Tick analysis
            features = self._add_tick_features(data, features)
            
            logger.info(f"Generated {len(features.columns)} microstructure features")
            
        except Exception as e:
            logger.error(f"Error extracting microstructure features: {e}")
            
        return self.normalize_features(features)
    
    def _add_volume_analysis_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add volume analysis features"""
        
        # Volume rate
        features['volume_rate'] = data['Volume'] / data['Volume'].rolling(20).mean()
        
        # Intraday volume distribution (proxy)
        features['volume_first_half'] = data['Volume'] * 0.6  # Simplified assumption
        features['volume_second_half'] = data['Volume'] * 0.4
        features['volume_imbalance'] = features['volume_first_half'] / features['volume_second_half']
        
        # Volume clusters
        features['high_volume_day'] = (data['Volume'] > data['Volume'].rolling(20).quantile(0.8)).astype(int)
        features['low_volume_day'] = (data['Volume'] < data['Volume'].rolling(20).quantile(0.2)).astype(int)
        
        return features
    
    def _add_spread_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add bid-ask spread proxy features"""
        
        # High-Low spread as proxy for bid-ask spread
        features['hl_spread'] = (data['High'] - data['Low']) / data['Close']
        features['hl_spread_ma_10'] = features['hl_spread'].rolling(10).mean()
        features['hl_spread_volatility'] = features['hl_spread'].rolling(10).std()
        
        # Relative spread position
        features['spread_position'] = (data['Close'] - data['Low']) / (data['High'] - data['Low'])
        
        return features
    
    def _add_depth_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add market depth proxy features"""
        
        # Volume-weighted price levels
        features['vwap_daily'] = ((data['High'] + data['Low'] + data['Close']) / 3 * data['Volume']).cumsum() / data['Volume'].cumsum()
        features['price_above_vwap'] = (data['Close'] > features['vwap_daily']).astype(int)
        
        # Depth proxy using volume and price range
        features['depth_proxy'] = data['Volume'] / (data['High'] - data['Low'])
        features['depth_proxy_ma'] = features['depth_proxy'].rolling(10).mean()
        
        return features
    
    def _add_tick_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add tick-level proxy features"""
        
        # Price changes
        features['price_change'] = data['Close'].diff()
        features['price_change_abs'] = features['price_change'].abs()
        
        # Tick direction
        features['uptick'] = (features['price_change'] > 0).astype(int)
        features['downtick'] = (features['price_change'] < 0).astype(int)
        features['unchanged'] = (features['price_change'] == 0).astype(int)
        
        # Tick patterns
        features['consecutive_upticks'] = features['uptick'].groupby((features['uptick'] == 0).cumsum()).cumsum()
        features['consecutive_downticks'] = features['downtick'].groupby((features['downtick'] == 0).cumsum()).cumsum()
        
        return features


class TimeSeriesFeatureEngine(BaseFeatureEngine):
    """Engine for time-series specific features"""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract time-series features"""
        logger.info("Extracting time-series features")
        
        features = pd.DataFrame(index=data.index)
        
        try:
            # Lag features
            features = self._add_lag_features(data, features)
            
            # Rolling statistics
            features = self._add_rolling_statistics(data, features)
            
            # Seasonal features
            features = self._add_seasonal_features(data, features)
            
            # Autocorrelation features
            features = self._add_autocorrelation_features(data, features)
            
            # Statistical features
            features = self._add_statistical_features(data, features)
            
            logger.info(f"Generated {len(features.columns)} time-series features")
            
        except Exception as e:
            logger.error(f"Error extracting time-series features: {e}")
            
        return self.normalize_features(features)
    
    def _add_lag_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add lagged features"""
        
        # Price lags
        for lag in [1, 2, 3, 5, 10, 20]:
            features[f'close_lag_{lag}'] = data['Close'].shift(lag)
            features[f'return_lag_{lag}'] = data['Close'].pct_change().shift(lag)
            
        # Volume lags
        for lag in [1, 2, 3, 5]:
            features[f'volume_lag_{lag}'] = data['Volume'].shift(lag)
            
        return features
    
    def _add_rolling_statistics(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add rolling statistical features"""
        
        returns = data['Close'].pct_change()
        
        # Rolling mean and std
        for window in [5, 10, 20, 50]:
            features[f'return_mean_{window}'] = returns.rolling(window).mean()
            features[f'return_std_{window}'] = returns.rolling(window).std()
            features[f'return_skew_{window}'] = returns.rolling(window).skew()
            features[f'return_kurtosis_{window}'] = returns.rolling(window).kurt()
            
        # Rolling quantiles
        for window in [20, 50]:
            for q in [0.1, 0.25, 0.75, 0.9]:
                features[f'return_quantile_{q}_{window}'] = returns.rolling(window).quantile(q)
                
        return features
    
    def _add_seasonal_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add seasonal/calendar features"""
        
        if hasattr(data.index, 'dayofweek'):
            # Day of week effects
            features['day_of_week'] = data.index.dayofweek
            features['is_monday'] = (data.index.dayofweek == 0).astype(int)
            features['is_friday'] = (data.index.dayofweek == 4).astype(int)
            
            # Month effects
            features['month'] = data.index.month
            features['is_january'] = (data.index.month == 1).astype(int)
            features['is_december'] = (data.index.month == 12).astype(int)
            
            # Quarter effects
            features['quarter'] = data.index.quarter
            features['is_q4'] = (data.index.quarter == 4).astype(int)
            
        # Market anomalies (simplified)
        features['potential_earnings_season'] = ((data.index.month.isin([1, 4, 7, 10]))).astype(int)
        
        return features
    
    def _add_autocorrelation_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add autocorrelation features"""
        
        returns = data['Close'].pct_change().dropna()
        
        # Autocorrelation at different lags
        for lag in [1, 2, 3, 5, 10]:
            if len(returns) > lag:
                features[f'autocorr_{lag}'] = returns.rolling(window=50).apply(
                    lambda x: x.autocorr(lag=lag) if len(x) > lag else np.nan
                )
                
        return features
    
    def _add_statistical_features(self, data: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features"""
        
        returns = data['Close'].pct_change()
        
        # Distribution features
        for window in [20, 50]:
            # Percentile features
            features[f'return_rank_{window}'] = returns.rolling(window).rank(pct=True)
            
            # Extreme value features
            features[f'max_return_{window}'] = returns.rolling(window).max()
            features[f'min_return_{window}'] = returns.rolling(window).min()
            features[f'return_range_{window}'] = features[f'max_return_{window}'] - features[f'min_return_{window}']
            
        # Stability features
        features['price_stability_20'] = 1 - (data['Close'].rolling(20).std() / data['Close'].rolling(20).mean())
        
        return features


def create_comprehensive_features(data: pd.DataFrame, 
                                config: FeatureConfig,
                                fundamentals: Optional[Dict] = None,
                                news_data: Optional[List] = None) -> pd.DataFrame:
    """Create comprehensive features using all engines"""
    
    logger.info("Creating comprehensive feature set")
    
    all_features = pd.DataFrame(index=data.index)
    
    # Technical indicators
    if config.technical_indicators:
        tech_engine = TechnicalIndicatorEngine(config)
        tech_features = tech_engine.extract_features(data)
        all_features = pd.concat([all_features, tech_features], axis=1)
        
    # Fundamental analysis
    if config.fundamental_features:
        fund_engine = FundamentalAnalysisEngine(config)
        fund_features = fund_engine.extract_features(data, fundamentals)
        all_features = pd.concat([all_features, fund_features], axis=1)
        
    # Sentiment analysis
    if config.sentiment_features:
        sent_engine = SentimentAnalysisEngine(config)
        sent_features = sent_engine.extract_features(data, news_data)
        all_features = pd.concat([all_features, sent_features], axis=1)
        
    # Market microstructure
    if config.microstructure_features:
        micro_engine = MarketMicrostructureEngine(config)
        micro_features = micro_engine.extract_features(data)
        all_features = pd.concat([all_features, micro_features], axis=1)
        
    # Time-series features
    if config.time_series_features:
        ts_engine = TimeSeriesFeatureEngine(config)
        ts_features = ts_engine.extract_features(data)
        all_features = pd.concat([all_features, ts_features], axis=1)
    
    # Remove features with too many NaN values
    nan_threshold = 0.5  # Remove features with >50% NaN values
    nan_ratios = all_features.isnull().sum() / len(all_features)
    features_to_keep = nan_ratios[nan_ratios <= nan_threshold].index
    all_features = all_features[features_to_keep]
    
    # Forward fill remaining NaN values
    all_features = all_features.fillna(method='ffill').fillna(method='bfill')
    
    logger.info(f"Generated {len(all_features.columns)} total features")
    
    return all_features