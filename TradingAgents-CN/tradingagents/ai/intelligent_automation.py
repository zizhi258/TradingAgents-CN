"""
Intelligent Automation System for TradingAgents-CN

This module provides AI-powered automation for report generation, smart alerting,
dynamic strategy recommendations, and automated decision-making workflows.
"""

import asyncio
import json
import os
import pandas as pd
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import schedule
from pathlib import Path
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from email.mime.application import MimeApplication
import jinja2

# TradingAgents imports
from tradingagents.utils.logging_init import get_logger
from tradingagents.dataflows import get_YFin_data_window, get_china_stock_data_unified
from tradingagents.services.mailer.email_sender import EmailSender

logger = get_logger("intelligent_automation")


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ReportType(Enum):
    """Types of automated reports"""
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_ANALYSIS = "weekly_analysis"
    MONTHLY_REVIEW = "monthly_review"
    RISK_ASSESSMENT = "risk_assessment"
    MARKET_ALERT = "market_alert"
    PORTFOLIO_UPDATE = "portfolio_update"
    CUSTOM_ANALYSIS = "custom_analysis"


class AutomationTrigger(Enum):
    """Automation trigger types"""
    SCHEDULED = "scheduled"
    PRICE_THRESHOLD = "price_threshold"
    VOLUME_THRESHOLD = "volume_threshold"
    NEWS_EVENT = "news_event"
    TECHNICAL_SIGNAL = "technical_signal"
    MARKET_CONDITION = "market_condition"
    CUSTOM_CONDITION = "custom_condition"


@dataclass
class AlertCondition:
    """Alert condition definition"""
    condition_id: str
    name: str
    description: str
    trigger_type: AutomationTrigger
    severity: AlertSeverity
    parameters: Dict[str, Any] = field(default_factory=dict)
    symbols: Optional[List[str]] = None
    enabled: bool = True
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    cooldown_minutes: int = 60


@dataclass
class ReportTemplate:
    """Report template configuration"""
    template_id: str
    name: str
    report_type: ReportType
    template_content: str
    format: str = "html"  # html, markdown, pdf
    recipients: List[str] = field(default_factory=list)
    scheduling: Optional[Dict[str, Any]] = None
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationTask:
    """Automation task definition"""
    task_id: str
    name: str
    task_type: str
    trigger: AutomationTrigger
    action: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0


@dataclass
class SmartAlert:
    """Smart alert with context and recommendations"""
    alert_id: str
    title: str
    message: str
    severity: AlertSeverity
    symbol: Optional[str] = None
    condition_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    action_taken: Optional[str] = None
    acknowledged: bool = False


class MarketConditionMonitor:
    """Monitor market conditions and detect significant changes"""
    
    def __init__(self):
        self.market_indicators = {}
        self.thresholds = {
            'volatility_spike': 2.0,  # 2x normal volatility
            'volume_surge': 3.0,      # 3x average volume
            'price_gap': 0.05,        # 5% price gap
            'correlation_break': 0.3   # Correlation change > 0.3
        }
    
    def analyze_market_conditions(self, symbol: str, 
                                data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze current market conditions"""
        try:
            if data.empty or len(data) < 20:
                return {}
            
            conditions = {}
            
            # Volatility analysis
            returns = data['Close'].pct_change().dropna()
            current_vol = returns.tail(5).std() * np.sqrt(252)
            historical_vol = returns.std() * np.sqrt(252)
            vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1
            
            conditions['volatility'] = {
                'current': float(current_vol),
                'historical': float(historical_vol),
                'ratio': float(vol_ratio),
                'spike_detected': vol_ratio > self.thresholds['volatility_spike']
            }
            
            # Volume analysis
            avg_volume = data['Volume'].tail(20).mean()
            recent_volume = data['Volume'].tail(5).mean()
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            conditions['volume'] = {
                'recent_avg': float(recent_volume),
                'historical_avg': float(avg_volume),
                'ratio': float(volume_ratio),
                'surge_detected': volume_ratio > self.thresholds['volume_surge']
            }
            
            # Price gap analysis
            price_changes = data['Close'].pct_change().abs()
            max_change = price_changes.tail(5).max()
            
            conditions['price_action'] = {
                'max_recent_change': float(max_change),
                'gap_detected': max_change > self.thresholds['price_gap'],
                'trend_direction': 'up' if data['Close'].tail(5).mean() > data['Close'].head(5).mean() else 'down'
            }
            
            # Technical indicators
            conditions['technical'] = self._calculate_technical_signals(data)
            
            return conditions
            
        except Exception as e:
            logger.error(f"Market condition analysis failed for {symbol}: {e}")
            return {}
    
    def _calculate_technical_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical analysis signals"""
        try:
            signals = {}
            
            # Simple Moving Averages
            sma_20 = data['Close'].rolling(20).mean()
            sma_50 = data['Close'].rolling(50).mean() if len(data) >= 50 else sma_20
            
            current_price = data['Close'].iloc[-1]
            
            signals['sma_position'] = {
                'above_sma20': current_price > sma_20.iloc[-1],
                'above_sma50': current_price > sma_50.iloc[-1],
                'sma_crossover': sma_20.iloc[-1] > sma_50.iloc[-1] if len(sma_50.dropna()) > 0 else False
            }
            
            # RSI calculation
            rsi = self._calculate_rsi(data['Close'])
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                signals['rsi'] = {
                    'value': float(current_rsi),
                    'overbought': current_rsi > 70,
                    'oversold': current_rsi < 30
                }
            
            # Support/Resistance levels
            highs = data['High'].rolling(10).max()
            lows = data['Low'].rolling(10).min()
            
            signals['support_resistance'] = {
                'resistance_level': float(highs.iloc[-1]),
                'support_level': float(lows.iloc[-1]),
                'near_resistance': abs(current_price - highs.iloc[-1]) / current_price < 0.02,
                'near_support': abs(current_price - lows.iloc[-1]) / current_price < 0.02
            }
            
            return signals
            
        except Exception as e:
            logger.error(f"Technical signal calculation failed: {e}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        try:
            delta = prices.diff()
            gain = np.where(delta > 0, delta, 0)
            loss = np.where(delta < 0, -delta, 0)
            
            avg_gain = pd.Series(gain).rolling(window=window).mean()
            avg_loss = pd.Series(loss).rolling(window=window).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
        except Exception as e:
            logger.error(f"RSI calculation failed: {e}")
            return pd.Series()


class ReportGenerator:
    """AI-powered report generator with templates and customization"""
    
    def __init__(self, 
                 template_dir: str = "report_templates",
                 output_dir: str = "generated_reports",
                 llm_orchestrator=None):
        
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.llm_orchestrator = llm_orchestrator
        
        # Ensure directories exist
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=True
        )
        
        # Default templates
        self.default_templates = {
            ReportType.DAILY_SUMMARY: self._get_daily_summary_template(),
            ReportType.MARKET_ALERT: self._get_market_alert_template(),
            ReportType.RISK_ASSESSMENT: self._get_risk_assessment_template()
        }
        
        self._create_default_templates()
        
        logger.info("Report Generator initialized")
    
    async def generate_report(self, 
                            report_type: ReportType,
                            symbols: List[str],
                            template_id: Optional[str] = None,
                            custom_parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate intelligent report using AI analysis
        
        Args:
            report_type: Type of report to generate
            symbols: List of symbols to include
            template_id: Custom template ID
            custom_parameters: Additional parameters
            
        Returns:
            Dict containing report content and metadata
        """
        try:
            start_time = datetime.now()
            parameters = custom_parameters or {}
            
            # Collect data for analysis
            data_collection = await self._collect_report_data(symbols, report_type)
            
            # Generate AI insights if orchestrator available
            ai_insights = {}
            if self.llm_orchestrator:
                ai_insights = await self._generate_ai_insights(
                    symbols, data_collection, report_type
                )
            
        # Prepare template context
        template_context = {
            'report_type': report_type.value,
            'symbols': symbols,
            'generation_time': start_time,
            'data': data_collection,
            'ai_insights': ai_insights,
            'parameters': parameters
        }

            # Attach latest ChartingArtist charts into context (if available)
            try:
                charts_by_symbol = self._collect_charts_for_symbols(symbols)
                if charts_by_symbol:
                    template_context['charts_by_symbol'] = charts_by_symbol
            except Exception as _chart_e:
                logger.warning(f"Failed to attach charts in report: {_chart_e}")
            
            # Load and render template
            template_name = template_id or f"{report_type.value}.html"
            
            try:
                template = self.jinja_env.get_template(template_name)
            except jinja2.TemplateNotFound:
                # Use default template
                template_content = self.default_templates.get(report_type, "")
                template = jinja2.Template(template_content)
            
            rendered_content = template.render(**template_context)
            
            # Save report
            report_filename = f"{report_type.value}_{start_time.strftime('%Y%m%d_%H%M%S')}.html"
            report_path = self.output_dir / report_filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(rendered_content)
            
            generation_time = (datetime.now() - start_time).total_seconds()
            
            report_info = {
                'report_id': report_filename[:-5],  # Remove .html extension
                'report_type': report_type.value,
                'symbols': symbols,
                'content': rendered_content,
                'file_path': str(report_path),
                'generation_time': generation_time,
                'data_points': sum(len(data) if isinstance(data, (list, dict)) else 1 
                                 for data in data_collection.values()),
                'ai_insights_generated': bool(ai_insights),
                'timestamp': start_time
            }
            
            logger.info(f"Generated {report_type.value} report in {generation_time:.2f}s")
            return report_info
            
        except Exception as e:
            logger.error(f"Report generation failed: {e}")
            return {
                'error': str(e),
                'report_type': report_type.value,
                'symbols': symbols,
                'timestamp': datetime.now()
            }

    def _collect_charts_for_symbols(self, symbols: List[str], limit_per_symbol: int = 2) -> Dict[str, List[Dict[str, Any]]]:
        """Collect recent HTML charts generated by ChartingArtist for each symbol.

        Returns a dict: { symbol: [ { 'title': str, 'srcdoc': str }, ... ] }
        where 'srcdoc' is pre-escaped content suitable for iframe srcdoc attribute.
        """
        charts_dir = Path(os.getenv("CHART_STORAGE_PATH", "data/attachments/charts"))
        results: Dict[str, List[Dict[str, Any]]] = {}

        if not charts_dir.exists() or not charts_dir.is_dir():
            return results

        for sym in symbols:
            try:
                files = sorted(
                    charts_dir.glob(f"{sym}_*.html"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                picked = files[:limit_per_symbol]
                items: List[Dict[str, Any]] = []
                for fp in picked:
                    try:
                        content = fp.read_text(encoding="utf-8", errors="ignore")
                        # escape quotes for attribute usage
                        srcdoc = content.replace('"', '&quot;').replace("'", '&#39;')
                        # derive simple title
                        name = fp.stem
                        parts = name.split('_')
                        ctype = parts[1] if len(parts) > 1 else 'chart'
                        items.append({'title': f"{sym} {ctype}", 'srcdoc': srcdoc})
                    except Exception:
                        continue
                if items:
                    results[sym] = items
            except Exception:
                continue

        return results
    
    async def _collect_report_data(self, symbols: List[str], 
                                 report_type: ReportType) -> Dict[str, Any]:
        """Collect data needed for report generation"""
        data_collection = {}
        
        for symbol in symbols:
            try:
                # Get market data
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                
                market_data = get_YFin_data_window(symbol, start_date, end_date)
                
                if market_data is not None and not market_data.empty:
                    # Calculate basic metrics
                    current_price = market_data['Close'].iloc[-1]
                    prev_price = market_data['Close'].iloc[-2] if len(market_data) > 1 else current_price
                    change = current_price - prev_price
                    change_pct = (change / prev_price * 100) if prev_price != 0 else 0
                    
                    # Volume analysis
                    avg_volume = market_data['Volume'].mean()
                    current_volume = market_data['Volume'].iloc[-1]
                    
                    # Volatility
                    returns = market_data['Close'].pct_change().dropna()
                    volatility = returns.std() * np.sqrt(252) * 100
                    
                    data_collection[symbol] = {
                        'market_data': market_data,
                        'metrics': {
                            'current_price': float(current_price),
                            'change': float(change),
                            'change_pct': float(change_pct),
                            'volume': float(current_volume),
                            'avg_volume': float(avg_volume),
                            'volatility': float(volatility),
                            'high_52w': float(market_data['High'].max()),
                            'low_52w': float(market_data['Low'].min())
                        }
                    }
                
            except Exception as e:
                logger.warning(f"Failed to collect data for {symbol}: {e}")
                data_collection[symbol] = {'error': str(e)}
        
        return data_collection
    
    async def _generate_ai_insights(self, symbols: List[str], 
                                  data_collection: Dict[str, Any],
                                  report_type: ReportType) -> Dict[str, Any]:
        """Generate AI-powered insights for the report"""
        try:
            insights = {}
            
            for symbol in symbols:
                if symbol not in data_collection or 'error' in data_collection[symbol]:
                    continue
                
                metrics = data_collection[symbol].get('metrics', {})
                
                # Create analysis prompt
                prompt = self._create_analysis_prompt(symbol, metrics, report_type)
                
                # Get AI analysis
                result = await self.llm_orchestrator.execute_task(
                    agent_role="fundamental_expert",
                    task_prompt=prompt,
                    task_type="fundamental_analysis",
                    context={
                        'symbol': symbol,
                        'report_type': report_type.value,
                        'metrics': metrics
                    }
                )
                
                if result.success:
                    insights[symbol] = {
                        'analysis': result.result,
                        'confidence': getattr(result, 'confidence_score', 0.8),
                        'model_used': result.model_used.name if result.model_used else 'unknown'
                    }
            
            return insights
            
        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            return {}
    
    def _create_analysis_prompt(self, symbol: str, metrics: Dict[str, Any], 
                              report_type: ReportType) -> str:
        """Create analysis prompt based on report type and data"""
        
        if report_type == ReportType.DAILY_SUMMARY:
            return f"""
Please provide a brief daily analysis for {symbol} based on the following metrics:

Current Price: ${metrics.get('current_price', 'N/A'):.2f}
Daily Change: {metrics.get('change_pct', 'N/A'):.2f}%
Volume: {metrics.get('volume', 'N/A'):,.0f} (Avg: {metrics.get('avg_volume', 'N/A'):,.0f})
Volatility: {metrics.get('volatility', 'N/A'):.1f}%

Please provide:
1. Key observations about price action and volume
2. Short-term outlook (next 1-3 trading days)
3. Any notable technical or fundamental factors
4. Risk considerations

Keep the analysis concise and actionable.
"""
        
        elif report_type == ReportType.RISK_ASSESSMENT:
            return f"""
Please provide a risk assessment for {symbol} based on the following data:

Current Price: ${metrics.get('current_price', 'N/A'):.2f}
52-Week High: ${metrics.get('high_52w', 'N/A'):.2f}
52-Week Low: ${metrics.get('low_52w', 'N/A'):.2f}
Volatility: {metrics.get('volatility', 'N/A'):.1f}%
Volume Pattern: Current vs Average = {(metrics.get('volume', 0) / max(metrics.get('avg_volume', 1), 1)):.1f}x

Please assess:
1. Current risk level (Low/Medium/High)
2. Key risk factors to monitor
3. Potential downside scenarios
4. Risk mitigation suggestions
5. Position sizing recommendations

Focus on practical risk management insights.
"""
        
        else:  # Default general analysis
            return f"""
Please analyze {symbol} based on the current market data:

Price: ${metrics.get('current_price', 'N/A'):.2f} ({metrics.get('change_pct', 'N/A'):+.2f}%)
Volume: {metrics.get('volume', 'N/A'):,.0f}
Volatility: {metrics.get('volatility', 'N/A'):.1f}%

Provide insights on current market position, trends, and outlook.
"""
    
    def _get_daily_summary_template(self) -> str:
        """Get default daily summary template with embedded charts (if available)"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Daily Market Summary - {{ generation_time.strftime('%Y-%m-%d') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { color: #2c5aa0; border-bottom: 2px solid #2c5aa0; padding-bottom: 10px; }
        .symbol-section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
        .metric { background: #f8f9fa; padding: 10px; border-radius: 5px; }
        .positive { color: #28a745; }
        .negative { color: #dc3545; }
        .insight { background: #e9f4ff; padding: 15px; border-left: 4px solid #2c5aa0; margin: 10px 0; }
        .charts { background: #f5f7fb; padding: 12px; border-radius: 6px; }
        .chart-item { background:#fff; padding:4px; border-radius:6px; margin:8px 0; }
    </style>
</head>
<body>
    <div class=\"header\">
        <h1>Daily Market Summary</h1>
        <p>Generated on {{ generation_time.strftime('%B %d, %Y at %I:%M %p') }}</p>
    </div>
    
    {% for symbol in symbols %}
    <div class=\"symbol-section\">
        <h2>{{ symbol }}</h2>
        
        {% if data[symbol] and 'metrics' in data[symbol] %}
        <div class=\"metrics\">
            <div class=\"metric\">
                <strong>Current Price</strong><br>
                ${{ \"%.2f\"|format(data[symbol].metrics.current_price) }}
            </div>
            <div class=\"metric\">
                <strong>Daily Change</strong><br>
                <span class=\"{{ 'positive' if data[symbol].metrics.change_pct > 0 else 'negative' }}\">{{ \"{:+.2f}%\".format(data[symbol].metrics.change_pct) }}</span>
            </div>
            <div class=\"metric\">
                <strong>Volume</strong><br>
                {{ \"{:,.0f}\".format(data[symbol].metrics.volume) }}
            </div>
            <div class=\"metric\">
                <strong>Volatility</strong><br>
                {{ \"%.1f%\"|format(data[symbol].metrics.volatility) }}
            </div>
        </div>
        
        {% if ai_insights and symbol in ai_insights %}
        <div class=\"insight\">
            <h3>AI Analysis</h3>
            <p>{{ ai_insights[symbol].analysis|replace('\\n', '<br>')|safe }}</p>
            <small>Confidence: {{ \"%.0f%\"|format(ai_insights[symbol].confidence * 100) }} | Model: {{ ai_insights[symbol].model_used }}</small>
        </div>
        {% endif %}

        {% if charts_by_symbol and charts_by_symbol.get(symbol) %}
        <div class=\"charts\">
            <h3>Charts</h3>
            {% for chart in charts_by_symbol.get(symbol, []) %}
            <div class=\"chart-item\">
                <div style=\"font-weight:600;margin:4px 0;\">{{ chart.title }}</div>
                <iframe srcdoc='{{ chart.srcdoc | safe }}' width=\"100%\" height=\"520\" style=\"border:0; border-radius:6px;\"></iframe>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        {% else %}
        <p>Data not available for {{ symbol }}</p>
        {% endif %}
    </div>
    {% endfor %}
    
    <div style=\"margin-top: 30px; font-size: 12px; color: #666;\"> 
        <p>This report was generated automatically by TradingAgents-CN AI system.</p>
        <p>Report ID: {{ report_type }}_{{ generation_time.strftime('%Y%m%d_%H%M%S') }}</p>
    </div>
</body>
</html>
"""
    
    def _get_market_alert_template(self) -> str:
        """Get default market alert template with optional chart embed"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Market Alert - {{ generation_time.strftime('%Y-%m-%d %H:%M') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .alert { padding: 20px; border-radius: 8px; margin: 10px 0; }
        .alert.critical { background: #f8d7da; border: 1px solid #f5c6cb; }
        .alert.warning { background: #fff3cd; border: 1px solid #ffeaa7; }
        .alert.info { background: #d1ecf1; border: 1px solid #bee5eb; }
        .timestamp { color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <h1>🚨 Market Alert</h1>
    <p class="timestamp">{{ generation_time.strftime('%B %d, %Y at %I:%M %p') }}</p>
    
    {% for symbol in symbols %}
    {% if data[symbol] and 'metrics' in data[symbol] %}
    <div class="alert {{ 'critical' if data[symbol].metrics.change_pct|abs > 5 else 'warning' if data[symbol].metrics.change_pct|abs > 3 else 'info' }}">
        <h2>{{ symbol }}</h2>
        <p><strong>Price Movement:</strong> {{ "{:+.2f}% (${:.2f})".format(data[symbol].metrics.change_pct, data[symbol].metrics.current_price) }}</p>
        
        {% if ai_insights and symbol in ai_insights %}
        <p><strong>AI Analysis:</strong></p>
        <p>{{ ai_insights[symbol].analysis|replace('\\n', '<br>')|safe }}</p>
        {% endif %}

        {% if charts_by_symbol and charts_by_symbol.get(symbol) %}
        <div class="charts" style="margin-top: 10px;">
            {% for chart in charts_by_symbol.get(symbol, [])[:1] %}
            <iframe srcdoc='{{ chart.srcdoc | safe }}' width="100%" height="420" style="border:0; border-radius:6px;"></iframe>
            {% endfor %}
        </div>
        {% endif %}
    </div>
    {% endif %}
    {% endfor %}
</body>
</html>
"""
    
    def _get_risk_assessment_template(self) -> str:
        """Get default risk assessment template with optional chart embed"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Risk Assessment Report - {{ generation_time.strftime('%Y-%m-%d') }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .risk-high { color: #dc3545; font-weight: bold; }
        .risk-medium { color: #ffc107; font-weight: bold; }
        .risk-low { color: #28a745; font-weight: bold; }
        .assessment { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; }
    </style>
</head>
<body>
    <h1>Risk Assessment Report</h1>
    <p>Generated: {{ generation_time.strftime('%B %d, %Y') }}</p>
    
    {% for symbol in symbols %}
    <div class="assessment">
        <h2>{{ symbol }}</h2>
        
        {% if data[symbol] and 'metrics' in data[symbol] %}
        <p><strong>Current Price:</strong> ${{ "%.2f"|format(data[symbol].metrics.current_price) }}</p>
        <p><strong>Volatility Level:</strong> {{ "%.1f%"|format(data[symbol].metrics.volatility) }}</p>
        
        {% set volatility = data[symbol].metrics.volatility %}
        <p><strong>Risk Level:</strong> 
        {% if volatility > 40 %}
            <span class="risk-high">HIGH</span>
        {% elif volatility > 25 %}
            <span class="risk-medium">MEDIUM</span>
        {% else %}
            <span class="risk-low">LOW</span>
        {% endif %}
        </p>
        
        {% if ai_insights and symbol in ai_insights %}
        <div style="margin-top: 15px;">
            <h3>Risk Analysis</h3>
            <p>{{ ai_insights[symbol].analysis|replace('\\n', '<br>')|safe }}</p>
        </div>
        {% endif %}

        {% if charts_by_symbol and charts_by_symbol.get(symbol) %}
        <div class="charts" style="margin-top: 12px;">
            {% for chart in charts_by_symbol.get(symbol, [])[:1] %}
            <iframe srcdoc='{{ chart.srcdoc | safe }}' width="100%" height="440" style="border:0; border-radius:6px;"></iframe>
            {% endfor %}
        </div>
        {% endif %}
        {% endif %}
    </div>
    {% endfor %}
</body>
</html>
"""
    
    def _create_default_templates(self):
        """Create default template files"""
        for report_type, template_content in self.default_templates.items():
            template_file = self.template_dir / f"{report_type.value}.html"
            if not template_file.exists():
                with open(template_file, 'w', encoding='utf-8') as f:
                    f.write(template_content)


class SmartAlertSystem:
    """Intelligent alert system with machine learning and contextual awareness"""
    
    def __init__(self, 
                 llm_orchestrator=None,
                 email_config: Optional[Dict[str, Any]] = None):
        
        self.llm_orchestrator = llm_orchestrator
        self.email_sender = EmailSender() if email_config else None
        
        # Alert management
        self.active_conditions: Dict[str, AlertCondition] = {}
        self.alert_history: List[SmartAlert] = []
        self.condition_monitor = MarketConditionMonitor()
        
        # Alert templates
        self.alert_templates = self._initialize_alert_templates()
        
        logger.info("Smart Alert System initialized")
    
    def add_alert_condition(self, condition: AlertCondition) -> bool:
        """Add a new alert condition"""
        try:
            self.active_conditions[condition.condition_id] = condition
            logger.info(f"Added alert condition: {condition.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add alert condition: {e}")
            return False
    
    async def check_alert_conditions(self, symbols: List[str]) -> List[SmartAlert]:
        """Check all active alert conditions and generate alerts"""
        triggered_alerts = []
        
        for condition in self.active_conditions.values():
            if not condition.enabled:
                continue
            
            # Check cooldown
            if (condition.last_triggered and 
                datetime.now() - condition.last_triggered < timedelta(minutes=condition.cooldown_minutes)):
                continue
            
            # Check condition based on trigger type
            alert = await self._evaluate_condition(condition, symbols)
            if alert:
                triggered_alerts.append(alert)
                condition.last_triggered = datetime.now()
                condition.trigger_count += 1
        
        # Store alerts in history
        self.alert_history.extend(triggered_alerts)
        
        # Keep only recent alerts in memory (last 1000)
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        return triggered_alerts
    
    async def _evaluate_condition(self, condition: AlertCondition, 
                                symbols: List[str]) -> Optional[SmartAlert]:
        """Evaluate a specific alert condition"""
        try:
            relevant_symbols = condition.symbols or symbols
            
            for symbol in relevant_symbols:
                # Get market data
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
                
                market_data = get_YFin_data_window(symbol, start_date, end_date)
                if market_data is None or market_data.empty:
                    continue
                
                # Evaluate based on trigger type
                triggered = False
                context = {}
                
                if condition.trigger_type == AutomationTrigger.PRICE_THRESHOLD:
                    triggered, context = self._check_price_threshold(
                        market_data, condition.parameters
                    )
                
                elif condition.trigger_type == AutomationTrigger.VOLUME_THRESHOLD:
                    triggered, context = self._check_volume_threshold(
                        market_data, condition.parameters
                    )
                
                elif condition.trigger_type == AutomationTrigger.TECHNICAL_SIGNAL:
                    triggered, context = self._check_technical_signal(
                        market_data, condition.parameters
                    )
                
                elif condition.trigger_type == AutomationTrigger.MARKET_CONDITION:
                    market_conditions = self.condition_monitor.analyze_market_conditions(
                        symbol, market_data
                    )
                    triggered, context = self._check_market_condition(
                        market_conditions, condition.parameters
                    )
                
                if triggered:
                    # Generate intelligent alert with AI analysis
                    alert = await self._generate_smart_alert(
                        condition, symbol, context, market_data
                    )
                    return alert
            
            return None
            
        except Exception as e:
            logger.error(f"Condition evaluation failed for {condition.condition_id}: {e}")
            return None
    
    def _check_price_threshold(self, data: pd.DataFrame, 
                             parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check price threshold conditions"""
        current_price = data['Close'].iloc[-1]
        
        threshold_type = parameters.get('type', 'absolute')
        threshold_value = parameters.get('value', 0)
        
        if threshold_type == 'absolute':
            if parameters.get('direction') == 'above':
                triggered = current_price > threshold_value
            else:
                triggered = current_price < threshold_value
        
        elif threshold_type == 'percentage':
            prev_price = data['Close'].iloc[-2] if len(data) > 1 else current_price
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            if parameters.get('direction') == 'above':
                triggered = change_pct > threshold_value
            else:
                triggered = change_pct < threshold_value
        
        else:
            triggered = False
        
        context = {
            'current_price': float(current_price),
            'threshold_value': threshold_value,
            'threshold_type': threshold_type,
            'direction': parameters.get('direction', 'above')
        }
        
        return triggered, context
    
    def _check_volume_threshold(self, data: pd.DataFrame,
                              parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check volume threshold conditions"""
        current_volume = data['Volume'].iloc[-1]
        avg_volume = data['Volume'].mean()
        
        multiplier = parameters.get('multiplier', 2.0)
        triggered = current_volume > avg_volume * multiplier
        
        context = {
            'current_volume': float(current_volume),
            'average_volume': float(avg_volume),
            'volume_ratio': float(current_volume / avg_volume),
            'threshold_multiplier': multiplier
        }
        
        return triggered, context
    
    def _check_technical_signal(self, data: pd.DataFrame,
                               parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check technical analysis signals"""
        signal_type = parameters.get('signal', 'rsi_oversold')
        
        triggered = False
        context = {}
        
        if signal_type == 'rsi_oversold':
            rsi = self.condition_monitor._calculate_rsi(data['Close'])
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                threshold = parameters.get('threshold', 30)
                triggered = current_rsi < threshold
                context = {'rsi': float(current_rsi), 'threshold': threshold}
        
        elif signal_type == 'rsi_overbought':
            rsi = self.condition_monitor._calculate_rsi(data['Close'])
            if not rsi.empty:
                current_rsi = rsi.iloc[-1]
                threshold = parameters.get('threshold', 70)
                triggered = current_rsi > threshold
                context = {'rsi': float(current_rsi), 'threshold': threshold}
        
        elif signal_type == 'moving_average_cross':
            short_ma = data['Close'].rolling(parameters.get('short_period', 20)).mean()
            long_ma = data['Close'].rolling(parameters.get('long_period', 50)).mean()
            
            if len(short_ma.dropna()) > 1 and len(long_ma.dropna()) > 1:
                # Check for golden cross (short MA crosses above long MA)
                prev_short = short_ma.iloc[-2]
                prev_long = long_ma.iloc[-2]
                curr_short = short_ma.iloc[-1]
                curr_long = long_ma.iloc[-1]
                
                if parameters.get('direction') == 'golden_cross':
                    triggered = prev_short <= prev_long and curr_short > curr_long
                else:  # death_cross
                    triggered = prev_short >= prev_long and curr_short < curr_long
                
                context = {
                    'short_ma': float(curr_short),
                    'long_ma': float(curr_long),
                    'cross_type': 'golden' if curr_short > curr_long else 'death'
                }
        
        return triggered, context
    
    def _check_market_condition(self, market_conditions: Dict[str, Any],
                               parameters: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Check market condition triggers"""
        condition_type = parameters.get('condition', 'volatility_spike')
        
        if condition_type == 'volatility_spike':
            volatility_data = market_conditions.get('volatility', {})
            triggered = volatility_data.get('spike_detected', False)
            context = volatility_data
        
        elif condition_type == 'volume_surge':
            volume_data = market_conditions.get('volume', {})
            triggered = volume_data.get('surge_detected', False)
            context = volume_data
        
        elif condition_type == 'technical_breakout':
            technical_data = market_conditions.get('technical', {})
            support_resistance = technical_data.get('support_resistance', {})
            triggered = (support_resistance.get('near_resistance', False) or 
                        support_resistance.get('near_support', False))
            context = technical_data
        
        else:
            triggered = False
            context = market_conditions
        
        return triggered, context
    
    async def _generate_smart_alert(self, condition: AlertCondition, 
                                  symbol: str, context: Dict[str, Any],
                                  market_data: pd.DataFrame) -> SmartAlert:
        """Generate intelligent alert with AI analysis and recommendations"""
        
        alert_id = f"alert_{condition.condition_id}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create base alert
        alert = SmartAlert(
            alert_id=alert_id,
            title=f"{condition.name} - {symbol}",
            message=f"Alert condition '{condition.name}' triggered for {symbol}",
            severity=condition.severity,
            symbol=symbol,
            condition_id=condition.condition_id,
            context=context
        )
        
        # Generate AI-powered analysis and recommendations
        if self.llm_orchestrator:
            try:
                # Create context prompt
                analysis_prompt = f"""
Alert triggered for {symbol}: {condition.name}

Current market situation:
{json.dumps(context, indent=2)}

Condition details: {condition.description}
Alert severity: {condition.severity.value}

Please provide:
1. Analysis of what triggered this alert
2. Potential impact on the stock price
3. Recommended actions for investors
4. Risk level and time sensitivity
5. What to monitor going forward

Keep the response concise but actionable.
"""
                
                result = await self.llm_orchestrator.execute_task(
                    agent_role="risk_manager",
                    task_prompt=analysis_prompt,
                    task_type="risk_assessment",
                    context={
                        'symbol': symbol,
                        'alert_severity': condition.severity.value,
                        'condition_type': condition.trigger_type.value
                    }
                )
                
                if result.success:
                    # Parse AI response for recommendations
                    alert.message = result.result
                    alert.recommendations = self._extract_recommendations(result.result)
                
            except Exception as e:
                logger.error(f"AI alert analysis failed: {e}")
        
        return alert
    
    def _extract_recommendations(self, ai_response: str) -> List[str]:
        """Extract actionable recommendations from AI response"""
        recommendations = []
        
        # Simple pattern matching for recommendations
        lines = ai_response.split('\n')
        in_recommendations = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for recommendation sections
            if any(keyword in line.lower() for keyword in ['recommend', 'action', 'suggest']):
                in_recommendations = True
                if ':' in line:
                    rec = line.split(':', 1)[1].strip()
                    if rec:
                        recommendations.append(rec)
                continue
            
            # Extract numbered or bulleted items
            if in_recommendations and (line.startswith(('1.', '2.', '3.', '-', '*'))):
                rec = line[2:].strip() if line[1:2] in '.* ' else line[1:].strip()
                if rec:
                    recommendations.append(rec)
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _initialize_alert_templates(self) -> Dict[str, str]:
        """Initialize alert message templates"""
        return {
            'price_threshold': "Price alert: {symbol} {direction} ${threshold:.2f} (Current: ${current_price:.2f})",
            'volume_threshold': "Volume surge: {symbol} volume {volume_ratio:.1f}x average ({current_volume:,.0f})",
            'technical_signal': "Technical signal: {symbol} {signal_type} (RSI: {rsi:.1f})",
            'market_condition': "Market condition: {symbol} {condition_type} detected",
            'news_event': "News alert: {symbol} - {headline}",
            'general': "Alert: {condition_name} triggered for {symbol}"
        }


class IntelligentAutomation:
    """Main automation orchestrator combining all automation capabilities"""
    
    def __init__(self, 
                 config: Dict[str, Any],
                 llm_orchestrator=None,
                 rag_system=None):
        
        self.config = config
        self.llm_orchestrator = llm_orchestrator
        self.rag_system = rag_system
        
        # Initialize subsystems
        self.report_generator = ReportGenerator(
            template_dir=config.get('templates_dir', 'report_templates'),
            output_dir=config.get('reports_dir', 'generated_reports'),
            llm_orchestrator=llm_orchestrator
        )
        
        self.alert_system = SmartAlertSystem(
            llm_orchestrator=llm_orchestrator,
            email_config=config.get('email')
        )
        
        # Automation tasks
        self.automation_tasks: Dict[str, AutomationTask] = {}
        self.scheduler_running = False
        self.scheduler_thread = None
        
        # Performance metrics
        self.metrics = {
            'reports_generated': 0,
            'alerts_sent': 0,
            'automation_runs': 0,
            'success_rate': 0.0,
            'last_updated': datetime.now()
        }
        
        logger.info("Intelligent Automation System initialized")
    
    def add_automation_task(self, task: AutomationTask) -> bool:
        """Add an automation task"""
        try:
            self.automation_tasks[task.task_id] = task
            
            # Schedule if needed
            if task.schedule and task.enabled:
                self._schedule_task(task)
            
            logger.info(f"Added automation task: {task.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add automation task: {e}")
            return False
    
    def start_scheduler(self):
        """Start the automation scheduler"""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Automation scheduler started")
    
    def stop_scheduler(self):
        """Stop the automation scheduler"""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logger.info("Automation scheduler stopped")
    
    def _run_scheduler(self):
        """Run the automation scheduler"""
        while self.scheduler_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def _schedule_task(self, task: AutomationTask):
        """Schedule a task based on its schedule string"""
        try:
            if task.schedule == "daily":
                schedule.every().day.at("09:00").do(self._execute_task, task.task_id)
            elif task.schedule == "hourly":
                schedule.every().hour.do(self._execute_task, task.task_id)
            elif task.schedule.startswith("every"):
                # Parse "every X minutes/hours"
                parts = task.schedule.split()
                if len(parts) >= 3:
                    interval = int(parts[1])
                    unit = parts[2].lower()
                    
                    if unit.startswith("minute"):
                        schedule.every(interval).minutes.do(self._execute_task, task.task_id)
                    elif unit.startswith("hour"):
                        schedule.every(interval).hours.do(self._execute_task, task.task_id)
            
        except Exception as e:
            logger.error(f"Task scheduling failed for {task.task_id}: {e}")
    
    async def _execute_task(self, task_id: str):
        """Execute an automation task"""
        if task_id not in self.automation_tasks:
            return
        
        task = self.automation_tasks[task_id]
        if not task.enabled:
            return
        
        try:
            task.last_run = datetime.now()
            task.run_count += 1
            
            # Execute task action
            if asyncio.iscoroutinefunction(task.action):
                result = await task.action(**task.parameters)
            else:
                result = task.action(**task.parameters)
            
            task.success_count += 1
            self.metrics['automation_runs'] += 1
            
            logger.info(f"Automation task executed successfully: {task.name}")
            
        except Exception as e:
            task.failure_count += 1
            logger.error(f"Automation task failed: {task.name} - {e}")
        
        # Update success rate
        total_runs = sum(task.run_count for task in self.automation_tasks.values())
        total_successes = sum(task.success_count for task in self.automation_tasks.values())
        self.metrics['success_rate'] = total_successes / max(total_runs, 1)
        self.metrics['last_updated'] = datetime.now()
    
    async def generate_scheduled_report(self, report_type: ReportType, 
                                      symbols: List[str]) -> Dict[str, Any]:
        """Generate a scheduled report"""
        try:
            result = await self.report_generator.generate_report(
                report_type=report_type,
                symbols=symbols
            )
            
            self.metrics['reports_generated'] += 1
            return result
            
        except Exception as e:
            logger.error(f"Scheduled report generation failed: {e}")
            return {'error': str(e)}
    
    async def run_alert_check(self, symbols: List[str]) -> List[SmartAlert]:
        """Run alert condition checks"""
        try:
            alerts = await self.alert_system.check_alert_conditions(symbols)
            
            # Send alerts if any triggered
            if alerts:
                for alert in alerts:
                    await self._send_alert(alert)
                    
                self.metrics['alerts_sent'] += len(alerts)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Alert check failed: {e}")
            return []
    
    async def _send_alert(self, alert: SmartAlert):
        """Send alert notification"""
        try:
            # Email notification if configured
            if self.alert_system.email_sender:
                subject = f"[{alert.severity.value.upper()}] {alert.title}"
                
                body = f"""
Alert: {alert.title}
Severity: {alert.severity.value.upper()}
Symbol: {alert.symbol or 'N/A'}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Message:
{alert.message}

Recommendations:
{chr(10).join(['• ' + rec for rec in alert.recommendations])}

Context:
{json.dumps(alert.context, indent=2)}
"""
                
                # This would send email - implementation depends on email configuration
                logger.info(f"Alert notification prepared: {alert.title}")
            
        except Exception as e:
            logger.error(f"Alert sending failed: {e}")
    
    def get_automation_status(self) -> Dict[str, Any]:
        """Get automation system status"""
        return {
            'scheduler_running': self.scheduler_running,
            'active_tasks': len([t for t in self.automation_tasks.values() if t.enabled]),
            'total_tasks': len(self.automation_tasks),
            'metrics': self.metrics,
            'alert_conditions': len(self.alert_system.active_conditions),
            'recent_alerts': len([a for a in self.alert_system.alert_history 
                                if datetime.now() - a.timestamp < timedelta(hours=24)])
        }


# Utility functions for common automation patterns
def create_daily_summary_task(symbols: List[str], 
                             automation_system: IntelligentAutomation) -> AutomationTask:
    """Create a daily summary automation task"""
    
    async def generate_daily_summary():
        return await automation_system.generate_scheduled_report(
            ReportType.DAILY_SUMMARY, symbols
        )
    
    return AutomationTask(
        task_id="daily_summary",
        name="Daily Market Summary",
        task_type="report_generation",
        trigger=AutomationTrigger.SCHEDULED,
        action=generate_daily_summary,
        schedule="daily",
        parameters={'symbols': symbols}
    )


def create_price_alert_condition(symbol: str, threshold: float, 
                                direction: str = "above") -> AlertCondition:
    """Create a price threshold alert condition"""
    
    return AlertCondition(
        condition_id=f"price_alert_{symbol}_{direction}_{threshold}",
        name=f"{symbol} Price {direction.title()} ${threshold}",
        description=f"Alert when {symbol} price goes {direction} ${threshold}",
        trigger_type=AutomationTrigger.PRICE_THRESHOLD,
        severity=AlertSeverity.WARNING,
        parameters={
            'type': 'absolute',
            'value': threshold,
            'direction': direction
        },
        symbols=[symbol]
    )
