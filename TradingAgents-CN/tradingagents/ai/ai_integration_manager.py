"""
AI Integration Layer for TradingAgents-CN

This module integrates all AI-powered features with existing TradingAgents-CN components
including ChartingArtist, news analysis, risk management, and the core trading system.
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import threading

# Core TradingAgents imports
from tradingagents.agents.specialized.charting_artist import ChartingArtist
from tradingagents.agents.specialized.news_hunter import NewsHunter
from tradingagents.agents.managers.risk_manager import RiskManager
from tradingagents.utils.enhanced_news_filter import EnhancedNewsFilter
from tradingagents.utils.logging_init import get_logger
from tradingagents.config.config_manager import ConfigManager
from tradingagents.ml.pipeline import MLPipeline

# AI System imports
from .llm_orchestrator import AIOrchestrator
from .financial_rag import FinancialRAGSystem
from .intelligent_automation import IntelligentAutomation
from .enhanced_coordination import EnhancedMultiAgentCoordinator
from .production_api import ProductionAPIServer

logger = get_logger("ai_integration")


@dataclass
class IntegrationConfig:
    """Configuration for AI integration"""
    # Core AI settings
    enable_llm_orchestrator: bool = True
    enable_rag_system: bool = True
    enable_automation: bool = True
    enable_coordination: bool = True
    enable_production_api: bool = True
    
    # Integration settings
    integrate_charting_artist: bool = True
    integrate_news_analysis: bool = True
    integrate_risk_management: bool = True
    integrate_ml_pipeline: bool = True
    
    # Performance settings
    max_concurrent_integrations: int = 10
    cache_integration_results: bool = True
    enable_real_time_updates: bool = True
    
    # Data paths
    knowledge_base_path: str = "ai_knowledge_base"
    reports_output_path: str = "ai_reports"
    cache_path: str = "ai_cache"


class EnhancedChartingArtistIntegration:
    """Enhanced ChartingArtist with AI-powered insights"""
    
    def __init__(self, ai_orchestrator: AIOrchestrator, rag_system: FinancialRAGSystem):
        self.ai_orchestrator = ai_orchestrator
        self.rag_system = rag_system
        self.charting_artist = None
        
        # Chart analysis templates
        self.chart_analysis_prompts = {
            'technical_insights': """
Analyze the following technical chart data and provide insights:

Chart Type: {chart_type}
Symbol: {symbol}
Timeframe: {timeframe}
Current Price: ${current_price}
Key Technical Indicators:
{technical_indicators}

Chart Patterns Detected:
{patterns}

Please provide:
1. Technical analysis summary
2. Key support and resistance levels
3. Trend analysis and momentum
4. Entry/exit recommendations
5. Risk considerations

Focus on actionable trading insights based on the chart analysis.
""",
            
            'comparative_analysis': """
Compare the technical analysis of the following symbols:

Symbols: {symbols}
Analysis Period: {period}
Market Context: {market_context}

Technical Summaries:
{technical_summaries}

Please provide:
1. Relative strength comparison
2. Correlation analysis
3. Sector performance insights
4. Portfolio allocation recommendations
5. Risk-adjusted opportunities

Create a comprehensive comparative analysis for portfolio optimization.
""",
            
            'pattern_validation': """
Validate and analyze the following chart patterns:

Symbol: {symbol}
Detected Patterns: {patterns}
Confidence Levels: {confidence_levels}
Historical Context: {historical_context}

Market Conditions:
{market_conditions}

Please assess:
1. Pattern reliability and historical performance
2. Current market context alignment
3. Probability of successful pattern completion
4. Risk/reward analysis
5. Timing considerations

Provide pattern validation with statistical confidence.
"""
        }
    
    async def create_enhanced_chart_analysis(self, 
                                           symbol: str,
                                           chart_type: str = "candlestick",
                                           timeframe: str = "1D",
                                           include_ai_insights: bool = True) -> Dict[str, Any]:
        """Create enhanced chart analysis with AI insights"""
        
        try:
            # Get traditional charting analysis
            traditional_analysis = await self._get_traditional_chart_analysis(
                symbol, chart_type, timeframe
            )
            
            if not include_ai_insights:
                return traditional_analysis
            
            # Enhance with AI insights
            ai_insights = await self._generate_ai_chart_insights(
                symbol, traditional_analysis, timeframe
            )
            
            # Get contextual information from RAG
            rag_context = await self._get_chart_context_from_rag(symbol, timeframe)
            
            # Combine all analyses
            enhanced_analysis = {
                'symbol': symbol,
                'timeframe': timeframe,
                'chart_type': chart_type,
                'timestamp': datetime.now(),
                'traditional_analysis': traditional_analysis,
                'ai_insights': ai_insights,
                'contextual_information': rag_context,
                'confidence_score': self._calculate_analysis_confidence(
                    traditional_analysis, ai_insights, rag_context
                ),
                'recommendations': self._synthesize_recommendations(
                    traditional_analysis, ai_insights, rag_context
                )
            }
            
            logger.info(f"Enhanced chart analysis completed for {symbol}")
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"Enhanced chart analysis failed for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}
    
    async def _get_traditional_chart_analysis(self, symbol: str, 
                                            chart_type: str, timeframe: str) -> Dict[str, Any]:
        """Get traditional chart analysis"""
        
        # Simulate traditional charting analysis
        # In practice, this would integrate with the actual ChartingArtist
        return {
            'price_action': {
                'trend': 'uptrend',
                'momentum': 'strong',
                'volatility': 'moderate'
            },
            'technical_indicators': {
                'rsi': 65.4,
                'macd': 'bullish_crossover',
                'moving_averages': 'above_sma20_sma50'
            },
            'support_resistance': {
                'support_levels': [150.0, 145.0],
                'resistance_levels': [160.0, 165.0]
            },
            'patterns': [
                {'pattern': 'ascending_triangle', 'confidence': 0.8}
            ]
        }
    
    async def _generate_ai_chart_insights(self, symbol: str, 
                                        traditional_analysis: Dict[str, Any],
                                        timeframe: str) -> Dict[str, Any]:
        """Generate AI-powered chart insights"""
        
        try:
            # Prepare analysis prompt
            prompt = self.chart_analysis_prompts['technical_insights'].format(
                chart_type='candlestick',
                symbol=symbol,
                timeframe=timeframe,
                current_price=traditional_analysis.get('price_action', {}).get('current_price', 'N/A'),
                technical_indicators=json.dumps(traditional_analysis.get('technical_indicators', {}), indent=2),
                patterns=json.dumps(traditional_analysis.get('patterns', []), indent=2)
            )
            
            # Get AI analysis
            result = await self.ai_orchestrator.execute_task(
                agent_role="technical_analyst",
                task_prompt=prompt,
                task_type="technical_analysis",
                context={
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'chart_enhanced': True
                }
            )
            
            if result.success:
                return {
                    'ai_analysis': result.result,
                    'confidence': getattr(result, 'confidence_score', 0.8),
                    'model_used': result.model_used.name if result.model_used else 'unknown',
                    'insights_generated': True
                }
            else:
                return {
                    'error': result.error_message,
                    'insights_generated': False
                }
                
        except Exception as e:
            logger.error(f"AI chart insights generation failed: {e}")
            return {'error': str(e), 'insights_generated': False}
    
    async def _get_chart_context_from_rag(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Get contextual information from RAG system"""
        
        try:
            # Query RAG for relevant context
            rag_response = await self.rag_system.query(
                query_text=f"Technical analysis context for {symbol} {timeframe} timeframe",
                query_type="technical",
                symbols=[symbol],
                agent_role="technical_analyst"
            )
            
            return {
                'contextual_analysis': rag_response.generated_response,
                'relevant_sources': rag_response.sources,
                'confidence': rag_response.confidence_score,
                'documents_used': len(rag_response.retrieved_documents)
            }
            
        except Exception as e:
            logger.warning(f"RAG context retrieval failed: {e}")
            return {'error': str(e), 'context_available': False}
    
    def _calculate_analysis_confidence(self, traditional_analysis: Dict[str, Any],
                                     ai_insights: Dict[str, Any],
                                     rag_context: Dict[str, Any]) -> float:
        """Calculate overall analysis confidence"""
        
        confidence_factors = []
        
        # Traditional analysis confidence
        if traditional_analysis.get('patterns'):
            pattern_confidences = [p.get('confidence', 0.5) for p in traditional_analysis['patterns']]
            confidence_factors.append(np.mean(pattern_confidences))
        
        # AI insights confidence
        if ai_insights.get('confidence'):
            confidence_factors.append(ai_insights['confidence'])
        
        # RAG context confidence
        if rag_context.get('confidence'):
            confidence_factors.append(rag_context['confidence'])
        
        return np.mean(confidence_factors) if confidence_factors else 0.5
    
    def _synthesize_recommendations(self, traditional_analysis: Dict[str, Any],
                                  ai_insights: Dict[str, Any],
                                  rag_context: Dict[str, Any]) -> List[str]:
        """Synthesize actionable recommendations"""
        
        recommendations = []
        
        # Extract recommendations from AI insights
        if ai_insights.get('ai_analysis'):
            ai_text = ai_insights['ai_analysis'].lower()
            if 'buy' in ai_text or 'bullish' in ai_text:
                recommendations.append("Consider long position based on AI technical analysis")
            elif 'sell' in ai_text or 'bearish' in ai_text:
                recommendations.append("Consider short position based on AI technical analysis")
        
        # Add pattern-based recommendations
        for pattern in traditional_analysis.get('patterns', []):
            if pattern.get('confidence', 0) > 0.7:
                recommendations.append(f"Strong {pattern['pattern']} pattern detected - monitor for breakout")
        
        # Add risk management recommendations
        support_levels = traditional_analysis.get('support_resistance', {}).get('support_levels', [])
        if support_levels:
            recommendations.append(f"Set stop-loss below key support at ${min(support_levels)}")
        
        return recommendations[:5]  # Limit to top 5 recommendations


class EnhancedNewsAnalysisIntegration:
    """Enhanced news analysis with AI-powered sentiment and impact assessment"""
    
    def __init__(self, ai_orchestrator: AIOrchestrator, rag_system: FinancialRAGSystem):
        self.ai_orchestrator = ai_orchestrator
        self.rag_system = rag_system
        self.news_filter = EnhancedNewsFilter()
        
        # News analysis templates
        self.news_analysis_prompts = {
            'sentiment_analysis': """
Analyze the sentiment and market impact of the following news:

Headline: {headline}
Summary: {summary}
Source: {source}
Symbol: {symbol}
Publication Time: {pub_time}

Please provide:
1. Sentiment score (-1 to +1)
2. Market impact assessment (Low/Medium/High)
3. Key themes and topics
4. Potential price impact direction
5. Time horizon for impact (immediate/short-term/long-term)
6. Confidence level in analysis

Focus on actionable market insights and trading implications.
""",
            
            'news_synthesis': """
Synthesize the following news articles into a comprehensive market outlook:

Symbol: {symbol}
Time Period: {time_period}
Number of Articles: {num_articles}

News Summary:
{news_summary}

Market Context:
{market_context}

Please create:
1. Overall sentiment trend
2. Key catalysts and drivers
3. Risk factors identified
4. Market opportunity assessment
5. Strategic recommendations
6. Timeline for potential impacts

Provide a balanced and comprehensive news-driven analysis.
""",
            
            'cross_asset_impact': """
Analyze cross-asset impact of the following news:

Primary Symbol: {primary_symbol}
Related Symbols: {related_symbols}
Sector: {sector}
Market Cap: {market_cap}

News Event: {news_event}
Event Type: {event_type}
Severity: {severity}

Assess impact on:
1. Primary symbol price action
2. Sector rotation effects
3. Related companies impact
4. Market-wide implications
5. Currency/commodity effects
6. Risk-on/risk-off sentiment

Provide cross-asset correlation analysis and trading opportunities.
"""
        }
    
    async def analyze_news_with_ai(self, 
                                 news_articles: List[Dict[str, Any]],
                                 symbol: str,
                                 time_window: str = "24h") -> Dict[str, Any]:
        """Analyze news articles with AI-powered insights"""
        
        try:
            if not news_articles:
                return {'error': 'No news articles provided', 'symbol': symbol}
            
            # Filter and prioritize news
            filtered_news = self.news_filter.filter_news(news_articles, symbol)
            
            # Individual news analysis
            individual_analyses = []
            for article in filtered_news[:10]:  # Limit to top 10 articles
                analysis = await self._analyze_single_article(article, symbol)
                individual_analyses.append(analysis)
            
            # Synthesize overall analysis
            synthesis = await self._synthesize_news_analysis(
                individual_analyses, symbol, time_window
            )
            
            # Get related context from RAG
            rag_context = await self._get_news_context_from_rag(symbol, time_window)
            
            # Calculate sentiment metrics
            sentiment_metrics = self._calculate_sentiment_metrics(individual_analyses)
            
            # Generate trading signals
            trading_signals = self._generate_news_trading_signals(
                individual_analyses, sentiment_metrics
            )
            
            enhanced_analysis = {
                'symbol': symbol,
                'time_window': time_window,
                'timestamp': datetime.now(),
                'articles_analyzed': len(individual_analyses),
                'individual_analyses': individual_analyses,
                'synthesis': synthesis,
                'rag_context': rag_context,
                'sentiment_metrics': sentiment_metrics,
                'trading_signals': trading_signals,
                'confidence_score': synthesis.get('confidence', 0.5),
                'market_impact': self._assess_market_impact(sentiment_metrics, trading_signals)
            }
            
            # Ingest news into RAG system for future queries
            await self._ingest_news_to_rag(filtered_news, symbol)
            
            logger.info(f"Enhanced news analysis completed for {symbol}: {len(individual_analyses)} articles")
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"Enhanced news analysis failed for {symbol}: {e}")
            return {'error': str(e), 'symbol': symbol}
    
    async def _analyze_single_article(self, article: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        """Analyze a single news article"""
        
        try:
            prompt = self.news_analysis_prompts['sentiment_analysis'].format(
                headline=article.get('headline', ''),
                summary=article.get('summary', ''),
                source=article.get('source', ''),
                symbol=symbol,
                pub_time=article.get('datetime', datetime.now())
            )
            
            result = await self.ai_orchestrator.execute_task(
                agent_role="news_hunter",
                task_prompt=prompt,
                task_type="news_analysis",
                context={
                    'symbol': symbol,
                    'article_id': article.get('id', 'unknown'),
                    'news_enhanced': True
                }
            )
            
            if result.success:
                # Parse AI response for structured data
                parsed_analysis = self._parse_sentiment_analysis(result.result)
                
                return {
                    'article': article,
                    'ai_analysis': result.result,
                    'parsed_sentiment': parsed_analysis,
                    'confidence': getattr(result, 'confidence_score', 0.7),
                    'model_used': result.model_used.name if result.model_used else 'unknown',
                    'analysis_successful': True
                }
            else:
                return {
                    'article': article,
                    'error': result.error_message,
                    'analysis_successful': False
                }
                
        except Exception as e:
            logger.error(f"Single article analysis failed: {e}")
            return {
                'article': article,
                'error': str(e),
                'analysis_successful': False
            }
    
    def _parse_sentiment_analysis(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI sentiment analysis response into structured data"""
        
        parsed = {
            'sentiment_score': 0.0,
            'market_impact': 'Medium',
            'impact_direction': 'Neutral',
            'time_horizon': 'short-term',
            'confidence': 0.5
        }
        
        try:
            response_lower = ai_response.lower()
            
            # Extract sentiment score
            import re
            sentiment_match = re.search(r'sentiment.*?(-?\d+\.?\d*)', response_lower)
            if sentiment_match:
                parsed['sentiment_score'] = float(sentiment_match.group(1))
            
            # Determine market impact
            if any(word in response_lower for word in ['high impact', 'significant', 'major']):
                parsed['market_impact'] = 'High'
            elif any(word in response_lower for word in ['low impact', 'minor', 'minimal']):
                parsed['market_impact'] = 'Low'
            
            # Determine direction
            if any(word in response_lower for word in ['positive', 'bullish', 'upward']):
                parsed['impact_direction'] = 'Positive'
            elif any(word in response_lower for word in ['negative', 'bearish', 'downward']):
                parsed['impact_direction'] = 'Negative'
            
        except Exception as e:
            logger.debug(f"Sentiment parsing error: {e}")
        
        return parsed
    
    async def _synthesize_news_analysis(self, individual_analyses: List[Dict[str, Any]],
                                      symbol: str, time_window: str) -> Dict[str, Any]:
        """Synthesize individual news analyses into overall outlook"""
        
        try:
            # Prepare synthesis data
            successful_analyses = [a for a in individual_analyses if a.get('analysis_successful')]
            
            if not successful_analyses:
                return {'error': 'No successful analyses to synthesize', 'confidence': 0.0}
            
            # Create news summary
            news_summary = []
            for analysis in successful_analyses:
                article = analysis['article']
                sentiment = analysis.get('parsed_sentiment', {})
                news_summary.append(f"- {article.get('headline', 'N/A')} (Sentiment: {sentiment.get('sentiment_score', 0):.2f})")
            
            prompt = self.news_analysis_prompts['news_synthesis'].format(
                symbol=symbol,
                time_period=time_window,
                num_articles=len(successful_analyses),
                news_summary='\n'.join(news_summary),
                market_context=f"Analysis period: {time_window}"
            )
            
            result = await self.ai_orchestrator.execute_task(
                agent_role="sentiment_analyst",
                task_prompt=prompt,
                task_type="sentiment_analysis",
                context={'symbol': symbol, 'synthesis': True}
            )
            
            if result.success:
                return {
                    'synthesis_text': result.result,
                    'confidence': getattr(result, 'confidence_score', 0.7),
                    'articles_synthesized': len(successful_analyses)
                }
            else:
                return {
                    'error': result.error_message,
                    'confidence': 0.0
                }
                
        except Exception as e:
            logger.error(f"News synthesis failed: {e}")
            return {'error': str(e), 'confidence': 0.0}
    
    async def _get_news_context_from_rag(self, symbol: str, time_window: str) -> Dict[str, Any]:
        """Get news context from RAG system"""
        
        try:
            rag_response = await self.rag_system.query(
                query_text=f"Recent news trends and sentiment for {symbol} in {time_window}",
                query_type="news",
                symbols=[symbol],
                agent_role="news_hunter"
            )
            
            return {
                'contextual_analysis': rag_response.generated_response,
                'historical_sources': rag_response.sources,
                'confidence': rag_response.confidence_score
            }
            
        except Exception as e:
            logger.warning(f"News RAG context failed: {e}")
            return {'error': str(e)}
    
    def _calculate_sentiment_metrics(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate aggregate sentiment metrics"""
        
        successful = [a for a in analyses if a.get('analysis_successful')]
        
        if not successful:
            return {
                'overall_sentiment': 0.0,
                'sentiment_distribution': {},
                'impact_assessment': 'Unknown',
                'consensus_strength': 0.0
            }
        
        # Extract sentiment scores
        sentiment_scores = []
        impact_levels = []
        directions = []
        
        for analysis in successful:
            parsed = analysis.get('parsed_sentiment', {})
            sentiment_scores.append(parsed.get('sentiment_score', 0.0))
            impact_levels.append(parsed.get('market_impact', 'Medium'))
            directions.append(parsed.get('impact_direction', 'Neutral'))
        
        # Calculate metrics
        overall_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0.0
        sentiment_std = np.std(sentiment_scores) if len(sentiment_scores) > 1 else 0.0
        
        # Sentiment distribution
        positive_count = sum(1 for s in sentiment_scores if s > 0.1)
        negative_count = sum(1 for s in sentiment_scores if s < -0.1)
        neutral_count = len(sentiment_scores) - positive_count - negative_count
        
        # Consensus strength (lower std = higher consensus)
        consensus_strength = max(0.0, 1.0 - sentiment_std) if sentiment_std > 0 else 1.0
        
        return {
            'overall_sentiment': overall_sentiment,
            'sentiment_std': sentiment_std,
            'sentiment_distribution': {
                'positive': positive_count,
                'negative': negative_count,
                'neutral': neutral_count
            },
            'impact_assessment': self._aggregate_impact_assessment(impact_levels),
            'consensus_strength': consensus_strength,
            'dominant_direction': max(set(directions), key=directions.count) if directions else 'Neutral'
        }
    
    def _aggregate_impact_assessment(self, impact_levels: List[str]) -> str:
        """Aggregate impact assessment from individual analyses"""
        
        if not impact_levels:
            return 'Unknown'
        
        impact_scores = {'Low': 1, 'Medium': 2, 'High': 3}
        avg_impact = np.mean([impact_scores.get(level, 2) for level in impact_levels])
        
        if avg_impact >= 2.5:
            return 'High'
        elif avg_impact >= 1.5:
            return 'Medium'
        else:
            return 'Low'
    
    def _generate_news_trading_signals(self, analyses: List[Dict[str, Any]],
                                     sentiment_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trading signals based on news analysis"""
        
        signals = {
            'signal_strength': 'Neutral',
            'direction': 'Hold',
            'confidence': 0.0,
            'reasoning': [],
            'risk_factors': []
        }
        
        overall_sentiment = sentiment_metrics.get('overall_sentiment', 0.0)
        consensus_strength = sentiment_metrics.get('consensus_strength', 0.0)
        impact_assessment = sentiment_metrics.get('impact_assessment', 'Medium')
        
        # Determine signal strength
        if abs(overall_sentiment) > 0.3 and consensus_strength > 0.6:
            signals['signal_strength'] = 'Strong'
        elif abs(overall_sentiment) > 0.1 and consensus_strength > 0.4:
            signals['signal_strength'] = 'Moderate'
        else:
            signals['signal_strength'] = 'Weak'
        
        # Determine direction
        if overall_sentiment > 0.1:
            signals['direction'] = 'Buy'
        elif overall_sentiment < -0.1:
            signals['direction'] = 'Sell'
        else:
            signals['direction'] = 'Hold'
        
        # Calculate confidence
        signals['confidence'] = min(0.9, consensus_strength * (abs(overall_sentiment) + 0.1))
        
        # Generate reasoning
        if signals['signal_strength'] == 'Strong':
            signals['reasoning'].append(f"Strong consensus ({consensus_strength:.2f}) with clear sentiment direction")
        
        if impact_assessment == 'High':
            signals['reasoning'].append("High market impact expected from news events")
        
        # Add risk factors
        if consensus_strength < 0.5:
            signals['risk_factors'].append("Low consensus among news sources - mixed signals")
        
        if impact_assessment == 'Low':
            signals['risk_factors'].append("Limited market impact expected - signals may be weak")
        
        return signals
    
    async def _ingest_news_to_rag(self, news_articles: List[Dict[str, Any]], symbol: str):
        """Ingest news articles into RAG system for future queries"""
        
        try:
            for article in news_articles:
                # Add news to RAG knowledge base
                await self.rag_system.knowledge_base.add_document(
                    FinancialDocument(
                        doc_id=f"news_{symbol}_{article.get('id', hash(article.get('headline', '')))}",
                        title=article.get('headline', 'No Title'),
                        content=article.get('summary', ''),
                        doc_type="news",
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(article.get('datetime', time.time())),
                        metadata={
                            'source': article.get('source', ''),
                            'url': article.get('url', ''),
                            'category': article.get('category', '')
                        }
                    )
                )
            
            logger.debug(f"Ingested {len(news_articles)} news articles for {symbol}")
            
        except Exception as e:
            logger.warning(f"News ingestion to RAG failed: {e}")
    
    def _assess_market_impact(self, sentiment_metrics: Dict[str, Any],
                            trading_signals: Dict[str, Any]) -> str:
        """Assess overall market impact"""
        
        impact_factors = []
        
        # Sentiment impact
        overall_sentiment = abs(sentiment_metrics.get('overall_sentiment', 0.0))
        if overall_sentiment > 0.3:
            impact_factors.append('High')
        elif overall_sentiment > 0.1:
            impact_factors.append('Medium')
        else:
            impact_factors.append('Low')
        
        # Signal strength impact
        signal_strength = trading_signals.get('signal_strength', 'Weak')
        impact_factors.append(signal_strength)
        
        # Consensus impact
        consensus = sentiment_metrics.get('consensus_strength', 0.0)
        if consensus > 0.7:
            impact_factors.append('High')
        elif consensus > 0.4:
            impact_factors.append('Medium')
        else:
            impact_factors.append('Low')
        
        # Aggregate assessment
        high_count = impact_factors.count('High') + impact_factors.count('Strong')
        medium_count = impact_factors.count('Medium') + impact_factors.count('Moderate')
        
        if high_count >= 2:
            return 'High'
        elif high_count + medium_count >= 2:
            return 'Medium'
        else:
            return 'Low'


class EnhancedRiskManagementIntegration:
    """Enhanced risk management with AI-powered analysis and recommendations"""
    
    def __init__(self, ai_orchestrator: AIOrchestrator, ml_pipeline: MLPipeline):
        self.ai_orchestrator = ai_orchestrator
        self.ml_pipeline = ml_pipeline
        
        # Risk analysis templates
        self.risk_prompts = {
            'portfolio_risk': """
Analyze the risk profile of the following portfolio:

Portfolio Composition:
{portfolio_composition}

Individual Position Risks:
{position_risks}

Market Context:
{market_context}

Correlation Analysis:
{correlation_data}

Please provide:
1. Overall portfolio risk assessment (Low/Medium/High)
2. Key risk concentrations and exposures
3. Correlation risks and diversification gaps
4. Stress test scenarios and potential losses
5. Risk mitigation recommendations
6. Position sizing adjustments
7. Hedging opportunities

Focus on actionable risk management strategies.
""",
            
            'single_position_risk': """
Assess the risk characteristics of this position:

Symbol: {symbol}
Position Size: {position_size}
Entry Price: {entry_price}
Current Price: {current_price}
Time Held: {time_held}

Market Data:
{market_data}

Technical Analysis:
{technical_analysis}

Fundamental Factors:
{fundamental_factors}

Please evaluate:
1. Position-specific risk level
2. Maximum potential loss scenarios
3. Volatility and drawdown expectations
4. Catalyst risks (earnings, events, news)
5. Technical risk levels (support/resistance)
6. Optimal stop-loss and take-profit levels
7. Position management recommendations

Provide comprehensive single-position risk analysis.
""",
            
            'market_regime_risk': """
Analyze current market regime and associated risks:

Market Indicators:
{market_indicators}

Economic Context:
{economic_context}

Sector Performance:
{sector_performance}

Volatility Environment:
{volatility_data}

Historical Context:
{historical_context}

Assess:
1. Current market regime classification
2. Regime stability and transition risks
3. Asset class correlations in current regime
4. Optimal portfolio allocation for regime
5. Early warning indicators for regime change
6. Risk management adjustments needed
7. Opportunity areas in current environment

Focus on regime-appropriate risk management strategies.
"""
        }
    
    async def assess_portfolio_risk(self, 
                                  portfolio: Dict[str, Any],
                                  market_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Comprehensive AI-powered portfolio risk assessment"""
        
        try:
            # Individual position analysis
            position_risks = {}
            for symbol, position in portfolio.get('positions', {}).items():
                position_risk = await self._assess_position_risk(symbol, position)
                position_risks[symbol] = position_risk
            
            # Calculate portfolio-level metrics
            portfolio_metrics = self._calculate_portfolio_metrics(portfolio, position_risks)
            
            # Get correlation analysis
            correlation_analysis = await self._analyze_portfolio_correlations(
                list(portfolio.get('positions', {}).keys())
            )
            
            # ML-based risk predictions
            ml_risk_assessment = await self._get_ml_risk_predictions(portfolio)
            
            # AI-powered comprehensive analysis
            ai_risk_analysis = await self._get_ai_portfolio_risk_analysis(
                portfolio, position_risks, portfolio_metrics, correlation_analysis
            )
            
            # Stress testing
            stress_test_results = await self._perform_portfolio_stress_tests(portfolio, position_risks)
            
            # Risk recommendations
            risk_recommendations = self._generate_risk_recommendations(
                portfolio_metrics, position_risks, ai_risk_analysis, stress_test_results
            )
            
            comprehensive_risk_assessment = {
                'portfolio_id': portfolio.get('id', 'unknown'),
                'assessment_timestamp': datetime.now(),
                'overall_risk_level': self._determine_overall_risk_level(portfolio_metrics),
                'portfolio_metrics': portfolio_metrics,
                'position_risks': position_risks,
                'correlation_analysis': correlation_analysis,
                'ml_predictions': ml_risk_assessment,
                'ai_analysis': ai_risk_analysis,
                'stress_test_results': stress_test_results,
                'recommendations': risk_recommendations,
                'confidence_score': ai_risk_analysis.get('confidence', 0.7),
                'next_review_date': datetime.now() + timedelta(days=7)
            }
            
            logger.info(f"Portfolio risk assessment completed: {portfolio.get('id', 'unknown')}")
            return comprehensive_risk_assessment
            
        except Exception as e:
            logger.error(f"Portfolio risk assessment failed: {e}")
            return {'error': str(e), 'portfolio_id': portfolio.get('id', 'unknown')}
    
    async def _assess_position_risk(self, symbol: str, position: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk for individual position"""
        
        try:
            # Get market data
            market_data = await self._get_position_market_data(symbol)
            
            # Calculate position metrics
            position_metrics = self._calculate_position_metrics(position, market_data)
            
            # Get AI risk analysis
            prompt = self.risk_prompts['single_position_risk'].format(
                symbol=symbol,
                position_size=position.get('size', 0),
                entry_price=position.get('entry_price', 0),
                current_price=market_data.get('current_price', 0),
                time_held=position.get('days_held', 0),
                market_data=json.dumps(market_data, indent=2),
                technical_analysis=json.dumps(market_data.get('technical', {}), indent=2),
                fundamental_factors=json.dumps(market_data.get('fundamentals', {}), indent=2)
            )
            
            result = await self.ai_orchestrator.execute_task(
                agent_role="risk_manager",
                task_prompt=prompt,
                task_type="risk_assessment",
                context={'symbol': symbol, 'position_analysis': True}
            )
            
            return {
                'symbol': symbol,
                'position_metrics': position_metrics,
                'ai_analysis': result.result if result.success else None,
                'risk_level': self._categorize_risk_level(position_metrics),
                'max_loss_estimate': position_metrics.get('max_loss_estimate', 0),
                'stop_loss_recommendation': position_metrics.get('stop_loss_level'),
                'confidence': getattr(result, 'confidence_score', 0.7),
                'analysis_successful': result.success
            }
            
        except Exception as e:
            logger.error(f"Position risk assessment failed for {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'risk_level': 'Unknown',
                'analysis_successful': False
            }
    
    def _calculate_position_metrics(self, position: Dict[str, Any],
                                  market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate position-specific risk metrics"""
        
        metrics = {}
        
        try:
            entry_price = position.get('entry_price', 0)
            current_price = market_data.get('current_price', entry_price)
            position_size = position.get('size', 0)
            
            # P&L calculations
            unrealized_pnl = (current_price - entry_price) * position_size
            unrealized_pnl_pct = (current_price / entry_price - 1) if entry_price > 0 else 0
            
            # Volatility-based risk
            volatility = market_data.get('volatility', 0.2)  # 20% default
            one_day_var = current_price * volatility / np.sqrt(252)  # Daily VaR
            position_var = one_day_var * abs(position_size)
            
            # Support/resistance based risk
            support_level = market_data.get('support_level')
            resistance_level = market_data.get('resistance_level')
            
            max_loss_estimate = 0
            if support_level and current_price > support_level:
                max_loss_estimate = (current_price - support_level) * abs(position_size)
            else:
                max_loss_estimate = position_var * 2.33  # 99% confidence
            
            metrics = {
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct,
                'position_var': position_var,
                'max_loss_estimate': max_loss_estimate,
                'volatility': volatility,
                'position_value': current_price * abs(position_size),
                'stop_loss_level': support_level if support_level else current_price * 0.95,
                'take_profit_level': resistance_level if resistance_level else current_price * 1.05
            }
            
        except Exception as e:
            logger.error(f"Position metrics calculation failed: {e}")
            metrics = {'error': str(e)}
        
        return metrics
    
    async def _get_position_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data for position analysis"""
        
        # Simulate market data retrieval
        # In practice, integrate with actual data sources
        return {
            'current_price': 150.0,
            'volatility': 0.25,
            'support_level': 145.0,
            'resistance_level': 160.0,
            'technical': {
                'rsi': 65,
                'macd': 'bullish',
                'trend': 'upward'
            },
            'fundamentals': {
                'pe_ratio': 18.5,
                'debt_to_equity': 0.3,
                'growth_rate': 0.15
            }
        }
    
    def _calculate_portfolio_metrics(self, portfolio: Dict[str, Any],
                                   position_risks: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate portfolio-level risk metrics"""
        
        try:
            positions = portfolio.get('positions', {})
            
            # Portfolio value and allocation
            total_value = sum(
                pos.get('size', 0) * pos.get('current_price', pos.get('entry_price', 0))
                for pos in positions.values()
            )
            
            # Risk aggregation
            total_var = sum(
                risk.get('position_metrics', {}).get('position_var', 0)
                for risk in position_risks.values()
                if risk.get('analysis_successful', False)
            )
            
            # Concentration analysis
            position_weights = {}
            for symbol, position in positions.items():
                position_value = position.get('size', 0) * position.get('current_price', position.get('entry_price', 0))
                position_weights[symbol] = position_value / total_value if total_value > 0 else 0
            
            max_concentration = max(position_weights.values()) if position_weights else 0
            
            # Sector concentration (simplified)
            sector_weights = defaultdict(float)
            for symbol, weight in position_weights.items():
                # Simplified sector mapping - in practice, use actual sector data
                sector = 'Technology'  # Default sector
                sector_weights[sector] += weight
            
            max_sector_concentration = max(sector_weights.values()) if sector_weights else 0
            
            return {
                'total_portfolio_value': total_value,
                'total_var': total_var,
                'var_as_percent_of_portfolio': (total_var / total_value) if total_value > 0 else 0,
                'max_position_concentration': max_concentration,
                'max_sector_concentration': max_sector_concentration,
                'number_of_positions': len(positions),
                'position_weights': position_weights,
                'sector_weights': dict(sector_weights),
                'diversification_score': 1 - max_concentration  # Simple diversification measure
            }
            
        except Exception as e:
            logger.error(f"Portfolio metrics calculation failed: {e}")
            return {'error': str(e)}
    
    def _categorize_risk_level(self, position_metrics: Dict[str, Any]) -> str:
        """Categorize position risk level"""
        
        try:
            volatility = position_metrics.get('volatility', 0.2)
            var_pct = position_metrics.get('position_var', 0) / position_metrics.get('position_value', 1)
            
            if volatility > 0.4 or var_pct > 0.05:
                return 'High'
            elif volatility > 0.25 or var_pct > 0.02:
                return 'Medium'
            else:
                return 'Low'
                
        except Exception:
            return 'Unknown'
    
    def _determine_overall_risk_level(self, portfolio_metrics: Dict[str, Any]) -> str:
        """Determine overall portfolio risk level"""
        
        try:
            var_pct = portfolio_metrics.get('var_as_percent_of_portfolio', 0)
            max_concentration = portfolio_metrics.get('max_position_concentration', 0)
            diversification_score = portfolio_metrics.get('diversification_score', 1)
            
            risk_score = 0
            
            # VaR contribution
            if var_pct > 0.03:
                risk_score += 2
            elif var_pct > 0.015:
                risk_score += 1
            
            # Concentration contribution
            if max_concentration > 0.3:
                risk_score += 2
            elif max_concentration > 0.15:
                risk_score += 1
            
            # Diversification contribution
            if diversification_score < 0.5:
                risk_score += 2
            elif diversification_score < 0.75:
                risk_score += 1
            
            if risk_score >= 4:
                return 'High'
            elif risk_score >= 2:
                return 'Medium'
            else:
                return 'Low'
                
        except Exception:
            return 'Unknown'
    
    async def _analyze_portfolio_correlations(self, symbols: List[str]) -> Dict[str, Any]:
        """Analyze correlations between portfolio positions"""
        
        try:
            # Simulate correlation analysis
            # In practice, calculate actual correlations from price data
            correlations = {}
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols):
                    if i < j:
                        # Simulate correlation (random for demo)
                        correlation = np.random.uniform(-0.3, 0.8)
                        correlations[f"{symbol1}_{symbol2}"] = correlation
            
            # Calculate average correlation
            avg_correlation = np.mean(list(correlations.values())) if correlations else 0
            
            # Identify highly correlated pairs
            high_correlation_pairs = [
                pair for pair, corr in correlations.items()
                if abs(corr) > 0.7
            ]
            
            return {
                'pairwise_correlations': correlations,
                'average_correlation': avg_correlation,
                'high_correlation_pairs': high_correlation_pairs,
                'diversification_benefit': max(0, 1 - avg_correlation),
                'correlation_risk_score': 'High' if avg_correlation > 0.6 else 'Medium' if avg_correlation > 0.3 else 'Low'
            }
            
        except Exception as e:
            logger.error(f"Correlation analysis failed: {e}")
            return {'error': str(e)}
    
    async def _get_ml_risk_predictions(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Get ML-based risk predictions"""
        
        try:
            # Use ML pipeline for risk predictions if available
            if self.ml_pipeline:
                # This would use actual ML models for risk prediction
                # For now, simulate ML predictions
                
                symbols = list(portfolio.get('positions', {}).keys())
                
                ml_predictions = {}
                for symbol in symbols:
                    # Simulate ML risk prediction
                    ml_predictions[symbol] = {
                        'predicted_volatility': np.random.uniform(0.15, 0.35),
                        'downside_probability': np.random.uniform(0.2, 0.4),
                        'expected_return': np.random.uniform(-0.05, 0.15),
                        'confidence': np.random.uniform(0.6, 0.9)
                    }
                
                return {
                    'individual_predictions': ml_predictions,
                    'portfolio_predicted_volatility': np.mean([pred['predicted_volatility'] for pred in ml_predictions.values()]),
                    'portfolio_downside_probability': np.mean([pred['downside_probability'] for pred in ml_predictions.values()]),
                    'ml_model_available': True
                }
            else:
                return {
                    'ml_model_available': False,
                    'message': 'ML pipeline not available for risk predictions'
                }
                
        except Exception as e:
            logger.error(f"ML risk predictions failed: {e}")
            return {'error': str(e), 'ml_model_available': False}
    
    async def _get_ai_portfolio_risk_analysis(self, portfolio: Dict[str, Any],
                                            position_risks: Dict[str, Any],
                                            portfolio_metrics: Dict[str, Any],
                                            correlation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive AI portfolio risk analysis"""
        
        try:
            # Prepare portfolio composition summary
            positions = portfolio.get('positions', {})
            composition_summary = []
            
            for symbol, position in positions.items():
                weight = portfolio_metrics.get('position_weights', {}).get(symbol, 0)
                risk_level = position_risks.get(symbol, {}).get('risk_level', 'Unknown')
                composition_summary.append(f"- {symbol}: {weight*100:.1f}% allocation (Risk: {risk_level})")
            
            prompt = self.risk_prompts['portfolio_risk'].format(
                portfolio_composition='\n'.join(composition_summary),
                position_risks=json.dumps({k: v.get('position_metrics', {}) for k, v in position_risks.items()}, indent=2),
                market_context="Current market environment analysis",
                correlation_data=json.dumps(correlation_analysis, indent=2)
            )
            
            result = await self.ai_orchestrator.execute_task(
                agent_role="risk_manager",
                task_prompt=prompt,
                task_type="risk_assessment",
                context={'portfolio_analysis': True}
            )
            
            if result.success:
                return {
                    'comprehensive_analysis': result.result,
                    'confidence': getattr(result, 'confidence_score', 0.7),
                    'model_used': result.model_used.name if result.model_used else 'unknown',
                    'analysis_successful': True
                }
            else:
                return {
                    'error': result.error_message,
                    'analysis_successful': False
                }
                
        except Exception as e:
            logger.error(f"AI portfolio risk analysis failed: {e}")
            return {'error': str(e), 'analysis_successful': False}
    
    async def _perform_portfolio_stress_tests(self, portfolio: Dict[str, Any],
                                            position_risks: Dict[str, Any]) -> Dict[str, Any]:
        """Perform portfolio stress tests"""
        
        try:
            portfolio_value = sum(
                pos.get('size', 0) * pos.get('current_price', pos.get('entry_price', 0))
                for pos in portfolio.get('positions', {}).values()
            )
            
            # Define stress scenarios
            stress_scenarios = {
                'market_crash_10pct': {'market_decline': -0.10},
                'market_crash_20pct': {'market_decline': -0.20},
                'volatility_spike': {'volatility_multiplier': 2.0},
                'sector_rotation': {'sector_decline': -0.15},
                'black_swan': {'extreme_decline': -0.30}
            }
            
            stress_results = {}
            
            for scenario_name, scenario_params in stress_scenarios.items():
                scenario_loss = 0
                
                for symbol, position_risk in position_risks.items():
                    if not position_risk.get('analysis_successful'):
                        continue
                    
                    position_value = position_risk.get('position_metrics', {}).get('position_value', 0)
                    
                    if 'market_decline' in scenario_params:
                        # Apply market decline
                        loss = position_value * abs(scenario_params['market_decline'])
                        scenario_loss += loss
                    
                    elif 'volatility_multiplier' in scenario_params:
                        # Apply volatility-based loss
                        position_var = position_risk.get('position_metrics', {}).get('position_var', 0)
                        loss = position_var * scenario_params['volatility_multiplier']
                        scenario_loss += loss
                    
                    elif 'extreme_decline' in scenario_params:
                        # Apply extreme scenario
                        loss = position_value * abs(scenario_params['extreme_decline'])
                        scenario_loss += loss
                
                stress_results[scenario_name] = {
                    'total_loss': scenario_loss,
                    'loss_percentage': (scenario_loss / portfolio_value) if portfolio_value > 0 else 0,
                    'remaining_value': portfolio_value - scenario_loss,
                    'scenario_parameters': scenario_params
                }
            
            return {
                'stress_scenarios': stress_results,
                'max_loss_scenario': max(stress_results.items(), key=lambda x: x[1]['total_loss']),
                'portfolio_resilience_score': 1 - max(result['loss_percentage'] for result in stress_results.values())
            }
            
        except Exception as e:
            logger.error(f"Stress testing failed: {e}")
            return {'error': str(e)}
    
    def _generate_risk_recommendations(self, portfolio_metrics: Dict[str, Any],
                                     position_risks: Dict[str, Any],
                                     ai_analysis: Dict[str, Any],
                                     stress_tests: Dict[str, Any]) -> List[str]:
        """Generate actionable risk management recommendations"""
        
        recommendations = []
        
        try:
            # Concentration risk recommendations
            max_concentration = portfolio_metrics.get('max_position_concentration', 0)
            if max_concentration > 0.25:
                recommendations.append(f"Reduce concentration risk - maximum position is {max_concentration*100:.1f}% of portfolio")
            
            # Diversification recommendations
            diversification_score = portfolio_metrics.get('diversification_score', 1)
            if diversification_score < 0.7:
                recommendations.append("Improve diversification by adding positions in different sectors/asset classes")
            
            # VaR-based recommendations
            var_pct = portfolio_metrics.get('var_as_percent_of_portfolio', 0)
            if var_pct > 0.03:
                recommendations.append(f"Portfolio VaR is high ({var_pct*100:.1f}%) - consider reducing position sizes")
            
            # Individual position recommendations
            for symbol, risk in position_risks.items():
                if risk.get('risk_level') == 'High':
                    recommendations.append(f"Review high-risk position in {symbol} - consider reducing size or hedging")
            
            # Stress test recommendations
            if stress_tests.get('portfolio_resilience_score', 1) < 0.5:
                recommendations.append("Portfolio shows high vulnerability to stress scenarios - consider hedging strategies")
            
            # Limit recommendations to most important
            return recommendations[:7]
            
        except Exception as e:
            logger.error(f"Risk recommendation generation failed: {e}")
            return ["Unable to generate recommendations due to analysis error"]


class ComprehensiveAIIntegrationManager:
    """Main manager for all AI integrations with TradingAgents-CN"""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        
        # Core AI systems
        self.ai_orchestrator = None
        self.rag_system = None
        self.automation_system = None
        self.coordinator = None
        self.production_api = None
        
        # Integration components
        self.charting_integration = None
        self.news_integration = None
        self.risk_integration = None
        
        # System state
        self.integration_status = {}
        self.performance_metrics = {}
        
        logger.info("AI Integration Manager initialized")
    
    async def initialize_ai_systems(self, multi_model_config: Dict[str, Any]):
        """Initialize all AI systems"""
        
        try:
            logger.info("Initializing AI systems...")
            
            # Initialize AI Orchestrator
            if self.config.enable_llm_orchestrator:
                self.ai_orchestrator = AIOrchestrator(multi_model_config)
                self.integration_status['ai_orchestrator'] = 'initialized'
                logger.info("AI Orchestrator initialized")
            
            # Initialize RAG System
            if self.config.enable_rag_system:
                self.rag_system = FinancialRAGSystem(
                    knowledge_base_path=self.config.knowledge_base_path,
                    llm_orchestrator=self.ai_orchestrator
                )
                self.integration_status['rag_system'] = 'initialized'
                logger.info("RAG System initialized")
            
            # Initialize Automation System
            if self.config.enable_automation:
                self.automation_system = IntelligentAutomation(
                    config={
                        'reports_dir': self.config.reports_output_path,
                        'templates_dir': str(Path(self.config.reports_output_path) / 'templates')
                    },
                    llm_orchestrator=self.ai_orchestrator,
                    rag_system=self.rag_system
                )
                self.integration_status['automation_system'] = 'initialized'
                logger.info("Automation System initialized")
            
            # Initialize Multi-Agent Coordinator
            if self.config.enable_coordination:
                from tradingagents.core.multi_model_manager import MultiModelManager
                mm_manager = MultiModelManager(multi_model_config)
                
                self.coordinator = EnhancedMultiAgentCoordinator(
                    multi_model_manager=mm_manager,
                    llm_orchestrator=self.ai_orchestrator
                )
                self.integration_status['coordinator'] = 'initialized'
                logger.info("Multi-Agent Coordinator initialized")
            
            # Initialize Production API
            if self.config.enable_production_api:
                self.production_api = ProductionAPIServer(multi_model_config)
                self.production_api.set_ai_components(
                    self.ai_orchestrator,
                    self.rag_system,
                    self.automation_system,
                    self.coordinator
                )
                self.integration_status['production_api'] = 'initialized'
                logger.info("Production API initialized")
            
            logger.info("All AI systems initialized successfully")
            
        except Exception as e:
            logger.error(f"AI systems initialization failed: {e}")
            raise
    
    async def initialize_integrations(self, ml_pipeline: MLPipeline = None):
        """Initialize integrations with existing components"""
        
        try:
            logger.info("Initializing component integrations...")
            
            # Initialize ChartingArtist integration
            if self.config.integrate_charting_artist and self.ai_orchestrator:
                self.charting_integration = EnhancedChartingArtistIntegration(
                    self.ai_orchestrator, self.rag_system
                )
                self.integration_status['charting_integration'] = 'initialized'
                logger.info("ChartingArtist integration initialized")
            
            # Initialize News Analysis integration
            if self.config.integrate_news_analysis and self.ai_orchestrator:
                self.news_integration = EnhancedNewsAnalysisIntegration(
                    self.ai_orchestrator, self.rag_system
                )
                self.integration_status['news_integration'] = 'initialized'
                logger.info("News Analysis integration initialized")
            
            # Initialize Risk Management integration
            if self.config.integrate_risk_management and self.ai_orchestrator:
                self.risk_integration = EnhancedRiskManagementIntegration(
                    self.ai_orchestrator, ml_pipeline
                )
                self.integration_status['risk_integration'] = 'initialized'
                logger.info("Risk Management integration initialized")
            
            logger.info("All component integrations initialized successfully")
            
        except Exception as e:
            logger.error(f"Component integrations initialization failed: {e}")
            raise
    
    async def run_comprehensive_analysis(self, 
                                       symbol: str,
                                       analysis_type: str = "full",
                                       include_chart_analysis: bool = True,
                                       include_news_analysis: bool = True,
                                       include_risk_assessment: bool = True) -> Dict[str, Any]:
        """Run comprehensive AI-powered analysis"""
        
        try:
            start_time = datetime.now()
            analysis_results = {
                'symbol': symbol,
                'analysis_type': analysis_type,
                'timestamp': start_time,
                'components': {}
            }
            
            # Chart analysis
            if include_chart_analysis and self.charting_integration:
                logger.info(f"Running enhanced chart analysis for {symbol}")
                chart_analysis = await self.charting_integration.create_enhanced_chart_analysis(
                    symbol=symbol,
                    include_ai_insights=True
                )
                analysis_results['components']['chart_analysis'] = chart_analysis
            
            # News analysis
            if include_news_analysis and self.news_integration:
                logger.info(f"Running enhanced news analysis for {symbol}")
                # Get recent news (simulated)
                news_articles = []  # Would get actual news articles
                news_analysis = await self.news_integration.analyze_news_with_ai(
                    news_articles=news_articles,
                    symbol=symbol
                )
                analysis_results['components']['news_analysis'] = news_analysis
            
            # Risk assessment
            if include_risk_assessment and self.risk_integration:
                logger.info(f"Running risk assessment for {symbol}")
                # Create sample portfolio for single symbol
                sample_portfolio = {
                    'id': f'single_position_{symbol}',
                    'positions': {
                        symbol: {
                            'size': 100,
                            'entry_price': 150.0,
                            'current_price': 152.0,
                            'days_held': 30
                        }
                    }
                }
                risk_assessment = await self.risk_integration.assess_portfolio_risk(sample_portfolio)
                analysis_results['components']['risk_assessment'] = risk_assessment
            
            # Synthesis using coordination system
            if self.coordinator and len(analysis_results['components']) > 1:
                logger.info(f"Creating coordinated synthesis for {symbol}")
                
                from .enhanced_coordination import CoordinationTask
                
                synthesis_task = CoordinationTask(
                    task_id=f"synthesis_{symbol}_{int(time.time())}",
                    task_type="comprehensive_analysis",
                    description=f"Synthesize comprehensive analysis results for {symbol}",
                    context={
                        'symbol': symbol,
                        'analysis_components': list(analysis_results['components'].keys()),
                        'synthesis_mode': True
                    },
                    complexity_level="high",
                    priority=0.8
                )
                
                coordination_result = await self.coordinator.execute_coordinated_analysis(
                    task=synthesis_task,
                    max_agents=3
                )
                
                analysis_results['coordinated_synthesis'] = coordination_result
            
            # Calculate overall metrics
            analysis_results['execution_time'] = (datetime.now() - start_time).total_seconds()
            analysis_results['success'] = True
            analysis_results['components_analyzed'] = len(analysis_results['components'])
            
            logger.info(f"Comprehensive analysis completed for {symbol} in {analysis_results['execution_time']:.2f}s")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Comprehensive analysis failed for {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now()
            }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        
        return {
            'integration_status': self.integration_status,
            'config': {
                'llm_orchestrator_enabled': self.config.enable_llm_orchestrator,
                'rag_system_enabled': self.config.enable_rag_system,
                'automation_enabled': self.config.enable_automation,
                'coordination_enabled': self.config.enable_coordination,
                'production_api_enabled': self.config.enable_production_api
            },
            'system_health': {
                'ai_orchestrator': self.ai_orchestrator.get_health_status() if self.ai_orchestrator else None,
                'rag_system': self.rag_system.get_system_stats() if self.rag_system else None,
                'automation_system': self.automation_system.get_automation_status() if self.automation_system else None,
                'coordinator': self.coordinator.get_coordination_stats() if self.coordinator else None
            },
            'last_updated': datetime.now().isoformat()
        }
    
    async def start_production_services(self):
        """Start production services"""
        
        try:
            # Start automation scheduler if available
            if self.automation_system:
                self.automation_system.start_scheduler()
                logger.info("Automation scheduler started")
            
            # Start production API if available
            if self.production_api and self.config.enable_production_api:
                # Note: In practice, you'd run this in a separate thread or process
                logger.info("Production API ready to start")
            
            logger.info("Production services started")
            
        except Exception as e:
            logger.error(f"Failed to start production services: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown all AI systems gracefully"""
        
        try:
            logger.info("Shutting down AI systems...")
            
            # Stop automation system
            if self.automation_system:
                self.automation_system.stop_scheduler()
                logger.info("Automation scheduler stopped")
            
            # Save RAG system data
            if self.rag_system:
                self.rag_system.knowledge_base.save_knowledge_base()
                logger.info("RAG knowledge base saved")
            
            # Clear caches
            if self.ai_orchestrator:
                self.ai_orchestrator.clear_cache()
                logger.info("AI orchestrator cache cleared")
            
            logger.info("AI systems shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Factory function for easy setup
def create_ai_integration_manager(config_dict: Dict[str, Any] = None) -> ComprehensiveAIIntegrationManager:
    """
    Factory function to create AI integration manager
    
    Args:
        config_dict: Optional configuration dictionary
        
    Returns:
        Configured ComprehensiveAIIntegrationManager
    """
    
    # Create integration config
    integration_config = IntegrationConfig()
    
    if config_dict:
        for key, value in config_dict.items():
            if hasattr(integration_config, key):
                setattr(integration_config, key, value)
    
    # Create manager
    manager = ComprehensiveAIIntegrationManager(integration_config)
    
    logger.info("AI Integration Manager created")
    return manager