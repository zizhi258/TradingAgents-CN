"""ML-Enhanced Trading Agents Integration

This module provides integration between the ML pipeline and the existing
TradingAgents multi-agent system, creating ML-powered agents and enhancing
existing agents with machine learning capabilities.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import asyncio
from dataclasses import dataclass

# Import existing TradingAgents components
from tradingagents.agents.utils.agent_utils import Toolkit
from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.agents.specialized.base_specialized_agent import BaseSpecializedAgent
from tradingagents.dataflows import (
    get_YFin_data_window, get_china_stock_data_unified,
    get_finnhub_news
)

# Import ML pipeline components
from .pipeline import MLPipeline, PipelineConfig, create_default_pipeline
from .models import create_model, ModelConfig
from .feature_engineering import create_comprehensive_features, FeatureConfig
from .deployment import InferenceService, ModelRegistry, DeploymentConfig

# Import logging system
from tradingagents.utils.logging_init import get_logger
logger = get_logger("ml_integration")


@dataclass
class MLAgentConfig:
    """Configuration for ML-enhanced agents"""
    enable_ml_predictions: bool = True
    enable_real_time_training: bool = False
    prediction_confidence_threshold: float = 0.7
    max_prediction_age_minutes: int = 30
    fallback_to_traditional_analysis: bool = True
    ml_weight_in_decisions: float = 0.6  # 60% ML, 40% traditional
    
    # Model preferences
    preferred_models: Dict[str, str] = None
    
    def __post_init__(self):
        if self.preferred_models is None:
            self.preferred_models = {
                "price_prediction": "xgboost",
                "signal_classification": "random_forest",
                "volatility_prediction": "lstm",
                "risk_assessment": "random_forest"
            }


class MLEnhancedAnalyst(BaseSpecializedAgent):
    """ML-Enhanced Market Analyst Agent"""
    
    def __init__(self, agent_id: str, ml_pipeline: MLPipeline, 
                 config: MLAgentConfig = None, **kwargs):
        super().__init__(agent_id, **kwargs)
        self.ml_pipeline = ml_pipeline
        self.config = config or MLAgentConfig()
        self.prediction_cache = {}
        self.last_training_time = None
        
        logger.info(f"ML-Enhanced Analyst initialized: {agent_id}")
    
    async def analyze_stock(self, symbol: str, analysis_type: str = "comprehensive") -> Dict:
        """Perform ML-enhanced stock analysis"""
        
        logger.info(f"Starting ML-enhanced analysis for {symbol}")
        
        try:
            # Get market data
            market_data = await self._get_market_data(symbol)
            
            if market_data is None or market_data.empty:
                return {"error": f"No market data available for {symbol}"}
            
            # Perform traditional analysis
            traditional_analysis = await self._traditional_analysis(market_data, symbol)
            
            # Perform ML analysis if enabled
            ml_analysis = {}
            if self.config.enable_ml_predictions:
                ml_analysis = await self._ml_analysis(market_data, symbol)
            
            # Combine analyses
            combined_analysis = self._combine_analyses(traditional_analysis, ml_analysis, symbol)
            
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}
    
    async def _get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get market data for analysis"""
        
        try:
            # Get recent data (last 2 years)
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
            
            # Try US market first
            data = get_YFin_data_window(symbol, start_date, end_date)
            
            if data is None or data.empty:
                # Try China market
                data = get_china_stock_data_unified(symbol, start_date=start_date, end_date=end_date)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return None
    
    async def _traditional_analysis(self, data: pd.DataFrame, symbol: str) -> Dict:
        """Perform traditional technical analysis"""
        
        analysis = {
            "type": "traditional",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Basic price analysis
            current_price = data['Close'].iloc[-1]
            prev_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
            
            analysis.update({
                "current_price": current_price,
                "price_change": current_price - prev_price,
                "price_change_pct": ((current_price - prev_price) / prev_price) * 100,
                "volume": data['Volume'].iloc[-1],
                "high_52w": data['High'].tail(252).max() if len(data) >= 252 else data['High'].max(),
                "low_52w": data['Low'].tail(252).min() if len(data) >= 252 else data['Low'].min()
            })
            
            # Technical indicators
            analysis["technical_indicators"] = self._calculate_technical_indicators(data)
            
            # Trend analysis
            analysis["trend_analysis"] = self._analyze_trend(data)
            
            # Support and resistance
            analysis["support_resistance"] = self._find_support_resistance(data)
            
        except Exception as e:
            logger.error(f"Traditional analysis failed for {symbol}: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    async def _ml_analysis(self, data: pd.DataFrame, symbol: str) -> Dict:
        """Perform ML-based analysis"""
        
        analysis = {
            "type": "ml_enhanced",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "predictions": {},
            "confidence_scores": {},
            "model_info": {}
        }
        
        try:
            # Generate features for prediction
            features = await self._generate_features(data)
            
            if features is None or features.empty:
                analysis["error"] = "Failed to generate features"
                return analysis
            
            # Get predictions for different tasks
            tasks = ["price_prediction", "signal_classification", "volatility_prediction", "risk_assessment"]
            
            for task in tasks:
                try:
                    prediction_result = self.ml_pipeline.get_model_predictions(symbol, features.tail(1))
                    
                    if task in prediction_result and prediction_result[task].get("success"):
                        analysis["predictions"][task] = prediction_result[task]["prediction"]
                        analysis["confidence_scores"][task] = self._calculate_confidence(prediction_result[task])
                        analysis["model_info"][task] = {
                            "model_type": prediction_result[task].get("model_type"),
                            "model_version": prediction_result[task].get("model_version"),
                            "latency_ms": prediction_result[task].get("latency_ms")
                        }
                    else:
                        analysis["predictions"][task] = None
                        analysis["confidence_scores"][task] = 0.0
                        
                except Exception as e:
                    logger.error(f"ML prediction failed for {task} - {symbol}: {e}")
                    analysis["predictions"][task] = None
                    analysis["confidence_scores"][task] = 0.0
            
            # Generate ML-based insights
            analysis["ml_insights"] = self._generate_ml_insights(analysis["predictions"])
            
        except Exception as e:
            logger.error(f"ML analysis failed for {symbol}: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    async def _generate_features(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Generate features for ML prediction"""
        
        try:
            # Use simplified feature generation for real-time analysis
            features = pd.DataFrame(index=data.index)
            
            # Basic price features
            features['close'] = data['Close']
            features['high'] = data['High']
            features['low'] = data['Low']
            features['volume'] = data['Volume']
            
            # Technical indicators
            features['sma_20'] = data['Close'].rolling(20).mean()
            features['sma_50'] = data['Close'].rolling(50).mean()
            features['ema_12'] = data['Close'].ewm(span=12).mean()
            features['ema_26'] = data['Close'].ewm(span=26).mean()
            
            # RSI
            delta = data['Close'].diff()
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = pd.Series(gain).rolling(14).mean()
            avg_loss = pd.Series(loss).rolling(14).mean()
            rs = avg_gain / avg_loss
            features['rsi_14'] = 100 - (100 / (1 + rs))
            
            # MACD
            features['macd'] = features['ema_12'] - features['ema_26']
            features['macd_signal'] = features['macd'].ewm(span=9).mean()
            
            # Volatility
            features['volatility_20'] = data['Close'].pct_change().rolling(20).std()
            
            # Volume indicators
            features['volume_sma_20'] = data['Volume'].rolling(20).mean()
            features['volume_ratio'] = data['Volume'] / features['volume_sma_20']
            
            # Price ratios
            features['price_to_sma20'] = data['Close'] / features['sma_20']
            features['price_to_sma50'] = data['Close'] / features['sma_50']
            
            # Lag features
            features['close_lag1'] = data['Close'].shift(1)
            features['return_lag1'] = data['Close'].pct_change().shift(1)
            features['return_lag5'] = data['Close'].pct_change(5).shift(5)
            
            return features.dropna()
            
        except Exception as e:
            logger.error(f"Feature generation failed: {e}")
            return None
    
    def _calculate_confidence(self, prediction_result: Dict) -> float:
        """Calculate confidence score for ML prediction"""
        
        # Simple confidence calculation based on latency and success
        base_confidence = 0.8 if prediction_result.get("success") else 0.0
        
        # Adjust based on latency (lower latency = higher confidence)
        latency_ms = prediction_result.get("latency_ms", 1000)
        latency_penalty = min(0.3, latency_ms / 5000)  # Max 30% penalty
        
        confidence = max(0.0, base_confidence - latency_penalty)
        
        return confidence
    
    def _generate_ml_insights(self, predictions: Dict) -> Dict:
        """Generate insights from ML predictions"""
        
        insights = {}
        
        try:
            # Price prediction insights
            price_pred = predictions.get("price_prediction")
            if price_pred is not None:
                if isinstance(price_pred, list) and len(price_pred) > 0:
                    price_change = price_pred[0]
                    if price_change > 0.02:  # 2% threshold
                        insights["price_outlook"] = "bullish"
                        insights["price_confidence"] = "high" if price_change > 0.05 else "medium"
                    elif price_change < -0.02:
                        insights["price_outlook"] = "bearish"
                        insights["price_confidence"] = "high" if price_change < -0.05 else "medium"
                    else:
                        insights["price_outlook"] = "neutral"
                        insights["price_confidence"] = "low"
            
            # Signal classification insights
            signal_pred = predictions.get("signal_classification")
            if signal_pred is not None:
                if isinstance(signal_pred, list) and len(signal_pred) > 0:
                    signal = signal_pred[0]
                    insights["trading_signal"] = signal
                    insights["signal_strength"] = "strong" if signal in ["BUY", "SELL"] else "weak"
            
            # Volatility prediction insights
            vol_pred = predictions.get("volatility_prediction")
            if vol_pred is not None:
                if isinstance(vol_pred, list) and len(vol_pred) > 0:
                    volatility = vol_pred[0]
                    if volatility > 0.3:  # 30% annual volatility
                        insights["volatility_outlook"] = "high"
                    elif volatility < 0.15:
                        insights["volatility_outlook"] = "low"
                    else:
                        insights["volatility_outlook"] = "medium"
            
            # Risk assessment insights
            risk_pred = predictions.get("risk_assessment")
            if risk_pred is not None:
                if isinstance(risk_pred, list) and len(risk_pred) > 0:
                    risk_level = risk_pred[0]
                    insights["risk_level"] = risk_level
                    
                    if risk_level == "HIGH":
                        insights["risk_warning"] = "High risk detected - consider position sizing"
                    elif risk_level == "LOW":
                        insights["risk_note"] = "Low risk environment - potential opportunity"
        
        except Exception as e:
            logger.error(f"Failed to generate ML insights: {e}")
            insights["error"] = str(e)
        
        return insights
    
    def _combine_analyses(self, traditional: Dict, ml_analysis: Dict, symbol: str) -> Dict:
        """Combine traditional and ML analyses"""
        
        combined = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "analysis_type": "ml_enhanced",
            "traditional_analysis": traditional,
            "ml_analysis": ml_analysis,
            "combined_insights": {},
            "recommendations": {},
            "confidence_score": 0.0
        }
        
        try:
            # Calculate overall confidence
            ml_confidences = ml_analysis.get("confidence_scores", {})
            avg_ml_confidence = np.mean(list(ml_confidences.values())) if ml_confidences else 0.0
            
            # Weight traditional analysis confidence (simplified)
            traditional_confidence = 0.7  # Assume 70% confidence for traditional analysis
            
            # Combined confidence
            combined["confidence_score"] = (
                self.config.ml_weight_in_decisions * avg_ml_confidence +
                (1 - self.config.ml_weight_in_decisions) * traditional_confidence
            )
            
            # Generate combined insights
            combined["combined_insights"] = self._generate_combined_insights(
                traditional, ml_analysis
            )
            
            # Generate recommendations
            combined["recommendations"] = self._generate_recommendations(
                traditional, ml_analysis, combined["confidence_score"]
            )
            
        except Exception as e:
            logger.error(f"Failed to combine analyses for {symbol}: {e}")
            combined["error"] = str(e)
        
        return combined
    
    def _generate_combined_insights(self, traditional: Dict, ml_analysis: Dict) -> Dict:
        """Generate insights combining traditional and ML analysis"""
        
        insights = {}
        
        try:
            # Price direction consensus
            traditional_trend = traditional.get("trend_analysis", {}).get("overall_trend", "neutral")
            ml_outlook = ml_analysis.get("ml_insights", {}).get("price_outlook", "neutral")
            
            if traditional_trend == ml_outlook and traditional_trend != "neutral":
                insights["price_direction_consensus"] = traditional_trend
                insights["consensus_strength"] = "strong"
            elif traditional_trend != "neutral" and ml_outlook != "neutral":
                insights["price_direction_consensus"] = "mixed_signals"
                insights["consensus_strength"] = "weak"
            else:
                insights["price_direction_consensus"] = "neutral"
                insights["consensus_strength"] = "neutral"
            
            # Risk-adjusted outlook
            ml_risk = ml_analysis.get("ml_insights", {}).get("risk_level", "MEDIUM")
            traditional_volatility = traditional.get("technical_indicators", {}).get("volatility", "medium")
            
            if ml_risk == "HIGH" or traditional_volatility == "high":
                insights["risk_adjusted_outlook"] = "caution_advised"
            elif ml_risk == "LOW" and traditional_volatility == "low":
                insights["risk_adjusted_outlook"] = "favorable_environment"
            else:
                insights["risk_adjusted_outlook"] = "normal_conditions"
            
            # Trading signal strength
            ml_signal = ml_analysis.get("ml_insights", {}).get("trading_signal")
            traditional_momentum = traditional.get("technical_indicators", {}).get("momentum", "neutral")
            
            if ml_signal in ["BUY", "SELL"] and traditional_momentum != "neutral":
                insights["signal_strength"] = "strong"
            elif ml_signal == "HOLD" or traditional_momentum == "neutral":
                insights["signal_strength"] = "weak"
            else:
                insights["signal_strength"] = "medium"
        
        except Exception as e:
            logger.error(f"Failed to generate combined insights: {e}")
            insights["error"] = str(e)
        
        return insights
    
    def _generate_recommendations(self, traditional: Dict, ml_analysis: Dict, 
                                confidence: float) -> Dict:
        """Generate trading recommendations"""
        
        recommendations = {
            "action": "HOLD",
            "confidence": confidence,
            "reasoning": [],
            "risk_factors": [],
            "position_sizing": "normal"
        }
        
        try:
            # Determine primary action
            ml_signal = ml_analysis.get("ml_insights", {}).get("trading_signal", "HOLD")
            price_outlook = ml_analysis.get("ml_insights", {}).get("price_outlook", "neutral")
            
            if confidence > self.config.prediction_confidence_threshold:
                if ml_signal == "BUY" and price_outlook == "bullish":
                    recommendations["action"] = "BUY"
                    recommendations["reasoning"].append("ML models indicate bullish sentiment")
                elif ml_signal == "SELL" and price_outlook == "bearish":
                    recommendations["action"] = "SELL"
                    recommendations["reasoning"].append("ML models indicate bearish sentiment")
            
            # Risk-based position sizing
            risk_level = ml_analysis.get("ml_insights", {}).get("risk_level", "MEDIUM")
            volatility = ml_analysis.get("ml_insights", {}).get("volatility_outlook", "medium")
            
            if risk_level == "HIGH" or volatility == "high":
                recommendations["position_sizing"] = "reduced"
                recommendations["risk_factors"].append("High volatility/risk detected")
            elif risk_level == "LOW" and volatility == "low":
                recommendations["position_sizing"] = "normal"
            
            # Additional considerations
            if confidence < 0.5:
                recommendations["risk_factors"].append("Low prediction confidence")
                if recommendations["action"] != "HOLD":
                    recommendations["action"] = "HOLD"
                    recommendations["reasoning"].append("Holding due to low confidence")
        
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            recommendations["error"] = str(e)
        
        return recommendations
    
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict:
        """Calculate basic technical indicators"""
        
        indicators = {}
        
        try:
            # Moving averages
            sma_20 = data['Close'].rolling(20).mean().iloc[-1]
            sma_50 = data['Close'].rolling(50).mean().iloc[-1]
            current_price = data['Close'].iloc[-1]
            
            indicators['sma_20'] = sma_20
            indicators['sma_50'] = sma_50
            indicators['price_vs_sma20'] = "above" if current_price > sma_20 else "below"
            indicators['price_vs_sma50'] = "above" if current_price > sma_50 else "below"
            
            # RSI
            delta = data['Close'].diff()
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            avg_gain = pd.Series(gain).rolling(14).mean().iloc[-1]
            avg_loss = pd.Series(loss).rolling(14).mean().iloc[-1]
            
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                indicators['rsi_14'] = rsi
                
                if rsi > 70:
                    indicators['rsi_signal'] = "overbought"
                elif rsi < 30:
                    indicators['rsi_signal'] = "oversold"
                else:
                    indicators['rsi_signal'] = "neutral"
            
            # Volatility
            returns = data['Close'].pct_change()
            volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
            indicators['volatility'] = "high" if volatility > 0.3 else "low" if volatility < 0.15 else "medium"
            
            # Momentum
            if len(data) >= 10:
                momentum = (current_price - data['Close'].iloc[-10]) / data['Close'].iloc[-10]
                if momentum > 0.05:
                    indicators['momentum'] = "bullish"
                elif momentum < -0.05:
                    indicators['momentum'] = "bearish"
                else:
                    indicators['momentum'] = "neutral"
        
        except Exception as e:
            logger.error(f"Technical indicators calculation failed: {e}")
            indicators['error'] = str(e)
        
        return indicators
    
    def _analyze_trend(self, data: pd.DataFrame) -> Dict:
        """Analyze price trend"""
        
        trend_analysis = {}
        
        try:
            # Short-term trend (20 days)
            if len(data) >= 20:
                short_trend = data['Close'].iloc[-1] - data['Close'].iloc[-20]
                short_trend_pct = short_trend / data['Close'].iloc[-20]
                
                trend_analysis['short_term'] = "bullish" if short_trend_pct > 0.02 else "bearish" if short_trend_pct < -0.02 else "neutral"
            
            # Medium-term trend (60 days)
            if len(data) >= 60:
                medium_trend = data['Close'].iloc[-1] - data['Close'].iloc[-60]
                medium_trend_pct = medium_trend / data['Close'].iloc[-60]
                
                trend_analysis['medium_term'] = "bullish" if medium_trend_pct > 0.05 else "bearish" if medium_trend_pct < -0.05 else "neutral"
            
            # Overall trend
            short = trend_analysis.get('short_term', 'neutral')
            medium = trend_analysis.get('medium_term', 'neutral')
            
            if short == medium and short != 'neutral':
                trend_analysis['overall_trend'] = short
            elif short == 'bullish' or medium == 'bullish':
                trend_analysis['overall_trend'] = 'mixed_bullish'
            elif short == 'bearish' or medium == 'bearish':
                trend_analysis['overall_trend'] = 'mixed_bearish'
            else:
                trend_analysis['overall_trend'] = 'neutral'
        
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            trend_analysis['error'] = str(e)
        
        return trend_analysis
    
    def _find_support_resistance(self, data: pd.DataFrame) -> Dict:
        """Find support and resistance levels"""
        
        levels = {}
        
        try:
            # Simple support/resistance based on recent highs and lows
            if len(data) >= 50:
                recent_data = data.tail(50)
                
                # Resistance (recent high)
                resistance = recent_data['High'].max()
                
                # Support (recent low)
                support = recent_data['Low'].min()
                
                current_price = data['Close'].iloc[-1]
                
                levels['resistance'] = resistance
                levels['support'] = support
                levels['distance_to_resistance'] = (resistance - current_price) / current_price
                levels['distance_to_support'] = (current_price - support) / current_price
        
        except Exception as e:
            logger.error(f"Support/resistance calculation failed: {e}")
            levels['error'] = str(e)
        
        return levels


class MLEnhancedChartingArtist(BaseSpecializedAgent):
    """ML-Enhanced Charting Artist Agent"""
    
    def __init__(self, agent_id: str, ml_pipeline: MLPipeline, 
                 config: MLAgentConfig = None, **kwargs):
        super().__init__(agent_id, **kwargs)
        self.ml_pipeline = ml_pipeline
        self.config = config or MLAgentConfig()
        
        logger.info(f"ML-Enhanced Charting Artist initialized: {agent_id}")
    
    async def create_ml_enhanced_chart(self, symbol: str, chart_type: str = "price_prediction") -> Dict:
        """Create ML-enhanced charts with predictions and insights"""
        
        logger.info(f"Creating ML-enhanced chart for {symbol}")
        
        try:
            # Get market data
            market_data = await self._get_market_data(symbol)
            
            if market_data is None or market_data.empty:
                return {"error": f"No market data available for {symbol}"}
            
            # Generate ML predictions
            features = await self._generate_features(market_data)
            predictions = self.ml_pipeline.get_model_predictions(symbol, features.tail(30)) if features is not None else {}
            
            # Create enhanced chart data
            chart_data = {
                "symbol": symbol,
                "chart_type": chart_type,
                "timestamp": datetime.now().isoformat(),
                "market_data": {
                    "prices": market_data['Close'].tail(100).tolist(),
                    "volumes": market_data['Volume'].tail(100).tolist(),
                    "dates": [d.strftime('%Y-%m-%d') for d in market_data.index.tail(100)]
                },
                "ml_overlays": {},
                "predictions": predictions,
                "chart_insights": {}
            }
            
            # Add ML overlays based on chart type
            if chart_type == "price_prediction":
                chart_data["ml_overlays"] = await self._create_prediction_overlay(market_data, predictions)
            elif chart_type == "volatility_analysis":
                chart_data["ml_overlays"] = await self._create_volatility_overlay(market_data, predictions)
            elif chart_type == "risk_assessment":
                chart_data["ml_overlays"] = await self._create_risk_overlay(market_data, predictions)
            
            # Generate chart insights
            chart_data["chart_insights"] = self._generate_chart_insights(market_data, predictions)
            
            return chart_data
            
        except Exception as e:
            logger.error(f"ML-enhanced chart creation failed for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}
    
    async def _get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get market data for charting"""
        # Reuse the same method from MLEnhancedAnalyst
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")  # 1 year of data
            
            data = get_YFin_data_window(symbol, start_date, end_date)
            
            if data is None or data.empty:
                data = get_china_stock_data_unified(symbol, start_date=start_date, end_date=end_date)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return None
    
    async def _generate_features(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Generate features for ML predictions in charting context"""
        # Reuse the same method from MLEnhancedAnalyst
        try:
            features = pd.DataFrame(index=data.index)
            
            # Basic features
            features['close'] = data['Close']
            features['volume'] = data['Volume']
            features['sma_20'] = data['Close'].rolling(20).mean()
            features['sma_50'] = data['Close'].rolling(50).mean()
            features['rsi_14'] = self._calculate_rsi(data['Close'])
            features['volatility_20'] = data['Close'].pct_change().rolling(20).std()
            
            return features.dropna()
            
        except Exception as e:
            logger.error(f"Feature generation failed: {e}")
            return None
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(window).mean()
        avg_loss = pd.Series(loss).rolling(window).mean()
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    async def _create_prediction_overlay(self, data: pd.DataFrame, predictions: Dict) -> Dict:
        """Create price prediction overlay for charts"""
        
        overlay = {
            "type": "price_prediction",
            "prediction_line": [],
            "confidence_bands": [],
            "signals": []
        }
        
        try:
            price_pred = predictions.get("price_prediction", {})
            
            if price_pred.get("success") and price_pred.get("prediction"):
                current_price = data['Close'].iloc[-1]
                predicted_change = price_pred["prediction"]
                
                if isinstance(predicted_change, list) and len(predicted_change) > 0:
                    predicted_change = predicted_change[0]
                
                # Create prediction line (next 5 days)
                prediction_prices = []
                for i in range(5):
                    predicted_price = current_price * (1 + predicted_change * (i + 1) / 5)
                    prediction_prices.append(predicted_price)
                
                overlay["prediction_line"] = prediction_prices
                
                # Create confidence bands (±10% of prediction)
                confidence_margin = abs(predicted_change) * 0.1
                upper_band = [p * (1 + confidence_margin) for p in prediction_prices]
                lower_band = [p * (1 - confidence_margin) for p in prediction_prices]
                
                overlay["confidence_bands"] = {
                    "upper": upper_band,
                    "lower": lower_band
                }
            
            # Add trading signals
            signal_pred = predictions.get("signal_classification", {})
            if signal_pred.get("success") and signal_pred.get("prediction"):
                signal = signal_pred["prediction"]
                if isinstance(signal, list) and len(signal) > 0:
                    signal = signal[0]
                
                overlay["signals"].append({
                    "type": signal,
                    "price": current_price,
                    "timestamp": datetime.now().isoformat()
                })
        
        except Exception as e:
            logger.error(f"Failed to create prediction overlay: {e}")
            overlay["error"] = str(e)
        
        return overlay
    
    async def _create_volatility_overlay(self, data: pd.DataFrame, predictions: Dict) -> Dict:
        """Create volatility analysis overlay"""
        
        overlay = {
            "type": "volatility_analysis",
            "historical_volatility": [],
            "predicted_volatility": [],
            "volatility_zones": []
        }
        
        try:
            # Historical volatility
            returns = data['Close'].pct_change()
            hist_vol = returns.rolling(20).std() * np.sqrt(252)
            overlay["historical_volatility"] = hist_vol.tail(50).fillna(0).tolist()
            
            # Predicted volatility
            vol_pred = predictions.get("volatility_prediction", {})
            if vol_pred.get("success") and vol_pred.get("prediction"):
                predicted_vol = vol_pred["prediction"]
                if isinstance(predicted_vol, list) and len(predicted_vol) > 0:
                    predicted_vol = predicted_vol[0]
                
                overlay["predicted_volatility"] = [predicted_vol] * 5  # Next 5 periods
                
                # Volatility zones
                current_vol = hist_vol.iloc[-1] if not pd.isna(hist_vol.iloc[-1]) else 0.2
                
                if predicted_vol > current_vol * 1.5:
                    overlay["volatility_zones"].append("high_vol_expected")
                elif predicted_vol < current_vol * 0.5:
                    overlay["volatility_zones"].append("low_vol_expected")
                else:
                    overlay["volatility_zones"].append("normal_vol_expected")
        
        except Exception as e:
            logger.error(f"Failed to create volatility overlay: {e}")
            overlay["error"] = str(e)
        
        return overlay
    
    async def _create_risk_overlay(self, data: pd.DataFrame, predictions: Dict) -> Dict:
        """Create risk assessment overlay"""
        
        overlay = {
            "type": "risk_assessment",
            "risk_levels": [],
            "risk_indicators": [],
            "position_sizing_suggestions": []
        }
        
        try:
            # Risk prediction
            risk_pred = predictions.get("risk_assessment", {})
            if risk_pred.get("success") and risk_pred.get("prediction"):
                risk_level = risk_pred["prediction"]
                if isinstance(risk_level, list) and len(risk_level) > 0:
                    risk_level = risk_level[0]
                
                overlay["risk_levels"].append({
                    "level": risk_level,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Position sizing suggestions based on risk
                if risk_level == "HIGH":
                    overlay["position_sizing_suggestions"].append("Reduce position size by 50%")
                    overlay["risk_indicators"].append("high_risk_warning")
                elif risk_level == "LOW":
                    overlay["position_sizing_suggestions"].append("Normal position size acceptable")
                    overlay["risk_indicators"].append("low_risk_environment")
                else:
                    overlay["position_sizing_suggestions"].append("Use standard position size")
                    overlay["risk_indicators"].append("medium_risk")
        
        except Exception as e:
            logger.error(f"Failed to create risk overlay: {e}")
            overlay["error"] = str(e)
        
        return overlay
    
    def _generate_chart_insights(self, data: pd.DataFrame, predictions: Dict) -> Dict:
        """Generate insights for chart visualization"""
        
        insights = {
            "key_levels": {},
            "pattern_recognition": {},
            "ml_confidence": {},
            "recommended_actions": []
        }
        
        try:
            # Key price levels
            current_price = data['Close'].iloc[-1]
            recent_high = data['High'].tail(50).max()
            recent_low = data['Low'].tail(50).min()
            
            insights["key_levels"] = {
                "current_price": current_price,
                "resistance": recent_high,
                "support": recent_low,
                "distance_to_resistance": (recent_high - current_price) / current_price,
                "distance_to_support": (current_price - recent_low) / current_price
            }
            
            # ML confidence assessment
            confidences = []
            for task, pred in predictions.items():
                if pred.get("success"):
                    # Simple confidence based on latency
                    latency = pred.get("latency_ms", 1000)
                    conf = max(0.5, 1.0 - (latency / 5000))  # Lower latency = higher confidence
                    confidences.append(conf)
            
            if confidences:
                insights["ml_confidence"] = {
                    "average_confidence": np.mean(confidences),
                    "min_confidence": np.min(confidences),
                    "max_confidence": np.max(confidences)
                }
            
            # Recommended actions based on predictions
            if predictions.get("signal_classification", {}).get("success"):
                signal = predictions["signal_classification"]["prediction"]
                if isinstance(signal, list) and len(signal) > 0:
                    signal = signal[0]
                
                insights["recommended_actions"].append(f"Trading signal: {signal}")
            
            if predictions.get("risk_assessment", {}).get("success"):
                risk = predictions["risk_assessment"]["prediction"]
                if isinstance(risk, list) and len(risk) > 0:
                    risk = risk[0]
                
                insights["recommended_actions"].append(f"Risk level: {risk}")
        
        except Exception as e:
            logger.error(f"Failed to generate chart insights: {e}")
            insights["error"] = str(e)
        
        return insights


def create_ml_enhanced_agents(ml_pipeline: MLPipeline, config: MLAgentConfig = None) -> Dict[str, BaseSpecializedAgent]:
    """Create a suite of ML-enhanced agents"""
    
    if config is None:
        config = MLAgentConfig()
    
    agents = {
        "ml_analyst": MLEnhancedAnalyst("ml_enhanced_analyst", ml_pipeline, config),
        "ml_charting_artist": MLEnhancedChartingArtist("ml_enhanced_charting_artist", ml_pipeline, config)
    }
    
    logger.info(f"Created {len(agents)} ML-enhanced agents")
    
    return agents


async def demonstrate_ml_integration(symbols: List[str] = None) -> Dict:
    """Demonstrate ML integration with TradingAgents system"""
    
    if symbols is None:
        symbols = ["AAPL", "MSFT"]
    
    logger.info(f"Demonstrating ML integration with symbols: {symbols}")
    
    try:
        # Create ML pipeline
        ml_pipeline = create_default_pipeline(symbols)
        
        # Train models (simplified for demo)
        logger.info("Training ML models...")
        pipeline_results = ml_pipeline.run_full_pipeline(symbols)
        
        # Create ML-enhanced agents
        ml_config = MLAgentConfig()
        agents = create_ml_enhanced_agents(ml_pipeline, ml_config)
        
        # Demonstrate agent capabilities
        demo_results = {
            "pipeline_results": pipeline_results,
            "agent_analyses": {},
            "agent_charts": {}
        }
        
        for symbol in symbols:
            # ML-enhanced analysis
            analysis = await agents["ml_analyst"].analyze_stock(symbol)
            demo_results["agent_analyses"][symbol] = analysis
            
            # ML-enhanced charts
            chart = await agents["ml_charting_artist"].create_ml_enhanced_chart(symbol)
            demo_results["agent_charts"][symbol] = chart
        
        logger.info("ML integration demonstration completed successfully")
        return demo_results
        
    except Exception as e:
        logger.error(f"ML integration demonstration failed: {e}")
        return {"error": str(e)}