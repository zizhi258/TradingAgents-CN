"""
TradingAgents-CN AI Module

Comprehensive AI-powered features for financial analysis including:
- Multi-LLM Integration with intelligent routing
- RAG System with financial knowledge base
- Intelligent Automation for reports and alerts  
- Enhanced Multi-Agent Coordination
- Production API with cost optimization
- Seamless integration with existing components

This module transforms TradingAgents-CN into an advanced AI-powered financial analysis system.
"""

# Import all AI components for easy access
from .llm_orchestrator import AIOrchestrator, TaskPriority, OrchestratorStatus
from .financial_rag import FinancialRAGSystem, FinancialDocument, RAGQuery, RAGResponse
from .intelligent_automation import (
    IntelligentAutomation, ReportType, AlertSeverity, AutomationTrigger,
    SmartAlert, ReportGenerator, SmartAlertSystem
)
from .enhanced_coordination import (
    EnhancedMultiAgentCoordinator, AgentRole, CoordinationMode, ConsensusMethod,
    CoordinationTask, AgentOpinion, ConsensusResult
)
from .production_api import ProductionAPIServer, create_production_api
from .ai_integration_manager import (
    ComprehensiveAIIntegrationManager, IntegrationConfig,
    create_ai_integration_manager
)

# Utility imports
from tradingagents.utils.logging_init import get_logger

logger = get_logger("ai_module")

# Version information
__version__ = "1.0.0"
__author__ = "TradingAgents-CN AI Team"

# Main classes for easy import
__all__ = [
    # Core AI Systems
    'AIOrchestrator',
    'FinancialRAGSystem', 
    'IntelligentAutomation',
    'EnhancedMultiAgentCoordinator',
    'ProductionAPIServer',
    
    # Integration Manager
    'ComprehensiveAIIntegrationManager',
    'IntegrationConfig',
    
    # Data Models
    'FinancialDocument',
    'RAGQuery', 
    'RAGResponse',
    'CoordinationTask',
    'AgentOpinion',
    'ConsensusResult',
    'SmartAlert',
    
    # Enums
    'TaskPriority',
    'OrchestratorStatus', 
    'ReportType',
    'AlertSeverity',
    'AutomationTrigger',
    'AgentRole',
    'CoordinationMode',
    'ConsensusMethod',
    
    # Factory functions
    'create_production_api',
    'create_ai_integration_manager',
    
    # Utilities
    'initialize_ai_system',
    'create_comprehensive_analysis'
]


# Convenience functions for quick setup and usage
async def initialize_ai_system(config_path: str = None, 
                              enable_all_features: bool = True) -> ComprehensiveAIIntegrationManager:
    """
    Initialize the complete AI system with sensible defaults
    
    Args:
        config_path: Path to configuration file (optional)
        enable_all_features: Whether to enable all AI features
        
    Returns:
        ComprehensiveAIIntegrationManager: Initialized AI system
    """
    
    try:
        # Load configuration
        if config_path:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            # Default configuration
            config = {
                'enable_llm_orchestrator': enable_all_features,
                'enable_rag_system': enable_all_features,
                'enable_automation': enable_all_features,
                'enable_coordination': enable_all_features,
                'enable_production_api': enable_all_features,
                'integrate_charting_artist': True,
                'integrate_news_analysis': True,
                'integrate_risk_management': True
            }
        
        # Create AI integration manager
        ai_manager = create_ai_integration_manager(config)
        
        # Load multi-model configuration
        from tradingagents.config.config_manager import ConfigManager
        config_manager = ConfigManager()
        
        # Try to load multi-model config
        try:
            multi_model_config = config_manager.get_config('multi_model_config.yaml')
        except:
            # Fallback configuration
            multi_model_config = {
                'providers': {
                    'google_ai': {'enabled': True},
                    'siliconflow': {'enabled': True},
                    'deepseek': {'enabled': True}
                }
            }
        
        # Initialize AI systems
        await ai_manager.initialize_ai_systems(multi_model_config)
        
        # Initialize integrations
        await ai_manager.initialize_integrations()
        
        logger.info("AI system initialized successfully")
        return ai_manager
        
    except Exception as e:
        logger.error(f"AI system initialization failed: {e}")
        raise


async def create_comprehensive_analysis(symbol: str,
                                      analysis_type: str = "full",
                                      ai_manager: ComprehensiveAIIntegrationManager = None) -> Dict[str, Any]:
    """
    Create comprehensive AI-powered analysis for a symbol
    
    Args:
        symbol: Stock symbol to analyze
        analysis_type: Type of analysis ("full", "technical", "fundamental", "risk")
        ai_manager: Initialized AI manager (will create if None)
        
    Returns:
        Dict containing comprehensive analysis results
    """
    
    try:
        # Initialize AI manager if not provided
        if ai_manager is None:
            ai_manager = await initialize_ai_system()
        
        # Run comprehensive analysis
        analysis_results = await ai_manager.run_comprehensive_analysis(
            symbol=symbol,
            analysis_type=analysis_type,
            include_chart_analysis=True,
            include_news_analysis=True, 
            include_risk_assessment=True
        )
        
        logger.info(f"Comprehensive analysis completed for {symbol}")
        return analysis_results
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed for {symbol}: {e}")
        return {
            'symbol': symbol,
            'error': str(e),
            'success': False
        }


# Example usage functions
def example_llm_orchestrator():
    """Example of using the LLM Orchestrator"""
    
    example_code = '''
# Initialize AI Orchestrator
from tradingagents.ai import AIOrchestrator, TaskPriority
import asyncio

async def main():
    config = {
        'providers': {
            'google_ai': {'enabled': True, 'api_key_env': 'GOOGLE_API_KEY'},
            'siliconflow': {'enabled': True, 'api_key_env': 'SILICONFLOW_API_KEY'}
        },
        'caching': {'enabled': True, 'ttl': 3600},
        'cost_management': {'daily_max': 50.0}
    }
    
    orchestrator = AIOrchestrator(config)
    
    # Execute analysis task
    result = await orchestrator.execute_task(
        agent_role="fundamental_expert",
        task_prompt="Analyze AAPL stock fundamentals",
        task_type="fundamental_analysis",
        priority=TaskPriority.HIGH
    )
    
    print(f"Analysis: {result.result}")
    print(f"Model used: {result.model_used.name}")
    print(f"Cost: ${result.actual_cost:.3f}")

# Run the example
asyncio.run(main())
'''
    
    return example_code


def example_rag_system():
    """Example of using the RAG System"""
    
    example_code = '''
# Initialize RAG System
from tradingagents.ai import FinancialRAGSystem, RAGQuery
import asyncio

async def main():
    # Initialize RAG system
    rag_system = FinancialRAGSystem(
        knowledge_base_path="financial_kb",
        llm_orchestrator=orchestrator  # From previous example
    )
    
    # Ingest some financial data
    stats = rag_system.ingest_symbol_data(
        symbol="AAPL",
        include_news=True,
        include_market_data=True,
        days_back=30
    )
    print(f"Ingested: {stats}")
    
    # Query the system
    response = await rag_system.query(
        query_text="What are the recent trends for AAPL?",
        query_type="general",
        symbols=["AAPL"]
    )
    
    print(f"Answer: {response.generated_response}")
    print(f"Sources: {response.sources}")

# Run the example
asyncio.run(main())
'''
    
    return example_code


def example_production_api():
    """Example of setting up the Production API"""
    
    example_code = '''
# Setup Production API
from tradingagents.ai import create_production_api
import uvicorn

# Create API server
config = {
    'enable_docs': True,
    'rate_limiting': True,
    'cost_optimization': True,
    'cors_origins': ["*"]
}

api_server = create_production_api(config)

# Set AI components (from previous examples)
api_server.set_ai_components(
    ai_orchestrator=orchestrator,
    rag_system=rag_system, 
    automation_system=automation_system,
    coordinator=coordinator
)

# Run the server
if __name__ == "__main__":
    api_server.run(host="0.0.0.0", port=8000)
'''
    
    return example_code


def example_comprehensive_integration():
    """Example of comprehensive AI integration"""
    
    example_code = '''
# Comprehensive AI Integration
from tradingagents.ai import create_ai_integration_manager
import asyncio

async def main():
    # Initialize comprehensive AI system
    ai_manager = await initialize_ai_system(
        enable_all_features=True
    )
    
    # Run comprehensive analysis
    results = await ai_manager.run_comprehensive_analysis(
        symbol="AAPL",
        analysis_type="full",
        include_chart_analysis=True,
        include_news_analysis=True,
        include_risk_assessment=True
    )
    
    # Print results
    print("=== Comprehensive Analysis Results ===")
    print(f"Symbol: {results['symbol']}")
    print(f"Success: {results['success']}")
    print(f"Components analyzed: {results['components_analyzed']}")
    
    if 'chart_analysis' in results['components']:
        chart = results['components']['chart_analysis']
        print(f"Chart Analysis: {chart.get('confidence_score', 'N/A')}")
    
    if 'news_analysis' in results['components']:
        news = results['components']['news_analysis']
        print(f"News Sentiment: {news.get('sentiment_metrics', {})}")
    
    if 'risk_assessment' in results['components']:
        risk = results['components']['risk_assessment']
        print(f"Risk Level: {risk.get('overall_risk_level', 'N/A')}")
    
    # Start production services
    await ai_manager.start_production_services()
    
    print("AI system is ready for production use!")

# Run the example
asyncio.run(main())
'''
    
    return example_code


# Documentation helpers
def get_feature_overview() -> str:
    """Get overview of all AI features"""
    
    return """
TradingAgents-CN AI Features Overview:

🧠 Multi-LLM Integration System:
- Intelligent routing across OpenAI, Claude, Gemini, DeepSeek
- Automatic failover and cost optimization
- Performance monitoring and circuit breakers

📚 RAG System:
- Financial domain knowledge base with vector embeddings
- Semantic search for contextual information
- Automatic news and market data ingestion

🤖 Intelligent Automation:
- Automated report generation with AI insights
- Smart alerting with contextual analysis
- Dynamic strategy recommendations

👥 Enhanced Multi-Agent Coordination:
- LLM-powered agent selection and consensus building
- Conflict resolution and evidence-based decisions
- Performance tracking and optimization

🚀 Production API:
- Cost-optimized endpoints with rate limiting
- Real-time monitoring and health checks
- RESTful API with comprehensive documentation

🔗 Seamless Integration:
- Enhanced ChartingArtist with AI insights
- AI-powered news sentiment analysis
- Advanced risk management with ML predictions
"""


logger.info("TradingAgents-CN AI module loaded successfully")